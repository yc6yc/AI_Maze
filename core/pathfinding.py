from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from math import inf
from typing import Callable

from .state import CARDINAL_MOVES, MazeState, Position, move_to_delta


WalkableFn = Callable[[Position], bool]
CostFn = Callable[[Position], float]


def neighbors(pos: Position, maze: MazeState, walkable_override: WalkableFn | None = None) -> list[Position]:
    walkable = walkable_override or maze.is_walkable
    result: list[Position] = []
    r, c = pos
    for move in CARDINAL_MOVES:
        dr, dc = move_to_delta(move)
        nxt = (r + dr, c + dc)
        if maze.in_bounds(nxt) and walkable(nxt):
            result.append(nxt)
    return result


def reconstruct_path(came_from: dict[Position, Position], start: Position, goal: Position) -> list[Position]:
    if goal == start:
        return [start]
    if goal not in came_from:
        return []
    path = [goal]
    cur = goal
    while cur != start:
        cur = came_from[cur]
        path.append(cur)
    path.reverse()
    return path


def extract_path(came_from: dict[Position, Position], start: Position, goal: Position) -> list[Position]:
    """Compatibility alias for Dijkstra-style predecessor maps."""
    return reconstruct_path(came_from, start, goal)


def bfs(
    maze: MazeState,
    start: Position,
    goal: Position | None = None,
    walkable_override: WalkableFn | None = None,
) -> list[Position] | dict[Position, int]:
    walkable = walkable_override or maze.is_walkable
    if not maze.in_bounds(start) or not walkable(start):
        return [] if goal is not None else {}

    queue: deque[Position] = deque([start])
    dist: dict[Position, int] = {start: 0}
    came_from: dict[Position, Position] = {}

    while queue:
        cur = queue.popleft()
        if goal is not None and cur == goal:
            return reconstruct_path(came_from, start, goal)
        for nxt in neighbors(cur, maze, walkable):
            if nxt in dist:
                continue
            dist[nxt] = dist[cur] + 1
            came_from[nxt] = cur
            queue.append(nxt)

    if goal is not None:
        return []
    return dist


def astar(
    maze: MazeState,
    start: Position,
    goal: Position,
    walkable_override: WalkableFn | None = None,
    cost_fn: CostFn | None = None,
) -> list[Position]:
    walkable = walkable_override or maze.is_walkable
    if not maze.in_bounds(start) or not maze.in_bounds(goal):
        return []
    if not walkable(start) or not walkable(goal):
        return []

    def heuristic(pos: Position) -> int:
        return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])

    cost = cost_fn or (lambda _pos: 1.0)
    open_heap: list[tuple[float, Position]] = [(heuristic(start), start)]
    came_from: dict[Position, Position] = {}
    g_score: dict[Position, float] = {start: 0.0}

    while open_heap:
        _priority, cur = heappop(open_heap)
        if cur == goal:
            return reconstruct_path(came_from, start, goal)
        for nxt in neighbors(cur, maze, walkable):
            tentative = g_score[cur] + max(cost(nxt), 0.0)
            if tentative >= g_score.get(nxt, inf):
                continue
            came_from[nxt] = cur
            g_score[nxt] = tentative
            heappush(open_heap, (tentative + heuristic(nxt), nxt))
    return []


def dijkstra(
    maze: MazeState,
    start: Position,
    goal: Position | None = None,
    walkable_override: WalkableFn | None = None,
    cost_fn: CostFn | None = None,
) -> tuple[dict[Position, float], dict[Position, Position]]:
    walkable = walkable_override or maze.is_walkable
    if not maze.in_bounds(start) or not walkable(start):
        return {}, {}

    cost = cost_fn or (lambda _pos: 1.0)
    heap: list[tuple[float, Position]] = [(0.0, start)]
    dist: dict[Position, float] = {start: 0.0}
    came_from: dict[Position, Position] = {}

    while heap:
        cur_cost, cur = heappop(heap)
        if cur_cost > dist[cur]:
            continue
        if goal is not None and cur == goal:
            break
        for nxt in neighbors(cur, maze, walkable):
            nxt_cost = cur_cost + max(cost(nxt), 0.0)
            if nxt_cost >= dist.get(nxt, inf):
                continue
            dist[nxt] = nxt_cost
            came_from[nxt] = cur
            heappush(heap, (nxt_cost, nxt))
    return dist, came_from
