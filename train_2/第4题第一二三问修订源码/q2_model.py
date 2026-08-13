from pathlib import Path
import csv
import math
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "writer" / "figure"
FIG.mkdir(parents=True, exist_ok=True)

# Geometry from corrected Q1.
VS = 409.1970032881473e-6       # single-chamber swept volume, m^3
CR = 11.063792444592519
RPM = 6000.0
OMEGA = 2 * math.pi * RPM / 60

# AIE 225CS public test curve, read from Turner et al., SAE 2018-01-1452,
# Fig. 17. Values are digitized to plotting precision, not claimed as raw data.
RPM_SRC = np.array([5000, 5167, 5333, 5500, 5667, 5833, 6000, 6167,
                    6333, 6500, 6667, 6833, 7000, 7167, 7333, 7500], float)
TORQUE_LBFT = np.array([22.5, 24.2, 26.6, 28.1, 27.6, 28.7, 29.0, 29.1,
                        29.3, 29.6, 29.8, 30.0, 30.5, 30.4, 30.7, 30.9])
LBFT_TO_NM = 1.3558179483
VS_SRC = 225e-6

torque_src_nm_6000 = float(np.interp(RPM, RPM_SRC, TORQUE_LBFT)) * LBFT_TO_NM
bmep = 2 * math.pi * torque_src_nm_6000 / VS_SRC
torque_target = bmep * VS / (2 * math.pi)
power_target = torque_target * OMEGA

# Conservative transfer uncertainty: curve digitization and model discrepancy are
# small compared with the unobserved differences in ports, cooling and sealing.
bmep_low = 0.85 * bmep
bmep_high = 1.15 * bmep
power_low = bmep_low * VS * RPM / 60
power_high = bmep_high * VS * RPM / 60

# Energy closure at WOT. Volumetric efficiency is not supplied for the target;
# report a central estimate and a range rather than hiding this uncertainty.
rho_air = 1.184              # kg/m^3, 25 C, 1 atm
afr = 14.5                   # gasoline stoichiometric value used by the source
lhv = 43.5e6                 # J/kg, source paper
eta_v_center = 1.00
air_cycle = rho_air * eta_v_center * VS
fuel_cycle = air_cycle / afr
fuel_flow = fuel_cycle * RPM / 60
eta_b = (bmep * VS) / (fuel_cycle * lhv)
bsfc = 3.6e9 / (eta_b * lhv)
eta_b_low = bmep_low * afr / (rho_air * 1.10 * lhv)
eta_b_high = bmep_high * afr / (rho_air * 0.90 * lhv)

# Perfect-mixing overlap model. xi is overlap-throughput mass divided by the
# reference chamber mass. These relationships are exact under the stated model.
xi = np.linspace(0.001, 0.5, 500)
residual_remaining = np.exp(-xi)
short_circuit_fraction = 1 - (1 - np.exp(-xi)) / xi

def overlap_metrics(x):
    residual_reduction = 1 - math.exp(-x)
    short_fraction = 1 - (1 - math.exp(-x)) / x if x else 0.0
    return residual_reduction, short_fraction

xi0 = 0.20
xi_cases = [0.18, 0.20, 0.22]

# Efficiency response around the representative xi0. r0 and k_r are reported
# assumptions, not hidden fitted constants. k_r spans a moderate residual-gas
# penalty; pumping work is neglected only for the WOT, near-equal-pressure case.
r0 = 0.15
k_range = (0.3, 0.7)

def total_short_loss(x):
    return x - (1 - math.exp(-x)) if x else 0.0

def relative_efficiency(x, k_r, port_fuel_injection=True):
    combustion = 1 - k_r * r0 * math.exp(-x)
    combustion0 = 1 - k_r * r0 * math.exp(-xi0)
    fuel = 1 - total_short_loss(x) if port_fuel_injection else 1.0
    fuel0 = 1 - total_short_loss(xi0) if port_fuel_injection else 1.0
    return combustion / combustion0 * fuel / fuel0

