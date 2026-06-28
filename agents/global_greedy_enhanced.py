"""
global_greedy_enhanced.py — Algorithm B (Enhanced Global Greedy)
Faithful port of web/app.js simulateGlobalGreedy with ALL proven optimizations:

1. Dead-end coin penalty (walkableNbrs <= 2 → cost × 1.8)
2. Frontier revisit suppression (target × 3 + first-step × 5)
3. Exit-visible frontier suppression
4. Direction momentum (+6 same, -4 opposite)
5. Candidate first-step oscillation suppression (>=3: -8, >=2: -3)
"""
from __future__ import annotations
from agents.base import BaseAgent
from core.pathfinding import dijkstra, extract_path
from core.state import Action, GameContext, MazeState, Move, Position, COIN_CELLS


CFG = {
    "coin": 50.0, "front_val": 14.0, "boss_val": 120.0, "exit_val": 1_000_000.0,
    "trap_cost": 31.0, "retry_buf": 1, "front_unk_w": 4.0, "revisit": 0.15,
    "min_explore": 0.25,
    # enhanced:
    "dead_mul": 1.8, "ft_revisit": 3.0, "ff_revisit": 5.0,
    "mom_bonus": 6.0, "mom_pen": 4.0, "osc_heavy": 8.0, "osc_mild": 3.0,
}


class GlobalGreedyEnhancedAgent(BaseAgent):
    def __init__(self, config=None):
        self.c = {**CFG, **(config or {})}
        self._vc: dict[Position, int] = {}
        self._ld: tuple[int, int] | None = None
        self._kb: list[Position] = []

    def on_episode_start(self, ctx: GameContext):
        self._vc = {ctx.player.pos: 1}
        self._ld = None
        self._kb = []

    def on_episode_end(self, ctx: GameContext): pass

    # -- helpers --
    def _cost_fn(self, ctx: MazeState):
        tc = self.c["trap_cost"]
        return lambda p: 1.0 + tc if ctx.cell(p) == "T" and p not in ctx.triggered_traps else 1.0

    def _dij(self, maze, start): return dijkstra(maze, start, cost_fn=self._cost_fn(maze))

    def _walkable_nbrs(self, maze, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)) if maze.is_walkable((r+dr, c+dc)))

    def _unk_nbrs(self, maze, pos):
        r, c = pos
        return sum(1 for dr, dc in ((-1,0),(1,0),(0,-1),(0,1))
                   if 0 <= r+dr < maze.rows and 0 <= c+dc < maze.cols and maze.fog_map[r+dr][c+dc] is None)

    def _scan_bosses(self, maze): return [p for p, c in maze.known_cells() if c == "B"]

    def _expl_ratio(self, maze):
        t = maze.rows * maze.cols
        e = sum(1 for _, c in maze.known_cells())
        return e / t if t else 0.0

    def _force_collect(self, coins, cc):
        if not self._kb: return False
        need = max(cc * self.c["retry_buf"], cc)
        return coins < need

    def _score_boss(self, dist, coins, maze, cc):
        if not self._kb: return -1e9
        need = max(cc * self.c["retry_buf"], cc)
        ready = coins >= need
        base = self.c["boss_val"] / max(dist, 1.0)
        base += 40.0 if ready else -max(0.0, need - coins)
        if self._expl_ratio(maze) < self.c["min_explore"] and not ready: base -= 25.0
        return base

    def _exit_visible(self, maze): return any(c == "E" for _, c in maze.known_cells())

    def _find_frontiers(self, maze):
        out = []
        for pos, _ in maze.known_cells():
            if not maze.is_walkable(pos): continue
            r, c = pos
            for dr, dc in ((-1,0),(1,0),(0,-1),(0,1)):
                nr, nc = r+dr, c+dc
                if 0 <= nr < maze.rows and 0 <= nc < maze.cols and maze.fog_map[nr][nc] is None:
                    out.append(pos); break
        return out

    # -- main decide --
    def decide(self, ctx: GameContext) -> Action:
        maze = ctx.maze
        pos = ctx.player.pos
        coins = ctx.player.coins
        cc = ctx.coin_consumption
        boss_done = ctx.boss_defeated
        cfg = self.c

        self._kb = self._scan_bosses(maze)
        self._vc[pos] = self._vc.get(pos, 0) + 1

        cands: list[tuple[str, float, list[Position]]] = []  # (type, score, movePath)
        d, prev = self._dij(maze, pos)

        # Scan all known cells
        for tpos, cell in maze.known_cells():
            if tpos == pos or tpos not in d: continue
            path = extract_path(prev, pos, tpos)
            if not path or len(path) < 2: continue
            mp = path[1:]
            if not mp: continue
            dc = d[tpos]
            rp = cfg["revisit"] * self._vc.get(tpos, 0)

            if cell in COIN_CELLS:
                wn = self._walkable_nbrs(maze, tpos)
                ed = dc * cfg["dead_mul"] if wn <= 2 else dc
                sc = cfg["coin"] / max(ed, 1.0) - rp
                if self._force_collect(coins, cc): sc += 20.0
                cands.append(("coin", sc, mp))
            elif cell == "B":
                sc = self._score_boss(dc, coins, maze, cc) - rp
                cands.append(("boss", sc, mp))
            elif cell == "E" and boss_done:
                cands.append(("exit", cfg["exit_val"] / max(dc, 1.0), mp))

        # Frontiers
        ev = self._exit_visible(maze)
        if not ev or not boss_done:
            for f in self._find_frontiers(maze):
                if f == pos or f not in d: continue
                fp = extract_path(prev, pos, f)
                if not fp or len(fp) < 2: continue
                fmp = fp[1:]
                if not fmp: continue
                unk = self._unk_nbrs(maze, f)
                fs = (cfg["front_val"] + cfg["front_unk_w"] * unk) / max(d[f], 1.0)
                fs -= cfg["ft_revisit"] * self._vc.get(f, 0)
                fs -= cfg["ff_revisit"] * self._vc.get(fmp[0], 0)
                cands.append(("frontier", fs, fmp))

        if not cands: return Action(move=Move.STAY.value)

        # Direction momentum (frontiers only)
        if self._ld:
            for i, (ty, sc, path) in enumerate(cands):
                if ty != "frontier" or not path: continue
                dr, dc = path[0][0] - pos[0], path[0][1] - pos[1]
                if (dr, dc) == self._ld: cands[i] = (ty, sc + cfg["mom_bonus"], path)
                elif (dr, dc) == (-self._ld[0], -self._ld[1]): cands[i] = (ty, sc - cfg["mom_pen"], path)

        # Oscillation suppression
        for i, (ty, sc, path) in enumerate(cands):
            if not path: continue
            v = self._vc.get(path[0], 0)
            if v >= 3: cands[i] = (ty, sc - cfg["osc_heavy"], path)
            elif v >= 2: cands[i] = (ty, sc - cfg["osc_mild"], path)

        cands.sort(key=lambda x: x[1], reverse=True)
        bp = cands[0][2]
        if not bp: return Action(move=Move.STAY.value)

        self._ld = (bp[0][0] - pos[0], bp[0][1] - pos[1])
        return Action(move=_mv(pos, bp[0]))


def _mv(src, dst):
    dr, dc = dst[0] - src[0], dst[1] - src[1]
    if dr == -1: return Move.UP.value
    if dr == 1: return Move.DOWN.value
    if dc == -1: return Move.LEFT.value
    if dc == 1: return Move.RIGHT.value
    return Move.STAY.value
