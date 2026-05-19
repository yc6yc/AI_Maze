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
    matplotlib.use("Agg")   # 无显示器时使用非交互后端
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    import matplotlib.image as mpimg
    from matplotlib.animation import FuncAnimation, PillowWriter
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

from core.state import MazeState, CELL_WALL

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
}
_SPRITE_CACHE: Dict[str, Any] = {}


def _load_sprite(name: str):
    """懒加载角色贴图；若素材不存在则返回 None。"""
    if not HAS_MPL:
        return None
    if name in _SPRITE_CACHE:
        return _SPRITE_CACHE[name]

    path = SPRITE_FILES[name]
    if not path.exists():
        _SPRITE_CACHE[name] = None
        return None

    try:
        _SPRITE_CACHE[name] = mpimg.imread(path)
    except Exception:
        _SPRITE_CACHE[name] = None
    return _SPRITE_CACHE[name]


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
        interpolation="bilinear",
        zorder=zorder,
    )
    return True


def render_frame(
    maze: MazeState,
    player_pos: Tuple[int, int],
    ax=None,
    title: str = "",
):
    """在给定 axes 上渲染迷宫当前帧"""
    if not HAS_MPL:
        return None

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    ax.clear()

    rows, cols = maze.rows, maze.cols
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10)

    player_sprite = _load_sprite("player")
    boss_sprite = _load_sprite("boss")

    for r in range(rows):
        for c in range(cols):
            cell = maze.fog_map[r][c]
            color = CELL_COLORS.get(cell, "#ffffff")
            cell_y = rows - 1 - r
            rect = patches.Rectangle(
                (c, cell_y), 1, 1,
                linewidth=0.3, edgecolor="#aaaaaa", facecolor=color
            )
            ax.add_patch(rect)
            if cell == "B" and _draw_sprite(ax, boss_sprite, c, cell_y, scale=0.86, zorder=4):
                continue
            if cell and cell not in ("#", " ", None):
                ax.text(
                    c + 0.5, cell_y + 0.5, cell,
                    ha="center", va="center", fontsize=7, color="#333333"
                )

    # 玩家位置
    pr, pc = player_pos
    player_y = rows - 1 - pr
    if not _draw_sprite(ax, player_sprite, pc, player_y, scale=0.9, zorder=7):
        circle = plt.Circle(
            (pc + 0.5, player_y + 0.5), 0.35,
            color=PLAYER_COLOR, zorder=7
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

    fig, ax = plt.subplots(figsize=(7, 7))
    plt.tight_layout()

    def update(frame_idx):
        snap = history[frame_idx]
        pos = tuple(snap["pos"])
        render_frame(
            maze, pos, ax=ax,
            title=f"Round {snap['round']} | Coins {snap['coins']}"
        )

    ani = FuncAnimation(fig, update, frames=len(history), interval=1000 // fps)
    writer = PillowWriter(fps=fps)
    ani.save(output_path, writer=writer)
    plt.close(fig)
    print(f"[visualizer] 已保存回放: {output_path}")


def render_path_overlay(
    maze: MazeState,
    path: List[Tuple[int, int]],
    output_path: str = "path.png",
):
    """在地图上叠加路径箭头并保存图片"""
    if not HAS_MPL:
        return

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
