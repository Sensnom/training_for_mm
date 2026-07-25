"""Build publication figures for Questions 1 and 2 from verified results."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
import warnings

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "training_for_mm-matplotlib")
)

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd


FORMATS = ("png", "pdf", "svg")
FIGURE_STEMS = (
    "fig_q1_group_staff",
    "fig_q2_daily_lower_actual",
    "fig_q1_q2_staff_comparison",
)
FONT_CANDIDATES = (
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "Microsoft YaHei",
    "SimHei",
)

BLUE = "#3B6FB6"
GRAY = "#B8BEC7"
ORANGE = "#D9772B"
DARK = "#28323C"
GRID = "#E5E7EB"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"缺少结果文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法解析 JSON 结果文件：{path}") from exc


def _read_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"缺少结果文件：{path}")
    table = pd.read_csv(path)
    missing = required_columns.difference(table.columns)
    if missing:
        raise ValueError(f"{path.name} 缺少字段：{sorted(missing)}")
    return table


def _require_integer_series(series: pd.Series, field: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise")
    if values.isna().any() or not np.allclose(values, np.rint(values)):
        raise ValueError(f"字段 {field} 必须全部为整数")
    return values.astype(int)


def load_summary_results(output_dir: str | Path) -> tuple[dict, dict]:
    """Load the two authoritative summary JSON files."""

    results = Path(output_dir) / "results"
    q1 = _read_json(results / "q1_model_results.json")
    q2 = _read_json(results / "q2_model_results.json")
    for name, data, fields in (
        ("q1_model_results.json", q1, {"total_staff", "group_staff"}),
        (
            "q2_model_results.json",
            q2,
            {
                "total_staff",
                "daily_lower_bound_total",
                "actual_workdays",
                "redundancy_day",
                "redundant_workdays",
            },
        ),
    ):
        missing = fields.difference(data)
        if missing:
            raise ValueError(f"{name} 缺少字段：{sorted(missing)}")
    return q1, q2


def load_q1_group_results(output_dir: str | Path) -> tuple[pd.DataFrame, dict]:
    """Load and cross-check the ten Question 1 group staff values."""

    output = Path(output_dir)
    table = _read_csv(
        output / "tables" / "q1_group_results.csv",
        {"group", "optimal_staff"},
    ).copy()
    q1, _ = load_summary_results(output)
    table["group"] = _require_integer_series(table["group"], "group")
    table["optimal_staff"] = _require_integer_series(
        table["optimal_staff"], "optimal_staff"
    )
    table = table.sort_values("group").reset_index(drop=True)

    expected_groups = list(range(1, len(q1["group_staff"]) + 1))
    if table["group"].tolist() != expected_groups or len(table) != 10:
        raise ValueError("问题一小组编号必须完整且恰为第1组至第10组")
    json_staff = [int(value) for value in q1["group_staff"]]
    if table["optimal_staff"].tolist() != json_staff:
        raise ValueError("问题一 CSV 与 JSON 的各组最优编制不一致")
    csv_total = int(table["optimal_staff"].sum())
    if csv_total != int(q1["total_staff"]):
        raise ValueError(
            f"问题一各组人数总和 {csv_total} 与 total_staff "
            f"{q1['total_staff']} 不一致"
        )
    return table, q1


def load_q2_daily_results(output_dir: str | Path) -> tuple[pd.DataFrame, dict]:
    """Load and cross-check Question 2 daily lower and actual staffing."""

    output = Path(output_dir)
    lower = _read_csv(
        output / "tables" / "q2_daily_lower_bound.csv",
        {"day", "minimum_workers"},
    ).copy()
    actual = _read_csv(
        output / "tables" / "q2_daily_actual.csv",
        {"day", "minimum_workers", "actual_workers", "redundant_workers"},
    ).copy()
    _, q2 = load_summary_results(output)

    for table in (lower, actual):
        table["day"] = _require_integer_series(table["day"], "day")
        table.sort_values("day", inplace=True)
        table.reset_index(drop=True, inplace=True)
        if table["day"].tolist() != list(range(1, 11)):
            raise ValueError("问题二日期编号必须完整且恰为第1天至第10天")
    for field in ("minimum_workers",):
        lower[field] = _require_integer_series(lower[field], field)
    for field in ("minimum_workers", "actual_workers", "redundant_workers"):
        actual[field] = _require_integer_series(actual[field], field)

    if lower["minimum_workers"].tolist() != actual["minimum_workers"].tolist():
        raise ValueError("问题二两张逐日表中的最低人数不一致")
    if lower["minimum_workers"].tolist() != [
        int(value) for value in q2.get("daily_lower_bound", [])
    ]:
        raise ValueError("问题二逐日下界 CSV 与 JSON 不一致")
    if actual["actual_workers"].tolist() != [
        int(value) for value in q2.get("actual_daily_workers", [])
    ]:
        raise ValueError("问题二实际人数 CSV 与 JSON 不一致")

    difference = actual["actual_workers"] - lower["minimum_workers"]
    if not difference.equals(actual["redundant_workers"]):
        raise ValueError("问题二冗余人数列与实际值减下界不一致")
    difference_days = actual.loc[difference.ne(0), "day"].tolist()
    expected_day = int(q2["redundancy_day"])
    if difference_days != [expected_day]:
        raise ValueError(
            f"问题二仅允许第 {expected_day} 天存在人数差异，"
            f"实际差异日期为 {difference_days}"
        )
    if int(difference.sum()) != int(q2["redundant_workdays"]):
        raise ValueError("问题二逐日差异总和与 redundant_workdays 不一致")

    lower_total = int(lower["minimum_workers"].sum())
    actual_total = int(actual["actual_workers"].sum())
    if lower_total != int(q2["daily_lower_bound_total"]):
        raise ValueError("问题二逐日下界总和与 JSON 不一致")
    if actual_total != int(q2["actual_workdays"]):
        raise ValueError("问题二实际工作人日总和与 JSON 不一致")
    if actual_total != int(q2["total_staff"]) * 8:
        raise ValueError("问题二实际工作人日不等于总招聘人数乘以8")

    merged = lower[["day", "minimum_workers"]].copy()
    merged["actual_workers"] = actual["actual_workers"]
    merged["redundant_workers"] = difference
    return merged, q2


def _select_chinese_font(project_dir: str | Path) -> str | None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in FONT_CANDIDATES:
        if candidate in available:
            return candidate
    requested_font = (
        Path(project_dir) / "assets" / "fonts" / "NotoSansHans-Regular.otf"
    )
    module_font = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "fonts"
        / "NotoSansHans-Regular.otf"
    )
    bundled_font = requested_font if requested_font.is_file() else module_font
    if bundled_font.is_file():
        font_manager.fontManager.addfont(bundled_font)
        bundled_name = font_manager.FontProperties(fname=bundled_font).get_name()
        warnings.warn(
            "未检测到首选系统中文字体，已使用项目内置 Noto Sans Hans。",
            RuntimeWarning,
            stacklevel=2,
        )
        return bundled_name
    warnings.warn(
        "未检测到 Source Han Sans SC、Noto Sans CJK SC、Microsoft YaHei "
        "或 SimHei；中文可能无法正常显示。",
        RuntimeWarning,
        stacklevel=2,
    )
    return None


def _apply_style(font_name: str | None) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [font_name] if font_name else ["DejaVu Sans"],
            "axes.unicode_minus": False,
            "axes.edgecolor": DARK,
            "axes.labelcolor": DARK,
            "axes.linewidth": 0.8,
            "axes.titlesize": 12,
            "axes.titleweight": "semibold",
            "axes.labelsize": 10,
            "xtick.color": DARK,
            "ytick.color": DARK,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "svg.fonttype": "path",
            "svg.hashsalt": "training_for_mm_q1_q2",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _polish_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=3, width=0.8)


def _atomic_save(fig, target: Path, suffix: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "Creator": "training_for_mm",
        "Title": target.stem,
        "CreationDate": None,
        "ModDate": None,
    }
    with tempfile.NamedTemporaryFile(
        prefix=f".{target.stem}-", suffix=f".{suffix}", dir=target.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        save_kwargs = {
            "format": suffix,
            "bbox_inches": "tight",
            "pad_inches": 0.08,
        }
        if suffix == "png":
            save_kwargs.update(dpi=300, metadata={"Software": "training_for_mm"})
        elif suffix == "pdf":
            save_kwargs.update(metadata=metadata)
        elif suffix == "svg":
            save_kwargs.update(
                metadata={
                    "Creator": "training_for_mm",
                    "Date": "1970-01-01T00:00:00",
                }
            )
        fig.savefig(temporary, **save_kwargs)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _save_figure(fig, destination: Path, stem: str) -> list[Path]:
    paths: list[Path] = []
    try:
        for suffix in FORMATS:
            target = destination / f"{stem}.{suffix}"
            _atomic_save(fig, target, suffix)
            paths.append(target)
    finally:
        plt.close(fig)
    return paths


def plot_q1_group_staff(
    table: pd.DataFrame, summary: dict, destination: str | Path
) -> list[Path]:
    """Plot optimal fixed staffing for the ten Question 1 groups."""

    destination = Path(destination)
    values = table["optimal_staff"].to_numpy(dtype=int)
    groups = table["group"].to_numpy(dtype=int)
    maximum = int(values.max())
    colors = [ORANGE if value == maximum else BLUE for value in values]

    fig, ax = plt.subplots(figsize=(7.2, 4.3), constrained_layout=True)
    bars = ax.bar(
        np.arange(len(groups)),
        values,
        width=0.66,
        color=colors,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    ax.bar_label(bars, labels=[str(value) for value in values], padding=3, fontsize=8.5)
    average = float(values.mean())
    ax.axhline(
        average,
        color=DARK,
        linewidth=1.0,
        linestyle=(0, (4, 3)),
        label=f"平均每组 {average:.1f} 人",
    )
    ax.set_xticks(np.arange(len(groups)), [f"第{group}组" for group in groups])
    ax.set_ylabel("最少招聘人数（人）")
    ax.set_ylim(0, maximum * 1.26)
    ax.text(
        0.02,
        0.94,
        f"总招聘人数：{int(summary['total_staff'])}人",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        color=DARK,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": GRID},
    )
    ax.legend(loc="upper right")
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[0])


def plot_q2_daily_lower_actual(
    table: pd.DataFrame, summary: dict, destination: str | Path
) -> list[Path]:
    """Plot Question 2 daily lower bounds against actual worker counts."""

    destination = Path(destination)
    days = table["day"].to_numpy(dtype=int)
    lower = table["minimum_workers"].to_numpy(dtype=int)
    actual = table["actual_workers"].to_numpy(dtype=int)
    difference = actual - lower
    changed_index = int(np.flatnonzero(difference)[0])

    fig, ax = plt.subplots(figsize=(7.4, 4.5), constrained_layout=True)
    x = np.arange(len(days))
    width = 0.36
    lower_bars = ax.bar(
        x - width / 2,
        lower,
        width,
        label="逐日最低人数",
        color=GRAY,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    actual_colors = [ORANGE if value else BLUE for value in difference]
    actual_bars = ax.bar(
        x + width / 2,
        actual,
        width,
        label="实际工作人数",
        color=actual_colors,
        edgecolor="white",
        linewidth=0.5,
        zorder=3,
    )
    ax.set_xticks(x, [f"第{day}天" for day in days])
    ax.set_ylabel("工作人数（人）")
    ax.set_ylim(0, max(actual) * 1.30)
    ax.legend(loc="upper left", ncols=2)
    ax.text(
        0.98,
        0.96,
        f"逐日下界总和：{int(summary['daily_lower_bound_total'])}\n"
        f"实际工作人日：{int(summary['actual_workdays'])}"
        f" = {int(summary['total_staff'])} × 8",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9.2,
        linespacing=1.5,
        color=DARK,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": GRID},
    )
    target_bar = actual_bars[changed_index]
    ax.annotate(
        f"第{days[changed_index]}天增加{difference[changed_index]}个工作人日",
        xy=(
            target_bar.get_x() + target_bar.get_width() / 2,
            target_bar.get_height(),
        ),
        xytext=(0, 25),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=9,
        color=ORANGE,
        arrowprops={"arrowstyle": "-|>", "color": ORANGE, "lw": 1.0},
    )
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[1])


def plot_q1_q2_staff_comparison(
    q1_summary: dict, q2_summary: dict, destination: str | Path
) -> list[Path]:
    """Plot minimum staff totals for Questions 1 and 2."""

    destination = Path(destination)
    q1_total = int(q1_summary["total_staff"])
    q2_total = int(q2_summary["total_staff"])
    difference = q1_total - q2_total
    if difference <= 0:
        raise ValueError("问题二最少招聘人数必须少于问题一")
    ratio = difference / q1_total

    fig, ax = plt.subplots(figsize=(5.4, 4.4), constrained_layout=True)
    x = np.arange(2)
    values = [q1_total, q2_total]
    bars = ax.bar(
        x,
        values,
        width=0.52,
        color=[BLUE, ORANGE],
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    ax.bar_label(bars, labels=[str(value) for value in values], padding=4, fontsize=10)
    ax.set_xticks(x, ["问题一", "问题二"])
    ax.set_ylabel("最少招聘人数（人）")
    bracket_y = max(values) * 1.10
    bracket_drop = max(values) * 0.018
    ax.plot(
        [x[0], x[0], x[1], x[1]],
        [bracket_y - bracket_drop, bracket_y, bracket_y, bracket_y - bracket_drop],
        color=DARK,
        linewidth=1.0,
        clip_on=False,
    )
    ax.text(
        x.mean(),
        bracket_y + max(values) * 0.018,
        f"减少{difference}人，降幅{ratio:.2%}",
        ha="center",
        va="bottom",
        fontsize=10,
        color=DARK,
    )
    ax.set_ylim(0, max(values) * 1.24)
    _polish_axes(ax)
    return _save_figure(fig, destination, FIGURE_STEMS[2])


def build_all_figures(
    project_dir: str | Path, output_dir: str | Path
) -> list[Path]:
    """Validate inputs, build all main figures, and publish paper copies."""

    project = Path(project_dir).expanduser().resolve()
    output = Path(output_dir).expanduser().resolve()
    figure_output = output / "figures" / "q1_q2"
    paper_figures = project / "figures"

    q1_table, q1_summary = load_q1_group_results(output)
    q2_table, q2_summary = load_q2_daily_results(output)
    summary_q1, summary_q2 = load_summary_results(output)
    if q1_summary != summary_q1 or q2_summary != summary_q2:
        raise ValueError("绘图数据加载过程中汇总结果发生不一致")

    _apply_style(_select_chinese_font(project))
    generated: list[Path] = []
    generated.extend(plot_q1_group_staff(q1_table, q1_summary, figure_output))
    generated.extend(
        plot_q2_daily_lower_actual(q2_table, q2_summary, figure_output)
    )
    generated.extend(
        plot_q1_q2_staff_comparison(q1_summary, q2_summary, figure_output)
    )

    paper_figures.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in generated:
        target = paper_figures / source.name
        shutil.copy2(source, target)
        copied.append(target)
    return generated + copied


def build_parser() -> argparse.ArgumentParser:
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="从问题一、问题二核验结果生成论文图"
    )
    parser.add_argument("--project-dir", type=Path, default=project_dir)
    parser.add_argument(
        "--output-dir", type=Path, default=project_dir / "paper_output"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = build_all_figures(args.project_dir, args.output_dir)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
