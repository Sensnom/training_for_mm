import csv, json, math, time
from pathlib import Path
import numpy as np

# Reuse the verified Q4 MC kernel only for B-only numerical validation.
from q4_strict_periodic_mc import summarize, unit_tests

OUT = Path(__file__).resolve().parent

# -------------------------
# Problem constants
# -------------------------
L = 10000.0      # nm
DELTA = 1.8      # nm
R_A = 30.0       # nm
LEN_A = 5000.0   # nm
R_B = 200.0      # nm

# volumes in um^3
V_A = math.pi * (R_A/1000.0)**2 * (LEN_A/1000.0)
V_B = (4.0/3.0) * math.pi * (R_B/1000.0)**3
C_A = 1.05 * V_A
C_B = 0.05 * V_B

# Strict flat-cylinder direct-X probability already proved in P0 repair.
pA = LEN_A/(2.0*L) + math.pi*R_A/(2.0*L)
pB = 2.0*R_B/L
# For a non-crossing object, the extra center interval that can touch one specified
# electrode through the tunneling/contact tolerance has width DELTA, regardless of
# object X half-extent. Thus pE = DELTA/L for both A and B.
pE = DELTA/L


def p_self(na: int, nb: int) -> float:
    """Analytic lower bound: at least one object directly crosses X."""
    return 1.0 - (1.0-pA)**na * (1.0-pB)**nb


def p_necessary_upper(na: int, nb: int) -> float:
    """
    Analytic upper bound for total conduction.

    Conduction implies either:
      D = at least one direct X-crossing object, or
      no D, but at least one left-electrode anchor AND one right-electrode anchor.

    For one A: P(D or specified-side anchor) = pA + pE.
    For one B: P(D or specified-side anchor) = pB + pE.
    The left/right non-crossing anchor strips are disjoint, each of width DELTA.
    Inclusion-exclusion yields the necessary-event probability below.
    """
    q_noD_noL = (1.0-pA-pE)**na * (1.0-pB-pE)**nb
    q_noD_noLR = (1.0-pA-2.0*pE)**na * (1.0-pB-2.0*pE)**nb
    return 1.0 - 2.0*q_noD_noL + q_noD_noLR


def min_n_for_self(p_single: float, target: float = 0.90) -> int:
    return math.ceil(math.log(1.0-target)/math.log(1.0-p_single))


def strict_cheaper(na: int, nb: int, cstar: float) -> bool:
    return na*C_A + nb*C_B < cstar - 1e-15


