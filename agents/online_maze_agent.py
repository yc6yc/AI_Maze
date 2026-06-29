from __future__ import annotations

from dataclasses import dataclass

from core.pathfinding import dijkstra, extract_path, neighbors
from core.state import COIN_CELLS, Action, GameContext, Move, Position, delta_to_move

from .base import BaseAgent


@dataclass
class OnlineMazeConfig:
    coin_value: float = 50.0
    trap_damage: float = 30.0
    trap_step_cost: float = 31.0
    frontier_info_weight: float = 8.0
    frontier_step_cost: float = 1.2
    finish_ratio_margin: float = 0.15
    max_finish_coins: int = 8
    boss_value: float = 140.0
    boss_ready_bonus: float = 40.0
    revisit_penalty: float = 0.4


class OnlineMazePlanningAgent(BaseAgent):
    """Online fog planner adapted from the standalone online_maze_agent.py.

    The original file keeps its own memory map and returns U/D/L/R actions.
    This project already owns the fog map, scoring, traps and Boss lifecycle,
    so this adapter only plans a single legal move from GameContext.
    """

    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(OnlineMazeConfig, k)}
        self.config = OnlineMazeConfig(**allowed)
        self.visits: dict[Position, int] = {}

    def decide(self, ctx: GameContext) -> Action:
        pos = ctx.player.pos
        self.visits[pos] = self.visits.get(pos, 0) + 1

        boss_plan = self._best_boss_plan(ctx)
        if boss_plan is not None:
            return self._first_step(ctx, boss_plan)

        finish_plan = self._best_known_finish_plan(ctx)
        resource_plan = self._best_resource_plan(ctx)

        chosen: list[Position] | None = None
        if finish_plan is not None:
            finish_path, finish_ratio = finish_plan
            chosen = finish_path
            if resource_plan is not None:
                resource_path, _resource_score = resource_plan
                projected_ratio = self._projected_ratio(ctx, resource_path)
                if projected_ratio > finish_ratio + self.config.finish_ratio_margin:
                    chosen = resource_path
        elif resource_plan is not None:
            chosen = resource_plan[0]
        else:
            chosen = self._best_frontier_plan(ctx)

        if chosen is None:
            return self._fallback_move(ctx)
        return self._first_step(ctx, chosen)

    def _best_boss_plan(self, ctx: GameContext) -> list[Position] | None:
        if ctx.boss_defeated:
            return None
        dist, prev = dijkstra(ctx.maze, ctx.player.pos, cost_fn=self._cost(ctx))
        best: tuple[float, list[Position]] | None = None
        for pos, cell in ctx.maze.known_cells():
            if cell != "B" or pos in ctx.maze.defeated_bosses or pos not in dist:
                continue
            path = extract_path(prev, ctx.player.pos, pos)
            if len(path) < 2:
                continue
            distance = max(dist[pos], 1.0)
            score = self.config.boss_value / distance
            if ctx.player.coins >= max(ctx.coin_consumption, 0):
                score += self.config.boss_ready_bonus
            else:
                score -= max(ctx.coin_consumption - ctx.player.coins, 0)
            score -= self.config.revisit_penalty * self.visits.get(pos, 0)
            if best is None or score > best[0]:
                best = (score, path)
        return best[1] if best else None

    def _best_known_finish_plan(self, ctx: GameContext) -> tuple[list[Position], float] | None:
        if not ctx.boss_defeated:
            return None
        exits = [pos for pos, cell in ctx.maze.known_cells() if cell == "E"]
        if not exits:
            return None
        exit_pos = exits[0]
        direct = self._path_to(ctx, ctx.player.pos, exit_pos)
        if not direct:
            return None

        best_path = direct
        best_ratio = self._projected_ratio(ctx, direct)
        coins = self._visible_uncollected_coins(ctx)

        for coin in coins:
            path = self._joined_path(ctx, [ctx.player.pos, coin, exit_pos])
            if path is None:
                continue
            ratio = self._projected_ratio(ctx, path)
            if ratio > best_ratio + 1e-12:
                best_path = path
                best_ratio = ratio

        dist, _prev = dijkstra(ctx.maze, ctx.player.pos, cost_fn=self._cost(ctx))
        candidate_coins = sorted([coin for coin in coins if coin in dist], key=lambda coin: dist[coin])[
            : max(self.config.max_finish_coins, 0)
        ]
        for first in candidate_coins:
            for second in candidate_coins:
                if second == first:
                    continue
                path = self._joined_path(ctx, [ctx.player.pos, first, second, exit_pos])
                if path is None:
                    continue
                ratio = self._projected_ratio(ctx, path)
                if ratio > best_ratio + 1e-12:
                    best_path = path
                    best_ratio = ratio

        return best_path, best_ratio

    def _best_resource_plan(self, ctx: GameContext) -> tuple[list[Position], float] | None:
        best: tuple[list[Position], float] | None = None
        for coin in self._visible_uncollected_coins(ctx):
            path = self._path_to(ctx, ctx.player.pos, coin)
            if not path or len(path) < 2:
                continue
            gain = self._path_delta_value(ctx, path)
            if gain <= 0:
                continue
            score = gain / max(len(path) - 1, 1)
            score -= self.config.revisit_penalty * self.visits.get(coin, 0)
            if best is None or score > best[1]:
                best = (path, score)
        return best

    def _best_frontier_plan(self, ctx: GameContext) -> list[Position] | None:
        dist, prev = dijkstra(ctx.maze, ctx.player.pos, cost_fn=self._cost(ctx))
        best: tuple[float, list[Position]] | None = None
        for frontier in self._frontiers(ctx):
            if frontier == ctx.player.pos or frontier not in dist:
                continue
            path = extract_path(prev, ctx.player.pos, frontier)
            if len(path) < 2:
                continue
            info = self._unknown_neighbor_count(ctx, frontier)
            gain = self._path_delta_value(ctx, path)
            score = self.config.frontier_info_weight * info + gain - self.config.frontier_step_cost * (len(path) - 1)
            score -= self.config.revisit_penalty * self.visits.get(frontier, 0)
            if best is None or score > best[0]:
                best = (score, path)
        return best[1] if best else None

    def _visible_uncollected_coins(self, ctx: GameContext) -> list[Position]:
        return [pos for pos, cell in ctx.maze.known_cells() if cell in COIN_CELLS]

    def _frontiers(self, ctx: GameContext) -> list[Position]:
        result: list[Position] = []
        for pos, _cell in ctx.maze.known_cells():
            if ctx.maze.is_walkable(pos) and self._unknown_neighbor_count(ctx, pos):
                result.append(pos)
        return result

    def _unknown_neighbor_count(self, ctx: GameContext, pos: Position) -> int:
        r, c = pos
        count = 0
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None:
                count += 1
        return count

    def _joined_path(self, ctx: GameContext, waypoints: list[Position]) -> list[Position] | None:
        result = [waypoints[0]]
        for start, goal in zip(waypoints, waypoints[1:]):
            segment = self._path_to(ctx, start, goal)
            if not segment:
                return None
            result.extend(segment[1:])
        return result

    def _path_to(self, ctx: GameContext, start: Position, target: Position) -> list[Position]:
        dist, prev = dijkstra(ctx.maze, start, goal=target, cost_fn=self._cost(ctx))
        if target not in dist:
            return []
        return extract_path(prev, start, target)

    def _projected_ratio(self, ctx: GameContext, path: list[Position]) -> float:
        value = ctx.player.coins + self._path_delta_value(ctx, path)
        steps = ctx.step_count + max(len(path) - 1, 0)
        return value / max(steps, 1)

    def _path_delta_value(self, ctx: GameContext, path: list[Position]) -> float:
        gain = 0.0
        seen: set[Position] = set()
        for pos in path[1:]:
            if pos in seen:
                continue
            seen.add(pos)
            cell = ctx.maze.cell(pos)
            if cell in COIN_CELLS:
                gain += self.config.coin_value
            elif cell == "T" and pos not in ctx.maze.triggered_traps:
                gain -= self.config.trap_damage
        return gain

    def _cost(self, ctx: GameContext):
        def cost(pos: Position) -> float:
            cell = ctx.maze.cell(pos)
            if cell == "T" and pos not in ctx.maze.triggered_traps:
                return 1.0 + self.config.trap_step_cost
            return 1.0

        return cost

    def _first_step(self, ctx: GameContext, path: list[Position]) -> Action:
        if len(path) < 2:
            return Action(move=Move.STAY.value)
        cur = ctx.player.pos
        nxt = path[1]
        return Action(move=delta_to_move((nxt[0] - cur[0], nxt[1] - cur[1])))

    def _fallback_move(self, ctx: GameContext) -> Action:
        options = neighbors(ctx.player.pos, ctx.maze)
        if not options:
            return Action(move=Move.STAY.value)
        options.sort(
            key=lambda pos: (
                1 if ctx.maze.cell(pos) == "T" and pos not in ctx.maze.triggered_traps else 0,
                self.visits.get(pos, 0),
                pos,
            )
        )
        return self._first_step(ctx, [ctx.player.pos, options[0]])
