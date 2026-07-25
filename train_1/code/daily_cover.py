"""Daily aggregate staffing models and analytic workforce bounds."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np

from milp_utils import MilpResult, solve_integer_program


@dataclass(frozen=True)
class DailyMinimumResult:
    minimum_workers: np.ndarray  # [day, group]
    shift_counts: np.ndarray  # [day, group, shift]
    metadata: list[dict]


@dataclass(frozen=True)
class Q1AnalyticResult:
    peak_daily_minimum: np.ndarray
    total_daily_minimum: np.ndarray
    workday_lower_bound: np.ndarray
    staff: np.ndarray
    total_required_workdays: np.ndarray
    extra_workdays_needed: np.ndarray


@dataclass(frozen=True)
class Q2AnalyticResult:
    daily_lower_bound: np.ndarray
    staff: int
    required_workdays: int
    redundant_workdays: int
    actual_daily_workers: np.ndarray
    redundancy_day: int | None


def _solve_one_day_group(
    demand_vector: np.ndarray,
    coverage: np.ndarray,
    exact_workers: int | None = None,
    solver: str = "HiGHS",
) -> tuple[np.ndarray, MilpResult]:
    shift_count = coverage.shape[1]
    rows = [coverage.astype(float)]
    lower = [np.asarray(demand_vector, dtype=float)]
    upper = [np.full(coverage.shape[0], np.inf)]
    if exact_workers is not None:
        rows.append(np.ones((1, shift_count), dtype=float))
        lower.append(np.array([exact_workers], dtype=float))
        upper.append(np.array([exact_workers], dtype=float))
        objective = np.arange(1, shift_count + 1, dtype=float)
    else:
        objective = np.ones(shift_count, dtype=float)
    result = solve_integer_program(
        objective,
        np.vstack(rows),
        np.concatenate(lower),
        np.concatenate(upper),
        solver=solver,
    )
    values = result.values
    if exact_workers is None:
        minimum = int(values.sum())
        # Resolve alternative minimum covers deterministically.
        values, result = _solve_one_day_group(
            demand_vector, coverage, exact_workers=minimum, solver=solver
        )
    return values, result


def solve_daily_minima(
    demand: np.ndarray, coverage: np.ndarray, solver: str = "HiGHS"
) -> DailyMinimumResult:
    if demand.shape != (10, 11, 10):
        raise ValueError(f"demand 维度必须为 (10, 11, 10)，实际 {demand.shape}")
    if coverage.shape != (11, 10):
        raise ValueError(f"coverage 维度必须为 (11, 10)，实际 {coverage.shape}")

    minima = np.zeros((10, 10), dtype=np.int64)
    shifts = np.zeros((10, 10, 10), dtype=np.int64)
    metadata: list[dict] = []
    for day in range(10):
        for group in range(10):
            counts, info = _solve_one_day_group(
                demand[day, :, group], coverage, solver=solver
            )
            minimum = int(counts.sum())
            minima[day, group] = minimum
            shifts[day, group, :] = counts
            row = {
                "day": day + 1,
                "group": group + 1,
                "minimum_workers": minimum,
                **{f"shift_{s + 1}": int(counts[s]) for s in range(10)},
                "solver_name": info.solver_name,
                "solver_status": info.status,
                "objective_value": minimum,
                "runtime_seconds": info.runtime_seconds,
            }
            metadata.append(row)

    actual = np.einsum("hs,dgs->dhg", coverage, shifts)
    if not np.all(actual >= demand):
        raise AssertionError("日内整数规划结果未覆盖全部需求")
    if not np.array_equal(shifts.sum(axis=2), minima):
        raise AssertionError("日内班型人数和与最低人数不一致")
    return DailyMinimumResult(minima, shifts, metadata)


def analytic_q1_staff(minimum_workers: np.ndarray) -> Q1AnalyticResult:
    minimum_workers = np.asarray(minimum_workers, dtype=np.int64)
    if minimum_workers.shape != (10, 10):
        raise ValueError("问题一最低人数矩阵必须为 (10, 10)")
    peak = minimum_workers.max(axis=0)
    totals = minimum_workers.sum(axis=0)
    workday_bound = np.ceil(totals / 8).astype(np.int64)
    staff = np.maximum(peak, workday_bound)
    required = 8 * staff
    return Q1AnalyticResult(
        peak_daily_minimum=peak,
        total_daily_minimum=totals,
        workday_lower_bound=workday_bound,
        staff=staff,
        total_required_workdays=required,
        extra_workdays_needed=required - totals,
    )


def _allocate_extra_days(
    lower_bound: np.ndarray, staff: int, extra: int
) -> np.ndarray:
    actual = np.asarray(lower_bound, dtype=np.int64).copy()
    order = sorted(range(len(actual)), key=lambda d: (-int(lower_bound[d]), d))
    cursor = 0
    while extra:
        day = order[cursor % len(order)]
        if actual[day] < staff:
            actual[day] += 1
            extra -= 1
        cursor += 1
        if cursor > len(order) * (staff + 1):
            raise RuntimeError("无法分配冗余工作人日")
    return actual


def analytic_q2_staff(minimum_workers: np.ndarray) -> Q2AnalyticResult:
    minimum_workers = np.asarray(minimum_workers, dtype=np.int64)
    if minimum_workers.shape != (10, 10):
        raise ValueError("问题二最低人数矩阵必须为 (10, 10)")
    daily = minimum_workers.sum(axis=1)
    staff = max(int(daily.max()), ceil(int(daily.sum()) / 8))
    required = 8 * staff
    redundant = required - int(daily.sum())
    actual = _allocate_extra_days(daily, staff, redundant)
    changed = np.flatnonzero(actual > daily)
    redundancy_day = int(changed[0] + 1) if redundant and len(changed) == 1 else None
    return Q2AnalyticResult(
        daily_lower_bound=daily,
        staff=staff,
        required_workdays=required,
        redundant_workdays=redundant,
        actual_daily_workers=actual,
        redundancy_day=redundancy_day,
    )


def solve_exact_day_group(
    demand_vector: np.ndarray,
    coverage: np.ndarray,
    workers: int,
    solver: str = "HiGHS",
) -> tuple[np.ndarray, MilpResult]:
    """Public exact-worker model used by final Q1/Q2 quota construction."""

    counts, info = _solve_one_day_group(
        demand_vector, coverage, workers, solver=solver
    )
    if int(counts.sum()) != workers:
        raise AssertionError("精确人数模型未满足班型人数总和")
    return counts, info
