from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.routers.config import deep_merge, load_config
from eval.eval_runner import run_eval


router = APIRouter()


class EvalRequest(BaseModel):
    maps: list[str] | None = None
    agents: list[str] | None = None
    max_rounds: int | None = Field(default=None, ge=1)
    config: dict | None = None


@router.post("/run")
def run_eval_api(payload: EvalRequest) -> dict:
    config = deep_merge(load_config(), payload.config or {})
    try:
        return run_eval(maps=payload.maps, agents=payload.agents, config=config, max_rounds=payload.max_rounds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
