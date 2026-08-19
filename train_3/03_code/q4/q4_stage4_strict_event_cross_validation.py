import csv, json, math
from pathlib import Path
import numpy as np
from q4_stage3_improved_global_search import p_self, p_necessary_upper

OUT=Path(__file__).resolve().parent
L=10000.0; H=L/2; DELTA=1.8; R_A=30.0; HALF_A=2500.0; R_B=200.0
M=1_000_000
SEED=314159265
CANDIDATES=[(0,57),(0,56),(1,48),(2,39),(3,30),(4,21),(5,12),(6,3)]

def wilson(k,n,z=1.96):
    ph=k/n; den=1+z*z/n
    cen=(ph+z*z/(2*n))/den
    rad=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/den
    return cen-rad,cen+rad

def run_candidate(na,nb,seed,M,chunk=100_000):
    rng=np.random.default_rng(seed + na*1009 + nb*9176)
    k_self=0; k_nec=0
    done=0
    while done<M:
        m=min(chunk,M-done)
        anyD=np.zeros(m,dtype=bool)
        anyL=np.zeros(m,dtype=bool)
        anyR=np.zeros(m,dtype=bool)
        if na:
            cx=rng.uniform(-H,H,size=(m,na))
            ux=rng.uniform(-1.0,1.0,size=(m,na))  # one Cartesian component of isotropic direction
            hx=HALF_A*np.abs(ux)+R_A*np.sqrt(np.maximum(0.0,1.0-ux*ux))
            cross=(cx-hx < -H) | (cx+hx > H)
            left=(~cross) & (cx-hx <= -H+DELTA)
            right=(~cross) & (cx+hx >= H-DELTA)
            anyD |= np.any(cross,axis=1); anyL |= np.any(left,axis=1); anyR |= np.any(right,axis=1)
        if nb:
            cx=rng.uniform(-H,H,size=(m,nb))
            hx=R_B
            cross=(cx-hx < -H) | (cx+hx > H)
            left=(~cross) & (cx-hx <= -H+DELTA)
            right=(~cross) & (cx+hx >= H-DELTA)
            anyD |= np.any(cross,axis=1); anyL |= np.any(left,axis=1); anyR |= np.any(right,axis=1)
        nec=anyD | ((~anyD) & anyL & anyR)
        k_self += int(anyD.sum()); k_nec += int(nec.sum()); done += m
    return k_self,k_nec

def main():
    rows=[]
    for na,nb in CANDIDATES:
        ks,kn=run_candidate(na,nb,SEED,M)
        ps=ks/M; pn=kn/M
        slo,shi=wilson(ks,M); nlo,nhi=wilson(kn,M)
        row={
            'N_A':na,'N_B':nb,'M':M,'seed_base':SEED,
            'p_self_mc':ps,'p_self_ci_low':slo,'p_self_ci_high':shi,'p_self_analytic':p_self(na,nb),
            'p_necessary_event_mc':pn,'p_necessary_ci_low':nlo,'p_necessary_ci_high':nhi,
            'p_necessary_analytic':p_necessary_upper(na,nb),
            'analytic_classification':'FEASIBLE_BY_LOWER_BOUND' if p_self(na,nb)>=0.9 else ('INFEASIBLE_BY_UPPER_BOUND' if p_necessary_upper(na,nb)<0.9 else 'UNRESOLVED')
        }
        rows.append(row)
        print(na,nb,ps,pn,row['p_self_analytic'],row['p_necessary_analytic'])

    # Numerical formula checks: analytic values should lie inside or extremely near the MC 95% intervals.
    # We only hard-require small absolute MC discrepancy and the analytic classification, because CI coverage is stochastic.
    assert all(abs(r['p_self_mc']-r['p_self_analytic'])<0.002 for r in rows)
    assert all(abs(r['p_necessary_event_mc']-r['p_necessary_analytic'])<0.002 for r in rows)
    assert rows[0]['p_self_analytic']>=0.90
    assert all(r['p_necessary_analytic']<0.90 for r in rows[1:])

    with open(OUT/'stage4_strict_event_M1000000.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary={'M':M,'seed_base':SEED,'rows':rows,'verdict':'STAGE4_PASS_STRICT_EVENT_FORMULAS_VALIDATED'}
    (OUT/'stage4_strict_event_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 第4问 阶段4：严格几何必要事件公式的 Monte Carlo 交叉验证','',
        f'- 每个方案样本量：M={M:,}',
        '- A 的 X 向半宽严格采用平端圆柱公式：h_x=(L_A/2)|u_x|+r_A sqrt(1-u_x^2)。',
        '- 本阶段不使用胶囊体 A 的全图近似；只验证阶段3解析下界/上界公式。','',
        '|方案|MC自短路|解析自短路|MC必要事件|解析必要事件|解析判定|',
        '|---|---:|---:|---:|---:|---|']
    for r in rows:
        md.append(f"|({r['N_A']},{r['N_B']})|{r['p_self_mc']:.9f}|{r['p_self_analytic']:.9f}|{r['p_necessary_event_mc']:.9f}|{r['p_necessary_analytic']:.9f}|{r['analytic_classification']}|")
    md += ['', '**阶段4结论：** 严格平端圆柱/球体的 Monte Carlo 结果与解析公式一致；(0,57) 由自短路解析下界证明可行，七个更便宜前沿点均由必要事件解析上界证明不可行。']
    (OUT/'stage4_strict_event_report.md').write_text('\n'.join(md),encoding='utf-8')

if __name__=='__main__': main()
