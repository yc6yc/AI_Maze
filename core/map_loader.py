from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .state import Position, Skill


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = PROJECT_ROOT / "map"


class MapValidationError(ValueError):
    pass


def resolve_map_path(name_or_path: str | Path) -> Path:
    path = Path(name_or_path)
    candidates: list[Path] = []
    if path.is_absolute():
        candidates.append(path)
    else:
        candidates.append(PROJECT_ROOT / path)
        candidates.append(MAP_DIR / path)
        if path.suffix != ".json":
            candidates.append(MAP_DIR / f"{path}.json")
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Map not found: {name_or_path}")


def load_json(path: str | Path) -> dict[str, Any]:
    resolved = resolve_map_path(path)
    with resolved.open("r", encoding="utf-8") as f:
        data = json.load(f)
    validate_map_data(data)
    return data


def save_map(path: str | Path, data: dict[str, Any]) -> Path:
    validate_map_data(data)
    target = Path(path)
    if not target.is_absolute():
        target = MAP_DIR / target
    if target.suffix != ".json":
        target = target.with_suffix(".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return target


def list_maps() -> list[str]:
    MAP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path.name for path in MAP_DIR.glob("*.json"))


def validate_map_data(data: dict[str, Any]) -> None:
    maze = data.get("maze")
    if not isinstance(maze, list) or not maze:
        raise MapValidationError("maze must be a non-empty 2D array")
    cols = None
    start_count = 0
    end_count = 0
    for row in maze:
        if not isinstance(row, list) or not row:
            raise MapValidationError("each maze row must be a non-empty array")
        cols = cols or len(row)
        if len(row) != cols:
            raise MapValidationError("maze rows must have equal length")
        for cell in row:
            if not isinstance(cell, str):
                raise MapValidationError("maze cells must be strings")
            if cell == "S":
                start_count += 1
            if cell == "E":
                end_count += 1
    if start_count != 1:
        raise MapValidationError("maze must contain exactly one S")
    if end_count != 1:
        raise MapValidationError("maze must contain exactly one E")


def find_cell(maze: list[list[str]], target: str) -> Position:
    for r, row in enumerate(maze):
        for c, cell in enumerate(row):
            if cell == target:
                return (r, c)
    raise MapValidationError(f"maze does not contain {target}")


def parse_skills(data: dict[str, Any]) -> list[Skill]:
    skills = data.get("PlayerSkills", [])
    result: list[Skill] = []
    if not isinstance(skills, list):
        return result
    for item in skills:
        if not isinstance(item, list | tuple) or len(item) < 2:
            continue
        result.append(Skill(damage=int(item[0]), cooldown=max(int(item[1]), 0)))
    return result
