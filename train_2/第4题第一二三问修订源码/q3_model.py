"""Question 3 optimization calibrated by the public AIE 225CS bench curve.

The Turner-Pearson-Bassett 5000--7500 r/min torque points are digitized from
SAE 2018-01-1452.  They calibrate the BMEP level and speed trend.  The target
engine's unmeasured design-space response is still represented by an explicit
physics-informed surface, with +/-15% transfer uncertainty.
"""
from pathlib import Path
import csv
import math
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figure"
FIG.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "q3_results.csv"

# Q1 geometry and public bench calibration.
R, e, B = 105.0, 15.0, 50.0
VS = 409.1970032881473e-6
CR0 = 11.063792444592519
RPM = 6000.0
RPM_SRC = np.array([5000, 5167, 5333, 5500, 5667, 5833, 6000, 6167,
                    6333, 6500, 6667, 6833, 7000, 7167, 7333, 7500], float)
TORQUE_LBFT = np.array([22.5, 24.2, 26.6, 28.1, 27.6, 28.7, 29.0, 29.1,
                        29.3, 29.6, 29.8, 30.0, 30.5, 30.4, 30.7, 30.9])
LBFT_TO_NM = 1.3558179483
VS_SRC = 225e-6
TORQUE_SRC_NM = np.interp(RPM, RPM_SRC, TORQUE_LBFT) * LBFT_TO_NM
BMEP_SRC_PA = 2.0 * math.pi * TORQUE_SRC_NM / VS_SRC
# Transfer the calibrated BMEP to the problem geometry. This reproduces Q2.
P0 = BMEP_SRC_PA * VS * RPM / 60.0 / 1000.0  # kW
ETA0 = 0.309118
LHV = 43.5e6       # J/kg

def rotor_area(d):
    r = d / 2.0
    s = r - R / 2.0
    rho = ((math.sqrt(3)*R/2)**2 + s*s) / (2*s)
    gamma = 2*math.asin((math.sqrt(3)*R/2)/rho)
    return 3*math.sqrt(3)*R*R/4 + 1.5*rho*rho*(gamma-math.sin(gamma))

def geometry(d):
    Ah = math.pi*(R*R + 3*e*e)
    Ar = rotor_area(d)
    vfree = (Ah-Ar)*B/1000.0
    vmin = (vfree-1.5*(VS*1e6))/3.0
    vmax = vmin + VS*1e6
    return vmin, vmax, vmax/vmin

rng = np.random.default_rng(20260813)
N = 70000
d = rng.uniform(132.3, 159.0, N)
alpha = rng.uniform(20.0, 60.0, N)       # deg; maps to xi through a prior
ign = rng.uniform(10.0, 30.0, N)         # deg BTDC
eoi = rng.uniform(570.0, 620.0, N)       # eccentric-shaft deg, post-firing TDC prior
lam = rng.uniform(0.95, 1.15, N)

vmin = np.empty(N); vmax = np.empty(N); cr = np.empty(N)
for i, di in enumerate(d):
    vmin[i], vmax[i], cr[i] = geometry(float(di))

# Dimensionless overlap throughput.  alpha -> xi requires port area curves;
# the linear map is explicitly a design prior around alpha=44 deg, xi=0.20.
xi = 0.20 * alpha / 44.0
residual_reduction = 1.0 - np.exp(-xi)
short_loss = xi - (1.0 - np.exp(-xi))       # reference-mass fraction

# Bounded, smooth response factors.  They are deliberately small around Q2,
# preventing an uncalibrated response surface from creating artificial gains.
f_geom_p = 1.0 + 0.030*np.tanh((cr-CR0)/4.0)
f_ov_p = 1.0 + 0.045*(residual_reduction-(1-np.exp(-0.20))) - 0.75*(short_loss-(0.20-(1-np.exp(-0.20))))
f_ign_p = 1.0 - 0.035*((ign-18.0)/10.0)**2
f_eoi_p = 1.0 - 0.025*((eoi-597.0)/25.0)**2
f_lam_p = 1.0 - 0.70*(lam-1.00)**2 - 0.10*(lam-1.00)
power = P0*f_geom_p*f_ov_p*f_ign_p*f_eoi_p*f_lam_p

f_geom_eta = 1.0 + 0.045*np.tanh((cr-CR0)/4.0)
f_ov_eta = 1.0 + 0.10*(residual_reduction-(1-np.exp(-0.20))) - 0.95*short_loss
f_ign_eta = 1.0 - 0.045*((ign-18.0)/10.0)**2
f_eoi_eta = 1.0 - 0.030*((eoi-597.0)/25.0)**2
f_lam_eta = 1.0 - 0.55*(lam-1.02)**2 - 0.14*(lam-1.02)
eta = np.clip(ETA0*f_geom_eta*f_ov_eta*f_ign_eta*f_eoi_eta*f_lam_eta, 0.22, 0.36)
bsfc = 3.6e9/(eta*LHV)

# Emission index proxy (dimensionless, lower is better).  It combines the
# measurable mechanisms that are available without an emissions bench.
hc = 1.8*short_loss*(1.0 + 0.55*np.maximum(0, 597-eoi)/30.0)
co = 0.75*np.maximum(0, 1.0-lam)/0.05 + 0.10*((lam-1.0)/0.10)**2
temp_proxy = (cr/CR0)**0.25 * (1.0 + 0.018*(18.0-ign)) * (1.0-0.30*np.maximum(0, lam-1.0))
nox = 0.55*np.clip(temp_proxy-1.0, -0.5, 1.0)**2 + 0.12*temp_proxy
emission = hc + co + nox

