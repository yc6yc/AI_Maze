import pytest

from core.state import Action, Skill
from eval.simulator import LocalSimulator, simulate_boss_battle


def test_simulator_reveals_initial_fov_and_collects_coin() -> None:
    data = {
        "maze": [["#", "#", "#"], ["#", "S", "C"], ["#", "#", "E"]],
        "B": [],
        "PlayerSkills": [],
        "minRouds": 2,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)
    assert sim.ctx.maze.fog_map[1][2] == "C"
    sim.step(Action(move="RIGHT"))
    assert sim.ctx.player.coins == 50
    assert sim.ground_truth[1][2] == " "


def test_exit_requires_boss_defeated() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "E", "#"], ["#", "B", " ", "#"], ["#", "#", "#", "#"]],
        "B": [10],
        "PlayerSkills": [[10, 0]],
        "minRouds": 1,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)
    sim.step(Action(move="RIGHT"))
    assert sim.ctx.result == "running"
    assert sim.ctx.last_event["type"] == "exit_locked"


def test_boss_event_contains_round_skill_and_damage_details() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [25],
        "PlayerSkills": [[10, 0], [7, 1]],
        "minRouds": 3,
        "CoinConsumption": 5,
    }
    sim = LocalSimulator(data)
    state = sim.step(Action(move="RIGHT"))
    event = state["boss_event"]
    assert event["result"] == "win"
    assert event["initial_health"] == 25
    assert event["remaining_health"] == 0
    assert event["total_damage"] == 25
    assert event["rounds_used"] == 3
    assert event["rounds"][0]["skill_index"] == 0
    assert event["rounds"][0]["damage"] == 10
    assert event["rounds"][0]["hp_before"] == 25
    assert event["rounds"][0]["hp_after"] == 15
    assert state["boss_events"][-1]["maze_step"] == state["step"]


def test_boss_skill_cooldown_lasts_full_battle_rounds() -> None:
    battle = simulate_boss_battle([Skill(12, 4)], health=24, min_rounds=6)

    assert battle["result"] == "win"
    assert [round_info["action"] for round_info in battle["rounds"]] == [
        "attack",
        "wait",
        "wait",
        "wait",
        "wait",
        "attack",
    ]
    assert [round_info["cooldowns_before"][0] for round_info in battle["rounds"]] == [0, 4, 3, 2, 1, 0]
    assert [round_info["cooldowns_after"][0] for round_info in battle["rounds"]] == [4, 3, 2, 1, 0, 4]
    assert battle["rounds"][0]["damage"] == 12
    assert battle["rounds"][5]["damage"] == 12
    assert battle["final_cooldowns"] == [4]


def test_boss_battle_uses_cooldown_aware_skill_plan() -> None:
    battle = simulate_boss_battle([Skill(100, 100), Skill(60, 1)], health=200, min_rounds=3)

    assert battle["result"] == "win"
    assert [round_info["skill_index"] for round_info in battle["rounds"]] == [1, 0, 1]
    assert [round_info["damage"] for round_info in battle["rounds"]] == [60, 100, 60]
    assert battle["total_damage"] == 200


def test_revealed_boss_sequence_planner_saves_big_skill_for_later_boss() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        "B": [1, 100],
        "PlayerSkills": [[100, 5], [1, 0]],
        "minRouds": 2,
        "CoinConsumption": 5,
    }
    sim = LocalSimulator(data)
    sim.ctx.player.coins = 10

    state = sim.step(Action(move="RIGHT"))
    first, second, third, fourth = state["boss_events"]
    assert first["planning_mode"] == "current_boss"
    assert first["rounds"][0]["skill_index"] == 0
    assert second["result"] == "lose"
    assert second["revived"] is True

    assert third["planning_mode"] == "known_sequence"
    assert third["planned_boss_orders"] == [1, 2]
    assert third["planned_boss_healths"] == [1, 100]
    assert third["rounds"][0]["skill_index"] == 1
    assert fourth["planning_mode"] == "known_sequence"
    assert fourth["rounds"][0]["skill_index"] == 0
    assert state["boss_defeated"] is True


