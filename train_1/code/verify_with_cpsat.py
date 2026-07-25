"""Optional CP-SAT verification of employee-day degree matrices."""

from __future__ import annotations

from time import perf_counter

import numpy as np


def _verify_one(staff: int, workers: np.ndarray, cp_model) -> tuple[bool, bool]:
    model = cp_model.CpModel()
    work = {
        (employee, day): model.NewBoolVar(f"y_{employee}_{day}")
        for employee in range(staff)
        for day in range(10)
    }
    for employee in range(staff):
        model.Add(sum(work[employee, day] for day in range(10)) == 8)
    for day in range(10):
        model.Add(
            sum(work[employee, day] for employee in range(staff))
            == int(workers[day])
        )
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.Solve(model)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    counts_match = feasible and all(
        sum(solver.Value(work[e, d]) for e in range(staff)) == int(workers[d])
        for d in range(10)
    )
    return feasible, counts_match


def verify_with_cpsat(
    q1_staff: np.ndarray,
    q1_actual_workers: np.ndarray,
    q2_staff: int,
    q2_actual_workers: np.ndarray,
) -> dict:
    started = perf_counter()
    try:
        from ortools.sat.python import cp_model
        import ortools
    except ImportError:
        return {
            "status": "SKIPPED",
            "reason": "OR-Tools is not installed; CP-SAT is an optional independent check",
            "ortools_version": None,
            "q1_all_groups_feasible": None,
            "q2_feasible": None,
            "q2_daily_counts_match": None,
            "runtime_seconds": perf_counter() - started,
        }

    q1_feasible = []
    for group in range(10):
        feasible, _ = _verify_one(
            int(q1_staff[group]), q1_actual_workers[:, group], cp_model
        )
        q1_feasible.append(feasible)
    q2_feasible, q2_match = _verify_one(
        q2_staff, q2_actual_workers, cp_model
    )
    return {
        "status": "PASS" if all(q1_feasible) and q2_feasible and q2_match else "FAIL",
        "reason": None,
        "ortools_version": ortools.__version__,
        "q1_all_groups_feasible": all(q1_feasible),
        "q2_feasible": q2_feasible,
        "q2_daily_counts_match": q2_match,
        "runtime_seconds": perf_counter() - started,
    }

