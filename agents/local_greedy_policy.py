from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import inf

from core.pathfinding import dijkstra, reconstruct_path
from core.state import COIN_CELLS, Action, CARDINAL_MOVES, GameContext, Move, Position, delta_to_move, move_to_delta

from .base import BaseAgent


@dataclass
class LocalGreedyConfig:
    coin_value: float = 50.0
    trap_penalty: float = 30.0
    trap_step_cost: float = 31.0
    coin_unknown_min_gain: float = 5.0
    frontier_unknown_weight: float = 4.0
    frontier_base_value: float = 8.0
    visited_penalty: float = 2.0
    backtrack_penalty: float = 3.0
    recent_penalty: float = 5.0
    recent_window: int = 8
    fallback_trap_penalty: float = 100.0
    max_recent_visits: int = 30


class LocalGreedyAgent(BaseAgent):
    """Fog-constrained Original planner.

    The agent only reads ``ctx.maze.fog_map`` through ``MazeState`` helpers. Unknown
    cells are intentionally not walkable; movement toward new space happens by
    targeting known frontier cells adjacent to unknown cells.
    """

    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(LocalGreedyConfig, k)}
        self.config = LocalGreedyConfig(**allowed)
        self.visits: dict[Position, int] = {}
        self.recent: deque[Position] = deque(maxlen=max(int(self.config.recent_window), 1))
        self.previous_pos: Position | None = None
        self.known_bosses: set[Position] = set()

    def decide(self, ctx: GameContext) -> Action:
        cur = ctx.player.pos
        self._remember(ctx)
        self.visits[cur] = self.visits.get(cur, 0) + 1

        path = self._path_to_exit_after_bosses(ctx)
        if not path:
            path = self._path_to_visible_boss(ctx)
        if not path:
            path = self._path_to_best_coin(ctx)
        if not path:
            path = self._path_to_best_frontier(ctx)
        if not path:
            path = self._fallback_path(ctx)

        action = self._action_from_path(cur, path)
        if action.move != Move.STAY.value:
            self.previous_pos = cur
            self.recent.append(cur)
        return action

    def _remember(self, ctx: GameContext) -> None:
        for pos, cell in ctx.maze.known_cells():
            if cell == "B" and pos not in ctx.maze.defeated_bosses:
                self.known_bosses.add(pos)

    def _path_to_exit_after_bosses(self, ctx: GameContext) -> list[Position]:
        if not self._all_known_bosses_defeated(ctx) or not self._exit_known(ctx):
            return []
        return self._path_to(ctx, ctx.maze.end)

    def _path_to_visible_boss(self, ctx: GameContext) -> list[Position]:
        bosses = self._visible_bosses(ctx)
        if not bosses:
            return []
        dist, came_from = self._weighted_dijkstra(ctx, ctx.player.pos)
        reachable = [boss for boss in bosses if boss in dist]
        if not reachable:
            return []
        target = min(reachable, key=lambda pos: dist[pos])
        return reconstruct_path(came_from, ctx.player.pos, target)

    def _path_to_best_coin(self, ctx: GameContext) -> list[Position]:
        coins = self._visible_coins(ctx)
        if not coins:
            return []

        cur = ctx.player.pos
        dist, came_from = self._weighted_dijkstra(ctx, cur)
        exit_known = self._exit_known(ctx)
        exit_dist = inf
        baseline_ratio = 0.0
        if exit_known:
            exit_dist = dist.get(ctx.maze.end, inf)
            if exit_dist < inf:
                baseline_ratio = self._ratio(ctx.player.coins, ctx.step_count + exit_dist)

        best_path: list[Position] = []
        best_ratio = -inf
        for coin in coins:
            if coin not in dist:
                continue
            path = reconstruct_path(came_from, cur, coin)
            if len(path) < 2:
                continue
            dist_to_coin = len(path) - 1
            trap_count = self._untriggered_trap_count(ctx, path)
            net_value = self.config.coin_value - trap_count * self.config.trap_penalty
            if net_value <= 0:
                continue

            if not exit_known:
                gain_per_step = net_value / max(dist_to_coin, 1)
                if gain_per_step < self.config.coin_unknown_min_gain:
                    continue
                coin_ratio = gain_per_step
            else:
                if exit_dist == inf:
                    continue
                coin_exit_dist = self._distance(ctx, coin, ctx.maze.end)
                if coin_exit_dist == inf:
                    continue
                coin_ratio = self._ratio(ctx.player.coins + net_value, ctx.step_count + dist_to_coin + coin_exit_dist)
                if coin_ratio <= baseline_ratio:
                    continue

            coin_ratio -= self.visits.get(coin, 0) * 0.01
            if coin_ratio > best_ratio:
                best_ratio = coin_ratio
                best_path = path
        return best_path

    def _path_to_best_frontier(self, ctx: GameContext) -> list[Position]:
        cur = ctx.player.pos
        dist, came_from = self._weighted_dijkstra(ctx, cur)
        best_score = -inf
        best_pos: Position | None = None
        for pos in dist:
            unknown_count = self._unknown_neighbor_count(ctx, pos)
            if unknown_count <= 0:
                continue
            distance = max(dist[pos], 1.0)
            score = (unknown_count * self.config.frontier_unknown_weight + self.config.frontier_base_value) / distance
            if pos == self.previous_pos:
                score -= self.config.recent_penalty
            score -= self.visits.get(pos, 0) * 0.05
            if score > best_score:
                best_score = score
                best_pos = pos
        if best_pos is None:
            return []
        return reconstruct_path(came_from, cur, best_pos)

    def _fallback_path(self, ctx: GameContext) -> list[Position]:
        cur = ctx.player.pos
        candidates: list[tuple[float, Position]] = []
        for nxt in self._neighbors(ctx, cur):
            cell = ctx.maze.cell(nxt)
            score = -self.visits.get(nxt, 0) * self.config.visited_penalty
            if cell == "T" and nxt not in ctx.maze.triggered_traps:
                score -= self.config.fallback_trap_penalty
            if nxt == self.previous_pos:
                score -= self.config.backtrack_penalty
            if nxt in self.recent:
                score -= self.config.recent_penalty
            candidates.append((score, nxt))
        if not candidates:
            return []
        _score, nxt = max(candidates, key=lambda item: item[0])
        return [cur, nxt]

    def _path_to(self, ctx: GameContext, target: Position) -> list[Position]:
        dist, came_from = self._weighted_dijkstra(ctx, ctx.player.pos)
        if target not in dist:
            return []
        return reconstruct_path(came_from, ctx.player.pos, target)

    def _weighted_dijkstra(
        self,
        ctx: GameContext,
        start: Position,
    ) -> tuple[dict[Position, float], dict[Position, Position]]:
        return dijkstra(ctx.maze, start, cost_fn=self._cost(ctx))

    def _distance(self, ctx: GameContext, start: Position, target: Position) -> float:
        dist, _came_from = self._weighted_dijkstra(ctx, start)
        return dist.get(target, inf)

    def _cost(self, ctx: GameContext):
        def cost(pos: Position) -> float:
            cell = ctx.maze.cell(pos)
            if cell == "T" and pos not in ctx.maze.triggered_traps:
                return 1.0 + self.config.trap_step_cost
            return 1.0

        return cost

    def _visible_coins(self, ctx: GameContext) -> list[Position]:
        return [pos for pos, cell in ctx.maze.known_cells() if cell in COIN_CELLS]

    def _visible_bosses(self, ctx: GameContext) -> list[Position]:
        return sorted(
            pos
            for pos, cell in ctx.maze.known_cells()
            if cell == "B" and pos not in ctx.maze.defeated_bosses
        )

    def _all_known_bosses_defeated(self, ctx: GameContext) -> bool:
        visible_bosses = {pos for pos, cell in ctx.maze.known_cells() if cell == "B"}
        self.known_bosses.update(visible_bosses - ctx.maze.defeated_bosses)
        return bool(self.known_bosses) and all(pos in ctx.maze.defeated_bosses for pos in self.known_bosses)

    def _exit_known(self, ctx: GameContext) -> bool:
        return ctx.maze.cell(ctx.maze.end) == "E"

    def _untriggered_trap_count(self, ctx: GameContext, path: list[Position]) -> int:
        return sum(1 for pos in path[1:] if ctx.maze.cell(pos) == "T" and pos not in ctx.maze.triggered_traps)

    def _unknown_neighbor_count(self, ctx: GameContext, pos: Position) -> int:
        r, c = pos
        count = 0
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None:
                count += 1
        return count

    def _neighbors(self, ctx: GameContext, pos: Position) -> list[Position]:
        result: list[Position] = []
        r, c = pos
        for move in CARDINAL_MOVES:
            dr, dc = move_to_delta(move)
            nxt = (r + dr, c + dc)
            if ctx.maze.in_bounds(nxt) and ctx.maze.is_walkable(nxt):
                result.append(nxt)
        return result

    def _action_from_path(self, cur: Position, path: list[Position]) -> Action:
        if len(path) < 2:
            return Action()
        nxt = path[1]
        return Action(move=delta_to_move((nxt[0] - cur[0], nxt[1] - cur[1])))

    def _ratio(self, value: float, steps: float) -> float:
        return value / max(steps, 1.0)
