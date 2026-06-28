from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.composite_agent import make_agent
from api.routers.config import deep_merge, load_config
from core.map_loader import load_json
from eval.simulator import LocalSimulator


router = APIRouter()

AGENT_REGISTRY = {
    "hybrid", "local", "local_3x3", "planner",
    "global_greedy", "direct_global",
    "ai_global_greedy", "ai_global_planner", "ai_composite",
    "fog_original", "b_enhanced",
}
_sessions: dict[str, dict] = {}


class StartRequest(BaseModel):
    map: str = "sample"
    agent: str = "hybrid"
    config: dict | None = None
    boss_source: str | None = None
    boss_count: int | None = Field(default=None, ge=0)
    boss_healths: list[int] | None = None
    boss_healths_revealed: bool = False


class RunRequest(BaseModel):
    max_rounds: int | None = Field(default=None, ge=1)


class StartRunRequest(StartRequest):
    max_rounds: int | None = Field(default=None, ge=1)


class AppendBossRequest(BaseModel):
    boss_healths: list[int]
    boss_healths_revealed: bool = False


def _boss_source(payload: StartRequest, *, map_has_boss_array: bool) -> str:
    source = (payload.boss_source or "auto").lower()
    if source not in {"auto", "map", "manual"}:
        raise ValueError("boss_source must be auto, map, or manual")
    if source == "auto":
        return "map" if map_has_boss_array else "manual"
    return source


def _manual_boss_healths(payload: StartRequest, *, boss_source: str) -> list[int] | None:
    if boss_source != "manual":
        return None
    if payload.boss_healths is None:
        raise ValueError("boss_healths must be provided when boss_source is manual")
    healths = [int(value) for value in payload.boss_healths]
    if payload.boss_count is not None and payload.boss_count != len(healths):
        raise ValueError("boss_count must match boss_healths length")
    if not healths:
        raise ValueError("boss_healths must not be empty when boss_source is manual")
    if any(value <= 0 for value in healths):
        raise ValueError("all boss_healths must be greater than 0")
    return healths


def _create_sim_session(payload: StartRequest) -> tuple[str, LocalSimulator, object]:
    if payload.agent not in AGENT_REGISTRY:
        raise HTTPException(status_code=400, detail=f"unknown agent: {payload.agent}")
    config = deep_merge(load_config(), payload.config or {})
    try:
        data = load_json(payload.map)
        map_has_boss_array = isinstance(data.get("B"), list) and len(data.get("B", [])) > 0
        boss_source = _boss_source(payload, map_has_boss_array=map_has_boss_array)
        manual_boss_healths = _manual_boss_healths(payload, boss_source=boss_source)
        sim_cfg = config.get("sim", {})
        sim = LocalSimulator(
            data,
            max_steps=int(sim_cfg.get("max_steps", 500)),
            coin_value=int(sim_cfg.get("coin_value", 50)),
            trap_damage=int(sim_cfg.get("trap_damage", 30)),
            view_radius=int(sim_cfg.get("view_radius", 1)),
            boss_healths=manual_boss_healths,
            boss_source=boss_source,
            boss_healths_revealed=payload.boss_healths_revealed,
        )
        agent = make_agent(payload.agent, config)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sid = uuid4().hex
    _sessions[sid] = {"sim": sim, "agent": agent}
    return sid, sim, agent


@router.post("/start")
def start_sim(payload: StartRequest) -> dict:
    sid, sim, _agent = _create_sim_session(payload)
    return {"session_id": sid, "state": sim.snapshot()}


@router.post("/start-run")
def start_and_run_sim(payload: StartRunRequest) -> dict:
    sid, sim, agent = _create_sim_session(payload)
    summary = sim.run(agent, payload.max_rounds)
    return {"session_id": sid, "state": sim.snapshot(), "summary": summary}


@router.post("/{sid}/step")
def step_sim(sid: str) -> dict:
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    sim: LocalSimulator = session["sim"]
    agent = session["agent"]
    action = agent.decide(sim.ctx)
    state = sim.step(action)
    return {"session_id": sid, "action": {"move": action.move, "use_skill": action.use_skill}, "state": state}


@router.post("/{sid}/run")
def run_sim(sid: str, payload: RunRequest | None = None) -> dict:
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    sim: LocalSimulator = session["sim"]
    agent = session["agent"]
    summary = sim.run(agent, payload.max_rounds if payload else None)
    return {"session_id": sid, "state": sim.snapshot(), "summary": summary}


@router.post("/{sid}/bosses/append")
def append_manual_bosses(sid: str, payload: AppendBossRequest) -> dict:
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    sim: LocalSimulator = session["sim"]
    try:
        state = sim.append_manual_bosses(payload.boss_healths, reveal_all=payload.boss_healths_revealed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_id": sid, "state": state, "summary": sim.summary()}


@router.delete("/{sid}")
def delete_sim(sid: str) -> dict[str, str]:
    if sid in _sessions:
        del _sessions[sid]
    return {"message": "deleted"}