# Figure 1: test-data calibration and displacement transfer.
fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.15), constrained_layout=True)
ax = axes[0]
ax.plot(RPM_SRC, TORQUE_LBFT * LBFT_TO_NM, "o-", color="#21618c", lw=1.7, ms=4,
        label="AIE 225CS test curve (digitized)")
ax.axvline(RPM, color="0.5", ls="--", lw=1)
ax.scatter([RPM], [torque_src_nm_6000], color="#b03a2e", zorder=4)
ax.annotate(f"{torque_src_nm_6000:.1f} N m\nBMEP={bmep/1e5:.2f} bar",
            (RPM, torque_src_nm_6000), xytext=(12, -34), textcoords="offset points")
ax.set(xlabel="Eccentric-shaft speed (r/min)", ylabel="Brake torque (N m)", xlim=(4900, 7600))
ax.grid(alpha=.25); ax.legend(frameon=False, fontsize=8)

ax = axes[1]
vals = [power_low/1000, power_target/1000, power_high/1000]
ax.bar(["lower", "central", "upper"], vals, color=["#8fb9cf", "#21618c", "#8fb9cf"])
for i, val in enumerate(vals): ax.text(i, val + .8, f"{val:.1f}", ha="center")
ax.axhline(7.05, color="#b03a2e", ls="--", lw=1.3, label="old draft: 7.05 kW")
ax.set(ylabel="Target-engine brake power at 6000 r/min (kW)", ylim=(0, 58))
ax.grid(axis="y", alpha=.22); ax.legend(frameon=False, fontsize=8)
fig.savefig(FIG / "q2_bench_calibration.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# Figure 2: overlap model independent of unknown port dimensions.
fig, ax = plt.subplots(figsize=(7.4, 4.25), constrained_layout=True)
ax.plot(xi, 100*(1-residual_remaining), lw=2.1, label="Residual-gas reduction")
ax.plot(xi, 100*short_circuit_fraction, lw=2.1, label="Short-circuit share of overlap inflow")
for x in xi_cases:
    rr, sc = overlap_metrics(x)
    ax.scatter([x, x], [100*rr, 100*sc], s=25)
ax.axvline(xi0, color="0.45", ls="--", lw=1)
ax.set(xlabel="Dimensionless overlap throughput, xi", ylabel="Mass fraction (%)", xlim=(0, .5), ylim=(0, 42))
ax.grid(alpha=.25); ax.legend(frameon=False)
fig.savefig(FIG / "q2_overlap_mixing.png", dpi=220, bbox_inches="tight")
plt.close(fig)

rows = [
    ("source_torque_6000_Nm", torque_src_nm_6000),
    ("calibrated_BMEP_bar", bmep/1e5),
    ("target_torque_6000_Nm", torque_target),
    ("target_power_6000_kW", power_target/1000),
    ("target_power_low_kW", power_low/1000),
    ("target_power_high_kW", power_high/1000),
    ("brake_thermal_efficiency_center_pct", eta_b*100),
    ("brake_thermal_efficiency_low_pct", eta_b_low*100),
    ("brake_thermal_efficiency_high_pct", eta_b_high*100),
    ("fuel_flow_center_kg_h", fuel_flow*3600),
    ("BSFC_center_g_kWh", bsfc),
]
for x in xi_cases:
    rr, sc = overlap_metrics(x)
    rows.extend([(f"xi_{x:.2f}_residual_reduction_pct", rr*100),
                 (f"xi_{x:.2f}_short_circuit_of_overlap_inflow_pct", sc*100),
                 (f"xi_{x:.2f}_total_short_loss_pct_refmass", total_short_loss(x)*100)])
    for k in k_range:
        rows.extend([
            (f"xi_{x:.2f}_PFI_eff_change_pct_k{k:.1f}", (relative_efficiency(x,k,True)-1)*100),
            (f"xi_{x:.2f}_post_exhaust_DI_eff_change_pct_k{k:.1f}", (relative_efficiency(x,k,False)-1)*100),
        ])

with (ROOT / "writer" / "q2_results.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["metric", "value"]); w.writerows(rows)

for k, v in rows: print(k, v)
