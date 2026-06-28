from __future__ import annotations

from core.state import Action, GameContext, Move

from .ai_maze_global_greedy import AIMazeGlobalGreedyAgent
from .ai_maze_global_planner import AIMazeGlobalPlannerAgent, AIMazePlannerPhase
from .base import BaseAgent
from .combat_agent import CombatAgent
from .local_3x3_greedy import Local3x3GreedyAgent


class AIMazeCompositeAgent(BaseAgent):
    """Reference AI_Maze composite scheduler adapted to this project."""

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        composite_cfg = cfg.get("composite", cfg)
        global_cfg = {**cfg.get("global", {}), "max_steps": cfg.get("sim", {}).get("max_steps", 500)}
        self.strategy = composite_cfg.get("strategy", composite_cfg.get("mode", "hybrid"))
        self.stuck_threshold = int(composite_cfg.get("stuck_threshold", 2))
        self.local = Local3x3GreedyAgent(cfg.get("local", {}))
        self.global_planner = AIMazeGlobalPlannerAgent(global_cfg)
        self.global_greedy = AIMazeGlobalGreedyAgent(global_cfg)
        self.combat = CombatAgent(cfg.get("combat", {}).get("enable_memory", True))
        self.stuck_count = 0
        self.global_active = False

    def decide(self, ctx: GameContext) -> Action:
        if self.combat.should_fight(ctx):
            self.stuck_count = 0
            return self.combat.decide(ctx)

        if self.strategy == "direct_global":
            self.stuck_count = 0
            self.global_active = False
            return self.global_greedy.decide(ctx)

        if self.global_planner.phase in {AIMazePlannerPhase.RUSH_TO_BOSS, AIMazePlannerPhase.RUSH_TO_EXIT}:
            self.global_active = True
            self.stuck_count = 0
            return self.global_planner.decide(ctx)

        if self.global_active:
            candidates = self.local.score_3x3(ctx.player.pos, ctx)
            if any(score > 0 for _pos, score in candidates):
                self.global_active = False
                self.stuck_count = 0
                self.global_planner.path = []
            else:
                return self.global_planner.decide(ctx)

        action = self.local.decide(ctx)
        if action.move == Move.STAY.value:
            self.stuck_count += 1
            if self.stuck_count >= self.stuck_threshold:
                self.global_active = True
                self.stuck_count = 0
                self.global_planner.path = []
                return self.global_planner.decide(ctx)
        else:
            self.stuck_count = 0
        return action
