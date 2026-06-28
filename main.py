from __future__ import annotations

import argparse
import json
from pathlib import Path

from agents.composite_agent import make_agent
from eval.simulator import LocalSimulator


PROJECT_ROOT = Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Maze simulation")
    parser.add_argument("--map", default="sample", help="Map name or path")
    parser.add_argument("--agent", default="hybrid", help="hybrid, local, planner, global_greedy")
    parser.add_argument("--config", default=str(PROJECT_ROOT / "config.json"), help="Config JSON path")
    parser.add_argument("--max-steps", type=int, default=None, help="Override max simulation steps")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    sim_cfg = config.get("sim", {})
    max_steps = args.max_steps or int(sim_cfg.get("max_steps", 500))
    sim = LocalSimulator.from_json(
        args.map,
        max_steps=max_steps,
        coin_value=int(sim_cfg.get("coin_value", 50)),
        trap_damage=int(sim_cfg.get("trap_damage", 30)),
        view_radius=int(sim_cfg.get("view_radius", 1)),
    )
    agent = make_agent(args.agent, config)
    summary = sim.run(agent, max_steps)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
