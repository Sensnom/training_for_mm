import csv, json, math, time
from pathlib import Path
import numpy as np
from q4_strict_periodic_mc import summarize, C_A, C_B, V_B_UM3
from q4_stage3_improved_global_search import p_self, p_necessary_upper

OUT=Path(__file__).resolve().parent
M=500_000
SEEDS=[2026081801,2026081807,2026081819]
JOBS=[]
for s in SEEDS:
    JOBS.append((0,57,s,'global_optimum'))
    JOBS.append((0,56,s,'strongest_cheaper_competitor'))
JOBS.append((8,0,2026081829,'pure_A_reference'))

def main():
    rows=[]
    for na,nb,seed,label in JOBS:
        t0=time.time()
        r=summarize(na,nb,M,np.uint64(seed),0)
        r['label']=label
        r['analytic_p_self']=p_self(na,nb)
        r['analytic_total_upper']=p_necessary_upper(na,nb)
        r['elapsed_s']=time.time()-t0
        rows.append(r)
        print(label, seed, r['p_hat'], r['wilson_low'], r['wilson_high'], r['p_network_only_hat'])

    opt=[r for r in rows if r['label']=='global_optimum']
    comp=[r for r in rows if r['label']=='strongest_cheaper_competitor']
    pureA=[r for r in rows if r['label']=='pure_A_reference']
    assert all(r['wilson_low']>=0.90 for r in opt)
    assert all(r['wilson_high']<0.90 for r in comp)
    assert pureA[0]['wilson_low']>=0.90

    with open(OUT/'stage5_final_independent_validation.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    opt_mean=sum(r['p_hat'] for r in opt)/len(opt)
    comp_mean=sum(r['p_hat'] for r in comp)/len(comp)
    summary={
        'M_per_run':M,
        'seeds':SEEDS,
        'global_optimum':{
            'N_A':0,'N_B':57,'cost_yuan':57*C_B,
            'B_volume_fraction_percent':57*V_B_UM3/1000*100,
            'analytic_direct_X_probability':p_self(0,57),
            'MC_mean_p_hat_over_3_fresh_seeds':opt_mean,
            'all_three_wilson_low_ge_0p90':all(r['wilson_low']>=0.90 for r in opt),
        },
        'strongest_cheaper_competitor':{
            'N_A':0,'N_B':56,'cost_yuan':56*C_B,
            'analytic_total_upper':p_necessary_upper(0,56),
            'MC_mean_p_hat_over_3_fresh_seeds':comp_mean,
            'all_three_wilson_high_lt_0p90':all(r['wilson_high']<0.90 for r in comp),
        },
        'pure_A_reference':pureA[0],
        'final_verdict':'LOCK_Q4_GLOBAL_OPTIMUM_(0,57)',
        'proof_role':'analytic feasibility + analytic exclusion of every cheaper integer point; MC is independent numerical validation only.'
    }
    (OUT/'stage5_final_lock_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

    md=['# 第4问 阶段5：最终独立验证与结果锁定','',
        f'- 每次独立验证样本量：M={M:,}',
        f'- 最优方案独立种子：{SEEDS}',
        f'- 解析可行概率下界 P(0,57) >= {p_self(0,57):.12f}',
        f'- 最小成本 C_min = {57*C_B:.12f} 元',
        f'- B 填充体积分数 = {57*V_B_UM3/1000*100:.12f}%','',
        '## 独立复核结果','',
        '|标签|方案|seed|p_hat|Wilson 95% CI|network-only|',
        '|---|---|---:|---:|---|---:|']
    for r in rows:
        md.append(f"|{r['label']}|({r['N_A']},{r['N_B']})|{r['seed']}|{r['p_hat']:.9f}|[{r['wilson_low']:.9f},{r['wilson_high']:.9f}]|{r['p_network_only_hat']:.9f}|")
    md += ['',
        f'- (0,57) 三个全新随机种子的 p_hat 均值：{opt_mean:.9f}；三次 Wilson 下端点均 > 0.90。',
        f'- (0,56) 三个全新随机种子的 p_hat 均值：{comp_mean:.9f}；三次 Wilson 上端点均 < 0.90。',
        '- 纯 A 参考方案 (8,0) 亦通过数值复核，但成本高于 57B。','',
        '## 最终锁定','',
        '**Q4 全局最优方案锁定为：N_A*=0，N_B*=57。**',
        '',
        '该结论的最优性由解析证明给出；Monte Carlo 仅承担独立数值验证。']
    (OUT/'stage5_final_validation_report.md').write_text('\n'.join(md),encoding='utf-8')

if __name__=='__main__':
    main()
