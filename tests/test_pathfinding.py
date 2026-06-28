from core.pathfinding import astar, bfs, dijkstra, extract_path
from core.state import MazeState


def make_maze() -> MazeState:
    fog = [
        ["S", " ", "#", "E"],
        ["#", " ", " ", " "],
        ["#", "#", " ", "#"],
    ]
    return MazeState(rows=3, cols=4, fog_map=fog, start=(0, 0), end=(0, 3))


def test_bfs_finds_shortest_known_path() -> None:
    maze = make_maze()
    path = bfs(maze, (0, 0), (0, 3))
    assert path == [(0, 0), (0, 1), (1, 1), (1, 2), (1, 3), (0, 3)]


def test_astar_matches_reachable_goal() -> None:
    maze = make_maze()
    path = astar(maze, (0, 0), (0, 3))
    assert path[0] == (0, 0)
    assert path[-1] == (0, 3)


def test_dijkstra_respects_unknown_as_blocked() -> None:
    maze = MazeState(rows=1, cols=3, fog_map=[["S", None, "E"]], start=(0, 0), end=(0, 2))
    dist, _came = dijkstra(maze, (0, 0))
    assert (0, 2) not in dist


def test_extract_path_alias_reconstructs_dijkstra_path() -> None:
    maze = make_maze()
    _dist, came = dijkstra(maze, (0, 0), (0, 3))
    assert extract_path(came, (0, 0), (0, 3)) == [(0, 0), (0, 1), (1, 1), (1, 2), (1, 3), (0, 3)]
