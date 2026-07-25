"""Unified command-line entry point for Questions 1 and 2."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import pandas as pd
import scipy

from build_q1_q2_figures import build_all_figures
from daily_cover import solve_daily_minima
from data_loader import load_demand
from shift_patterns import build_coverage, generate_shift_patterns
from solve_core_and_roster import solve_q1, solve_q2
from verify_full_milp import verify_full_milp
from verify_with_cpsat import verify_with_cpsat


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(
        path, index=False, encoding="utf-8-sig", lineterminator="\n"
    )


def _shift_plan_rows(
    shift_counts: np.ndarray, actual_workers: np.ndarray, patterns
) -> list[dict]:
    rows = []
    for day in range(10):
        for group in range(10):
            for shift, pattern in enumerate(patterns):
                rows.append(
                    {
                        "day": day + 1,
                        "group": group + 1,
                        "actual_workers": int(actual_workers[day, group]),
                        "shift": shift + 1,
                        "shift_workers": int(shift_counts[day, group, shift]),
                        **{
                            key: value
                            for key, value in pattern.as_dict().items()
                            if key in {
                                "first_start",
                                "first_end",
                                "second_start",
                                "second_end",
                            }
                        },
                    }
                )
    return rows


def run_all(
    data_path: str | Path,
    output_dir: str | Path,
    requested_solver: str = "auto",
) -> dict:
    started = perf_counter()
    output = Path(output_dir).expanduser().resolve()
    tables = output / "tables"
    results = output / "results"
    logs = output / "logs"
    figures = output / "figures"
    for directory in (tables, results, logs, figures):
        directory.mkdir(parents=True, exist_ok=True)

    data = load_demand(data_path)
    patterns = generate_shift_patterns()
    coverage = build_coverage(patterns)
    daily = solve_daily_minima(data.demand, coverage, solver=requested_solver)
    q1 = solve_q1(
        data.demand, coverage, patterns, daily, solver=requested_solver
    )
    q2 = solve_q2(
        data.demand, coverage, patterns, daily, solver=requested_solver
    )
    full_milp = verify_full_milp(
        data.demand, coverage, solver=requested_solver
    )
    cpsat = verify_with_cpsat(
        q1.staff, q1.actual_workers, q2.staff, q2.actual_daily_workers
    )

    _write_json(results / "data_validation.json", data.validation_summary())
    (logs / "data_validation.log").write_text(
        json.dumps(data.validation_summary(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(tables / "shift_patterns_q1_q2.csv", [p.as_dict() for p in patterns])
    coverage_rows = []
    for hour in range(11):
        coverage_rows.append(
            {
                "hour": hour + 1,
                "hour_start": f"{hour + 8:02d}:00",
                "hour_end": f"{hour + 9:02d}:00",
                **{
                    f"shift_{shift + 1}": int(coverage[hour, shift])
                    for shift in range(10)
                },
            }
        )
    _write_csv(tables / "shift_coverage_matrix.csv", coverage_rows)
    _write_csv(tables / "daily_minimum_by_group.csv", daily.metadata)

    _write_csv(tables / "q1_group_results.csv", q1.group_results)
    _write_csv(
        tables / "q1_daily_shift_plan.csv",
        _shift_plan_rows(q1.shift_counts, q1.actual_workers, patterns),
    )
    _write_csv(tables / "q1_maxflow_summary.csv", q1.maxflow_summary)
    _write_csv(tables / "q1_employee_day_status.csv", q1.employee_day_status)
    _write_csv(tables / "q1_employee_schedule.csv", q1.employee_schedule)
    _write_csv(tables / "q1_hourly_coverage.csv", q1.hourly_coverage)

    q2_lower_rows = []
    cumulative = 0
    for day, workers in enumerate(q2.daily_lower_bound, start=1):
        cumulative += int(workers)
        q2_lower_rows.append(
            {
                "day": day,
                "minimum_workers": int(workers),
                "cumulative_minimum": cumulative,
            }
        )
    _write_csv(tables / "q2_daily_lower_bound.csv", q2_lower_rows)
    _write_csv(
        tables / "q2_daily_actual.csv",
        [
            {
                "day": day + 1,
                "minimum_workers": int(q2.daily_lower_bound[day]),
                "actual_workers": int(q2.actual_daily_workers[day]),
                "redundant_workers": int(
                    q2.actual_daily_workers[day] - q2.daily_lower_bound[day]
                ),
            }
            for day in range(10)
        ],
    )
    _write_csv(
        tables / "q2_daily_shift_plan.csv",
        _shift_plan_rows(
            q2.shift_counts, q2.shift_counts.sum(axis=2), patterns
        ),
    )
    _write_csv(tables / "q2_maxflow_summary.csv", [q2.maxflow_summary])
    _write_csv(tables / "q2_employee_day_status.csv", q2.employee_day_status)
    _write_csv(tables / "q2_employee_schedule.csv", q2.employee_schedule)
    _write_csv(tables / "q2_hourly_coverage.csv", q2.hourly_coverage)

    q2_redundancy = {
        "daily_lower_bound_total": int(q2.daily_lower_bound.sum()),
        "staff": q2.staff,
        "required_workdays": int(q2.actual_daily_workers.sum()),
        "redundant_workdays": q2.redundant_workdays,
        "redundancy_day": q2.redundancy_day,
    }
    _write_json(results / "q2_redundancy_summary.json", q2_redundancy)
    _write_json(results / "q2_verification.json", q2.verification)
    _write_json(results / "full_milp_verification.json", full_milp)
    _write_json(results / "cpsat_roster_verification.json", cpsat)
    (logs / "full_milp_verification.log").write_text(
        json.dumps(full_milp, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    q1_verification_fields = {
        ("verification_status" if key == "status" else key): value
        for key, value in q1.verification.items()
    }
    q2_verification_fields = {
        ("verification_status" if key == "status" else key): value
        for key, value in q2.verification.items()
    }
    q1_results = {
        "status": "OPTIMAL",
        "group_staff": [int(v) for v in q1.staff],
        "total_staff": int(q1.staff.sum()),
        "group_max_flows": [
            int(row["computed_max_flow"]) for row in q1.maxflow_summary
        ],
        "all_groups_full_flow": all(
            row["is_full_flow"] for row in q1.maxflow_summary
        ),
        **q1_verification_fields,
        "full_milp_objective": full_milp["q1"]["objective_value"],
    }
    q2_results = {
        "status": "OPTIMAL",
        "daily_lower_bound": [int(v) for v in q2.daily_lower_bound],
        "daily_lower_bound_total": int(q2.daily_lower_bound.sum()),
        "total_staff": q2.staff,
        "actual_daily_workers": [int(v) for v in q2.actual_daily_workers],
        "actual_workdays": int(q2.actual_daily_workers.sum()),
        "redundant_workdays": q2.redundant_workdays,
        "redundancy_day": q2.redundancy_day,
        "max_flow": int(q2.maxflow_summary["computed_max_flow"]),
        "full_flow": bool(q2.maxflow_summary["is_full_flow"]),
        **q2_verification_fields,
        "full_milp_objective": full_milp["q2"]["objective_value"],
    }
    _write_json(results / "q1_model_results.json", q1_results)
    _write_json(results / "q2_model_results.json", q2_results)
    build_all_figures(
        project_dir=Path(__file__).resolve().parents[1],
        output_dir=output,
    )

    environment = {
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scipy_version": scipy.__version__,
        "requested_solver": requested_solver,
        "actual_solver": full_milp["q1"]["solver_name"],
        "actual_solver_version": full_milp["q1"]["solver_version"],
        "solver_fallback_used": False,
        "maxflow_algorithm": "Deterministic Dinic integer maximum flow",
        "data_path": data.source_path,
        "data_sha256": data.source_sha256,
        "runtime_seconds": perf_counter() - started,
    }
    consolidated = {
        "environment": environment,
        "q1": q1_results,
        "q2": q2_results,
        "full_milp": full_milp,
        "cpsat": cpsat,
    }
    _write_json(results / "core_model_results.json", consolidated)
    (logs / "run_modeling.log").write_text(
        json.dumps(consolidated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return consolidated


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="求解展销会排班问题一、二并输出可审计结果"
    )
    project_dir = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--data",
        type=Path,
        default=project_dir / "data" / "附件1.xlsx",
        help="原始需求 .xlsx 路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "paper_output",
        help="结果输出目录",
    )
    parser.add_argument(
        "--solver",
        default="auto",
        choices=("auto", "HiGHS", "SCIP"),
        help="整数规划求解器；SCIP 需要安装 PySCIPOpt，缺失时直接报错",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_all(args.data, args.output, args.solver)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
