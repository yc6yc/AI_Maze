from __future__ import annotations

from pathlib import Path


def resolve_map_path(map_arg: str = "maze_15_15.json") -> str:
    """
    Resolve map path with folder fallback:
    1) explicit path if it exists
    2) ./map地图/<file>
    3) ./map/<file>
    4) ./<file>
    """
    candidate = Path(map_arg)
    if candidate.exists():
        return str(candidate)

    base = candidate.name
    search_list = [
        Path("map地图") / base,
        Path("map") / base,
        Path(base),
    ]
    for path in search_list:
        if path.exists():
            return str(path)
    return map_arg
