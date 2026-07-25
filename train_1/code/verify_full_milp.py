"""Independent aggregate MILP verification for Questions 1 and 2."""

from __future__ import annotations

import numpy as np

from milp_utils import solve_integer_program


def _result_dict(info, objective_value: int) -> dict:
    return {
        "solver_name": info.solver_name,
        "solver_version": info.solver_version,
        "status": info.status,
        "objective_value": objective_value,
        "best_bound": info.best_bound,
        "relative_gap": info.relative_gap,
        "runtime_seconds": info.runtime_seconds,
    }


def verify_q1_full_milp(
    demand: np.ndarray, coverage: np.ndarray, solver: str = "HiGHS"
) -> dict:
    # Variables: W_g (10), then x_{d,g,s} (1000).
    variable_count = 10 + 10 * 10 * 10

    def x_index(day: int, group: int, shift: int) -> int:
        return 10 + (day * 10 + group) * 10 + shift

    rows, lower, upper = [], [], []
    for day in range(10):
        for hour in range(11):
            for group in range(10):
                row = np.zeros(variable_count)
                for shift in range(10):
                    row[x_index(day, group, shift)] = coverage[hour, shift]
                rows.append(row)
                lower.append(float(demand[day, hour, group]))
                upper.append(np.inf)
    for day in range(10):
        for group in range(10):
            row = np.zeros(variable_count)
            row[group] = -1
            for shift in range(10):
                row[x_index(day, group, shift)] = 1
            rows.append(row)
            lower.append(-np.inf)
            upper.append(0)
    for group in range(10):
        row = np.zeros(variable_count)
        row[group] = -8
        for day in range(10):
            for shift in range(10):
                row[x_index(day, group, shift)] = 1
        rows.append(row)
        lower.append(0)
        upper.append(0)

    objective = np.zeros(variable_count)
    objective[:10] = 1
    info = solve_integer_program(
        objective,
        np.vstack(rows),
        np.array(lower),
        np.array(upper),
        solver=solver,
    )
    staff = info.values[:10]
    result = _result_dict(info, int(staff.sum()))
    result["group_staff"] = [int(v) for v in staff]
    return result


def verify_q2_full_milp(
    demand: np.ndarray, coverage: np.ndarray, solver: str = "HiGHS"
) -> dict:
    # Variables: W, then x_{d,g,s} (1000).
    variable_count = 1 + 10 * 10 * 10

    def x_index(day: int, group: int, shift: int) -> int:
        return 1 + (day * 10 + group) * 10 + shift

    rows, lower, upper = [], [], []
    for day in range(10):
        for hour in range(11):
            for group in range(10):
                row = np.zeros(variable_count)
                for shift in range(10):
                    row[x_index(day, group, shift)] = coverage[hour, shift]
                rows.append(row)
                lower.append(float(demand[day, hour, group]))
                upper.append(np.inf)
    for day in range(10):
        row = np.zeros(variable_count)
        row[0] = -1
        for group in range(10):
            for shift in range(10):
                row[x_index(day, group, shift)] = 1
        rows.append(row)
        lower.append(-np.inf)
        upper.append(0)
    row = np.zeros(variable_count)
    row[0] = -8
    row[1:] = 1
    rows.append(row)
    lower.append(0)
    upper.append(0)

    objective = np.zeros(variable_count)
    objective[0] = 1
    info = solve_integer_program(
        objective,
        np.vstack(rows),
        np.array(lower),
        np.array(upper),
        solver=solver,
    )
    return _result_dict(info, int(info.values[0]))


def verify_full_milp(
    demand: np.ndarray, coverage: np.ndarray, solver: str = "HiGHS"
) -> dict:
    return {
        "role": "independent aggregate MILP verification; not the main construction",
        "q1": verify_q1_full_milp(demand, coverage, solver=solver),
        "q2": verify_q2_full_milp(demand, coverage, solver=solver),
    }