def test_known_boss_sequence_dp_avoids_greedy_overkill() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [5, 9],
        "PlayerSkills": [[9, 5], [5, 0]],
        "minRouds": 2,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data, boss_healths_revealed=True)

    state = sim.step(Action(move="RIGHT"))
    first, second = state["boss_events"]

    assert first["planning_mode"] == "known_sequence"
    assert first["planned_boss_healths"] == [5, 9]
    assert first["rounds"][0]["skill_index"] == 1
    assert second["rounds"][0]["skill_index"] == 0
    assert state["boss_defeated"] is True


def test_manual_boss_stops_at_b_and_waits_for_live_health_input() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#", "#"], ["#", "S", "B", " ", "E", "#"], ["#", "#", "#", "#", "#", "#"]],
        "PlayerSkills": [[100, 4], [1, 0]],
        "minRouds": 6,
        "CoinConsumption": 5,
    }
    sim = LocalSimulator(data, boss_source="manual")

    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True
    assert state["pending_boss_pos"] == [1, 2]
    assert state["boss_events"] == []

    state = sim.submit_manual_boss_health(1)
    assert state["awaiting_boss_input"] is True
    assert state["boss_events"][0]["initial_health"] == 1
    assert state["boss_events"][0]["result"] == "win"

    state = sim.submit_manual_boss_health(100, reveal_all=True)
    assert state["boss_events"][-1]["initial_health"] == 100
    assert state["boss_events"][-1]["planning_mode"] == "known_sequence"
    assert state["awaiting_boss_input"] is True


def test_boss_sequence_uses_min_rounds_as_total_round_budget() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#", "#", "#"], ["#", "S", "B", " ", "B", "E", "#"], ["#", "#", "#", "#", "#", "#", "#"]],
        "B": [12, 12],
        "PlayerSkills": [[12, 4]],
        "minRouds": 5,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)

    state = sim.step(Action(move="RIGHT"))
    first, second = state["boss_events"]
    assert first["result"] == "win"
    assert first["maze_step"] == state["step"]
    assert first["final_cooldowns"] == [4]
    assert first["round_limit"] == 5
    assert first["total_rounds_used"] == 1

    assert second["result"] == "lose"
    assert second["maze_step"] == state["step"]
    assert second["round_limit"] == 4
    assert second["rounds"][0]["action"] == "wait"
    assert second["rounds"][0]["cooldowns_before"] == [4]
    assert second["total_rounds_used"] == 5
    assert state["defeated_boss_count"] == 1
    assert state["boss_defeated"] is False
    assert state["done"] is True
    assert state["result"] == "lose"


def test_snapshot_only_exposes_encountered_boss_healths() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        "B": [12, 12, 99],
        "PlayerSkills": [[12, 4]],
        "minRouds": 5,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)

    initial = sim.snapshot(include_history=False)
    assert initial["all_boss_healths_revealed"] is False
    assert initial["known_boss_healths"] == []
    assert initial["current_boss_health"] is None

    state = sim.step(Action(move="RIGHT"))
    assert state["known_boss_healths"] == [
        {"order": 1, "health": 12, "status": "defeated"},
        {"order": 2, "health": 12, "status": "current"},
    ]
    assert state["current_boss_health"] == {"order": 2, "health": 12, "status": "current"}
    assert all(item["health"] != 99 for item in state["known_boss_healths"])
    assert "boss_health_sequence" not in state


def test_boss_sequence_can_win_within_total_round_budget() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#", "#", "#"], ["#", "S", "B", " ", "B", "E", "#"], ["#", "#", "#", "#", "#", "#", "#"]],
        "B": [10, 10],
        "PlayerSkills": [[10, 0]],
        "minRouds": 2,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)

    state = sim.step(Action(move="RIGHT"))
    first, second = state["boss_events"]
    assert first["result"] == "win"
    assert first["round_limit"] == 2
    assert first["total_rounds_used"] == 1
    assert second["result"] == "win"
    assert second["round_limit"] == 1
    assert second["total_rounds_used"] == 2
    assert state["defeated_boss_count"] == 2
    assert state["boss_defeated"] is True
    assert sim.ground_truth[1][2] == " "
    assert sim.ground_truth[1][4] == " "


