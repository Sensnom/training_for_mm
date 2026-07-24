from pathlib import Path
import math

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "paper_output" / "tables" / "q2_employee_schedule.csv"
OUT_DIR = ROOT / "paper_output" / "figures" / "two_stage_visualization"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH)
for col in ["employee", "day"]:
    df[col] = pd.to_numeric(df[col])
for col in ["group", "shift"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial"],
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 9,
    }
)

NAVY = "#17324D"
BLUE = "#0072B2"
SKY = "#56B4E9"
GREEN = "#009E73"
ORANGE = "#E69F00"
VERM = "#D55E00"
PURPLE = "#8E6C8A"
LIGHT_BLUE = "#EAF3F8"
LIGHT_GREEN = "#E9F5EF"
LIGHT_ORANGE = "#FFF3E3"
LIGHT_PURPLE = "#F3ECF4"
GRAY = "#64727F"
LIGHT_GRAY = "#EEF1F3"
GRID = "#D7DEE3"


def rounded_box(ax, xy, width, height, fc, ec, lw=1.6, radius=0.018, zorder=2):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        transform=ax.transAxes,
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def arrow(ax, start, end, color=GRAY, lw=2.0, mutation=13, rad=0.0, zorder=5):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        connectionstyle=f"arc3,rad={rad}",
        transform=ax.transAxes,
        linewidth=lw,
        color=color,
        mutation_scale=mutation,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def save_all(fig, stem):
    # Fixed canvas is intentional: bbox_inches="tight" can misinterpret the
    # transformed connection patches used in the framework diagram.
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, facecolor="white")
    fig.savefig(OUT_DIR / f"{stem}.pdf", facecolor="white")
    fig.savefig(OUT_DIR / f"{stem}.svg", facecolor="white")


