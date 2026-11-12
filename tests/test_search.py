import math
import random

import pytest

from route_planner import ALGORITHMS, Graph, GraphFormatError, astar, bidirectional_dijkstra, dijkstra
from route_planner.bench import random_queries, run_benchmark
from route_planner.generate import generate_city
from route_planner.search import path_cost

ALGOS = list(ALGORITHMS.values())


def floyd_warshall(g: Graph):
    """O(n^3) reference answer, deliberately written differently from the
    algorithms under test."""
    n = g.num_nodes
    d = [[math.inf] * n for _ in range(n)]
    for u in range(n):
        d[u][u] = 0.0
        for v, w in g.adj[u]:
            d[u][v] = min(d[u][v], w)
    for k in range(n):
        dk = d[k]
        for i in range(n):
            dik = d[i][k]
            if dik == math.inf:
                continue
            di = d[i]
            for j in range(n):
                if dik + dk[j] < di[j]:
                    di[j] = dik + dk[j]
    return d


def random_graph(n: int, edge_prob: float, seed: int) -> Graph:
    """Random directed graph with coordinates; includes parallel edges,
    self-loops and unreachable pairs."""
    rng = random.Random(seed)
    g = Graph()
    for _ in range(n):
        g.add_node(rng.uniform(0, 1000), rng.uniform(0, 1000))
    for u in range(n):
        for v in range(n):
            if rng.random() < edge_prob:
                length = g.straight_line(u, v) * rng.uniform(1.0, 2.0)
                g.add_edge(u, v, length, rng.choice([8.0, 14.0, 25.0]))
    return g


def line_graph() -> Graph:
    """0 -> 1 -> 2 -> 3 along the x axis, plus a slow direct edge 0 -> 3."""
    g = Graph()
    for x in (0, 100, 200, 300):
        g.add_node(x, 0)
    for u in range(3):
        g.add_edge(u, u + 1, 100, 10)       # 10 s each
    g.add_edge(0, 3, 300, 5)                 # 60 s
    return g


# ---- correctness against a reference ---------------------------------

@pytest.mark.parametrize("seed", range(25))
def test_all_algorithms_match_floyd_warshall(seed):
    g = random_graph(n=18, edge_prob=0.12, seed=seed)
    ref = floyd_warshall(g)
    for s in range(g.num_nodes):
        for t in range(g.num_nodes):
            for algo in ALGOS:
                res = algo(g, s, t)
                if ref[s][t] == math.inf:
                    assert not res.found and res.path == [], (algo.__name__, s, t)
                else:
                    assert res.cost == pytest.approx(ref[s][t]), (algo.__name__, s, t)
                    assert res.path[0] == s and res.path[-1] == t
                    assert path_cost(g, res.path) == pytest.approx(res.cost)


def test_algorithms_agree_on_generated_city():
    g, _ = generate_city(30, seed=3)
    stats, _ = run_benchmark(g, random_queries(g, 150, seed=9))  # raises on mismatch
    assert len(stats) == 3


# ---- specific behaviour --------------------------------------------

@pytest.mark.parametrize("algo", ALGOS)
def test_prefers_faster_route_over_fewer_edges(algo):
    res = algo(line_graph(), 0, 3)
    assert res.cost == pytest.approx(30.0)
    assert res.path == [0, 1, 2, 3]


@pytest.mark.parametrize("algo", ALGOS)
def test_source_equals_target(algo):
    res = algo(line_graph(), 2, 2)
    assert res.cost == 0 and res.path == [2]


@pytest.mark.parametrize("algo", ALGOS)
def test_one_way_edges_are_respected(algo):
    res = algo(line_graph(), 3, 0)   # every edge points away from 0
    assert not res.found and res.path == []


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("bad", [-1, 4, 99])
def test_invalid_node_raises(algo, bad):
    with pytest.raises(ValueError):
        algo(line_graph(), 0, bad)


