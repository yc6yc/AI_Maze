from __future__ import annotations

"""
global_greedy.py — 直接全局贪心策略
----------------------------------------------------
与旧的“局部 3×3 贪心 + 全局 fallback”不同，
本策略每一回合都基于当前已探索的全部 fog_map 已知区域做决策：

1. 扫描所有已知且可达的候选目标：金币 / 前沿 / BOSS / 出口
2. 用“目标价值 / 实际路径代价”的端到端评分选择最佳目标
3. 只执行最佳路径的第一步
4. 下一回合重新扫描和评分

注意：
- 仅使用 ctx.maze.fog_map，不读取完整地图
- 不穿越 fog_map == None 的未知区域
- BOSS 策略调整为：只要金币够 1 次重试即可允许冲 BOSS
"""

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent
from core.pathfinding import astar, dijkstra, extract_path
from core.state import (
    Action,
    GameContext,
    MazeState,
    CELL_BOSS,
    CELL_COIN,
    CELL_END,
    CELL_GOLD,
    CELL_TRAP,
)

Pos = Tuple[int, int]

DEFAULT_CONFIG = {
    "coin_value": 50.0,
    "frontier_value": 14.0,
    "boss_value": 120.0,
    "exit_value": 1000000.0,
    "trap_penalty": 30.0,
    "trap_step_cost": 31.0,
    "target_retry_buffer": 1,
    "frontier_unknown_weight": 4.0,
    "revisit_penalty": 0.15,
    "min_explore_before_boss": 0.25,
}


