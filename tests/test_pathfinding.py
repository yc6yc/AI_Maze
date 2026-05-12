"""
tests/test_pathfinding.py — 寻路算法单元测试
负责人：角色4（评测）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.state import MazeState
from core.pathfinding import bfs, astar, dijkstra, extract_path

# 5×5 测试地图
GRID = [
    ["#", "#", "#", "#", "#"],
    ["#", "S", " ", " ", "#"],
    ["#", "#", "#", " ", "#"],
    ["#", " ", " ", " ", "#"],
    ["#", "#", "#", "E", "#"],
]


@pytest.fixture
def maze():
    return MazeState.from_full_map(GRID)


def test_bfs_finds_path(maze):
    path = bfs(maze, (1, 1), (4, 3))
    assert path is not None
    assert path[0] == (1, 1)
    assert path[-1] == (4, 3)


def test_astar_same_length_as_bfs(maze):
    p_bfs = bfs(maze, (1, 1), (4, 3))
    p_astar = astar(maze, (1, 1), (4, 3))
    assert p_astar is not None
    assert len(p_astar) == len(p_bfs)


def test_bfs_no_path():
    grid = [
        ["#", "#", "#"],
        ["#", "S", "#"],
        ["#", "#", "E"],
    ]
    m = MazeState.from_full_map(grid)
    path = bfs(m, (1, 1), (2, 2))
    assert path is None


def test_dijkstra(maze):
    dist, prev = dijkstra(maze, (1, 1))
    path = extract_path(prev, (1, 1), (4, 3))
    assert path is not None
    assert path[-1] == (4, 3)
