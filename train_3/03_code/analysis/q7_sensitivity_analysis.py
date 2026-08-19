#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第7题解析敏感性分析与论文图表生成。

只使用已经锁定的解析事件公式，不修改Q1-Q4正式求解内核。
输出：delta/方向/边界语义/成本效率/p(N)/解析下界Pareto数据及SVG/PNG图。
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "04_results" / "sensitivity"
FIGURES = ROOT / "05_figures"
RESULTS.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

# 固定正式参数
L = 10000.0
DELTA0 = 1.8
LA = 5000.0
RA = 30.0
RB = 200.0
CA_DENSITY = 1.05
CB_DENSITY = 0.05

VA_UM3 = math.pi * (RA / 1000.0) ** 2 * (LA / 1000.0)
VB_UM3 = 4.0 / 3.0 * math.pi * (RB / 1000.0) ** 3
CA = CA_DENSITY * VA_UM3
CB = CB_DENSITY * VB_UM3
P_A_ISO = LA / (2.0 * L) + math.pi * RA / (2.0 * L)
P_B = 2.0 * RB / L

plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def lower_self(na: int, nb: int, p_a: float = P_A_ISO, p_b: float = P_B) -> float:
    return 1.0 - (1.0 - p_a) ** na * (1.0 - p_b) ** nb


def necessary_upper(na: int, nb: int, delta: float, p_a: float = P_A_ISO, p_b: float = P_B) -> float:
    """直接跨界或左右电极锚点必要事件的概率上界。"""
    pe = delta / L
    return (
        1.0
        - 2.0 * (1.0 - p_a - pe) ** na * (1.0 - p_b - pe) ** nb
        + (1.0 - p_a - 2.0 * pe) ** na * (1.0 - p_b - 2.0 * pe) ** nb
    )


def n_for_target(p: float, target: float = 0.90) -> int:
    return math.ceil(math.log(1.0 - target) / math.log(1.0 - p))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def savefig(fig, stem: str) -> None:
    fig.savefig(FIGURES / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def build_delta() -> list[dict]:
    deltas = [0.0, 0.9, 1.8, 3.6, 5.4, 9.0]
    frontier = [(0, 56), (1, 48), (2, 39), (3, 30), (4, 21), (5, 12), (6, 3)]
    rows = []
    for d in deltas:
        all_frontier = [((na, nb), necessary_upper(na, nb, d)) for na, nb in frontier]
        strongest = max(all_frontier, key=lambda x: x[1])
        rows.append({
            "delta_nm": d,
            "U7": necessary_upper(7, 0, d),
            "L8_direct": lower_self(8, 0),
            "U8": necessary_upper(8, 0, d),
            "U_0_56": necessary_upper(0, 56, d),
            "L_0_57_direct": lower_self(0, 57),
            "U_0_57": necessary_upper(0, 57, d),
            "strongest_cheaper_NA": strongest[0][0],
            "strongest_cheaper_NB": strongest[0][1],
            "strongest_cheaper_upper": strongest[1],
        })
    write_csv(
        RESULTS / "q7_delta_sensitivity.csv",
        list(rows[0].keys()), rows
    )

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    xs = [r["delta_nm"] for r in rows]
    ax.plot(xs, [r["U7"] for r in rows], marker="o", label=r"$U_7$")
    ax.plot(xs, [r["U8"] for r in rows], marker="s", label=r"$U_8$")
    ax.plot(xs, [r["U_0_56"] for r in rows], marker="^", label=r"$U_{(0,56)}$")
    ax.plot(xs, [r["U_0_57"] for r in rows], marker="D", label=r"$U_{(0,57)}$")
    ax.axhline(0.90, linestyle="--", linewidth=1.2, label="90%阈值")
    ax.set_xlabel(r"接触阈值 $\delta$ / nm")
    ax.set_ylabel("必要事件概率上界")
    ax.set_title("接触阈值敏感性")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig(fig, "q7-delta-sensitivity")
    return rows


def build_direction() -> list[dict]:
    # 严格平端圆柱：h_x=(l/2)|u_x|+r*sqrt(1-u_x^2)
    # 完全沿X时 u_x=1，因此 p_D=2*(l/2)/L=l/L=0.5，而非0.506。
    cases = [
        ("X轴向对齐", 0.5),
        ("各向同性（主口径）", P_A_ISO),
        ("轴向完全垂直X", 2.0 * RA / L),
    ]
    rows = []
    for name, p in cases:
        n90 = n_for_target(p)
        rows.append({
            "direction_case": name,
            "p_A_direct": p,
            "n_A_for_90_direct": n90,
            "cost_for_90_yuan": n90 * CA,
            "lower_at_8": 1.0 - (1.0 - p) ** 8,
        })
    write_csv(RESULTS / "q7_direction_sensitivity.csv", list(rows[0].keys()), rows)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    names = [r["direction_case"] for r in rows]
    vals = [r["p_A_direct"] for r in rows]
    bars = ax.bar(names, vals)
    ax.axhline(P_A_ISO, linestyle="--", linewidth=1.0, label="各向同性基准")
    ax.set_ylabel("A 单粒子直接跨 X 概率")
    ax.set_title("A 方向分布敏感性")
    ax.set_ylim(0, max(vals) * 1.22)
    for b, r in zip(bars, rows):
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.012,
            f"n90={r['n_A_for_90_direct']}\n成本={r['cost_for_90_yuan']:.4f}元",
            ha="center", va="bottom", fontsize=9
        )
    ax.legend()
    savefig(fig, "q7-direction-sensitivity")
    return rows


