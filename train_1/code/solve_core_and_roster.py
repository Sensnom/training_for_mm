"""Core deterministic constructions for Questions 1 and 2."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from daily_cover import (
    DailyMinimumResult,
    analytic_q1_staff,
    analytic_q2_staff,
    solve_exact_day_group,
)
from roster_flow import FlowRoster, assign_rest_days
from schedule_mapping import map_q1_schedule, map_q2_schedule
from shift_patterns import ShiftPattern
from verification import verify_q1_schedule, verify_q2_schedule


@dataclass(frozen=True)
class Q1Result:
    staff: np.ndarray
    actual_workers: np.ndarray
    shift_counts: np.ndarray
    group_results: list[dict]
    maxflow_summary: list[dict]
    employee_day_status: list[dict]
    employee_schedule: list[dict]
    hourly_coverage: list[dict]
    verification: dict


@dataclass(frozen=True)
class Q2Result:
    staff: int
    daily_lower_bound: np.ndarray
    actual_daily_workers: np.ndarray
    redundant_workdays: int
    redundancy_day: int | None
    shift_counts: np.ndarray
    maxflow_summary: dict
    employee_day_status: list[dict]
    employee_schedule: list[dict]
    hourly_coverage: list[dict]
    verification: dict


def _allocate_q1_workdays(minimum: np.ndarray, staff: int) -> np.ndarray:
    actual = np.asarray(minimum, dtype=np.int64).copy()
    extra = 8 * staff - int(actual.sum())
    order = sorted(range(10), key=lambda day: (-int(minimum[day]), day))
    for day in order:
        addition = min(extra, staff - int(actual[day]))
        actual[day] += addition
        extra -= addition
        if extra == 0:
            break
    if extra:
        raise RuntimeError("问题一补充工作人日无法在每日编制上限内分配")
    return actual


def solve_q1(
    demand: np.ndarray,
    coverage: np.ndarray,
    patterns: list[ShiftPattern],
    daily: DailyMinimumResult,
    solver: str = "HiGHS",
) -> Q1Result:
    analytic = analytic_q1_staff(daily.minimum_workers)
    actual_workers = np.zeros((10, 10), dtype=np.int64)
    shift_counts = np.zeros((10, 10, 10), dtype=np.int64)
    for group in range(10):
        actual_workers[:, group] = _allocate_q1_workdays(
            daily.minimum_workers[:, group], int(analytic.staff[group])
        )
        for day in range(10):
            counts, _ = solve_exact_day_group(
                demand[day, :, group],
                coverage,
                int(actual_workers[day, group]),
                solver=solver,
            )
            shift_counts[day, group, :] = counts

    group_results = []
    for group in range(10):
        group_results.append(
            {
                "group": group + 1,
                "peak_daily_minimum": int(analytic.peak_daily_minimum[group]),
                "total_daily_minimum": int(analytic.total_daily_minimum[group]),
                "workday_lower_bound": int(analytic.workday_lower_bound[group]),
                "optimal_staff": int(analytic.staff[group]),
                "total_required_workdays": int(
                    analytic.total_required_workdays[group]
                ),
                "extra_workdays_needed": int(
                    analytic.extra_workdays_needed[group]
                ),
            }
        )

    flow_rosters: list[FlowRoster] = []
    maxflow_summary = []
    for group in range(10):
        roster = assign_rest_days(
            int(analytic.staff[group]), actual_workers[:, group]
        )
        flow_rosters.append(roster)
        maxflow_summary.append(
            {
                "group": group + 1,
                "staff": int(analytic.staff[group]),
                "required_flow": roster.required_flow,
                "computed_max_flow": roster.computed_max_flow,
                "is_full_flow": roster.is_full_flow,
                "runtime_seconds": roster.runtime_seconds,
                "algorithm": roster.algorithm,
            }
        )
    schedule, day_status = map_q1_schedule(
        analytic.staff,
        shift_counts,
        [roster.work_status for roster in flow_rosters],
        patterns,
    )
    hourly, verification = verify_q1_schedule(
        schedule, analytic.staff, shift_counts, demand, coverage, patterns
    )
    return Q1Result(
        staff=analytic.staff,
        actual_workers=actual_workers,
        shift_counts=shift_counts,
        group_results=group_results,
        maxflow_summary=maxflow_summary,
        employee_day_status=day_status,
        employee_schedule=schedule,
        hourly_coverage=hourly,
        verification=verification,
    )


def solve_q2(
    demand: np.ndarray,
    coverage: np.ndarray,
    patterns: list[ShiftPattern],
    daily: DailyMinimumResult,
    solver: str = "HiGHS",
) -> Q2Result:
    analytic = analytic_q2_staff(daily.minimum_workers)
    group_workers = daily.minimum_workers.copy()
    for day in range(10):
        extra = int(
            analytic.actual_daily_workers[day] - analytic.daily_lower_bound[day]
        )
        order = sorted(
            range(10),
            key=lambda group: (-int(daily.minimum_workers[day, group]), group),
        )
        cursor = 0
        while extra:
            group_workers[day, order[cursor % 10]] += 1
            extra -= 1
            cursor += 1

    shift_counts = np.zeros((10, 10, 10), dtype=np.int64)
    for day in range(10):
        for group in range(10):
            counts, _ = solve_exact_day_group(
                demand[day, :, group],
                coverage,
                int(group_workers[day, group]),
                solver=solver,
            )
            shift_counts[day, group, :] = counts
    if not np.array_equal(
        shift_counts.sum(axis=(1, 2)), analytic.actual_daily_workers
    ):
        raise AssertionError("问题二每日匿名班型总人数与目标人数不一致")

    roster = assign_rest_days(analytic.staff, analytic.actual_daily_workers)
    schedule, day_status = map_q2_schedule(
        analytic.staff, shift_counts, roster.work_status, patterns
    )
    hourly, verification = verify_q2_schedule(
        schedule, analytic.staff, shift_counts, demand, coverage, patterns
    )
    maxflow_summary = {
        "staff": analytic.staff,
        "required_flow": roster.required_flow,
        "computed_max_flow": roster.computed_max_flow,
        "is_full_flow": roster.is_full_flow,
        "runtime_seconds": roster.runtime_seconds,
        "algorithm": roster.algorithm,
    }
    return Q2Result(
        staff=analytic.staff,
        daily_lower_bound=analytic.daily_lower_bound,
        actual_daily_workers=analytic.actual_daily_workers,
        redundant_workdays=analytic.redundant_workdays,
        redundancy_day=analytic.redundancy_day,
        shift_counts=shift_counts,
        maxflow_summary=maxflow_summary,
        employee_day_status=day_status,
        employee_schedule=schedule,
        hourly_coverage=hourly,
        verification=verification,
    )
