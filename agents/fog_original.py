"""
fog_original.py — Fog-constrained A* Planner
Faithful port of web/app.js simulateFogOriginal — all proven optimizations included.

Priorities: Exit > Boss > Coin(ratio-filter + dead-end-penalty) > Frontier > Fallback
"""
from __future__ import annotations
from agents.base import BaseAgent
from core.pathfinding import dijkstra, extract_path, neighbors
from core.state import Action, GameContext, Move, Position, COIN_CELLS


CFG = {
    "coin": 50, "trap_dmg": 30, "trap_cost": 31,
    "front_base": 8.0, "front_unk_w": 4.0, "dead_mul": 1.8,
    "min_gain": 5.0, "back_pen": 5.0, "osc_pen": 5.0,
}


class FogOriginalAgent(BaseAgent):
    def __init__(self, config=None):
        self.c = {**CFG, **(config or {})}
        self._last: Position | None = None
        self._recents: set[str] = set()

    def on_episode_start(self, ctx: GameContext) -> None:
        self._last = None
        self._recents = set()

    def on_episode_end(self, ctx: GameContext) -> None: pass

    # -- helpers --
    def _key(self, p: Position) -> str: return f"{p[0]},{p[1]}"

    def _cost_fn(self, ctx: GameContext):
        tc = self.c["trap_cost"]
        return lambda p: 1.0 + tc if ctx.maze.cell(p) == "T" and p not in ctx.maze.triggered_traps else 1.0

    def _dij(self, ctx, start): return dijkstra(ctx.maze, start, cost_fn=self._cost_fn(ctx))

    def _visible(self, ctx, cells):
        return [p for p, c in ctx.maze.known_cells() if c in cells]

    def _walkable_nbrs(self, ctx, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)) if ctx.maze.is_walkable((r+dr, c+dc)))

    def _unk_nbrs(self, ctx, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                   if 0 <= r+dr < ctx.maze.rows and 0 <= c+dc < ctx.maze.cols and ctx.maze.fog_map[r+dr][c+dc] is None)

    def _frontiers(self, ctx):
        out = []
        for pos, _ in ctx.maze.known_cells():
            if not ctx.maze.is_walkable(pos): continue
            r, c = pos
            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                nr, nc = r+dr, c+dc
                if 0 <= nr < ctx.maze.rows and 0 <= nc < ctx.maze.cols and ctx.maze.fog_map[nr][nc] is None:
                    out.append(pos); break
        return out

    def _traps_on_path(self, ctx, path):
        return sum(1 for p in path if ctx.maze.cell(p) == "T" and p not in ctx.maze.triggered_traps)

    def _best_to(self, ctx, pos, targets):
        best_p, best_d, best_t = None, float("inf"), None
        for t in targets:
            d, prev = self._dij(ctx, pos)
            if t in d and d[t] < best_d:
                best_d, best_p, best_t = d[t], extract_path(prev, pos, t), t
        return best_p, best_t

    # -- main decide --
    def decide(self, ctx: GameContext) -> Action:
        pos = ctx.player.pos
        coins = ctx.player.coins
        steps = ctx.step_count
        boss_done = ctx.boss_defeated
        cfg = self.c

        exits = self._visible(ctx, {"E"})
        bosses = self._visible(ctx, {"B"})
        coins_pos = self._visible(ctx, COIN_CELLS)

        # P1: Exit
        if boss_done and exits:
            p, _ = self._best_to(ctx, pos, exits)
            if p and len(p) >= 2: return Action(move=_mv(pos, p[1]))

        # P2: Boss
        if bosses:
            p, _ = self._best_to(ctx, pos, bosses)
            if p and len(p) >= 2: return Action(move=_mv(pos, p[1]))

        # P3: Coin
        if coins_pos:
            best_r, best_act = -float("inf"), None
            exit_known = bool(exits)
            baseline = 0.0
            if exit_known:
                ep, _ = self._best_to(ctx, pos, exits)
                ed = len(ep) - 1 if ep else 0
                baseline = coins / max(steps + ed, 1)

            for cp in coins_pos:
                d, prev = self._dij(ctx, pos)
                if cp not in d: continue
                cpath = extract_path(prev, pos, cp)
                if not cpath or len(cpath) < 2: continue
                dist = len(cpath) - 1
                tr = self._traps_on_path(ctx, cpath)
                net = cfg["coin"] - tr * cfg["trap_dmg"]
                if net <= 0: continue
                wn = self._walkable_nbrs(ctx, cp)
                eff = dist * cfg["dead_mul"] if wn <= 2 else dist
                gps = net / max(eff, 1)
                if not exit_known and gps < cfg["min_gain"]: continue
                cr = float("-inf")
                if exits:
                    d2, _ = self._dij(ctx, cp)
                    e2 = d2.get(exits[0], float("inf"))
                    cr = (coins + net) / max(steps + eff + e2, 1)
                else:
                    cr = gps
                if cr > best_r:
                    best_r = cr
                    best_act = Action(move=_mv(pos, cpath[1]))
            if best_act and (not exit_known or best_r > baseline):
                return best_act

        # P4: Frontiers
        fronts = self._frontiers(ctx)
        if fronts:
            best_fs, best_fa = -float("inf"), None
            d, prev = self._dij(ctx, pos)
            for f in fronts:
                if f == pos or f not in d: continue
                fp = extract_path(prev, pos, f)
                if not fp or len(fp) < 2: continue
                unk = self._unk_nbrs(ctx, f)
                fs = (cfg["front_base"] + cfg["front_unk_w"] * unk) / max(len(fp) - 1, 1)
                fs2 = fp[1]
                if self._last and fs2 == self._last: fs -= cfg["back_pen"]
                if self._key(fs2) in self._recents: fs -= cfg["osc_pen"]
                if fs > best_fs: best_fs, best_fa = fs, Action(move=_mv(pos, fs2))
            if best_fa: return best_fa

        # P5: Fallback — any non-wall neighbor
        nbrs = neighbors(pos, ctx.maze, walkable_override=lambda p: ctx.maze.cell(p) != "#")
        if nbrs:
            best = nbrs[0]
            if self._last:
                for n in nbrs:
                    if n != self._last: best = n; break
            return Action(move=_mv(pos, best))
        return Action(move=Move.STAY.value)


def _mv(src, dst):
    dr, dc = dst[0] - src[0], dst[1] - src[1]
    if dr == -1: return Move.UP.value
    if dr == 1: return Move.DOWN.value
    if dc == -1: return Move.LEFT.value
    if dc == 1: return Move.RIGHT.value
    return Move.STAY.value
