"""
tests/test_local_greedy_policy.py — LocalGreedyAgent 单元测试

验证内容：
1. 基础行为：返回合法 Action，四周全是墙时 STAY / 调用 fallback
2. 贪心方向选择：优先走金币、远离陷阱、已触发陷阱不再扣分
3. 对角邻居贡献：对角金币以 /2 权重影响方向得分
4. 已访问格子惩罚：history 中出现的坐标会被扣分
5. 配置参数：coin_value / trap_penalty 可调，影响决策

运行方式：
  pytest -s tests/test_local_greedy_policy.py
  python tests/test_local_greedy_policy.py
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.local_greedy_policy import LocalGreedyAgent, DEFAULT_CONFIG  # noqa: F401
from core.state import GameContext, MazeState, PlayerState, Action


# --------------------------------------------------------------------------- #
# 辅助工厂
# --------------------------------------------------------------------------- #

def build_context(grid, pos, history=None, triggered_traps=None):
    """
    从字符串网格 + 起始位置构造最小可用的 GameContext。

    参数说明：
    - grid: 二维字符串列表，直接传给 MazeState.from_full_map
    - pos: 玩家当前位置 (row, col)
    - history: 历史快照列表，每项含 {"pos": (r, c)}，用于计算已访问格子
    - triggered_traps: 已触发陷阱坐标集合，触发后不再扣分
    """
    maze = MazeState.from_full_map(grid)
    if triggered_traps:
        maze.triggered_traps = set(triggered_traps)
    player = PlayerState(pos=pos)
    return GameContext(
        maze=maze,
        player=player,
        coin_consumption=0,
        min_rounds=10,
        history=list(history or []),
    )


def run_verbose_greedy_demo(grid, pos, label="", history=None, triggered_traps=None):
    """
    运行一步贪心决策并打印详细日志，方便在控制台观察决策过程。
    pytest -s 时可见输出；python 直接运行同样有效。
    """
    agent = LocalGreedyAgent()
    ctx = build_context(grid, pos, history=history, triggered_traps=triggered_traps)

    print(f"\n{'='*50}")
    if label:
        print(f"场景：{label}")
    print(f"玩家位置: {pos}")
    print("地图：")
    for row in grid:
        print("  " + " ".join(row))

    from agents.local_greedy_policy import DIRECTION_MAP
    visited = {tuple(snap["pos"]) for snap in ctx.history}
    r, c = pos
    maze = ctx.maze
    print("方向得分：")
    for move, offsets in DIRECTION_MAP.items():
        dr, dc = offsets["direct"]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < maze.rows and 0 <= nc < maze.cols and maze.is_walkable(nr, nc)):
            print(f"  {move}: 不可走")
            continue
        score = agent._cell_value(nr, nc, maze, visited)
        for ddr, ddc in offsets["diagonals"]:
            dnr, dnc = r + ddr, c + ddc
            if 0 <= dnr < maze.rows and 0 <= dnc < maze.cols and maze.is_walkable(dnr, dnc):
                score += agent._cell_value(dnr, dnc, maze, visited) / 2
        print(f"  {move}: {score:.1f}")

    action = agent.decide(ctx)
    print(f"最终决策: {action.move}")
    print("=" * 50)
    return action


# --------------------------------------------------------------------------- #
# 测试地图
# --------------------------------------------------------------------------- #

# 玩家在 (1,1)，右侧有金币，上方是墙
GRID_COIN_RIGHT = [
    ["#", "#", "#", "#", "#"],
    ["#", " ", "C", " ", "#"],
    ["#", " ", " ", " ", "#"],
    ["#", "#", "#", "#", "#"],
]

# 玩家在 (1,1)，四周全是墙
GRID_ALL_WALLS = [
    ["#", "#", "#"],
    ["#", " ", "#"],
    ["#", "#", "#"],
]

# 玩家在 (1,1)，右侧是陷阱，下方是空格
GRID_TRAP_RIGHT = [
    ["#", "#", "#", "#"],
    ["#", " ", "T", "#"],
    ["#", " ", " ", "#"],
    ["#", "#", "#", "#"],
]

# 玩家在 (2,2)，四方均可走，右侧有金币
GRID_OPEN_COIN = [
    ["#", "#", "#", "#", "#"],
    ["#", " ", " ", " ", "#"],
    ["#", " ", " ", "C", "#"],
    ["#", " ", " ", " ", "#"],
    ["#", "#", "#", "#", "#"],
]


# --------------------------------------------------------------------------- #
# 基础行为
# --------------------------------------------------------------------------- #

class TestBasicBehavior:

    def test_returns_action_object(self):
        """decide() 必须返回 Action 实例。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_COIN_RIGHT, (1, 1))
        assert isinstance(agent.decide(ctx), Action)

    def test_move_is_valid_direction(self):
        """返回的 move 必须是合法方向字符串。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_COIN_RIGHT, (1, 1))
        assert agent.decide(ctx).move in {"UP", "DOWN", "LEFT", "RIGHT", "STAY"}

    def test_stay_when_surrounded_by_walls(self):
        """四周全是墙时，没有 fallback 则返回 STAY。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_ALL_WALLS, (1, 1))
        assert agent.decide(ctx).move == "STAY"

    def test_fallback_agent_called_when_no_moves(self):
        """四周全是墙时，有 fallback 则调用 fallback.decide()。"""
        from unittest.mock import MagicMock
        fallback = MagicMock()
        fallback.decide.return_value = Action(move="UP")
        agent = LocalGreedyAgent(fallback_agent=fallback)
        ctx = build_context(GRID_ALL_WALLS, (1, 1))
        result = agent.decide(ctx)
        fallback.decide.assert_called_once_with(ctx)
        assert result.move == "UP"

    def test_agent_name(self):
        assert LocalGreedyAgent().name == "LocalGreedyAgent"


