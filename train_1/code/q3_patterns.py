"""Question 3 shift-pattern generation and analytic blind-zone proof."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


OPENING_HOUR = 8
CLOSING_HOUR = 19
BLOCK_HOURS = 4
BLIND_HOUR = 13


@dataclass(frozen=True)
class Q3FulltimePattern:
    index: int
    first_start: int
    first_end: int
    second_start: int
    second_end: int
    minimum_break_hours: int

    @property
    def name(self) -> str:
        return f"F{self.index}"

    def as_dict(self) -> dict:
        return {
            "shift_id": self.name,
            "first_start": f"{self.first_start:02d}:00",
            "first_end": f"{self.first_end:02d}:00",
            "second_start": f"{self.second_start:02d}:00",
            "second_end": f"{self.second_end:02d}:00",
            "minimum_break_hours": self.minimum_break_hours,
        }


@dataclass(frozen=True)
class Q3ParttimePattern:
    index: int
    start: int
    end: int

    @property
    def name(self) -> str:
        return f"P{self.index}"

    def as_dict(self) -> dict:
        return {
            "shift_id": self.name,
            "shift_start": f"{self.start:02d}:00",
            "shift_end": f"{self.end:02d}:00",
        }


def generate_fulltime_patterns(
    minimum_break_hours: int,
) -> list[Q3FulltimePattern]:
    if minimum_break_hours not in (1, 2):
        raise ValueError("问题三全职最小休息时长只能为 1 或 2 小时")
    pairs: list[tuple[int, int]] = []
    latest_start = CLOSING_HOUR - BLOCK_HOURS
    for first_start in range(OPENING_HOUR, latest_start + 1):
        earliest_second = first_start + BLOCK_HOURS + minimum_break_hours
        for second_start in range(earliest_second, latest_start + 1):
            pairs.append((first_start, second_start))
    return [
        Q3FulltimePattern(
            index=index,
            first_start=first,
            first_end=first + BLOCK_HOURS,
            second_start=second,
            second_end=second + BLOCK_HOURS,
            minimum_break_hours=minimum_break_hours,
        )
        for index, (first, second) in enumerate(pairs, start=1)
    ]


def generate_parttime_patterns() -> list[Q3ParttimePattern]:
    """Enumerate all four-hour shifts that cover 13:00--14:00."""

    starts = [
        start
        for start in range(OPENING_HOUR, CLOSING_HOUR - BLOCK_HOURS + 1)
        if start <= BLIND_HOUR < start + BLOCK_HOURS
    ]
    return [
        Q3ParttimePattern(index=index, start=start, end=start + BLOCK_HOURS)
        for index, start in enumerate(starts, start=1)
    ]


def build_fulltime_coverage(
    patterns: list[Q3FulltimePattern],
) -> np.ndarray:
    coverage = np.zeros(
        (CLOSING_HOUR - OPENING_HOUR, len(patterns)), dtype=np.int64
    )
    for column, pattern in enumerate(patterns):
        coverage[
            pattern.first_start - OPENING_HOUR : pattern.first_end - OPENING_HOUR,
            column,
        ] = 1
        coverage[
            pattern.second_start - OPENING_HOUR : pattern.second_end - OPENING_HOUR,
            column,
        ] = 1
    if not np.all(coverage.sum(axis=0) == 2 * BLOCK_HOURS):
        raise AssertionError("每个问题三全职班型必须覆盖 8 小时")
    return coverage


def build_parttime_coverage(
    patterns: list[Q3ParttimePattern],
) -> np.ndarray:
    coverage = np.zeros(
        (CLOSING_HOUR - OPENING_HOUR, len(patterns)), dtype=np.int64
    )
    for column, pattern in enumerate(patterns):
        coverage[
            pattern.start - OPENING_HOUR : pattern.end - OPENING_HOUR,
            column,
        ] = 1
    if not np.all(coverage.sum(axis=0) == BLOCK_HOURS):
        raise AssertionError("每个问题三兼职班型必须覆盖 4 小时")
    return coverage


def blind_zone_proof(
    demand: np.ndarray, patterns: list[Q3FulltimePattern]
) -> dict:
    demand = np.asarray(demand, dtype=np.int64)
    if demand.shape != (10, 11, 10):
        raise ValueError("需求张量必须为 (10, 11, 10)")
    coverage = build_fulltime_coverage(patterns)
    blind_index = BLIND_HOUR - OPENING_HOUR
    daily = demand[:, blind_index, :].sum(axis=1)
    all_zero = bool(np.all(coverage[blind_index, :] == 0))
    return {
        "status": "PROVED_INFEASIBLE" if all_zero and np.all(daily > 0) else "NOT_PROVED",
        "blind_hour_start": f"{BLIND_HOUR:02d}:00",
        "blind_hour_end": f"{BLIND_HOUR + 1:02d}:00",
        "all_patterns_zero_at_blind_hour": all_zero,
        "positive_demand_in_all_groups_and_days": bool(
            np.all(demand[:, blind_index, :] > 0)
        ),
        "daily_blind_hour_demand": [int(value) for value in daily],
        "total_blind_hour_demand": int(daily.sum()),
    }
