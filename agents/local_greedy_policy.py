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
from typing import List, Optional, Tuple

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
        # 历史走过的格子集合（用于 visited_penalty）
        visited: set = {tuple(snap["pos"]) for snap in ctx.history} if ctx.history else set()

        candidates = self._score_3x3(r, c, maze, visited)

        if candidates:
            # 按得分降序，选最高分
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
    # 3×3 窗口评分（供 decide 和 CompositeAgent 调用）
    # ------------------------------------------------------------------ #
    def _score_3x3(
        self,
        r: int,
        c: int,
        maze: MazeState,
        visited: set = None,
    ) -> List[Tuple[Tuple[int, int], float]]:
        """
        扫描以 (r,c) 为中心的 3×3 窗口内所有可达邻居，
        返回 [(pos, score), ...] 列表（仅包含可走格，不含中心格本身）。

        距离定义：
          - 上下左右直接邻居  dist=1
          - 对角邻居          dist=2（需经由中转格才能到达）
        """
        results: List[Tuple[Tuple[int, int], float]] = []

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < maze.rows and 0 <= nc < maze.cols):
                    continue
                if not maze.is_walkable(nr, nc):
                    continue

                dist = abs(dr) + abs(dc)  # 1 或 2
                # 对角格子（dist=2）需要至少一个中转格可走才能实际到达
                if dist == 2:
                    mid1 = (r, nc)   # 先横后竖的中转
                    mid2 = (nr, c)   # 先竖后横的中转
                    if not (maze.is_walkable(*mid1) or maze.is_walkable(*mid2)):
                        continue

                score = self._cell_score(nr, nc, maze, dist, visited or set())
                results.append(((nr, nc), score))

        return results

    # ------------------------------------------------------------------ #
    # 单格评分
    # ------------------------------------------------------------------ #
    def _cell_score(
        self,
        r: int,
        c: int,
        maze: MazeState,
        dist: int,
        visited: set = None,
    ) -> float:
        """
        计算格子 (r,c) 的期望得分。

        coin      → +coin_value * w_coin
        unknown   → +explore_bonus（未探索格代表潜在的金币机会）
        trap      → -trap_penalty * w_trap（已触发的陷阱不重复扣）
        dist      → -dist * w_dist（距离惩罚，dist=1 直接邻居，dist=2 对角）
        visited   → -visited_penalty（历史走过的格子，避免打转）
        backtrack → -w_backtrack（上一步来的格子，避免原路折返）
        """
        cfg = self.cfg
        cell = maze.fog_map[r][c]   # None 表示未探索

        coin_v     = 0.0
        trap_v     = 0.0
        explore_v  = 0.0
        visited_v  = 0.0

        if cell in (CELL_COIN, CELL_GOLD):
            coin_v = cfg["coin_value"]
        elif cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            trap_v = cfg["trap_penalty"]
        elif cell is None:
            # 未探索格：给予探索期望奖励，鼓励 AI 主动开雾
            explore_v = cfg.get("explore_bonus", 8.0)

        if visited and (r, c) in visited:
            visited_v = cfg.get("visited_penalty", 3.0)

        backtrack_penalty = 0.0
        if self._prev_pos is not None and (r, c) == self._prev_pos:
            backtrack_penalty = cfg.get("w_backtrack", 2.0)

        return (
            coin_v    * cfg["w_coin"]
            + explore_v
            - trap_v  * cfg["w_trap"]
            - dist    * cfg["w_dist"]
            - visited_v
            - backtrack_penalty
        )

    # ------------------------------------------------------------------ #
    # 对角格子的第一步中转逻辑
    # ------------------------------------------------------------------ #
    def _first_step(
        self,
        r: int, c: int,
        target: Tuple[int, int],
        maze: MazeState,
    ) -> Optional[Tuple[int, int]]:
        """
        返回本回合应走的第一步坐标。

        - 直接邻居（曼哈顿距离=1）：target 就是第一步
        - 对角邻居（曼哈顿距离=2）：找一个同时相邻于 (r,c) 和 target
          的可通行格子作为中转格，走向中转格
        """
        tr, tc = target
        dist = abs(tr - r) + abs(tc - c)

        if dist == 1:
            # 直接邻居，直接走过去
            return target

        # 对角格子：候选中转格是两者的公共上下左右邻居
        # 公共邻居只有两个：(r, tc) 和 (tr, c)
        candidates = [(r, tc), (tr, c)]
        for mid_r, mid_c in candidates:
            if (0 <= mid_r < maze.rows and
                    0 <= mid_c < maze.cols and
                    maze.is_walkable(mid_r, mid_c)):
                return (mid_r, mid_c)   # 走向中转格

        return None   # 两个中转格都是墙，无法到达对角格子


# --------------------------------------------------------------------------- #
# 模块级工具函数
# --------------------------------------------------------------------------- #
def _pos_to_move(r: int, c: int, target: Tuple[int, int]) -> str:
    dr = target[0] - r
    dc = target[1] - c
    if dr == -1: return "UP"
    if dr ==  1: return "DOWN"
    if dc == -1: return "LEFT"
    if dc ==  1: return "RIGHT"
    return "STAY"