def build_boundary_semantics() -> list[dict]:
    rows = [
        {"boundary_semantics": "题面回迁+同一ID", "pA_self": P_A_ISO, "pB_self": P_B, "p57B_self": lower_self(0, 57), "network_note": "只按显式回迁像建立接触"},
        {"boundary_semantics": "硬截断/删除越界", "pA_self": 0.0, "pB_self": 0.0, "p57B_self": 0.0, "network_note": "只能靠截断后的网络导通"},
        {"boundary_semantics": "回迁但拆分ID", "pA_self": 0.0, "pB_self": 0.0, "p57B_self": 0.0, "network_note": "原像/回迁像不再内禀连通"},
        {"boundary_semantics": "全局最小镜像", "pA_self": P_A_ISO, "pB_self": P_B, "p57B_self": lower_self(0, 57), "network_note": "自短路相同，但粒子间接触被扩大"},
    ]
    write_csv(RESULTS / "q7_boundary_semantics.csv", list(rows[0].keys()), rows)

    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    names = [r["boundary_semantics"] for r in rows]
    x = list(range(len(names)))
    width = 0.25
    ax.bar([v - width for v in x], [r["pA_self"] for r in rows], width=width, label="A单粒子")
    ax.bar(x, [r["pB_self"] for r in rows], width=width, label="B单粒子")
    ax.bar([v + width for v in x], [r["p57B_self"] for r in rows], width=width, label="57B至少一粒自短路")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=10, ha="right")
    ax.set_ylabel("自短路概率分量")
    ax.set_title("边界语义对自短路机制的影响")
    ax.legend()
    savefig(fig, "q7-boundary-semantics")
    return rows


def build_pn_curves() -> list[dict]:
    rows = []
    nmax = 100
    for n in range(nmax + 1):
        rows.append({"N": n, "A_direct_lower": 1.0 - (1.0 - P_A_ISO) ** n, "B_direct_lower": 1.0 - (1.0 - P_B) ** n})
    write_csv(RESULTS / "q7_pn_curves.csv", list(rows[0].keys()), rows)

    fig, ax = plt.subplots(figsize=(8.2, 5.0))
    ax.plot([r["N"] for r in rows], [r["A_direct_lower"] for r in rows], label="A直接自短路下界")
    ax.plot([r["N"] for r in rows], [r["B_direct_lower"] for r in rows], label="B直接自短路下界")
    ax.axhline(0.90, linestyle="--", linewidth=1.2, label="90%阈值")
    ax.scatter([8, 57], [lower_self(8, 0), lower_self(0, 57)], zorder=3)
    ax.annotate("A: N=8", (8, lower_self(8, 0)), xytext=(14, 0.80), arrowprops={"arrowstyle": "->"})
    ax.annotate("B: N=57", (57, lower_self(0, 57)), xytext=(64, 0.78), arrowprops={"arrowstyle": "->"})
    ax.set_xlabel("粒子数量 N")
    ax.set_ylabel("至少一粒直接自短路的概率下界")
    ax.set_title("直接自短路概率下界随粒子数量变化")
    ax.set_xlim(0, nmax)
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig(fig, "q7-pn-curves")
    return rows


