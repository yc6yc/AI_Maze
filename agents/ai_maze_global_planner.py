from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from core.pathfinding import astar, dijkstra, extract_path
from core.state import COIN_CELLS, Action, GameContext, Position, delta_to_move

from .base import BaseAgent


class AIMazePlannerPhase(Enum):
    EXPLORE = auto()
    COLLECT = auto()
    RUSH_TO_BOSS = auto()
    RUSH_TO_EXIT = auto()
    RETRY_COLLECT = auto()


@dataclass
class AIMazeGlobalPlannerConfig:
    w_coin: float = 2.0
    retry_buffer: int = 3
    min_explore_ratio: float = 0.4
    rush_round_threshold: int = 50
    trap_step_cost: float = 31.0
    max_steps: int = 500


class AIMazeGlobalPlannerAgent(BaseAgent):
    """Reference AI_Maze global phase planner adapted to current simulator."""

    def __init__(self, config: dict | None = None) -> None:
        values = config or {}
        allowed = {k: v for k, v in values.items() if hasattr(AIMazeGlobalPlannerConfig, k)}
        self.config = AIMazeGlobalPlannerConfig(**allowed)
        self.phase = AIMazePlannerPhase.EXPLORE
        self.path: list[Position] = []
        self.known_boss: Position | None = None
        self.all_bosses: list[Position] = []
        self.previous_value = 0
        self.previous_defeated_count = 0

    def decide(self, ctx: GameContext) -> Action:
        self._scan_bosses(ctx)
        self._detect_failure(ctx)
        self._detect_boss_defeated(ctx)
        self._update_phase(ctx)

        if not self.path or not ctx.maze.is_walkable(self.path[0]):
            self._replan(ctx)

        if not self.path:
            self.previous_value = ctx.player.coins
            self.previous_defeated_count = len(ctx.maze.defeated_bosses)
            return Action()

        nxt = self.path.pop(0)
        self.previous_value = ctx.player.coins
        self.previous_defeated_count = len(ctx.maze.defeated_bosses)
        return Action(move=delta_to_move((nxt[0] - ctx.player.pos[0], nxt[1] - ctx.player.pos[1])))

    def _scan_bosses(self, ctx: GameContext) -> None:
        self.all_bosses = [
            pos for pos in self.all_bosses if ctx.maze.cell(pos) == "B" and pos not in ctx.maze.defeated_bosses
        ]
        for pos, cell in ctx.maze.known_cells():
            if cell == "B" and pos not in ctx.maze.defeated_bosses and pos not in self.all_bosses:
                self.all_bosses.append(pos)
        if self.known_boss is not None and (
            ctx.maze.cell(self.known_boss) != "B" or self.known_boss in ctx.maze.defeated_bosses
        ):
            self.known_boss = None
        if self.known_boss is None and self.all_bosses:
            self.known_boss = self.all_bosses[0]

    def _detect_failure(self, ctx: GameContext) -> None:
        if ctx.coin_consumption <= 0 or self.phase != AIMazePlannerPhase.RUSH_TO_BOSS:
            return
        value_drop = self.previous_value - ctx.player.coins
        if value_drop >= ctx.coin_consumption * 0.8 and ctx.player.coins < ctx.coin_consumption:
            self.phase = AIMazePlannerPhase.RETRY_COLLECT
            self.path = []

    def _detect_boss_defeated(self, ctx: GameContext) -> None:
        if self.phase == AIMazePlannerPhase.RUSH_TO_EXIT:
            return
        if not self.all_bosses and len(ctx.maze.defeated_bosses) > 0:
            self.phase = AIMazePlannerPhase.RUSH_TO_EXIT
            self.path = []
            return
        if len(ctx.maze.defeated_bosses) > self.previous_defeated_count and self._exit_known(ctx):
            self.phase = AIMazePlannerPhase.RUSH_TO_EXIT
            self.path = []

    def _update_phase(self, ctx: GameContext) -> None:
        if self.phase == AIMazePlannerPhase.RUSH_TO_EXIT:
            return
        if self.phase == AIMazePlannerPhase.RETRY_COLLECT:
            if ctx.player.coins >= ctx.coin_consumption:
                self.phase = AIMazePlannerPhase.RUSH_TO_BOSS
                self.path = []
            return

        steps_left = max(int(self.config.max_steps), ctx.max_steps) - ctx.player.rounds
        if steps_left <= self.config.rush_round_threshold and self.known_boss is not None:
            self.phase = AIMazePlannerPhase.RUSH_TO_BOSS
            self.path = []
            return

        target_value = self.config.retry_buffer * ctx.coin_consumption if ctx.coin_consumption > 0 else 0
        boss_known = self.known_boss is not None
        value_ready = ctx.player.coins >= target_value
        explored_enough = self._explored_ratio(ctx) >= self.config.min_explore_ratio

        if self.phase in {AIMazePlannerPhase.EXPLORE, AIMazePlannerPhase.COLLECT}:
            if boss_known and value_ready and explored_enough:
                self.phase = AIMazePlannerPhase.RUSH_TO_BOSS
                self.path = []
            elif boss_known and not value_ready:
                self.phase = AIMazePlannerPhase.COLLECT

    def _replan(self, ctx: GameContext) -> None:
        cur = ctx.player.pos
        if self.phase == AIMazePlannerPhase.RUSH_TO_EXIT:
            self.path = self._plan_path(ctx, cur, ctx.maze.end, avoid_traps=False)
            return
        if self.phase == AIMazePlannerPhase.RUSH_TO_BOSS:
            if self.known_boss is None:
                self.phase = AIMazePlannerPhase.EXPLORE
                self._replan(ctx)
                return
            self.path = self._plan_path(ctx, cur, self.known_boss, avoid_traps=True)
            return
        if self.phase == AIMazePlannerPhase.EXPLORE:
            path = self._path_to_frontier(ctx, cur)
            if path:
                self.path = path
                return
            if self._exit_known(ctx):
                self.phase = AIMazePlannerPhase.RUSH_TO_EXIT
                self._replan(ctx)
                return
            self.phase = AIMazePlannerPhase.COLLECT
            self._replan(ctx)
            return
        if self.phase in {AIMazePlannerPhase.COLLECT, AIMazePlannerPhase.RETRY_COLLECT}:
            coin = self._best_coin_target(ctx, cur)
            if coin is not None:
                self.path = self._plan_path(ctx, cur, coin, avoid_traps=True)
                return
            if self.known_boss is not None:
                self.phase = AIMazePlannerPhase.RUSH_TO_BOSS
            elif self._exit_known(ctx):
                self.phase = AIMazePlannerPhase.RUSH_TO_EXIT
            else:
                self.phase = AIMazePlannerPhase.EXPLORE
            self.path = []

    def _plan_path(self, ctx: GameContext, start: Position, goal: Position | None, *, avoid_traps: bool) -> list[Position]:
        if goal is None:
            return []
        if not avoid_traps:
            path = astar(ctx.maze, start, goal)
            return path[1:] if len(path) > 1 else []
        dist, prev = dijkstra(ctx.maze, start, goal=goal, cost_fn=self._cost(ctx))
        if goal not in dist:
            return []
        path = extract_path(prev, start, goal)
        return path[1:] if len(path) > 1 else []

    def _path_to_frontier(self, ctx: GameContext, start: Position) -> list[Position]:
        dist, prev = dijkstra(ctx.maze, start)
        frontiers = [pos for pos in dist if self._unknown_neighbor_count(ctx, pos) > 0]
        if not frontiers:
            return []
        target = min(frontiers, key=lambda pos: dist[pos])
        path = extract_path(prev, start, target)
        return path[1:] if len(path) > 1 else []

    def _best_coin_target(self, ctx: GameContext, start: Position) -> Position | None:
        dist, _prev = dijkstra(ctx.maze, start, cost_fn=self._cost(ctx))
        coins = [pos for pos, cell in ctx.maze.known_cells() if cell in COIN_CELLS and pos in dist]
        if not coins:
            return None
        return max(coins, key=lambda pos: self.config.w_coin * 50 / (dist[pos] + 1))

    def _unknown_neighbor_count(self, ctx: GameContext, pos: Position) -> int:
        r, c = pos
        return sum(
            1
            for nxt in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if ctx.maze.in_bounds(nxt) and ctx.maze.cell(nxt) is None
        )

    def _exit_known(self, ctx: GameContext) -> bool:
        return ctx.maze.cell(ctx.maze.end) == "E"

    def _explored_ratio(self, ctx: GameContext) -> float:
        known = sum(1 for _pos, _cell in ctx.maze.known_cells())
        return known / max(ctx.maze.rows * ctx.maze.cols, 1)

    def _cost(self, ctx: GameContext):
        def cost(pos: Position) -> float:
            if ctx.maze.cell(pos) == "T" and pos not in ctx.maze.triggered_traps:
                return 1.0 + self.config.trap_step_cost
            return 1.0

        return cost
