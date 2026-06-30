from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Literal


Position = tuple[int, int]
Cell = str | None


class Move(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    STAY = "STAY"


MOVE_DELTAS: dict[str, Position] = {
    Move.UP.value: (-1, 0),
    Move.DOWN.value: (1, 0),
    Move.LEFT.value: (0, -1),
    Move.RIGHT.value: (0, 1),
    Move.STAY.value: (0, 0),
}

CARDINAL_MOVES: tuple[str, ...] = (
    Move.UP.value,
    Move.DOWN.value,
    Move.LEFT.value,
    Move.RIGHT.value,
)

WALKABLE_CELLS = {" ", ".", "S", "E", "B", "T", "C", "G", "L"}
COIN_CELLS = {"C", "G"}


@dataclass
class Skill:
    damage: int
    cooldown: int
    remaining_cooldown: int = 0

    def clone(self) -> Skill:
        return Skill(self.damage, self.cooldown, self.remaining_cooldown)


@dataclass
class PlayerState:
    pos: Position
    coins: int = 0
    skills: list[Skill] = field(default_factory=list)
    rounds: int = 0

    def clone(self) -> PlayerState:
        return PlayerState(
            pos=self.pos,
            coins=self.coins,
            skills=[skill.clone() for skill in self.skills],
            rounds=self.rounds,
        )


@dataclass
class MazeState:
    rows: int
    cols: int
    fog_map: list[list[Cell]]
    start: Position
    end: Position
    triggered_traps: set[Position] = field(default_factory=set)
    defeated_bosses: set[Position] = field(default_factory=set)

    def in_bounds(self, pos: Position) -> bool:
        r, c = pos
        return 0 <= r < self.rows and 0 <= c < self.cols

    def cell(self, pos: Position) -> Cell:
        r, c = pos
        if not self.in_bounds(pos):
            return "#"
        return self.fog_map[r][c]

    def is_walkable(self, pos: Position) -> bool:
        cell = self.cell(pos)
        return cell in WALKABLE_CELLS

    def known_cells(self) -> Iterable[tuple[Position, str]]:
        for r, row in enumerate(self.fog_map):
            for c, cell in enumerate(row):
                if cell is not None:
                    yield (r, c), cell


@dataclass(frozen=True)
class Action:
    move: str = Move.STAY.value
    use_skill: int | None = None

    def normalized_move(self) -> str:
        return self.move if self.move in MOVE_DELTAS else Move.STAY.value


@dataclass
class GameContext:
    maze: MazeState
    player: PlayerState
    boss_healths: list[int]
    min_rounds: int
    coin_consumption: int
    step_count: int = 0
    max_steps: int = 500
    boss_defeated: bool = False
    done: bool = False
    result: Literal["running", "win", "lose", "timeout"] = "running"
    history: list[dict[str, Any]] = field(default_factory=list)
    last_event: dict[str, Any] | None = None


def move_to_delta(move: str) -> Position:
    return MOVE_DELTAS.get(move, (0, 0))


def delta_to_move(delta: Position) -> str:
    for move, move_delta in MOVE_DELTAS.items():
        if move_delta == delta:
            return move
    return Move.STAY.value


def step_toward(src: Position, dst: Position) -> str:
    sr, sc = src
    dr, dc = dst
    return delta_to_move((dr - sr, dc - sc))


def serialize_fog_map(fog_map: list[list[Cell]]) -> list[list[Cell]]:
    return [[cell for cell in row] for row in fog_map]
