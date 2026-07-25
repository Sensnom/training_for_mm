"""Employee-level verification and independent CP-SAT audit for Question 3."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

from q3_models import Q3ScenarioResult
from q3_roster import Q3RosterResult


@dataclass(frozen=True)
class Q3VerificationResult:
    hourly_coverage: list[dict]
    cross_group_summary: list[dict]
    transition_rows: list[dict]
    summary: dict


def compute_q3_coverage(result: Q3ScenarioResult) -> np.ndarray:
    assert result.z is not None and result.p is not None
    coverage = np.zeros((10, 11, 10), dtype=np.int64)
    for day in range(10):
        for shift, pattern in enumerate(result.fulltime_patterns):
            for first_group in range(10):
                for second_group in range(10):
                    count = int(
                        result.z[day, shift, first_group, second_group]
                    )
                    if not count:
                        continue
                    coverage[
                        day,
                        pattern.first_start - 8 : pattern.first_end - 8,
                        first_group,
                    ] += count
                    coverage[
                        day,
                        pattern.second_start - 8 : pattern.second_end - 8,
                        second_group,
                    ] += count
        for shift, pattern in enumerate(result.parttime_patterns):
            for group in range(10):
                count = int(result.p[day, shift, group])
                if count:
                    coverage[
                        day, pattern.start - 8 : pattern.end - 8, group
                    ] += count
    return coverage


def _verify_cpsat(
    fulltime_staff: int,
    daily_fulltime: np.ndarray,
    parttime_staff: int,
    daily_parttime: np.ndarray,
) -> dict:
    try:
        from ortools.sat.python import cp_model
        import ortools
    except ImportError as exc:
        raise RuntimeError("请求执行 CP-SAT 复核，但 OR-Tools 未安装") from exc

    model = cp_model.CpModel()
    fulltime = {
        (employee, day): model.new_bool_var(f"f_{employee}_{day}")
        for employee in range(fulltime_staff)
        for day in range(10)
    }
    for employee in range(fulltime_staff):
        model.add(
            sum(fulltime[employee, day] for day in range(10)) == 8
        )
    for day in range(10):
        model.add(
            sum(fulltime[employee, day] for employee in range(fulltime_staff))
            == int(daily_fulltime[day])
        )

    parttime = {
        (employee, day): model.new_bool_var(f"p_{employee}_{day}")
        for employee in range(parttime_staff)
        for day in range(10)
    }
    for day in range(10):
        model.add(
            sum(parttime[employee, day] for employee in range(parttime_staff))
            == int(daily_parttime[day])
        )

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    passed = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    if not passed:
        raise AssertionError(f"问题三 CP-SAT 人员池复核失败：status={status}")
    return {
        "status": "PASS",
        "solver": "OR-Tools CP-SAT",
        "solver_version": ortools.__version__,
        "fulltime_employee_count": fulltime_staff,
        "parttime_employee_count": parttime_staff,
        "daily_fulltime_workers": [int(v) for v in daily_fulltime],
        "daily_parttime_workers": [int(v) for v in daily_parttime],
    }


def verify_q3_rosters(
    result: Q3ScenarioResult,
    roster: Q3RosterResult,
    demand: np.ndarray,
    *,
    run_cpsat: bool = True,
) -> Q3VerificationResult:
    if result.status != "OPTIMAL" or result.z is None or result.p is None:
        raise ValueError("只能验证问题三最优可行方案")
    if result.fulltime_staff is None or result.parttime_staff is None:
        raise ValueError("问题三方案缺少人员规模")
    demand = np.asarray(demand, dtype=np.int64)
    if demand.shape != (10, 11, 10):
        raise ValueError("需求张量必须为 (10, 11, 10)")
    if not np.array_equal(roster.reconstructed_z, result.z):
        raise AssertionError("员工表反算的宏观 z 不一致")
    if not np.array_equal(roster.reconstructed_p, result.p):
        raise AssertionError("员工表反算的宏观 p 不一致")

    fulltime_by_employee: dict[str, list[dict]] = defaultdict(list)
    for row in roster.fulltime_schedule:
        fulltime_by_employee[str(row["employee_id"])].append(row)
    if len(fulltime_by_employee) != result.fulltime_staff:
        raise AssertionError("全职员工人数与人员池规模不一致")
    for employee, rows in fulltime_by_employee.items():
        counts = Counter(str(row["status"]) for row in rows)
        if len(rows) != 10 or counts != Counter({"WORK": 8, "REST": 2}):
            raise AssertionError(f"全职员工 {employee} 未满足做八休二")
        if len({int(row["day"]) for row in rows}) != 10:
            raise AssertionError(f"全职员工 {employee} 存在重复日期")

    parttime_employee_days: set[tuple[str, int]] = set()
    for row in roster.parttime_schedule:
        key = (str(row["employee_id"]), int(row["day"]))
        if key in parttime_employee_days:
            raise AssertionError("兼职员工同一天承担多个班次")
        parttime_employee_days.add(key)
        number = int(str(row["employee_id"])[1:])
        if not 1 <= number <= result.parttime_staff:
            raise AssertionError("兼职员工编号超出人员池")

    coverage = compute_q3_coverage(result)
    slack = coverage - demand
    if np.any(slack < 0):
        index = np.argwhere(slack < 0)[0]
        raise AssertionError(
            "问题三逐小时覆盖缺口："
            f"day={index[0] + 1}, hour={index[1] + 8}, group={index[2] + 1}"
        )
    hourly_rows = [
        {
            "day": day + 1,
            "hour_start": f"{hour + 8:02d}:00",
            "hour_end": f"{hour + 9:02d}:00",
            "group": group + 1,
            "demand": int(demand[day, hour, group]),
            "coverage": int(coverage[day, hour, group]),
            "slack": int(slack[day, hour, group]),
        }
        for day in range(10)
        for hour in range(11)
        for group in range(10)
    ]

    transition = np.zeros((10, 10), dtype=np.int64)
    daily_work = np.zeros(10, dtype=np.int64)
    daily_cross = np.zeros(10, dtype=np.int64)
    for row in roster.fulltime_schedule:
        if row["status"] != "WORK":
            continue
        day = int(row["day"]) - 1
        daily_work[day] += 1
        first = int(row["first_group"]) - 1
        second = int(row["second_group"]) - 1
        if first != second:
            transition[first, second] += 1
            daily_cross[day] += 1
    total_cross = int(daily_cross.sum())
    if total_cross != result.cross_group_employee_days:
        raise AssertionError("员工表跨组次数与宏观目标不一致")
    cross_rows = [
        {
            "day": day + 1,
            "fulltime_workdays": int(daily_work[day]),
            "cross_group_employee_days": int(daily_cross[day]),
            "cross_group_rate": (
                float(daily_cross[day] / daily_work[day])
                if daily_work[day]
                else 0.0
            ),
        }
        for day in range(10)
    ]
    cross_rows.append(
        {
            "day": "ALL",
            "fulltime_workdays": int(daily_work.sum()),
            "cross_group_employee_days": total_cross,
            "cross_group_rate": (
                float(total_cross / daily_work.sum())
                if daily_work.sum()
                else 0.0
            ),
        }
    )
    transition_rows = [
        {
            "from_group": first + 1,
            **{
                f"to_group_{second + 1}": int(transition[first, second])
                for second in range(10)
            },
        }
        for first in range(10)
    ]

    daily_parttime = result.p.sum(axis=(1, 2))
    if np.any(daily_parttime > result.parttime_staff):
        raise AssertionError("兼职每日人数超过兼职人员池")
    cpsat = (
        _verify_cpsat(
            result.fulltime_staff,
            daily_work,
            result.parttime_staff,
            daily_parttime,
        )
        if run_cpsat
        else {"status": "SKIPPED_BY_REQUEST"}
    )
    summary = {
        "status": "PASS",
        "scenario": result.spec.scenario_id,
        "demand_cell_count": 1100,
        "deficit_count": int(np.count_nonzero(slack < 0)),
        "minimum_slack": int(slack.min()),
        "maximum_slack": int(slack.max()),
        "total_slack": int(slack.sum()),
        "fulltime_employee_count": result.fulltime_staff,
        "parttime_employee_count": result.parttime_staff,
        "fulltime_record_count": len(roster.fulltime_schedule),
        "parttime_shift_record_count": len(roster.parttime_schedule),
        "all_fulltime_employees_work_8_rest_2": True,
        "parttime_at_most_one_shift_per_day": True,
        "macro_z_matches_employee_schedule": True,
        "macro_p_matches_employee_schedule": True,
        "cross_group_employee_days": total_cross,
        "cross_group_rate": (
            float(total_cross / daily_work.sum()) if daily_work.sum() else 0.0
        ),
        "cpsat_status": cpsat["status"],
        "cpsat": cpsat,
        "maxflow_required": roster.flow_roster.required_flow,
        "maxflow_value": roster.flow_roster.computed_max_flow,
        "maxflow_full": roster.flow_roster.is_full_flow,
        "maxflow_algorithm": roster.flow_roster.algorithm,
    }
    return Q3VerificationResult(
        hourly_coverage=hourly_rows,
        cross_group_summary=cross_rows,
        transition_rows=transition_rows,
        summary=summary,
    )
