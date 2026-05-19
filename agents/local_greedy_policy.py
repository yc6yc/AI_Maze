"""
local_greedy_policy.py — 局部贪心拾取策略（完整 3×3 视野）
负责人：角色2（算法A）
---------------------------------------------------------
核心思路：
  扫描当前位置的完整 3×3（9个格子）邻域内所有可见格子的性价比，
  选出目标后，若目标是对角格子（需两步才能到达），则规划第一步中转。

格子分类：
  - 直接邻居（上下左右，距离=1）：可直接走过去
  - 对角邻居（左上/右上/左下/右下，距离=2）：不能直接走，
    需找一个共同相邻的直接邻居作为中转格再走一步

性价比函数：
  score(cell) = coin_value * w_coin        （金币收益）
              - trap_penalty * w_trap       （陷阱风险）
              - distance * w_dist           （距离代价，1或2）

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
    "w_backtrack": 2.0,     # 回退到上一步位置的额外惩罚系数
}


class LocalGreedyAgent(BaseAgent):
    """
    局部贪心拾取 Agent。
    扫描完整 3×3（9格）视野，对直接邻居直接走，
    对对角格子计算第一步中转格。
    若 3×3 内无正收益目标，则委托全局规划。
    """

    def __init__(self, config: dict = None, fallback_agent=None):
        super().__init__(name="LocalGreedyAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.fallback_agent = fallback_agent
        self._prev_pos: Optional[Tuple[int, int]] = None   # 上一步所在位置

    # ------------------------------------------------------------------ #
    # 主接口
    # ------------------------------------------------------------------ #
    def decide(self, ctx: GameContext) -> Action:
        r, c = ctx.player.pos
        maze = ctx.maze

        candidates = self._score_3x3(r, c, maze)

        if candidates:
            # 按性价比降序，选最高分
            candidates.sort(key=lambda x: x[1], reverse=True)
            for best_pos, best_score in candidates:
                if best_score <= 0:
                    break
                # 找到本回合应走的第一步
                first_step = self._first_step(r, c, best_pos, maze)
                if first_step is not None:
                    self._prev_pos = (r, c)   # 记录本步出发位置
                    return Action(move=_pos_to_move(r, c, first_step))

        # 无局部收益 -> 交给 fallback
        self._prev_pos = (r, c)
        if self.fallback_agent is not None:
            return self.fallback_agent.decide(ctx)
        return Action(move="STAY")

    # ------------------------------------------------------------------ #
    # 完整 3×3 扫描
    # ------------------------------------------------------------------ #
    def _score_3x3(
        self,
        r: int,
        c: int,
        maze: MazeState,
    ) -> List[Tuple[Tuple[int, int], float]]:
        """
        扫描 3×3 内全部 8 个格子（不含中心自身），
        对每个已知、可通行的格子计算性价比。
        返回 [(目标坐标, 性价比分数), ...]
        """
        results = []
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if dr == 0 and dc == 0:
                    continue  # 跳过自身
                nr, nc = r + dr, c + dc
                if not (0 <= nr < maze.rows and 0 <= nc < maze.cols):
                    continue
                cell = maze.get(nr, nc)
                if cell is None or cell == CELL_WALL:
                    continue  # 未探索或墙壁跳过
                if not maze.is_walkable(nr, nc):
                    continue
                dist = abs(dr) + abs(dc)   # 直接邻居=1，对角邻居=2
                score = self._cell_score(nr, nc, cell, dist, maze)
                results.append(((nr, nc), score))
        return results

    def _cell_score(
        self,
        r: int, c: int,
        cell: str,
        dist: int,
        maze: MazeState,
    ) -> float:
        """计算单个格子的性价比，对回退到上一步位置的格子施加额外惩罚"""
        cfg = self.cfg
        coin_v = 0.0
        trap_v = 0.0
        backtrack_v = 0.0

        if cell in (CELL_COIN, CELL_GOLD):
            coin_v = cfg["coin_value"]
        if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            trap_v = cfg["trap_penalty"]
        # 回退惩罚：若该格子正是上一步出发的位置（即原路返回），额外扣分
        if self._prev_pos is not None and (r, c) == self._prev_pos:
            backtrack_v = cfg["w_backtrack"]

        score = (
            coin_v * cfg["w_coin"]
            - trap_v * cfg["w_trap"]
            - dist   * cfg["w_dist"]       # dist=1（直接邻居）或 2（对角邻居）
            - backtrack_v                  # 回退到上一步位置的额外惩罚
        )
        return score

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
