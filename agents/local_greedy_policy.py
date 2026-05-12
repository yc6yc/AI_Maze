"""
local_greedy_policy.py — 局部贪心拾取策略（3×3 视野）
负责人：角色2（算法A）
---------------------------------------------------------
核心思路：
  在当前位置的 3×3 邻域内，计算每个可达格子的「性价比」，
  优先移动到性价比最高的格子。

性价比函数（可在 config.yaml 调整权重）：
  score(cell) = coin_value(cell) * w_coin
              - trap_penalty(cell) * w_trap
              - distance_cost(cell) * w_dist

  - coin_value: G/C -> config["coin_value"], 0 otherwise
  - trap_penalty: T -> config["trap_penalty"] (陷阱一次触发)
  - distance_cost: 到该格曼哈顿距离

已触发陷阱记录在 maze.triggered_traps，不重复扣分。
"""

from __future__ import annotations
from typing import List, Tuple, Optional

from agents.base_agent import BaseAgent
from core.state import (
    GameContext, Action, MazeState,
    CELL_TRAP, CELL_COIN, CELL_GOLD, CELL_WALL,
)
from core.pathfinding import bfs

# 默认权重（由 config 注入后覆盖）
DEFAULT_CONFIG = {
    "coin_value": 50,       # G/C 的金币价值
    "trap_penalty": 30,     # 陷阱触发扣分
    "w_coin": 1.0,
    "w_trap": 1.0,
    "w_dist": 0.5,
}


class LocalGreedyAgent(BaseAgent):
    """
    局部贪心拾取 Agent。
    只观测当前位置 ±1 的 3×3 窗口内已知格子。
    若 3×3 内无收益目标，则委托全局规划提供下一步方向。
    """

    def __init__(self, config: dict = None, fallback_agent=None):
        super().__init__(name="LocalGreedyAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.fallback_agent = fallback_agent   # 无局部目标时调用全局规划

    # ------------------------------------------------------------------ #
    # 主接口
    # ------------------------------------------------------------------ #
    def decide(self, ctx: GameContext) -> Action:
        r, c = ctx.player.pos
        maze = ctx.maze

        candidates = self._score_neighbors(r, c, maze, ctx)

        if candidates:
            # 按性价比降序，选最高分
            candidates.sort(key=lambda x: x[1], reverse=True)
            best_pos, best_score = candidates[0]
            if best_score > 0:
                move = self._pos_to_move(r, c, best_pos)
                return Action(move=move)

        # 无局部收益 -> 交给 fallback
        if self.fallback_agent is not None:
            return self.fallback_agent.decide(ctx)
        return Action(move="STAY")

    # ------------------------------------------------------------------ #
    # 性价比计算
    # ------------------------------------------------------------------ #
    def _score_neighbors(
        self,
        r: int,
        c: int,
        maze: MazeState,
        ctx: GameContext,
    ) -> List[Tuple[Tuple[int, int], float]]:
        """计算 3×3 范围内每个已知可达格子的性价比"""
        results = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < maze.rows and 0 <= nc < maze.cols):
                    continue
                cell = maze.get(nr, nc)
                if cell is None or cell == CELL_WALL:
                    continue
                # 必须可直接移动（上下左右）
                if abs(dr) + abs(dc) != 1:
                    continue
                score = self._cell_score(nr, nc, cell, maze)
                results.append(((nr, nc), score))
        return results

    def _cell_score(
        self,
        r: int, c: int,
        cell: str,
        maze: MazeState,
    ) -> float:
        cfg = self.cfg
        coin_v = 0.0
        trap_v = 0.0
        dist_v = 1.0   # 相邻格距离恒为1

        if cell in (CELL_COIN, CELL_GOLD):
            coin_v = cfg["coin_value"]
        if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            trap_v = cfg["trap_penalty"]

        score = (
            coin_v * cfg["w_coin"]
            - trap_v * cfg["w_trap"]
            - dist_v * cfg["w_dist"]
        )
        return score

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _pos_to_move(r: int, c: int, target: Tuple[int, int]) -> str:
        dr = target[0] - r
        dc = target[1] - c
        if dr == -1: return "UP"
        if dr ==  1: return "DOWN"
        if dc == -1: return "LEFT"
        if dc ==  1: return "RIGHT"
        return "STAY"
