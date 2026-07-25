"""Independent checks derived from employee-level schedule rows."""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from shift_patterns import ShiftPattern


def _hourly_rows(
    demand: np.ndarray, coverage: np.ndarray, counts: np.ndarray
) -> tuple[list[dict], dict]:
    computed = np.einsum("hs,dgs->dhg", coverage, counts)
    slack = computed - demand
    rows = []
    for day in range(10):
        for hour in range(11):
            for group in range(10):
                rows.append(
                    {
                        "day": day + 1,
                        "hour": hour + 1,
                        "hour_start": f"{hour + 8:02d}:00",
                        "hour_end": f"{hour + 9:02d}:00",
                        "group": group + 1,
                        "demand": int(demand[day, hour, group]),
                        "coverage": int(computed[day, hour, group]),
                        "slack": int(slack[day, hour, group]),
                    }
                )
    summary = {
        "demand_cell_count": int(demand.size),
        "deficit_count": int(np.count_nonzero(slack < 0)),
        "minimum_slack": int(slack.min()),
        "maximum_slack": int(slack.max()),
        "total_slack": int(slack.sum()),
    }
    return rows, summary


def verify_q1_schedule(
    schedule: list[dict],
    staff: np.ndarray,
    expected_shift_counts: np.ndarray,
    demand: np.ndarray,
    coverage: np.ndarray,
    patterns: list[ShiftPattern],
) -> tuple[list[dict], dict]:
    total_staff = int(np.sum(staff))
    if len(schedule) != total_staff * 10:
        raise AssertionError("问题一员工排班记录数错误")
    valid_shifts = {p.index for p in patterns}
    by_employee: dict[int, list[dict]] = defaultdict(list)
    actual = np.zeros((10, 10, 10), dtype=np.int64)
    for row in schedule:
        by_employee[int(row["employee"])].append(row)
        if row["status"] == "WORK":
            shift = int(row["shift"])
            if shift not in valid_shifts:
                raise AssertionError("问题一出现非法班型")
            actual[int(row["day"]) - 1, int(row["fixed_group"]) - 1, shift - 1] += 1
        elif row["status"] != "REST":
            raise AssertionError("问题一出现非法状态")
    if len(by_employee) != total_staff:
        raise AssertionError("问题一员工数错误")
    for employee, rows in by_employee.items():
        if len(rows) != 10:
            raise AssertionError(f"员工 {employee} 不是 10 条记录")
        statuses = Counter(row["status"] for row in rows)
        if statuses["WORK"] != 8 or statuses["REST"] != 2:
            raise AssertionError(f"员工 {employee} 未满足做八休二")
        if len({row["fixed_group"] for row in rows}) != 1:
            raise AssertionError(f"员工 {employee} 的固定小组发生变化")
    if not np.array_equal(actual, expected_shift_counts):
        raise AssertionError("问题一员工级班型计数与匿名配额不一致")
    hourly_rows, summary = _hourly_rows(demand, coverage, actual)
    if summary["deficit_count"]:
        raise AssertionError("问题一逐小时覆盖存在缺口")
    summary.update(
        {
            "status": "PASS",
            "employee_count": total_staff,
            "record_count": len(schedule),
            "work_record_count": sum(r["status"] == "WORK" for r in schedule),
            "rest_record_count": sum(r["status"] == "REST" for r in schedule),
        }
    )
    return hourly_rows, summary


def verify_q2_schedule(
    schedule: list[dict],
    staff: int,
    expected_shift_counts: np.ndarray,
    demand: np.ndarray,
    coverage: np.ndarray,
    patterns: list[ShiftPattern],
) -> tuple[list[dict], dict]:
    if len(schedule) != staff * 10:
        raise AssertionError("问题二员工排班记录数错误")
    valid_shifts = {p.index for p in patterns}
    by_employee: dict[int, list[dict]] = defaultdict(list)
    actual = np.zeros((10, 10, 10), dtype=np.int64)
    employee_days: set[tuple[int, int]] = set()
    for row in schedule:
        employee = int(row["employee"])
        day = int(row["day"])
        by_employee[employee].append(row)
        if row["status"] == "WORK":
            key = (employee, day)
            if key in employee_days:
                raise AssertionError("问题二同一员工同一天被分到多个小组")
            employee_days.add(key)
            group, shift = int(row["group"]), int(row["shift"])
            if shift not in valid_shifts:
                raise AssertionError("问题二出现非法班型")
            actual[day - 1, group - 1, shift - 1] += 1
        elif row["status"] != "REST":
            raise AssertionError("问题二出现非法状态")
    if len(by_employee) != staff:
        raise AssertionError("问题二员工数错误")
    for employee, rows in by_employee.items():
        statuses = Counter(row["status"] for row in rows)
        if len(rows) != 10 or statuses["WORK"] != 8 or statuses["REST"] != 2:
            raise AssertionError(f"问题二员工 {employee} 未满足做八休二")
    if not np.array_equal(actual, expected_shift_counts):
        raise AssertionError("问题二员工级班型计数与匿名配额不一致")
    hourly_rows, summary = _hourly_rows(demand, coverage, actual)
    if summary["deficit_count"]:
        raise AssertionError("问题二逐小时覆盖存在缺口")
    summary.update(
        {
            "status": "PASS",
            "employee_count": staff,
            "record_count": len(schedule),
            "work_record_count": sum(r["status"] == "WORK" for r in schedule),
            "rest_record_count": sum(r["status"] == "REST" for r in schedule),
            "one_group_per_workday": True,
        }
    )
    return hourly_rows, summary

