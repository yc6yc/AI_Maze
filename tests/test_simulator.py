"""
tests/test_simulator.py — 模拟器集成测试
负责人：角色4（评测）
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from eval.simulator import LocalSimulator
from agents.composite_agent import CompositeAgent
from agents.global_planner import GlobalPlannerAgent
from core.state import Action


MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "maze_15_15.json")


@pytest.mark.skipif(not os.path.exists(MAP_PATH), reason="缺少 maze_15_15.json")
def test_simulator_runs_without_crash():
    sim = LocalSimulator.from_json(MAP_PATH)
    agent = CompositeAgent()
    stats = sim.run(agent, max_rounds=300)
    assert isinstance(stats["rounds"], int)
    assert stats["rounds"] <= 300


@pytest.mark.skipif(not os.path.exists(MAP_PATH), reason="缺少 maze_15_15.json")
def test_global_planner_does_not_loop():
    sim = LocalSimulator.from_json(MAP_PATH)
    agent = GlobalPlannerAgent()
    stats = sim.run(agent, max_rounds=200)
    # 最多 200 回合结束，不因死循环挂起
    assert stats["rounds"] <= 200


def test_boss_bridge_receives_current_coins_and_win_continues():
    seen_coins = []

    def boss_handler(coins: int) -> int:
        seen_coins.append(coins)
        return 1

    sim = LocalSimulator(
        ground_truth=[["S", "G", "B", "E"]],
        skills=[],
        boss_hp=[1],
        coin_consumption=999,
        min_rounds=0,
        boss_battle_handler=boss_handler,
    )

    sim._step(Action(move="RIGHT"))
    sim._step(Action(move="RIGHT"))
    sim._step(Action(move="RIGHT"))

    assert seen_coins == [50]
    assert sim.ctx.player.coins == 50
    assert sim.stats()["won"] is True
    assert sim.ctx.history[1]["phase"] == "boss"
    assert sim.ctx.history[1]["boss_result"] is None
    assert sim.ctx.history[1]["steps"] == 1
    assert sim.ctx.history[1]["coin_step_ratio"] == 50
    assert sim.ctx.history[2]["phase"] == "boss"
    assert sim.ctx.history[2]["boss_result"] == 1
    assert sim.ctx.history[2]["steps"] == 1
    assert sim.ctx.history[2]["coin_step_ratio"] == 50
    assert sim.ctx.history[4]["steps"] == 2
    assert sim.ctx.history[4]["coin_step_ratio"] == 25


def test_boss_bridge_loss_returns_to_start():
    def boss_handler(coins: int) -> int:
        return 0

    sim = LocalSimulator(
        ground_truth=[["S", "B", "E"]],
        skills=[],
        boss_hp=[1],
        coin_consumption=999,
        min_rounds=0,
        boss_battle_handler=boss_handler,
    )

    sim._step(Action(move="RIGHT"))

    assert sim.ctx.player.pos == (0, 0)
    assert sim.ctx.player.coins == 0
    assert sim.stats()["won"] is False
    assert sim.stats()["boss_defeated"] == 0
    assert sim.ctx.history[0]["phase"] == "boss"
    assert sim.ctx.history[0]["boss_result"] is None
    assert sim.ctx.history[0]["steps"] == 0
    assert sim.ctx.history[1]["phase"] == "boss"
    assert sim.ctx.history[1]["boss_result"] == 0
    assert sim.ctx.history[1]["steps"] == 0
    assert sim.ctx.history[2]["steps"] == 0


def test_default_boss_bridge_pauses_until_external_result():
    sim = LocalSimulator(
        ground_truth=[["S", "B", "E"]],
        skills=[],
        boss_hp=[1],
        coin_consumption=999,
        min_rounds=0,
    )

    sim._step(Action(move="RIGHT"))

    assert sim.ctx.player.pos == (0, 1)
    assert sim.stats()["rounds"] == 0
    assert sim.stats()["won"] is False
    assert sim.ctx.history[0]["phase"] == "boss"
    assert sim.ctx.history[0]["boss_result"] is None
    assert sim.ctx.history[0]["steps"] == 0
