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

    minRounds 语义说明：
      服务器下发的 minRounds 是 BOSS 战中的最大攻击轮数上限。
      每个战斗回合玩家可使用一个技能（BOSS 不反击）。
      超出 minRounds 轮未击败 BOSS → 挑战失败，扣除 CoinConsumption 金币。
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

    def can_defeat_in_time(self, ctx: GameContext, boss_hp: int) -> bool:
        """
        预判能否在 minRounds 轮内击败 BOSS。

        策略：贪心模拟 minRounds 轮的最优技能使用序列，
        计算累计最大伤害，若 >= boss_hp 则可在时限内击败。

        参数：
          boss_hp  : 当前 BOSS 血量（失败后服务器会告知已扣减的血量）
        返回：
          True  → 按最优序列可在 minRounds 内击败
          False → 打不死，此次挑战必然失败，需提前准备重试金币
        """
        min_rounds = ctx.min_rounds
        skills = [s for s in ctx.player.skills]  # 复制，避免修改原始状态
        # 模拟冷却
        cds = [s.remaining_cd for s in skills]
        total_damage = 0
        for round_i in range(min_rounds):
            # 找本轮可用（cd==0）且伤害最大的技能
            best_dmg, best_idx = 0, -1
            for i, s in enumerate(skills):
                if cds[i] == 0 and s.damage > best_dmg:
                    best_dmg, best_idx = s.damage, i
            if best_idx >= 0:
                total_damage += best_dmg
                cds[best_idx] = skills[best_idx].cooldown  # 进入冷却
            # 冷却递减
            cds = [max(0, cd - 1) for cd in cds]
            if total_damage >= boss_hp:
                return True
        return total_damage >= boss_hp

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
