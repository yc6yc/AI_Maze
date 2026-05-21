"""
local_greedy_policy.py — 局部贪心拾取策略（完整 3×3 视野）
负责人：角色2（算法A）
---------------------------------------------------------
核心思路（对应 txt 策略文档）：

一、确认可达集
  1. 从中心格出发，检查上下左右 4 个直接邻居是否可走，
     可走的加入中心格的可达集 S_center。
  2. 对 S_center 中的每个方向格 j，检查从 j 可到达的
     对角邻居（仍在 3×3 视野内），可走的加入 j 的可达集 S_j。

二、贪心选方向
  对 S_center 中每个方向 d，计算方向得分：
    score(d) = cell_value(直接邻居) / 1
             + Σ cell_value(对角邻居) / 2  （对角邻居 ∈ S_d）

  格子价值：金币=+coin_value，陷阱=-trap_penalty，
           已访问空格=-visited_penalty，其余=0

  选得分最高的方向走；多个并列则随机选一个。

已触发陷阱记录在 maze.triggered_traps，不重复扣分。
"""

from __future__ import annotations
import random
from typing import Dict, List, Set, Tuple

from agents.base_agent import BaseAgent
from core.state import (
    GameContext, Action, MazeState,
    CELL_TRAP, CELL_COIN, CELL_GOLD,
)

DEFAULT_CONFIG = {
    "coin_value": 50,
    "trap_penalty": 30,
    "visited_penalty": 1,
    "w_coin": 1.0,
    "w_trap": 1.0,
}

# 每个方向：直接邻居偏移 + 可经由该方向到达的两个对角邻居偏移
DIRECTION_MAP: Dict[str, dict] = {
    "UP":    {"direct": (-1,  0), "diagonals": [(-1, -1), (-1,  1)]},
    "DOWN":  {"direct": ( 1,  0), "diagonals": [( 1, -1), ( 1,  1)]},
    "LEFT":  {"direct": ( 0, -1), "diagonals": [(-1, -1), ( 1, -1)]},
    "RIGHT": {"direct": ( 0,  1), "diagonals": [(-1,  1), ( 1,  1)]},
}


class LocalGreedyAgent(BaseAgent):
    """
    局部贪心拾取 Agent。
    先确定中心格可达集（哪些方向可走），
    再对每个可走方向建其子可达集并计算累计得分，
    选得分最高的方向走。
    """

    def __init__(self, config: dict = None):
        super().__init__(name="LocalGreedyAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self._prev_pos = None   # 上一步所在位置

    # ------------------------------------------------------------------ #
    # 主接口
    # ------------------------------------------------------------------ #
    def decide(self, ctx: GameContext) -> Action:
        r, c = ctx.player.pos
        maze = ctx.maze
        visited: Set[Tuple] = {tuple(snap["pos"]) for snap in ctx.history}

        # ── 步骤一：建中心格可达集 ──────────────────────────────────────
        # S_center: move -> 直接邻居坐标（仅可走的方向）
        s_center: Dict[str, Tuple[int, int]] = {}
        for move, offsets in DIRECTION_MAP.items():
            dr, dc = offsets["direct"]
            nr, nc = r + dr, c + dc
            if (0 <= nr < maze.rows and 0 <= nc < maze.cols
                    and maze.is_walkable(nr, nc)):
                s_center[move] = (nr, nc)

        if candidates:
            # 按性价比降序，选最高分
            candidates.sort(key=lambda x: x[1], reverse=True)
            for best_pos, best_score in candidates:
                if best_score <= 0:
                    break
                # 找到本回合应走的第一步
                first_step = self._first_step(r, c, best_pos, maze)
                if first_step is not None:
                    self._prev_pos = (r, c)
                    return Action(move=_pos_to_move(r, c, first_step))

        # 3×3 内无正收益 → 返回 STAY，由 CompositeAgent 切换全局规划
        return Action(move="STAY")

    # ------------------------------------------------------------------ #
    # 格子价值
    # ------------------------------------------------------------------ #
    def _cell_value(
        self,
        r: int,
        c: int,
        maze: MazeState,
        visited: Set,
    ) -> float:
        cfg = self.cfg
        cell = maze.get(r, c)
        if cell in (CELL_COIN, CELL_GOLD):
            return cfg["coin_value"] * cfg["w_coin"]
        if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            return -cfg["trap_penalty"] * cfg["w_trap"]
        if (r, c) in visited:
            return -cfg["visited_penalty"]
        return 0.0