# --------------------------------------------------------------------------- #
# 贪心方向选择
# --------------------------------------------------------------------------- #

class TestGreedyDirection:

    def test_prefers_coin_direction(self):
        """右侧有金币，应选 RIGHT。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_COIN_RIGHT, (1, 1))
        assert agent.decide(ctx).move == "RIGHT"

    def test_prefers_gold_over_empty(self):
        """右侧有 GOLD 格，应优先选 RIGHT。"""
        grid = [
            ["#", "#", "#", "#", "#"],
            ["#", " ", "G", " ", "#"],
            ["#", " ", " ", " ", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        agent = LocalGreedyAgent()
        ctx = build_context(grid, (1, 1))
        assert agent.decide(ctx).move == "RIGHT"

    def test_avoids_untriggered_trap(self):
        """右侧是未触发陷阱，下方是空格，应选 DOWN 而非 RIGHT。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_TRAP_RIGHT, (1, 1))
        assert agent.decide(ctx).move == "DOWN"

    def test_triggered_trap_not_penalized(self):
        """已触发的陷阱不再扣分，RIGHT 或 DOWN 均可接受。"""
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_TRAP_RIGHT, (1, 1), triggered_traps={(1, 2)})
        assert agent.decide(ctx).move in {"RIGHT", "DOWN"}


# --------------------------------------------------------------------------- #
# 对角邻居贡献
# --------------------------------------------------------------------------- #

class TestDiagonalContribution:

    def test_diagonal_coin_adds_half_score(self):
        """
        玩家 (1,1)，RIGHT 直接邻居 (1,2) 空，对角 (2,2) 金币 → 得分 25。
        DOWN  直接邻居 (2,1) 空，对角 (2,2) 金币 → 得分 25。
        两者并列，结果为 RIGHT 或 DOWN。
        """
        grid = [
            ["#", "#", "#", "#"],
            ["#", " ", " ", "#"],
            ["#", " ", "C", "#"],
            ["#", "#", "#", "#"],
        ]
        agent = LocalGreedyAgent()
        ctx = build_context(grid, (1, 1))
        assert agent.decide(ctx).move in {"RIGHT", "DOWN"}

    def test_direct_coin_beats_diagonal_coin(self):
        """
        RIGHT 直接邻居有金币（得分 50），DOWN 只有对角金币（得分 25），
        应选 RIGHT。
        """
        grid = [
            ["#", "#", "#", "#", "#"],
            ["#", " ", "C", " ", "#"],
            ["#", " ", " ", "C", "#"],
            ["#", "#", "#", "#", "#"],
        ]
        agent = LocalGreedyAgent()
        ctx = build_context(grid, (1, 1))
        assert agent.decide(ctx).move == "RIGHT"


# --------------------------------------------------------------------------- #
# 已访问格子惩罚
# --------------------------------------------------------------------------- #

