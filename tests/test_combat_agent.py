"""
tests/test_combat_agent.py - CombatAgent 战斗逻辑单元测试

这个文件专门验证：
1. 什么时候应该进入战斗状态
2. 进入战斗后应当选择哪个技能
3. BOSS 战中 min_rounds / CoinConsumption 相关规则的本地演示
4. CombatAgent 只负责“决策”，不会直接修改金币或技能冷却

如果你想直接在控制台里看完整打怪过程，可以用下面两种方式运行：
1. pytest -s tests/test_combat_agent.py
2. python tests/test_combat_agent.py
"""
import os
import sys

import pytest

# 让测试文件可以直接导入项目根目录下的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.combat_agent import CombatAgent
from core.state import GameContext, MazeState, PlayerState, Skill


def format_skill_states(skills):
    """把技能列表格式化成适合控制台阅读的一行文字。"""
    return "；".join(
        f"技能{idx}(伤害={sk.damage}, 冷却={sk.cooldown}, 剩余冷却={sk.remaining_cd})"
        for idx, sk in enumerate(skills)
    )


def format_available_skills(player):
    """把当前可用技能整理成简短文字，方便打印战斗日志。"""
    available = player.available_skills()
    if not available:
        return "无"
    return "；".join(
        f"技能{idx}(伤害={sk.damage}, 冷却={sk.cooldown})"
        for idx, sk in available
    )


def build_context(
    grid,
    pos,
    coins=0,
    skill_specs=None,
    boss_defeated=None,
    coin_consumption=30,
    min_rounds=100,
):
    """
    构造一个最小可用的 GameContext，方便测试 CombatAgent。

    参数说明：
    - grid: 测试地图，直接传给 MazeState.from_full_map
    - pos: 玩家当前位置 (row, col)
    - coins: 当前金币数
    - skill_specs: 技能配置列表，每项格式为
      (damage, cooldown, remaining_cd)
    - boss_defeated: 已击败 BOSS 的记录列表
    - coin_consumption: 每次挑战失败后扣除的金币数
    - min_rounds: 单次 BOSS 挑战允许的最大攻击轮数

    说明：
    CombatAgent 实际只会用到位置、地图和技能信息，
    但这里仍然把 coins、boss_defeated 等字段一起补齐，
    这样测试环境会更接近真实的 GameContext。
    """
    # 根据完整地图创建 MazeState。
    # 在单元测试里直接给完整地图最方便，不需要模拟迷雾逐步揭露。
    maze = MazeState.from_full_map(grid)

    # 把简单的元组配置转成真正的 Skill 对象。
    # 例如 (50, 3, 0) 表示：伤害 50，冷却 3，当前可用。
    skills = [
        Skill(damage=damage, cooldown=cooldown, remaining_cd=remaining_cd)
        for damage, cooldown, remaining_cd in (skill_specs or [])
    ]

    # 构造玩家状态：位置、金币、技能都在这里挂上去。
    player = PlayerState(pos=pos, coins=coins, skills=skills)

    # 返回完整上下文对象，供 CombatAgent 读取。
    return GameContext(
        maze=maze,
        player=player,
        coin_consumption=coin_consumption,
        min_rounds=min_rounds,
        boss_defeated=list(boss_defeated or []),
    )


def run_verbose_battle_demo(ctx, boss_hps):
    """
    运行一个带详细控制台输出的战斗演示。

    这里不是完整游戏模拟器，而是专门为了观察 CombatAgent 的战斗决策：
    - 每回合打印 BOSS 血量
    - 打印当前金币
    - 打印哪些技能可用
    - 打印 CombatAgent 的决策结果
    - 打印造成的伤害和冷却变化
    """
    agent = CombatAgent()
    total_rounds = 0

    print("\n================ 战斗演示开始 ================")
    print(f"初始金币: {ctx.player.coins}")
    print(f"玩家位置: {ctx.player.pos}")
    print(f"初始技能状态: {format_skill_states(ctx.player.skills)}")

    for boss_index, start_hp in enumerate(boss_hps, start=1):
        boss_hp = start_hp
        print(f"\n---- 第 {boss_index} 只 BOSS 出现，初始血量 {start_hp} ----")

        # 这里顺手验证一下：演示场景确实处于战斗状态。
        assert agent.should_fight(ctx) is True

        while boss_hp > 0:
            total_rounds += 1
            print(f"\n[回合 {total_rounds}]")
            print(f"当前金币: {ctx.player.coins}")
            print(f"BOSS 当前血量: {boss_hp}")
            print(f"当前可用技能: {format_available_skills(ctx.player)}")

            action = agent.decide_combat(ctx)
            print(f"CombatAgent 决策: move={action.move}, use_skill={action.use_skill}")

            if action.use_skill is None:
                print("本回合没有可用技能，角色选择原地等待。")
            else:
                damage = ctx.player.use_skill(action.use_skill)
                boss_hp -= damage
                print(f"释放技能 {action.use_skill}，造成 {damage} 点伤害。")
                print(f"BOSS 受击后剩余血量: {max(boss_hp, 0)}")

            print(f"冷却推进前: {format_skill_states(ctx.player.skills)}")
            ctx.player.tick_cooldowns()
            print(f"冷却推进后: {format_skill_states(ctx.player.skills)}")

        ctx.boss_defeated.append(start_hp)
        print(f"第 {boss_index} 只 BOSS 已击败。")
        print(f"当前已击败 BOSS 列表: {ctx.boss_defeated}")

    print("\n================ 战斗演示结束 ================")
    print(f"总战斗回合数: {total_rounds}")
    print(f"战斗结束时金币: {ctx.player.coins}")
    print(f"最终技能状态: {format_skill_states(ctx.player.skills)}")

    return total_rounds


