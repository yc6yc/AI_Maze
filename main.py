"""
main.py — 一键运行入口
负责人：组长（角色1）
-----------------------
用法：
    # 本地模拟（离线）
    python main.py --mode sim --map maze_15_15.json

    # 对接裁判服务器（真实对局，需补充服务器 URL）
    python main.py --mode online --url http://judge:8080

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


def run_sim(map_path: str, cfg: dict, max_rounds: int = 500, visualize: bool = False, visualize_window: bool = False):
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

    if visualize:
        try:
            from viz.visualizer import render_history
            render_history(sim.ctx.maze, sim.ctx.history, output_path="replay.gif")
        except Exception as e:
            print(f"[VIZ] 可视化失败: {e}")

    if visualize_window:
        try:
            from viz.visualizer import render_history_window
            render_history_window(sim.ctx.maze, sim.ctx.history)
        except Exception as e:
            print(f"[VIZ] 窗口可视化失败: {e}")

    return stats


def run_eval(map_path: str, cfg: dict, runs: int = 5, max_rounds: int = 500):
    from eval.eval_runner import run_batch
    summary = run_batch([map_path], "composite", runs, max_rounds, cfg)
    print("\n[EVAL] 汇总:")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")


def run_online(url: str, cfg: dict):
    """
    TODO: 对接裁判服务器（WebSocket / HTTP 轮询）
    流程：
      1. 连接服务器，接收初始 JSON
      2. 解析为 GameContext（core.api_adapter.parse_initial_packet）
      3. 每回合调用 agent.decide(ctx)，发送 action_to_json(action)
      4. 接收回合反馈，调用 apply_round_feedback(ctx, feedback)
    """
    print(f"[ONLINE] 连接服务器: {url}")
    print("[ONLINE] TODO: 实现 WebSocket/HTTP 轮询客户端")


def main():
    parser = argparse.ArgumentParser(description="AI Maze 主程序")
    parser.add_argument("--mode",      choices=["sim", "eval", "online"], default="sim")
    parser.add_argument("--map",       default="maze_15_15.json")
    parser.add_argument("--runs",      type=int, default=5)
    parser.add_argument("--rounds",    type=int, default=500)
    parser.add_argument("--config",    default="config.json")
    parser.add_argument("--url",       default="http://localhost:8080")
    parser.add_argument("--visualize", action="store_true", help="生成 replay.gif 动图")
    parser.add_argument("--visualize-window", action="store_true", help="弹出交互式可视化窗口")
    args = parser.parse_args()

    cfg = load_config(args.config)
    map_path = resolve_map_path(args.map)

    if args.mode == "sim":
        run_sim(map_path, cfg, args.rounds, args.visualize, args.visualize_window)
    elif args.mode == "eval":
        run_eval(map_path, cfg, args.runs, args.rounds)
    elif args.mode == "online":
        run_online(args.url, cfg)


if __name__ == "__main__":
    main()
