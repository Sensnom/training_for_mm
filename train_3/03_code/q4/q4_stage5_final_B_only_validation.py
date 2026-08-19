import csv, json, time
from pathlib import Path
import numpy as np
from q4_strict_periodic_mc import summarize, unit_tests, C_B, V_B_UM3
from q4_stage3_improved_global_search import p_self, p_necessary_upper

OUT=Path(__file__).resolve().parent
M=1_000_000
SEEDS=[2026081801,2026081807,2026081819]

def main():
    tests=unit_tests(seed=20260818)
    if not all(t['pass'] for t in tests): raise RuntimeError('B kernel unit tests failed')
    rows=[]
    for seed in SEEDS:
        for nb,label in [(57,'global_optimum'),(56,'strongest_cheaper_competitor')]:
            t0=time.time(); r=summarize(0,nb,M,np.uint64(seed),0); r['elapsed_s']=time.time()-t0
            r['label']=label; r['analytic_p_self']=p_self(0,nb); r['analytic_total_upper']=p_necessary_upper(0,nb)
            rows.append(r); print(label,seed,r['p_hat'],r['wilson_low'],r['wilson_high'],r['p_network_only_hat'])
    opt=[r for r in rows if r['N_B']==57]; comp=[r for r in rows if r['N_B']==56]
    assert all(r['wilson_low']>=0.90 for r in opt)
    assert all(r['wilson_high']<0.90 for r in comp)
    with open(OUT/'stage5_final_B_only_M1000000.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary={
        'M_per_run':M,'seeds':SEEDS,
        'best':{'N_A':0,'N_B':57,'cost_yuan':57*C_B,'B_volume_fraction_percent':57*V_B_UM3/1000*100,
                'analytic_p_self':p_self(0,57),'mean_p_hat':sum(r['p_hat'] for r in opt)/len(opt),
                'all_wilson_low_ge_0p90':all(r['wilson_low']>=0.9 for r in opt)},
        'competitor':{'N_A':0,'N_B':56,'cost_yuan':56*C_B,'analytic_total_upper':p_necessary_upper(0,56),
                      'mean_p_hat':sum(r['p_hat'] for r in comp)/len(comp),
                      'all_wilson_high_lt_0p90':all(r['wilson_high']<0.9 for r in comp)},
        'rows':rows,'verdict':'LOCK_Q4_GLOBAL_OPTIMUM_(0,57)'
    }
    (OUT/'stage5_final_lock_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 第4问 阶段5：最终 B-only 全图独立验证与锁定','',f'- 每次样本量：M={M:,}',f'- 三个全新随机种子：{SEEDS}',
        '- 最优方案与最强更便宜竞争者均为纯 B，因此本阶段完全不受 A 胶囊近似影响。','',
        '|方案|seed|p_hat|Wilson 95% CI|network-only|', '|---|---:|---:|---|---:|']
    for r in rows:
        md.append(f"|({r['N_A']},{r['N_B']})|{r['seed']}|{r['p_hat']:.9f}|[{r['wilson_low']:.9f},{r['wilson_high']:.9f}]|{r['p_network_only_hat']:.9f}|")
    md += ['',f"- (0,57) 三次 p_hat 均值：{sum(r['p_hat'] for r in opt)/len(opt):.9f}；三次 Wilson 下端点均 > 0.90。",
           f"- (0,56) 三次 p_hat 均值：{sum(r['p_hat'] for r in comp)/len(comp):.9f}；三次 Wilson 上端点均 < 0.90。",
           '', '**最终锁定：N_A*=0，N_B*=57，C_min=%.12f 元，Phi_B=%.12f%%。**' % (57*C_B,57*V_B_UM3/1000*100)]
    (OUT/'stage5_final_B_only_report.md').write_text('\n'.join(md),encoding='utf-8')

if __name__=='__main__': main()