def test_missing_map_boss_array_enters_manual_live_input_mode() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "PlayerSkills": [[10, 0]],
        "minRouds": 1,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)
    state = sim.step(Action(move="RIGHT"))
    assert state["boss_health_source"] == "manual"
    assert state["awaiting_boss_input"] is True


def test_manual_finish_input_clears_current_b_and_allows_maze_to_continue() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        "PlayerSkills": [[50, 0]],
        "minRouds": 3,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data, boss_source="manual")

    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True

    state = sim.submit_manual_boss_health(20)
    assert state["boss_events"][-1]["result"] == "win"
    assert state["awaiting_boss_input"] is True

    state = sim.finish_manual_boss_input()
    assert state["awaiting_boss_input"] is False
    assert sim.ground_truth[1][2] == " "

    state = sim.step(Action(move="RIGHT"))
    assert state["result"] == "win"


def test_manual_boss_healths_are_read_in_live_input_order() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#", "#"], ["#", "S", "B", "B", "E", "#"], ["#", "#", "#", "#", "#", "#"]],
        "PlayerSkills": [[100, 0]],
        "minRouds": 2,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data, boss_source="manual")
    assert sim.ctx.boss_healths == []
    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True
    state = sim.submit_manual_boss_health(30)
    assert state["boss_events"][-1]["initial_health"] == 30
    sim.finish_manual_boss_input()

    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True
    state = sim.submit_manual_boss_health(60)
    first, second = state["boss_events"]
    assert [first["initial_health"], second["initial_health"]] == [30, 60]
    assert sim.snapshot(include_history=False)["encountered_bosses"] == 2
    assert sim.snapshot(include_history=False)["defeated_boss_count"] == 2


def test_manual_failed_boss_revive_requires_replan_of_known_sequence() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        "PlayerSkills": [[10, 0]],
        "minRouds": 2,
        "CoinConsumption": 15,
    }
    sim = LocalSimulator(data, boss_source="manual")
    sim.ctx.player.coins = 40

    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True

    state = sim.submit_manual_boss_health(10)
    assert state["boss_events"][-1]["result"] == "win"
    assert state["defeated_boss_count"] == 1
    assert state["manual_boss_replan_required"] is False

    state = sim.submit_manual_boss_health(20)
    failed = state["boss_events"][-1]
    assert failed["result"] == "lose"
    assert failed["revived"] is True
    assert failed["revive_cost"] == 15
    assert failed["value_before"] == 40
    assert failed["value_after"] == 25
    assert failed["manual_input_required_after_revive"] is True
    assert failed["manual_replan_required_after_revive"] is True
    assert failed["boss_sequence_reset_on_revive"] is True
    assert failed["restart_boss_order"] == 1
    assert state["awaiting_boss_input"] is True
    assert state["manual_boss_replan_required"] is True
    assert state["value"] == 25
    assert state["defeated_boss_count"] == 0
    assert sim.boss_health_sequence == [10, 20]

    with pytest.raises(ValueError):
        sim.submit_manual_boss_health(5)

    state = sim.replan_manual_boss_sequence()
    replanned = state["boss_events"][-1]
    assert replanned["result"] == "lose"
    assert replanned["manual_replan_required_after_revive"] is True
    assert state["awaiting_boss_input"] is True
    assert state["manual_boss_replan_required"] is True
    assert state["value"] == 10
    assert state["defeated_boss_count"] == 0


def test_map_boss_array_is_isolated_from_manual_healths() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [45],
        "PlayerSkills": [[100, 0]],
        "minRouds": 1,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data, boss_healths=[0, -10])
    event = sim.step(Action(move="RIGHT"))["boss_event"]
    assert event["initial_health"] == 45
    assert event["encounter_order"] == 1
    assert sim.snapshot(include_history=False)["boss_health_source"] == "map"


def test_manual_boss_source_can_override_map_boss_array() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [45],
        "PlayerSkills": [[100, 0]],
        "minRouds": 2,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data, boss_source="manual")
    state = sim.step(Action(move="RIGHT"))
    assert state["awaiting_boss_input"] is True
    state = sim.submit_manual_boss_health(20)
    assert [event["initial_health"] for event in state["boss_events"]] == [20]
    assert state["boss_health_source"] == "manual"
    assert state["defeated_boss_count"] == 1