def test_astar_and_bidirectional_settle_fewer_nodes_than_dijkstra():
    g, _ = generate_city(60, seed=5)
    s, t = 0, g.num_nodes - 1
    d = dijkstra(g, s, t).settled
    assert astar(g, s, t).settled < d
    assert bidirectional_dijkstra(g, s, t).settled < d


def test_heuristic_is_admissible_on_generated_city():
    """h(u) must never exceed the true remaining travel time."""
    g, _ = generate_city(15, seed=11)
    ref = floyd_warshall(g)
    t = g.num_nodes // 2
    for u in range(g.num_nodes):
        h = g.straight_line(u, t) / g.max_speed
        assert h <= ref[u][t] + 1e-9


def test_overestimating_heuristic_can_return_a_worse_route():
    """Shows why admissibility matters: a heuristic that overestimates
    makes A* commit to the slow direct edge."""
    g = line_graph()
    greedy = lambda u: 0.0 if u == 3 else 1000.0 * (u != 0)  # noqa: E731
    res = astar(g, 0, 3, heuristic=greedy)
    assert res.cost > dijkstra(g, 0, 3).cost


# ---- graph construction and file format --------------------------------

def test_edge_shorter_than_straight_line_is_rejected():
    g = line_graph()
    with pytest.raises(ValueError):
        g.add_edge(0, 3, 10, 10)


def test_non_positive_speed_is_rejected():
    with pytest.raises(ValueError):
        line_graph().add_edge(0, 1, 100, 0)


def test_save_and_load_round_trip(tmp_path):
    g, edges = generate_city(12, seed=2)
    path = tmp_path / "city.graph"
    g.save(path, edges)
    h = Graph.load(path)
    assert (h.num_nodes, h.num_edges) == (g.num_nodes, g.num_edges)
    for s, t in random_queries(g, 30, seed=4):
        assert dijkstra(h, s, t).cost == pytest.approx(dijkstra(g, s, t).cost, rel=1e-4)


@pytest.mark.parametrize("content", [
    "",                                   # no nodes
    "n 0 0 0\nn 2 1 1\n",                 # ids not consecutive
    "n 0 0 0\nn 1 100 0\ne 0 1 abc 30\n", # bad number
    "n 0 0 0\ne 0 5 10 30\n",             # unknown node
    "n 0 0 0\nn 1 100 0\ne 0 1 50 30\n",  # shorter than straight line
    "x 1 2 3\n",                          # unknown record
])
def test_malformed_files_raise(tmp_path, content):
    path = tmp_path / "bad.graph"
    path.write_text(content)
    with pytest.raises(GraphFormatError):
        Graph.load(path)


def test_generator_is_deterministic():
    a, ea = generate_city(20, seed=42)
    b, eb = generate_city(20, seed=42)
    assert ea == eb and a.xs == b.xs
    assert generate_city(20, seed=43)[1] != ea


@pytest.mark.parametrize("algo", ALGOS)
def test_each_node_is_settled_at_most_once_per_direction(algo):
    """The heap uses lazy deletion, so stale entries must be skipped;
    otherwise nodes get re-expanded (correct answer, wasted work)."""
    g, _ = generate_city(25, seed=8)
    res = algo(g, 0, g.num_nodes - 1)
    if algo is bidirectional_dijkstra:
        assert len(res.settled_nodes) == res.settled
    else:
        assert len(set(res.settled_nodes)) == len(res.settled_nodes) == res.settled


def test_load_tolerates_rounding_on_straight_roads(tmp_path):
    """A road exactly as long as the straight line can come back 1 mm too
    short after coordinates are rounded to 3 decimals in the file."""
    path = tmp_path / "rounded.graph"
    path.write_text("n 0 0.0004 0\nn 1 99.9996 0\ne 0 1 99.999 30\n")
    g = Graph.load(path)
    assert g.num_edges == 1
    assert dijkstra(g, 0, 1).cost == pytest.approx(g.straight_line(0, 1) / (30 / 3.6))