def run_boss_retry_penalty_demo(ctx, boss_hp):
    """
    打印“BOSS 战超过 min_rounds 后扣金币复活继续挑战”的完整过程。

    这里模拟的是你描述的规则：
    - 每次挑战同一个 BOSS，最多只能打 ctx.min_rounds 个攻击回合
    - 如果这次挑战没打死 BOSS，就扣 ctx.coin_consumption 金币
    - 扣完金币后继续挑战同一个 BOSS，BOSS 保留剩余血量
    - 直到 BOSS 被击败，或者金币扣到 0 / 不足以继续为止

    说明：
    这段流程是为了测试和演示 BOSS 战规则，所以写在测试文件里手工模拟。
    CombatAgent 本身仍然只负责“每一回合该放哪个技能”。
    """
    agent = CombatAgent()
    total_rounds = 0
    attempt = 0
    initial_boss_hp = boss_hp

    print("\n================ BOSS 重试扣金币演示开始 ================")
    print(f"初始金币: {ctx.player.coins}")
    print(f"BOSS 初始血量: {boss_hp}")
    print(f"单次挑战最大攻击回合数 min_rounds: {ctx.min_rounds}")
    print(f"每次挑战失败扣金币: {ctx.coin_consumption}")
    print(f"初始技能状态: {format_skill_states(ctx.player.skills)}")

    while boss_hp > 0 and ctx.player.coins > 0:
        attempt += 1
        print(f"\n---- 第 {attempt} 次挑战开始 ----")
        print(f"挑战开始前金币: {ctx.player.coins}")
        print(f"挑战开始前 BOSS 剩余血量: {boss_hp}")
        print(
            f"CombatAgent 预判本次能否在 {ctx.min_rounds} 轮内击败: "
            f"{agent.can_defeat_in_time(ctx, boss_hp)}"
        )

        for attack_round in range(1, ctx.min_rounds + 1):
            total_rounds += 1
            print(f"\n[第 {attempt} 次挑战 / 攻击回合 {attack_round}]")
            print(f"当前金币: {ctx.player.coins}")
            print(f"BOSS 当前血量: {boss_hp}")
            print(f"当前可用技能: {format_available_skills(ctx.player)}")

            action = agent.decide_combat(ctx)
            print(f"CombatAgent 决策: move={action.move}, use_skill={action.use_skill}")

            if action.use_skill is None:
                print("本回合没有可用技能，角色选择原地等待。")
            else:
                damage = ctx.player.use_skill(action.use_skill)
                boss_hp -= damage
                print(f"释放技能 {action.use_skill}，造成 {damage} 点伤害。")
                print(f"BOSS 受击后剩余血量: {max(boss_hp, 0)}")

            if boss_hp <= 0:
                ctx.boss_defeated.append(initial_boss_hp)
                print("BOSS 已被击败，本轮挑战成功。")
                break

            print(f"冷却推进前: {format_skill_states(ctx.player.skills)}")
            ctx.player.tick_cooldowns()
            print(f"冷却推进后: {format_skill_states(ctx.player.skills)}")

        if boss_hp <= 0:
            break

        ctx.player.coins -= ctx.coin_consumption
        print(f"\n本次挑战在 {ctx.min_rounds} 轮内未击败 BOSS。")
        print(f"扣除 {ctx.coin_consumption} 金币后复活，继续挑战同一个 BOSS。")
        print(f"扣费后金币: {ctx.player.coins}")

        if ctx.player.coins <= 0:
            print("金币已扣完，无法继续复活，判定挑战失败。")
            break

    print("\n================ BOSS 重试扣金币演示结束 ================")
    print(f"总攻击回合数: {total_rounds}")
    print(f"最终金币: {ctx.player.coins}")
    print(f"BOSS 最终剩余血量: {max(boss_hp, 0)}")
    print(f"已击败 BOSS 列表: {ctx.boss_defeated}")

    return {
        "won": boss_hp <= 0,
        "attempts": attempt,
        "total_rounds": total_rounds,
        "remaining_boss_hp": max(boss_hp, 0),
        "coins": ctx.player.coins,
    }


