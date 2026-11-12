"""Draw which nodes each algorithm settled for one query (needs matplotlib)."""
from __future__ import annotations

from .graph import Graph
from .search import ALGORITHMS


def plot_search_areas(g: Graph, source: int, target: int, out_path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    segments, fast = [], []
    for u in range(g.num_nodes):
        for v, w in g.adj[u]:
            seg = [(g.xs[u], g.ys[u]), (g.xs[v], g.ys[v])]
            # arterials have the highest speed: travel time per metre is lowest
            (fast if g.straight_line(u, v) / w > 15 else segments).append(seg)

    names = list(ALGORITHMS)
    fig, axes = plt.subplots(1, len(names), figsize=(5.2 * len(names), 5.6))
    for ax, name in zip(axes, names):
        res = ALGORITHMS[name](g, source, target)
        ax.add_collection(LineCollection(segments, colors="#dcdcdc", linewidths=0.5))
        ax.add_collection(LineCollection(fast, colors="#b4b4b4", linewidths=1.4))
        sx = [g.xs[u] for u in res.settled_nodes]
        sy = [g.ys[u] for u in res.settled_nodes]
        ax.scatter(sx, sy, s=9, color="#2f6db5", alpha=0.75, linewidths=0, zorder=2)
        ax.plot([g.xs[u] for u in res.path], [g.ys[u] for u in res.path], color="#e4572e", linewidth=2.4, zorder=3)
        ax.scatter([g.xs[source], g.xs[target]], [g.ys[source], g.ys[target]], s=50,
                   color="#111111", zorder=4)
        ax.set_title(f"{name}\n{res.settled} nodes settled · {res.cost / 60:.1f} min")
        ax.set_aspect("equal")
        ax.autoscale()
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Same query, three algorithms (blue = settled nodes, red = fastest route, thick grey = arterial roads)")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
