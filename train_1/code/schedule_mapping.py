"""Deterministic mapping from anonymous shift slots to concrete employees."""

from __future__ import annotations

import numpy as np

from shift_patterns import ShiftPattern


def _time_fields(pattern: ShiftPattern) -> dict:
    return {
        "first_start": f"{pattern.first_start:02d}:00",
        "first_end": f"{pattern.first_end:02d}:00",
        "second_start": f"{pattern.second_start:02d}:00",
        "second_end": f"{pattern.second_end:02d}:00",
    }


def map_q1_schedule(
    staff: np.ndarray,
    shift_counts: np.ndarray,
    work_status_by_group: list[np.ndarray],
    patterns: list[ShiftPattern],
) -> tuple[list[dict], list[dict]]:
    pattern_map = {pattern.index: pattern for pattern in patterns}
    schedule: list[dict] = []
    day_status: list[dict] = []
    employee_offset = 0
    for group in range(10):
        group_staff = int(staff[group])
        status = work_status_by_group[group]
        if status.shape != (group_staff, 10):
            raise ValueError("问题一工作状态矩阵维度不匹配")
        assignments: dict[tuple[int, int], int] = {}
        for day in range(10):
            workers = [i + 1 for i in range(group_staff) if status[i, day]]
            slots = [
                shift + 1
                for shift in range(10)
                for _ in range(int(shift_counts[day, group, shift]))
            ]
            if len(workers) != len(slots):
                raise AssertionError("问题一工作员工数与匿名班次槽位数不一致")
            for group_employee, shift in zip(workers, slots, strict=True):
                assignments[(group_employee, day + 1)] = shift

        for group_employee in range(1, group_staff + 1):
            employee = employee_offset + group_employee
            for day in range(1, 11):
                is_work = bool(status[group_employee - 1, day - 1])
                day_status.append(
                    {
                        "employee": employee,
                        "group_employee": group_employee,
                        "fixed_group": group + 1,
                        "day": day,
                        "status": "WORK" if is_work else "REST",
                    }
                )
                if is_work:
                    shift = assignments[(group_employee, day)]
                    pattern = pattern_map[shift]
                    schedule.append(
                        {
                            "employee": employee,
                            "group_employee": group_employee,
                            "fixed_group": group + 1,
                            "day": day,
                            "status": "WORK",
                            "shift": shift,
                            **_time_fields(pattern),
                        }
                    )
                else:
                    schedule.append(
                        {
                            "employee": employee,
                            "group_employee": group_employee,
                            "fixed_group": group + 1,
                            "day": day,
                            "status": "REST",
                            "shift": "",
                            "first_start": "",
                            "first_end": "",
                            "second_start": "",
                            "second_end": "",
                        }
                    )
        employee_offset += group_staff
    return schedule, day_status


def map_q2_schedule(
    staff: int,
    shift_counts: np.ndarray,
    work_status: np.ndarray,
    patterns: list[ShiftPattern],
) -> tuple[list[dict], list[dict]]:
    pattern_map = {pattern.index: pattern for pattern in patterns}
    assignments: dict[tuple[int, int], tuple[int, int]] = {}
    for day in range(10):
        workers = [i + 1 for i in range(staff) if work_status[i, day]]
        slots = [
            (group + 1, shift + 1)
            for group in range(10)
            for shift in range(10)
            for _ in range(int(shift_counts[day, group, shift]))
        ]
        if len(workers) != len(slots):
            raise AssertionError("问题二工作员工数与匿名班次槽位数不一致")
        for employee, slot in zip(workers, slots, strict=True):
            assignments[(employee, day + 1)] = slot

    schedule: list[dict] = []
    day_status: list[dict] = []
    for employee in range(1, staff + 1):
        for day in range(1, 11):
            is_work = bool(work_status[employee - 1, day - 1])
            day_status.append(
                {
                    "employee": employee,
                    "day": day,
                    "status": "WORK" if is_work else "REST",
                }
            )
            if is_work:
                group, shift = assignments[(employee, day)]
                schedule.append(
                    {
                        "employee": employee,
                        "day": day,
                        "status": "WORK",
                        "group": group,
                        "shift": shift,
                        **_time_fields(pattern_map[shift]),
                    }
                )
            else:
                schedule.append(
                    {
                        "employee": employee,
                        "day": day,
                        "status": "REST",
                        "group": "",
                        "shift": "",
                        "first_start": "",
                        "first_end": "",
                        "second_start": "",
                        "second_end": "",
                    }
                )
    return schedule, day_status