@pytest.mark.parametrize(
    ("grid", "pos"),
    [
        (
            [
                ["#", "#", "#"],
                ["#", "B", "#"],
                ["#", "#", "#"],
            ],
            (1, 1),
        ),
        (
            [
                ["#", "#", "#", "#"],
                ["#", " ", "B", "#"],
                ["#", " ", " ", "#"],
                ["#", "#", "#", "#"],
            ],
            (1, 1),
        ),
    ],
)
def test_should_fight_when_player_is_on_or_next_to_boss(grid, pos):
    """
    测试 should_fight() 的两个典型触发条件：
    1. 玩家正站在 BOSS 格子上
    2. 玩家与 BOSS 上下左右相邻

    这两个场景都应该进入战斗状态。
    """
    ctx = build_context(
        grid=grid,
        pos=pos,
        coins=120,
        skill_specs=[(20, 2, 0)],
        boss_defeated=[90],
    )
    assert CombatAgent().should_fight(ctx) is True


def test_should_not_fight_when_no_boss_is_visible():
    """
    如果当前位置和四邻域都没有 BOSS，
    should_fight() 应该返回 False。

    这里故意保留金币和已击败 BOSS 记录，
    用来说明这些信息不会影响 should_fight() 的判断。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#", "#"],
            ["#", " ", " ", "#"],
            ["#", " ", " ", "#"],
            ["#", "#", "#", "#"],
        ],
        pos=(1, 1),
        coins=80,
        skill_specs=[(15, 1, 0)],
        boss_defeated=[100, 70],
    )
    assert CombatAgent().should_fight(ctx) is False


def test_decide_combat_chooses_highest_damage_ready_skill():
    """
    测试 decide_combat() 是否会从“当前可用技能”中，
    选出伤害最高的那一个。

    本例中：
    - 技能 0：伤害 25，可用
    - 技能 1：伤害 80，但仍在冷却，不能选
    - 技能 2：伤害 50，可用

    因此最终应该选择技能 2，而不是技能 1。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=250,
        skill_specs=[
            (25, 2, 0),
            (80, 5, 3),
            (50, 1, 0),
        ],
        boss_defeated=[120],
    )

    action = CombatAgent().decide_combat(ctx)

    # CombatAgent 的设计是战斗时原地输出，不移动。
    assert action.move == "STAY"

    # 在可用技能中，技能 2 的伤害最高，因此应选择编号 2。
    assert action.use_skill == 2

    # CombatAgent 只负责“做决定”，不会直接改金币。
    assert ctx.player.coins == 250

    # CombatAgent 也不会自己推进冷却或消耗技能；
    # 真正的冷却变化应由模拟器或执行层负责。
    assert [sk.remaining_cd for sk in ctx.player.skills] == [0, 3, 0]


def test_decide_combat_waits_when_all_skills_are_on_cooldown():
    """
    如果所有技能都还在冷却中，
    CombatAgent 应该返回“原地等待，不放技能”。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=60,
        skill_specs=[
            (30, 2, 1),
            (55, 4, 2),
        ],
        boss_defeated=[],
    )

    action = CombatAgent().decide_combat(ctx)

    assert action.move == "STAY"
    assert action.use_skill is None


def test_can_defeat_in_time_respects_boss_battle_round_limit():
    """
    验证 can_defeat_in_time() 会参考 GameContext.min_rounds。

    这个例子里只有一个无冷却技能，每回合固定造成 30 伤害。
    - min_rounds = 2 时，最多打出 60 伤害
    - 因此 boss_hp = 60 可以击败，boss_hp = 70 就不行
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=10,
        skill_specs=[(30, 0, 0)],
        boss_defeated=[],
        coin_consumption=5,
        min_rounds=2,
    )

    agent = CombatAgent()

    assert agent.can_defeat_in_time(ctx, boss_hp=60) is True
    assert agent.can_defeat_in_time(ctx, boss_hp=70) is False


