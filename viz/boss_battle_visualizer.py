"""
boss_battle_visualizer.py — 独立的 BOSS 战可视化窗口
----------------------------------------------------
不修改现有迷宫可视化逻辑，单独打开一个窗口展示玩家与 BOSS 的战斗过程。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    import matplotlib.image as mpimg
    import numpy as np
    import matplotlib.patches as patches
    import matplotlib.patheffects as patheffects
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.widgets import Button
    HAS_MPL = True
    plt = None
except ImportError:
    HAS_MPL = False
    patheffects = None
    plt = None

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

from agents.combat_agent import CombatAgent
from core.state import GameContext, MazeState, PlayerState, Skill

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
PLAYER_FILE = ASSETS_DIR / "player.png"
BOSS_FILE = ASSETS_DIR / "boss.png"
DEMON_SLIME_DIR = ASSETS_DIR / "demon_slime"
DEMON_IDLE_FILE = DEMON_SLIME_DIR / "demon_idle.gif"
DEMON_CLEAVE_FILE = DEMON_SLIME_DIR / "demon_cleave.gif"
DEMON_HIT_FILE = DEMON_SLIME_DIR / "demon_take_hit.gif"
DEMON_DEATH_FILE = DEMON_SLIME_DIR / "demon_death.gif"
_ASSET_CACHE: Dict[str, Any] = {}
_INTERACTIVE_BACKENDS = ["TkAgg", "Qt5Agg", "QtAgg", "WXAgg", "MacOSX"]
DEFAULT_BOSS_BATTLE_FPS = 8


@dataclass
class BossBattleFrame:
    boss_index: int
    boss_total: int
    attempt: int
    attack_round: int
    total_round: int
    skill_idx: Optional[int]
    damage: int
    coins: int
    boss_hp: int
    boss_hp_max: int
    defeated: bool
    retry: bool
    failed: bool
    skills: List[Dict[str, int]]
    phase: str = "idle"
    motion_t: float = 0.0
    hit_flash: float = 0.0
    shake: float = 0.0
    impact_text: Optional[str] = None
    duration_ms: int = 120

    def title(self) -> str:
        return (
            f"BOSS {self.boss_index}/{self.boss_total} | "
            f"Attempt {self.attempt} | Turn {self.attack_round} | "
            f"Total {self.total_round}"
        )


def _load_pyplot(interactive: bool = False):
    global plt
    if plt is not None:
        return
    if not HAS_MPL:
        return
    if interactive:
        for backend in _INTERACTIVE_BACKENDS:
            try:
                matplotlib.use(backend, force=True)
                break
            except Exception:
                continue
    else:
        try:
            matplotlib.use("Agg", force=True)
        except Exception:
            pass
    import matplotlib.pyplot as _plt
    plt = _plt


def _load_asset(name: str, path: Path):
    if not HAS_MPL:
        return None
    if name in _ASSET_CACHE:
        return _ASSET_CACHE[name]
    if not path.exists():
        _ASSET_CACHE[name] = None
        return None
    try:
        _ASSET_CACHE[name] = mpimg.imread(path)
    except Exception:
        _ASSET_CACHE[name] = None
    return _ASSET_CACHE[name]


def _load_gif_frames(name: str, path: Path) -> List[Any]:
    if not HAS_MPL or not HAS_PIL:
        return []
    cache_key = f"gif::{name}"
    if cache_key in _ASSET_CACHE:
        return _ASSET_CACHE[cache_key]
    if not path.exists():
        _ASSET_CACHE[cache_key] = []
        return []
    try:
        frames: List[Any] = []
        with Image.open(path) as img:
            for idx in range(getattr(img, "n_frames", 1)):
                img.seek(idx)
                frame = img.convert("RGBA")
                frames.append(np.array(frame))
        _ASSET_CACHE[cache_key] = frames
    except Exception:
        _ASSET_CACHE[cache_key] = []
    return _ASSET_CACHE[cache_key]


def _remove_background_from_gif(src: Path, dst: Path):
    if not HAS_PIL:
        raise RuntimeError("Pillow unavailable")

    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        frames = []
        durations = []
        for idx in range(getattr(img, "n_frames", 1)):
            img.seek(idx)
            rgba = img.convert("RGBA")
            px = rgba.load()
            width, height = rgba.size
            bg = px[0, 0]
            for y in range(height):
                for x in range(width):
                    r, g, b, a = px[x, y]
                    if abs(r - bg[0]) <= 12 and abs(g - bg[1]) <= 12 and abs(b - bg[2]) <= 12:
                        px[x, y] = (r, g, b, 0)
            frames.append(rgba.copy())
            durations.append(img.info.get("duration", 80))
        frames[0].save(
            dst,
            save_all=True,
            append_images=frames[1:],
            loop=0,
            disposal=2,
            duration=durations,
            transparency=0,
        )


def ensure_boss_assets_ready():
    if not HAS_PIL:
        return
    if not DEMON_SLIME_DIR.exists():
        return
    for src in (DEMON_IDLE_FILE, DEMON_CLEAVE_FILE, DEMON_HIT_FILE, DEMON_DEATH_FILE):
        cleaned = src.with_name(f"{src.stem}_clean.gif")
        if not src.exists():
            continue
        if not cleaned.exists() or cleaned.stat().st_mtime < src.stat().st_mtime:
            try:
                _remove_background_from_gif(src, cleaned)
            except Exception:
                continue


def _select_boss_sprite(frame: BossBattleFrame):
    ensure_boss_assets_ready()
    idle_clean = DEMON_IDLE_FILE.with_name("demon_idle_clean.gif")
    cleave_clean = DEMON_CLEAVE_FILE.with_name("demon_cleave_clean.gif")
    hit_clean = DEMON_HIT_FILE.with_name("demon_take_hit_clean.gif")
    death_clean = DEMON_DEATH_FILE.with_name("demon_death_clean.gif")
    if frame.defeated:
        frames = _load_gif_frames("demon_death", death_clean if death_clean.exists() else DEMON_DEATH_FILE)
        if frames:
            return frames[min(int(frame.motion_t * len(frames)), len(frames) - 1)]
    if frame.hit_flash > 0:
        frames = _load_gif_frames("demon_hit", hit_clean if hit_clean.exists() else DEMON_HIT_FILE)
        if frames:
            return frames[min(int(frame.motion_t * len(frames)), len(frames) - 1)]
    if frame.phase == "attack" and frame.damage > 0:
        frames = _load_gif_frames("demon_cleave", cleave_clean if cleave_clean.exists() else DEMON_CLEAVE_FILE)
        if frames:
            return frames[min(int(frame.motion_t * len(frames)), len(frames) - 1)]
    idle_frames = _load_gif_frames("demon_idle", idle_clean if idle_clean.exists() else DEMON_IDLE_FILE)
    if idle_frames:
        return idle_frames[int(frame.total_round) % len(idle_frames)]
    return _clean_static_boss_sprite()


def _clean_static_boss_sprite():
    sprite = _load_asset("boss_window_boss", BOSS_FILE)
    if sprite is None or not HAS_MPL:
        return sprite
    arr = sprite.astype(np.float32).copy()
    if arr.shape[-1] < 4:
        return arr
    rgb = arr[..., :3]
    mask = (rgb[..., 0] < 0.25) & (rgb[..., 1] < 0.10) & (rgb[..., 2] < 0.20)
    arr[..., 3] = np.where(mask, 0.0, arr[..., 3])
    return arr


def _snapshot_skills(ctx: GameContext) -> List[Dict[str, int]]:
    return [
        {
            "damage": sk.damage,
            "cooldown": sk.cooldown,
            "remaining_cd": sk.remaining_cd,
        }
        for sk in ctx.player.skills
    ]


def simulate_boss_battle_frames(ctx: GameContext, boss_hps: List[int]) -> List[BossBattleFrame]:
    """
    只基于 CombatAgent 和当前上下文，离线生成 BOSS 战过程帧。
    不修改外部传入的 ctx。
    """
    from copy import deepcopy

    sim_ctx = deepcopy(ctx)
    agent = CombatAgent(enable_memory=True)
    frames: List[BossBattleFrame] = []
    total_round = 0

    for boss_index, boss_hp_max in enumerate(boss_hps, start=1):
        boss_hp = boss_hp_max
        attempt = 0

        while boss_hp > 0:
            attempt += 1
            for attack_round in range(1, sim_ctx.min_rounds + 1):
                total_round += 1
                action = agent.decide_combat_with_memory(sim_ctx)
                damage = 0
                if action.use_skill is not None:
                    damage = sim_ctx.player.use_skill(action.use_skill)
                    boss_hp = max(boss_hp - damage, 0)

                defeated = boss_hp <= 0
                sim_ctx.player.tick_cooldowns()
                timeline = [
                    ("windup", 0.05, 56, 0.0, 0.0, None),
                    ("attack", 0.22, 50, 0.0, 0.0, None),
                    ("lunge", 0.38, 44, 0.0, 0.0, None),
                    ("impact", 0.52, 68, 1.0 if damage > 0 else 0.0, 1.0 if damage > 0 else 0.0, f"-{damage}" if damage > 0 else None),
                    ("recover", 0.74, 58, 0.0, 0.25 if damage > 0 else 0.0, None),
                    ("idle", 0.96, 72, 0.0, 0.0, None),
                ]
                for phase, motion_t, duration_ms, hit_flash, shake, impact_text in timeline:
                    frames.append(
                        BossBattleFrame(
                            boss_index=boss_index,
                            boss_total=len(boss_hps),
                            attempt=attempt,
                            attack_round=attack_round,
                            total_round=total_round,
                            skill_idx=action.use_skill,
                            damage=damage,
                            coins=sim_ctx.player.coins,
                            boss_hp=boss_hp,
                            boss_hp_max=boss_hp_max,
                            defeated=defeated,
                            retry=False,
                            failed=False,
                            skills=_snapshot_skills(sim_ctx),
                            phase=phase if damage > 0 else "idle",
                            motion_t=motion_t,
                            hit_flash=hit_flash,
                            shake=shake,
                            impact_text=impact_text,
                            duration_ms=duration_ms,
                        )
                    )

                if defeated:
                    sim_ctx.boss_defeated.append(boss_hp_max)
                    agent.mark_boss_defeated(sim_ctx)
                    break

            if boss_hp <= 0:
                break

            sim_ctx.player.coins -= sim_ctx.coin_consumption
            failed = sim_ctx.player.coins <= 0
            frames.append(
                BossBattleFrame(
                    boss_index=boss_index,
                    boss_total=len(boss_hps),
                    attempt=attempt,
                    attack_round=sim_ctx.min_rounds,
                    total_round=total_round,
                    skill_idx=None,
                    damage=0,
                    coins=max(sim_ctx.player.coins, 0),
                    boss_hp=boss_hp,
                    boss_hp_max=boss_hp_max,
                    defeated=False,
                    retry=not failed,
                    failed=failed,
                    skills=_snapshot_skills(sim_ctx),
                    phase="retry" if not failed else "failed",
                    motion_t=1.0,
                    duration_ms=160,
                )
            )

            if failed:
                break

        if sim_ctx.player.coins <= 0 and boss_hp > 0:
            break

    return frames


def build_boss_battle_context(
    skill_specs: List[List[int]],
    min_rounds: int,
    coin_consumption: int,
    current_coins: int,
) -> GameContext:
    maze = MazeState.from_full_map(
        [
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ]
    )
    player = PlayerState(
        pos=(1, 1),
        coins=current_coins,
        skills=[Skill.from_list(spec) for spec in skill_specs],
    )
    return GameContext(
        maze=maze,
        player=player,
        coin_consumption=coin_consumption,
        min_rounds=min_rounds,
    )


def battle_result_from_frames(frames: List[BossBattleFrame], boss_count: int) -> int:
    if boss_count <= 0:
        return 1
    if not frames:
        return 0
    last = frames[-1]
    return 1 if last.defeated and last.boss_index == boss_count and not last.failed else 0


def make_visual_boss_battle_handler(
    skill_specs: List[List[int]],
    boss_hps: List[int],
    min_rounds: int,
    coin_consumption: int,
    fps: int = DEFAULT_BOSS_BATTLE_FPS,
):
    remaining_boss_hps = list(boss_hps)

    def handler(current_coins: int) -> int:
        if not remaining_boss_hps:
            return 1

        ctx = build_boss_battle_context(
            skill_specs=skill_specs,
            min_rounds=min_rounds,
            coin_consumption=coin_consumption,
            current_coins=current_coins,
        )
        frames = simulate_boss_battle_frames(ctx, remaining_boss_hps)
        render_boss_battle_window(frames, fps=fps)
        result = battle_result_from_frames(frames, len(remaining_boss_hps))
        if result == 1:
            remaining_boss_hps.clear()
        return result

    return handler


def _draw_progress_bar(ax, x: float, y: float, width: float, height: float, ratio: float, fill: str, bg: str):
    ratio = max(0.0, min(1.0, ratio))
    shell = patches.FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.003,rounding_size=0.012",
        facecolor=bg, edgecolor="#475569", linewidth=0.95,
        transform=ax.transAxes, zorder=1,
    )
    ax.add_patch(shell)
    if ratio <= 0:
        return
    fill_width = max(width * ratio - 0.004, 0.0)
    if fill_width > 0:
        fill_patch = patches.FancyBboxPatch(
            (x + 0.002, y + 0.002), fill_width, max(height - 0.004, 0.0),
            boxstyle="round,pad=0.002,rounding_size=0.01",
            facecolor=fill, edgecolor="none",
            transform=ax.transAxes, zorder=2,
        )
        ax.add_patch(fill_patch)
        shine = patches.Rectangle(
            (x + 0.003, y + height * 0.58), fill_width, max(height * 0.16, 0.002),
            facecolor="#ffffff", edgecolor="none", alpha=0.12,
            transform=ax.transAxes, zorder=3,
        )
        ax.add_patch(shine)


def _draw_sprite(ax, sprite, x: float, y: float, width: float, height: float, zorder: int = 5, clip_path=None):
    if sprite is None:
        return False
    artist = ax.imshow(
        sprite,
        extent=(x, x + width, y, y + height),
        interpolation="nearest",
        zorder=zorder,
        aspect="auto",
    )
    if clip_path is not None:
        artist.set_clip_path(clip_path)
    return True


def _flash_sprite(sprite, flash_strength: float):
    if not HAS_MPL or sprite is None or flash_strength <= 0:
        return sprite
    arr = sprite.astype(np.float32).copy()
    arr[..., :3] = arr[..., :3] * (1.0 - flash_strength) + 1.0 * flash_strength
    return np.clip(arr, 0.0, 1.0)


def _phase_energy(frame: BossBattleFrame) -> float:
    if frame.failed:
        return 0.88
    if frame.retry:
        return 0.55
    if frame.defeated:
        return 0.7
    if frame.damage <= 0:
        return 0.12
    return {
        "windup": 0.28,
        "attack": 0.52,
        "lunge": 0.8,
        "impact": 1.0,
        "recover": 0.38,
    }.get(frame.phase, 0.16)


def _add_text_effect(text_obj, outer_width: float, outer_color: str, inner_width: float = 0.0, inner_color: str = "#ffffff"):
    if not HAS_MPL or patheffects is None:
        return
    effects = [patheffects.withStroke(linewidth=outer_width, foreground=outer_color)]
    if inner_width > 0:
        effects.append(patheffects.withStroke(linewidth=inner_width, foreground=inner_color))
    effects.append(patheffects.Normal())
    text_obj.set_path_effects(effects)


def _draw_glow(ax, center, width: float, height: float, color: str, alpha: float, zorder: float, clip_path=None):
    if alpha <= 0:
        return
    for scale, factor in ((1.0, 0.45), (0.72, 0.32), (0.46, 0.2)):
        glow = patches.Ellipse(
            center, width * scale, height * scale,
            facecolor=color, edgecolor="none",
            alpha=alpha * factor, zorder=zorder,
        )
        if clip_path is not None:
            glow.set_clip_path(clip_path)
        ax.add_patch(glow)


def _curve_points(start, control, end, progress: float, steps: int = 36):
    progress = max(0.0, min(1.0, progress))
    if progress <= 0:
        return np.array([start, start], dtype=np.float32)
    count = max(8, int(steps * progress) + 6)
    t = np.linspace(0.0, progress, count)
    omt = 1.0 - t
    return (
        (omt * omt)[:, None] * start
        + (2.0 * omt * t)[:, None] * control
        + (t * t)[:, None] * end
    )


def _draw_trail_band(ax, points, width: float, color: str, alpha: float, zorder: float, clip_path=None):
    if len(points) < 2 or width <= 0 or alpha <= 0:
        return
    tangents = np.gradient(points, axis=0)
    normals = np.stack((-tangents[:, 1], tangents[:, 0]), axis=1)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.maximum(lengths, 1e-6)
    weights = np.sin(np.linspace(0.0, np.pi, len(points))) ** 0.75
    offsets = normals * (width * weights)[:, None]
    band = np.vstack((points + offsets, (points - offsets)[::-1]))
    patch = patches.Polygon(
        band,
        closed=True,
        facecolor=color,
        edgecolor="none",
        alpha=alpha,
        zorder=zorder,
    )
    if clip_path is not None:
        patch.set_clip_path(clip_path)
    ax.add_patch(patch)


def _draw_arena_backdrop(ax, arena, panel, frame: BossBattleFrame):
    heat = _phase_energy(frame)

    x = np.linspace(0.0, 1.0, 720)
    y = np.linspace(0.0, 1.0, 420)
    xx, yy = np.meshgrid(x, y)
    arena_img = np.zeros((420, 720, 4), dtype=np.float32)
    arena_img[..., 0] = 0.035 + 0.08 * (1.0 - yy) + 0.2 * heat * (1.0 - np.abs(xx - 0.7))
    arena_img[..., 1] = 0.055 + 0.075 * (1.0 - yy) + 0.025 * xx
    arena_img[..., 2] = 0.11 + 0.22 * yy + 0.04 * (1.0 - xx)
    arena_img[..., 3] = 1.0
    arena_artist = ax.imshow(arena_img, extent=(0.5, 8.1, 0.9, 6.1), zorder=0.08, aspect="auto")
    arena_artist.set_clip_path(arena)

    panel_img = np.zeros((420, 320, 4), dtype=np.float32)
    panel_img[..., 0] = 0.05 + 0.04 * (1.0 - yy[:, :320])
    panel_img[..., 1] = 0.085 + 0.03 * xx[:, :320]
    panel_img[..., 2] = 0.14 + 0.09 * yy[:, :320]
    panel_img[..., 3] = 1.0
    panel_artist = ax.imshow(panel_img, extent=(8.45, 11.5, 0.9, 6.1), zorder=0.08, aspect="auto")
    panel_artist.set_clip_path(panel)

    for verts, color, alpha in (
        ([(0.55, 6.1), (1.55, 6.1), (2.6, 2.55), (1.85, 2.55)], "#451018", 0.3),
        ([(6.35, 6.1), (7.9, 6.1), (7.05, 2.2), (6.15, 2.2)], "#3f0f1b", 0.28),
        ([(0.75, 1.2), (3.15, 1.2), (4.2, 0.9), (1.15, 0.9)], "#09111f", 0.72),
    ):
        patch = patches.Polygon(verts, closed=True, facecolor=color, edgecolor="none", alpha=alpha, zorder=0.18)
        patch.set_clip_path(arena)
        ax.add_patch(patch)

    _draw_glow(ax, (6.15, 4.95), 2.55, 2.55, "#f59e0b", 0.28 + heat * 0.12, 0.16, clip_path=arena)
    moon = patches.Circle((6.15, 4.95), 0.58, facecolor="#fde68a", edgecolor="#f8fafc", linewidth=0.6, alpha=0.18, zorder=0.19)
    moon.set_clip_path(arena)
    ax.add_patch(moon)

    for idx, y0 in enumerate((5.55, 5.15, 4.76, 4.36)):
        line, = ax.plot(
            [0.85 + idx * 0.15, 3.0 + idx * 0.2],
            [y0, y0 - 0.08],
            color="#cbd5e1",
            linewidth=max(0.6, 1.5 - idx * 0.22),
            alpha=0.08 + heat * 0.08,
            zorder=0.24,
        )
        line.set_clip_path(arena)
    for idx, y0 in enumerate((5.5, 5.08, 4.68)):
        line, = ax.plot(
            [4.9 + idx * 0.18, 7.55 + idx * 0.12],
            [y0 - 0.02, y0 + 0.04],
            color="#fecdd3",
            linewidth=max(0.7, 1.35 - idx * 0.18),
            alpha=0.08 + heat * 0.1,
            zorder=0.24,
        )
        line.set_clip_path(arena)

    panel_header = patches.FancyBboxPatch(
        (8.7, 5.45), 2.55, 0.4,
        boxstyle="round,pad=0.01,rounding_size=0.08",
        facecolor="#111827", edgecolor="#475569", linewidth=1.0,
        zorder=0.3,
    )
    panel_header.set_clip_path(panel)
    ax.add_patch(panel_header)


def _draw_action_trail(ax, frame: BossBattleFrame, start, end, clip_path=None):
    if frame.skill_idx is None or frame.damage <= 0:
        return
    progress = {
        "attack": 0.42,
        "lunge": 0.82,
        "impact": 1.0,
        "recover": 1.0,
    }.get(frame.phase, 0.0)
    if progress <= 0:
        return

    start_pt = np.array(start, dtype=np.float32)
    end_pt = np.array(end, dtype=np.float32)
    control = np.array(
        (
            start_pt[0] + (end_pt[0] - start_pt[0]) * 0.55,
            max(start_pt[1], end_pt[1]) + 0.95,
        ),
        dtype=np.float32,
    )
    points = _curve_points(start_pt, control, end_pt, progress=progress, steps=44)
    energy = _phase_energy(frame)
    _draw_trail_band(ax, points, 0.38 + energy * 0.08, "#f59e0b", 0.18 + energy * 0.15, 6.0, clip_path=clip_path)
    _draw_trail_band(ax, points, 0.26 + energy * 0.06, "#fb7185", 0.18 + energy * 0.12, 6.08, clip_path=clip_path)
    _draw_trail_band(ax, points, 0.14 + energy * 0.04, "#f8fafc", 0.42 + energy * 0.18, 6.16, clip_path=clip_path)
    core, = ax.plot(
        points[:, 0], points[:, 1],
        color="#fff7ed",
        linewidth=1.2 + energy * 0.85,
        alpha=0.75,
        zorder=6.2,
    )
    core.set_solid_capstyle("round")
    if clip_path is not None:
        core.set_clip_path(clip_path)

    tail_origin = start_pt - np.array((0.1, -0.08), dtype=np.float32)
    for idx, tail_len in enumerate((0.42, 0.62, 0.82)):
        line, = ax.plot(
            [tail_origin[0] - tail_len, tail_origin[0] - tail_len * 0.12],
            [tail_origin[1] - idx * 0.11, tail_origin[1] - idx * 0.03],
            color="#fef3c7",
            linewidth=max(0.8, 1.5 - idx * 0.22),
            alpha=0.18 + 0.12 * energy,
            zorder=5.8,
        )
        if clip_path is not None:
            line.set_clip_path(clip_path)


def _draw_impact_burst(ax, frame: BossBattleFrame, center, clip_path=None):
    if frame.damage <= 0 or frame.phase not in {"lunge", "impact", "recover"}:
        return
    strength = {"lunge": 0.42, "impact": 1.0, "recover": 0.46}[frame.phase]
    outer = patches.Circle(
        center, 0.24 + strength * 0.18,
        fill=False, edgecolor="#fde68a",
        linewidth=1.0 + strength * 1.8, alpha=0.32 + strength * 0.18,
        zorder=7.0,
    )
    inner = patches.Circle(
        center, 0.11 + strength * 0.1,
        facecolor="#fde68a", edgecolor="#fff7ed",
        linewidth=0.8, alpha=0.28 + strength * 0.18,
        zorder=7.1,
    )
    for patch in (outer, inner):
        if clip_path is not None:
            patch.set_clip_path(clip_path)
        ax.add_patch(patch)

    for idx in range(12):
        angle = -0.95 + idx * 0.3
        inner_r = 0.06 + 0.03 * (idx % 3)
        outer_r = 0.24 + strength * (0.18 + 0.04 * (idx % 2))
        x0 = center[0] + math.cos(angle) * inner_r
        y0 = center[1] + math.sin(angle) * inner_r
        x1 = center[0] + math.cos(angle) * outer_r
        y1 = center[1] + math.sin(angle) * outer_r
        line, = ax.plot(
            [x0, x1], [y0, y1],
            color="#fca5a5" if idx % 4 == 0 else "#fef08a",
            linewidth=0.95 + strength * (1.3 if idx % 4 == 0 else 0.9),
            alpha=0.34 + strength * 0.22,
            zorder=7.2,
        )
        line.set_solid_capstyle("round")
        if clip_path is not None:
            line.set_clip_path(clip_path)


def _draw_status_banner(ax, frame: BossBattleFrame):
    if frame.failed:
        label, face, edge, text_color = "DEFEAT", "#450a0a", "#ef4444", "#fee2e2"
    elif frame.retry:
        label, face, edge, text_color = "RETRY", "#431407", "#f59e0b", "#fef3c7"
    elif frame.defeated:
        label, face, edge, text_color = "BOSS DOWN", "#052e16", "#22c55e", "#dcfce7"
    else:
        return

    banner = patches.FancyBboxPatch(
        (2.35, 5.42), 3.95, 0.54,
        boxstyle="round,pad=0.015,rounding_size=0.12",
        facecolor=face, edgecolor=edge, linewidth=1.4,
        alpha=0.92, zorder=8.0,
    )
    ax.add_patch(banner)
    text = ax.text(
        4.325, 5.69, label,
        ha="center", va="center",
        fontsize=18, fontweight="black",
        color=text_color, zorder=8.2,
    )
    _add_text_effect(text, 4.8, "#020617", 1.5, edge)


def render_boss_battle_frame(frame: BossBattleFrame, ax=None):
    if not HAS_MPL:
        return None
    _load_pyplot(interactive=False)

    if ax is None:
        _, ax = plt.subplots(figsize=(12, 7))

    ax.clear()
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_facecolor("#05060a")
    ax.set_title(frame.title(), fontsize=13, color="#e5e7eb", pad=12)

    player_sprite = _load_asset("boss_window_player", PLAYER_FILE)
    boss_sprite = _select_boss_sprite(frame)
    energy = _phase_energy(frame)

    arena = patches.FancyBboxPatch(
        (0.5, 0.9), 7.6, 5.2,
        boxstyle="round,pad=0.02,rounding_size=0.18",
        facecolor="#0b1220",
        edgecolor="#334155",
        linewidth=1.5,
        zorder=0,
    )
    ax.add_patch(arena)
    panel = patches.FancyBboxPatch(
        (8.45, 0.9), 3.05, 5.2,
        boxstyle="round,pad=0.02,rounding_size=0.16",
        facecolor="#0f172a",
        edgecolor="#334155",
        linewidth=1.3,
        zorder=0,
    )
    ax.add_patch(panel)
    _draw_arena_backdrop(ax, arena, panel, frame)

    floor_shadow = patches.Ellipse((4.38, 1.42), 6.65, 0.92, facecolor="#030712", edgecolor="none", alpha=0.9, zorder=0.42)
    floor_shadow.set_clip_path(arena)
    ax.add_patch(floor_shadow)
    floor_ring = patches.Ellipse(
        (4.45, 1.68), 5.95, 0.52,
        fill=False, edgecolor="#f97316",
        linewidth=1.0 + energy * 0.55,
        alpha=0.12 + energy * 0.16, zorder=0.5,
    )
    floor_ring.set_clip_path(arena)
    ax.add_patch(floor_ring)
    inner_floor = patches.Ellipse((4.4, 1.64), 4.65, 0.32, facecolor="#111827", edgecolor="#1e293b", linewidth=0.8, alpha=0.88, zorder=0.47)
    inner_floor.set_clip_path(arena)
    ax.add_patch(inner_floor)

    t = frame.motion_t
    player_attack_offset = 0.0
    player_scale = 1.0
    if frame.phase == "windup":
        player_attack_offset = -0.16
        player_scale = 0.985
    elif frame.phase == "attack":
        player_attack_offset = 0.28
        player_scale = 1.015
    elif frame.phase == "lunge":
        player_attack_offset = 0.68
        player_scale = 1.05
    elif frame.phase == "impact":
        player_attack_offset = 0.4
        player_scale = 1.03
    elif frame.phase == "recover":
        player_attack_offset = 0.14
        player_scale = 1.01

    boss_shake = 0.0
    if frame.shake > 0:
        boss_shake = 0.12 if int(t * 24) % 2 == 0 else -0.12

    player_x = 0.96 + player_attack_offset
    player_y = 1.1 - (0.06 if frame.phase == "windup" else 0.0)
    boss_x = 5.16 + boss_shake
    boss_y = 1.25 + (0.06 if frame.defeated else 0.0)

    player_anchor = (player_x + 1.46, player_y + 2.6)
    boss_anchor = (boss_x + 0.92, boss_y + 1.48)

    _draw_glow(ax, (player_x + 1.28, player_y + 2.22), 2.35, 2.0, "#2563eb", 0.26 + energy * 0.08, 1.1, clip_path=arena)
    _draw_glow(ax, (boss_x + 1.0, boss_y + 1.8), 2.9, 2.3, "#dc2626", 0.2 + energy * 0.18, 1.12, clip_path=arena)

    player_shadow = patches.Ellipse((player_x + 1.22, 1.56), 1.72 * player_scale, 0.28, facecolor="#020617", edgecolor="none", alpha=0.72, zorder=2.0)
    player_shadow.set_clip_path(arena)
    ax.add_patch(player_shadow)
    boss_shadow = patches.Ellipse((boss_x + 0.95, 1.56), 1.5, 0.26, facecolor="#020617", edgecolor="none", alpha=0.78, zorder=2.0)
    boss_shadow.set_clip_path(arena)
    ax.add_patch(boss_shadow)

    if frame.damage > 0 and frame.phase == "windup":
        charge = patches.Circle((player_anchor[0] + 0.32, player_anchor[1] - 0.04), 0.12 + energy * 0.1, facecolor="#fef08a", edgecolor="#f59e0b", linewidth=0.8, alpha=0.8, zorder=5.3)
        charge.set_clip_path(arena)
        ax.add_patch(charge)
        _draw_glow(ax, (player_anchor[0] + 0.32, player_anchor[1] - 0.04), 0.52, 0.52, "#fde68a", 0.3, 5.2, clip_path=arena)

    if not _draw_sprite(ax, player_sprite, player_x, player_y, 2.55 * player_scale, 3.9 * player_scale, zorder=4.6, clip_path=arena):
        fallback = patches.Circle((player_x + 1.2, 2.8), 0.7, color="#60a5fa", zorder=4.6)
        fallback.set_clip_path(arena)
        ax.add_patch(fallback)

    flashed_boss = _flash_sprite(boss_sprite, 0.34 + 0.28 * frame.hit_flash if frame.hit_flash > 0 else 0.0)
    if not _draw_sprite(ax, flashed_boss, boss_x, boss_y, 2.35, 2.35, zorder=5.0, clip_path=arena):
        fallback = patches.Circle((boss_x + 1.0, boss_y + 1.0), 0.75, color="#ef4444", zorder=5.0)
        fallback.set_clip_path(arena)
        ax.add_patch(fallback)

    _draw_action_trail(ax, frame, (player_anchor[0] + 0.18, player_anchor[1] - 0.12), boss_anchor, clip_path=arena)
    _draw_impact_burst(ax, frame, (boss_anchor[0], boss_anchor[1]), clip_path=arena)

    if frame.impact_text:
        shadow = ax.text(
            boss_x + 1.02, 4.62,
            frame.impact_text,
            ha="center", va="center",
            fontsize=28 if frame.phase == "impact" else 24,
            fontweight="black", fontstyle="italic",
            rotation=-13, color="#fecaca", alpha=0.38, zorder=7.75,
        )
        _add_text_effect(shadow, 8.0, "#450a0a")
        damage_text = ax.text(
            boss_x + 0.96, 4.56,
            frame.impact_text,
            ha="center", va="center",
            fontsize=26 if frame.phase == "impact" else 22,
            fontweight="black", fontstyle="italic",
            rotation=-11, color="#fff7ed", zorder=8.0,
        )
        _add_text_effect(damage_text, 6.5, "#7f1d1d", 2.0, "#f97316")

    player_plate = patches.FancyBboxPatch(
        (0.82, 5.2), 2.0, 0.42,
        boxstyle="round,pad=0.015,rounding_size=0.08",
        facecolor="#0f172a", edgecolor="#3b82f6", linewidth=1.1,
        zorder=3.5,
    )
    player_plate.set_clip_path(arena)
    ax.add_patch(player_plate)
    boss_plate = patches.FancyBboxPatch(
        (5.15, 4.0), 2.15, 0.42,
        boxstyle="round,pad=0.015,rounding_size=0.08",
        facecolor="#2b0a12", edgecolor="#fb7185", linewidth=1.1,
        zorder=3.5,
    )
    boss_plate.set_clip_path(arena)
    ax.add_patch(boss_plate)

    player_label = ax.text(1.82, 5.41, "PLAYER", ha="center", va="center", fontsize=12, color="#eff6ff", fontweight="bold", zorder=3.8)
    boss_label = ax.text(6.22, 4.21, "DEMON SLIME", ha="center", va="center", fontsize=11, color="#ffe4e6", fontweight="bold", zorder=3.8)
    _add_text_effect(player_label, 3.0, "#0f172a")
    _add_text_effect(boss_label, 3.0, "#3f0f1b")

    player_state = f"Coins {frame.coins}"
    action_text = "WAIT" if frame.skill_idx is None else f"Skill {frame.skill_idx}"
    ax.text(0.96, 0.74, player_state, fontsize=10, color="#cbd5e1")
    ax.text(2.62, 0.74, f"Action {action_text}", fontsize=10, color="#e2e8f0")
    ax.text(5.18, 0.74, f"Damage {frame.damage}", fontsize=10, color="#fca5a5")

    hp_ratio = 0.0 if frame.boss_hp_max <= 0 else frame.boss_hp / frame.boss_hp_max
    hp_text = ax.text(5.2, 4.72, f"HP {frame.boss_hp}/{frame.boss_hp_max}", fontsize=11, color="#f8fafc", zorder=4.0)
    _add_text_effect(hp_text, 2.6, "#450a0a")
    _draw_progress_bar(ax, 0.437, 0.742, 0.218, 0.036, hp_ratio, "#ef4444", "#111827")

    status = "Fighting"
    color = "#60a5fa"
    if frame.defeated:
        status = "Boss Down"
        color = "#22c55e"
    elif frame.retry:
        status = "Retry"
        color = "#f59e0b"
    elif frame.failed:
        status = "Failed"
        color = "#ef4444"
    status_text = ax.text(9.98, 5.65, status, ha="center", va="center", fontsize=13, fontweight="bold", color=color, zorder=1.2)
    _add_text_effect(status_text, 3.2, "#020617")
    ax.text(8.86, 5.58, "BATTLE FLOW", fontsize=10.6, color="#f8fafc", fontweight="bold", zorder=1.2)
    ax.text(8.72, 5.2, f"Attempt {frame.attempt}", fontsize=10.3, color="#cbd5e1", zorder=1.2)
    ax.text(10.02, 5.2, f"Turn {frame.attack_round}", fontsize=10.3, color="#cbd5e1", zorder=1.2)
    ax.text(8.72, 4.88, f"Boss {frame.boss_index}/{frame.boss_total}", fontsize=10.3, color="#cbd5e1", zorder=1.2)
    ax.text(8.72, 4.5, "Skills", fontsize=11.2, color="#f8fafc", fontweight="bold", zorder=1.2)
    skill_y = 4.18
    for idx, skill in enumerate(frame.skills):
        ready = skill["remaining_cd"] == 0
        cd_text = f"cd {skill['remaining_cd']}/{skill['cooldown']}"
        line_color = "#22c55e" if ready else "#94a3b8"
        bg = patches.FancyBboxPatch(
            (8.66, skill_y - 0.18), 2.56, 0.31,
            boxstyle="round,pad=0.008,rounding_size=0.05",
            facecolor="#0b1220" if ready else "#111827",
            edgecolor="#1e293b", linewidth=0.8, alpha=0.92,
            zorder=1.0,
        )
        ax.add_patch(bg)
        ax.text(8.78, skill_y, f"S{idx}", fontsize=9.4, color="#f8fafc", zorder=1.2)
        ax.text(9.2, skill_y, f"{skill['damage']} dmg", fontsize=9.4, color="#cbd5e1", zorder=1.2)
        ax.text(10.18, skill_y, cd_text, fontsize=9.1, color=line_color, zorder=1.2)
        ratio = 1.0 if skill["cooldown"] == 0 else (skill["cooldown"] - skill["remaining_cd"]) / skill["cooldown"]
        _draw_progress_bar(ax, 0.731, (skill_y - 0.104) / 7.0, 0.188, 0.016, ratio, "#22c55e" if ready else "#64748b", "#111827")
        skill_y -= 0.45
        if skill_y < 1.65:
            break

    _draw_status_banner(ax, frame)

    return ax


def render_boss_battle_window(frames: List[BossBattleFrame], fps: int = DEFAULT_BOSS_BATTLE_FPS):
    if not HAS_MPL:
        print("[boss_viz] matplotlib 未安装，跳过 BOSS 战窗口")
        return
    if not frames:
        print("[boss_viz] 没有可展示的 BOSS 战帧")
        return

    _load_pyplot(interactive=True)
    if plt is None:
        print("[boss_viz] 无法加载交互式后端，无法显示 BOSS 战窗口")
        return

    fig, ax = plt.subplots(figsize=(12, 7))
    plt.subplots_adjust(bottom=0.18)
    state = {"idx": 0, "playing": False}

    def draw():
        render_boss_battle_frame(frames[state["idx"]], ax=ax)
        fig.canvas.draw_idle()

    def goto(idx: int):
        state["idx"] = max(0, min(idx, len(frames) - 1))
        draw()

    def on_prev(event):
        goto(state["idx"] - 1)

    def on_next(event):
        goto(state["idx"] + 1)

    base_interval = max(16, 1000 // max(fps, 1))
    timer = fig.canvas.new_timer(interval=base_interval)

    def on_timer():
        if state["playing"]:
            if state["idx"] < len(frames) - 1:
                goto(state["idx"] + 1)
                timer.interval = max(16, min(base_interval, frames[state["idx"]].duration_ms))
            else:
                state["playing"] = False
                play_button.label.set_text("Play")
                timer.stop()

    timer.add_callback(on_timer)

    def on_play(event):
        state["playing"] = not state["playing"]
        play_button.label.set_text("Pause" if state["playing"] else "Play")
        if state["playing"]:
            timer.interval = max(16, min(base_interval, frames[state["idx"]].duration_ms))
            timer.start()
        else:
            timer.stop()

    axprev = plt.axes([0.22, 0.05, 0.12, 0.07])
    axplay = plt.axes([0.40, 0.05, 0.12, 0.07])
    axnext = plt.axes([0.58, 0.05, 0.12, 0.07])
    prev_button = Button(axprev, "Prev")
    play_button = Button(axplay, "Play")
    next_button = Button(axnext, "Next")
    prev_button.on_clicked(on_prev)
    play_button.on_clicked(on_play)
    next_button.on_clicked(on_next)

    draw()
    plt.show()


def save_boss_battle_gif(frames: List[BossBattleFrame], output_path: str = "boss_battle.gif", fps: int = DEFAULT_BOSS_BATTLE_FPS):
    if not HAS_MPL:
        print("[boss_viz] matplotlib 未安装，跳过 GIF 导出")
        return
    if not frames:
        print("[boss_viz] 没有可导出的 BOSS 战帧")
        return

    _load_pyplot(interactive=False)
    fig, ax = plt.subplots(figsize=(12, 7))

    def update(frame_idx):
        render_boss_battle_frame(frames[frame_idx], ax=ax)

    ani = FuncAnimation(fig, update, frames=len(frames), interval=max(16, 1000 // max(fps, 1)))
    ani.save(output_path, writer=PillowWriter(fps=fps))
    plt.close(fig)
    print(f"[boss_viz] 已保存 BOSS 战回放: {output_path}")
