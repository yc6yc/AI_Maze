"""
combat_agent.py — 战斗/技能决策模块
负责人：角色3（全局规划）或角色2（局部贪心）可扩展
-------------------------------------------------------
当玩家站在 BOSS 相邻格子或同格时触发战斗回合。
策略：
  1. 优先使用伤害最高的可用技能
  2. 若无可用技能则等待（STAY）
  3. 击败 BOSS 后清除格子标记，继续寻路
"""

from __future__ import annotations
from typing import Optional

from core.state import GameContext, Action, CELL_BOSS


class CombatAgent:
    """
    无状态战斗决策辅助类（不继承 BaseAgent，作为组件嵌入其他 Agent）。
    """

    def should_fight(self, ctx: GameContext) -> bool:
        """判断当前是否处于战斗状态（站在 BOSS 格子或相邻）"""
        r, c = ctx.player.pos
        maze = ctx.maze
        if maze.get(r, c) == CELL_BOSS:
            return True
        for nr, nc in maze.neighbors(r, c):
            if maze.get(nr, nc) == CELL_BOSS:
                return True
        return False

    def decide_combat(self, ctx: GameContext) -> Action:
        """
        在战斗中选择最优技能。
        返回带 use_skill 的 STAY Action（不移动，专注攻击）。
        """
        available = ctx.player.available_skills()
        if not available:
            return Action(move="STAY", use_skill=None)

        # 选伤害最大的技能
        best_idx, best_skill = max(available, key=lambda x: x[1].damage)
        return Action(move="STAY", use_skill=best_idx)
