"""Question 3 conditional robust design based on the verified Q2 ODE interface.

This program does not use target-engine bench data.  It builds a deterministic
Latin-hypercube design from the conditioned Q2 open-system ODE, validates an
Extra-Trees response emulator on a held-out set, performs a robust multi-
objective search, and finally re-evaluates the recommendation with the ODE.
All reported results therefore remain conditional model predictions.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
from scipy.stats import qmc
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figure"
PAPER_FIG = ROOT.parent / "figures"
FIG.mkdir(exist_ok=True)
PAPER_FIG.mkdir(exist_ok=True)
SEED = 20260814
TRAIN_N = 400
SEARCH_N = 50000
BOUNDS = np.array([
    [132.3, 149.8], [20.0, 170.0], [10.0, 30.0], [570.0, 620.0],
    [0.95, 1.15], [0.96, 1.04], [0.90, 1.10],
])
NAMES = ["d_mm", "overlap_deg", "ign_btdc_deg", "eoi_deg", "lambda",
         "combustion_efficiency_scale", "friction_scale_multiplier"]


def load_q2():
    path = ROOT / "q2_closed_loop.py"
    spec = importlib.util.spec_from_file_location("q2_closed_loop", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


Q2 = load_q2()
BASE_ETA_COMB = 0.7392333965932314
BASE_FRICTION = 1.8


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def geometry(d_mm: float) -> tuple[float, float]:
    r, R, e, B = d_mm / 2.0, 105.0, 15.0, 50.0
    s = r - R / 2.0
    rho = ((math.sqrt(3.0) * R / 2.0) ** 2 + s * s) / (2.0 * s)
    gamma = 2.0 * math.asin((math.sqrt(3.0) * R / 2.0) / rho)
    rotor_area = 3.0 * math.sqrt(3.0) * R * R / 4.0 + 1.5 * rho * rho * (gamma - math.sin(gamma))
    free_cm3 = (math.pi * (R * R + 3.0 * e * e) - rotor_area) * B / 1000.0
    vs_cm3 = Q2.VS_TARGET_M3 * 1e6
    vmin = (free_cm3 - 1.5 * vs_cm3) / 3.0
    return vmin, (vmin + vs_cm3) / vmin


def lhs(n: int, seed: int, bounds: np.ndarray = BOUNDS) -> np.ndarray:
    return qmc.scale(qmc.LatinHypercube(bounds.shape[0], seed=seed).random(n), bounds[:, 0], bounds[:, 1])


def ode_case(x: np.ndarray, step: float = 3.0) -> dict[str, float]:
    d, overlap, ign, eoi, lam, eta_scale, friction_mult = map(float, x)
    vmin, cr = geometry(d)
    pars = Q2.expand_free_coefficients([BASE_ETA_COMB * eta_scale, BASE_FRICTION * friction_mult])
    out = Q2.simulate(6000.0, Q2.VS_TARGET_M3, cr, pars, overlap_deg=overlap,
                      lambda_air=lam, ignition_btdc_deg=ign, eoi_deg=eoi,
                      step_deg=step, max_cycles=30, collect_extrema=True)
    return {"Vmin_cm3": vmin, "CR": cr, **{k: float(out[k]) for k in
            ("power_kW", "eta_b", "BSFC_g_kWh", "pmax_MPa", "Tmax_K",
             "state_relative_residual")}, "converged": bool(out["converged"])}


def proxy_metrics(x: np.ndarray, pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Transparent conditional proxies; lower values are preferable."""
    d, overlap, ign, eoi, lam = (x[:, i] for i in range(5))
    power, eta, pmax, tmax = pred.T
    # HC/CO/NOx tendency proxy: overlap short-circuiting, rich mixture and high T.
    short = np.maximum(0.0, (overlap - 20.0) / 150.0)
    emission = (0.30 * short + 0.35 * np.maximum(0.0, 1.0 - lam) / 0.05
                + 0.20 * ((tmax - 2200.0) / 800.0) ** 2
                + 0.15 * np.maximum(0.0, 595.0 - eoi) / 25.0)
    _, cr = np.vectorize(geometry, otypes=[float, float])(d)
    reliability = (0.60 * (pmax / 8.0) ** 2 + 0.25 * (cr / 14.0) ** 2
                   + 0.15 * ((overlap - 95.0) / 100.0) ** 2)
    return emission, reliability