def test_memory_planner_replans_after_first_failed_attempt():
    """
    记忆逻辑：当第一轮挑战在 min_rounds 内失败后，
    第二轮应基于失败序列重规划，而不是机械重复。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=100,
        # 两个技能都无冷却，默认贪心第一轮会连续放技能0
        skill_specs=[
            (9, 0, 0),
            (8, 0, 0),
        ],
        boss_defeated=[],
        coin_consumption=5,
        min_rounds=2,
    )
    agent = CombatAgent(enable_memory=True)

    # 第一次挑战（2回合），记录到失败序列
    first_round_actions = []
    for _ in range(ctx.min_rounds):
        action = agent.decide_combat_with_memory(ctx)
        first_round_actions.append(action.use_skill)
        if action.use_skill is not None:
            ctx.player.use_skill(action.use_skill)
        ctx.player.tick_cooldowns()

    # 第二次挑战第一回合：应优先避开第一轮同回合使用过的技能
    action_second_attempt = agent.decide_combat_with_memory(ctx)
    assert first_round_actions[0] == 0
    assert action_second_attempt.use_skill == 1


def test_memory_planner_accumulates_failed_sequences():
    """
    记忆逻辑应累计多次失败序列参与重规划。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=100,
        skill_specs=[
            (10, 1, 0),
            (9, 1, 0),
            (8, 1, 0),
        ],
        boss_defeated=[],
        coin_consumption=5,
        min_rounds=1,
    )
    agent = CombatAgent(enable_memory=True)

    # 第1次失败：回合1通常选技能0
    a1 = agent.decide_combat_with_memory(ctx).use_skill
    if a1 is not None:
        ctx.player.use_skill(a1)
    ctx.player.tick_cooldowns()

    # 第2次失败开始：应避开技能0，优先技能1
    a2 = agent.decide_combat_with_memory(ctx).use_skill
    if a2 is not None:
        ctx.player.use_skill(a2)
    ctx.player.tick_cooldowns()

    # 第3次失败开始：应继续避开前两次（0/1），优先技能2
    a3 = agent.decide_combat_with_memory(ctx).use_skill
    assert a1 == 0
    assert a2 == 1
    assert a3 == 2


def test_verbose_combat_flow_prints_full_battle_log():
    """
    这个测试除了断言结果，还会把完整打怪过程打印到控制台。

    设计这个场景时，故意把技能冷却安排成会出现“等待回合”，
    这样能更直观看到 CombatAgent 在不同回合的决策变化。
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=180,
        # 技能 0：高伤害、长冷却，初始可用
        # 技能 1：较低伤害、也有冷却，初始不可用
        skill_specs=[
            (70, 4, 0),
            (25, 3, 3),
        ],
        boss_defeated=[],
    )

    rounds = run_verbose_battle_demo(ctx, boss_hps=[90, 60])

    # 断言演示最终确实打完了两只 BOSS。
    assert ctx.boss_defeated == [90, 60]

    # 这个演示场景下，战斗过程应稳定落在 5 回合。
    assert rounds == 5

    # CombatAgent 本身不处理金币变化，因此金币应保持不变。
    assert ctx.player.coins == 180


def test_boss_retry_penalty_flow_prints_failure_log():
    """
    打印并验证“BOSS 战超过最大攻击回合数后扣 5 金币复活继续打，
    直到金币扣完判定失败”的过程。

    这个场景里：
    - 单次挑战只能攻击 2 回合
    - 每回合固定造成 30 伤害
    - BOSS 初始血量 150
    - 初始金币 10，每次失败扣 5

    因此：
    - 第 1 次挑战后，BOSS 还剩 90，金币从 10 扣到 5
    - 第 2 次挑战后，BOSS 还剩 30，金币从 5 扣到 0
    - 金币扣完，判定失败
    """
    ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=10,
        skill_specs=[(30, 0, 0)],
        boss_defeated=[],
        coin_consumption=5,
        min_rounds=2,
    )
    result = run_boss_retry_penalty_demo(ctx, boss_hp=150)

    assert result["won"] is False
    assert result["attempts"] == 2
    assert result["total_rounds"] == 4
    assert result["remaining_boss_hp"] == 30
    assert result["coins"] == 0


if __name__ == "__main__":
    demo_ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=180,
        skill_specs=[
            (70, 4, 0),
            (25, 3, 3),
        ],
        boss_defeated=[],
    )
    run_verbose_battle_demo(demo_ctx, boss_hps=[90, 60])
    retry_demo_ctx = build_context(
        grid=[
            ["#", "#", "#"],
            ["#", "B", "#"],
            ["#", "#", "#"],
        ],
        pos=(1, 1),
        coins=10,
        skill_specs=[(30, 0, 0)],
        boss_defeated=[],
        coin_consumption=5,
        min_rounds=2,
    )
    run_boss_retry_penalty_demo(retry_demo_ctx, boss_hp=150)
