"""Build deterministic publication figures from formal Question 3 outputs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "training_for_mm-matplotlib")
)

from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

from build_q1_q2_figures import (
    BLUE,
    DARK,
    GRAY,
    GRID,
    ORANGE,
    _apply_style,
    _polish_axes,
    _save_figure,
    _select_chinese_font,
)


FIGURE_STEMS = (
    "fig_q3_strict_blind_hour",
    "fig_q3_cross_group_comparison",
    "fig_q3_mixed_staff_composition",
)


def _load_results(output: Path) -> tuple[pd.DataFrame, dict]:
    table_path = output / "tables" / "q3_scenario_comparison.csv"
    json_path = output / "results" / "q3_model_results.json"
    if not table_path.is_file() or not json_path.is_file():
        raise FileNotFoundError("缺少问题三场景比较表或模型结果 JSON")
    table = pd.read_csv(table_path)
    required = {
        "scenario",
        "status",
        "fulltime_staff",
        "parttime_staff",
        "total_staff",
        "allow_cross_group",
    }
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"q3_scenario_comparison.csv 缺少字段：{sorted(missing)}")
    if table["scenario"].tolist() != [f"S{i}" for i in range(8)]:
        raise ValueError("问题三场景必须按 S0--S7 完整排列")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    proof = payload.get("analytic_strict_infeasibility", {})
    if len(proof.get("daily_blind_hour_demand", [])) != 10:
        raise ValueError("问题三 JSON 缺少十日公共盲区需求")
    return table, payload


def _plot_blind_hour(proof: dict, destination: Path) -> list[Path]:
    values = np.asarray(proof["daily_blind_hour_demand"], dtype=int)
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    bars = ax.bar(
        np.arange(10),
        values,
        width=0.64,
        color=ORANGE,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    ax.bar_label(bars, labels=[str(value) for value in values], padding=3, fontsize=8)
    ax.set_xticks(np.arange(10), [f"第{day}天" for day in range(1, 11)])
    ax.set_ylabel("13:00—14:00 需求人数（人）")
    ax.set_ylim(0, values.max() * 1.28)
    ax.text(
        0.02,
        0.95,
        f"严格全职班型覆盖人数恒为0\n十日盲区需求合计：{int(proof['total_blind_hour_demand'])}人次",
        transform=ax.transAxes,
        ha="left",
        va="top",
        color=DARK,
        fontsize=9.2,
        linespacing=1.45,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": GRID},
    )
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[0])


def _plot_cross_group(table: pd.DataFrame, destination: Path) -> list[Path]:
    pairs = (("S2", "S3"), ("S4", "S5"), ("S6", "S7"))
    labels = ["1小时休息", "总人数最优混合", "兼职班次最少优先"]
    allowed = np.array(
        [int(table.loc[table["scenario"] == left, "total_staff"].iloc[0]) for left, _ in pairs]
    )
    forbidden = np.array(
        [int(table.loc[table["scenario"] == right, "total_staff"].iloc[0]) for _, right in pairs]
    )
    if np.any(allowed >= forbidden):
        raise ValueError("问题三跨组允许场景未减少总人数")
    x = np.arange(3)
    width = 0.35
    fig, ax = plt.subplots(figsize=(7.2, 4.4), constrained_layout=True)
    bars_allowed = ax.bar(
        x - width / 2, allowed, width, color=BLUE, label="允许同日跨组", zorder=3
    )
    bars_forbidden = ax.bar(
        x + width / 2, forbidden, width, color=GRAY, label="禁止同日跨组", zorder=3
    )
    ax.bar_label(bars_allowed, padding=3, fontsize=8.5)
    ax.bar_label(bars_forbidden, padding=3, fontsize=8.5)
    for index, saving in enumerate(forbidden - allowed):
        ax.text(
            x[index],
            max(allowed[index], forbidden[index]) + forbidden.max() * 0.055,
            f"节约{saving}人",
            ha="center",
            va="bottom",
            color=ORANGE,
            fontsize=9,
        )
    ax.set_xticks(x, labels)
    ax.set_ylabel("最少总招聘人数（人）")
    ax.set_ylim(0, forbidden.max() * 1.25)
    ax.legend(loc="upper left", ncols=2)
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[1])


def _plot_mixed_composition(table: pd.DataFrame, destination: Path) -> list[Path]:
    scenarios = ["S4", "S5", "S6", "S7"]
    labels = ["总人数最优\n允许跨组", "总人数最优\n禁止跨组", "班次最少\n允许跨组", "班次最少\n禁止跨组"]
    rows = table.set_index("scenario").loc[scenarios]
    fulltime = rows["fulltime_staff"].astype(int).to_numpy()
    parttime = rows["parttime_staff"].astype(int).to_numpy()
    totals = fulltime + parttime
    x = np.arange(4)
    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    ax.bar(x, fulltime, width=0.58, color=BLUE, label="全职员工", zorder=3)
    upper = ax.bar(
        x,
        parttime,
        width=0.58,
        bottom=fulltime,
        color=ORANGE,
        label="兼职员工",
        zorder=3,
    )
    ax.bar_label(upper, labels=[str(value) for value in totals], padding=3, fontsize=9)
    ax.set_xticks(x, labels)
    ax.set_ylabel("招聘人数（人）")
    ax.set_ylim(0, totals.max() * 1.18)
    ax.legend(loc="upper left", ncols=2)
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[2])


def build_q3_figures(output_dir: str | Path) -> list[Path]:
    output = Path(output_dir).expanduser().resolve()
    project = output.parent
    destination = output / "figures" / "q3"
    paper_figures = project / "figures"
    table, payload = _load_results(output)
    _apply_style(_select_chinese_font(project))
    generated: list[Path] = []
    generated.extend(
        _plot_blind_hour(payload["analytic_strict_infeasibility"], destination)
    )
    generated.extend(_plot_cross_group(table, destination))
    generated.extend(_plot_mixed_composition(table, destination))
    paper_figures.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in generated:
        target = paper_figures / source.name
        shutil.copy2(source, target)
        copied.append(target)
    return generated + copied
