"""Measure how arterial-road speed affects A* and bidirectional search.

    python3 scripts/speed_sweep.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from route_planner.generate import generate_city
from route_planner.bench import random_queries, run_benchmark
print(f"{'arterial km/h':>14}{'astar vs dijkstra':>19}{'bidir vs dijkstra':>19}")
for kmh in (30, 50, 70, 100, 130):
    g, _ = generate_city(150, seed=7, arterial_kmh=kmh)
    st, _ = run_benchmark(g, random_queries(g, 300, seed=1))
    d = {s.name: s.mean_settled for s in st}
    print(f"{kmh:>14}{d['astar']/d['dijkstra']:>18.2f}x{d['bidirectional']/d['dijkstra']:>18.2f}x")
