"""
composite_agent.py — 组合 Agent（集成入口，角色1负责）
------------------------------------------------------
运行优先级（从高到低）：
  1. 若处于战斗状态 -> CombatAgent
  2. 若 3×3 内有正收益 -> LocalGreedyAgent
  3. 否则 -> GlobalPlannerAgent
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.combat_agent import CombatAgent
from agents.local_greedy_policy import LocalGreedyAgent
from agents.global_planner import GlobalPlannerAgent
from core.state import GameContext, Action


class CompositeAgent(BaseAgent):

    def __init__(self, config: dict = None):
        super().__init__(name="CompositeAgent")
        cfg = config or {}
        self.global_planner = GlobalPlannerAgent(config=cfg.get("global", {}))
        self.local_greedy   = LocalGreedyAgent(
            config=cfg.get("local", {}),
            fallback_agent=self.global_planner,
        )
        self.combat = CombatAgent()

    def on_episode_start(self, ctx: GameContext):
        self.global_planner.on_episode_start(ctx)

    def on_episode_end(self, ctx: GameContext):
        self.global_planner.on_episode_end(ctx)

    def decide(self, ctx: GameContext) -> Action:
        if self.combat.should_fight(ctx):
            return self.combat.decide_combat(ctx)
        return self.local_greedy.decide(ctx)
