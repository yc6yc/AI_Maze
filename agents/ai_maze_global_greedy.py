from __future__ import annotations

from dataclasses import dataclass

from core.pathfinding import dijkstra, extract_path
from core.state import COIN_CELLS, Action, GameContext, Position, delta_to_move

from .base import BaseAgent


@dataclass
class AIMazeGlobalGreedyConfig:
    coin_value: float = 50.0
    frontier_value: float = 14.0
    boss_value: float = 120.0
    exit_value: float = 1_000_000.0
    trap_step_cost: float = 31.0
    target_retry_buffer: int = 1
    frontier_unknown_weight: float = 4.0
    revisit_penalty: float = 0.15
    min_explore_before_boss: float = 0.25


class AIMazeGlobalGreedyAgent(BaseAgent):
    """Reference AI_Maze direct global greedy strategy adapted to current state objects."""

    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(AIMazeGlobalGreedyConfig, k)}
        self.config = AIMazeGlobalGreedyConfig(**allowed)
        self.known_bosses: set[Position] = set()
        self.visits: dict[Position, int] = {}

    def decide(self, ctx: GameContext) -> Action:
        self._scan_bosses(ctx)
        self.visits[ctx.player.pos] = self.visits.get(ctx.player.pos, 0) + 1
        candidates = self._enumerate_candidates(ctx)
        if not candidates:
            return Action()

        _kind, _goal, _score, path = max(candidates, key=lambda item: item[2])
        if len(path) < 2:
            return Action()
        nxt = path[1]
        return Action(move=delta_to_move((nxt[0] - ctx.player.pos[0], nxt[1] - ctx.player.pos[1])))

    def _enumerate_candidates(self, ctx: GameContext) -> list[tuple[str, Position, float, list[Position]]]:
        dist, prev = dijkstra(ctx.maze, ctx.player.pos, cost_fn=self._cost(ctx))
        candidates: list[tuple[str, Position, float, list[Position]]] = []

        for pos, cell in ctx.maze.known_cells():
            if pos == ctx.player.pos or pos not in dist:
                continue
            path = extract_path(prev, ctx.player.pos, pos)
            if len(path) < 2:
                continue
            distance_cost = max(dist[pos], 1.0)
            revisit = self.config.revisit_penalty * self.visits.get(pos, 0)
            if cell in COIN_CELLS:
                score = self.config.coin_value / distance_cost - revisit
                if self._should_force_collect(ctx):
                    score += 20.0
                candidates.append(("coin", pos, score, path))
            elif cell == "B" and pos not in ctx.maze.defeated_bosses:
                score = self._score_boss_target(ctx, pos, distance_cost) - revisit
                candidates.append(("boss", pos, score, path))
            elif cell == "E" and self._can_exit(ctx):
                candidates.append(("exit", pos, self.config.exit_value / distance_cost, path))

        for frontier in self._find_frontiers(ctx):
            if frontier == ctx.player.pos or frontier not in dist:
                continue
            path = extract_path(prev, ctx.player.pos, frontier)
            if len(path) < 2:
                continue
            distance_cost = max(dist[frontier], 1.0)
            unknown_count = self._unknown_neighbor_count(ctx, frontier)
            raw_value = self.config.frontier_value + self.config.frontier_unknown_weight * unknown_count
            score = raw_value / distance_cost - self.config.revisit_penalty * self.visits.get(frontier, 0)
            candidates.append(("frontier", frontier, score, path))
        return candidates

    def _score_boss_target(self, ctx: GameContext, _target: Position, distance_cost: float) -> float:
        need = max(ctx.coin_consumption * self.config.target_retry_buffer, ctx.coin_consumption)
        ready = ctx.player.coins >= need
        score = self.config.boss_value / max(distance_cost, 1.0)
        if ready:
            score += 40.0
        else:
            score -= max(0.0, need - ctx.player.coins)
        if self._explored_ratio(ctx) < self.config.min_explore_before_boss and not ready:
            score -= 25.0
        return score

    def _should_force_collect(self, ctx: GameContext) -> bool:
        active_bosses = self._active_known_bosses(ctx)
        if not active_bosses:
            return False
        need = max(ctx.coin_consumption * self.config.target_retry_buffer, ctx.coin_consumption)
        return ctx.player.coins < need

    def _can_exit(self, ctx: GameContext) -> bool:
        return not self._active_known_bosses(ctx)

    def _scan_bosses(self, ctx: GameContext) -> None:
        for pos, cell in ctx.maze.known_cells():
            if cell == "B" and pos not in ctx.maze.defeated_bosses:
                self.known_bosses.add(pos)
        self.known_bosses = self._active_known_bosses(ctx)

    def _active_known_bosses(self, ctx: GameContext) -> set[Position]:
        return {
            pos
            for pos in self.known_bosses
            if pos not in ctx.maze.defeated_bosses and ctx.maze.cell(pos) == "B"
        }

    def _find_frontiers(self, ctx: GameContext) -> list[Position]:
        frontiers: list[Position] = []
        for pos, _cell in ctx.maze.known_cells():
            if ctx.maze.is_walkable(pos) and self._unknown_neighbor_count(ctx, pos):
                frontiers.append(pos)
        return frontiers

    def _unknown_neighbor_count(self, ctx: GameContext, pos: Position) -> int:
        r, c = pos
        count = 0
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None:
                count += 1
        return count

    def _explored_ratio(self, ctx: GameContext) -> float:
        known = sum(1 for _pos, _cell in ctx.maze.known_cells())
        return known / max(ctx.maze.rows * ctx.maze.cols, 1)

    def _cost(self, ctx: GameContext):
        def cost(pos: Position) -> float:
            if ctx.maze.cell(pos) == "T" and pos not in ctx.maze.triggered_traps:
                return 1.0 + self.config.trap_step_cost
            return 1.0

        return cost