class GlobalGreedyAgent(BaseAgent):
    def __init__(self, config: dict = None):
        super().__init__(name="GlobalGreedyAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self._prev_coin: int = 0
        self._prev_boss_count: int = 0
        self._known_bosses: List[Pos] = []
        self._visit_count: Dict[Pos, int] = {}

    def on_episode_start(self, ctx: GameContext):
        self._prev_coin = ctx.player.coins
        self._prev_boss_count = len(ctx.boss_defeated)
        self._known_bosses = []
        self._visit_count = {ctx.player.pos: 1}

    def on_episode_end(self, ctx: GameContext):
        pass

    def decide(self, ctx: GameContext) -> Action:
        self._scan_bosses(ctx.maze)
        self._mark_current_visit(ctx.player.pos)

        candidates = self._enumerate_candidates(ctx)
        if not candidates:
            self._prev_coin = ctx.player.coins
            self._prev_boss_count = len(ctx.boss_defeated)
            return Action(move="STAY")

        best_score = float("-inf")
        best_path: List[Pos] = []
        for _, goal, score, path in candidates:
            if path and score > best_score:
                best_score = score
                best_path = path

        self._prev_coin = ctx.player.coins
        self._prev_boss_count = len(ctx.boss_defeated)

        if not best_path:
            return Action(move="STAY")
        return Action(move=_pos_to_move(ctx.player.pos, best_path[0]))

    def _enumerate_candidates(self, ctx: GameContext) -> List[Tuple[str, Pos, float, List[Pos]]]:
        maze = ctx.maze
        pos = ctx.player.pos
        trap_cost = self.cfg["trap_step_cost"]

        def weight_fn(r: int, c: int) -> float:
            cell = maze.fog_map[r][c]
            if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
                return 1.0 + trap_cost
            return 1.0

        dist_map, prev = dijkstra(maze, pos, weight_fn=weight_fn)
        candidates: List[Tuple[str, Pos, float, List[Pos]]] = []

        for r in range(maze.rows):
            for c in range(maze.cols):
                cell = maze.fog_map[r][c]
                target = (r, c)
                if cell is None or target == pos:
                    continue
                if target not in dist_map:
                    continue

                path = extract_path(prev, pos, target)
                if not path:
                    continue
                move_path = path[1:]
                if not move_path:
                    continue

                distance_cost = dist_map[target]
                revisit_penalty = self.cfg["revisit_penalty"] * self._visit_count.get(target, 0)

                if cell in (CELL_COIN, CELL_GOLD):
                    score = self.cfg["coin_value"] / max(distance_cost, 1.0) - revisit_penalty
                    if self._should_force_collect(ctx):
                        score += 20.0
                    candidates.append(("coin", target, score, move_path))
                elif cell == CELL_BOSS:
                    score = self._score_boss_target(ctx, target, distance_cost) - revisit_penalty
                    candidates.append(("boss", target, score, move_path))
                elif cell == CELL_END and self._bosses_cleared(ctx):
                    score = self.cfg["exit_value"] / max(distance_cost, 1.0)
                    candidates.append(("exit", target, score, move_path))

        for frontier in self._find_frontiers(maze):
            if frontier == pos or frontier not in dist_map:
                continue
            path = extract_path(prev, pos, frontier)
            if not path:
                continue
            move_path = path[1:]
            if not move_path:
                continue
            distance_cost = dist_map[frontier]
            unknown_count = self._count_unknown_neighbors(maze, frontier)
            raw_value = self.cfg["frontier_value"] + self.cfg["frontier_unknown_weight"] * unknown_count
            score = raw_value / max(distance_cost, 1.0) - self.cfg["revisit_penalty"] * self._visit_count.get(frontier, 0)
            candidates.append(("frontier", frontier, score, move_path))

        return candidates

    def _score_boss_target(self, ctx: GameContext, target: Pos, distance_cost: float) -> float:
        if self._bosses_cleared(ctx):
            return -1e9

        coins = ctx.player.coins
        need = max(ctx.coin_consumption * self.cfg["target_retry_buffer"], ctx.coin_consumption)
        explored_ratio = self._explored_ratio(ctx.maze)
        ready = coins >= need

        base = self.cfg["boss_value"] / max(distance_cost, 1.0)
        if ready:
            base += 40.0
        else:
            base -= max(0.0, need - coins)

        if explored_ratio < self.cfg["min_explore_before_boss"] and not ready:
            base -= 25.0
        return base

    def _should_force_collect(self, ctx: GameContext) -> bool:
        if not self._known_bosses:
            return False
        need = max(ctx.coin_consumption * self.cfg["target_retry_buffer"], ctx.coin_consumption)
        return ctx.player.coins < need

    def _bosses_cleared(self, ctx: GameContext) -> bool:
        self._known_bosses = [pos for pos in self._known_bosses if ctx.maze.fog_map[pos[0]][pos[1]] == CELL_BOSS]
        return len(self._known_bosses) == 0 and len(ctx.boss_defeated) > 0

    def _scan_bosses(self, maze: MazeState) -> None:
        known = []
        for r in range(maze.rows):
            for c in range(maze.cols):
                if maze.fog_map[r][c] == CELL_BOSS:
                    known.append((r, c))
        self._known_bosses = known

    def _find_frontiers(self, maze: MazeState) -> List[Pos]:
        frontiers: List[Pos] = []
        for r in range(maze.rows):
            for c in range(maze.cols):
                if not maze.is_walkable(r, c):
                    continue
                if any(maze.fog_map[nr][nc] is None for nr, nc in maze.neighbors(r, c)):
                    frontiers.append((r, c))
        return frontiers

    def _count_unknown_neighbors(self, maze: MazeState, pos: Pos) -> int:
        return sum(1 for nr, nc in maze.neighbors(*pos) if maze.fog_map[nr][nc] is None)

    def _explored_ratio(self, maze: MazeState) -> float:
        total = maze.rows * maze.cols
        explored = sum(
            1
            for r in range(maze.rows)
            for c in range(maze.cols)
            if maze.fog_map[r][c] is not None
        )
        return explored / total if total else 0.0

    def _mark_current_visit(self, pos: Pos) -> None:
        self._visit_count[pos] = self._visit_count.get(pos, 0) + 1


def _pos_to_move(src: Pos, dst: Pos) -> str:
    dr = dst[0] - src[0]
    dc = dst[1] - src[1]
    if dr == -1:
        return "UP"
    if dr == 1:
        return "DOWN"
    if dc == -1:
        return "LEFT"
    if dc == 1:
        return "RIGHT"
    return "STAY"
