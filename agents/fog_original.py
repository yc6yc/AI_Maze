"""
fog_original.py — Fog-constrained A* Planner
Line-by-line faithful port of web/app.js simulateFogOriginal.

Priorities: Exit > Boss > Coin(ratio-filter + dead-end-penalty) > Frontier > Fallback
"""
from __future__ import annotations
from collections import OrderedDict
from agents.base import BaseAgent
from core.pathfinding import dijkstra, extract_path, neighbors
from core.state import Action, GameContext, Move, Position, COIN_CELLS, move_to_delta


CFG = {
    "coin": 50, "trap_dmg": 30, "trap_cost": 31,
    "front_base": 8.0, "front_unk_w": 4.0, "dead_mul": 1.8,
    "min_gain": 5.0, "back_pen": 5.0, "osc_pen": 5.0,
}


class FogOriginalAgent(BaseAgent):
    def __init__(self, config=None):
        self.c = {**CFG, **(config or {})}
        self._last: Position | None = None     # prevPos in JS
        self._recents: dict[str, int] = {}      # recentKeys dict with count
        self._recent_list: list[str] = []       # sliding window of last 8 keys

    def on_episode_start(self, ctx: GameContext) -> None:
        self._last = None
        self._recents = {}
        self._recent_list = []

    def on_episode_end(self, ctx: GameContext) -> None:
        pass

    # -- helpers --
    @staticmethod
    def _key(p: Position) -> str:
        return f"{p[0]},{p[1]}"

    def _cost_fn(self, ctx: GameContext):
        tc = self.c["trap_cost"]
        return lambda p: 1.0 + tc if ctx.maze.cell(p) == "T" and p not in ctx.maze.triggered_traps else 1.0

    def _dij(self, ctx, start):
        return dijkstra(ctx.maze, start, cost_fn=self._cost_fn(ctx))

    def _visible(self, ctx, cells):
        return [p for p, c in ctx.maze.known_cells() if c in cells]

    def _walkable_nbrs(self, ctx, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if ctx.maze.is_walkable((r + dr, c + dc)))

    def _unk_nbrs(self, ctx, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                   if 0 <= r + dr < ctx.maze.rows and 0 <= c + dc < ctx.maze.cols
                   and ctx.maze.fog_map[r + dr][c + dc] is None)

    def _frontiers(self, ctx):
        out = []
        for pos, _ in ctx.maze.known_cells():
            if not ctx.maze.is_walkable(pos):
                continue
            r, c = pos
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < ctx.maze.rows and 0 <= nc < ctx.maze.cols and ctx.maze.fog_map[nr][nc] is None:
                    out.append(pos)
                    break
        return out

    def _traps_on_path(self, ctx, path):
        return sum(1 for p in path
                   if ctx.maze.cell(p) == "T" and p not in ctx.maze.triggered_traps)

    # -- main decide --
    def decide(self, ctx: GameContext) -> Action:
        pos = ctx.player.pos
        coins = ctx.player.coins
        steps = ctx.step_count          # same as JS moveSteps
        boss_done = ctx.boss_defeated
        cfg = self.c

        exits = self._visible(ctx, {"E"})
        bosses = self._visible(ctx, {"B"})
        coins_pos = self._visible(ctx, COIN_CELLS)
        action: Action | None = None

        # P1: Exit
        if boss_done and exits:
            d, prev = self._dij(ctx, pos)
            for e in exits:
                if e in d:
                    p = extract_path(prev, pos, e)
                    if p and len(p) >= 2:
                        action = Action(move=_mv(pos, p[1]))
                        break

        # P2: Boss
        if not action and bosses:
            best_bd = float("inf")
            best_bp = None
            for b in bosses:
                d, prev = self._dij(ctx, pos)
                if b in d and d[b] < best_bd:
                    best_bd = d[b]
                    best_bp = extract_path(prev, pos, b)
            if best_bp and len(best_bp) >= 2:
                action = Action(move=_mv(pos, best_bp[1]))

        # P3: Coin
        if not action and coins_pos:
            best_r = -float("inf")
            best_act = None
            exit_known = bool(exits)
            baseline = 0.0
            if exit_known:
                d, prev = self._dij(ctx, pos)
                for e in exits:
                    if e in d:
                        ed = d[e]
                        baseline = coins / max(steps + ed, 1)
                        break

            for cp in coins_pos:
                d, prev = self._dij(ctx, pos)
                if cp not in d:
                    continue
                cpath = extract_path(prev, pos, cp)
                if not cpath or len(cpath) < 2:
                    continue
                dist_to_coin = len(cpath) - 1
                tr = self._traps_on_path(ctx, cpath)
                net = cfg["coin"] - tr * cfg["trap_dmg"]
                if net <= 0:
                    continue
                wn = self._walkable_nbrs(ctx, cp)
                effective_dist = dist_to_coin * cfg["dead_mul"] if wn <= 2 else dist_to_coin
                gps = net / max(dist_to_coin, 1)
                if not exit_known and gps < cfg["min_gain"]:
                    continue
                cr = float("-inf")
                if exits:
                    d2, _ = self._dij(ctx, cp)
                    e2 = d2.get(exits[0], float("inf"))
                    cr = (coins + net) / max(steps + effective_dist + e2, 1)
                else:
                    cr = gps
                if cr > best_r:
                    best_r = cr
                    best_act = Action(move=_mv(pos, cpath[1]))
            if best_act and (not exit_known or best_r > baseline):
                action = best_act

        # P4: Frontiers
        if not action:
            fronts = self._frontiers(ctx)
            if fronts:
                best_fs, best_fa = -float("inf"), None
                d, prev = self._dij(ctx, pos)
                for f in fronts:
                    if f == pos or f not in d:
                        continue
                    fp = extract_path(prev, pos, f)
                    if not fp or len(fp) < 2:
                        continue
                    unk = self._unk_nbrs(ctx, f)
                    fdist = len(fp) - 1
                    fs = (cfg["front_base"] + cfg["front_unk_w"] * unk) / max(fdist, 1)
                    first_step = fp[1]
                    if self._last and first_step == self._last:
                        fs -= cfg["back_pen"]
                    if self._key(first_step) in self._recents:
                        fs -= cfg["osc_pen"]
                    if fs > best_fs:
                        best_fs = fs
                        best_fa = Action(move=_mv(pos, first_step))
                if best_fa:
                    action = best_fa

        # P5: Fallback
        if not action:
            nbrs = neighbors(pos, ctx.maze, walkable_override=lambda p: ctx.maze.cell(p) != "#")
            if nbrs:
                best = nbrs[0]
                if self._last:
                    for n in nbrs:
                        if n != self._last:
                            best = n
                            break
                action = Action(move=_mv(pos, best))
            else:
                action = Action(move=Move.STAY.value)

        # -- update state for next call (mirrors JS simulation loop) --
        nr, nc = pos
        dr, dc = move_to_delta(action.move)
        next_pos = (nr + dr, nc + dc)
        self._last = pos  # prevPos = current pos before move
        nk = self._key(next_pos)
        self._recents[nk] = self._recents.get(nk, 0) + 1
        self._recent_list.append(nk)
        if len(self._recent_list) > 8:
            old = self._recent_list.pop(0)
            self._recents[old] -= 1
            if self._recents[old] <= 0:
                del self._recents[old]

        return action


def _mv(src, dst):
    dr, dc = dst[0] - src[0], dst[1] - src[1]
    if dr == -1:
        return Move.UP.value
    if dr == 1:
        return Move.DOWN.value
    if dc == -1:
        return Move.LEFT.value
    if dc == 1:
        return Move.RIGHT.value
    return Move.STAY.value
