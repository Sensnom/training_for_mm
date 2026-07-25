"""Deterministic integer maximum-flow construction for rest-day rosters."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import perf_counter

import numpy as np


@dataclass
class _Edge:
    to: int
    reverse: int
    capacity: int
    original_capacity: int


class Dinic:
    def __init__(self, node_count: int):
        self.graph: list[list[_Edge]] = [[] for _ in range(node_count)]

    def add_edge(self, source: int, target: int, capacity: int) -> _Edge:
        if capacity < 0:
            raise ValueError("最大流边容量不得为负")
        forward = _Edge(target, len(self.graph[target]), capacity, capacity)
        reverse = _Edge(source, len(self.graph[source]), 0, 0)
        self.graph[source].append(forward)
        self.graph[target].append(reverse)
        return forward

    def maximum_flow(self, source: int, sink: int) -> int:
        total = 0
        node_count = len(self.graph)
        while True:
            level = [-1] * node_count
            level[source] = 0
            queue = deque([source])
            while queue:
                node = queue.popleft()
                for edge in self.graph[node]:
                    if edge.capacity > 0 and level[edge.to] < 0:
                        level[edge.to] = level[node] + 1
                        queue.append(edge.to)
            if level[sink] < 0:
                return total

            cursor = [0] * node_count

            def send(node: int, amount: int) -> int:
                if node == sink:
                    return amount
                while cursor[node] < len(self.graph[node]):
                    edge = self.graph[node][cursor[node]]
                    if edge.capacity > 0 and level[node] + 1 == level[edge.to]:
                        pushed = send(edge.to, min(amount, edge.capacity))
                        if pushed:
                            edge.capacity -= pushed
                            reverse = self.graph[edge.to][edge.reverse]
                            reverse.capacity += pushed
                            return pushed
                    cursor[node] += 1
                return 0

            while True:
                pushed = send(source, 10**9)
                if not pushed:
                    break
                total += pushed


@dataclass(frozen=True)
class FlowRoster:
    work_status: np.ndarray  # [employee, day], True for WORK
    required_flow: int
    computed_max_flow: int
    is_full_flow: bool
    runtime_seconds: float
    algorithm: str = "Deterministic Dinic integer maximum flow"


def assign_rest_days(staff: int, workers_by_day: np.ndarray) -> FlowRoster:
    """Assign exactly two rest days per employee using a real max-flow run."""

    workers = np.asarray(workers_by_day, dtype=np.int64)
    if workers.shape != (10,):
        raise ValueError("每日工作人数必须为长度 10 的向量")
    if staff <= 0 or np.any(workers < 0) or np.any(workers > staff):
        raise ValueError("每日工作人数必须位于 0..staff")
    if int(workers.sum()) != 8 * staff:
        raise ValueError("十日工作人日总数必须等于 8×staff")
    rest = staff - workers

    source = 0
    employee_offset = 1
    day_offset = employee_offset + staff
    sink = day_offset + 10
    network = Dinic(sink + 1)
    employee_day_edges: list[list[_Edge]] = [[] for _ in range(staff)]
    for employee in range(staff):
        network.add_edge(source, employee_offset + employee, 2)
        for day in range(10):
            edge = network.add_edge(
                employee_offset + employee, day_offset + day, 1
            )
            employee_day_edges[employee].append(edge)
    for day in range(10):
        network.add_edge(day_offset + day, sink, int(rest[day]))

    started = perf_counter()
    computed = network.maximum_flow(source, sink)
    elapsed = perf_counter() - started
    required = 2 * staff
    full = computed == required
    if not full:
        raise RuntimeError(f"休息日最大流不足：{computed} < {required}")

    work_status = np.ones((staff, 10), dtype=bool)
    for employee in range(staff):
        for day, edge in enumerate(employee_day_edges[employee]):
            flow = edge.original_capacity - edge.capacity
            if flow not in (0, 1):
                raise AssertionError("员工—日期边流量不是 0/1")
            if flow == 1:
                work_status[employee, day] = False
    if not np.all(work_status.sum(axis=1) == 8):
        raise AssertionError("最大流结果未使每名员工恰好工作 8 天")
    if not np.array_equal(work_status.sum(axis=0), workers):
        raise AssertionError("最大流结果的每日工作人数不匹配")
    return FlowRoster(work_status, required, computed, full, elapsed)

