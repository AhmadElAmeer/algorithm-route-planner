"""Synthetic city generator.

Real road data would need a download, so the benchmark uses a generated
city with the features that matter to these algorithms:

* a jittered street grid (nodes are not perfectly aligned)
* curvy roads: each road is 0-25% longer than the straight line
* missing blocks: some streets are removed (parks, rivers)
* one-way streets, so the graph is directed and the reversed graph differs
* fast arterial roads every few blocks, which make the fastest route
  differ from the shortest one and weaken A*'s straight-line heuristic

The same seed always produces the same city.
"""
from __future__ import annotations

import random

from .graph import Graph

BLOCK_M = 120.0          # distance between grid lines, metres
STREET_KMH = 30.0
ARTERIAL_KMH = 70.0


def generate_city(size: int, seed: int = 0, *, remove_frac: float = 0.12,
                  one_way_frac: float = 0.15, arterial_every: int = 8,
                  arterial_kmh: float = ARTERIAL_KMH):
    """Return (graph, edge_list) for a size x size grid city.

    edge_list holds (u, v, length_m, speed_m_per_s) for saving to a file.
    """
    if size < 2:
        raise ValueError("size must be at least 2")
    if arterial_kmh <= 0:
        raise ValueError("arterial speed must be positive")
    rng = random.Random(seed)
    g = Graph()
    for r in range(size):
        for c in range(size):
            g.add_node(c * BLOCK_M + rng.uniform(-30, 30), r * BLOCK_M + rng.uniform(-30, 30))

    def node(r: int, c: int) -> int:
        return r * size + c

    edges: list[tuple[int, int, float, float]] = []
    for r in range(size):
        for c in range(size):
            for dr, dc in ((0, 1), (1, 0)):
                r2, c2 = r + dr, c + dc
                if r2 >= size or c2 >= size:
                    continue
                arterial = (dr == 0 and r % arterial_every == 0) or (dc == 0 and c % arterial_every == 0)
                if not arterial and rng.random() < remove_frac:
                    continue
                u, v = node(r, c), node(r2, c2)
                length = g.straight_line(u, v) * rng.uniform(1.0, 1.25)
                speed = (arterial_kmh if arterial else STREET_KMH) / 3.6
                if not arterial and rng.random() < one_way_frac:
                    pair = [(u, v)] if rng.random() < 0.5 else [(v, u)]
                else:
                    pair = [(u, v), (v, u)]
                for a, b in pair:
                    g.add_edge(a, b, length, speed)
                    edges.append((a, b, length, speed))
    return g, edges
