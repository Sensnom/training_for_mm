import pandas as pd
import numpy as np
from ortools.linear_solver import pywraplp
import sys

def load_data(filepath):
    df = pd.read_excel(filepath)
    data = []
    for i in range(len(df)):
        try:
            day = int(df.iloc[i, 0])
            hour_str = str(df.iloc[i, 1])
            if '-' in hour_str:
                row_data = [day, hour_str] + list(df.iloc[i, 2:12].values)
                data.append(row_data)
        except Exception as e:
            continue
            
    D = np.zeros((10, 11, 10), dtype=int)
    for row in data:
        day = row[0] - 1
        hour_str = row[1]
        start_h = int(hour_str.split(':')[0])
        hour_idx = start_h - 8
        for g in range(10):
            D[day, hour_idx, g] = int(row[2+g])
    return D

print("Loading data...")
D = load_data('e:/数学建模知识库/附件1.xls')

S12 = []
for b1 in range(8):
    for b2 in range(b1+4, 8):
        S12.append((b1, b2))

A = np.zeros((11, len(S12)), dtype=int)
for s_idx, (b1, b2) in enumerate(S12):
    for h in range(b1, b1+4): A[h, s_idx] = 1
    for h in range(b2, b2+4): A[h, s_idx] = 1

S3_original = []
for b1 in range(8):
    for b2 in range(b1+6, 8):
        S3_original.append((b1, b2))

S3_relaxed = []
for b1 in range(8):
    for b2 in range(b1+5, 8): # at least 1 hour gap
        S3_relaxed.append((b1, b2))

# --- Function to solve Q3 logic ---
def solve_q3(S3_list, name="Q3"):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    W = solver.IntVar(0, 100000, 'W')
    R = [solver.IntVar(0, 100000, f'R_{d}') for d in range(10)]
    n = {}
    for d in range(10):
        for p in range(len(S3_list)):
            for g1 in range(10):
                for g2 in range(10):
                    n[(d, p, g1, g2)] = solver.IntVar(0, 100000, f'n_{d}_{p}_{g1}_{g2}')

    solver.Add(sum(R) == 2 * W)
    for d in range(10):
        solver.Add(R[d] <= W)
        solver.Add(sum(n[(d, p, g1, g2)] for p in range(len(S3_list)) for g1 in range(10) for g2 in range(10)) == W - R[d])

    for d in range(10):
        for g in range(10):
            for h in range(11):
                expr = []
                for p, (b1, b2) in enumerate(S3_list):
                    if b1 <= h < b1 + 4:
                        for g2 in range(10):
                            expr.append(n[(d, p, g, g2)])
                    if b2 <= h < b2 + 4:
                        for g1 in range(10):
                            expr.append(n[(d, p, g1, g)])
                solver.Add(sum(expr) >= int(D[d, h, g]))

    solver.Minimize(W)
    status = solver.Solve()
    if status == pywraplp.Solver.OPTIMAL:
        ans = int(solver.Objective().Value())
        print(f"[SUCCESS] {name} Optimal workers: {ans}")
    else:
        print(f"[FAIL] {name} Not solved optimally (Infeasible)")

print("-" * 30)
solve_q3(S3_original, "Q3 Original (Gap >= 2h)")
solve_q3(S3_relaxed, "Q3 Relaxed (Gap >= 1h)")
