"""Deterministic employee-level construction for Question 3."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from q3_models import Q3ScenarioResult
from roster_flow import FlowRoster, assign_rest_days


@dataclass(frozen=True)
class Q3RosterResult:
    fulltime_schedule: list[dict]
    parttime_schedule: list[dict]
    flow_roster: FlowRoster
    reconstructed_z: np.ndarray
    reconstructed_p: np.ndarray


def _clock(hour: int) -> str:
    return f"{hour:02d}:00"


def build_q3_rosters(result: Q3ScenarioResult) -> Q3RosterResult:
    if result.status != "OPTIMAL" or result.z is None or result.p is None:
        raise ValueError("只有问题三最优可行方案才能构造员工级排班")
    if result.fulltime_staff is None or result.parttime_staff is None:
        raise ValueError("问题三方案缺少人员池规模")
    z = np.asarray(result.z, dtype=np.int64)
    p = np.asarray(result.p, dtype=np.int64)
    expected_z_shape = (10, len(result.fulltime_patterns), 10, 10)
    expected_p_shape = (10, len(result.parttime_patterns), 10)
    if z.shape != expected_z_shape or p.shape != expected_p_shape:
        raise ValueError("问题三宏观变量维度与班型不匹配")

    daily_workers = z.sum(axis=(1, 2, 3))
    flow = assign_rest_days(result.fulltime_staff, daily_workers)
    assignments: dict[tuple[int, int], tuple[int, int, int]] = {}
    for day in range(10):
        employees = [
            employee + 1
            for employee in range(result.fulltime_staff)
            if flow.work_status[employee, day]
        ]
        slots = [
            (shift, first_group, second_group)
            for shift in range(len(result.fulltime_patterns))
            for first_group in range(10)
            for second_group in range(10)
            for _ in range(int(z[day, shift, first_group, second_group]))
        ]
        if len(employees) != len(slots):
            raise AssertionError("问题三全职员工数与宏观班次槽位数不一致")
        for employee, slot in zip(employees, slots, strict=True):
            assignments[employee, day + 1] = slot

    fulltime_schedule: list[dict] = []
    reconstructed_z = np.zeros_like(z)
    for employee in range(1, result.fulltime_staff + 1):
        employee_id = f"F{employee:04d}"
        for day in range(1, 11):
            if not flow.work_status[employee - 1, day - 1]:
                fulltime_schedule.append(
                    {
                        "employee_id": employee_id,
                        "day": day,
                        "status": "REST",
                        "shift_id": "",
                        "first_start": "",
                        "first_end": "",
                        "first_group": "",
                        "second_start": "",
                        "second_end": "",
                        "second_group": "",
                        "cross_group": False,
                    }
                )
                continue
            shift, first_group, second_group = assignments[employee, day]
            pattern = result.fulltime_patterns[shift]
            reconstructed_z[
                day - 1, shift, first_group, second_group
            ] += 1
            fulltime_schedule.append(
                {
                    "employee_id": employee_id,
                    "day": day,
                    "status": "WORK",
                    "shift_id": pattern.name,
                    "first_start": _clock(pattern.first_start),
                    "first_end": _clock(pattern.first_end),
                    "first_group": first_group + 1,
                    "second_start": _clock(pattern.second_start),
                    "second_end": _clock(pattern.second_end),
                    "second_group": second_group + 1,
                    "cross_group": first_group != second_group,
                }
            )

    parttime_schedule: list[dict] = []
    reconstructed_p = np.zeros_like(p)
    for day in range(10):
        slots = [
            (shift, group)
            for shift in range(len(result.parttime_patterns))
            for group in range(10)
            for _ in range(int(p[day, shift, group]))
        ]
        if len(slots) > result.parttime_staff:
            raise AssertionError("问题三每日兼职槽位超过兼职人员池")
        for employee, (shift, group) in enumerate(slots, start=1):
            pattern = result.parttime_patterns[shift]
            reconstructed_p[day, shift, group] += 1
            parttime_schedule.append(
                {
                    "employee_id": f"P{employee:04d}",
                    "day": day + 1,
                    "shift_id": pattern.name,
                    "shift_start": _clock(pattern.start),
                    "shift_end": _clock(pattern.end),
                    "group": group + 1,
                }
            )

    if not np.array_equal(reconstructed_z, z):
        raise AssertionError("问题三全职员工表无法重构宏观 z")
    if not np.array_equal(reconstructed_p, p):
        raise AssertionError("问题三兼职员工表无法重构宏观 p")
    return Q3RosterResult(
        fulltime_schedule=fulltime_schedule,
        parttime_schedule=parttime_schedule,
        flow_roster=flow,
        reconstructed_z=reconstructed_z,
        reconstructed_p=reconstructed_p,
    )