def nondominated(objectives: np.ndarray) -> np.ndarray:
    order = np.argsort(objectives[:, 0])
    front: list[int] = []
    for i in order:
        if front:
            f = objectives[np.asarray(front)]
            if np.any(np.all(f <= objectives[i], axis=1) & np.any(f < objectives[i], axis=1)):
                continue
            keep = ~(np.all(objectives[i] <= f, axis=1) & np.any(objectives[i] < f, axis=1))
            front = list(np.asarray(front)[keep])
        front.append(int(i))
    return np.asarray(front, dtype=int)


def desirability(values: np.ndarray, lo: float, hi: float, maximize: bool) -> np.ndarray:
    z = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
    return z if maximize else 1.0 - z


def evaluate_search(model: ExtraTreesRegressor, n: int, seed: int,
                    weights=(0.40, 0.25, 0.20, 0.15)):
    nominal = lhs(n, seed, BOUNDS[:5])
    base = np.column_stack([nominal, np.ones(n), np.ones(n)])
    # Each scenario changes genuine model inputs, not only the final score.
    scenarios = [(1.00, 1.00, 0.0), (0.96, 1.10, 5.0),
                 (1.04, 0.90, -5.0), (0.98, 1.05, -5.0), (1.02, 0.95, 5.0)]
    scores, predictions = [], []
    for eta_s, fric_s, ov_delta in scenarios:
        xs = base.copy()
        xs[:, 1] = np.clip(xs[:, 1] + ov_delta, BOUNDS[1, 0], BOUNDS[1, 1])
        xs[:, 5], xs[:, 6] = eta_s, fric_s
        pred = model.predict(xs)
        em, risk = proxy_metrics(xs, pred)
        power, eta = pred[:, 0], pred[:, 1]
        score = (weights[0] * desirability(power, 35.0, 50.0, True)
                 + weights[1] * desirability(eta, 0.30, 0.36, True)
                 + weights[2] * desirability(em, 0.0, 1.5, False)
                 + weights[3] * desirability(risk, 0.35, 1.25, False))
        scores.append(score); predictions.append((pred, em, risk))
    robust = np.min(np.column_stack(scores), axis=1)
    pred0, em0, risk0 = predictions[0]
    vmins_cr = np.array([geometry(v) for v in nominal[:, 0]])
    feasible = ((vmins_cr[:, 0] > 0.0) & (nominal[:, 0] < 150.0)
                & (vmins_cr[:, 1] >= 5.0) & (vmins_cr[:, 1] <= 18.0)
                & (pred0[:, 2] <= 8.0) & (pred0[:, 0] > 0.0)
                & (pred0[:, 1] >= 0.22) & (pred0[:, 1] <= 0.40))
    idx = np.flatnonzero(feasible)
    objectives = np.column_stack([-pred0[idx, 0], -pred0[idx, 1], em0[idx], risk0[idx]])
    front_local = nondominated(objectives)
    front = idx[front_local]
    best = idx[np.argmax(robust[idx])]
    return nominal, pred0, em0, risk0, robust, feasible, front, best


def ode_rescore(nominal: np.ndarray, candidate_indices: np.ndarray,
                weights=(0.40, 0.25, 0.20, 0.15)) -> tuple[list[dict], int]:
    scenarios = [(1.00, 1.00, 0.0), (0.96, 1.10, 5.0),
                 (1.04, 0.90, -5.0), (0.98, 1.05, -5.0), (1.02, 0.95, 5.0)]
    records = []
    for idx in candidate_indices:
        scores, nominal_result = [], None
        for scenario_id, (eta_s, fric_s, ov_delta) in enumerate(scenarios):
            x = np.r_[nominal[idx], eta_s, fric_s]
            x[1] = np.clip(x[1] + ov_delta, BOUNDS[1, 0], BOUNDS[1, 1])
            result = ode_case(x, step=3.0)
            pred = np.array([[result["power_kW"], result["eta_b"], result["pmax_MPa"], result["Tmax_K"]]])
            em, risk = proxy_metrics(x[None, :], pred)
            score = (weights[0] * desirability(pred[:, 0], 35.0, 50.0, True)
                     + weights[1] * desirability(pred[:, 1], 0.30, 0.36, True)
                     + weights[2] * desirability(em, 0.0, 1.5, False)
                     + weights[3] * desirability(risk, 0.35, 1.25, False))[0]
            scores.append(float(score))
            if scenario_id == 0:
                nominal_result = {**result, "emission_proxy": float(em[0]), "reliability_proxy": float(risk[0])}
        records.append({"candidate_index": int(idx), "robust_score_ode_3deg": min(scores),
                        "worst_scenario": int(np.argmin(scores)), **dict(zip(NAMES[:5], nominal[idx])),
                        **{f"nominal_{k}": v for k, v in nominal_result.items()}})
    best_local = int(np.argmax([r["robust_score_ode_3deg"] for r in records]))
    return records, best_local