# Reliability risk proxy: normalized peak-pressure and apex-seal/friction loads.
# The 8 MPa gate is a preliminary engineering screening limit, not a measured
# property of the target engine.
p_peak_proxy = 6.8*(cr/CR0)**0.55*(1.0+0.012*(18.0-ign))*(1.0+0.18*np.maximum(0, 1.0-lam)/0.05)
seal_load = (cr/CR0)**0.70*(1.0+0.12*(alpha-44.0)/20.0)
friction = 1.0 + 0.30*((cr/CR0)-1.0)**2 + 0.12*((alpha-44.0)/20.0)**2
risk = 0.55*(p_peak_proxy/8.0)**2 + 0.30*seal_load**2 + 0.15*(friction/1.2)**2
feasible = (vmin > 0) & (cr >= 5.0) & (cr <= 18.0) & (p_peak_proxy <= 8.0) & (eta >= 0.22)

# Robustness: scenarios around the calibrated BMEP transfer (+/-15%) and
# overlap throughput (+/-15%).  The speed trend itself is observed in the
# public curve; the +/-15% term covers target-engine transfer differences.
scales = np.array([0.85, 1.00, 1.15])
scenario_power = np.stack([power*s for s in scales], axis=1)
scenario_eta = np.stack([eta*(1-0.04), eta, eta*(1-0.04)], axis=1)
scenario_em = np.stack([emission*1.15, emission, emission*1.15], axis=1)
scenario_risk = np.stack([risk*1.10, risk, risk*1.10], axis=1)
def desirability(z, lo, hi, maximize=True):
    q = (z-lo)/(hi-lo)
    return np.clip(q if maximize else 1-q, 0, 1)
score_s = (0.40*desirability(scenario_power, 35, 55, True)
           + 0.25*desirability(scenario_eta, .22, .34, True)
           + 0.20*desirability(scenario_em, 0, 1.8, False)
           + 0.15*desirability(scenario_risk, 0.5, 1.8, False))
robust_score = score_s.min(axis=1)

# Pareto front for (power up, BSFC/emission/risk down).
idx = np.flatnonzero(feasible)
order = idx[np.argsort(-power[idx])]
front = []
best_bsfc = float('inf'); best_em = float('inf'); best_risk = float('inf')
# Exact dominance check on a compact top set keeps runtime predictable.
for j in idx:
    dominated = np.any((power[idx] >= power[j]) & (bsfc[idx] <= bsfc[j]) &
                        (emission[idx] <= emission[j]) & (risk[idx] <= risk[j]) &
                        ((power[idx] > power[j]) | (bsfc[idx] < bsfc[j]) |
                         (emission[idx] < emission[j]) | (risk[idx] < risk[j])))
    if not dominated: front.append(j)
front = np.array(front, dtype=int)
best = idx[np.argmax(robust_score[idx])]

rows = []
for i in range(N):
    rows.append([d[i], alpha[i], ign[i], eoi[i], lam[i], vmin[i], cr[i], power[i], eta[i], bsfc[i], emission[i], p_peak_proxy[i], risk[i], robust_score[i], int(i in set(front)) if len(front)<5000 else 0, int(i==best), int(feasible[i])])
with OUT.open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['d_mm','overlap_deg','ign_btdc_deg','eoi_deg','lambda','Vmin_cm3','CR','power_kW','eta_b','BSFC_g_kWh','emission_proxy','p_peak_proxy_MPa','risk_proxy','robust_score','pareto','recommended','feasible']); w.writerows(rows)

# Pareto plot and robustness plot.
fig, ax = plt.subplots(figsize=(7.6,4.6), constrained_layout=True)
ax.scatter(bsfc[idx], power[idx], c=emission[idx], s=6, alpha=.18, cmap='viridis', label='feasible samples')
ax.scatter(bsfc[front], power[front], c='#c0392b', s=14, label='Pareto front')
ax.scatter([bsfc[best]], [power[best]], c='#111111', s=58, marker='*', label='robust recommendation', zorder=4)
ax.set(xlabel='BSFC (g/(kW h))', ylabel='Brake power at 6000 r/min (kW)')
ax.grid(alpha=.25); ax.legend(frameon=False, fontsize=8)
fig.savefig(FIG/'q3_pareto.png', dpi=220, bbox_inches='tight'); plt.close(fig)

fig, ax = plt.subplots(figsize=(7.6,4.2), constrained_layout=True)
order = np.argsort(-robust_score[idx])[:200]
sel = idx[order]
ax.plot(np.arange(len(sel)), robust_score[sel], color='#21618c', lw=1.6)
ax.axhline(robust_score[best], color='#c0392b', ls='--', lw=1)
ax.set(xlabel='Top feasible candidates (sorted)', ylabel='Maximin robust score', ylim=(0,1.02))
ax.grid(alpha=.25)
fig.savefig(FIG/'q3_robustness.png', dpi=220, bbox_inches='tight'); plt.close(fig)

print('bench_calibration', {'source_torque_6000_Nm': float(TORQUE_SRC_NM),
                            'source_BMEP_6000_bar': float(BMEP_SRC_PA/1e5),
                            'target_base_power_6000_kW': float(P0)})
print('feasible', int(feasible.sum()), 'pareto', len(front))
print('recommended', {k: float(v) for k,v in zip(['d_mm','overlap_deg','ign_btdc_deg','eoi_deg','lambda','power_kW','eta_b','BSFC','emission','risk','robust_score'], [d[best],alpha[best],ign[best],eoi[best],lam[best],power[best],eta[best],bsfc[best],emission[best],risk[best],robust_score[best]])})
