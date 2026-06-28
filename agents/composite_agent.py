from __future__ import annotations

from core.state import Action, GameContext, Move

from .ai_maze_composite import AIMazeCompositeAgent
from .ai_maze_global_greedy import AIMazeGlobalGreedyAgent
from .ai_maze_global_planner import AIMazeGlobalPlannerAgent
from .base import BaseAgent
from .combat_agent import CombatAgent
from .global_greedy import GlobalGreedyAgent
from .global_planner import GlobalPlannerAgent, PlannerPhase
from .local_3x3_greedy import Local3x3GreedyAgent
from .local_greedy_policy import LocalGreedyAgent


class CompositeAgent(BaseAgent):
    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        self.mode = cfg.get("mode", cfg.get("composite", {}).get("mode", "hybrid"))
        composite_cfg = cfg.get("composite", cfg)
        self.stuck_threshold = int(composite_cfg.get("stuck_threshold", 2))
        self.local = LocalGreedyAgent(cfg.get("local", {}))
        self.planner = GlobalPlannerAgent(cfg.get("global", {}))
        self.global_greedy = GlobalGreedyAgent({**cfg.get("global", {}), **cfg.get("local", {})})
        self.combat = CombatAgent(cfg.get("combat", {}).get("enable_memory", True))
        self.stay_count = 0
        self.global_dominant = False

    def decide(self, ctx: GameContext) -> Action:
        if self.combat.should_fight(ctx):
            self.stay_count = 0
            return self.combat.decide(ctx)

        if self.mode == "direct_global":
            return self.global_greedy.decide(ctx)
        if self.mode == "planner":
            return self.planner.decide(ctx)
        if self.mode == "local":
            return self.local.decide(ctx)

        if self.planner.phase in {PlannerPhase.RUSH_TO_BOSS, PlannerPhase.RUSH_TO_EXIT}:
            self.global_dominant = True
            action = self.planner.decide(ctx)
            if action.move != Move.STAY.value:
                return action

        if self.global_dominant:
            local_action = self.local.decide(ctx)
            if local_action.move != Move.STAY.value:
                self.global_dominant = False
                self.stay_count = 0
                return local_action
            action = self.planner.decide(ctx)
            if action.move != Move.STAY.value:
                return action

        action = self.local.decide(ctx)
        if action.move == Move.STAY.value:
            self.stay_count += 1
        else:
            self.stay_count = 0
            return action

        if self.stay_count >= self.stuck_threshold:
            self.global_dominant = True
            return self.planner.decide(ctx)
        return action


def make_agent(agent_name: str, config: dict | None = None) -> BaseAgent:
    normalized = (agent_name or "hybrid").lower()
    if normalized in {"hybrid", "composite"}:
        return CompositeAgent(config or {})
    if normalized == "local":
        return LocalGreedyAgent((config or {}).get("local", {}))
    if normalized in {"local_3x3", "local_greedy_3x3"}:
        return Local3x3GreedyAgent((config or {}).get("local", {}))
    if normalized == "planner":
        return GlobalPlannerAgent((config or {}).get("global", {}))
    if normalized in {"global_greedy", "direct_global"}:
        return GlobalGreedyAgent({**(config or {}).get("global", {}), **(config or {}).get("local", {})})
    if normalized in {"ai_global_greedy", "ai_maze_global_greedy"}:
        return AIMazeGlobalGreedyAgent({**(config or {}).get("global", {}), **(config or {}).get("local", {})})
    if normalized in {"ai_global_planner", "ai_maze_global_planner"}:
        return AIMazeGlobalPlannerAgent({**(config or {}).get("global", {}), **(config or {}).get("sim", {})})
    if normalized in {"ai_composite", "ai_maze", "ai_maze_hybrid"}:
        return AIMazeCompositeAgent(config or {})
    raise ValueError(f"Unknown agent: {agent_name}")
