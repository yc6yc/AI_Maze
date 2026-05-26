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
    "coin_value":      50,    # 金币的真实游戏价值
    "trap_penalty":    30,    # 陷阱的真实游戏扣分
    "step_cost":       10.0,  # 每步的机会成本估算（用于 value/steps 收益率计算）
    "explore_bonus":   8.0,   # 未探索直接邻居的期望奖励（在 _score_3x3 中单独使用）
    "visited_penalty": 3.0,   # 历史走过格子的额外惩罚（防打转）
    "w_backtrack":     2.0,   # 回头路额外惩罚（防折返）
}

# 每个方向：直接邻居偏移 + 可经由该方向到达的两个对角邻居偏移
DIRECTION_MAP = {
    "UP": {"direct": (-1, 0), "diagonals": [(-1, -1), (-1, 1)]},
    "DOWN": {"direct": (1, 0), "diagonals": [(1, -1), (1, 1)]},
    "LEFT": {"direct": (0, -1), "diagonals": [(-1, -1), (1, -1)]},
    "RIGHT": {"direct": (0, 1), "diagonals": [(-1, 1), (1, 1)]},
}


class LocalGreedyAgent(BaseAgent):
    """
    局部贪心拾取 Agent。
    先确定中心格可达集（哪些方向可走），
    再对每个可走方向建其子可达集并计算累计得分，
    选得分最高的方向走。
    """

    def __init__(self, config: dict = None, fallback_agent=None):
        super().__init__(name="LocalGreedyAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.fallback_agent = fallback_agent
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

        if self.fallback_agent is not None:
            return self.fallback_agent.decide(ctx)

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
        扫描以 (r,c) 为中心的 3×3 窗口内所有邻居，
        返回 [(pos, score), ...] 列表（不含中心格本身）。

        距离定义：
          - 上下左右直接邻居  dist=1
          - 对角邻居          dist=2（需经由中转格才能到达）

        Bug 修复：
          之前用 is_walkable 过滤所有格子，导致黑雾格（fog_map=None）
          被排除在外，_cell_score 里的 explore_bonus 永远不会被计算。
          修复：直接邻居（dist=1）中的黑雾格单独纳入评分（explore_bonus）；
                对角邻居（dist=2）仍要求实际可走才能到达，不处理黑雾对角格。
        """
        results: List[Tuple[Tuple[int, int], float]] = []
        visited = visited or set()

        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not (0 <= nr < maze.rows and 0 <= nc < maze.cols):
                    continue

                dist = abs(dr) + abs(dc)  # 1 或 2

                if dist == 1:
                    # 直接邻居：可走格 or 黑雾格（fog_map=None）都纳入评分
                    # 黑雾格 is_walkable==False，但走向它会揭露视野，值得探索
                    cell = maze.fog_map[nr][nc]
                    if cell is None:
                        # 黑雾直接邻居：只给探索奖励，不扣距离（走一步就能揭露）
                        score = self.cfg["explore_bonus"]
                        # 回头路惩罚仍然适用
                        if self._prev_pos is not None and (nr, nc) == self._prev_pos:
                            score -= self.cfg["w_backtrack"]
                        results.append(((nr, nc), score))
                        continue
                    elif not maze.is_walkable(nr, nc):
                        # 已知不可走（墙）：跳过
                        continue
                else:
                    # 对角邻居（dist=2）：必须实际可走才能到达
                    if not maze.is_walkable(nr, nc):
                        continue
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
        计算格子 (r,c) 的期望每步净收益（value/steps 形式）。

        游戏评分 = total_value / total_steps
          total_value = 金币×50 - 陷阱×30 - 失败次数×CoinConsumption

        因此每步走向目标格的「净收益率」为：
          score = (格子真实价值 - 步数机会成本) / dist
                + 其他修正项（explore奖励、visited惩罚、回头路惩罚）

        步数机会成本：每走一步让分母+1，相当于损失当前已有价值的
          1/total_steps，这里用一个固定估算值 step_cost 代替。

        各参数含义（config.json local 节）：
          coin_value     = 金币的真实游戏价值（50）
          trap_penalty   = 陷阱的真实游戏扣分（30）
          step_cost      = 每步的机会成本估算（默认10，可调）
          explore_bonus  = 未探索格的期望价值（黑雾格在_score_3x3中单独处理，这里不会触发）
          visited_penalty= 历史走过格子的额外惩罚（防打转）
          w_backtrack    = 回头路额外惩罚（防折返）
        """
        cfg = self.cfg
        cell = maze.fog_map[r][c]   # None 表示未探索

        # 真实游戏价值
        raw_value = 0.0
        if cell in (CELL_COIN, CELL_GOLD):
            raw_value = cfg["coin_value"]          # +50
        elif cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            raw_value = -cfg["trap_penalty"]        # -30（已触发的陷阱不重复扣）
        elif cell is None:
            # 黑雾直接邻居已在 _score_3x3 中单独计分，不会走到这里
            raw_value = cfg.get("explore_bonus", 8.0)

        # 步数机会成本：走 dist 步相当于花掉 dist × step_cost 的潜在价值
        step_cost = cfg.get("step_cost", 10.0)
        movement_cost = dist * step_cost

        # 每步净收益率：(真实价值 - 步数成本) / 步数
        # dist=1 时 score = raw_value - step_cost
        # dist=2 时 score = (raw_value - 2×step_cost) / 2，对角格自动更难竞争
        score = (raw_value - movement_cost) / dist

        # 修正项（不除以dist，作为绝对惩罚叠加）
        if visited and (r, c) in visited:
            score -= cfg["visited_penalty"]

        if self._prev_pos is not None and (r, c) == self._prev_pos:
            score -= cfg["w_backtrack"]

        return score

    def _cell_value(
        self,
        r: int,
        c: int,
        maze: MazeState,
        visited: Set,
        dist: int = 1,
    ) -> float:
        """Compatibility wrapper used by verbose demos/tests."""
        return self._cell_score(r, c, maze, dist, visited)

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
