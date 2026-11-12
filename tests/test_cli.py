import pytest

from route_planner.cli import main


@pytest.fixture
def city(tmp_path):
    path = tmp_path / "city.graph"
    assert main(["generate", "--size", "20", "--seed", "1", "-o", str(path)]) == 0
    return str(path)


def test_route_prints_travel_time(city, capsys):
    assert main(["route", city, "0", "399", "--algo", "bidirectional", "--show-path"]) == 0
    out = capsys.readouterr().out
    assert "travel time:" in out and "path: 0 " in out


def test_bench_reports_agreement(city, capsys):
    assert main(["bench", city, "--queries", "20"]) == 0
    out = capsys.readouterr().out
    assert "all algorithms agreed" in out
    for name in ("dijkstra", "astar", "bidirectional"):
        assert name in out


def test_unknown_node_exits_with_message(city, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["route", city, "0", "100000"])
    assert "not in the graph" in str(exc.value)


def test_missing_file_exits_with_message(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["bench", str(tmp_path / "nope.graph")])
    assert "cannot read" in str(exc.value)


def test_invalid_size_is_rejected(tmp_path):
    with pytest.raises(SystemExit):
        main(["generate", "--size", "1", "-o", str(tmp_path / "x")])


def test_plot_writes_png(city, tmp_path):
    pytest.importorskip("matplotlib")
    out = tmp_path / "search.png"
    assert main(["plot", city, "0", "399", "-o", str(out)]) == 0
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_creates_missing_output_directory(tmp_path):
    out = tmp_path / "data" / "nested" / "city.graph"
    assert main(["generate", "--size", "5", "-o", str(out)]) == 0
    assert out.exists()
