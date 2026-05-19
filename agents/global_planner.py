"""
global_planner.py — 全局迷宫探索与路径规划（重构版）
负责人：角色3（算法B）
----------------------------------------------------
评价指标：总价值 / 总步数
  总价值 = 金币数×50 - 陷阱×30 - 挑战失败次数×CoinConsumption

核心矛盾：
  步数宝贵，但金币缓冲不足 → 失败后大量回头路 → 总价值/步数双重受损
  → 策略：提前囤够 retry_buffer 次重试的金币，再快速冲向 BOSS

五阶段状态机：
  ┌─────────────────────────────────────────────────────────┐
  │  EXPLORE      探索地图，顺路收集金币，主要目标：发现 BOSS  │
  │     ↓ 发现 BOSS 且金币 < 缓冲目标                        │
  │  COLLECT      专项补充金币至 retry_buffer×CoinConsumption │
  │     ↓ 金币充足（或 EXPLORE 时即满足）                     │
  │  RUSH_TO_BOSS 快速导航至 BOSS 格，由 CombatAgent 接管战斗 │
  │     ↓ 所有 BOSS 击败（fog_map 中 B 消失）                 │
  │  RUSH_TO_EXIT 冲向终点 E                                  │
  │     ↓ 挑战失败 & 金币 < CoinConsumption                   │
  │  RETRY_COLLECT 补充至够 1 次重试，再回 RUSH_TO_BOSS        │
  └─────────────────────────────────────────────────────────┘

BOSS 战失败检测（AI 侧启发式）：
  - ctx.player.coins 骤降（降幅 ≈ CoinConsumption）且仍在 RUSH_TO_BOSS
  - 或走迷宫总步数接近 max_rounds 仍未切换到 RUSH_TO_EXIT

minRounds 说明（来自服务器输入）：
  minRounds 是 BOSS 战内部的最大攻击轮数，每轮使用一个技能攻击 BOSS（BOSS 不反击）。
  若在 minRounds 轮内未击败 BOSS，则挑战失败，扣除 CoinConsumption 枚金币，
  已击败部分 BOSS 的血量将对玩家可见，可继续重试。
  minRounds 与走迷宫的步数（round_num）完全无关。
"""

from __future__ import annotations
from enum import Enum, auto
from typing import List, Optional, Tuple

from agents.base_agent import BaseAgent
from core.state import (
    GameContext, Action, MazeState,
    CELL_TRAP, CELL_COIN, CELL_GOLD, CELL_BOSS,
)
from core.pathfinding import astar, bfs

DEFAULT_CONFIG = {
    "w_coin": 2.0,
    "w_trap": 1.5,
    "retry_buffer": 3,          # 预留 N 次重试所需金币（N × CoinConsumption）
    "min_explore_ratio": 0.4,   # 至少探索此比例格子才允许提前切到 RUSH_TO_BOSS
    "rush_round_threshold": 50, # 走迷宫总步数（round_num）距 max_rounds 不足此值时强制冲 BOSS
}

Pos = Tuple[int, int]


class Phase(Enum):
    EXPLORE       = auto()   # 探索地图，顺路拾取
    COLLECT       = auto()   # 专项补充金币到缓冲目标
    RUSH_TO_BOSS  = auto()   # 冲向 BOSS 战
    RUSH_TO_EXIT  = auto()   # 所有 BOSS 击败后冲终点
    RETRY_COLLECT = auto()   # 挑战失败后金币不足，补充后重试


