from agents.combat_agent import CombatAgent
from core.state import GameContext, MazeState, PlayerState, Skill


def test_combat_agent_uses_highest_ready_damage() -> None:
    maze = MazeState(
        rows=1,
        cols=2,
        fog_map=[["S", "B"]],
        start=(0, 0),
        end=(0, 1),
    )
    player = PlayerState(pos=(0, 0), skills=[Skill(5, 0), Skill(12, 2), Skill(20, 3, remaining_cooldown=1)])
    ctx = GameContext(maze=maze, player=player, boss_healths=[20], min_rounds=3, coin_consumption=0)
    action = CombatAgent().decide(ctx)
    assert action.use_skill == 1


def test_can_defeat_in_time() -> None:
    maze = MazeState(rows=1, cols=1, fog_map=[["B"]], start=(0, 0), end=(0, 0))
    player = PlayerState(pos=(0, 0), skills=[Skill(10, 0)])
    ctx = GameContext(maze=maze, player=player, boss_healths=[20], min_rounds=2, coin_consumption=0)
    assert CombatAgent().can_defeat_in_time(ctx, 20)
