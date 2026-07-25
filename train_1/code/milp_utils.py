"""Small, auditable wrapper around SCIP and SciPy/HiGHS."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class MilpResult:
    values: np.ndarray
    objective_value: float
    best_bound: float
    relative_gap: float
    runtime_seconds: float
    status: str
    solver_name: str = "SciPy/HiGHS"
    solver_version: str = scipy.__version__


def solve_integer_program(
    objective: np.ndarray,
    matrix: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    variable_lower: np.ndarray | float = 0.0,
    variable_upper: np.ndarray | float = np.inf,
    time_limit: float = 300.0,
    solver: str = "HiGHS",
) -> MilpResult:
    objective = np.asarray(objective, dtype=float)
    matrix = np.asarray(matrix, dtype=float)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != objective.size:
        raise ValueError("MILP 约束矩阵列数必须等于变量数")
    if lower.shape != (matrix.shape[0],) or upper.shape != lower.shape:
        raise ValueError("MILP 约束上下界维度不匹配")

    normalized_solver = solver.strip().lower()
    if normalized_solver in {"auto", "highs", "scipy/highs"}:
        return _solve_with_highs(
            objective,
            matrix,
            lower,
            upper,
            variable_lower,
            variable_upper,
            time_limit,
        )
    if normalized_solver in {"scip", "pyscipopt/scip"}:
        return _solve_with_scip(
            objective,
            matrix,
            lower,
            upper,
            variable_lower,
            variable_upper,
            time_limit,
        )
    raise ValueError(f"不支持的整数规划求解器：{solver}")


def _solve_with_highs(
    objective: np.ndarray,
    matrix: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    variable_lower: np.ndarray | float,
    variable_upper: np.ndarray | float,
    time_limit: float,
) -> MilpResult:
    started = perf_counter()
    result = milp(
        c=objective,
        integrality=np.ones(objective.size, dtype=np.uint8),
        bounds=Bounds(variable_lower, variable_upper),
        constraints=LinearConstraint(matrix, lower, upper),
        options={"presolve": True, "time_limit": time_limit, "mip_rel_gap": 0.0},
    )
    elapsed = perf_counter() - started
    if result.status != 0 or not result.success or result.x is None:
        raise RuntimeError(
            "HiGHS 未得到最优整数解："
            f"status={result.status}, success={result.success}, message={result.message}"
        )
    rounded = np.rint(result.x).astype(np.int64)
    if not np.allclose(result.x, rounded, atol=1e-7):
        raise RuntimeError("HiGHS 返回了非整数解")
    return MilpResult(
        values=rounded,
        objective_value=float(result.fun),
        best_bound=float(getattr(result, "mip_dual_bound", result.fun)),
        relative_gap=float(getattr(result, "mip_gap", 0.0)),
        runtime_seconds=elapsed,
        status="OPTIMAL",
    )


def _solve_with_scip(
    objective: np.ndarray,
    matrix: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    variable_lower: np.ndarray | float,
    variable_upper: np.ndarray | float,
    time_limit: float,
) -> MilpResult:
    try:
        from pyscipopt import Model, quicksum
    except ImportError as exc:
        raise RuntimeError(
            "请求使用 SCIP，但 PySCIPOpt 未安装；请执行 pip install pyscipopt"
        ) from exc

    variable_count = objective.size
    lb = np.broadcast_to(
        np.asarray(variable_lower, dtype=float), (variable_count,)
    )
    ub = np.broadcast_to(
        np.asarray(variable_upper, dtype=float), (variable_count,)
    )
    model = Model("staff_scheduling")
    model.hideOutput()
    model.setParam("limits/time", float(time_limit))
    model.setParam("limits/gap", 0.0)
    variables = [
        model.addVar(
            name=f"x_{index}",
            vtype="INTEGER",
            lb=float(lb[index]),
            ub=None if np.isinf(ub[index]) else float(ub[index]),
        )
        for index in range(variable_count)
    ]
    model.setObjective(
        quicksum(
            float(objective[index]) * variables[index]
            for index in np.flatnonzero(objective)
        ),
        "minimize",
    )
    for row_index in range(matrix.shape[0]):
        nonzero = np.flatnonzero(matrix[row_index])
        expression = quicksum(
            float(matrix[row_index, column]) * variables[column]
            for column in nonzero
        )
        row_lower = lower[row_index]
        row_upper = upper[row_index]
        if np.isfinite(row_lower) and np.isfinite(row_upper):
            if np.isclose(row_lower, row_upper):
                model.addCons(expression == float(row_lower))
            else:
                model.addCons(expression >= float(row_lower))
                model.addCons(expression <= float(row_upper))
        elif np.isfinite(row_lower):
            model.addCons(expression >= float(row_lower))
        elif np.isfinite(row_upper):
            model.addCons(expression <= float(row_upper))

    started = perf_counter()
    model.optimize()
    elapsed = perf_counter() - started
    status = str(model.getStatus()).lower()
    if status != "optimal":
        raise RuntimeError(f"SCIP 未得到最优整数解：status={status}")
    values = np.array([model.getVal(variable) for variable in variables])
    rounded = np.rint(values).astype(np.int64)
    if not np.allclose(values, rounded, atol=1e-7):
        raise RuntimeError("SCIP 返回了非整数解")
    version = (
        f"{model.getMajorVersion()}."
        f"{model.getMinorVersion()}."
        f"{model.getTechVersion()}"
    )
    return MilpResult(
        values=rounded,
        objective_value=float(model.getObjVal()),
        best_bound=float(model.getDualbound()),
        relative_gap=float(model.getGap()),
        runtime_seconds=elapsed,
        status="OPTIMAL",
        solver_name="PySCIPOpt/SCIP",
        solver_version=version,
    )
