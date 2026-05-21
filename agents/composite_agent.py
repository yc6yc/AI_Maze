"""
composite_agent.py — 组合 Agent（集成入口，角色1负责）
------------------------------------------------------
运行优先级（从高到低）：
  1. 若处于战斗状态          → CombatAgent
  2. 若 3×3 内有正收益目标    → LocalGreedyAgent（主力）
  3. 局部贪心连续无路可走时  → GlobalPlannerAgent（fallback）
  4. 全局规划到达有收益格子  → 切回 LocalGreedyAgent

局部/全局切换逻辑：
  - 局部贪心连续 STAY 超过 stuck_threshold 次，认定陷入死路
    → 激活全局规划器主导，直到周围出现正收益格子才交回局部
  - 全局规划器处于 RUSH_TO_BOSS / RUSH_TO_EXIT 阶段时不切回局部
    （这两个阶段需要全局控制）
"""

from __future__ import annotations

from agents.base_agent import BaseAgent
from agents.combat_agent import CombatAgent
from agents.local_greedy_policy import LocalGreedyAgent
from agents.global_planner import GlobalPlannerAgent, Phase
from core.state import GameContext, Action

# 局部贪心连续输出 STAY 达到此阈值时认定陷入死路
DEFAULT_STUCK_THRESHOLD = 2


class CompositeAgent(BaseAgent):

    def __init__(self, config: dict = None):
        super().__init__(name="CompositeAgent")
        cfg = config or {}
        global_cfg = {
            **cfg.get("global", {}),
            "max_rounds": cfg.get("sim", {}).get("max_rounds", 500),
        }
        self.global_planner = GlobalPlannerAgent(config=global_cfg)
        self.local_greedy   = LocalGreedyAgent(config=cfg.get("local", {}))
        self.combat = CombatAgent()

        self._stuck_threshold: int = cfg.get("composite", {}).get(
            "stuck_threshold", DEFAULT_STUCK_THRESHOLD
        )
        self._stuck_count: int = 0        # 局部贪心连续 STAY 计数
        self._global_active: bool = False # 全局规划器是否当前主导

    def on_episode_start(self, ctx: GameContext):
        self.global_planner.on_episode_start(ctx)
        self._stuck_count = 0
        self._global_active = False

    def on_episode_end(self, ctx: GameContext):
        self.global_planner.on_episode_end(ctx)

    def decide(self, ctx: GameContext) -> Action:
        # 优先级 1：战斗状态始终最高
        if self.combat.should_fight(ctx):
            self._stuck_count = 0
            return self.combat.decide_combat(ctx)

        # 全局规划器处于必须自主控制的阶段（RUSH_TO_BOSS / RUSH_TO_EXIT）
        # 这两个阶段目标明确且路径已由全局规划，不应被局部打断
        if self.global_planner.phase in (Phase.RUSH_TO_BOSS, Phase.RUSH_TO_EXIT):
            self._global_active = True
            self._stuck_count = 0
            return self.global_planner.decide(ctx)

        # 如果全局规划器当前主导，检查周围是否已有正收益格子
        if self._global_active:
            r, c = ctx.player.pos
            candidates = self.local_greedy._score_3x3(r, c, ctx.maze)
            has_local_reward = any(score > 0 for _, score in candidates)
            if has_local_reward:
                # 周围已有正收益，切回局部贪心
                self._global_active = False
                self._stuck_count = 0
                self.global_planner._path = []  # 清空全局路径缓存
            else:
                # 周围仍无收益，继续由全局规划器导航
                return self.global_planner.decide(ctx)

        # 优先级 2：局部贪心（主力）
        action = self.local_greedy.decide(ctx)

        if action.move == "STAY":
            # 局部贪心无路可走，计数
            self._stuck_count += 1
            if self._stuck_count >= self._stuck_threshold:
                # 连续卡顿，切换到全局规划器
                self._global_active = True
                self._stuck_count = 0
                self.global_planner._path = []  # 强制重新规划
                return self.global_planner.decide(ctx)
        else:
            self._stuck_count = 0

        return action
