"""Shortest-path algorithms that all answer the same question.

Each function returns a SearchResult with the travel time, the path, and
how many nodes the algorithm settled. "Settled" means popped from the
priority queue with its final distance, which is the standard way to
compare how much work point-to-point searches do.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from .graph import Graph

INF = math.inf


@dataclass
class SearchResult:
    cost: float                  # travel time in seconds; inf if unreachable
    path: list[int]              # nodes from source to target; [] if unreachable
    settled: int                 # nodes settled (both directions for bidirectional)
    settled_nodes: list[int] = field(default_factory=list, repr=False)  # for plotting

    @property
    def found(self) -> bool:
        return self.cost < INF


def _build_path(parent: dict[int, int], source: int, target: int) -> list[int]:
    path = [target]
    while path[-1] != source:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def dijkstra(g: Graph, source: int, target: int) -> SearchResult:
    """Dijkstra with early exit once the target is settled."""
    return astar(g, source, target, heuristic=lambda _: 0.0)


def astar(g: Graph, source: int, target: int, heuristic=None) -> SearchResult:
    """A* search. The default heuristic is straight-line distance divided by
    the fastest speed in the graph: no road can be shorter than the straight
    line or faster than max_speed, so it never overestimates (admissible).
    It is also consistent, so each node is settled at most once."""
    g.check_node(source)
    g.check_node(target)
    if heuristic is None:
        vmax = g.max_speed or 1.0
        tx, ty = g.xs[target], g.ys[target]
        xs, ys = g.xs, g.ys
        heuristic = lambda u: math.hypot(xs[u] - tx, ys[u] - ty) / vmax  # noqa: E731

    dist = {source: 0.0}
    parent: dict[int, int] = {}
    done: set[int] = set()
    order: list[int] = []
    heap = [(heuristic(source), source)]
    while heap:
        _, u = heapq.heappop(heap)
        if u in done:
            continue  # stale entry left behind by a later decrease-key
        done.add(u)
        order.append(u)
        if u == target:
            return SearchResult(dist[u], _build_path(parent, source, target), len(done), order)
        du = dist[u]
        for v, w in g.adj[u]:
            nd = du + w
            if nd < dist.get(v, INF):
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd + heuristic(v), v))
    return SearchResult(INF, [], len(done), order)


def bidirectional_dijkstra(g: Graph, source: int, target: int) -> SearchResult:
    """Run Dijkstra forward from the source and backward (on reversed edges)
    from the target, always expanding the side with the smaller queue top.

    `best` is the shortest source->target path seen so far through any edge
    that connects the two searches. It is safe to stop as soon as
    top_forward + top_backward >= best: any path not yet seen would have to
    leave the forward frontier and enter the backward one, so it costs at
    least that sum.
    """
    g.check_node(source)
    g.check_node(target)
    if source == target:
        return SearchResult(0.0, [source], 1, [source])

    dist = ({source: 0.0}, {target: 0.0})
    parent: tuple[dict[int, int], dict[int, int]] = ({}, {})
    done: tuple[set[int], set[int]] = (set(), set())
    heaps = ([(0.0, source)], [(0.0, target)])
    edges = (g.adj, g.radj)
    order: list[int] = []
    best, meet = INF, -1

    def top(side: int) -> float:
        h, d = heaps[side], done[side]
        while h and h[0][1] in d:      # drop stale entries
            heapq.heappop(h)
        return h[0][0] if h else INF

    while True:
        tf, tb = top(0), top(1)
        if tf + tb >= best or (tf == INF and tb == INF):
            break
        side = 0 if tf <= tb else 1
        other = 1 - side
        du, u = heapq.heappop(heaps[side])
        done[side].add(u)
        order.append(u)
        for v, w in edges[side][u]:
            nd = du + w
            if nd < dist[side].get(v, INF):
                dist[side][v] = nd
                parent[side][v] = u
                heapq.heappush(heaps[side], (nd, v))
            # Did this edge connect the two searches?
            dv_other = dist[other].get(v)
            if dv_other is not None and nd + dv_other < best:
                best, meet = nd + dv_other, v

    settled = len(done[0]) + len(done[1])
    if best == INF:
        return SearchResult(INF, [], settled, order)
    forward = _build_path(parent[0], source, meet)
    backward = _build_path(parent[1], target, meet)  # target ... meet
    return SearchResult(best, forward + backward[::-1][1:], settled, order)


ALGORITHMS = {
    "dijkstra": dijkstra,
    "astar": astar,
    "bidirectional": bidirectional_dijkstra,
}


def path_cost(g: Graph, path: list[int]) -> float:
    """Travel time along a path, using the cheapest parallel edge each step.
    Raises ValueError if consecutive nodes are not connected."""
    total = 0.0
    for u, v in zip(path, path[1:]):
        times = [w for x, w in g.adj[u] if x == v]
        if not times:
            raise ValueError(f"no edge {u}->{v}")
        total += min(times)
    return total