class GlobalPlannerAgent(BaseAgent):

    def __init__(self, config: dict = None):
        super().__init__(name="GlobalPlannerAgent")
        self.cfg = {**DEFAULT_CONFIG, **(config or {})}
        self.phase: Phase = Phase.EXPLORE
        self._path: List[Pos] = []

        # 内部追踪量
        self._known_boss_pos: Optional[Pos] = None   # 从 fog_map 发现的 BOSS 位置
        self._prev_coin: int = 0                     # 上回合金币数，用于检测失败扣款
        self._prev_boss_count: int = 0               # 上回合已击败 BOSS 数

    def on_episode_start(self, ctx: GameContext):
        self.phase = Phase.EXPLORE
        self._path = []
        self._known_boss_pos = None
        self._prev_coin = ctx.player.coins
        self._prev_boss_count = 0

    # ------------------------------------------------------------------ #
    # 主接口
    # ------------------------------------------------------------------ #
    def decide(self, ctx: GameContext) -> Action:
        self._scan_boss(ctx.maze)          # 更新已知 BOSS 位置
        self._detect_failure(ctx)          # 检测是否刚刚挑战失败
        self._detect_boss_defeated(ctx)    # 检测是否所有 BOSS 已被击败
        self._update_phase(ctx)            # 状态机切换

        if not self._path or not ctx.maze.is_walkable(*self._path[0]):
            self._replan(ctx)

        if not self._path:
            return Action(move="STAY")

        next_pos = self._path.pop(0)
        self._prev_coin = ctx.player.coins
        self._prev_boss_count = len(ctx.boss_defeated)
        return Action(move=_pos_to_move(ctx.player.pos, next_pos))

    # ------------------------------------------------------------------ #
    # 事件检测
    # ------------------------------------------------------------------ #
    def _scan_boss(self, maze: MazeState):
        """从 fog_map 中找 BOSS 格子位置；若已消失则清除记录"""
        if self._known_boss_pos is not None:
            r, c = self._known_boss_pos
            if maze.fog_map[r][c] != CELL_BOSS:
                # BOSS 格子内容已改变（全部击败后服务器会更新）
                self._known_boss_pos = None
            return
        for r in range(maze.rows):
            for c in range(maze.cols):
                if maze.fog_map[r][c] == CELL_BOSS:
                    self._known_boss_pos = (r, c)
                    return

    def _detect_failure(self, ctx: GameContext):
        """
        BOSS 挑战失败检测（启发式）：
        金币相比上回合减少约 CoinConsumption，且 BOSS 仍未被击败。
        """
        cc = ctx.coin_consumption
        if cc <= 0:
            return
        coin_drop = self._prev_coin - ctx.player.coins
        # 金币骤降 ≈ CoinConsumption 且不是正常拾取导致（拾取会增加金币）
        if coin_drop >= cc * 0.8 and self.phase == Phase.RUSH_TO_BOSS:
            # 挑战失败，检查是否还有足够金币
            if ctx.player.coins < cc:
                self.phase = Phase.RETRY_COLLECT
                self._path = []

    def _detect_boss_defeated(self, ctx: GameContext):
        """
        所有 BOSS 击败检测：
        策略：fog_map 中 BOSS 格消失（服务器更新格子内容）
        或 boss_defeated 列表增长后用 BFS 确认终点可直接到达。
        """
        if self.phase == Phase.RUSH_TO_EXIT:
            return
        # BOSS 格已消失 + 曾击败过至少一个 BOSS
        if self._known_boss_pos is None and len(ctx.boss_defeated) > 0:
            self.phase = Phase.RUSH_TO_EXIT
            self._path = []
            return
        # 备用：boss_defeated 增长后尝试 BFS 到终点，若无阻断则切换
        if (len(ctx.boss_defeated) > self._prev_boss_count
                and ctx.maze.end is not None):
            path = bfs(ctx.maze, ctx.player.pos, ctx.maze.end)
            if path is not None:
                self.phase = Phase.RUSH_TO_EXIT
                self._path = []

    # ------------------------------------------------------------------ #
    # 阶段切换
    # ------------------------------------------------------------------ #
    def _update_phase(self, ctx: GameContext):
        # RUSH_TO_EXIT 不可逆
        if self.phase == Phase.RUSH_TO_EXIT:
            return

        coins = ctx.player.coins
        cc = ctx.coin_consumption
        buf = self.cfg["retry_buffer"]
        target_coins = buf * cc if cc > 0 else 0   # 缓冲目标金币数

        # RETRY_COLLECT：凑够 1 次重试即可
        if self.phase == Phase.RETRY_COLLECT:
            if coins >= cc:
                self.phase = Phase.RUSH_TO_BOSS
                self._path = []
            return

        # 时间压力：走迷宫总步数接近 max_rounds 上限时，强制冲 BOSS
        # 注意：min_rounds 是 BOSS 战的攻击轮数限制，与 round_num 无关
        max_rounds = self.cfg.get("max_rounds", 500)
        steps_left = max_rounds - ctx.player.round_num
        if steps_left <= self.cfg["rush_round_threshold"] and self._known_boss_pos:
            if self.phase not in (Phase.RUSH_TO_BOSS,):
                self.phase = Phase.RUSH_TO_BOSS
                self._path = []
            return

        boss_known = self._known_boss_pos is not None

        # 计算已探索比例（用于防止太早放弃探索）
        total = ctx.maze.rows * ctx.maze.cols
        explored = sum(
            1 for r in range(ctx.maze.rows)
            for c in range(ctx.maze.cols)
            if ctx.maze.fog_map[r][c] is not None
        )
        explore_ratio = explored / total

        coin_ready = coins >= target_coins
        explored_enough = explore_ratio >= self.cfg["min_explore_ratio"]

        if self.phase in (Phase.EXPLORE, Phase.COLLECT):
            if boss_known and coin_ready and explored_enough:
                # 金币充足 + 已发现 BOSS + 探索充分 → 冲 BOSS
                self.phase = Phase.RUSH_TO_BOSS
                self._path = []
            elif boss_known and not coin_ready:
                # 已知 BOSS 在哪但金币不够 → 专项收集
                self.phase = Phase.COLLECT
            # else: 继续探索（还没找到 BOSS，或金币已足但探索不够）

    # ------------------------------------------------------------------ #
    # 重新规划路径
    # ------------------------------------------------------------------ #
    def _replan(self, ctx: GameContext):
        pos = ctx.player.pos
        maze = ctx.maze

        if self.phase == Phase.RUSH_TO_EXIT:
            # 直冲终点，不绕陷阱（时间优先）
            self._path = self._astar_path(pos, maze.end, maze, avoid_traps=False)
            return

        if self.phase == Phase.RUSH_TO_BOSS:
            goal = self._known_boss_pos
            if goal is None:
                # BOSS 未发现，回退到探索
                self.phase = Phase.EXPLORE
                self._replan(ctx)
                return
            # 冲 BOSS 时尽量绕陷阱（保留金币）
            self._path = self._astar_path(pos, goal, maze, avoid_traps=True)
            if not self._path:
                # 绕不开陷阱时强行通过
                self._path = self._astar_path(pos, goal, maze, avoid_traps=False)
            return

        if self.phase == Phase.EXPLORE:
            goal = self._nearest_frontier(pos, maze)
            if goal is None:
                # 全图已探索，转收集
                self.phase = Phase.COLLECT
                self._replan(ctx)
                return
            self._path = self._astar_path(pos, goal, maze, avoid_traps=False)
            return

        if self.phase in (Phase.COLLECT, Phase.RETRY_COLLECT):
            goal = self._best_coin_target(pos, maze)
            if goal is None:
                # 地图内无金币 → 只能硬冲 BOSS
                self.phase = Phase.RUSH_TO_BOSS
                self._replan(ctx)
                return
            self._path = self._astar_path(pos, goal, maze, avoid_traps=True)
            if not self._path:
                self._path = self._astar_path(pos, goal, maze, avoid_traps=False)

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    def _astar_path(
        self,
        pos: Pos,
        goal: Optional[Pos],
        maze: MazeState,
        avoid_traps: bool,
    ) -> List[Pos]:
        if goal is None:
            return []
        wk = (lambda r, c: self._custom_walkable(r, c, maze)) if avoid_traps else None
        path = astar(maze, pos, goal, walkable_override=wk)
        return path[1:] if path else []

    def _nearest_frontier(self, pos: Pos, maze: MazeState) -> Optional[Pos]:
        """最近的前沿格子（已知可行 & 有未知邻居）"""
        best: Optional[Tuple[float, Pos]] = None
        for r in range(maze.rows):
            for c in range(maze.cols):
                if maze.fog_map[r][c] is None or not maze.is_walkable(r, c):
                    continue
                for nr, nc in maze.neighbors(r, c):
                    if maze.fog_map[nr][nc] is None:
                        dist = abs(r - pos[0]) + abs(c - pos[1])
                        if best is None or dist < best[0]:
                            best = (dist, (r, c))
                        break
        return best[1] if best else None

    def _best_coin_target(self, pos: Pos, maze: MazeState) -> Optional[Pos]:
        """性价比最高的金币格子：coin_value / (曼哈顿距离 + 1)"""
        best_score, best_pos = -1e9, None
        for r in range(maze.rows):
            for c in range(maze.cols):
                if maze.fog_map[r][c] not in (CELL_COIN, CELL_GOLD):
                    continue
                dist = abs(r - pos[0]) + abs(c - pos[1]) + 1
                score = self.cfg["w_coin"] * 50 / dist
                if score > best_score:
                    best_score, best_pos = score, (r, c)
        return best_pos

    def _custom_walkable(self, r: int, c: int, maze: MazeState) -> bool:
        """尽量绕开未触发陷阱"""
        if not maze.is_walkable(r, c):
            return False
        cell = maze.fog_map[r][c]
        if cell == CELL_TRAP and (r, c) not in maze.triggered_traps:
            return False
        return True


def _pos_to_move(src: Pos, dst: Pos) -> str:
    dr = dst[0] - src[0]
    dc = dst[1] - src[1]
    if dr == -1: return "UP"
    if dr ==  1: return "DOWN"
    if dc == -1: return "LEFT"
    if dc ==  1: return "RIGHT"
    return "STAY"
