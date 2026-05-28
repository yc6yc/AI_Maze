"""
sim_with_boss_window.py — 保持现有 sim 流程，同时在 BOSS 战时弹出独立窗口

用法：
    python sim_with_boss_window.py --map maze_15_15.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents.composite_agent import CompositeAgent
from eval.simulator import LocalSimulator
from map_loader import resolve_map_path
from main import load_config
from viz.boss_battle_visualizer import DEFAULT_BOSS_BATTLE_FPS, make_visual_boss_battle_handler


def run_sim_with_boss_window(map_path: str, cfg: dict, max_rounds: int = 500, fps: int = DEFAULT_BOSS_BATTLE_FPS):
    with open(map_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    boss_handler = make_visual_boss_battle_handler(
        skill_specs=data.get("PlayerSkills", []),
        boss_hps=data.get("B", []),
        min_rounds=data.get("minRouds", 0),
        coin_consumption=data.get("CoinConsumption", 0),
        fps=fps,
    )

    sim = LocalSimulator.from_json(map_path, boss_battle_handler=boss_handler)
    agent = CompositeAgent(config=cfg)
    stats = sim.run(agent, max_rounds=max_rounds)
    print(f"[SIM+BOSS] 结果: {stats}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="本地模拟 + 独立 BOSS 战窗口")
    parser.add_argument("--map", default="maze_15_15.json")
    parser.add_argument("--rounds", type=int, default=500)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--fps", type=int, default=DEFAULT_BOSS_BATTLE_FPS)
    args = parser.parse_args()

    cfg = load_config(args.config)
    map_path = resolve_map_path(str(Path(args.map)))
    run_sim_with_boss_window(map_path, cfg, max_rounds=args.rounds, fps=args.fps)


if __name__ == "__main__":
    main()
