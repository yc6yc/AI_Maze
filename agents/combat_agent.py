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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from core.state import GameContext, Action, CELL_BOSS


@dataclass
class _MemoryState:
    failed_sequences: List[List[Optional[int]]] = field(default_factory=list)
    current_sequence: List[Optional[int]] = field(default_factory=list)
    round_in_attempt: int = 0
    pending_failure_commit: bool = False
    planned_sequence: Optional[List[Optional[int]]] = None


class CombatAgent:
    """
    无状态战斗决策辅助类（不继承 BaseAgent，作为组件嵌入其他 Agent）。

    minRounds 语义说明：
      服务器下发的 minRounds 是 BOSS 战中的最大攻击轮数上限。
      每个战斗回合玩家可使用一个技能（BOSS 不反击）。
      超出 minRounds 轮未击败 BOSS → 挑战失败，扣除 CoinConsumption 金币。
    """

    def __init__(self, enable_memory: bool = False):
        self.enable_memory = enable_memory
        self._memory_states: Dict[Tuple[int, int, int], _MemoryState] = {}

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

    def decide_combat_with_memory(self, ctx: GameContext) -> Action:
        """
        带“失败记忆”的战斗决策：
        - 每次在 min_rounds 内未击败 BOSS，则记录本次技能序列
        - 下一次复活挑战时，基于历史失败序列重规划新序列
        - 再下一次挑战时，使用前两次失败序列共同重规划，依此类推

        注意：
        - 原有 decide_combat() 逻辑保持不变；该方法是新增能力
        - 当 enable_memory=False 时，本方法退化为原始贪心策略
        """
        if not self.enable_memory:
            return self.decide_combat(ctx)

        boss_key = self._boss_key(ctx)
        if boss_key is None:
            return self.decide_combat(ctx)
        state = self._memory_states.setdefault(boss_key, _MemoryState())

        # 新一轮复活挑战开始：上一轮达到 min_rounds 且继续调用，说明上一轮失败
        if state.pending_failure_commit:
            state.failed_sequences.append(list(state.current_sequence))
            state.current_sequence.clear()
            state.round_in_attempt = 0
            state.pending_failure_commit = False
            state.planned_sequence = self._plan_sequence_from_memory(ctx, state.failed_sequences)

        skill_idx = self._choose_from_plan_or_greedy(ctx, state)
        state.current_sequence.append(skill_idx)
        state.round_in_attempt += 1

        if state.round_in_attempt >= max(1, int(ctx.min_rounds)):
            # 是否失败要到“下一次还能继续挑战”才能确认，因此先标记待提交
            state.pending_failure_commit = True

        return Action(move="STAY", use_skill=skill_idx)

    def mark_boss_defeated(self, ctx: GameContext):
        """
        在外部确认 BOSS 击败后调用，清除该 BOSS 的失败记忆。
        """
        boss_key = self._boss_key(ctx)
        if boss_key is not None:
            self._memory_states.pop(boss_key, None)

    def _choose_from_plan_or_greedy(self, ctx: GameContext, state: _MemoryState) -> Optional[int]:
        available = ctx.player.available_skills()
        if not available:
            return None

        # 若已有重规划序列，则优先按序列使用（可用才执行）
        if state.planned_sequence and state.round_in_attempt < len(state.planned_sequence):
            planned_idx = state.planned_sequence[state.round_in_attempt]
            if planned_idx is not None:
                for idx, _sk in available:
                    if idx == planned_idx:
                        return idx

        # 回退原有贪心：可用技能中伤害最高
        best_idx, _best_skill = max(available, key=lambda x: x[1].damage)
        return best_idx

    def _plan_sequence_from_memory(
        self,
        ctx: GameContext,
        failed_sequences: List[List[Optional[int]]],
    ) -> List[Optional[int]]:
        """
        根据历史失败序列重规划当前挑战的技能序列。
        规划规则：
        - 对每个回合，收集历史失败序列在该回合使用过的技能，作为“回合禁用集合”
        - 在当前回合可用技能中，优先选择不在禁用集合中的最高伤害技能
        - 若都在禁用集合中，则回退到最高伤害技能
        """
        rounds = max(1, int(ctx.min_rounds))
        cds = [skill.remaining_cd for skill in ctx.player.skills]
        cooldowns = [skill.cooldown for skill in ctx.player.skills]
        damages = [skill.damage for skill in ctx.player.skills]
        plan: List[Optional[int]] = []

        for turn in range(rounds):
            banned = {
                seq[turn]
                for seq in failed_sequences
                if turn < len(seq) and seq[turn] is not None
            }
            available = [idx for idx, cd in enumerate(cds) if cd == 0]
            if not available:
                plan.append(None)
            else:
                preferred = [idx for idx in available if idx not in banned]
                candidates = preferred if preferred else available
                chosen = max(candidates, key=lambda idx: damages[idx])
                plan.append(chosen)
                cds[chosen] = cooldowns[chosen]

            cds = [max(0, cd - 1) for cd in cds]
        return plan

    def _boss_key(self, ctx: GameContext) -> Optional[Tuple[int, int, int]]:
        """
        构造“当前 BOSS”的稳定键：
        (maze_id, boss_row, boss_col)
        """
        r, c = ctx.player.pos
        maze = ctx.maze
        if maze.get(r, c) == CELL_BOSS:
            return (id(maze), r, c)
        for nr, nc in maze.neighbors(r, c):
            if maze.get(nr, nc) == CELL_BOSS:
                return (id(maze), nr, nc)
        return None