def aggregate_day(day):
    work = df[(df["day"] == day) & (df["status"] == "WORK")]
    mat = (
        work.groupby(["group", "shift"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=range(1, 11), fill_value=0)
    )
    return mat


def draw_main_framework():
    day = 8
    quota = aggregate_day(day)
    shifts = list(quota.columns)
    qarr = quota.to_numpy()

    fig = plt.figure(figsize=(13.2, 7.7))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_axis_off()

    ax.text(
        0.5,
        0.955,
        "从“匿名班次”到“具体员工”的两阶段排班求解框架",
        ha="center",
        va="center",
        fontsize=21,
        fontweight="bold",
        color=NAVY,
    )
    ax.text(
        0.5,
        0.918,
        "第一阶段决定每类班次需要多少人；第二阶段在不改变班次配额的前提下回答“具体由谁执行”",
        ha="center",
        va="center",
        fontsize=10.5,
        color=GRAY,
    )

    # Stage backgrounds
    rounded_box(ax, (0.025, 0.18), 0.40, 0.68, LIGHT_BLUE, BLUE, lw=2.2, radius=0.022)
    rounded_box(ax, (0.575, 0.18), 0.40, 0.68, LIGHT_GREEN, GREEN, lw=2.2, radius=0.022)
    rounded_box(ax, (0.447, 0.25), 0.106, 0.55, LIGHT_ORANGE, ORANGE, lw=2.2, radius=0.02)

    ax.text(0.05, 0.825, "阶段 1  宏观匿名排班", fontsize=15.5, fontweight="bold", color=BLUE)
    ax.text(0.05, 0.793, "Mixed-integer linear programming (MILP)", fontsize=8.5, color=GRAY)
    ax.text(0.60, 0.825, "阶段 2  微观员工指派", fontsize=15.5, fontweight="bold", color=GREEN)
    ax.text(0.60, 0.793, "Constraint satisfaction / CP-SAT", fontsize=8.5, color=GRAY)

    # Demand tensor
    rounded_box(ax, (0.05, 0.60), 0.135, 0.145, "white", SKY, lw=1.4)
    for k, alpha in enumerate([0.22, 0.38, 0.56]):
        ax.add_patch(
            Rectangle(
                (0.066 + 0.012 * k, 0.635 + 0.012 * k),
                0.065,
                0.055,
                transform=ax.transAxes,
                facecolor=SKY,
                edgecolor=BLUE,
                alpha=alpha,
                linewidth=1,
                zorder=3,
            )
        )
    ax.text(0.117, 0.716, "需求张量", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    ax.text(0.117, 0.616, r"$D_{g,d,h}$", ha="center", fontsize=12, color=BLUE)
    ax.text(0.117, 0.588, "10组 × 10天 × 11小时", ha="center", fontsize=7.7, color=GRAY)

    # Shift templates
    rounded_box(ax, (0.05, 0.39), 0.135, 0.145, "white", SKY, lw=1.4)
    ax.text(0.117, 0.508, "合法班型库", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    for i, (x0, x1, y) in enumerate([(0.067, 0.108, 0.472), (0.126, 0.168, 0.472)]):
        ax.add_patch(
            Rectangle(
                (x0, y),
                x1 - x0,
                0.018,
                transform=ax.transAxes,
                color=[BLUE, GREEN][i],
                alpha=0.88,
                zorder=3,
            )
        )
    ax.plot([0.063, 0.172], [0.455, 0.455], transform=ax.transAxes, color=GRAY, lw=0.8)
    for j, label in enumerate(["8", "12", "15", "19"]):
        ax.text(0.064 + j * 0.036, 0.437, label, transform=ax.transAxes, fontsize=6.6, ha="center", color=GRAY)
    ax.text(0.117, 0.406, r"$S,\ A_{h,s}$", ha="center", fontsize=10.5, color=BLUE)

    # MILP engine
    rounded_box(ax, (0.215, 0.49), 0.18, 0.25, "white", BLUE, lw=1.7)
    ax.text(0.305, 0.704, "匿名班次优化器", ha="center", fontsize=11.5, fontweight="bold", color=NAVY)
    ax.text(0.305, 0.662, r"$\min\ W$", ha="center", fontsize=12, color=BLUE)
    ax.text(0.305, 0.617, r"$\sum_s A_{h,s}n_{g,d,s}\geq D_{g,d,h}$", ha="center", fontsize=9.6, color=NAVY)
    ax.text(0.305, 0.571, r"$\sum_{g,s}n_{g,d,s}+R_d=W$", ha="center", fontsize=9.6, color=NAVY)
    ax.text(0.305, 0.528, r"$\sum_d R_d=2W$", ha="center", fontsize=9.6, color=NAVY)
    ax.text(0.305, 0.500, "没有员工编号 i", ha="center", fontsize=7.7, color=VERM, fontweight="bold")
    arrow(ax, (0.188, 0.665), (0.215, 0.665), color=BLUE)
    arrow(ax, (0.188, 0.463), (0.215, 0.548), color=BLUE)

    # Actual quota heatmap inset
    hm_ax = fig.add_axes([0.236, 0.235, 0.144, 0.19])
    im = hm_ax.imshow(qarr, cmap="cividis", aspect="auto")
    hm_ax.set_xticks(range(len(shifts)))
    hm_ax.set_xticklabels([f"S{int(s)}" for s in shifts], fontsize=5.7)
    hm_ax.set_yticks(range(10))
    hm_ax.set_yticklabels([f"G{i}" for i in range(1, 11)], fontsize=5.7)
    hm_ax.tick_params(length=0)
    for spine in hm_ax.spines.values():
        spine.set_visible(False)
    hm_ax.set_title(f"输出：第{day}天匿名配额 $n^*_{{g,d,s}}$", fontsize=7.8, color=NAVY, pad=5, fontweight="bold")
    for r in range(qarr.shape[0]):
        for c in range(qarr.shape[1]):
            val = int(qarr[r, c])
            if val:
                hm_ax.text(c, r, str(val), ha="center", va="center", fontsize=5.2, color="white" if val > qarr.max() * 0.42 else NAVY)

    # Bridge / conservation contract
    ax.text(0.50, 0.748, "唯一接口", ha="center", fontsize=12, fontweight="bold", color=VERM)
    ax.text(0.50, 0.710, "班次配额契约", ha="center", fontsize=9.5, color=NAVY)
    ax.text(0.50, 0.624, r"$\sum_i y_{i,g,d,s}$", ha="center", fontsize=12.5, color=VERM)
    ax.text(0.50, 0.580, r"$=\,n^*_{g,d,s}$", ha="center", fontsize=12.5, color=VERM, fontweight="bold")
    ax.text(0.50, 0.505, "数量完全相等", ha="center", fontsize=9, color=NAVY)
    ax.text(0.50, 0.466, "第二阶段不可增删", ha="center", fontsize=8.2, color=GRAY)
    ax.text(0.50, 0.435, "第一阶段的班次", ha="center", fontsize=8.2, color=GRAY)
    ax.text(0.50, 0.322, "聚合解", ha="center", fontsize=8.3, color=BLUE, fontweight="bold")
    ax.text(0.50, 0.291, "→ 可执行解", ha="center", fontsize=8.3, color=GREEN, fontweight="bold")
    arrow(ax, (0.425, 0.53), (0.447, 0.53), color=ORANGE, lw=2.6)
    arrow(ax, (0.553, 0.53), (0.575, 0.53), color=ORANGE, lw=2.6)

    # Stage 2 employee state CSP
    rounded_box(ax, (0.60, 0.59), 0.16, 0.155, "white", GREEN, lw=1.5)
    ax.text(0.68, 0.713, "先分配工作/休息状态", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    # mini work/rest matrix
    state = (
        df.pivot(index="employee", columns="day", values="status")
        .iloc[:10]
        .replace({"REST": 0, "WORK": 1})
        .to_numpy(dtype=int)
    )
    x0, y0, cw, ch = 0.616, 0.618, 0.0115, 0.0075
    for r in range(state.shape[0]):
        for c in range(state.shape[1]):
            ax.add_patch(
                Rectangle(
                    (x0 + c * cw, y0 + (9 - r) * ch),
                    cw * 0.88,
                    ch * 0.82,
                    transform=ax.transAxes,
                    facecolor=GREEN if state[r, c] else "#C8CDD2",
                    edgecolor="none",
                    zorder=3,
                )
            )
    ax.text(0.68, 0.598, r"$\sum_d r_{i,d}=2$", ha="center", fontsize=9.5, color=GREEN)

    # Bipartite matching
    rounded_box(ax, (0.79, 0.59), 0.16, 0.155, "white", GREEN, lw=1.5)
    ax.text(0.87, 0.713, "再匹配匿名班次槽位", ha="center", fontsize=10, fontweight="bold", color=NAVY)
    employee_y = [0.68, 0.652, 0.624]
    slot_y = [0.686, 0.654, 0.618]
    for idx, y in enumerate(employee_y, start=1):
        ax.add_patch(
            Circle(
                (0.815, y),
                0.008,
                transform=ax.transAxes,
                facecolor=GREEN,
                edgecolor="white",
                lw=0.7,
                zorder=3,
            )
        )
        ax.text(0.798, y, f"E{idx}", ha="right", va="center", fontsize=6.5, color=GRAY)
    for idx, y in enumerate(slot_y, start=1):
        ax.add_patch(
            Circle(
                (0.925, y),
                0.008,
                transform=ax.transAxes,
                facecolor=ORANGE,
                edgecolor="white",
                lw=0.7,
                zorder=3,
            )
        )
        ax.text(0.941, y, f"槽{idx}", ha="left", va="center", fontsize=6.5, color=GRAY)
    for ya, yb in zip(employee_y, [slot_y[1], slot_y[2], slot_y[0]]):
        arrow(ax, (0.825, ya), (0.915, yb), color=PURPLE, lw=1.1, mutation=7, rad=0.04)
    ax.text(0.87, 0.598, r"$\sum_i y_{i,g,d,s}=n^*_{g,d,s}$", ha="center", fontsize=8.8, color=GREEN)
    arrow(ax, (0.76, 0.665), (0.79, 0.665), color=GREEN, lw=1.8)

    # Final schedule heatmap
    rounded_box(ax, (0.61, 0.285), 0.33, 0.22, "white", GREEN, lw=1.5)
    ax.text(0.775, 0.474, "输出：员工 × 日期的可执行排班表", ha="center", fontsize=10.5, fontweight="bold", color=NAVY)
    sample = df[df["employee"].between(1, 12)].copy()
    sample["code"] = np.where(sample["status"].eq("REST"), 0, sample["group"])
    sched = sample.pivot(index="employee", columns="day", values="code").to_numpy(dtype=int)
    colors = [
        "#D6DADF",
        "#0072B2",
        "#E69F00",
        "#009E73",
        "#CC79A7",
        "#56B4E9",
        "#D55E00",
        "#8E6C8A",
        "#6E8B3D",
        "#9C755F",
        "#4E79A7",
    ]
    sx0, sy0, scw, sch = 0.646, 0.321, 0.0235, 0.0108
    for r in range(sched.shape[0]):
        for c in range(sched.shape[1]):
            code = int(sched[r, c])
            ax.add_patch(
                Rectangle(
                    (sx0 + c * scw, sy0 + (11 - r) * sch),
                    scw * 0.92,
                    sch * 0.86,
                    transform=ax.transAxes,
                    facecolor=colors[code],
                    edgecolor="white",
                    linewidth=0.25,
                    zorder=3,
                )
            )
            ax.text(
                sx0 + c * scw + scw * 0.46,
                sy0 + (11 - r) * sch + sch * 0.43,
                "休" if code == 0 else str(code),
                ha="center",
                va="center",
                fontsize=4.8,
                color="white" if code != 0 else GRAY,
            )
    for c in range(10):
        ax.text(sx0 + c * scw + scw * 0.46, 0.304, f"D{c+1}", ha="center", fontsize=5.8, color=GRAY)
    ax.text(0.628, 0.385, "E1\n...\nE12", ha="center", va="center", fontsize=6.6, color=GRAY)
    ax.text(0.775, 0.292, "数字表示小组；“休”表示休息日；班型信息同步写入明细表", ha="center", fontsize=7.2, color=GRAY)
    arrow(ax, (0.87, 0.59), (0.82, 0.51), color=GREEN, lw=1.8, rad=0.12)

    # Bottom verification strip
    rounded_box(ax, (0.075, 0.055), 0.85, 0.085, "#F8FAFB", GRID, lw=1.2, radius=0.014)
    checks = [
        ("① 宏观覆盖不变", r"$\sum_s A_{h,s}n^*_{g,d,s}\geq D_{g,d,h}$", BLUE),
        ("② 配额逐类守恒", r"$\sum_i y_{i,g,d,s}=n^*_{g,d,s}$", ORANGE),
        ("③ 个人规则满足", "每天唯一安排；全职做8休2", GREEN),
    ]
    xs = [0.22, 0.50, 0.78]
    for (title, formula, color), x in zip(checks, xs):
        ax.text(x, 0.108, title, ha="center", fontsize=9.3, fontweight="bold", color=color)
        ax.text(x, 0.078, formula, ha="center", fontsize=8.2, color=NAVY)
    ax.text(0.5, 0.018, "图中热图和个人排班示例均取自问题二 406 人员工级排班结果", ha="center", fontsize=7.5, color=GRAY)

    save_all(fig, "fig_two_stage_framework_enhanced")
    plt.close(fig)


def draw_evidence_panels():
    day = 8
    quota = aggregate_day(day)
    shifts = list(quota.columns)
    qarr = quota.to_numpy()

    pivot_status = (
        df.pivot(index="employee", columns="day", values="status")
        .replace({"REST": 0, "WORK": 1})
        .to_numpy(dtype=int)
    )
    sample = df[df["employee"].between(1, 24)].copy()
    sample["code"] = np.where(sample["status"].eq("REST"), 0, sample["group"])
    group_mat = sample.pivot(index="employee", columns="day", values="code").to_numpy(dtype=int)

    fig = plt.figure(figsize=(12.2, 8.1))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.12], width_ratios=[1.03, 0.97], hspace=0.42, wspace=0.25)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    im = ax_a.imshow(qarr, cmap="cividis", aspect="auto")
    ax_a.set_xticks(range(len(shifts)))
    ax_a.set_xticklabels([f"班型 S{int(s)}" for s in shifts], rotation=30, ha="right", fontsize=7)
    ax_a.set_yticks(range(10))
    ax_a.set_yticklabels([f"小组 {i}" for i in range(1, 11)], fontsize=7.5)
    ax_a.set_title(f"A  第一阶段输出：第{day}天匿名班次配额", loc="left", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    for r in range(qarr.shape[0]):
        for c in range(qarr.shape[1]):
            val = int(qarr[r, c])
            if val:
                ax_a.text(c, r, str(val), ha="center", va="center", fontsize=6.5, color="white" if val > qarr.max() * 0.4 else NAVY)
    cbar = fig.colorbar(im, ax=ax_a, fraction=0.046, pad=0.03)
    cbar.set_label("匿名员工数（人）", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    ax_b.imshow(pivot_status, cmap=ListedColormap(["#D5D9DD", GREEN]), aspect="auto", interpolation="nearest")
    ax_b.set_xticks(range(10))
    ax_b.set_xticklabels([f"D{i}" for i in range(1, 11)], fontsize=7)
    ax_b.set_yticks([0, 99, 199, 299, 405])
    ax_b.set_yticklabels(["E1", "E100", "E200", "E300", "E406"], fontsize=7)
    ax_b.set_title("B  第二阶段状态寻优：406 人的工作/休息矩阵", loc="left", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax_b.set_xlabel("展销会日期", fontsize=8.5)
    ax_b.set_ylabel("员工编号", fontsize=8.5)
    ax_b.text(
        0.5,
        -0.16,
        "绿色 = 工作，灰色 = 休息；每一行恰有 2 个灰色单元",
        transform=ax_b.transAxes,
        ha="center",
        fontsize=7.8,
        color=GRAY,
    )

    group_colors = [
        "#D6DADF",
        "#0072B2",
        "#E69F00",
        "#009E73",
        "#CC79A7",
        "#56B4E9",
        "#D55E00",
        "#8E6C8A",
        "#6E8B3D",
        "#9C755F",
        "#4E79A7",
    ]
    ax_c.imshow(group_mat, cmap=ListedColormap(group_colors), vmin=0, vmax=10, aspect="auto", interpolation="nearest")
    ax_c.set_xticks(range(10))
    ax_c.set_xticklabels([f"第{i}天" for i in range(1, 11)], fontsize=8)
    ax_c.set_yticks(range(24))
    ax_c.set_yticklabels([f"E{i}" for i in range(1, 25)], fontsize=6.5)
    ax_c.set_title("C  贪心映射后的具体小组排班（前 24 名员工示例）", loc="left", fontsize=12, fontweight="bold", color=NAVY, pad=10)
    ax_c.set_xlabel("日期", fontsize=8.5)
    ax_c.set_ylabel("员工编号", fontsize=8.5)
    for r in range(group_mat.shape[0]):
        for c in range(group_mat.shape[1]):
            code = int(group_mat[r, c])
            ax_c.text(
                c,
                r,
                "休" if code == 0 else f"G{code}",
                ha="center",
                va="center",
                fontsize=5.7,
                color=GRAY if code == 0 else "white",
                fontweight="bold" if code else "normal",
            )

    for ax in [ax_a, ax_b, ax_c]:
        for spine in ax.spines.values():
            spine.set_color(GRID)
            spine.set_linewidth(0.8)
        ax.tick_params(length=0)

    fig.suptitle(
        "两阶段排班结果的可视化证据链：配额 → 状态 → 具体小组",
        y=0.985,
        fontsize=17,
        fontweight="bold",
        color=NAVY,
    )
    fig.text(
        0.5,
        0.012,
        "匿名配额是两个阶段之间的硬接口；第二阶段只改变“由谁执行”，不改变任何小组—日期—班型的人数。",
        ha="center",
        fontsize=9,
        color=GRAY,
    )
    save_all(fig, "fig_two_stage_evidence_panels")
    plt.close(fig)


if __name__ == "__main__":
    draw_main_framework()
    draw_evidence_panels()
    print(f"Generated figures in: {OUT_DIR}")
