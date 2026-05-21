"""
visualizer.py — 迷宫过程可视化（matplotlib）
负责人：角色4（评测），角色2/3可调用
----------------------------------------------
提供：
  - render_frame()   实时渲染单帧（动画用）
  - render_history() 回放历史轨迹
  - save_gif()       保存 GIF
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

try:
    import matplotlib
    import matplotlib.patches as patches
    import matplotlib.image as mpimg
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.widgets import Button
    HAS_MPL = True
    plt = None
except ImportError:
    HAS_MPL = False
    plt = None

from core.state import (
    MazeState,
    CELL_WALL,
    CELL_TRAP,
    CELL_COIN,
    CELL_GOLD,
    CELL_LOCK,
    CELL_BOSS,
    CELL_END,
)

# 颜色映射
CELL_COLORS: Dict[Optional[str], str] = {
    None:   "#888888",   # 未探索（雾）
    "#":    "#222222",   # 墙
    " ":    "#f5f5f5",   # 通路
    "S":    "#00cc44",   # 起点
    "E":    "#0055ff",   # 终点
    "B":    "#ff0000",   # BOSS
    "T":    "#ff8800",   # 陷阱
    "C":    "#ffdd00",   # 金币
    "G":    "#ffdd00",   # 金币(G)
    "L":    "#cc66ff",   # 锁
}
PLAYER_COLOR = "#ff00ff"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SPRITE_FILES = {
    "player": ASSETS_DIR / "player.png",
    "boss": ASSETS_DIR / "boss.png",
    "floor": ASSETS_DIR / "floor.png",
    "wall": ASSETS_DIR / "wall.png",
    "coin": ASSETS_DIR / "coin.png",
    "trap": ASSETS_DIR / "trap.png",
    "exit": ASSETS_DIR / "exit.png",
}
BACKGROUND_FILE = ASSETS_DIR / "background.png"
BACKGROUND_TILE_FILE = ASSETS_DIR / "floor_tile.png"
_ASSET_CACHE: Dict[str, Any] = {}
_INTERACTIVE_BACKENDS = ["TkAgg", "Qt5Agg", "QtAgg", "WXAgg", "MacOSX"]


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
    """懒加载图片素材；若素材不存在则返回 None。"""
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


def _load_sprite(name: str):
    """懒加载角色贴图；若素材不存在则返回 None。"""
    return _load_asset(name, SPRITE_FILES[name])


def _draw_sprite(ax, sprite, cell_x: int, cell_y: int, scale: float = 0.92, zorder: int = 6):
    """在单元格中心绘制 sprite。"""
    if sprite is None:
        return False

    margin = (1.0 - scale) / 2.0
    ax.imshow(
        sprite,
        extent=(
            cell_x + margin,
            cell_x + 1.0 - margin,
            cell_y + margin,
            cell_y + 1.0 - margin,
        ),
        interpolation="nearest",
        zorder=zorder,
    )
    return True


def _draw_tile_sprite(ax, name: str, cell_x: int, cell_y: int, scale: float = 1.0, zorder: int = 1):
    """Draw a named tile image and report whether it was available."""
    sprite = _load_sprite(name)
    return _draw_sprite(ax, sprite, cell_x, cell_y, scale=scale, zorder=zorder)


def _draw_base_tile(ax, cell: Optional[str], cell_x: int, cell_y: int):
    """Draw the visible maze tile before overlays such as coins, traps, and player."""
    if cell is None:
        rect = patches.Rectangle(
            (cell_x, cell_y), 1, 1,
            linewidth=0.15, edgecolor="#24202f", facecolor="#17161f", zorder=1
        )
        ax.add_patch(rect)
        return

    if cell == CELL_WALL:
        if not _draw_tile_sprite(ax, "wall", cell_x, cell_y, scale=1.0, zorder=1):
            _draw_cell_icon(ax, cell, cell_x, cell_y, zorder=1)
        return

    if not _draw_tile_sprite(ax, "floor", cell_x, cell_y, scale=1.0, zorder=1):
        color = CELL_COLORS.get(cell, "#f5f5f5")
        rect = patches.Rectangle(
            (cell_x, cell_y), 1, 1,
            linewidth=0.3, edgecolor="#aaaaaa", facecolor=color, zorder=1
        )
        ax.add_patch(rect)


def _draw_cell_sprite_overlay(ax, cell: Optional[str], cell_x: int, cell_y: int):
    """Draw gameplay objects with real pixel sprites where available."""
    if cell in (CELL_COIN, CELL_GOLD):
        return _draw_tile_sprite(ax, "coin", cell_x, cell_y, scale=0.9, zorder=8)
    if cell == CELL_TRAP:
        return _draw_tile_sprite(ax, "trap", cell_x, cell_y, scale=0.92, zorder=8)
    if cell == CELL_BOSS:
        return _draw_tile_sprite(ax, "boss", cell_x, cell_y, scale=0.92, zorder=8)
    if cell == CELL_END:
        return _draw_tile_sprite(ax, "exit", cell_x, cell_y, scale=0.92, zorder=8)
    return False


def _maze_for_snapshot(base_maze: MazeState, snap: Dict[str, Any]) -> MazeState:
    """Use the per-frame fog map when replay history provides one."""
    fog_map = snap.get("fog_map")
    if not fog_map:
        return base_maze
    return MazeState(
        rows=base_maze.rows,
        cols=base_maze.cols,
        fog_map=[row[:] for row in fog_map],
        start=base_maze.start,
        end=base_maze.end,
        triggered_traps=set(base_maze.triggered_traps),
    )


def _history_title(snap: Dict[str, Any]) -> str:
    steps = snap.get("steps", snap.get("round", 0))
    coins = snap.get("coins", 0)
    ratio = snap.get("coin_step_ratio", coins / steps if steps else 0)
    phase = snap.get("phase", "maze")
    title = f"{phase.upper()} | Step {steps} | Coins {coins} | Coins/Step {ratio:.2f}"
    if phase == "boss" and snap.get("boss_result") is not None:
        result = "WIN" if snap["boss_result"] == 1 else "LOSE"
        title += f" | Boss {result}"
    return title


def _draw_background(ax, rows: int, cols: int):
    """在迷宫底层绘制背景图像或铺砖纹理。"""
    bg = _load_asset("background", BACKGROUND_FILE)
    if bg is not None:
        ax.imshow(
            bg,
            extent=(0, cols, 0, rows),
            aspect="auto",
            zorder=-2,
        )
        return

    ax.set_facecolor("#1f1f1f")


def _draw_cell_icon(ax, cell: str, cell_x: int, cell_y: int, zorder: int = 5):
    """为金币、陷阱、墙、锁绘制简单图形图标。"""
    if cell in (CELL_COIN, CELL_GOLD):
        outer = patches.Circle(
            (cell_x + 0.5, cell_y + 0.5), 0.3,
            facecolor="#ffb300", edgecolor="#bf360c", linewidth=2.0, zorder=zorder
        )
        inner = patches.Circle(
            (cell_x + 0.5, cell_y + 0.5), 0.18,
            facecolor="#ffe082", edgecolor="none", zorder=zorder + 1
        )
        shine = patches.Wedge(
            (cell_x + 0.56, cell_y + 0.6), 0.18,
            theta1=40, theta2=90,
            facecolor="#fff8e1", edgecolor="none", zorder=zorder + 2
        )
        star = patches.RegularPolygon(
            (cell_x + 0.65, cell_y + 0.65), numVertices=5, radius=0.08,
            orientation=0.4, facecolor="#ffd54f", edgecolor="#f57f17",
            linewidth=1.0, zorder=zorder + 1
        )
        ax.add_patch(outer)
        ax.add_patch(inner)
        ax.add_patch(shine)
        ax.add_patch(star)
        ax.text(
            cell_x + 0.5, cell_y + 0.5, "C",
            ha="center", va="center", fontsize=10, fontweight="bold", color="#6d4c41", zorder=zorder + 3
        )
    elif cell == CELL_TRAP:
        trap_base = patches.FancyBboxPatch(
            (cell_x + 0.2, cell_y + 0.2), 0.6, 0.6,
            boxstyle="round,pad=0.02", facecolor="#ff7043",
            edgecolor="#d84315", linewidth=2.0, zorder=zorder
        )
        bolt = patches.Polygon(
            [
                (cell_x + 0.43, cell_y + 0.75),
                (cell_x + 0.55, cell_y + 0.55),
                (cell_x + 0.47, cell_y + 0.55),
                (cell_x + 0.58, cell_y + 0.35),
                (cell_x + 0.47, cell_y + 0.35),
                (cell_x + 0.55, cell_y + 0.45),
            ],
            closed=True,
            facecolor="#ffeb3b",
            edgecolor="#f57f17",
            linewidth=1.8,
            zorder=zorder + 1,
        )
        ax.add_patch(trap_base)
        ax.add_patch(bolt)
        ax.text(
            cell_x + 0.5, cell_y + 0.44, "!",
            ha="center", va="center", fontsize=14, fontweight="bold", color="#bf360c", zorder=zorder + 2
        )
    elif cell == CELL_LOCK:
        body = patches.FancyBboxPatch(
            (cell_x + 0.28, cell_y + 0.32), 0.44, 0.32,
            boxstyle="round,pad=0.02", facecolor="#9575cd",
            edgecolor="#5e35b1", linewidth=2.0, zorder=zorder,
        )
        shackle = patches.Arc(
            (cell_x + 0.5, cell_y + 0.72), 0.38, 0.38,
            theta1=185, theta2=355,
            edgecolor="#5e35b1", linewidth=2.2, zorder=zorder + 1
        )
        keyhole = patches.Circle(
            (cell_x + 0.5, cell_y + 0.45), 0.06,
            facecolor="#4a148c", edgecolor="none", zorder=zorder + 2
        )
        ax.add_patch(body)
        ax.add_patch(shackle)
        ax.add_patch(keyhole)
    elif cell == CELL_WALL:
        wall = patches.Rectangle(
            (cell_x + 0.02, cell_y + 0.02), 0.96, 0.96,
            facecolor="#5d4037", edgecolor="#3e2723", linewidth=2.0, zorder=zorder
        )
        ax.add_patch(wall)
        for offset_y in (0.25, 0.5, 0.75):
            ax.plot(
                [cell_x + 0.05, cell_x + 0.95],
                [cell_y + offset_y, cell_y + offset_y],
                color="#3e2723",
                linewidth=1.3,
                zorder=zorder + 1,
            )
        for offset_x in (0.33, 0.66):
            ax.plot(
                [cell_x + offset_x, cell_x + offset_x],
                [cell_y + 0.05, cell_y + 0.95],
                color="#3e2723",
                linewidth=1.3,
                zorder=zorder + 1,
            )


def render_frame(
    maze: MazeState,
    player_pos: Tuple[int, int],
    ax=None,
    title: str = "",
):
    """在给定 axes 上渲染迷宫当前帧"""
    if not HAS_MPL:
        return None
    _load_pyplot(interactive=False)

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    ax.clear()

    rows, cols = maze.rows, maze.cols
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.set_aspect("equal")
    ax.axis("off")
    _draw_background(ax, rows, cols)
    if title:
        ax.set_title(title, fontsize=10)

    player_sprite = _load_sprite("player")
    for r in range(rows):
        for c in range(cols):
            cell = maze.fog_map[r][c]
            cell_y = rows - 1 - r
            _draw_base_tile(ax, cell, c, cell_y)
            if cell is None:
                border = patches.Rectangle(
                    (c, cell_y), 1, 1,
                    linewidth=0.15, edgecolor="#24202f", facecolor="none", zorder=3
                )
                ax.add_patch(border)
            if cell != CELL_WALL and not _draw_cell_sprite_overlay(ax, cell, c, cell_y):
                _draw_cell_icon(ax, cell, c, cell_y, zorder=4)
            if cell and cell not in (
                "#", " ", None, CELL_COIN, CELL_GOLD,
                CELL_TRAP, CELL_LOCK, CELL_BOSS, CELL_END,
            ):
                ax.text(
                    c + 0.5, cell_y + 0.5, cell,
                    ha="center", va="center", fontsize=7, color="#333333"
                )

    # 玩家位置
    pr, pc = player_pos
    player_y = rows - 1 - pr
    if not _draw_sprite(ax, player_sprite, pc, player_y, scale=0.9, zorder=12):
        circle = plt.Circle(
            (pc + 0.5, player_y + 0.5), 0.35,
            color=PLAYER_COLOR, zorder=12
        )
        ax.add_patch(circle)
    return ax


def render_history(
    maze: MazeState,
    history: List[Dict[str, Any]],
    output_path: str = "replay.gif",
    fps: int = 4,
):
    """将 ctx.history 渲染为 GIF"""
    if not HAS_MPL:
        print("[visualizer] matplotlib 未安装，跳过可视化")
        return
    _load_pyplot(interactive=False)

    fig, ax = plt.subplots(figsize=(7, 7))
    plt.tight_layout()

    def update(frame_idx):
        snap = history[frame_idx]
        pos = tuple(snap["pos"])
        frame_maze = _maze_for_snapshot(maze, snap)
        render_frame(
            frame_maze, pos, ax=ax,
            title=_history_title(snap)
        )

    ani = FuncAnimation(fig, update, frames=len(history), interval=1000 // fps)
    writer = PillowWriter(fps=fps)
    ani.save(output_path, writer=writer)
    plt.close(fig)
    print(f"[visualizer] 已保存回放: {output_path}")


def render_history_window(
    maze: MazeState,
    history: List[Dict[str, Any]],
    fps: int = 4,
):
    """在弹出窗口中回放历史轨迹，支持按钮控制。"""
    if not HAS_MPL:
        print("[visualizer] matplotlib 未安装，跳过窗口可视化")
        return
    _load_pyplot(interactive=True)
    if plt is None:
        print("[visualizer] 无法加载交互式后端，无法显示窗口")
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    plt.subplots_adjust(bottom=0.16)

    state = {"idx": 0, "playing": False}

    def draw():
        snap = history[state["idx"]]
        pos = tuple(snap["pos"])
        frame_maze = _maze_for_snapshot(maze, snap)
        render_frame(
            frame_maze, pos, ax=ax,
            title=_history_title(snap)
        )
        fig.canvas.draw_idle()

    def goto(idx: int):
        state["idx"] = max(0, min(idx, len(history) - 1))
        draw()

    def on_prev(event):
        goto(state["idx"] - 1)

    def on_next(event):
        goto(state["idx"] + 1)

    timer = fig.canvas.new_timer(interval=1000 // fps)

    def on_timer():
        if state["playing"]:
            if state["idx"] < len(history) - 1:
                goto(state["idx"] + 1)
            else:
                state["playing"] = False
                play_button.label.set_text("Play")
                timer.stop()

    timer.add_callback(on_timer)

    def on_play(event):
        state["playing"] = not state["playing"]
        play_button.label.set_text("Pause" if state["playing"] else "Play")
        if state["playing"]:
            timer.start()
        else:
            timer.stop()

    axprev = plt.axes([0.18, 0.04, 0.12, 0.06])
    axplay = plt.axes([0.35, 0.04, 0.12, 0.06])
    axnext = plt.axes([0.52, 0.04, 0.12, 0.06])
    prev_button = Button(axprev, "Prev")
    play_button = Button(axplay, "Play")
    next_button = Button(axnext, "Next")
    prev_button.on_clicked(on_prev)
    play_button.on_clicked(on_play)
    next_button.on_clicked(on_next)

    draw()
    plt.show()


def render_path_overlay(
    maze: MazeState,
    path: List[Tuple[int, int]],
    output_path: str = "path.png",
):
    """在地图上叠加路径箭头并保存图片"""
    if not HAS_MPL:
        return
    _load_pyplot(interactive=False)

    fig, ax = plt.subplots(figsize=(8, 8))
    render_frame(maze, path[0] if path else (0, 0), ax=ax)

    rows = maze.rows
    for i in range(len(path) - 1):
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        ax.annotate(
            "",
            xy=(c2 + 0.5, rows - 1 - r2 + 0.5),
            xytext=(c1 + 0.5, rows - 1 - r1 + 0.5),
            arrowprops=dict(arrowstyle="->", color="blue", lw=1.5),
        )

    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[visualizer] 已保存路径图: {output_path}")
