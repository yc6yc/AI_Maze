from agents.ai_maze_composite import AIMazeCompositeAgent
from agents.ai_maze_global_greedy import AIMazeGlobalGreedyAgent
from agents.ai_maze_global_planner import AIMazeGlobalPlannerAgent
from agents.composite_agent import make_agent
from agents.local_3x3_greedy import Local3x3GreedyAgent
from core.state import GameContext, MazeState, PlayerState


def simple_ctx() -> GameContext:
    maze = MazeState(
        rows=3,
        cols=4,
        fog_map=[["#", "#", "#", "#"], ["#", "S", "C", "E"], ["#", "#", "#", "#"]],
        start=(1, 1),
        end=(1, 3),
    )
    return GameContext(maze=maze, player=PlayerState(pos=(1, 1)), boss_healths=[], min_rounds=0, coin_consumption=0)


def test_local_3x3_moves_to_adjacent_coin() -> None:
    assert Local3x3GreedyAgent().decide(simple_ctx()).move == "RIGHT"


def test_ai_maze_global_agents_can_decide() -> None:
    ctx = simple_ctx()
    assert AIMazeGlobalGreedyAgent().decide(ctx).move == "RIGHT"
    assert AIMazeGlobalPlannerAgent().decide(ctx).move in {"RIGHT", "STAY"}
    assert AIMazeCompositeAgent().decide(ctx).move == "RIGHT"


def test_make_agent_registers_ai_maze_algorithms() -> None:
    assert isinstance(make_agent("local_3x3", {}), Local3x3GreedyAgent)
    assert isinstance(make_agent("ai_global_greedy", {}), AIMazeGlobalGreedyAgent)
    assert isinstance(make_agent("ai_global_planner", {}), AIMazeGlobalPlannerAgent)
    assert isinstance(make_agent("ai_composite", {}), AIMazeCompositeAgent)
