"""
boss_battle_visualizer.py — 独立的 BOSS 战可视化窗口
----------------------------------------------------
不修改现有迷宫可视化逻辑，单独打开一个窗口展示玩家与 BOSS 的战斗过程。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    import matplotlib.image as mpimg
    import numpy as np
    import matplotlib.patches as patches
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.widgets import Button
    HAS_MPL = True
    plt = None
except ImportError:
    HAS_MPL = False
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
    agent = CombatAgent()
    frames: List[BossBattleFrame] = []
    total_round = 0

    for boss_index, boss_hp_max in enumerate(boss_hps, start=1):
        boss_hp = boss_hp_max
        attempt = 0

        while boss_hp > 0:
            attempt += 1
            for attack_round in range(1, sim_ctx.min_rounds + 1):
                total_round += 1
                action = agent.decide_combat(sim_ctx)
                damage = 0
                if action.use_skill is not None:
                    damage = sim_ctx.player.use_skill(action.use_skill)
                    boss_hp = max(boss_hp - damage, 0)

                defeated = boss_hp <= 0
                sim_ctx.player.tick_cooldowns()
                timeline = [
                    ("windup", 0.05, 90, 0.0, 0.0, None),
                    ("attack", 0.22, 90, 0.0, 0.0, None),
                    ("lunge", 0.38, 80, 0.0, 0.0, None),
                    ("impact", 0.52, 110, 1.0 if damage > 0 else 0.0, 1.0 if damage > 0 else 0.0, f"-{damage}" if damage > 0 else None),
                    ("recover", 0.74, 100, 0.0, 0.25 if damage > 0 else 0.0, None),
                    ("idle", 0.96, 110, 0.0, 0.0, None),
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
                    duration_ms=260,
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
    fps: int = 3,
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
    ax.add_patch(
        patches.Rectangle(
            (x, y), width, height,
            facecolor=bg, edgecolor="#334155", linewidth=1.0,
            transform=ax.transAxes, zorder=1,
        )
    )
    if ratio > 0:
        ax.add_patch(
            patches.Rectangle(
                (x, y), width * ratio, height,
                facecolor=fill, edgecolor="none",
                transform=ax.transAxes, zorder=2,
            )
        )


def _draw_sprite(ax, sprite, x: float, y: float, width: float, height: float, zorder: int = 5):
    if sprite is None:
        return False
    ax.imshow(
        sprite,
        extent=(x, x + width, y, y + height),
        interpolation="nearest",
        zorder=zorder,
        aspect="auto",
    )
    return True


def _flash_sprite(sprite, flash_strength: float):
    if not HAS_MPL or sprite is None or flash_strength <= 0:
        return sprite
    arr = sprite.astype(np.float32).copy()
    arr[..., :3] = arr[..., :3] * (1.0 - flash_strength) + 1.0 * flash_strength
    return np.clip(arr, 0.0, 1.0)


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
    ax.set_facecolor("#070b14")
    ax.set_title(frame.title(), fontsize=13, color="#e5e7eb", pad=12)

    player_sprite = _load_asset("boss_window_player", PLAYER_FILE)
    boss_sprite = _select_boss_sprite(frame)

    arena = patches.FancyBboxPatch(
        (0.5, 0.9), 7.6, 5.2,
        boxstyle="round,pad=0.02,rounding_size=0.16",
        facecolor="#101826",
        edgecolor="#334155",
        linewidth=1.5,
        zorder=0,
    )
    ax.add_patch(arena)
    panel = patches.FancyBboxPatch(
        (8.45, 0.9), 3.05, 5.2,
        boxstyle="round,pad=0.02,rounding_size=0.14",
        facecolor="#0f172a",
        edgecolor="#334155",
        linewidth=1.3,
        zorder=0,
    )
    ax.add_patch(panel)

    floor = patches.Ellipse((4.25, 1.7), 6.1, 0.72, facecolor="#0b1220", edgecolor="#1e293b", linewidth=1.0, zorder=0)
    ax.add_patch(floor)
    ax.plot([4.0, 4.6], [3.25, 3.25], color="#334155", linewidth=2.0, zorder=1, alpha=0.85)

    t = frame.motion_t
    player_attack_offset = 0.0
    player_scale = 1.0
    if frame.phase == "windup":
        player_attack_offset = -0.10
        player_scale = 0.99
    elif frame.phase == "attack":
        player_attack_offset = 0.22
        player_scale = 1.01
    elif frame.phase == "lunge":
        player_attack_offset = 0.55
        player_scale = 1.03
    elif frame.phase == "impact":
        player_attack_offset = 0.35
        player_scale = 1.02
    elif frame.phase == "recover":
        player_attack_offset = 0.12

    boss_shake = 0.0
    if frame.shake > 0:
        boss_shake = 0.08 if int(t * 24) % 2 == 0 else -0.08

    player_x = 1.0 + player_attack_offset
    player_y = 1.15
    boss_x = 5.3 + boss_shake
    boss_y = 1.25

    if not _draw_sprite(ax, player_sprite, player_x, player_y, 2.55 * player_scale, 3.9 * player_scale, zorder=4):
        ax.add_patch(patches.Circle((player_x + 1.2, 2.8), 0.7, color="#60a5fa", zorder=4))
    flashed_boss = _flash_sprite(boss_sprite, 0.55 if frame.hit_flash > 0 else 0.0)
    if not _draw_sprite(ax, flashed_boss, boss_x, boss_y, 2.35, 2.35, zorder=5):
        ax.add_patch(patches.Circle((boss_x + 1.0, boss_y + 1.0), 0.75, color="#ef4444", zorder=5))

    if frame.phase in {"attack", "lunge", "impact"} and frame.skill_idx is not None:
        slash = patches.Arc(
            (4.95, 3.08), 1.95, 1.15, angle=-8,
            theta1=210, theta2=340,
            color="#93c5fd",
            linewidth=3.6,
            zorder=6,
            alpha=0.95 if frame.phase != "impact" else 0.72,
        )
        ax.add_patch(slash)
        spark = patches.RegularPolygon(
            (5.5, 3.0), numVertices=4, radius=0.20,
            orientation=0.78, facecolor="#fef08a", edgecolor="#f59e0b",
            linewidth=1.0, zorder=7,
        )
        ax.add_patch(spark)
    if frame.impact_text:
        ax.text(boss_x + 1.0, 4.55, frame.impact_text, ha="center", va="center", fontsize=14, fontweight="bold", color="#fca5a5", zorder=7)

    ax.text(2.25, 5.35, "PLAYER", ha="center", va="bottom", fontsize=12, color="#e2e8f0", fontweight="bold")
    ax.text(6.3, 4.15, "DEMON SLIME", ha="center", va="bottom", fontsize=11, color="#fca5a5", fontweight="bold")

    player_state = f"Coins {frame.coins}"
    action_text = "WAIT" if frame.skill_idx is None else f"Skill {frame.skill_idx}"
    ax.text(0.95, 0.78, player_state, fontsize=10, color="#cbd5e1")
    ax.text(2.75, 0.78, f"Action {action_text}", fontsize=10, color="#cbd5e1")
    ax.text(5.1, 0.78, f"Damage {frame.damage}", fontsize=10, color="#fca5a5")

    hp_ratio = 0.0 if frame.boss_hp_max <= 0 else frame.boss_hp / frame.boss_hp_max
    ax.text(5.25, 4.75, f"HP {frame.boss_hp}/{frame.boss_hp_max}", fontsize=11, color="#f8fafc")
    _draw_progress_bar(ax, 0.44, 0.75, 0.21, 0.032, hp_ratio, "#ef4444", "#1e293b")

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
    ax.text(9.98, 5.66, status, ha="center", va="center", fontsize=13, fontweight="bold", color=color)
    ax.text(8.72, 5.28, f"Attempt {frame.attempt}", fontsize=10.5, color="#cbd5e1")
    ax.text(10.0, 5.28, f"Turn {frame.attack_round}", fontsize=10.5, color="#cbd5e1")
    ax.text(8.72, 4.95, f"Boss {frame.boss_index}/{frame.boss_total}", fontsize=10.5, color="#cbd5e1")
    ax.text(8.72, 4.55, "Skills", fontsize=11, color="#f8fafc", fontweight="bold")
    skill_y = 4.18
    for idx, skill in enumerate(frame.skills):
        ready = skill["remaining_cd"] == 0
        cd_text = f"cd {skill['remaining_cd']}/{skill['cooldown']}"
        line_color = "#22c55e" if ready else "#94a3b8"
        ax.text(8.72, skill_y, f"S{idx}", fontsize=9.5, color="#f8fafc")
        ax.text(9.18, skill_y, f"{skill['damage']} dmg", fontsize=9.5, color="#cbd5e1")
        ax.text(10.2, skill_y, cd_text, fontsize=9.2, color=line_color)
        ratio = 1.0 if skill["cooldown"] == 0 else (skill["cooldown"] - skill["remaining_cd"]) / skill["cooldown"]
        _draw_progress_bar(ax, 0.73, (skill_y - 0.09) / 7.0, 0.19, 0.016, ratio, "#22c55e" if ready else "#64748b", "#1e293b")
        skill_y -= 0.42
        if skill_y < 1.65:
            break

    return ax


def render_boss_battle_window(frames: List[BossBattleFrame], fps: int = 3):
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

    timer = fig.canvas.new_timer(interval=max(16, 1000 // max(fps, 1)))

    def on_timer():
        if state["playing"]:
            if state["idx"] < len(frames) - 1:
                goto(state["idx"] + 1)
                timer.interval = max(16, frames[state["idx"]].duration_ms)
            else:
                state["playing"] = False
                play_button.label.set_text("Play")
                timer.stop()

    timer.add_callback(on_timer)

    def on_play(event):
        state["playing"] = not state["playing"]
        play_button.label.set_text("Pause" if state["playing"] else "Play")
        if state["playing"]:
            timer.interval = max(16, frames[state["idx"]].duration_ms)
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


def save_boss_battle_gif(frames: List[BossBattleFrame], output_path: str = "boss_battle.gif", fps: int = 3):
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
