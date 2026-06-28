from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers import config, eval, maps, sim


PROJECT_ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="AI Maze", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(maps.router, prefix="/api/maps", tags=["maps"])
app.include_router(sim.router, prefix="/api/sim", tags=["simulation"])
app.include_router(eval.router, prefix="/api/eval", tags=["evaluation"])
app.include_router(config.router, prefix="/api/config", tags=["config"])

frontend_dir = PROJECT_ROOT / "frontend"
web_dir = PROJECT_ROOT / "web"
map_dir = PROJECT_ROOT / "map"
resources_dir = PROJECT_ROOT / "resources"
if (frontend_dir / "static").exists():
    app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")
if map_dir.exists():
    app.mount("/map", StaticFiles(directory=map_dir), name="map")
if resources_dir.exists():
    app.mount("/resources", StaticFiles(directory=resources_dir), name="resources")


@app.get("/")
def root() -> FileResponse:
    return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
