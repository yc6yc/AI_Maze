"""
api_adapter.py — 处理与裁判服务器的 JSON 交互
负责人：组长（角色1）
-----------------------------------------------
AI 挑战者每回合收到受限 JSON，本模块负责：
  1. 解析服务器下发的 JSON -> GameContext
  2. 将 Action 序列化为服务器期望格式上传
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from core.state import (
    GameContext, MazeState, PlayerState, Skill, Action, MazeState
)


# --------------------------------------------------------------------------- #
# 解析服务器初始包（AI 挑战者视角：受限可见）
# --------------------------------------------------------------------------- #
def parse_initial_packet(raw: Dict[str, Any], rows: int, cols: int) -> GameContext:
    """
    将比赛初始 JSON 解析为 GameContext。
    AI 挑战者只能看到：
      - maze 入口 S 的坐标（其余格子未知）
      - PlayerSkills
      - CoinConsumption
      - minRounds
    rows/cols 由入口 S 坐标推断上限，或由服务器约定传入。
    """
    maze_grid: Optional[List[List[str]]] = raw.get("maze")
    skill_raw: List[List[int]] = raw.get("PlayerSkills", [])
    coin_consumption: int = raw.get("CoinConsumption", 0)
    min_rounds: int = raw.get("minRouds", 0)   # 注意 JSON key 拼写

    skills = [Skill.from_list(s) for s in skill_raw]

    if maze_grid is not None:
        # ---- 本地模拟模式：完整地图可见 ----
        maze_state = MazeState.from_full_map(maze_grid)
    else:
        # ---- 真实对局模式：只创建雾图 ----
        maze_state = MazeState(rows=rows, cols=cols)

    # 找到起点 S（若完整地图已传入则从已揭露地图找）
    start_pos = maze_state.start or (0, 0)

    player = PlayerState(pos=start_pos, skills=skills)

    return GameContext(
        maze=maze_state,
        player=player,
        coin_consumption=coin_consumption,
        min_rounds=min_rounds,
    )


def parse_initial_json(path_or_str: str, rows: int = 15, cols: int = 15) -> GameContext:
    """从文件路径或 JSON 字符串解析"""
    try:
        with open(path_or_str, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = json.loads(path_or_str)
    return parse_initial_packet(data, rows, cols)


# --------------------------------------------------------------------------- #
# 序列化动作 -> JSON（上传给服务器）
# --------------------------------------------------------------------------- #
def action_to_json(action: Action) -> Dict[str, Any]:
    """将 Action 转为服务器期望的 JSON 格式（具体字段按裁判接口确认后调整）"""
    result: Dict[str, Any] = {"move": action.move}
    if action.use_skill is not None:
        result["skill"] = action.use_skill
    return result


# --------------------------------------------------------------------------- #
# 解析服务器每回合反馈
# --------------------------------------------------------------------------- #
def apply_round_feedback(ctx: GameContext, feedback: Dict[str, Any]):
    """
    将服务器下发的回合反馈应用到 GameContext。
    feedback 字段由裁判接口决定，示例：
    {
        "new_pos": [r, c],
        "visible_cells": [{"pos": [r, c], "cell": "G"}, ...],
        "coin_delta": 50,
        "boss_hp_revealed": [11, 13],   // 击败 boss 后才可见
        "round": 5
    }
    """
    if "new_pos" in feedback:
        r, c = feedback["new_pos"]
        ctx.player.pos = (r, c)

    for vc in feedback.get("visible_cells", []):
        r, c = vc["pos"]
        ctx.maze.reveal(r, c, vc["cell"])

    if "coin_delta" in feedback:
        ctx.player.coins += feedback["coin_delta"]

    if "boss_hp_revealed" in feedback:
        ctx.boss_defeated = feedback["boss_hp_revealed"]

    if "round" in feedback:
        ctx.player.round_num = feedback["round"]

    ctx.player.tick_cooldowns()
    ctx.history.append(ctx.snapshot())
