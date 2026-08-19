import csv, json, math, time
from pathlib import Path
import numpy as np
from q4_strict_periodic_mc import summarize, unit_tests, C_A, C_B
from q4_stage3_improved_global_search import p_self, p_necessary_upper

OUT=Path(__file__).resolve().parent
SEED=np.uint64(314159265)
M=200_000
CANDIDATES=[(0,57),(0,56),(1,48),(2,39),(3,30),(4,21),(5,12),(6,3)]

def main():
    tests=unit_tests(seed=20260818)
    if not all(t['pass'] for t in tests):
        raise RuntimeError('Stage 4 blocked: unit tests failed')
    rows=[]
    for na,nb in CANDIDATES:
        t0=time.time()
        r=summarize(na,nb,M,SEED,0)
        r['analytic_p_self']=p_self(na,nb)
        r['analytic_total_upper']=p_necessary_upper(na,nb)
        r['lower_gap_to_0p90']=r['wilson_low']-0.90
        r['upper_gap_to_0p90']=r['wilson_high']-0.90
        r['elapsed_s']=time.time()-t0
        rows.append(r)
        print(na,nb,r['p_hat'],r['wilson_low'],r['wilson_high'],r['p_network_only_hat'])

    # Expected classification: incumbent feasible, all cheaper frontier points infeasible.
    assert rows[0]['wilson_low'] >= 0.90, rows[0]
    assert all(r['wilson_high'] < 0.90 for r in rows[1:]), [r for r in rows[1:] if r['wilson_high']>=0.90]

    with open(OUT/'stage4_frontier_M200000.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary={
        'M':M,'seed':int(SEED),'candidates':rows,
        'classification_check':{
            'best_0_57_wilson_low_ge_0p90':rows[0]['wilson_low']>=0.90,
            'all_7_cheaper_frontier_wilson_high_lt_0p90':all(r['wilson_high']<0.90 for r in rows[1:]),
            'max_network_only_hat':max(r['p_network_only_hat'] for r in rows),
        },
        'verdict':'STAGE4_PASS'
    }
    (OUT/'stage4_cross_validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    md=['# 第4问 阶段4：全前沿数值交叉验证','',
        f'- Monte Carlo 样本量：M={M:,}',
        f'- 独立随机种子：{int(SEED)}',
        '- 用途：仅用于验证阶段3解析全局最优证明，不参与最优性判定。','',
        '|方案|p_hat|Wilson 95% CI|解析自短路下界|解析总导通上界|network-only|判定|',
        '|---|---:|---:|---:|---:|---:|---|']
    for r in rows:
        md.append(f"|({r['N_A']},{r['N_B']})|{r['p_hat']:.9f}|[{r['wilson_low']:.9f},{r['wilson_high']:.9f}]|{r['analytic_p_self']:.9f}|{r['analytic_total_upper']:.9f}|{r['p_network_only_hat']:.9f}|{r['status']}|")
    md += ['', '**阶段4结论：** (0,57) 的 Wilson 下端点高于 0.90；7 个成本更低的支配前沿点的 Wilson 上端点均低于 0.90。数值结果与阶段3解析证明一致。']
    (OUT/'stage4_cross_validation_report.md').write_text('\n'.join(md),encoding='utf-8')

if __name__=='__main__':
    main()
