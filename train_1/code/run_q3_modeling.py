"""Unified formal solver and result writer for Question 3."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import numpy as np
import pandas as pd

from data_loader import load_demand
from q3_models import (
    Q3ScenarioResult,
    build_default_scenarios,
    solve_q3_scenario,
)
from q3_patterns import blind_zone_proof, generate_fulltime_patterns
from q3_roster import build_q3_rosters
from q3_verification import compute_q3_coverage, verify_q3_rosters


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"拒绝写出空 CSV：{path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _stable_summary(result: Q3ScenarioResult) -> dict:
    summary = result.summary()
    summary.pop("runtime_seconds", None)
    return summary


def _scenario_row(result: Q3ScenarioResult, coverage_audit: dict) -> dict:
    primary = result.lexicographic_stages[0] if result.lexicographic_stages else {}
    return {
        "scenario": result.spec.scenario_id,
        "description": result.spec.description,
        "minimum_break_hours": result.spec.minimum_break_hours,
        "allow_cross_group": result.spec.allow_cross_group,
        "mixed_workforce": result.spec.mixed_workforce,
        "objective_policy": result.spec.objective_policy,
        "status": result.status,
        "fulltime_staff": result.fulltime_staff,
        "parttime_staff": result.parttime_staff,
        "total_staff": result.total_staff,
        "total_parttime_shifts": result.total_parttime_shifts,
        "total_paid_hours": result.total_paid_hours,
        "fulltime_workdays": result.fulltime_workdays,
        "cross_group_employee_days": result.cross_group_employee_days,
        "cross_group_rate": (
            result.cross_group_employee_days / result.fulltime_workdays
            if result.fulltime_workdays
            else 0.0
        ),
        "demand_cell_count": coverage_audit.get("demand_cell_count", ""),
        "deficit_count": coverage_audit.get("deficit_count", ""),
        "minimum_slack": coverage_audit.get("minimum_slack", ""),
        "maximum_slack": coverage_audit.get("maximum_slack", ""),
        "primary_objective": primary.get("objective", ""),
        "primary_value": primary.get("value", ""),
        "primary_best_bound": primary.get("best_bound", ""),
        "primary_relative_gap": primary.get("relative_gap", ""),
        "solver_name": result.solver_name,
        "solver_version": result.solver_version,
    }


def _pair_comparison(
    allowed: Q3ScenarioResult,
    forbidden: Q3ScenarioResult,
    label: str,
) -> dict:
    if allowed.status != "OPTIMAL" or forbidden.status != "OPTIMAL":
        raise AssertionError(f"{label} 的跨组 A/B 场景未全部最优")
    assert allowed.total_staff is not None and forbidden.total_staff is not None
    assert allowed.fulltime_staff is not None and forbidden.fulltime_staff is not None
    saving = forbidden.total_staff - allowed.total_staff
    return {
        "label": label,
        "allowed_scenario": allowed.spec.scenario_id,
        "forbidden_scenario": forbidden.spec.scenario_id,
        "allowed_total_staff": allowed.total_staff,
        "forbidden_total_staff": forbidden.total_staff,
        "total_staff_saving": saving,
        "total_staff_reduction_rate": saving / forbidden.total_staff,
        "fulltime_staff_saving": forbidden.fulltime_staff - allowed.fulltime_staff,
        "allowed_cross_group_employee_days": allowed.cross_group_employee_days,
        "allowed_cross_group_rate": (
            allowed.cross_group_employee_days / allowed.fulltime_workdays
            if allowed.fulltime_workdays
            else 0.0
        ),
    }


def _macro_fulltime_rows(result: Q3ScenarioResult) -> list[dict]:
    assert result.z is not None
    return [
        {
            "day": day + 1,
            "shift_id": result.fulltime_patterns[shift].name,
            "first_group": first + 1,
            "second_group": second + 1,
            "count": int(result.z[day, shift, first, second]),
        }
        for day in range(10)
        for shift in range(len(result.fulltime_patterns))
        for first in range(10)
        for second in range(10)
        if result.z[day, shift, first, second] > 0
    ]


def _macro_parttime_rows(result: Q3ScenarioResult) -> list[dict]:
    assert result.p is not None
    return [
        {
            "day": day + 1,
            "shift_id": result.parttime_patterns[shift].name,
            "group": group + 1,
            "count": int(result.p[day, shift, group]),
        }
        for day in range(10)
        for shift in range(len(result.parttime_patterns))
        for group in range(10)
        if result.p[day, shift, group] > 0
    ]


def run_q3(
    data_path: str | Path,
    output_dir: str | Path,
    *,
    solver: str = "SCIP",
    time_limit: float = 600.0,
    build_figures: bool = True,
) -> dict:
    if solver.strip().upper() != "SCIP":
        raise ValueError("问题三正式求解只允许 SCIP，不得回退至其他求解器")
    started = perf_counter()
    data = load_demand(data_path)
    output = Path(output_dir).resolve()
    tables = output / "tables"
    results_dir = output / "results"
    logs = output / "logs"

    specs = build_default_scenarios()
    scenario_results = [
        solve_q3_scenario(spec, data.demand, time_limit=time_limit)
        for spec in specs
    ]
    if any(
        result.solver_name != "PySCIPOpt/SCIP" for result in scenario_results
    ):
        raise AssertionError("问题三场景存在非 SCIP 求解结果")
    if [result.status for result in scenario_results[:2]] != [
        "INFEASIBLE",
        "INFEASIBLE",
    ]:
        raise AssertionError("严格问题三的两个场景必须均不可行")
    if any(result.status != "OPTIMAL" for result in scenario_results[2:]):
        raise AssertionError("问题三可行场景未全部达到全局最优")

    strict_proof = blind_zone_proof(
        data.demand, generate_fulltime_patterns(2)
    )
    if strict_proof["status"] != "PROVED_INFEASIBLE":
        raise AssertionError("严格问题三公共盲区解析证明失败")

    by_id = {result.spec.scenario_id: result for result in scenario_results}
    coverage_audits: dict[str, dict] = {}
    for result in scenario_results:
        if result.status != "OPTIMAL":
            coverage_audits[result.spec.scenario_id] = {
                "status": "NOT_APPLICABLE_INFEASIBLE"
            }
            continue
        coverage = compute_q3_coverage(result)
        slack = coverage - data.demand
        audit = {
            "status": "PASS",
            "demand_cell_count": int(slack.size),
            "deficit_count": int(np.count_nonzero(slack < 0)),
            "minimum_slack": int(slack.min()),
            "maximum_slack": int(slack.max()),
            "total_slack": int(slack.sum()),
        }
        if audit["deficit_count"]:
            raise AssertionError(
                f"{result.spec.scenario_id} 的宏观方案存在逐小时覆盖缺口"
            )
        coverage_audits[result.spec.scenario_id] = audit
    comparisons = {
        "gap_one_cross_group": _pair_comparison(
            by_id["S2"], by_id["S3"], "1小时休息方案"
        ),
        "headcount_cross_group": _pair_comparison(
            by_id["S4"], by_id["S5"], "总人数最优混合方案"
        ),
        "parttime_first_cross_group": _pair_comparison(
            by_id["S6"], by_id["S7"], "兼职班次最少优先方案"
        ),
    }
    s4, s6 = by_id["S4"], by_id["S6"]
    assert s4.total_staff is not None and s6.total_staff is not None
    comparisons["headcount_vs_policy"] = {
        "headcount_optimal_scenario": "S4",
        "parttime_first_scenario": "S6",
        "headcount_optimal_total_staff": s4.total_staff,
        "parttime_first_total_staff": s6.total_staff,
        "staff_difference": s6.total_staff - s4.total_staff,
        "reduction_rate_from_policy": (
            (s6.total_staff - s4.total_staff) / s6.total_staff
        ),
        "headcount_optimal_parttime_shifts": s4.total_parttime_shifts,
        "parttime_first_parttime_shifts": s6.total_parttime_shifts,
    }

    selected = s4
    roster = build_q3_rosters(selected)
    verification = verify_q3_rosters(
        selected, roster, data.demand, run_cpsat=True
    )

    _write_csv(
        tables / "q3_scenario_comparison.csv",
        [
            _scenario_row(
                result, coverage_audits[result.spec.scenario_id]
            )
            for result in scenario_results
        ],
    )
    _write_csv(
        tables / "q3_fulltime_employee_schedule.csv",
        roster.fulltime_schedule,
    )
    _write_csv(
        tables / "q3_parttime_employee_schedule.csv",
        roster.parttime_schedule,
    )
    _write_csv(
        tables / "q3_hourly_coverage.csv", verification.hourly_coverage
    )
    _write_csv(
        tables / "q3_cross_group_summary.csv",
        verification.cross_group_summary,
    )
    _write_csv(
        tables / "q3_group_transition_matrix.csv",
        verification.transition_rows,
    )
    _write_csv(
        tables / "q3_fulltime_macro_schedule.csv",
        _macro_fulltime_rows(selected),
    )
    _write_csv(
        tables / "q3_parttime_macro_schedule.csv",
        _macro_parttime_rows(selected),
    )

    model_payload = {
        "environment": {
            "python_version": platform.python_version(),
            "requested_solver": "SCIP",
            "actual_solver": "PySCIPOpt/SCIP",
            "actual_solver_version": selected.solver_version,
            "solver_fallback_used": False,
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "data_sha256": data.source_sha256,
        },
        "analytic_strict_infeasibility": strict_proof,
        "selected_scenario": "S4",
        "selected_scenario_reason": "首要目标为最小化全职与兼职总招聘人数",
        "scenarios": [
            {
                **_stable_summary(result),
                "coverage_audit": coverage_audits[result.spec.scenario_id],
            }
            for result in scenario_results
        ],
        "comparisons": comparisons,
        "policy_interpretation": {
            "parttime_shift_lower_bound": strict_proof[
                "total_blind_hour_demand"
            ],
            "parttime_first_scenario": "S6",
            "headcount_global_optimum_scenario": "S4",
            "headcount_global_optimum_proved": True,
        },
    }
    _write_json(results_dir / "q3_model_results.json", model_payload)
    _write_json(results_dir / "q3_verification.json", verification.summary)
    runtime_payload = {
        "total_runtime_seconds": perf_counter() - started,
        "scenario_runtime_seconds": {
            result.spec.scenario_id: result.runtime_seconds
            for result in scenario_results
        },
        "maxflow_runtime_seconds": roster.flow_roster.runtime_seconds,
    }
    _write_json(results_dir / "q3_solver_run_metadata.json", runtime_payload)
    _write_json(
        logs / "run_q3_modeling.log",
        {"model_results": model_payload, "runtime": runtime_payload},
    )
    if build_figures:
        from q3_figures import build_q3_figures

        build_q3_figures(output)
    return model_payload


def build_parser() -> argparse.ArgumentParser:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="使用 PySCIPOpt/SCIP 正式求解问题三八个场景"
    )
    parser.add_argument(
        "--data", type=Path, default=project / "data" / "附件1.xlsx"
    )
    parser.add_argument(
        "--output", type=Path, default=project / "paper_output"
    )
    parser.add_argument("--solver", choices=("SCIP",), default="SCIP")
    parser.add_argument("--time-limit", type=float, default=600.0)
    parser.add_argument("--no-figures", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_q3(
            args.data,
            args.output,
            solver=args.solver,
            time_limit=args.time_limit,
            build_figures=not args.no_figures,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
