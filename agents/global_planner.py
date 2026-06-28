from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf

from core.pathfinding import astar, bfs, dijkstra, reconstruct_path
from core.state import COIN_CELLS, Action, GameContext, Position, delta_to_move

from .base import BaseAgent


class PlannerPhase(str, Enum):
    EXPLORE = "EXPLORE"
    COLLECT = "COLLECT"
    RUSH_TO_BOSS = "RUSH_TO_BOSS"
    RUSH_TO_EXIT = "RUSH_TO_EXIT"
    RETRY_COLLECT = "RETRY_COLLECT"


@dataclass
class GlobalPlannerConfig:
    trap_step_cost: float = 31.0
    boss_coin_threshold: int = 0
    explore_ratio_before_boss: float = 0.18


class GlobalPlannerAgent(BaseAgent):
    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(GlobalPlannerConfig, k)}
        self.config = GlobalPlannerConfig(**allowed)
        self.phase = PlannerPhase.EXPLORE
        self.known_bosses: set[Position] = set()
        self._last_coins: int | None = None

    def decide(self, ctx: GameContext) -> Action:
        self._update_memory(ctx)
        self._select_phase(ctx)

        path: list[Position] = []
        if self.phase == PlannerPhase.RUSH_TO_EXIT:
            path = astar(ctx.maze, ctx.player.pos, ctx.maze.end, cost_fn=self._cost(ctx))
        elif self.phase == PlannerPhase.RUSH_TO_BOSS:
            path = self._path_to_nearest(ctx, self._available_bosses(ctx), weighted=True)
        elif self.phase in {PlannerPhase.COLLECT, PlannerPhase.RETRY_COLLECT}:
            path = self._path_to_nearest(ctx, self._coins(ctx), weighted=True)
            if not path:
                path = self._path_to_frontier(ctx)
        else:
            path = self._path_to_frontier(ctx)
            if not path:
                path = self._path_to_nearest(ctx, self._coins(ctx), weighted=True)

        return self._action_from_path(ctx.player.pos, path)

    def _update_memory(self, ctx: GameContext) -> None:
        for pos, cell in ctx.maze.known_cells():
            if cell == "B" and pos not in ctx.maze.defeated_bosses:
                self.known_bosses.add(pos)
        if self._last_coins is not None and ctx.player.coins < self._last_coins and self.phase == PlannerPhase.RUSH_TO_BOSS:
            self.phase = PlannerPhase.RETRY_COLLECT
        self._last_coins = ctx.player.coins

    def _select_phase(self, ctx: GameContext) -> None:
        if len(ctx.maze.defeated_bosses) >= len(self.known_bosses) and self._exit_known(ctx):
            if not self._available_bosses(ctx):
                self.phase = PlannerPhase.RUSH_TO_EXIT
                return
        if self._available_bosses(ctx):
            if ctx.player.coins >= self.config.boss_coin_threshold and self._explore_ratio(ctx) >= self.config.explore_ratio_before_boss:
                self.phase = PlannerPhase.RUSH_TO_BOSS
            else:
                self.phase = PlannerPhase.COLLECT if self._coins(ctx) else PlannerPhase.EXPLORE
            return
        self.phase = PlannerPhase.EXPLORE

    def _path_to_frontier(self, ctx: GameContext) -> list[Position]:
        dist = bfs(ctx.maze, ctx.player.pos)
        if not isinstance(dist, dict):
            return []
        frontiers = [pos for pos in dist if self._unknown_neighbor(ctx, pos)]
        if not frontiers:
            return []
        goal = min(frontiers, key=lambda pos: dist[pos])
        path = bfs(ctx.maze, ctx.player.pos, goal)
        return path if isinstance(path, list) else []

    def _path_to_nearest(self, ctx: GameContext, targets: list[Position], *, weighted: bool = False) -> list[Position]:
        if not targets:
            return []
        if weighted:
            dist, came_from = dijkstra(ctx.maze, ctx.player.pos, cost_fn=self._cost(ctx))
            reachable = [target for target in targets if target in dist]
            if not reachable:
                return []
            goal = min(reachable, key=lambda pos: dist[pos])
            return reconstruct_path(came_from, ctx.player.pos, goal)
        best_path: list[Position] = []
        best_len = inf
        for target in targets:
            path = bfs(ctx.maze, ctx.player.pos, target)
            if isinstance(path, list) and path and len(path) < best_len:
                best_path = path
                best_len = len(path)
        return best_path

    def _action_from_path(self, cur: Position, path: list[Position]) -> Action:
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

    def _coins(self, ctx: GameContext) -> list[Position]:
        return [pos for pos, cell in ctx.maze.known_cells() if cell in COIN_CELLS]

    def _available_bosses(self, ctx: GameContext) -> list[Position]:
        return sorted(pos for pos in self.known_bosses if pos not in ctx.maze.defeated_bosses and ctx.maze.cell(pos) == "B")

    def _exit_known(self, ctx: GameContext) -> bool:
        return ctx.maze.cell(ctx.maze.end) == "E"

    def _unknown_neighbor(self, ctx: GameContext, pos: Position) -> bool:
        r, c = pos
        for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None:
                return True
        return False

    def _explore_ratio(self, ctx: GameContext) -> float:
        known = sum(1 for _pos, _cell in ctx.maze.known_cells())
        return known / max(ctx.maze.rows * ctx.maze.cols, 1)
