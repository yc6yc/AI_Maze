"""
boss_visualize.py — 独立打开 BOSS 战可视化窗口

用法：
    python boss_visualize.py --map maze_15_15.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.state import GameContext, MazeState, PlayerState, Skill
from viz.boss_battle_visualizer import (
    render_boss_battle_window,
    save_boss_battle_gif,
    simulate_boss_battle_frames,
)


def build_boss_demo_context(map_path: str) -> tuple[GameContext, list[int]]:
    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    maze = MazeState.from_full_map(data["maze"])
    boss_pos = None
    for r, row in enumerate(data["maze"]):
        for c, cell in enumerate(row):
            if cell == "B":
                boss_pos = (r, c)
                break
        if boss_pos is not None:
            break

    if boss_pos is None:
        raise ValueError("地图中未找到 BOSS 格子")

    player = PlayerState(
        pos=boss_pos,
        coins=0,
        skills=[Skill.from_list(spec) for spec in data.get("PlayerSkills", [])],
    )

    ctx = GameContext(
        maze=maze,
        player=player,
        coin_consumption=data.get("CoinConsumption", 0),
        min_rounds=data.get("minRouds", 0),
    )
    return ctx, list(data.get("B", []))


def main():
    parser = argparse.ArgumentParser(description="独立 BOSS 战可视化")
    parser.add_argument("--map", default="maze_15_15.json")
    parser.add_argument("--fps", type=int, default=3)
    parser.add_argument("--save-gif", action="store_true")
    parser.add_argument("--gif-path", default="boss_battle.gif")
    args = parser.parse_args()

    map_path = str(Path(args.map))
    ctx, boss_hps = build_boss_demo_context(map_path)
    frames = simulate_boss_battle_frames(ctx, boss_hps)

    if args.save_gif:
        save_boss_battle_gif(frames, output_path=args.gif_path, fps=args.fps)

    render_boss_battle_window(frames, fps=args.fps)


if __name__ == "__main__":
    main()
