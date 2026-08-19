import math, csv, json
from pathlib import Path

L=10000.0
DELTA=1.8
R_A=30.0
LEN_A=5000.0
R_B=200.0
V_A=math.pi*(0.03**2)*5.0
V_B=4/3*math.pi*(0.2**3)
cA=1.05*V_A
cB=0.05*V_B
pA=LEN_A/(2*L)+math.pi*R_A/(2*L)
pB=2*R_B/L
pE=DELTA/L

def p_direct_any(a,b):
    return 1-(1-pA)**a*(1-pB)**b

def p_necessary_upper(a,b):
    # Necessary condition: at least one direct X-crossing particle D,
    # OR (at least one non-crossing left-electrode toucher AND one right toucher).
    q_noD_noL=(1-pA-pE)**a*(1-pB-pE)**b
    q_noD_noLR=(1-pA-2*pE)**a*(1-pB-2*pE)**b
    return 1 - 2*q_noD_noL + q_noD_noLR

Cstar=57*cB
rows=[]
for a in range(0,7):
    bmax=math.floor((Cstar-a*cA-1e-15)/cB)
    rows.append({
        'N_A':a,'N_B_max_cheaper':bmax,
        'cost_yuan':a*cA+bmax*cB,
        'p_direct_lower':p_direct_any(a,bmax),
        'p_conduction_upper':p_necessary_upper(a,bmax),
        'below_0p90':p_necessary_upper(a,bmax)<0.9,
    })

out=Path(__file__).resolve().parent
with open(out/'q4_analytic_frontier_proof.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
summary={
    'p_direct_A':pA,'p_direct_B':pB,'p_one_side_touch_non_cross_each_type':pE,
    'V_A_um3':V_A,'V_B_um3':V_B,'cost_A_each_yuan':cA,'cost_B_each_yuan':cB,
    'incumbent':{
        'N_A':0,'N_B':57,'cost_yuan':Cstar,
        'p_direct_lower':p_direct_any(0,57),
        'p_conduction_upper':p_necessary_upper(0,57),
        'B_volume_fraction_percent':57*V_B/1000*100,
    },
    'max_N_A_in_any_strictly_cheaper_solution':6,
    'frontier':rows,
    'verdict':'(0,57) is the exact global minimum-cost solution under Assumption A and the written boundary semantics, because it is feasible by the direct-X lower bound and every strictly cheaper integer solution is dominated by one of the seven frontier points whose necessary-event upper bound is <0.90.'
}
(out/'q4_analytic_global_proof.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

md=[]
md.append('# Q4 analytic global-optimality proof')
md.append('')
md.append(f'- p_A^D = {pA:.12f}')
md.append(f'- p_B^D = {pB:.12f}')
md.append(f'- p_E (one specified electrode, non-crossing shell) = {pE:.12f}')
md.append(f'- c_A = {cA:.12f} yuan/object')
md.append(f'- c_B = {cB:.12f} yuan/object')
md.append(f'- incumbent (0,57): cost = {Cstar:.12f} yuan, direct-X lower bound = {p_direct_any(0,57):.12f}')
md.append('')
md.append('|N_A|max N_B with cost < C(0,57)|cost/yuan|direct-X lower|necessary-event upper|')
md.append('|---:|---:|---:|---:|---:|')
for r in rows:
    md.append(f"|{r['N_A']}|{r['N_B_max_cheaper']}|{r['cost_yuan']:.9f}|{r['p_direct_lower']:.9f}|{r['p_conduction_upper']:.9f}|")
md.append('')
md.append('All seven necessary-event upper bounds are below 0.90. By monotonicity in N_B, all cheaper points beneath each frontier point are also infeasible. Since 7 A alone already costs more than 57 B, no other strictly cheaper integer point exists.')
(out/'q4_analytic_global_proof.md').write_text('\n'.join(md),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
