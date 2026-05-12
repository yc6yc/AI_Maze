"""
state.py — 统一状态/动作数据结构定义
负责人：组长（角色1）
--------------------------------------
AI 挑战者接收到的信息是受限的：
  - 仅知道入口 S 的坐标（地图全貌不可见）
  - 已探索过的格子记录在 fog_map（迷宫大小已知，内容未知）
  - BOSS 数量与血量不可见，只有被击败后方可知
  - 复活金币消耗 CoinConsumption 可见
  - 玩家技能列表 PlayerSkills 可见
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any


# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
CELL_WALL   = "#"
CELL_EMPTY  = " "
CELL_START  = "S"
CELL_END    = "E"
CELL_BOSS   = "B"
CELL_TRAP   = "T"
CELL_COIN   = "C"
CELL_GOLD   = "G"   # 若 JSON 里出现 G 按金币处理（参考 input说明.txt 补充后可调整）
CELL_LOCK   = "L"   # 锁/机关（maze_15_15 里出现过）

WALKABLE = {CELL_EMPTY, CELL_START, CELL_END, CELL_BOSS,
            CELL_TRAP, CELL_COIN, CELL_GOLD, CELL_LOCK}

# --------------------------------------------------------------------------- #
# 技能
# --------------------------------------------------------------------------- #
@dataclass
class Skill:
    damage: int       # 伤害值 a_i
    cooldown: int     # 冷却时间 b_i（0 表示无冷却）
    remaining_cd: int = 0   # 当前剩余冷却（游戏内维护）

    @classmethod
    def from_list(cls, raw: List[int]) -> "Skill":
        return cls(damage=raw[0], cooldown=raw[1])


# --------------------------------------------------------------------------- #
# 玩家状态
# --------------------------------------------------------------------------- #
@dataclass
class PlayerState:
    pos: Tuple[int, int]                # (row, col) 当前位置
    hp: int = 100                       # 生命值（如有血量规则可扩展）
    coins: int = 0                      # 持有金币
    skills: List[Skill] = field(default_factory=list)
    round_num: int = 0                  # 当前回合数

    def tick_cooldowns(self):
        """每回合推进一步，减少所有技能冷却"""
        for sk in self.skills:
            if sk.remaining_cd > 0:
                sk.remaining_cd -= 1

    def available_skills(self) -> List[Tuple[int, Skill]]:
        """返回当前可用技能 (index, Skill)"""
        return [(i, sk) for i, sk in enumerate(self.skills) if sk.remaining_cd == 0]

    def use_skill(self, idx: int) -> int:
        """使用技能，返回伤害值，并触发冷却"""
        sk = self.skills[idx]
        if sk.remaining_cd > 0:
            raise RuntimeError(f"技能 {idx} 仍在冷却中")
        sk.remaining_cd = sk.cooldown
        return sk.damage


# --------------------------------------------------------------------------- #
# 迷宫地图（含探索状态）
# --------------------------------------------------------------------------- #
@dataclass
class MazeState:
    rows: int
    cols: int
    # fog_map[r][c] = None 表示未探索；否则存储已知格子内容
    fog_map: List[List[Optional[str]]] = field(default_factory=list)
    start: Optional[Tuple[int, int]] = None
    end: Optional[Tuple[int, int]] = None

    # 已知陷阱（一次触发后变为普通格子）
    triggered_traps: set = field(default_factory=set)

    def __post_init__(self):
        if not self.fog_map:
            self.fog_map = [[None] * self.cols for _ in range(self.rows)]

    def reveal(self, r: int, c: int, cell: str):
        """将 (r,c) 格子内容揭露"""
        self.fog_map[r][c] = cell
        if cell == CELL_START:
            self.start = (r, c)
        elif cell == CELL_END:
            self.end = (r, c)

    def get(self, r: int, c: int) -> Optional[str]:
        return self.fog_map[r][c]

    def is_walkable(self, r: int, c: int) -> bool:
        cell = self.fog_map[r][c]
        if cell is None:
            return False   # 未探索时不走
        return cell in WALKABLE

    def neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        """返回上下左右四邻居（不检查可通行性）"""
        result = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                result.append((nr, nc))
        return result

    @classmethod
    def from_full_map(cls, grid: List[List[str]]) -> "MazeState":
        """
        服务器/本地模拟时使用：直接从完整地图初始化。
        AI 真实对局时不应调用此方法（全图不可见）。
        """
        rows, cols = len(grid), len(grid[0])
        ms = cls(rows=rows, cols=cols)
        for r in range(rows):
            for c in range(cols):
                ms.reveal(r, c, grid[r][c])
        return ms


# --------------------------------------------------------------------------- #
# 动作定义
# --------------------------------------------------------------------------- #
DIRECTIONS = {
    "UP":    (-1,  0),
    "DOWN":  ( 1,  0),
    "LEFT":  ( 0, -1),
    "RIGHT": ( 0,  1),
    "STAY":  ( 0,  0),
}

@dataclass
class Action:
    move: str = "STAY"              # UP / DOWN / LEFT / RIGHT / STAY
    use_skill: Optional[int] = None # 攻击技能编号（None = 不攻击）

    def delta(self) -> Tuple[int, int]:
        return DIRECTIONS[self.move]


# --------------------------------------------------------------------------- #
# 完整游戏上下文（传给各 Agent）
# --------------------------------------------------------------------------- #
@dataclass
class GameContext:
    maze: MazeState
    player: PlayerState
    coin_consumption: int        # 复活/超时惩罚金币
    min_rounds: int              # 本轮目标回合数
    boss_defeated: List[int] = field(default_factory=list)   # 已击败 boss 的血量（可见）
    history: List[Dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        """输出当前快照（用于日志/可视化）"""
        return {
            "round": self.player.round_num,
            "pos": self.player.pos,
            "coins": self.player.coins,
            "boss_defeated": len(self.boss_defeated),
        }
