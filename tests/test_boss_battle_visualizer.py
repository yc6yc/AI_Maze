import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.state import GameContext, MazeState, PlayerState, Skill
from viz.boss_battle_visualizer import (
    battle_result_from_frames,
    ensure_boss_assets_ready,
    make_visual_boss_battle_handler,
    render_boss_battle_frame,
    simulate_boss_battle_frames,
)


def build_ctx(skill_specs, coins=20, min_rounds=3, coin_consumption=5):
    maze = MazeState.from_full_map(
        [
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ]
    )
    player = PlayerState(
        pos=(1, 1),
        coins=coins,
        skills=[Skill(damage=dmg, cooldown=cd, remaining_cd=rem) for dmg, cd, rem in skill_specs],
    )
    return GameContext(
        maze=maze,
        player=player,
        coin_consumption=coin_consumption,
        min_rounds=min_rounds,
    )


def test_simulate_boss_battle_frames_records_multi_boss_sequence():
    ctx = build_ctx([(8, 0, 0)], coins=10, min_rounds=3, coin_consumption=5)
    frames = simulate_boss_battle_frames(ctx, [11, 13])

    assert frames
    assert frames[-1].defeated is True
    assert frames[-1].boss_index == 2
    assert frames[-1].boss_hp == 0
    assert any(frame.boss_index == 1 for frame in frames)
    assert any(frame.boss_index == 2 for frame in frames)


def test_simulate_boss_battle_frames_records_retry_and_failure():
    ctx = build_ctx([(30, 0, 0)], coins=10, min_rounds=2, coin_consumption=5)
    frames = simulate_boss_battle_frames(ctx, [150])

    assert any(frame.retry for frame in frames)
    assert frames[-1].failed is True
    assert frames[-1].coins == 0
    assert frames[-1].boss_hp == 30


def test_render_boss_battle_frame_headless():
    ctx = build_ctx([(8, 0, 0)], coins=10, min_rounds=3, coin_consumption=5)
    frame = simulate_boss_battle_frames(ctx, [11])[0]
    ax = render_boss_battle_frame(frame)
    assert ax is not None


def test_battle_result_from_frames_win():
    ctx = build_ctx([(8, 0, 0)], coins=10, min_rounds=3, coin_consumption=5)
    frames = simulate_boss_battle_frames(ctx, [11, 13])
    assert battle_result_from_frames(frames, 2) == 1


def test_visual_boss_battle_handler_returns_win(monkeypatch):
    monkeypatch.setattr(
        "viz.boss_battle_visualizer.render_boss_battle_window",
        lambda frames, fps=3: None,
    )
    handler = make_visual_boss_battle_handler(
        skill_specs=[[8, 0]],
        boss_hps=[11, 13],
        min_rounds=3,
        coin_consumption=5,
        fps=10,
    )
    assert handler(0) == 1


def test_simulated_frames_have_timing_and_asset_prep():
    ensure_boss_assets_ready()
    ctx = build_ctx([(8, 0, 0)], coins=10, min_rounds=3, coin_consumption=5)
    frames = simulate_boss_battle_frames(ctx, [11])
    assert all(frame.duration_ms > 0 for frame in frames)
