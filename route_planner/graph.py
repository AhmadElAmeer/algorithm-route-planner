"""Directed road graph with node coordinates.

Edge weights are travel times in seconds: length (metres) / speed (m/s).
Coordinates are kept so A* can use straight-line distance as a heuristic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path


ROUNDING_TOLERANCE_M = 0.01


class GraphFormatError(ValueError):
    """Raised when a graph file cannot be parsed."""


@dataclass
class Graph:
    xs: list[float] = field(default_factory=list)
    ys: list[float] = field(default_factory=list)
    # adj[u] = [(v, travel_time), ...]; radj is the reversed graph, used by
    # the backward half of bidirectional search.
    adj: list[list[tuple[int, float]]] = field(default_factory=list)
    radj: list[list[tuple[int, float]]] = field(default_factory=list)
    max_speed: float = 0.0  # fastest speed on any edge, m/s

    @property
    def num_nodes(self) -> int:
        return len(self.xs)

    @property
    def num_edges(self) -> int:
        return sum(len(a) for a in self.adj)

    def add_node(self, x: float, y: float) -> int:
        self.xs.append(x)
        self.ys.append(y)
        self.adj.append([])
        self.radj.append([])
        return len(self.xs) - 1

    def straight_line(self, u: int, v: int) -> float:
        return math.hypot(self.xs[u] - self.xs[v], self.ys[u] - self.ys[v])

    def add_edge(self, u: int, v: int, length: float, speed: float) -> None:
        """Add a one-way road from u to v.

        `length` must be at least the straight-line distance between the
        endpoints, otherwise the A* heuristic would stop being admissible.
        """
        for node in (u, v):
            if not 0 <= node < self.num_nodes:
                raise ValueError(f"node {node} does not exist")
        if speed <= 0:
            raise ValueError("speed must be positive")
        if length + 1e-9 < self.straight_line(u, v):
            raise ValueError(f"edge {u}->{v} is shorter than the straight line between its ends")
        t = length / speed
        self.adj[u].append((v, t))
        self.radj[v].append((u, t))
        self.max_speed = max(self.max_speed, speed)

    def check_node(self, u: int) -> None:
        if not isinstance(u, int) or not 0 <= u < self.num_nodes:
            raise ValueError(f"node {u!r} is not in the graph (0..{self.num_nodes - 1})")

    # ---- file format ---------------------------------------------------
    # n <id> <x> <y>                 node ids must be 0, 1, 2, ... in order
    # e <from> <to> <length_m> <speed_kmh>
    # lines starting with '#' are comments

    def save(self, path: str | Path, edges: list[tuple[int, int, float, float]]) -> None:
        with open(path, "w") as f:
            f.write(f"# {self.num_nodes} nodes, {len(edges)} edges\n")
            for i, (x, y) in enumerate(zip(self.xs, self.ys)):
                f.write(f"n {i} {x:.3f} {y:.3f}\n")
            for u, v, length, speed in edges:
                f.write(f"e {u} {v} {length:.3f} {speed * 3.6:.1f}\n")

    @classmethod
    def load(cls, path: str | Path) -> "Graph":
        g = cls()
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                parts = line.split()
                if not parts or parts[0].startswith("#"):
                    continue
                try:
                    if parts[0] == "n" and len(parts) == 4:
                        if int(parts[1]) != g.num_nodes:
                            raise GraphFormatError("node ids must be consecutive from 0")
                        g.add_node(float(parts[2]), float(parts[3]))
                    elif parts[0] == "e" and len(parts) == 5:
                        u, v, length = int(parts[1]), int(parts[2]), float(parts[3])
                        g.check_node(u)
                        g.check_node(v)
                        # Coordinates and lengths are stored with 3 decimals, so a
                        # perfectly straight road can come back a millimetre
                        # "shorter" than the line between its rounded ends. Clamp
                        # tiny differences (keeps A* exact); reject real ones.
                        line = g.straight_line(u, v)
                        if line - ROUNDING_TOLERANCE_M <= length < line:
                            length = line
                        g.add_edge(u, v, length, float(parts[4]) / 3.6)
                    else:
                        raise GraphFormatError("expected 'n id x y' or 'e from to length speed'")
                except (ValueError, GraphFormatError) as exc:
                    raise GraphFormatError(f"{path}:{lineno}: {exc}") from None
        if g.num_nodes == 0:
            raise GraphFormatError(f"{path}: graph has no nodes")
        return g
