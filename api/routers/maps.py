from __future__ import annotations

from copy import deepcopy
import json

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from core.map_loader import MapValidationError, list_maps, load_json, save_map, validate_map_data


router = APIRouter()


@router.get("")
def get_maps(response: Response) -> dict[str, list[str]]:
    response.headers["Cache-Control"] = "no-store"
    return {"maps": list_maps()}


@router.get("/{map_name}")
def get_map(map_name: str, response: Response) -> dict:
    try:
        data = load_json(map_name)
        response.headers["Cache-Control"] = "no-store"
        public_data = deepcopy(data)
        boss_healths = data.get("B")
        public_data["boss_healths_available"] = isinstance(boss_healths, list) and len(boss_healths) > 0
        if public_data["boss_healths_available"]:
            public_data["B"] = [None]
            public_data["boss_healths_hidden"] = True
        return public_data
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except MapValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/upload")
async def upload_map(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        raw = await file.read()
        data = json.loads(raw.decode("utf-8"))
        validate_map_data(data)
        filename = file.filename or "uploaded.json"
        path = save_map(filename, data)
        return {"name": path.name, "message": "uploaded"}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON") from exc
    except (UnicodeDecodeError, MapValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