def write_rows(path: Path, fieldnames: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames); w.writeheader(); w.writerows(rows)


def main() -> None:
    x = lhs(TRAIN_N, SEED)
    train_path = ROOT / "q3_ode_design.csv"
    rows, y = [], []
    if train_path.exists():
        with train_path.open(encoding="utf-8") as f:
            cached = list(csv.DictReader(f))
        if len(cached) == TRAIN_N:
            rows = cached
            x = np.array([[float(row[n]) for n in NAMES] for row in rows])
            y = [[float(row[k]) for k in ("power_kW", "eta_b", "pmax_MPa", "Tmax_K")] for row in rows]
    if not rows:
        for i, xi in enumerate(x):
            result = ode_case(xi)
            rows.append({"sample": i, **dict(zip(NAMES, xi)), **result})
            y.append([result[k] for k in ("power_kW", "eta_b", "pmax_MPa", "Tmax_K")])
    y = np.asarray(y)
    train_i, test_i = train_test_split(np.arange(TRAIN_N), test_size=0.20, random_state=SEED)
    model = ExtraTreesRegressor(n_estimators=800, min_samples_leaf=1, max_features=1.0,
                                random_state=SEED, n_jobs=-1).fit(x[train_i], y[train_i])
    test_pred = model.predict(x[test_i])
    metrics = {name: {"R2": float(r2_score(y[test_i, j], test_pred[:, j])),
                      "MAE": float(mean_absolute_error(y[test_i, j], test_pred[:, j]))}
               for j, name in enumerate(("power_kW", "eta_b", "pmax_MPa", "Tmax_K"))}
    model.fit(x, y)
    nominal, pred, em, risk, robust, feasible, front, best = evaluate_search(model, SEARCH_N, SEED + 1)
    # The emulator only screens candidates.  Formal selection is by five-scenario
    # ODE re-evaluation of the 40 highest emulator-robust candidates.
    top = np.flatnonzero(feasible)[np.argsort(-robust[feasible])[:40]]
    screen_cache = ROOT / "q3_ode_rescore.csv"
    if screen_cache.exists():
        with screen_cache.open(encoding="utf-8") as f:
            ode_screen = list(csv.DictReader(f))
        for record in ode_screen:
            for key in ("candidate_index", "worst_scenario"):
                record[key] = int(record[key])
            for key, value in list(record.items()):
                if key not in ("candidate_index", "worst_scenario", "nominal_converged"):
                    record[key] = float(value)
        best_local = int(np.argmax([r["robust_score_ode_3deg"] for r in ode_screen]))
    else:
        ode_screen, best_local = ode_rescore(nominal, top)
    best = int(ode_screen[best_local]["candidate_index"])
    ode_best = ode_case(np.r_[nominal[best], 1.0, 1.0], step=1.0)
    # Search stability under seeds, sample sizes and plausible preference weights.
    sensitivity = []
    configs = [(20000, SEED+2, (0.40,0.25,0.20,0.15)),
               (50000, SEED+3, (0.40,0.25,0.20,0.15)),
               (80000, SEED+4, (0.40,0.25,0.20,0.15)),
               (50000, SEED+5, (0.30,0.30,0.25,0.15)),
               (50000, SEED+6, (0.50,0.20,0.15,0.15))]
    for n, seed, weights in configs:
        a,b,c,d,e,f,g,h = evaluate_search(model,n,seed,weights)
        sensitivity.append({"sample_size":n,"seed":seed,"weights":str(weights),
                            **dict(zip(NAMES[:5],a[h])),"robust_score":float(e[h]),
                            "power_kW":float(b[h,0]),"eta_b":float(b[h,1])})
    pareto_path, sens_path, screen_path = ROOT/"q3_pareto.csv", ROOT/"q3_sensitivity.csv", ROOT/"q3_ode_rescore.csv"
    write_rows(train_path, list(rows[0]), rows)
    prows=[]
    for i in front:
        prows.append({**dict(zip(NAMES[:5],nominal[i])),"power_kW":pred[i,0],"eta_b":pred[i,1],
                      "BSFC_g_kWh":3.6e9/(pred[i,1]*Q2.LHV),"pmax_MPa":pred[i,2],"Tmax_K":pred[i,3],
                      "emission_proxy":em[i],"reliability_proxy":risk[i],"robust_score":robust[i],
                      "recommended":int(i==best)})
    write_rows(pareto_path,list(prows[0]),prows); write_rows(sens_path,list(sensitivity[0]),sensitivity); write_rows(screen_path,list(ode_screen[0]),ode_screen)
    fig,ax=plt.subplots(figsize=(7.4,4.6),constrained_layout=True)
    fi=np.flatnonzero(feasible); sc=ax.scatter(3.6e9/(pred[fi,1]*Q2.LHV),pred[fi,0],c=em[fi],s=5,alpha=.18,cmap="viridis")
    shown_front = front[np.linspace(0, len(front)-1, min(1500, len(front)), dtype=int)]
    ax.scatter(3.6e9/(pred[shown_front,1]*Q2.LHV),pred[shown_front,0],s=7,alpha=.28,c="#c0392b",label="surrogate non-dominated sample")
    ax.scatter(ode_best["BSFC_g_kWh"],ode_best["power_kW"],s=90,c="black",marker="*",label="ODE-rescored recommendation")
    ax.set(xlabel="BSFC (g/(kW h))",ylabel="Brake power (kW)"); ax.grid(alpha=.25); ax.legend(frameon=False); fig.colorbar(sc,ax=ax,label="emission proxy")
    fig.savefig(FIG/"q3-conditional-pareto.png",dpi=220); fig.savefig(PAPER_FIG/"q3-conditional-pareto.png",dpi=220); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(8.6,3.8),constrained_layout=True)
    axs[0].bar(metrics.keys(),[metrics[k]["R2"] for k in metrics]); axs[0].set_ylabel("Held-out R2"); axs[0].tick_params(axis="x",rotation=25); axs[0].grid(axis="y",alpha=.25)
    vals=np.array([[r[n] for n in NAMES[:5]] for r in sensitivity]); span=BOUNDS[:5,1]-BOUNDS[:5,0]
    axs[1].boxplot([(vals[:,j]-BOUNDS[j,0])/span[j] for j in range(5)],tick_labels=["d","overlap","ign","EOI","lambda"]); axs[1].set_ylabel("Normalized recommendation"); axs[1].grid(axis="y",alpha=.25)
    fig.savefig(FIG/"q3-validation-sensitivity.png",dpi=220); fig.savefig(PAPER_FIG/"q3-validation-sensitivity.png",dpi=220); plt.close(fig)
    outputs=[train_path,pareto_path,sens_path,screen_path,FIG/"q3-conditional-pareto.png",FIG/"q3-validation-sensitivity.png",PAPER_FIG/"q3-conditional-pareto.png",PAPER_FIG/"q3-validation-sensitivity.png"]
    metadata={"status":"generated_conditional_model","seed":SEED,"training_samples":TRAIN_N,"search_samples":SEARCH_N,
              "bounds":dict(zip(NAMES,BOUNDS.tolist())),"emulator":"ExtraTreesRegressor","held_out_metrics":metrics,
              "feasible_count":int(feasible.sum()),"pareto_count":int(len(front)),"recommended_inputs":dict(zip(NAMES[:5],nominal[best].tolist())),
              "recommended_emulator":{"power_kW":float(pred[best,0]),"eta_b":float(pred[best,1]),"pmax_MPa":float(pred[best,2]),"Tmax_K":float(pred[best,3]),"emission_proxy":float(em[best]),"reliability_proxy":float(risk[best]),"robust_score":float(robust[best])},
              "recommended_ode_recheck":ode_best,"ode_rescore":{"candidate_count":len(ode_screen),"scenario_count":5,"formal_selection":"maximum worst-scenario score from 3-degree ODE rescore; selected point rechecked at 1 degree","selected_record":ode_screen[best_local]},"interpretation":"conditional design recommendation; not target-engine bench optimum",
              "scenario_definition":"actual ODE inputs: combustion efficiency +/-4%, FMEP multiplier +/-10%, overlap implementation +/-5 deg",
              "versions":{"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__},
              "q2_script_sha256":sha256(ROOT/"q2_closed_loop.py")}
    meta_path=ROOT/"q3_run_metadata.json"; meta_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    metadata["outputs"]=[{"path":str(p.relative_to(ROOT.parent)),"sha256":sha256(p)} for p in outputs]
    meta_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:metadata[k] for k in ("held_out_metrics","feasible_count","pareto_count","recommended_inputs","recommended_emulator","recommended_ode_recheck")},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
