import json
from pathlib import Path

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

ROOT = Path(r"C:\Users\FY\Documents\Codex\2026-07-19\new-chat-2")
DATA = Path(r"E:\数学建模知识库\附件1.xls")
OUT = ROOT / "output" / "verified"
OUT.mkdir(parents=True, exist_ok=True)


def load_demand():
    df = pd.read_excel(DATA)
    D = np.zeros((10, 11, 10), dtype=int)
    n = 0
    for _, row in df.iterrows():
        try:
            d = int(row.iloc[0]) - 1
            hs = str(row.iloc[1])
            if "-" not in hs:
                continue
            h = int(hs.split(":")[0]) - 8
            if 0 <= d < 10 and 0 <= h < 11:
                D[d, h, :] = [int(v) for v in row.iloc[2:12]]
                n += 1
        except Exception:
            pass
    assert n == 110 and np.all(D > 0)
    return D


def patterns(b1, b2, gap=2):
    ans = []
    for s1 in range(0, 12 - b1):
        for s2 in range(s1 + b1 + gap, 12 - b2):
            ans.append((s1, s2, b1, b2))
    return ans


P44 = patterns(4, 4)
P43 = patterns(4, 3)
P34 = patterns(3, 4)


def solve(types, D):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    N = solver.IntVar(0, 100000, "N")
    R = [solver.IntVar(0, 100000, f"R_{d}") for d in range(10)]
    allp = {"44": P44, "43": P43, "34": P34}
    z = {}
    for t in types:
        for d in range(10):
            for p in range(len(allp[t])):
                for g in range(10):
                    for k in range(10):
                        z[t,d,p,g,k] = solver.IntVar(0, 100000, f"z_{t}_{d}_{p}_{g}_{k}")

    solver.Add(sum(R) == 2 * N)
    for d in range(10):
        solver.Add(sum(z[t,d,p,g,k] for t in types for p in range(len(allp[t])) for g in range(10) for k in range(10)) + R[d] == N)
        for h in range(11):
            for g in range(10):
                terms = []
                for t in types:
                    for p,(s1,s2,b1,b2) in enumerate(allp[t]):
                        if s1 <= h < s1+b1:
                            terms.extend(z[t,d,p,g,k] for k in range(10))
                        if s2 <= h < s2+b2:
                            terms.extend(z[t,d,p,k,g] for k in range(10))
                solver.Add(sum(terms) >= int(D[d,h,g]))

    repair = sum(z[t,d,p,g,k] for t in types if t != "44" for d in range(10) for p in range(len(allp[t])) for g in range(10) for k in range(10))
    solver.Minimize(repair)
    st1 = solver.Solve()
    assert st1 == pywraplp.Solver.OPTIMAL
    S = int(round(repair.solution_value()))
    solver.Add(repair == S)
    solver.Minimize(N)
    st2 = solver.Solve()
    assert st2 == pywraplp.Solver.OPTIMAL
    nval = int(round(N.solution_value()))
    daily_repair = [sum(int(round(z[t,d,p,g,k].solution_value())) for t in types if t != "44" for p in range(len(allp[t])) for g in range(10) for k in range(10)) for d in range(10)]
    daily_work = [sum(int(round(z[t,d,p,g,k].solution_value())) for t in types for p in range(len(allp[t])) for g in range(10) for k in range(10)) for d in range(10)]
    return {"types": types, "repair_employee_days": S, "workers": nval, "daily_repair": daily_repair, "daily_work": daily_work, "status": "OPTIMAL_LEXICOGRAPHIC"}


def main():
    D = load_demand()
    blind_demand = [int(D[d,5,:].sum()) for d in range(10)]  # 13:00-14:00
    result = {
        "pattern_counts": {"44": len(P44), "43": len(P43), "34": len(P34)},
        "blind_hour_daily_total": blind_demand,
        "blind_hour_all_days": sum(blind_demand),
        "scenario_B_44_43": solve(["44","43"], D),
        "scenario_C_44_43_34": solve(["44","43","34"], D),
    }
    (OUT / "repair_43_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
