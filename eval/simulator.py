"""
simulator.py — 本地模拟器（离线验证用）
负责人：角色4（评测）
--------------------------------------------
在没有真实裁判服务器时，本地跑通一局完整游戏。
完整地图在模拟器中可见，AI 仍只收到受限视野（通过 fog 机制实现）。

使用方式：
    sim = LocalSimulator.from_json("maze_15_15.json")
    sim.run(agent, max_rounds=200)
    print(sim.stats())
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, Tuple

from core.state import (
    GameContext, MazeState, PlayerState, Skill, Action,
    CELL_TRAP, CELL_COIN, CELL_GOLD, CELL_BOSS, CELL_END, CELL_WALL,
)
from agents.base_agent import BaseAgent

COIN_VALUE = 50
TRAP_DAMAGE = 30
VIEW_RADIUS = 1   # 3×3 视野半径


class LocalSimulator:
    """
    本地离线模拟器。
    ground_truth_grid: 完整地图（模拟器持有，AI 不直接访问）
    ctx: 传给 AI 的受限上下文（fog_map 只揭露已探索区域）
    """

    def __init__(
        self,
        ground_truth: List[List[str]],
        skills: List[List[int]],
        boss_hp: List[int],
        coin_consumption: int,
        min_rounds: int,
    ):
        self.ground_truth = ground_truth
        rows, cols = len(ground_truth), len(ground_truth[0])
        self.rows, self.cols = rows, cols

        # 找到起点
        start = self._find_cell("S")
        assert start is not None, "地图中缺少起点 S"

        # AI 可见的受限地图（fog）
        fog_maze = MazeState(rows=rows, cols=cols)

        player = PlayerState(
            pos=start,
            skills=[Skill.from_list(s) for s in skills],
        )

        self.ctx = GameContext(
            maze=fog_maze,
            player=player,
            coin_consumption=coin_consumption,
            min_rounds=min_rounds,
        )

        # 模拟器内部状态
        self._boss_hp: List[int] = list(boss_hp)
        self._boss_idx: int = 0   # 当前应击败的 boss 序号（顺序固定）
        self._done: bool = False
        self._won: bool = False
        self._round: int = 0

        # 初始揭露起点视野
        self._reveal_fov(start)

    # ------------------------------------------------------------------ #
    # 工厂方法
    # ------------------------------------------------------------------ #
    @classmethod
    def from_json(cls, path: str) -> "LocalSimulator":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            ground_truth=data["maze"],
            skills=data["PlayerSkills"],
            boss_hp=data["B"],
            coin_consumption=data["CoinConsumption"],
            min_rounds=data["minRouds"],
        )

    # ------------------------------------------------------------------ #
    # 主循环
    # ------------------------------------------------------------------ #
    def run(self, agent: BaseAgent, max_rounds: int = 500) -> Dict[str, Any]:
        agent.on_episode_start(self.ctx)
        while not self._done and self._round < max_rounds:
            action = agent.decide(self.ctx)
            self._step(action)
        agent.on_episode_end(self.ctx)
        return self.stats()

    def _step(self, action: Action):
        self._round += 1
        ctx = self.ctx
        player = ctx.player
        player.round_num = self._round

        # 1. 移动
        dr, dc = action.delta()
        r, c = player.pos
        nr, nc = r + dr, c + dc

        # 边界与墙壁检查（以 ground_truth 为准）
        if (0 <= nr < self.rows and 0 <= nc < self.cols
                and self.ground_truth[nr][nc] != CELL_WALL):
            player.pos = (nr, nc)

        pr, pc = player.pos
        cell = self.ground_truth[pr][pc]

        # 2. 格子效果
        if cell == CELL_TRAP and (pr, pc) not in ctx.maze.triggered_traps:
            player.coins -= TRAP_DAMAGE
            ctx.maze.triggered_traps.add((pr, pc))

        elif cell in (CELL_COIN, CELL_GOLD):
            player.coins += COIN_VALUE
            # 拾取后格子变为空地（模拟器更新 ground_truth）
            self.ground_truth[pr][pc] = " "
            ctx.maze.reveal(pr, pc, " ")

        elif cell == CELL_BOSS:
            self._handle_boss(action)

        elif cell == CELL_END:
            if self._boss_idx >= len(self._boss_hp):
                self._done = True
                self._won = True

        # 3. 揭露 FOV
        self._reveal_fov(player.pos)

        # 4. 技能冷却
        player.tick_cooldowns()

        # 5. 记录快照（走迷宫无超时金币惩罚；超出 max_rounds 由 run() 的 while 条件终止）
        ctx.history.append(ctx.snapshot())

    def _handle_boss(self, action: Action):
        """处理 BOSS 战斗"""
        if self._boss_idx >= len(self._boss_hp):
            return
        if action.use_skill is None:
            return
        try:
            dmg = self.ctx.player.use_skill(action.use_skill)
        except RuntimeError:
            return
        self._boss_hp[self._boss_idx] -= dmg
        if self._boss_hp[self._boss_idx] <= 0:
            # BOSS 击败
            self.ctx.boss_defeated.append(self._boss_hp[self._boss_idx])
            self._boss_idx += 1

    # ------------------------------------------------------------------ #
    # 视野揭露（3×3）
    # ------------------------------------------------------------------ #
    def _reveal_fov(self, pos: Tuple[int, int]):
        r, c = pos
        for dr in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
            for dc in range(-VIEW_RADIUS, VIEW_RADIUS + 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    self.ctx.maze.reveal(nr, nc, self.ground_truth[nr][nc])

    def _find_cell(self, target: str) -> Optional[Tuple[int, int]]:
        for r, row in enumerate(self.ground_truth):
            for c, cell in enumerate(row):
                if cell == target:
                    return (r, c)
        return None

    # ------------------------------------------------------------------ #
    # 统计
    # ------------------------------------------------------------------ #
    def stats(self) -> Dict[str, Any]:
        player = self.ctx.player
        return {
            "won": self._won,
            "rounds": self._round,
            "coins": player.coins,
            "boss_defeated": self._boss_idx,
            "history_len": len(self.ctx.history),
        }
