from __future__ import annotations

from dataclasses import dataclass
from math import inf

from core.pathfinding import dijkstra, reconstruct_path
from core.state import COIN_CELLS, Action, GameContext, Position, delta_to_move

from .base import BaseAgent


@dataclass
class GlobalGreedyConfig:
    trap_step_cost: float = 31.0
    frontier_value: float = 12.0
    frontier_unknown_weight: float = 2.0
    boss_value: float = 160.0
    exit_value: float = 10000.0
    coin_value: float = 50.0
    revisit_penalty: float = 1.8
    boss_coin_threshold: int = 0


class GlobalGreedyAgent(BaseAgent):
    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(GlobalGreedyConfig, k)}
        self.config = GlobalGreedyConfig(**allowed)
        self.visits: dict[Position, int] = {}

    def decide(self, ctx: GameContext) -> Action:
        cur = ctx.player.pos
        self.visits[cur] = self.visits.get(cur, 0) + 1
        dist, came_from = dijkstra(ctx.maze, cur, cost_fn=self._cost(ctx))
        candidates: list[tuple[float, Position]] = []

        all_bosses = [pos for pos, cell in ctx.maze.known_cells() if cell == "B" and pos not in ctx.maze.defeated_bosses]
        boss_done = not all_bosses and ctx.maze.cell(ctx.maze.end) == "E"

        for pos, cell in ctx.maze.known_cells():
            if pos == cur or pos not in dist:
                continue
            distance = max(dist.get(pos, inf), 1.0)
            revisit = self.visits.get(pos, 0) * self.config.revisit_penalty
            if cell in COIN_CELLS:
                candidates.append((self.config.coin_value / distance - revisit, pos))
            elif cell == "B" and pos not in ctx.maze.defeated_bosses:
                score = self.config.boss_value / distance
                if ctx.player.coins >= self.config.boss_coin_threshold:
                    score += 10.0
                else:
                    score -= (self.config.boss_coin_threshold - ctx.player.coins) / max(distance, 1.0)
                candidates.append((score, pos))
            elif cell == "E" and boss_done:
                candidates.append((self.config.exit_value / distance, pos))

            unknown_neighbors = self._unknown_neighbor_count(ctx, pos)
            if unknown_neighbors:
                frontier_score = (
                    self.config.frontier_value + self.config.frontier_unknown_weight * unknown_neighbors
                ) / distance - revisit
                candidates.append((frontier_score, pos))

        if not candidates:
            return Action()

        _score, goal = max(candidates, key=lambda item: item[0])
        path = reconstruct_path(came_from, cur, goal)
        if len(path) < 2:
            return Action()
        nxt = path[1]
        return Action(move=delta_to_move((nxt[0] - cur[0], nxt[1] - cur[1])))

    def _cost(self, ctx: GameContext):
        def cost(pos: Position) -> float:
            cell = ctx.maze.cell(pos)
            if cell == "T" and pos not in ctx.maze.triggered_traps:
                return 1.0 + self.config.trap_step_cost
            return 1.0

        return cost

    def _unknown_neighbor_count(self, ctx: GameContext, pos: Position) -> int:
        r, c = pos
        count = 0
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None:
                count += 1
        return count