def test_single_b_cell_can_spawn_multiple_bosses_from_health_sequence() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [20, 40, 60, 80],
        "PlayerSkills": [[100, 0]],
        "minRouds": 4,
        "CoinConsumption": 0,
    }
    sim = LocalSimulator(data)

    state = sim.step(Action(move="RIGHT"))
    first, second, third, fourth = state["boss_events"]
    assert first["encounter_order"] == 1
    assert first["initial_health"] == 20
    assert [second["initial_health"], third["initial_health"], fourth["initial_health"]] == [40, 60, 80]
    assert {event["maze_step"] for event in state["boss_events"]} == {state["step"]}
    assert sim.ground_truth[1][2] == " "
    assert sim.snapshot(include_history=False)["boss_defeated"]


def test_failed_boss_attempts_auto_revive_until_value_exhausted() -> None:
    data = {
        "maze": [["#", "#", "#", "#"], ["#", "S", "B", "E"], ["#", "#", "#", "#"]],
        "B": [100],
        "PlayerSkills": [[10, 0]],
        "minRouds": 1,
        "CoinConsumption": 15,
    }
    sim = LocalSimulator(data)
    sim.ctx.player.coins = 40

    state = sim.step(Action(move="RIGHT"))
    first, second, third = state["boss_events"]
    assert first["result"] == "lose"
    assert first["attempt"] == 1
    assert first["coins_before"] == 40
    assert first["value_before"] == 40
    assert first["revived"] is True
    assert first["revive_cost"] == 15
    assert first["coins_after"] == 25
    assert first["value_after"] == 25
    assert first["revive"]["used"] is True
    assert first["revive"]["cost"] == 15

    assert second["attempt"] == 2
    assert second["coins_before"] == 25
    assert second["coins_after"] == 10
    assert second["revived"] is True

    assert third["attempt"] == 3
    assert third["coins_before"] == 10
    assert third["coins_after"] == 0
    assert third["revived"] is False
    assert third["revive_cost"] == 10
    assert state["boss_event"]["attempt"] == 3
    assert state["done"] is True
    assert state["result"] == "lose"


def test_boss_revive_restarts_sequence_from_first_boss_until_success() -> None:
    data = {
        "maze": [["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        "B": [10, 50],
        "PlayerSkills": [[50, 0], [10, 0]],
        "minRouds": 2,
        "CoinConsumption": 5,
    }
    sim = LocalSimulator(data)
    sim.ctx.player.coins = 20
    sim.ctx.player.skills[0].remaining_cooldown = 4

    state = sim.step(Action(move="RIGHT"))
    first, second, third, fourth = state["boss_events"]
    assert [(event["encounter_order"], event["attempt"], event["result"]) for event in state["boss_events"]] == [
        (1, 1, "win"),
        (2, 1, "lose"),
        (1, 2, "win"),
        (2, 2, "win"),
    ]
    assert first["total_rounds_used"] == 1
    assert second["revived"] is True
    assert second["coins_before"] == 20
    assert second["coins_after"] == 15
    assert second["boss_sequence_reset_on_revive"] is True
    assert second["restart_boss_order"] == 1
    assert second["final_cooldowns"] == [2, 0]
    assert second["skill_cooldowns_reset_on_revive"] is True
    assert second["cooldowns_after_revive"] == [0, 0]
    assert second["boss_healths_revealed_on_revive"] is True
    assert second["known_boss_healths_after_revive"] == [
        {"order": 1, "health": 10, "status": "current"},
        {"order": 2, "health": 50, "status": "known"},
    ]
    assert third["total_rounds_before"] == 0
    assert third["round_limit"] == 2
    assert third["coins_before"] == 15
    assert [skill["initial_remaining_cooldown"] for skill in third["skills"]] == [0, 0]
    assert fourth["total_rounds_used"] == 2
    assert state["all_boss_healths_revealed"] is True
    assert state["known_boss_healths"] == [
        {"order": 1, "health": 10, "status": "defeated"},
        {"order": 2, "health": 50, "status": "defeated"},
    ]
    assert state["boss_event"]["result"] == "win"
    assert state["boss_defeated"] is True
    assert state["defeated_boss_count"] == 2
    assert state["value"] == 15