def main():
    # 0) Re-run the B kernel unit tests before global search.
    tests = unit_tests(seed=20260818)
    if not all(t['pass'] for t in tests):
        raise RuntimeError('B geometry/unit tests failed; stop stage 3.')
    (OUT/'stage3_unit_tests.json').write_text(json.dumps(tests, ensure_ascii=False, indent=2), encoding='utf-8')

    # 1) Analytic initial incumbents.
    nA_self = min_n_for_self(pA)
    nB_self = min_n_for_self(pB)
    pureA = {'N_A': nA_self, 'N_B': 0, 'cost_yuan': nA_self*C_A, 'p_self': p_self(nA_self,0)}
    pureB = {'N_A': 0, 'N_B': nB_self, 'cost_yuan': nB_self*C_B, 'p_self': p_self(0,nB_self)}
    best = pureB if pureB['cost_yuan'] < pureA['cost_yuan'] else pureA
    Cstar = best['cost_yuan']

    # 2) Exact cost-dominance frontier under C < Cstar.
    # Since 7 A already costs more than the 57-B incumbent, only NA = 0,...,6 can compete.
    max_na = math.floor((Cstar - 1e-15)/C_A)
    frontier = []
    for na in range(max_na+1):
        # Largest integer nb satisfying na*C_A + nb*C_B < Cstar.
        nb = math.ceil((Cstar-na*C_A)/C_B) - 1
        if nb < 0:
            continue
        row = {
            'N_A': na,
            'N_B_frontier': nb,
            'cost_yuan': na*C_A + nb*C_B,
            'p_self_lower': p_self(na,nb),
            'p_total_necessary_upper': p_necessary_upper(na,nb),
            'upper_below_0p90': p_necessary_upper(na,nb) < 0.90,
        }
        frontier.append(row)

    # 3) Independent exhaustive audit of ALL strictly cheaper integer points.
    all_cheaper = []
    for na in range(max_na+1):
        nb_max = math.ceil((Cstar-na*C_A)/C_B) - 1
        for nb in range(max(0,nb_max)+1):
            if not strict_cheaper(na,nb,Cstar):
                continue
            all_cheaper.append({
                'N_A':na,
                'N_B':nb,
                'cost_yuan':na*C_A+nb*C_B,
                'p_self_lower':p_self(na,nb),
                'p_total_necessary_upper':p_necessary_upper(na,nb),
            })
    all_cheaper.sort(key=lambda r:r['p_total_necessary_upper'], reverse=True)

    assert len(all_cheaper) == 216, len(all_cheaper)
    assert all(r['p_total_necessary_upper'] < 0.90 for r in all_cheaper)
    assert all(r['upper_below_0p90'] for r in frontier)

    # 4) Fresh independent full-graph MC validation for best and strongest cheaper competitor.
    # Search/global proof does NOT depend on these MC runs; they are numerical validation only.
    mc_jobs = [
        (0,57,500000,271828182,'independent_opt_seed_e'),
        (0,57,500000,161803398,'independent_opt_seed_phi'),
        (0,56,500000,271828182,'independent_competitor_56B'),
    ]
    mc_rows=[]
    for na,nb,M,seed,label in mc_jobs:
        t0=time.time()
        r=summarize(na,nb,M,np.uint64(seed),0)
        r['label']=label
        r['analytic_p_self']=p_self(na,nb)
        r['analytic_total_upper']=p_necessary_upper(na,nb)
        r['elapsed_s']=time.time()-t0
        mc_rows.append(r)

    # 5) Write evidence files.
    with open(OUT/'stage3_frontier_7points.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(frontier[0].keys())); w.writeheader(); w.writerows(frontier)
    with open(OUT/'stage3_all_216_cheaper_points.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(all_cheaper[0].keys())); w.writeheader(); w.writerows(all_cheaper)
    with open(OUT/'stage3_mc_independent_validation.csv','w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(mc_rows[0].keys())); w.writeheader(); w.writerows(mc_rows)

    summary = {
        'constants': {
            'p_D_A':pA,'p_D_B':pB,'p_E_one_side_non_crossing':pE,
            'V_A_um3':V_A,'V_B_um3':V_B,'c_A_yuan':C_A,'c_B_yuan':C_B,
            'cost_ratio_A_over_B':C_A/C_B,
        },
        'pure_A_analytic':pureA,
        'pure_B_analytic':pureB,
        'incumbent_global_candidate':best,
        'max_N_A_in_strictly_cheaper_solution':max_na,
        'frontier':frontier,
        'number_of_strictly_cheaper_integer_points':len(all_cheaper),
        'strongest_cheaper_point_by_upper_bound':all_cheaper[0],
        'all_cheaper_upper_bounds_below_0p90':all(r['p_total_necessary_upper']<0.90 for r in all_cheaper),
        'mc_validation':mc_rows,
        'verdict': 'GLOBAL_OPTIMUM_PROVED: (N_A,N_B)=(0,57)',
        'logic': [
            '57 B is feasible because its analytic direct-X lower bound exceeds 0.90.',
            'Any strictly cheaper integer solution has N_A<=6.',
            'For each fixed N_A, conduction probability is nondecreasing in N_B, so only the maximum cheaper N_B frontier point can dominate that row.',
            'The analytic necessary-event upper bound is below 0.90 at all seven frontier points.',
            'Therefore every one of the 216 strictly cheaper integer points is infeasible.',
            'Monte Carlo is used only as independent numerical validation, not as the global-optimality proof.'
        ]
    }
    (OUT/'stage3_global_search_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

    md=[]
    md += ['# 第4问 阶段3：改进后的整数全局搜索结果','']
    md += [f'- 纯A解析最小自短路可行数：{nA_self}，成本 {pureA["cost_yuan"]:.12f} 元，解析下界 {pureA["p_self"]:.12f}。']
    md += [f'- 纯B解析最小自短路可行数：{nB_self}，成本 {pureB["cost_yuan"]:.12f} 元，解析下界 {pureB["p_self"]:.12f}。']
    md += [f'- 更新成本上界：C* = C(0,57) = {Cstar:.12f} 元。','']
    md += ['## 7个成本支配前沿点','', '|N_A|N_B|max cheaper cost|p_self lower|p_total necessary upper|', '|---:|---:|---:|---:|---:|']
    for r in frontier:
        md.append(f'|{r["N_A"]}|{r["N_B_frontier"]}|{r["cost_yuan"]:.9f}|{r["p_self_lower"]:.9f}|{r["p_total_necessary_upper"]:.9f}|')
    md += ['', f'216个成本严格低于(0,57)的整数点已全部枚举。最大的总导通概率必要事件上界出现在 ({all_cheaper[0]["N_A"]},{all_cheaper[0]["N_B"]})，为 {all_cheaper[0]["p_total_necessary_upper"]:.12f} < 0.90。', '']
    md += ['## 独立Monte Carlo数值验证','', '|方案|M|seed|p_hat|Wilson 95% CI|network_only|', '|---|---:|---:|---:|---|---:|']
    for r in mc_rows:
        md.append(f'|({r["N_A"]},{r["N_B"]})|{r["M"]}|{r["seed"]}|{r["p_hat"]:.9f}|[{r["wilson_low"]:.9f}, {r["wilson_high"]:.9f}]|{r["p_network_only_hat"]:.9f}|')
    md += ['', '## 最终结论','', f'**全局最优解：N_A*=0，N_B*=57；最小成本 C_min={Cstar:.12f} 元。**', f'B体积分数 = {57*V_B/1000*100:.12f}%。']
    (OUT/'stage3_improved_global_search_report.md').write_text('\n'.join(md),encoding='utf-8')

    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
