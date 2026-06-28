from agents.local_greedy_policy import LocalGreedyAgent
from core.state import GameContext, MazeState, PlayerState


def test_local_greedy_moves_to_adjacent_coin() -> None:
    maze = MazeState(
        rows=3,
        cols=3,
        fog_map=[["#", "#", "#"], ["#", "S", "C"], ["#", "#", "#"]],
        start=(1, 1),
        end=(1, 2),
    )
    ctx = GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[], min_rounds=0, coin_consumption=0)
    agent = LocalGreedyAgent()
    action = agent.decide(ctx)
    assert action.move == "RIGHT"


def test_local_greedy_fallback_moves_when_no_positive_target() -> None:
    maze = MazeState(
        rows=3,
        cols=3,
        fog_map=[["#", "#", "#"], ["#", "S", " "], ["#", "#", "#"]],
        start=(1, 1),
        end=(1, 2),
    )
    ctx = GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[], min_rounds=0, coin_consumption=0)
    agent = LocalGreedyAgent()
    action = agent.decide(ctx)
    assert action.move == "RIGHT"


def test_local_greedy_rushes_visible_boss_before_coin() -> None:
    maze = MazeState(
        rows=3,
        cols=5,
        fog_map=[["#", "#", "#", "#", "#"], ["#", "S", "B", "C", "#"], ["#", "#", "#", "#", "#"]],
        start=(1, 1),
        end=(1, 4),
    )
    ctx = GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[10], min_rounds=1, coin_consumption=0)
    agent = LocalGreedyAgent()
    action = agent.decide(ctx)
    assert action.move == "RIGHT"


def test_local_greedy_rushes_exit_after_known_boss_defeated() -> None:
    maze = MazeState(
        rows=3,
        cols=5,
        fog_map=[["#", "#", "#", "#", "#"], ["#", "S", "B", "E", "#"], ["#", "#", "#", "#", "#"]],
        start=(1, 1),
        end=(1, 3),
        defeated_bosses={(1, 2)},
    )
    ctx = GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[10], min_rounds=1, coin_consumption=0)
    agent = LocalGreedyAgent()
    agent.known_bosses.add((1, 2))
    action = agent.decide(ctx)
    assert action.move == "RIGHT"


def test_local_greedy_moves_to_frontier_when_only_unknown_space_remains() -> None:
    maze = MazeState(
        rows=3,
        cols=4,
        fog_map=[["#", "#", "#", "#"], ["#", "S", " ", None], ["#", "#", "#", "#"]],
        start=(1, 1),
        end=(1, 3),
    )
    ctx = GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[], min_rounds=0, coin_consumption=0)
    agent = LocalGreedyAgent()
    action = agent.decide(ctx)
    assert action.move == "RIGHT"
