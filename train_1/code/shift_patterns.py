"""Generate legal two-block shifts for Questions 1 and 2."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


OPENING_HOUR = 8
CLOSING_HOUR = 19
BLOCK_HOURS = 4


@dataclass(frozen=True)
class ShiftPattern:
    index: int
    first_start: int
    first_end: int
    second_start: int
    second_end: int

    @property
    def name(self) -> str:
        return f"S{self.index}"

    def as_dict(self) -> dict:
        return {
            "shift": self.index,
            "shift_name": self.name,
            "first_start": f"{self.first_start:02d}:00",
            "first_end": f"{self.first_end:02d}:00",
            "second_start": f"{self.second_start:02d}:00",
            "second_end": f"{self.second_end:02d}:00",
        }


def generate_shift_patterns() -> list[ShiftPattern]:
    """Enumerate all ordered, non-overlapping 4h+4h shifts."""

    pairs: list[tuple[int, int]] = []
    latest_start = CLOSING_HOUR - BLOCK_HOURS
    for first_start in range(OPENING_HOUR, latest_start + 1):
        first_end = first_start + BLOCK_HOURS
        for second_start in range(first_end, latest_start + 1):
            pairs.append((first_start, second_start))
    return [
        ShiftPattern(
            index=i,
            first_start=first_start,
            first_end=first_start + BLOCK_HOURS,
            second_start=second_start,
            second_end=second_start + BLOCK_HOURS,
        )
        for i, (first_start, second_start) in enumerate(pairs, start=1)
    ]


def build_coverage(patterns: list[ShiftPattern]) -> np.ndarray:
    coverage = np.zeros((CLOSING_HOUR - OPENING_HOUR, len(patterns)), dtype=np.int64)
    for column, pattern in enumerate(patterns):
        for hour in range(pattern.first_start, pattern.first_end):
            coverage[hour - OPENING_HOUR, column] = 1
        for hour in range(pattern.second_start, pattern.second_end):
            coverage[hour - OPENING_HOUR, column] = 1
    if coverage.shape != (11, 10):
        raise AssertionError(f"合法班型覆盖矩阵维度异常：{coverage.shape}")
    if not np.all(coverage.sum(axis=0) == 8):
        raise AssertionError("每个班型必须恰好覆盖 8 个小时单元")
    return coverage

