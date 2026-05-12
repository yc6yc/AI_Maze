"""
global_planner.py — 全局迷宫探索与路径规划
负责人：角色3（算法B）
----------------------------------------------------
阶段状态机（Phase）：
  EXPLORE  -> 未知区域探索（前沿 Frontier 优先）
  COLLECT  -> 全图已探索，贪心收集高价值目标
  RUSH     -> 剩余回合数不足或收益已低，直冲终点

目标函数（step_cost 可在 config 调整）：
  cost(格子) = base_cost
             - coin_gain(格子) * w_coin / (distance+1)
             + trap_risk(格子) * w_trap

全局规划器每回合生成一条「待执行路径」，沿路径走一步；
若路径被阻断（新揭露墙壁），重新规划。
"""

from __future__ import annotations
from enum import Enum, auto
from typing import List, Optional, Set, Tuple

from agents.base_agent import BaseAgent
from core.state import (
    GameContext, Action, MazeState,
    CELL_WALL, CELL_TRAP, CELL_COIN, CELL_GOLD, CELL_END,
)
from core.pathfinding import astar, bfs, dijkstra, extract_path

DEFAULT_CONFIG = {
    "w_coin": 2.0,
    "w_trap": 1.5,
    "base_cost": 1.0,
    "rush_round_threshold": 5,   # 距 minRounds 剩余不足此值时切换 RUSH
}

Pos = Tuple[int, int]


class Phase(Enum):
    EXPLORE = auto()
    COLLECT = auto()
    RUSH    = auto()


class GlobalPlannerAgent(BaseAgent):
    """
    全局规划 Agent，三阶段状态机 + A* 寻路。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="GlobalPlannerAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.phase: Phase = Phase.EXPLORE
        self._path: List[Pos] = []   # 当前待执行路径（不含起点）
        self._visited: Set[Pos] = set()

    # ------------------------------------------------------------------ #
    # 主接口
    # ------------------------------------------------------------------ #
    def decide(self, ctx: GameContext) -> Action:
        player = ctx.player
        maze = ctx.maze
        pos = player.pos
        self._visited.add(pos)

        self._update_phase(ctx)

        # 如果当前路径无效或已空，重新规划
        if not self._path or not maze.is_walkable(*self._path[0]):
            self._replan(ctx)

        if not self._path:
            return Action(move="STAY")

        next_pos = self._path.pop(0)
        move = _pos_to_move(pos, next_pos)
        return Action(move=move)

    def on_episode_start(self, ctx: GameContext):
        self.phase = Phase.EXPLORE
        self._path = []
        self._visited = set()

    # ------------------------------------------------------------------ #
    # 阶段切换
    # ------------------------------------------------------------------ #
    def _update_phase(self, ctx: GameContext):
        rounds_left = ctx.min_rounds - ctx.player.round_num
        if rounds_left <= self.cfg["rush_round_threshold"]:
            self.phase = Phase.RUSH
            return

        # 若仍有未探索格子 -> EXPLORE；否则进入 COLLECT
        has_unknown = any(
            ctx.maze.fog_map[r][c] is None
            for r in range(ctx.maze.rows)
            for c in range(ctx.maze.cols)
        )
        if has_unknown and self.phase == Phase.EXPLORE:
            self.phase = Phase.EXPLORE
        elif not has_unknown and self.phase != Phase.RUSH:
            self.phase = Phase.COLLECT

    # ------------------------------------------------------------------ #
    # 重新规划
    # ------------------------------------------------------------------ #
    def _replan(self, ctx: GameContext):
        pos = ctx.player.pos
        maze = ctx.maze

        if self.phase == Phase.RUSH:
            goal = maze.end
            if goal:
                path = astar(maze, pos, goal)
                self._path = path[1:] if path else []
            return

        if self.phase == Phase.EXPLORE:
            goal = self._nearest_frontier(pos, maze)
        else:  # COLLECT
            goal = self._best_collect_target(pos, maze, ctx)

        if goal is None:
            # 退化：直冲终点
            self.phase = Phase.RUSH
            self._replan(ctx)
            return

        path = astar(
            maze, pos, goal,
            walkable_override=lambda r, c: self._custom_walkable(r, c, maze),
        )
        self._path = path[1:] if path else []

    # ------------------------------------------------------------------ #
    # 前沿探索：找最近的未知格子的可达邻居
    # ------------------------------------------------------------------ #
    def _nearest_frontier(self, pos: Pos, maze: MazeState) -> Optional[Pos]:
        """
        前沿格子：已知可行格子中，有至少一个未知邻居的格子。
        选择距当前位置最近的前沿格子。
        """
        best: Optional[Tuple[float, Pos]] = None
        for r in range(maze.rows):
            for c in range(maze.cols):
                if maze.fog_map[r][c] is None:
                    continue
                if not maze.is_walkable(r, c):
                    continue
                for nr, nc in maze.neighbors(r, c):
                    if maze.fog_map[nr][nc] is None:
                        dist = abs(r - pos[0]) + abs(c - pos[1])
                        if best is None or dist < best[0]:
                            best = (dist, (r, c))
                        break
        return best[1] if best else None

    # ------------------------------------------------------------------ #
    # 收集阶段：性价比最高目标
    # ------------------------------------------------------------------ #
    def _best_collect_target(
        self, pos: Pos, maze: MazeState, ctx: GameContext
    ) -> Optional[Pos]:
        """
        枚举地图上所有金币/奖励格子，
        计算 value / distance 性价比，选最高者。
        """
        best_score = -1e9
        best_pos: Optional[Pos] = None

        for r in range(maze.rows):
            for c in range(maze.cols):
                cell = maze.fog_map[r][c]
                if cell not in (CELL_COIN, CELL_GOLD):
                    continue
                dist = abs(r - pos[0]) + abs(c - pos[1]) + 1
                score = self.cfg["w_coin"] * 50 / dist
                if score > best_score:
                    best_score = score
                    best_pos = (r, c)

        return best_pos

    # ------------------------------------------------------------------ #
    # 自定义可行性（规避已知陷阱，除非被迫）
    # ------------------------------------------------------------------ #
    def _custom_walkable(self, r: int, c: int, maze: MazeState) -> bool:
        if not maze.is_walkable(r, c):
            return False
        cell = maze.fog_map[r][c]
        if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            return False   # 尽量绕开未触发陷阱
        return True


def _pos_to_move(src: Pos, dst: Pos) -> str:
    dr = dst[0] - src[0]
    dc = dst[1] - src[1]
    if dr == -1: return "UP"
    if dr ==  1: return "DOWN"
    if dc == -1: return "LEFT"
    if dc ==  1: return "RIGHT"
    return "STAY"
