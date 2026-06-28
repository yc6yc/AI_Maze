from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.state import COIN_CELLS, Action, GameContext, Position, delta_to_move

from .base import BaseAgent


@dataclass
class Local3x3Config:
    coin_value: float = 50.0
    trap_penalty: float = 30.0
    step_cost: float = 10.0
    explore_bonus: float = 8.0
    visited_penalty: float = 3.0
    w_backtrack: float = 2.0


class Local3x3GreedyAgent(BaseAgent):
    """Reference AI_Maze 3x3 local greedy policy adapted to this project."""

    def __init__(self, config: dict | None = None, fallback_agent: BaseAgent | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(Local3x3Config, k)}
        self.config = Local3x3Config(**allowed)
        self.fallback_agent = fallback_agent
        self.previous_pos: Position | None = None

    def decide(self, ctx: GameContext) -> Action:
        cur = ctx.player.pos
        visited = self._visited_from_history(ctx)
        candidates = self.score_3x3(cur, ctx, visited)
        candidates.sort(key=lambda item: item[1], reverse=True)

        for target, score in candidates:
            if score <= 0:
                break
            first_step = self._first_step(cur, target, ctx)
            if first_step is None:
                continue
            self.previous_pos = cur
            return Action(move=delta_to_move((first_step[0] - cur[0], first_step[1] - cur[1])))

        if self.fallback_agent is not None:
            return self.fallback_agent.decide(ctx)
        return Action()

    def score_3x3(
        self,
        cur: Position,
        ctx: GameContext,
        visited: set[Position] | None = None,
    ) -> list[tuple[Position, float]]:
        r, c = cur
        visited = visited or set()
        result: list[tuple[Position, float]] = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                pos = (r + dr, c + dc)
                if not ctx.maze.in_bounds(pos):
                    continue
                dist = abs(dr) + abs(dc)
                cell = ctx.maze.cell(pos)
                if dist == 1:
                    if cell is None:
                        score = self.config.explore_bonus
                        if self.previous_pos == pos:
                            score -= self.config.w_backtrack
                        result.append((pos, score))
                        continue
                    if not ctx.maze.is_walkable(pos):
                        continue
                else:
                    if not ctx.maze.is_walkable(pos):
                        continue
                    mid_a = (r, c + dc)
                    mid_b = (r + dr, c)
                    if not (
                        ctx.maze.in_bounds(mid_a)
                        and ctx.maze.is_walkable(mid_a)
                        or ctx.maze.in_bounds(mid_b)
                        and ctx.maze.is_walkable(mid_b)
                    ):
                        continue
                result.append((pos, self._cell_score(pos, ctx, dist, visited)))
        return result

    def _cell_score(self, pos: Position, ctx: GameContext, dist: int, visited: set[Position]) -> float:
        cell = ctx.maze.cell(pos)
        raw_value = 0.0
        if cell in COIN_CELLS:
            raw_value = self.config.coin_value
        elif cell == "T" and pos not in ctx.maze.triggered_traps:
            raw_value = -self.config.trap_penalty
        elif cell is None:
            raw_value = self.config.explore_bonus

        score = (raw_value - dist * self.config.step_cost) / max(dist, 1)
        if pos in visited:
            score -= self.config.visited_penalty
        if self.previous_pos == pos:
            score -= self.config.w_backtrack
        return score

    def _first_step(self, cur: Position, target: Position, ctx: GameContext) -> Position | None:
        cr, cc = cur
        tr, tc = target
        if abs(tr - cr) + abs(tc - cc) == 1:
            return target
        for step in ((cr, tc), (tr, cc)):
            if ctx.maze.in_bounds(step) and ctx.maze.is_walkable(step):
                return step
        return None

    def _visited_from_history(self, ctx: GameContext) -> set[Position]:
        visited: set[Position] = set()
        for item in ctx.history:
            raw: Any = item.get("pos") if isinstance(item, dict) else None
            if isinstance(raw, list | tuple) and len(raw) == 2:
                visited.add((int(raw[0]), int(raw[1])))
        return visited
