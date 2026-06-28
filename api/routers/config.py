from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.json"

router = APIRouter()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_config(config: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@router.get("")
def get_config() -> dict[str, Any]:
    return load_config()


@router.put("")
def set_config(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="config payload must be an object")
    config = deep_merge(load_config(), payload)
    write_config(config)
    return config
