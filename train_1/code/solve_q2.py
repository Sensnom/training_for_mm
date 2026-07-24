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
print("Demand matrix shape:", D.shape)

S12 = []
for b1 in range(8):
    for b2 in range(b1+4, 8):
        S12.append((b1, b2))
print("Number of shifts for Q1/Q2:", len(S12))

A = np.zeros((11, len(S12)), dtype=int)
for s_idx, (b1, b2) in enumerate(S12):
    for h in range(b1, b1+4): A[h, s_idx] = 1
    for h in range(b2, b2+4): A[h, s_idx] = 1

S3 = []
for b1 in range(8):
    for b2 in range(b1+6, 8):
        S3.append((b1, b2))
print("Number of shift pairs for Q3 (2 groups):", len(S3))

# --- Q1 ---
print("-" * 30)
print("Solving Question 1...")
solver1 = pywraplp.Solver.CreateSolver('SCIP')
W_q1_vars = []
for g in range(10):
    W = solver1.IntVar(0, 10000, f'W_{g}')
    R = [solver1.IntVar(0, 10000, f'R_{g}_{d}') for d in range(10)]
    n = {}
    for d in range(10):
        for s in range(len(S12)):
            n[(d, s)] = solver1.IntVar(0, 10000, f'n_{g}_{d}_{s}')
    
    solver1.Add(sum(R) == 2 * W)
    for d in range(10):
        solver1.Add(R[d] <= W)
        solver1.Add(sum(n[(d, s)] for s in range(len(S12))) == W - R[d])
        for h in range(11):
            solver1.Add(sum(A[h, s] * n[(d, s)] for s in range(len(S12))) >= int(D[d, h, g]))
    W_q1_vars.append(W)

solver1.Minimize(sum(W_q1_vars))
status1 = solver1.Solve()
if status1 == pywraplp.Solver.OPTIMAL:
    ans_q1 = int(solver1.Objective().Value())
    print(f"[SUCCESS] Optimal total workers for Q1: {ans_q1}")
else:
    print("[FAIL] Q1 Not solved optimally")

# --- Q2 ---
print("-" * 30)
print("Solving Question 2...")
solver2 = pywraplp.Solver.CreateSolver('SCIP')
W2 = solver2.IntVar(0, 100000, 'W2')
R2 = [solver2.IntVar(0, 100000, f'R2_{d}') for d in range(10)]
W2_gd = {}
for g in range(10):
    for d in range(10):
        W2_gd[(g, d)] = solver2.IntVar(0, 100000, f'W2_{g}_{d}')

n2 = {}
for g in range(10):
    for d in range(10):
        for s in range(len(S12)):
            n2[(g, d, s)] = solver2.IntVar(0, 100000, f'n2_{g}_{d}_{s}')

solver2.Add(sum(R2) == 2 * W2)
for d in range(10):
    solver2.Add(R2[d] <= W2)
    solver2.Add(sum(W2_gd[(g, d)] for g in range(10)) == W2 - R2[d])

for g in range(10):
    for d in range(10):
        solver2.Add(sum(n2[(g, d, s)] for s in range(len(S12))) == W2_gd[(g, d)])
        for h in range(11):
            solver2.Add(sum(A[h, s] * n2[(g, d, s)] for s in range(len(S12))) >= int(D[d, h, g]))

solver2.Minimize(W2)
status2 = solver2.Solve()
if status2 == pywraplp.Solver.OPTIMAL:
    ans_q2 = int(solver2.Objective().Value())
    print(f"[SUCCESS] Optimal total workers for Q2: {ans_q2}")
else:
    print("[FAIL] Q2 Not solved optimally")

# --- Q3 ---
print("-" * 30)
print("Solving Question 3...")
solver3 = pywraplp.Solver.CreateSolver('SCIP')
W3 = solver3.IntVar(0, 100000, 'W3')
R3 = [solver3.IntVar(0, 100000, f'R3_{d}') for d in range(10)]

n_1g = {} # Serving 1 group
for d in range(10):
    for s in range(len(S12)):
        for g in range(10):
            n_1g[(d, s, g)] = solver3.IntVar(0, 100000, f'n1_{d}_{s}_{g}')

n_2g = {} # Serving 2 groups
for d in range(10):
    for p in range(len(S3)):
        for g1 in range(10):
            for g2 in range(10):
                if g1 != g2:
                    n_2g[(d, p, g1, g2)] = solver3.IntVar(0, 100000, f'n2_{d}_{p}_{g1}_{g2}')

solver3.Add(sum(R3) == 2 * W3)
for d in range(10):
    solver3.Add(R3[d] <= W3)
    total_workers_today = (
        sum(n_1g[(d, s, g)] for s in range(len(S12)) for g in range(10)) + 
        sum(n_2g[(d, p, g1, g2)] for p in range(len(S3)) for g1 in range(10) for g2 in range(10) if g1 != g2)
    )
    solver3.Add(total_workers_today == W3 - R3[d])

for d in range(10):
    for g in range(10):
        for h in range(11):
            expr = []
            # from 1g
            for s, (b1, b2) in enumerate(S12):
                if b1 <= h < b1+4 or b2 <= h < b2+4:
                    expr.append(n_1g[(d, s, g)])
            # from 2g
            for p, (b1, b2) in enumerate(S3):
                if b1 <= h < b1+4:
                    for g2 in range(10):
                        if g != g2: expr.append(n_2g[(d, p, g, g2)])
                if b2 <= h < b2+4:
                    for g1 in range(10):
                        if g1 != g: expr.append(n_2g[(d, p, g1, g)])
            solver3.Add(sum(expr) >= int(D[d, h, g]))

solver3.Minimize(W3)
status3 = solver3.Solve()
if status3 == pywraplp.Solver.OPTIMAL:
    ans_q3 = int(solver3.Objective().Value())
    print(f"[SUCCESS] Optimal total workers for Q3: {ans_q3}")
else:
    print("[FAIL] Q3 Not solved optimally")
