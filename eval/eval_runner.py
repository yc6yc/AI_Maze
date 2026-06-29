from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.composite_agent import make_agent
from core.map_loader import list_maps
from eval.simulator import LocalSimulator


AGENT_REGISTRY = {
    "hybrid": lambda config: make_agent("hybrid", config),
    "local": lambda config: make_agent("local", config),
    "planner": lambda config: make_agent("planner", config),
    "global_greedy": lambda config: make_agent("global_greedy", config),
    "ai_global_greedy": lambda config: make_agent("ai_global_greedy", config),
    "ai_global_planner": lambda config: make_agent("ai_global_planner", config),
    "fog_original": lambda config: make_agent("fog_original", config),
    "b_enhanced": lambda config: make_agent("b_enhanced", config),
}


@dataclass
class EvalCase:
    map_name: str
    agent_name: str


def run_eval(
    *,
    maps: list[str] | None = None,
    agents: list[str] | None = None,
    config: dict[str, Any] | None = None,
    max_rounds: int | None = None,
) -> dict[str, Any]:
    config = config or {}
    selected_maps = maps or list_maps()
    selected_agents = agents or ["hybrid", "fog_original", "b_enhanced", "local", "planner", "global_greedy"]
    sim_cfg = config.get("sim", {})
    results: list[dict[str, Any]] = []

    for map_name in selected_maps:
        for agent_name in selected_agents:
            if agent_name not in AGENT_REGISTRY:
                results.append({"map": map_name, "agent": agent_name, "error": "unknown agent"})
                continue
            try:
                sim = LocalSimulator.from_json(
                    map_name,
                    max_steps=max_rounds or int(sim_cfg.get("max_steps", 500)),
                    coin_value=int(sim_cfg.get("coin_value", 50)),
                    trap_damage=int(sim_cfg.get("trap_damage", 30)),
                    view_radius=int(sim_cfg.get("view_radius", 1)),
                )
                agent = AGENT_REGISTRY[agent_name](config)
                summary = sim.run(agent, max_rounds)
                results.append({"map": Path(map_name).name, "agent": agent_name, **summary})
            except Exception as exc:  # pragma: no cover - returned to API/CLI for visibility
                results.append({"map": map_name, "agent": agent_name, "error": str(exc)})

    valid_scores = [item["score"] for item in results if "score" in item]
    return {
        "results": results,
        "average_score": sum(valid_scores) / len(valid_scores) if valid_scores else 0,
        "count": len(results),
    }
