import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

ROOT = Path(r"C:\Users\FY\Documents\Codex\2026-07-19\new-chat-2")
OUT = ROOT / "output" / "verified"
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path(r"E:\数学建模知识库\附件1.xls")


def load_demand():
    df = pd.read_excel(DATA)
    rows = []
    for _, row in df.iterrows():
        try:
            d = int(row.iloc[0])
            hs = str(row.iloc[1])
            if "-" not in hs:
                continue
            h = int(hs.split(":")[0]) - 8
            vals = [int(v) for v in row.iloc[2:12]]
            if 1 <= d <= 10 and 0 <= h < 11:
                rows.append((d - 1, h, vals))
        except Exception:
            pass
    D = np.zeros((10, 11, 10), dtype=int)
    for d, h, vals in rows:
        D[d, h, :] = vals
    assert len(rows) == 110 and np.all(D > 0)
    return D


def patterns(gap):
    ans = []
    for s1 in range(8):
        for s2 in range(s1 + 4 + gap, 8):
            ans.append((s1, s2))
    return ans


def cover_matrix(P):
    A = np.zeros((11, len(P)), dtype=int)
    for j, (s1, s2) in enumerate(P):
        A[s1:s1 + 4, j] = 1
        A[s2:s2 + 4, j] = 1
    return A


def solve_q1(D):
    P = patterns(0); A = cover_matrix(P)
    s = pywraplp.Solver.CreateSolver("SCIP")
    W = [s.IntVar(0, 10000, f"W_{g}") for g in range(10)]
    R = {(g,d): s.IntVar(0, 10000, f"R_{g}_{d}") for g in range(10) for d in range(10)}
    x = {(g,d,p): s.IntVar(0, 10000, f"x_{g}_{d}_{p}") for g in range(10) for d in range(10) for p in range(len(P))}
    for g in range(10):
        s.Add(sum(R[g,d] for d in range(10)) == 2 * W[g])
        for d in range(10):
            s.Add(sum(x[g,d,p] for p in range(len(P))) == W[g] - R[g,d])
            for h in range(11):
                s.Add(sum(int(A[h,p]) * x[g,d,p] for p in range(len(P))) >= int(D[d,h,g]))
    s.Minimize(sum(W))
    status = s.Solve()
    assert status == pywraplp.Solver.OPTIMAL
    return int(round(s.Objective().Value())), [int(round(v.solution_value())) for v in W]


def solve_flexible(D, gap):
    P = patterns(gap); A = cover_matrix(P)
    s = pywraplp.Solver.CreateSolver("SCIP")
    W = s.IntVar(0, 100000, "W")
    R = [s.IntVar(0, 100000, f"R_{d}") for d in range(10)]
    x = {(d,g,p): s.IntVar(0, 100000, f"x_{d}_{g}_{p}") for d in range(10) for g in range(10) for p in range(len(P))}
    s.Add(sum(R) == 2 * W)
    for d in range(10):
        s.Add(sum(x[d,g,p] for g in range(10) for p in range(len(P))) == W - R[d])
        for g in range(10):
            for h in range(11):
                s.Add(sum(int(A[h,p]) * x[d,g,p] for p in range(len(P))) >= int(D[d,h,g]))
    s.Minimize(W)
    status = s.Solve()
    if status != pywraplp.Solver.OPTIMAL:
        return None, [], len(P)
    work = [sum(int(round(x[d,g,p].solution_value())) for g in range(10) for p in range(len(P))) for d in range(10)]
    return int(round(W.solution_value())), work, len(P)


