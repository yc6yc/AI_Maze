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
