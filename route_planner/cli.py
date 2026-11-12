"""Command-line interface.

    python -m route_planner generate --size 120 --seed 7 -o city.graph
    python -m route_planner route city.graph 0 14399 --algo astar
    python -m route_planner bench city.graph --queries 200
    python -m route_planner plot city.graph 0 14399 -o search.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bench import ResultMismatch, format_table, random_queries, run_benchmark
from .generate import generate_city
from .graph import Graph, GraphFormatError
from .search import ALGORITHMS


def _load(path: str) -> Graph:
    try:
        return Graph.load(path)
    except OSError as exc:
        sys.exit(f"error: cannot read {path}: {exc.strerror}")
    except GraphFormatError as exc:
        sys.exit(f"error: {exc}")


def cmd_generate(a) -> int:
    g, edges = generate_city(a.size, a.seed, arterial_kmh=a.arterial_kmh)
    out = Path(a.output)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        g.save(out, edges)
    except OSError as exc:
        sys.exit(f"error: cannot write {out}: {exc.strerror}")
    print(f"wrote {a.output}: {g.num_nodes} nodes, {g.num_edges} directed edges")
    return 0


def cmd_route(a) -> int:
    g = _load(a.graph)
    try:
        res = ALGORITHMS[a.algo](g, a.source, a.target)
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    if not res.found:
        print(f"no route from {a.source} to {a.target} ({res.settled} nodes settled)")
        return 1
    print(f"travel time: {res.cost / 60:.2f} min over {len(res.path) - 1} road segments")
    print(f"nodes settled by {a.algo}: {res.settled}")
    if a.show_path:
        print("path:", " ".join(map(str, res.path)))
    return 0


def cmd_bench(a) -> int:
    g = _load(a.graph)
    queries = random_queries(g, a.queries, a.seed)
    try:
        stats, unreachable = run_benchmark(g, queries)
    except ResultMismatch as exc:
        print(f"MISMATCH: {exc}", file=sys.stderr)
        return 2
    print(f"{g.num_nodes} nodes, {g.num_edges} edges, {len(queries)} random queries "
          f"({unreachable} unreachable); all algorithms agreed on every travel time\n")
    print(format_table(stats))
    return 0


def cmd_plot(a) -> int:
    g = _load(a.graph)
    try:
        from .plot import plot_search_areas
        plot_search_areas(g, a.source, a.target, a.output)
    except ImportError:
        sys.exit("error: plotting needs matplotlib (pip install matplotlib)")
    except ValueError as exc:
        sys.exit(f"error: {exc}")
    print(f"wrote {a.output}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="route_planner", description="Compare shortest-path algorithms on a road graph.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("generate", help="generate a synthetic city graph")
    s.add_argument("--size", type=int, default=100, help="grid is size x size (default 100)")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--arterial-kmh", type=float, default=70.0,
                   help="speed on arterial roads; streets are 30 (default 70)")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(fn=cmd_generate)

    s = sub.add_parser("route", help="find the fastest route between two nodes")
    s.add_argument("graph")
    s.add_argument("source", type=int)
    s.add_argument("target", type=int)
    s.add_argument("--algo", choices=ALGORITHMS, default="astar")
    s.add_argument("--show-path", action="store_true")
    s.set_defaults(fn=cmd_route)

    s = sub.add_parser("bench", help="compare algorithms on random queries")
    s.add_argument("graph")
    s.add_argument("--queries", type=int, default=200)
    s.add_argument("--seed", type=int, default=1)
    s.set_defaults(fn=cmd_bench)

    s = sub.add_parser("plot", help="draw the nodes each algorithm settled")
    s.add_argument("graph")
    s.add_argument("source", type=int)
    s.add_argument("target", type=int)
    s.add_argument("-o", "--output", default="search.png")
    s.set_defaults(fn=cmd_plot)

    a = p.parse_args(argv)
    if getattr(a, "size", 2) < 2 or getattr(a, "queries", 1) < 1 or getattr(a, "arterial_kmh", 1) <= 0:
        p.error("--size must be >= 2, --queries >= 1 and --arterial-kmh > 0")
    return a.fn(a)
