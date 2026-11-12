"""Benchmark: run every algorithm on the same random queries.

Every query is answered by all algorithms and the costs are compared, so a
benchmark run doubles as a correctness check on a large graph.
"""
from __future__ import annotations

import random
import statistics
import time
from dataclasses import dataclass

from .graph import Graph
from .search import ALGORITHMS


class ResultMismatch(AssertionError):
    pass


@dataclass
class AlgoStats:
    name: str
    settled: list[int]
    seconds: list[float]

    @property
    def mean_settled(self) -> float:
        return statistics.fmean(self.settled)

    @property
    def median_ms(self) -> float:
        return statistics.median(self.seconds) * 1000


def random_queries(g: Graph, count: int, seed: int) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    return [(rng.randrange(g.num_nodes), rng.randrange(g.num_nodes)) for _ in range(count)]


def run_benchmark(g: Graph, queries: list[tuple[int, int]], algorithms=None):
    """Return (stats per algorithm, number of unreachable queries)."""
    names = algorithms or list(ALGORITHMS)
    stats = {n: AlgoStats(n, [], []) for n in names}
    unreachable = 0
    for s, t in queries:
        costs = {}
        for name in names:
            start = time.perf_counter()
            res = ALGORITHMS[name](g, s, t)
            stats[name].seconds.append(time.perf_counter() - start)
            stats[name].settled.append(res.settled)
            costs[name] = res.cost
        ref = costs[names[0]]
        for name, c in costs.items():
            if not (c == ref or abs(c - ref) <= 1e-6 * max(1.0, ref)):
                raise ResultMismatch(f"{s}->{t}: {names[0]}={ref} but {name}={c}")
        if ref == float("inf"):
            unreachable += 1
    return list(stats.values()), unreachable


def format_table(stats: list[AlgoStats], baseline: str = "dijkstra") -> str:
    base = next((s for s in stats if s.name == baseline), stats[0])
    lines = [f"{'algorithm':<15}{'mean settled':>14}{'vs ' + base.name:>16}{'median ms':>12}"]
    for s in stats:
        ratio = s.mean_settled / base.mean_settled if base.mean_settled else 0
        lines.append(f"{s.name:<15}{s.mean_settled:>14.0f}{ratio:>15.2f}x{s.median_ms:>12.2f}")
    return "\n".join(lines)
