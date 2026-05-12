"""
eval_runner.py — 批量评测脚本
负责人：角色4（评测）
--------------------------------------------------
批量跑多个迷宫 JSON，输出均值/方差表格。

用法：
    python -m eval.eval_runner --maps maze_15_15.json --runs 10
    python -m eval.eval_runner --maps maps/*.json --runs 5 --agent composite
"""

from __future__ import annotations
import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Any

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.simulator import LocalSimulator
from agents.composite_agent import CompositeAgent
from agents.local_greedy_policy import LocalGreedyAgent
from agents.global_planner import GlobalPlannerAgent


AGENT_REGISTRY = {
    "composite": lambda cfg: CompositeAgent(config=cfg),
    "greedy":    lambda cfg: LocalGreedyAgent(config=cfg.get("local", {})),
    "global":    lambda cfg: GlobalPlannerAgent(config=cfg.get("global", {})),
}


def run_single(map_path: str, agent_name: str, cfg: dict, max_rounds: int) -> Dict[str, Any]:
    sim = LocalSimulator.from_json(map_path)
    agent = AGENT_REGISTRY[agent_name](cfg)
    result = sim.run(agent, max_rounds=max_rounds)
    result["map"] = map_path
    return result


def run_batch(
    map_paths: List[str],
    agent_name: str = "composite",
    runs: int = 5,
    max_rounds: int = 500,
    cfg: dict = None,
) -> Dict[str, Any]:
    cfg = cfg or {}
    all_results: List[Dict[str, Any]] = []

    for mp in map_paths:
        for _ in range(runs):
            r = run_single(mp, agent_name, cfg, max_rounds)
            all_results.append(r)
            print(f"  [{mp}] won={r['won']} rounds={r['rounds']} coins={r['coins']}")

    coins_list    = [r["coins"] for r in all_results]
    rounds_list   = [r["rounds"] for r in all_results]
    win_rate      = sum(r["won"] for r in all_results) / len(all_results)

    summary = {
        "agent": agent_name,
        "total_runs": len(all_results),
        "win_rate": win_rate,
        "coins_mean": statistics.mean(coins_list),
        "coins_stdev": statistics.stdev(coins_list) if len(coins_list) > 1 else 0,
        "rounds_mean": statistics.mean(rounds_list),
        "rounds_stdev": statistics.stdev(rounds_list) if len(rounds_list) > 1 else 0,
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="AI Maze 批量评测")
    parser.add_argument("--maps",   nargs="+", required=True, help="迷宫 JSON 文件路径（支持 glob）")
    parser.add_argument("--runs",   type=int,  default=5,    help="每张地图重复次数")
    parser.add_argument("--agent",  default="composite",     help="agent 名称: composite/greedy/global")
    parser.add_argument("--rounds", type=int,  default=500,  help="最大回合数上限")
    parser.add_argument("--config", default=None,            help="config.json 路径（可选）")
    args = parser.parse_args()

    cfg = {}
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    # 展开 glob
    map_paths: List[str] = []
    for pattern in args.maps:
        expanded = list(Path(".").glob(pattern))
        map_paths.extend(str(p) for p in expanded) if expanded else map_paths.append(pattern)

    print(f"\n{'='*50}")
    print(f"评测 Agent: {args.agent}  地图数: {len(map_paths)}  每图次数: {args.runs}")
    print(f"{'='*50}")

    summary = run_batch(map_paths, args.agent, args.runs, args.rounds, cfg)

    print(f"\n{'='*50}  汇总  {'='*50}")
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")


if __name__ == "__main__":
    main()
