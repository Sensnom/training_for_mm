"""Strict loader for the exhibition staffing demand workbook."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re

import numpy as np
import pandas as pd


EXPECTED_DAYS = tuple(range(1, 11))
EXPECTED_START_HOURS = tuple(range(8, 19))
EXPECTED_GROUP_COLUMNS = tuple(f"小组{i}" for i in range(1, 11))
HOUR_PATTERN = re.compile(
    r"^\s*(\d{1,2}):00\s*[-–—]\s*(\d{1,2}):00\s*$"
)


@dataclass(frozen=True)
class DemandData:
    demand: np.ndarray
    days: tuple[int, ...]
    hour_labels: tuple[str, ...]
    group_labels: tuple[str, ...]
    source_path: str
    source_sha256: str

    def validation_summary(self) -> dict:
        return {
            "status": "VALID",
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "shape": list(self.demand.shape),
            "size": int(self.demand.size),
            "dtype": str(self.demand.dtype),
            "days": list(self.days),
            "hour_labels": list(self.hour_labels),
            "group_labels": list(self.group_labels),
            "minimum_demand": int(self.demand.min()),
            "maximum_demand": int(self.demand.max()),
            "total_person_hours": int(self.demand.sum()),
            "missing_value_count": 0,
            "duplicate_day_hour_count": 0,
        }


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_hour(value: object, row_number: int) -> tuple[int, str]:
    text = str(value).strip()
    match = HOUR_PATTERN.fullmatch(text)
    if not match:
        raise ValueError(
            f"第 {row_number} 行小时段 {text!r} 不符合 HH:00-HH:00 格式"
        )
    start, end = (int(match.group(1)), int(match.group(2)))
    if end != start + 1 or start not in EXPECTED_START_HOURS:
        raise ValueError(f"第 {row_number} 行小时段 {text!r} 不在 08:00--19:00")
    return start, f"{start:02d}:00-{end:02d}:00"


def load_demand(path: str | Path) -> DemandData:
    """Read and validate the 10×11×10 demand tensor.

    The workbook must contain one title row followed by a header row with
    ``天``, ``小时`` and ``小组1`` through ``小组10``.
    """

    source = Path(path).expanduser().resolve()
    if source.suffix.lower() != ".xlsx":
        raise ValueError(f"需求文件必须为 .xlsx，实际为 {source.suffix or '<无扩展名>'}")
    if not source.is_file():
        raise FileNotFoundError(f"找不到需求文件：{source}")

    try:
        frame = pd.read_excel(source, sheet_name=0, header=1, engine="openpyxl")
    except Exception as exc:
        raise ValueError(f"无法读取 Excel 需求文件 {source}: {exc}") from exc

    expected_columns = ("天", "小时", *EXPECTED_GROUP_COLUMNS)
    actual_columns = tuple(str(c).strip() for c in frame.columns)
    if actual_columns != expected_columns:
        raise ValueError(
            "Excel 列名不匹配；"
            f"期望 {expected_columns}，实际 {actual_columns}"
        )
    if len(frame) != 110:
        raise ValueError(f"需求记录必须恰有 110 行，实际 {len(frame)} 行")
    if frame.isna().any().any():
        locations = np.argwhere(frame.isna().to_numpy())
        first_row, first_col = locations[0]
        raise ValueError(
            f"需求数据存在缺失值：Excel 第 {int(first_row) + 3} 行，"
            f"列 {frame.columns[int(first_col)]}"
        )

    records: list[tuple[int, int, np.ndarray]] = []
    seen: set[tuple[int, int]] = set()
    for offset, row in frame.iterrows():
        row_number = int(offset) + 3
        day_value = row["天"]
        if isinstance(day_value, bool) or not float(day_value).is_integer():
            raise ValueError(f"第 {row_number} 行日期必须为整数，实际 {day_value!r}")
        day = int(day_value)
        if day not in EXPECTED_DAYS:
            raise ValueError(f"第 {row_number} 行日期 {day} 不在 1..10")

        start_hour, _ = _parse_hour(row["小时"], row_number)
        key = (day, start_hour)
        if key in seen:
            raise ValueError(f"日期 {day}、{start_hour:02d}:00 存在重复记录")
        seen.add(key)

        raw_values = row[list(EXPECTED_GROUP_COLUMNS)].to_numpy()
        try:
            numeric = np.asarray(raw_values, dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {row_number} 行包含非数值需求") from exc
        if not np.all(np.isfinite(numeric)):
            raise ValueError(f"第 {row_number} 行包含非有限需求值")
        if not np.all(numeric == np.floor(numeric)):
            raise ValueError(f"第 {row_number} 行需求人数包含小数")
        values = numeric.astype(np.int64)
        if np.any(values <= 0):
            raise ValueError(f"第 {row_number} 行需求人数必须全部为正整数")
        records.append((day, start_hour, values))

    expected_keys = {
        (day, hour) for day in EXPECTED_DAYS for hour in EXPECTED_START_HOURS
    }
    missing = sorted(expected_keys - seen)
    extra = sorted(seen - expected_keys)
    if missing or extra:
        raise ValueError(f"日期—小时组合不完整：缺失 {missing}，额外 {extra}")

    demand = np.empty((10, 11, 10), dtype=np.int64)
    for day, start_hour, values in records:
        demand[day - 1, start_hour - 8, :] = values

    assert demand.shape == (10, 11, 10)
    assert demand.size == 1100
    assert np.issubdtype(demand.dtype, np.integer)
    assert np.all(demand > 0)
    hour_labels = tuple(f"{h:02d}:00-{h + 1:02d}:00" for h in EXPECTED_START_HOURS)
    return DemandData(
        demand=demand,
        days=EXPECTED_DAYS,
        hour_labels=hour_labels,
        group_labels=EXPECTED_GROUP_COLUMNS,
        source_path=str(source),
        source_sha256=_hash_file(source),
    )

