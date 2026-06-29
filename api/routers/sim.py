from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.composite_agent import make_agent
from api.routers.config import deep_merge, load_config
from core.map_loader import load_json
from eval.simulator import LocalSimulator


router = APIRouter()

ENSEMBLE_AGENT = "ensemble"
ENSEMBLE_CANDIDATE_AGENTS = [
    "hybrid",
    "fog_original",
    "b_enhanced",
    "local",
    "planner",
    "global_greedy",
    "ai_global_planner",
    "ai_global_greedy",
]

AGENT_REGISTRY = {
    "hybrid", "local", "planner",
    "global_greedy", "direct_global",
    "ai_global_greedy", "ai_global_planner",
    "fog_original", "b_enhanced", ENSEMBLE_AGENT,
}
_sessions: dict[str, dict] = {}


class StartRequest(BaseModel):
    map: str = "sample"
    agent: str = "hybrid"
    config: dict | None = None
    boss_source: str | None = None
    boss_healths_revealed: bool = False


class RunRequest(BaseModel):
    max_rounds: int | None = Field(default=None, ge=1)


class StartRunRequest(StartRequest):
    max_rounds: int | None = Field(default=None, ge=1)


class SubmitBossHealthRequest(BaseModel):
    boss_health: int
    boss_healths_revealed: bool = False


def _boss_source(payload: StartRequest, *, map_has_boss_array: bool) -> str:
    source = (payload.boss_source or "auto").lower()
    if source not in {"auto", "map", "manual"}:
        raise ValueError("boss_source must be auto, map, or manual")
    if source == "auto":
        return "map" if map_has_boss_array else "manual"
    return source


def _load_sim_inputs(payload: StartRequest) -> tuple[dict, dict, str]:
    config = deep_merge(load_config(), payload.config or {})
    try:
        data = load_json(payload.map)
        map_has_boss_array = isinstance(data.get("B"), list) and len(data.get("B", [])) > 0
        boss_source = _boss_source(payload, map_has_boss_array=map_has_boss_array)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return config, data, boss_source


def _create_sim(data: dict, config: dict, boss_source: str, payload: StartRequest) -> LocalSimulator:
    sim_cfg = config.get("sim", {})
    return LocalSimulator(
        data,
        max_steps=int(sim_cfg.get("max_steps", 500)),
        coin_value=int(sim_cfg.get("coin_value", 50)),
        trap_damage=int(sim_cfg.get("trap_damage", 30)),
        view_radius=int(sim_cfg.get("view_radius", 1)),
        boss_healths=[] if boss_source == "manual" else None,
        boss_source=boss_source,
        boss_healths_revealed=payload.boss_healths_revealed,
    )


def _create_sim_session(payload: StartRequest) -> tuple[str, LocalSimulator, object]:
    if payload.agent not in AGENT_REGISTRY:
        raise HTTPException(status_code=400, detail=f"unknown agent: {payload.agent}")
    if payload.agent == ENSEMBLE_AGENT:
        raise HTTPException(status_code=400, detail="Ensemble Algorithm can only be used with compute-and-play")
    config, data, boss_source = _load_sim_inputs(payload)
    try:
        sim = _create_sim(data, config, boss_source, payload)
        agent = make_agent(payload.agent, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sid = uuid4().hex
    _sessions[sid] = {"sim": sim, "agent": agent}
    return sid, sim, agent


def _ensemble_rank(summary: dict) -> tuple[float, int, int, int]:
    score = float(summary.get("score") or 0)
    won = 1 if summary.get("result") == "win" else 0
    value = int(summary.get("total_value") or summary.get("value") or 0)
    steps = int(summary.get("total_steps") or summary.get("step") or 0)
    return (score, won, value, -steps)


def _run_ensemble(payload: StartRunRequest) -> dict:
    config, data, boss_source = _load_sim_inputs(payload)
    candidates: list[dict] = []
    best: tuple[str, LocalSimulator, object, dict] | None = None

    for agent_name in ENSEMBLE_CANDIDATE_AGENTS:
        try:
            sim = _create_sim(data, config, boss_source, payload)
            agent = make_agent(agent_name, config)
            summary = sim.run(agent, payload.max_rounds)
            candidate = {
                "agent": agent_name,
                "result": summary.get("result"),
                "score": summary.get("score", 0),
                "total_value": summary.get("total_value", summary.get("value", 0)),
                "total_steps": summary.get("total_steps", summary.get("step", 0)),
            }
            candidates.append(candidate)
            if best is None or _ensemble_rank(summary) > _ensemble_rank(best[3]):
                best = (agent_name, sim, agent, summary)
        except Exception as exc:  # pragma: no cover - surfaced to the UI as candidate diagnostics
            candidates.append({"agent": agent_name, "error": str(exc)})

    if best is None:
        raise HTTPException(status_code=400, detail="all ensemble candidate algorithms failed")

    best_agent_name, best_sim, best_agent, best_summary = best
    candidates.sort(
        key=lambda item: (
            0 if item.get("error") else 1,
            float(item.get("score") or 0),
            1 if item.get("result") == "win" else 0,
            int(item.get("total_value") or 0),
            -int(item.get("total_steps") or 0),
        ),
        reverse=True,
    )
    ensemble_result = {
        "selected_agent": best_agent_name,
        "selected_score": best_summary.get("score", 0),
        "selected_result": best_summary.get("result"),
        "selected_total_value": best_summary.get("total_value", best_summary.get("value", 0)),
        "selected_total_steps": best_summary.get("total_steps", best_summary.get("step", 0)),
        "candidates": candidates,
    }
    state = best_sim.snapshot()
    state["ensemble_result"] = ensemble_result
    summary = {**best_summary, "ensemble": ensemble_result}

    sid = uuid4().hex
    _sessions[sid] = {"sim": best_sim, "agent": best_agent, "ensemble": ensemble_result}
    return {"session_id": sid, "state": state, "summary": summary}


@router.post("/start")
def start_sim(payload: StartRequest) -> dict:
    sid, sim, _agent = _create_sim_session(payload)
    return {"session_id": sid, "state": sim.snapshot()}


@router.post("/start-run")
def start_and_run_sim(payload: StartRunRequest) -> dict:
    if payload.agent == ENSEMBLE_AGENT:
        return _run_ensemble(payload)
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


@router.post("/{sid}/bosses/input")
def submit_manual_boss_health(sid: str, payload: SubmitBossHealthRequest) -> dict:
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    sim: LocalSimulator = session["sim"]
    try:
        if payload.boss_health == -1:
            state = sim.finish_manual_boss_input()
        else:
            state = sim.submit_manual_boss_health(
                payload.boss_health,
                reveal_all=payload.boss_healths_revealed,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_id": sid, "state": state, "summary": sim.summary()}


@router.post("/{sid}/bosses/replan")
def replan_manual_boss_sequence(sid: str) -> dict:
    session = _sessions.get(sid)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    sim: LocalSimulator = session["sim"]
    try:
        state = sim.replan_manual_boss_sequence()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session_id": sid, "state": state, "summary": sim.summary()}


@router.delete("/{sid}")
def delete_sim(sid: str) -> dict[str, str]:
    if sid in _sessions:
        del _sessions[sid]
    return {"message": "deleted"}