class TestVisitedPenalty:

    def test_coin_still_wins_over_visited_penalty(self):
        """
        右侧 (2,3) 有金币且在 history 中，
        coin_value(50) >> visited_penalty(1)，仍应选 RIGHT。
        """
        agent = LocalGreedyAgent()
        ctx = build_context(GRID_OPEN_COIN, (2, 2), history=[{"pos": (2, 3)}])
        assert agent.decide(ctx).move == "RIGHT"

    def test_avoids_visited_when_unvisited_exists(self):
        """右侧已访问（无金币），下方未访问，应选 DOWN。"""
        grid = [
            ["#", "#", "#", "#"],
            ["#", " ", " ", "#"],
            ["#", " ", " ", "#"],
            ["#", "#", "#", "#"],
        ]
        agent = LocalGreedyAgent()
        ctx = build_context(grid, (1, 1), history=[{"pos": (1, 2)}])
        assert agent.decide(ctx).move == "DOWN"


# --------------------------------------------------------------------------- #
# 配置参数
# --------------------------------------------------------------------------- #

class TestConfig:

    def test_default_config_has_required_keys(self):
        for key in ("coin_value", "trap_penalty", "visited_penalty", "w_coin", "w_trap"):
            assert key in DEFAULT_CONFIG

    def test_zero_coin_value_still_returns_valid_move(self):
        """coin_value=0 时金币无吸引力，决策仍为合法方向。"""
        agent = LocalGreedyAgent(config={"coin_value": 0, "visited_penalty": 0})
        ctx = build_context(GRID_COIN_RIGHT, (1, 1))
        assert agent.decide(ctx).move in {"UP", "DOWN", "LEFT", "RIGHT", "STAY"}

    def test_high_trap_penalty_avoids_trap(self):
        """极高 trap_penalty 时，陷阱方向得分极低，必然不选 RIGHT。"""
        agent = LocalGreedyAgent(config={"trap_penalty": 10000})
        ctx = build_context(GRID_TRAP_RIGHT, (1, 1))
        assert agent.decide(ctx).move != "RIGHT"

    def test_custom_config_only_overrides_specified_keys(self):
        """传入自定义 config 时，只覆盖指定键，其余保持默认。"""
        agent = LocalGreedyAgent(config={"coin_value": 100})
        assert agent.cfg["coin_value"] == 100
        assert agent.cfg["trap_penalty"] == DEFAULT_CONFIG["trap_penalty"]


# --------------------------------------------------------------------------- #
# 详细演示（pytest -s 时可见控制台输出）
# --------------------------------------------------------------------------- #

def test_verbose_coin_right_demo():
    action = run_verbose_greedy_demo(GRID_COIN_RIGHT, (1, 1), label="右侧有金币，应选 RIGHT")
    assert action.move == "RIGHT"


def test_verbose_trap_right_demo():
    action = run_verbose_greedy_demo(GRID_TRAP_RIGHT, (1, 1), label="右侧有陷阱，应选 DOWN")
    assert action.move == "DOWN"


def test_verbose_triggered_trap_demo():
    action = run_verbose_greedy_demo(
        GRID_TRAP_RIGHT, (1, 1),
        label="陷阱已触发，不再扣分",
        triggered_traps={(1, 2)},
    )
    assert action.move in {"RIGHT", "DOWN"}


def test_verbose_visited_penalty_demo():
    grid = [
        ["#", "#", "#", "#"],
        ["#", " ", " ", "#"],
        ["#", " ", " ", "#"],
        ["#", "#", "#", "#"],
    ]
    action = run_verbose_greedy_demo(
        grid, (1, 1),
        label="右侧已访问，应选 DOWN",
        history=[{"pos": (1, 2)}],
    )
    assert action.move == "DOWN"


# --------------------------------------------------------------------------- #
# 直接运行入口
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    print("\n===== LocalGreedyAgent 手动演示 =====")
    run_verbose_greedy_demo(GRID_COIN_RIGHT, (1, 1), label="右侧有金币")
    run_verbose_greedy_demo(GRID_TRAP_RIGHT, (1, 1), label="右侧有陷阱")
    run_verbose_greedy_demo(
        GRID_TRAP_RIGHT, (1, 1),
        label="陷阱已触发",
        triggered_traps={(1, 2)},
    )
    run_verbose_greedy_demo(
        [["#","#","#","#"],["#"," "," ","#"],["#"," "," ","#"],["#","#","#","#"]],
        (1, 1), label="右侧已访问", history=[{"pos": (1, 2)}],
    )
    run_verbose_greedy_demo(GRID_ALL_WALLS, (1, 1), label="四周全是墙（STAY）")
