# Q4 verification record

- status: verified
- date: 2026-08-18
- formal optimum: `(N_A,N_B)=(0,57)`
- formal cost: `0.095504416669` yuan
- formal B volume fraction: `0.191008833338%`
- analytic feasibility certificate: `L_(0,57)=0.902397648016>0.90`
- exact cheaper-region proof: seven cost-dominating frontier points all have necessary-event upper bounds below `0.90`; exhaustive audit contains 216 strictly cheaper integer points, with maximum upper bound `U_(0,56)=0.898341781388`.
- checkpoint reproduction: copied `03_code/q4/q4_global_proof.py` to a temporary directory and re-executed it; reproduced incumbent and all seven frontier records exactly without modifying `03_code/`. Stdout is stored in `06_verification/q4_global_proof_checkpoint05_stdout.txt`.
- strict-event Monte Carlo: `04_results/q4/stage4_strict_event_M1000000.csv`, M=1,000,000 for incumbent plus seven frontier points; strict flat-ended-cylinder/sphere event estimates are consistent with analytic bounds.
- final full-graph B-only validation: `04_results/q4/stage5_final_B_only_M1000000.csv`, three new seeds, M=1,000,000 each. Every `(0,57)` Wilson lower endpoint is >0.90; every `(0,56)` Wilson upper endpoint is <0.90; network-only frequency is zero in all six threshold-near runs.
- delta sensitivity: for delta=0,0.9,1.8,3.6,5.4,9.0 nm, `(0,57)` direct lower bound remains `0.902397648016`; the strongest cheaper point remains `(0,56)` and its upper bound remains below 0.90 (maximum `0.898592567280`).
- scope limitation: A-direction distribution is a high-impact assumption. If the A orientation distribution changes, the mixed cheaper frontier must be recomputed; `(0,57)` is not claimed globally optimal across orientation models.
- approximation boundary: the production mixed-network A-A/A-B capsule approximation is irrelevant to the locked optimum proof; the exact proof is network-distance-independent and the final threshold-near full-graph validation is B-only.