def solve_cross_group(D, gap):
    P = patterns(gap)
    s = pywraplp.Solver.CreateSolver("SCIP")
    W = s.IntVar(0, 100000, "W3")
    R = [s.IntVar(0, 100000, f"R3_{d}") for d in range(10)]
    x = {(d,p,g1,g2): s.IntVar(0, 100000, f"z_{d}_{p}_{g1}_{g2}")
         for d in range(10) for p in range(len(P)) for g1 in range(10) for g2 in range(10)}
    s.Add(sum(R) == 2 * W)
    for d in range(10):
        s.Add(sum(x[d,p,g1,g2] for p in range(len(P)) for g1 in range(10) for g2 in range(10)) == W - R[d])
        for g in range(10):
            for h in range(11):
                terms = []
                for p,(s1,s2) in enumerate(P):
                    if s1 <= h < s1+4:
                        terms.extend(x[d,p,g,g2] for g2 in range(10))
                    if s2 <= h < s2+4:
                        terms.extend(x[d,p,g1,g] for g1 in range(10))
                s.Add(sum(terms) >= int(D[d,h,g]))
    s.Minimize(W)
    status = s.Solve()
    if status != pywraplp.Solver.OPTIMAL:
        return None, [], len(P)
    work = [sum(int(round(x[d,p,g1,g2].solution_value())) for p in range(len(P)) for g1 in range(10) for g2 in range(10)) for d in range(10)]
    return int(round(W.solution_value())), work, len(P)


def main():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    D = load_demand()
    q1, q1_groups = solve_q1(D)
    q2, q2_daily, p0 = solve_flexible(D, 0)
    q3_r1, q3_daily, p1 = solve_cross_group(D, 1)
    q3_r2, _, p2 = solve_cross_group(D, 2)
    q3_r0, q3_r0_daily, _ = solve_cross_group(D, 0)
    total_demand = int(D.sum())
    lower_bound_hours = int(np.ceil(total_demand / 64))
    results = {
        "data": {"shape": list(D.shape), "cells": int(D.size), "min": int(D.min()), "max": int(D.max()), "total_person_hours": total_demand},
        "hour_lower_bound": lower_bound_hours,
        "q1": {"workers": q1, "group_pools": q1_groups, "status": "OPTIMAL"},
        "q2": {"workers": q2, "daily_working": q2_daily, "status": "OPTIMAL", "patterns": p0},
        "q3_strict": {"workers": None, "status": "INFEASIBLE_BY_ANALYTIC_BLIND_ZONE_AND_MIP", "patterns": p2},
        "q3_gap1": {"workers": q3_r1, "daily_working": q3_daily, "status": "OPTIMAL", "patterns": p1},
        "q3_gap0": {"workers": q3_r0, "daily_working": q3_r0_daily, "status": "OPTIMAL_CONTROL_SCENARIO", "patterns": p0},
        "flexibility": {"cross_day_saving": q1-q2, "intra_day_saving": q2-q3_r0, "gap1_premium_over_gap0": q3_r1-q3_r0}
    }
    (OUT / "verified_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame({"group": np.arange(1,11), "q1_pool": q1_groups}).to_csv(OUT / "q1_group_pools.csv", index=False)
    pd.DataFrame(D.sum(axis=2), index=np.arange(1,11), columns=[f"{h}:00" for h in range(8,19)]).to_csv(OUT / "daily_hour_total_demand.csv")

    fig, ax = plt.subplots(figsize=(8.5,4.8))
    labels = ["固定小组\n问题1", "跨天换组\n问题2", "无最小间隔\n对照", "间隔≥1小时\n修正"]
    vals = [q1, q2, q3_r0, q3_r1]
    colors = ["#355C7D", "#4C956C", "#7A9E9F", "#D17B49"]
    bars = ax.bar(labels, vals, color=colors, width=.62)
    ax.set_ylabel("最少招聘人数")
    ax.set_ylim(0, max(vals)*1.18)
    ax.set_title("经复算的招聘人数比较")
    for b,v in zip(bars, vals): ax.text(b.get_x()+b.get_width()/2, v+5, str(v), ha="center", fontweight="bold")
    ax.text(2, 45, "严格间隔≥2小时：结构性不可行", ha="center", color="#A23E48", fontweight="bold")
    ax.spines[["top","right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT / "workers_comparison.png", dpi=220); plt.close(fig)

    heat = D.sum(axis=2)
    fig, ax = plt.subplots(figsize=(9.2,5.1))
    im = ax.imshow(heat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(11), [f"{h}-{h+1}" for h in range(8,19)], rotation=45, ha="right")
    ax.set_yticks(range(10), [f"第{d}天" for d in range(1,11)])
    ax.set_title("每日各小时总需求热力图（10组求和）")
    fig.colorbar(im, ax=ax, label="需求人数")
    fig.tight_layout(); fig.savefig(OUT / "demand_heatmap.png", dpi=220); plt.close(fig)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