def build_cost_efficiency() -> list[dict]:
    rows = [
        {"medium": "A圆柱", "single_efficiency_per_yuan": P_A_ISO / CA, "critical_efficiency_per_yuan": lower_self(8, 0) / (8 * CA)},
        {"medium": "B球", "single_efficiency_per_yuan": P_B / CB, "critical_efficiency_per_yuan": lower_self(0, 57) / (57 * CB)},
    ]
    write_csv(RESULTS / "q7_cost_efficiency.csv", list(rows[0].keys()), rows)

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    x = [0, 1]
    width = 0.34
    ax.bar([v - width/2 for v in x], [r["single_efficiency_per_yuan"] for r in rows], width=width, label=r"单粒子 $p^D/c$")
    ax.bar([v + width/2 for v in x], [r["critical_efficiency_per_yuan"] for r in rows], width=width, label=r"90%临界方案 $L/c$")
    ax.set_xticks(x)
    ax.set_xticklabels([r["medium"] for r in rows])
    ax.set_ylabel("单位成本效率 / 每元")
    ax.set_title("A/B 成本效率对比")
    ax.legend()
    savefig(fig, "q7-cost-efficiency")
    return rows


def build_pareto() -> dict:
    points = []
    for na in range(21):
        for nb in range(81):
            points.append({
                "N_A": na,
                "N_B": nb,
                "cost_yuan": na * CA + nb * CB,
                "p_self_lower": lower_self(na, nb),
            })
    # Pareto: 成本越小越好，解析下界越大越好。
    pts_sorted = sorted(points, key=lambda r: (r["cost_yuan"], -r["p_self_lower"]))
    frontier = []
    best_p = -1.0
    for r in pts_sorted:
        if r["p_self_lower"] > best_p + 1e-15:
            frontier.append(r)
            best_p = r["p_self_lower"]
    write_csv(RESULTS / "q7_pareto_domain.csv", list(points[0].keys()), points)
    write_csv(RESULTS / "q7_pareto_frontier.csv", list(frontier[0].keys()), frontier)

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ax.scatter([r["cost_yuan"] for r in points], [r["p_self_lower"] for r in points], s=10, alpha=0.18, label="展示域整数候选")
    ax.plot([r["cost_yuan"] for r in frontier], [r["p_self_lower"] for r in frontier], linewidth=1.4, label="解析下界Pareto前沿")
    ax.scatter([57 * CB], [lower_self(0, 57)], s=55, zorder=4, label="(0,57)")
    ax.axhline(0.90, linestyle="--", linewidth=1.2, label="90%阈值")
    ax.set_xlabel("成本 / 元")
    ax.set_ylabel("直接自短路概率下界")
    ax.set_title(r"成本—直接自短路下界 Pareto 展示（$0\leq N_A\leq20, 0\leq N_B\leq80$）")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.2)
    ax.legend()
    savefig(fig, "q7-pareto-frontier")
    return {"domain_points": len(points), "frontier_points": len(frontier)}


def main() -> None:
    delta_rows = build_delta()
    direction_rows = build_direction()
    boundary_rows = build_boundary_semantics()
    build_pn_curves()
    build_cost_efficiency()
    pareto_meta = build_pareto()

    summary = {
        "formal_p_A_isotropic": P_A_ISO,
        "formal_p_B": P_B,
        "formal_q3_NA": 8,
        "formal_q4": {"N_A": 0, "N_B": 57, "cost_yuan": 57 * CB},
        "delta_range_nm": [r["delta_nm"] for r in delta_rows],
        "delta_strongest_cheaper_always": all((r["strongest_cheaper_NA"], r["strongest_cheaper_NB"]) == (0, 56) for r in delta_rows),
        "delta_max_U_0_56": max(r["U_0_56"] for r in delta_rows),
        "direction_note": "严格平端圆柱完全沿X时p_D=0.5；建模手草稿中的0.506已校正。",
        "direction_rows": direction_rows,
        "pareto": pareto_meta,
        "boundary_semantics_rows": boundary_rows,
    }
    with (RESULTS / "q7_sensitivity_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
