# Q3 verification record

- status: verified
- date: 2026-08-18
- formal result: `N_A*=8`, exact volume fraction `0.0113097336%`, reported `0.01%`
- formal proof: `U_7=0.8722778410<0.90`, `L_8=0.9048100243>0.90`
- independent MC sanity check source: File Library `q2_q3_independent_derivation.md`
  - n=7, M=100000: 0.872230, z=-0.045, analytic in Wilson 95% interval
  - n=7, M=500000: 0.871868, z=-0.868, analytic in Wilson 95% interval
  - n=8, M=100000: 0.905730, z=0.991, analytic in Wilson 95% interval
  - n=8, M=500000: 0.905210, z=0.964, analytic in Wilson 95% interval
- delta sensitivity: verified analytic evidence from `03_code/analysis/q7_sensitivity_analysis.py`; `N_A*=8` stable for delta=0,0.9,1.8,3.6,5.4,9.0 nm.
- direction sensitivity: high-impact assumption; x-aligned / isotropic / transverse direct-X probabilities are 0.5 / 0.254712389 / 0.006, with self-short 90% root counts 4 / 8 / 383.
- interpretation: Monte Carlo checks implementation only. The threshold gate is analytic, not sample-frequency based.
