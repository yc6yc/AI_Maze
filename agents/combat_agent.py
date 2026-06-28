from __future__ import annotations

from collections import defaultdict

from core.state import Action, GameContext, Move, Position
from eval.simulator import can_defeat_boss

from .base import BaseAgent


class CombatAgent(BaseAgent):
    def __init__(self, enable_memory: bool = True) -> None:
        self.enable_memory = enable_memory
        self.failed_round_skills: dict[Position, set[int]] = defaultdict(set)
        self._last_coins: int | None = None

    def should_fight(self, ctx: GameContext) -> bool:
        target = self._nearby_boss(ctx)
        if target is None:
            return False
        cell = ctx.maze.cell(target)
        return cell == "B"

    def decide(self, ctx: GameContext) -> Action:
        target = self._nearby_boss(ctx)
        if target is None:
            return Action()

        if self._last_coins is not None and ctx.player.coins < self._last_coins:
            self.failed_round_skills[target].clear()
        self._last_coins = ctx.player.coins

        ready = [idx for idx, skill in enumerate(ctx.player.skills) if skill.remaining_cooldown <= 0]
        if not ready:
            return Action(move=Move.STAY.value)

        if self.enable_memory:
            remembered = self.failed_round_skills[target]
            filtered = [idx for idx in ready if idx not in remembered]
            if filtered:
                ready = filtered

        best_idx = max(ready, key=lambda idx: ctx.player.skills[idx].damage)
        return Action(move=Move.STAY.value, use_skill=best_idx)

    def can_defeat_in_time(self, ctx: GameContext, boss_health: int) -> bool:
        return can_defeat_boss(ctx.player.skills, boss_health, ctx.min_rounds)

    def _nearby_boss(self, ctx: GameContext) -> Position | None:
        r, c = ctx.player.pos
        for pos in ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(pos) and ctx.maze.cell(pos) == "B":
                return pos
        return None
