"""
pathfinding.py — 通用寻路算法库
负责人：角色3（全局规划），角色2（局部贪心）共用
------------------------------------------------
提供：
  - BFS（无权最短路径）
  - A*（启发式最短路径）
  - Dijkstra（带权最短路径）
"""

from __future__ import annotations
import heapq
from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

from core.state import MazeState


# 坐标类型
Pos = Tuple[int, int]


# --------------------------------------------------------------------------- #
# BFS
# --------------------------------------------------------------------------- #
def bfs(
    maze: MazeState,
    start: Pos,
    goal: Pos,
    walkable_override: Optional[Callable[[int, int], bool]] = None,
) -> Optional[List[Pos]]:
    """
    BFS 最短路径。返回从 start 到 goal 的格子列表（含两端），
    若不可达返回 None。
    walkable_override: 可选的自定义可通行判断函数 (r, c) -> bool
    """
    is_walkable = walkable_override or maze.is_walkable

    visited: Dict[Pos, Optional[Pos]] = {start: None}
    queue: deque[Pos] = deque([start])

    while queue:
        cur = queue.popleft()
        if cur == goal:
            return _reconstruct(visited, start, goal)
        r, c = cur
        for nr, nc in maze.neighbors(r, c):
            nxt = (nr, nc)
            if nxt not in visited and is_walkable(nr, nc):
                visited[nxt] = cur
                queue.append(nxt)
    return None


# --------------------------------------------------------------------------- #
# A*
# --------------------------------------------------------------------------- #
def astar(
    maze: MazeState,
    start: Pos,
    goal: Pos,
    walkable_override: Optional[Callable[[int, int], bool]] = None,
    heuristic: Callable[[Pos, Pos], float] = None,
) -> Optional[List[Pos]]:
    """
    A* 最短路径。默认曼哈顿距离启发函数。
    """
    is_walkable = walkable_override or maze.is_walkable
    h = heuristic or _manhattan

    g_score: Dict[Pos, float] = {start: 0}
    came_from: Dict[Pos, Optional[Pos]] = {start: None}
    # heap: (f, g, pos)
    heap: List[Tuple[float, float, Pos]] = [(h(start, goal), 0, start)]

    while heap:
        f, g, cur = heapq.heappop(heap)
        if cur == goal:
            return _reconstruct(came_from, start, goal)
        if g > g_score.get(cur, float("inf")):
            continue
        r, c = cur
        for nr, nc in maze.neighbors(r, c):
            nxt = (nr, nc)
            if not is_walkable(nr, nc):
                continue
            ng = g + 1
            if ng < g_score.get(nxt, float("inf")):
                g_score[nxt] = ng
                came_from[nxt] = cur
                heapq.heappush(heap, (ng + h(nxt, goal), ng, nxt))
    return None


# --------------------------------------------------------------------------- #
# Dijkstra（带权）
# --------------------------------------------------------------------------- #
def dijkstra(
    maze: MazeState,
    start: Pos,
    goal: Optional[Pos] = None,
    weight_fn: Callable[[int, int], float] = None,
) -> Tuple[Dict[Pos, float], Dict[Pos, Optional[Pos]]]:
    """
    Dijkstra 算法。返回 (dist, prev) 字典。
    weight_fn: (r, c) -> float，格子代价（默认 1）。
    若指定 goal，找到即提前退出。
    """
    w = weight_fn or (lambda r, c: 1.0)

    dist: Dict[Pos, float] = {start: 0.0}
    prev: Dict[Pos, Optional[Pos]] = {start: None}
    heap: List[Tuple[float, Pos]] = [(0.0, start)]

    while heap:
        d, cur = heapq.heappop(heap)
        if cur == goal:
            break
        if d > dist.get(cur, float("inf")):
            continue
        r, c = cur
        for nr, nc in maze.neighbors(r, c):
            nxt = (nr, nc)
            if not maze.is_walkable(nr, nc):
                continue
            nd = d + w(nr, nc)
            if nd < dist.get(nxt, float("inf")):
                dist[nxt] = nd
                prev[nxt] = cur
                heapq.heappush(heap, (nd, nxt))

    return dist, prev


def extract_path(prev: Dict[Pos, Optional[Pos]], start: Pos, goal: Pos) -> Optional[List[Pos]]:
    """从 Dijkstra prev 字典重建路径"""
    if goal not in prev:
        return None
    return _reconstruct(prev, start, goal)


# --------------------------------------------------------------------------- #
# 内部工具
# --------------------------------------------------------------------------- #
def _reconstruct(came_from: Dict[Pos, Optional[Pos]], start: Pos, goal: Pos) -> List[Pos]:
    path: List[Pos] = []
    cur: Optional[Pos] = goal
    while cur is not None:
        path.append(cur)
        cur = came_from.get(cur)
    path.reverse()
    return path


def _manhattan(a: Pos, b: Pos) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
