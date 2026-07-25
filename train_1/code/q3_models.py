"""Formal PySCIPOpt/SCIP models for all Question 3 scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import numpy as np

from q3_patterns import (
    Q3FulltimePattern,
    Q3ParttimePattern,
    build_fulltime_coverage,
    build_parttime_coverage,
    generate_fulltime_patterns,
    generate_parttime_patterns,
)


@dataclass(frozen=True)
class Q3ScenarioSpec:
    scenario_id: str
    description: str
    minimum_break_hours: int
    allow_cross_group: bool
    mixed_workforce: bool
    objective_policy: str


@dataclass
class Q3ScenarioResult:
    spec: Q3ScenarioSpec
    status: str
    solver_name: str
    solver_version: str
    runtime_seconds: float
    best_bound: float | None = None
    relative_gap: float | None = None
    fulltime_staff: int | None = None
    parttime_staff: int | None = None
    total_staff: int | None = None
    total_parttime_shifts: int | None = None
    total_paid_hours: int | None = None
    cross_group_employee_days: int | None = None
    fulltime_workdays: int | None = None
    lexicographic_stages: list[dict] = field(default_factory=list)
    z: np.ndarray | None = None
    p: np.ndarray | None = None
    fulltime_patterns: list[Q3FulltimePattern] = field(default_factory=list)
    parttime_patterns: list[Q3ParttimePattern] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "scenario": self.spec.scenario_id,
            "description": self.spec.description,
            "minimum_break_hours": self.spec.minimum_break_hours,
            "allow_cross_group": self.spec.allow_cross_group,
            "mixed_workforce": self.spec.mixed_workforce,
            "objective_policy": self.spec.objective_policy,
            "status": self.status,
            "fulltime_staff": self.fulltime_staff,
            "parttime_staff": self.parttime_staff,
            "total_staff": self.total_staff,
            "total_parttime_shifts": self.total_parttime_shifts,
            "total_paid_hours": self.total_paid_hours,
            "cross_group_employee_days": self.cross_group_employee_days,
            "fulltime_workdays": self.fulltime_workdays,
            "solver_name": self.solver_name,
            "solver_version": self.solver_version,
            "best_bound": self.best_bound,
            "relative_gap": self.relative_gap,
            "runtime_seconds": self.runtime_seconds,
            "lexicographic_stages": self.lexicographic_stages,
        }


def build_default_scenarios() -> tuple[Q3ScenarioSpec, ...]:
    return (
        Q3ScenarioSpec("S0", "严格2小时休息，允许同日跨组", 2, True, False, "staff"),
        Q3ScenarioSpec("S1", "严格2小时休息，禁止同日跨组", 2, False, False, "staff"),
        Q3ScenarioSpec("S2", "1小时休息，允许同日跨组", 1, True, False, "staff"),
        Q3ScenarioSpec("S3", "1小时休息，禁止同日跨组", 1, False, False, "staff"),
        Q3ScenarioSpec("S4", "严格全职与兼职混合，允许同日跨组，总人数最优", 2, True, True, "headcount"),
        Q3ScenarioSpec("S5", "严格全职与兼职混合，禁止同日跨组，总人数最优", 2, False, True, "headcount"),
        Q3ScenarioSpec("S6", "严格全职与兼职混合，允许同日跨组，兼职班次最少优先", 2, True, True, "parttime_first"),
        Q3ScenarioSpec("S7", "严格全职与兼职混合，禁止同日跨组，兼职班次最少优先", 2, False, True, "parttime_first"),
    )


def _scip_version(model) -> str:
    return (
        f"{model.getMajorVersion()}."
        f"{model.getMinorVersion()}."
        f"{model.getTechVersion()}"
    )


def _configure_model(model, time_limit: float) -> None:
    model.hideOutput()
    model.setParam("limits/time", float(time_limit))
    model.setParam("limits/gap", 0.0)
    model.setParam("parallel/maxnthreads", 1)
    model.setParam("randomization/permutationseed", 0)
    model.setParam("randomization/randomseedshift", 0)
    model.setParam("randomization/lpseed", 0)


def _integer_value(model, expression) -> int:
    raw = float(model.getVal(expression))
    rounded = int(round(raw))
    if abs(raw - rounded) > 1e-6:
        raise RuntimeError(f"SCIP 返回非整数目标值 {raw}")
    return rounded


def solve_q3_scenario(
    spec: Q3ScenarioSpec,
    demand: np.ndarray,
    *,
    time_limit: float = 600.0,
) -> Q3ScenarioResult:
    try:
        from pyscipopt import Model, quicksum
    except ImportError as exc:
        raise RuntimeError(
            "问题三正式求解要求 PySCIPOpt/SCIP，不允许回退至其他求解器"
        ) from exc

    demand = np.asarray(demand, dtype=np.int64)
    if demand.shape != (10, 11, 10) or np.any(demand <= 0):
        raise ValueError("问题三需求必须为 (10, 11, 10) 正整数张量")
    if spec.objective_policy not in {"staff", "headcount", "parttime_first"}:
        raise ValueError(f"未知问题三目标策略：{spec.objective_policy}")

    fulltime_patterns = generate_fulltime_patterns(spec.minimum_break_hours)
    parttime_patterns = generate_parttime_patterns() if spec.mixed_workforce else []
    full_cov = build_fulltime_coverage(fulltime_patterns)
    part_cov = (
        build_parttime_coverage(parttime_patterns)
        if parttime_patterns
        else np.zeros((11, 0), dtype=np.int64)
    )

    model = Model(f"q3_{spec.scenario_id}")
    _configure_model(model, time_limit)
    upper_staff = int(demand.sum())
    wf = model.addVar("W_F", vtype="INTEGER", lb=0, ub=upper_staff)
    wp = (
        model.addVar("W_P", vtype="INTEGER", lb=0, ub=upper_staff)
        if spec.mixed_workforce
        else None
    )

    group_pairs = (
        [(g, k) for g in range(10) for k in range(10)]
        if spec.allow_cross_group
        else [(g, g) for g in range(10)]
    )
    z = {
        (day, shift, g, k): model.addVar(
            f"z_{day + 1}_{shift + 1}_{g + 1}_{k + 1}",
            vtype="INTEGER",
            lb=0,
            ub=upper_staff,
        )
        for day in range(10)
        for shift in range(len(fulltime_patterns))
        for g, k in group_pairs
    }
    p = {
        (day, shift, group): model.addVar(
            f"p_{day + 1}_{shift + 1}_{group + 1}",
            vtype="INTEGER",
            lb=0,
            ub=upper_staff,
        )
        for day in range(10)
        for shift in range(len(parttime_patterns))
        for group in range(10)
    }

    daily_fulltime = []
    for day in range(10):
        expression = quicksum(
            z[day, shift, g, k]
            for shift in range(len(fulltime_patterns))
            for g, k in group_pairs
        )
        daily_fulltime.append(expression)
        model.addCons(expression <= wf, name=f"fulltime_pool_day_{day + 1}")
    model.addCons(
        quicksum(daily_fulltime) == 8 * wf,
        name="fulltime_eight_of_ten_days",
    )

    daily_parttime = []
    if spec.mixed_workforce:
        assert wp is not None
        for day in range(10):
            expression = quicksum(
                p[day, shift, group]
                for shift in range(len(parttime_patterns))
                for group in range(10)
            )
            daily_parttime.append(expression)
            model.addCons(
                expression <= wp, name=f"parttime_pool_day_{day + 1}"
            )

    for day in range(10):
        for hour in range(11):
            for group in range(10):
                full_terms = []
                for shift, pattern in enumerate(fulltime_patterns):
                    if pattern.first_start <= hour + 8 < pattern.first_end:
                        full_terms.extend(
                            z[day, shift, group, k]
                            for g, k in group_pairs
                            if g == group
                        )
                    if pattern.second_start <= hour + 8 < pattern.second_end:
                        full_terms.extend(
                            z[day, shift, g, group]
                            for g, k in group_pairs
                            if k == group
                        )
                part_terms = [
                    p[day, shift, group]
                    for shift in range(len(parttime_patterns))
                    if part_cov[hour, shift]
                ]
                model.addCons(
                    quicksum(full_terms) + quicksum(part_terms)
                    >= int(demand[day, hour, group]),
                    name=f"cover_{day + 1}_{hour + 8}_{group + 1}",
                )

    total_parttime = quicksum(p.values())
    cross_group = quicksum(
        variable
        for (day, shift, g, k), variable in z.items()
        if g != k
    )
    total_headcount = wf + (wp if wp is not None else 0)
    paid_hours = 64 * wf + 4 * total_parttime
    if spec.objective_policy == "staff":
        stages = [("fulltime_staff", wf), ("cross_group_employee_days", cross_group)]
    elif spec.objective_policy == "headcount":
        stages = [
            ("total_staff", total_headcount),
            ("total_paid_hours", paid_hours),
            ("cross_group_employee_days", cross_group),
        ]
    else:
        stages = [
            ("total_parttime_shifts", total_parttime),
            ("fulltime_staff", wf),
            ("parttime_staff", wp),
            ("cross_group_employee_days", cross_group),
        ]

    started = perf_counter()
    stage_records: list[dict] = []
    first_status: str | None = None
    final_bound: float | None = None
    final_gap: float | None = None
    for stage_index, (name, expression) in enumerate(stages):
        model.setObjective(expression, "minimize")
        model.optimize()
        status = str(model.getStatus()).lower()
        if stage_index == 0:
            first_status = status
        if status == "infeasible":
            if stage_index != 0:
                raise RuntimeError(
                    f"{spec.scenario_id} 固定前层最优值后变为不可行"
                )
            return Q3ScenarioResult(
                spec=spec,
                status="INFEASIBLE",
                solver_name="PySCIPOpt/SCIP",
                solver_version=_scip_version(model),
                runtime_seconds=perf_counter() - started,
                fulltime_patterns=fulltime_patterns,
                parttime_patterns=parttime_patterns,
            )
        if status != "optimal":
            raise RuntimeError(
                f"{spec.scenario_id} 的 {name} 未达到最优：status={status}"
            )
        optimum = _integer_value(model, expression)
        stage_records.append(
            {
                "stage": stage_index + 1,
                "objective": name,
                "value": optimum,
                "best_bound": float(model.getDualbound()),
                "relative_gap": float(model.getGap()),
                "status": "OPTIMAL",
            }
        )
        final_bound = float(model.getDualbound())
        final_gap = float(model.getGap())
        if stage_index + 1 < len(stages):
            model.freeTransform()
            model.addCons(expression == optimum, name=f"fix_{name}")

    if first_status != "optimal":
        raise AssertionError("问题三首层状态记录异常")
    z_values = np.zeros(
        (10, len(fulltime_patterns), 10, 10), dtype=np.int64
    )
    for key, variable in z.items():
        z_values[key] = _integer_value(model, variable)
    p_values = np.zeros(
        (10, len(parttime_patterns), 10), dtype=np.int64
    )
    for key, variable in p.items():
        p_values[key] = _integer_value(model, variable)

    wf_value = _integer_value(model, wf)
    wp_value = _integer_value(model, wp) if wp is not None else 0
    parttime_value = int(p_values.sum())
    cross_value = int(
        sum(
            z_values[:, :, g, k].sum()
            for g in range(10)
            for k in range(10)
            if g != k
        )
    )
    fulltime_workdays = int(z_values.sum())
    if fulltime_workdays != 8 * wf_value:
        raise AssertionError("全职宏观方案不满足做八休二总量")
    return Q3ScenarioResult(
        spec=spec,
        status="OPTIMAL",
        solver_name="PySCIPOpt/SCIP",
        solver_version=_scip_version(model),
        runtime_seconds=perf_counter() - started,
        best_bound=final_bound,
        relative_gap=final_gap,
        fulltime_staff=wf_value,
        parttime_staff=wp_value,
        total_staff=wf_value + wp_value,
        total_parttime_shifts=parttime_value,
        total_paid_hours=64 * wf_value + 4 * parttime_value,
        cross_group_employee_days=cross_value,
        fulltime_workdays=fulltime_workdays,
        lexicographic_stages=stage_records,
        z=z_values,
        p=p_values,
        fulltime_patterns=fulltime_patterns,
        parttime_patterns=parttime_patterns,
    )
