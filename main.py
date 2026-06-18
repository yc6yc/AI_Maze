"""
main.py — 一键运行入口
-----------------------
用法：
    # 本地模拟（命令行）
    python main.py --mode sim --map maze_15_15.json

    # 批量评测
    python main.py --mode eval --map maze_15_15.json --runs 10
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents.composite_agent import CompositeAgent
from eval.simulator import LocalSimulator
from map_loader import resolve_map_path


def load_config(path: str = "config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def run_sim(map_path: str, cfg: dict, max_rounds: int = 500):
    print(f"\n[SIM] 地图: {map_path}")
    sim = LocalSimulator.from_json(map_path)
    agent = CompositeAgent(config=cfg)
    agent.on_episode_start(sim.ctx)

    while not sim._done and sim._round < max_rounds:
        action = agent.decide(sim.ctx)
        sim._step(action)

    agent.on_episode_end(sim.ctx)
    stats = sim.stats()
    print(f"[SIM] 结果: {stats}")
    return stats


def run_eval(map_path: str, cfg: dict, runs: int = 5, max_rounds: int = 500):
    from eval.eval_runner import run_batch
    summary = run_batch([map_path], "composite", runs, max_rounds, cfg)
    print("\n[EVAL] 汇总:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")


def main():
    parser = argparse.ArgumentParser(description="AI Maze 主程序")
    parser.add_argument("--mode",   choices=["sim", "eval"], default="sim")
    parser.add_argument("--map",    default="maze_15_15.json")
    parser.add_argument("--runs",   type=int, default=5)
    parser.add_argument("--rounds", type=int, default=500)
    parser.add_argument("--config", default="config.json")
    args = parser.parse_args()

    cfg = load_config(args.config)
    map_path = resolve_map_path(args.map)

    if args.mode == "sim":
        run_sim(map_path, cfg, args.rounds)
    elif args.mode == "eval":
        run_eval(map_path, cfg, args.runs, args.rounds)


if __name__ == "__main__":
    main()
