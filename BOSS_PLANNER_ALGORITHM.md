# Boss 技能规划算法文档

本文档只描述“如何规划打 Boss 的技能释放顺序”。完整 Boss 战状态机、自动/手动输入、复活和前端交互请看：

```text
BOSS_BATTLE_LOGIC.md
```

当前技能规划核心代码位于：

```text
eval/simulator.py
```

主要函数：

```python
simulate_boss_battle()
_plan_boss_battle()
_plan_boss_sequence()
_boss_planner_choices()
_conservative_plan_tiebreak()
_estimate_future_damage_capacity()
_advance_boss_cooldowns()
_build_boss_rounds()
```

## 1. 算法目标

Boss 技能规划的目标是：

1. 在 `minRouds` 总回合限制内击败 Boss。
2. 正确处理每个技能的冷却回合。
3. 尽量减少复活，尤其是 `CoinConsumption` 很高的地图。
4. 第一次复活前不偷看后续 Boss 血量。
5. 复活后或血量已全部可见时，可以对已知 Boss 序列整体规划。

## 2. 输入和输出

### 2.1 输入

技能规划函数接收：

```python
skills: list[Skill]
healths: list[int]
min_rounds: int
conserve_skills: bool
```

其中：

- `skills`：玩家技能列表。
- `healths`：本次规划可见的 Boss 血量序列。
- `min_rounds`：当前剩余可用 Boss 战回合数。
- `conserve_skills`：是否启用“当前 Boss 保守规划”。

### 2.2 Skill 字段

每个技能有：

```python
damage: int
cooldown: int
remaining_cooldown: int
```

地图中的技能格式：

```json
"PlayerSkills": [[12, 4], [5, 2], [2, 0]]
```

含义：

```text
[技能伤害, 技能冷却]
```

### 2.3 输出

规划函数输出：

```python
list[int | None]
```

含义：

- `0`：使用第 1 个技能
- `1`：使用第 2 个技能
- `2`：使用第 3 个技能
- `None`：等待一回合

示例：

```python
[0, None, 2, 1]
```

表示：

```text
第 1 回合：使用 Skill #1
第 2 回合：等待
第 3 回合：使用 Skill #3
第 4 回合：使用 Skill #2
```

## 3. 两种规划模式

当前项目中有两种 Boss 技能规划模式。

## 3.1 current_boss 模式

触发条件：

```python
all_boss_healths_revealed == False
```

也就是第一次复活前。

特点：

- 只知道当前 Boss 血量。
- 不知道后续 Boss 血量。
- 自动模式虽然地图里有完整 `"B": [...]`，也不能使用后续 Boss 血量。
- 手动模式本来只输入了当前 Boss，也没有后续 Boss 血量。
- 使用 `conserve_skills=True`。

调用路径：

```python
battle = simulate_boss_battle(
    self.ctx.player.skills,
    health,
    round_limit,
    conserve_skills=True,
)
```

这里的 `health` 只等于当前 Boss 血量：

```python
health = self.boss_health_sequence[health_idx]
```

不会传入：

```python
self.boss_health_sequence[health_idx + 1:]
```

状态字段：

```text
planning_mode = "current_boss"
planning_strategy = "conservative_current_boss"
planned_boss_healths = [当前 Boss 血量]
```

## 3.2 known_sequence 模式

触发条件：

```python
all_boss_healths_revealed == True
```

典型场景：

- 自动模式复活后。
- 手动模式复活后点击“重新规划挑战已知 Boss”。
- 测试或调试时显式设置 `boss_healths_revealed = true`。

特点：

- 可以使用当前已知 Boss 血量序列。
- 从当前 Boss 开始，一直规划到最后一个已知 Boss。
- 适合复活后的整体最优规划。

调用路径：

```python
known_healths = self.boss_health_sequence[health_idx:]
sequence_plan = _plan_boss_sequence(
    self.ctx.player.skills,
    known_healths,
    round_limit,
)
```

状态字段：

```text
planning_mode = "known_sequence"
planned_boss_healths = known_healths
```

## 4. 动态规划核心

核心函数：

```python
_plan_boss_sequence(skills, healths, min_rounds, conserve_skills=False)
```

它是一个按回合推进的动态规划搜索。

## 4.1 DP 状态

每个状态由两个部分组成：

```python
(boss_idx, cooldowns)
```

其中：

- `boss_idx`：当前正在打第几个 Boss。
- `cooldowns`：所有技能当前剩余冷却，类型是 `tuple[int, ...]`。

状态保存的值：

```python
(remaining_health, plan)
```

其中：

- `remaining_health`：当前 Boss 剩余血量。
- `plan`：到达该状态的技能序列。

完整结构：

```python
dp: dict[
    tuple[int, tuple[int, ...]],
    tuple[int, list[int | None]]
]
```

## 4.2 初始状态

初始状态：

```python
initial_cooldowns = tuple(max(skill.remaining_cooldown, 0) for skill in skills)

dp = {
    (0, initial_cooldowns): (healths[0], [])
}
```

含义：

- 从 Boss #1 开始。
- 当前 Boss 血量为 `healths[0]`。
- 技能冷却继承进入 Boss 战时的真实状态。
- 技能序列为空。

## 4.3 按回合扩展

算法从第 1 回合开始，最多扩展到 `max_rounds`：

```python
for _round_no in range(1, max_rounds + 1):
    next_states = {}
```

每一层代表 Boss 战中的 1 个回合。

对于当前层中的每个状态：

1. 找到当前可选动作。
2. 生成新技能序列。
3. 如果使用技能，则扣 Boss 血量。
4. 如果当前 Boss 被打死，则进入下一只 Boss。
5. 更新技能冷却。
6. 保存更优状态。

## 4.4 状态转移

伪代码：

```python
for (boss_idx, cooldowns), (remaining_health, plan) in dp.items():
    for choice in _boss_planner_choices(skills, cooldowns):
        new_plan = [*plan, choice]
        new_boss_idx = boss_idx
        new_remaining = remaining_health

        if choice is not None:
            new_remaining -= skills[choice].damage

            if new_remaining <= 0:
                new_boss_idx += 1

                if new_boss_idx >= len(healths):
                    winning_plans.append(new_plan)
                    continue

                new_remaining = healths[new_boss_idx]

        new_cooldowns = _advance_boss_cooldowns(skills, cooldowns, choice)
        key = (new_boss_idx, new_cooldowns)
        _store_boss_dp_state(next_states, key, new_remaining, new_plan)
```

## 5. 可选动作生成

函数：

```python
_boss_planner_choices(skills, cooldowns)
```

规则：

1. 找出所有冷却为 0 的技能。
2. 按伤害高、冷却短、下标小排序。
3. 过滤被支配技能。
4. 必要时加入 `None` 表示等待。

## 5.1 可用技能

```python
ready = [idx for idx, cooldown in enumerate(cooldowns) if cooldown <= 0]
```

只有 `cooldown <= 0` 的技能可以使用。

## 5.2 被支配技能过滤

如果同一回合有两个技能 A 和 B：

```text
B.damage >= A.damage
B.cooldown <= A.cooldown
```

并且 B 至少有一项严格更优，那么 A 被认为是被支配技能。

被支配技能不会进入候选动作。

好处：

- 减少搜索分支。
- 避免选择明显不如另一个技能的动作。

## 5.3 等待动作

等待动作使用：

```python
None
```

以下情况会加入等待动作：

- 当前没有任何技能可用。
- 或者存在技能仍在冷却中。

这样算法可以选择“等一个关键技能冷却好”，而不是被迫使用低价值技能。

## 6. 技能冷却推进

函数：

```python
_advance_boss_cooldowns(skills, cooldowns, used_idx)
```

规则：

1. 如果本回合使用了技能 `used_idx`，该技能冷却设置为它的完整冷却值。
2. 其他技能如果正在冷却，则冷却减 1。
3. 如果本回合等待，则所有正在冷却的技能都减 1。
4. 冷却最小为 0。

代码逻辑：

```python
if used_idx is not None:
    next_cooldowns[used_idx] = skills[used_idx].cooldown

for idx, cooldown in enumerate(next_cooldowns):
    if idx != used_idx and cooldown > 0:
        next_cooldowns[idx] = cooldown - 1
```

示例：

技能 `[12, 4]` 在第 1 回合使用：

```text
R1 使用后 CD = 4
R2 CD = 3
R3 CD = 2
R4 CD = 1
R5 CD = 0
R6 可以再次使用
```

## 7. 状态保存和剪枝

同一个状态 key：

```python
(boss_idx, cooldowns)
```

可能由多条技能序列到达。

保存规则：

```python
if current is None:
    保存
elif remaining_health < current_remaining_health:
    保存
elif remaining_health == current_remaining_health and 当前 plan tie-break 更好:
    保存
```

也就是说，同样打到同一个 Boss、同样技能 CD 状态时：

- 当前 Boss 剩余血量越低越好。
- 剩余血量相同，则使用稳定排序规则。

## 7.1 状态数量限制

常量：

```python
BOSS_SEQUENCE_STATE_LIMIT = 50000
```

如果某一层状态太多，会剪枝：

```python
_trim_boss_sequence_states()
```

排序优先级：

1. 打到更后面的 Boss。
2. 当前 Boss 剩余血量更低。
3. 技能总冷却更低。
4. 技能序列 tie-break 更好。

这样可以避免技能很多时搜索爆炸。

## 8. 找到胜利方案后的处理

如果某个方案在当前回合层打完全部可见 Boss：

```python
winning_plans.append(new_plan)
```

然后根据模式选择返回方式。

## 8.1 known_sequence 返回方式

当 `conserve_skills=False`：

```python
return min(winning_plans, key=_plan_tiebreak)
```

也就是找到能打完整个已知 Boss 序列的最短回合层后，立刻返回该层中最优方案。

普通 tie-break：

```python
_plan_tiebreak(plan) = (等待次数, 方案长度, 技能顺序)
```

偏好：

1. 等待更少。
2. 序列更短。
3. 技能下标更靠前。

## 8.2 current_boss 保守返回方式

当 `conserve_skills=True`：

```python
conservative_winning_plans.extend(winning_plans)
return min(
    conservative_winning_plans,
    key=lambda plan: _conservative_plan_tiebreak(skills, healths, plan, max_rounds),
)
```

当前配置：

```python
BOSS_CONSERVE_EXTRA_ROUNDS = 0
```

也就是说：

- 仍然优先在最短可胜利回合层中选择方案。
- 但同一层内不会只看伤害最大，而是看后续战斗能力。

## 9. current_boss 保守评分

函数：

```python
_conservative_plan_tiebreak(skills, healths, plan, max_rounds)
```

该评分只用于第一次复活前的当前 Boss 规划。

排序返回：

```python
(
    exact_kill_penalty,
    -future_damage_capacity,
    efficient_skill_pressure,
    overkill,
    len(plan),
    final_cooldown_pressure,
    long_cooldown_pressure,
    waits,
    skill_order,
)
```

排序是从左到右比较，数值越小越优。

## 9.1 exact_kill_penalty

```python
exact_kill_penalty = 0 if overkill == 0 else 1
```

含义：

- 优先选择刚好击杀当前 Boss 的方案。
- 避免浪费伤害。

示例：

Boss HP = 14，技能 `[12, 4]`、`[5, 2]`、`[2, 0]`。

可选方案：

```text
12 + 2 = 14，刚好击杀
12 + 5 = 17，溢出 3
```

算法优先选择：

```text
12 + 2
```

## 9.2 future_damage_capacity

```python
future_damage_capacity = _estimate_future_damage_capacity(...)
```

含义：

- 当前 Boss 打完后，在剩余回合里理论还能打出多少伤害。
- 数值越大越好。
- 排序中使用 `-future_damage_capacity`，所以越大越靠前。

重要限制：

- 它不读取后续 Boss 血量。
- 它只根据技能 CD、技能伤害、技能冷却、剩余回合数估算。

因此它不违反“不偷看后续 Boss 血量”的规则。

## 9.3 efficient_skill_pressure

```python
efficient_skill_pressure += skill.damage / (skill.cooldown + 1)
```

含义：

- 衡量使用了多少高频输出技能。
- 数值越低越优。

这样做的目的：

- 尽量保留高频短 CD 技能给后续未知 Boss。
- 对高复活成本地图更稳。

## 9.4 overkill

```python
overkill = max(total_damage - total_health, 0)
```

含义：

- 当前规划对可见 Boss 造成的溢出伤害。
- 越少越好。

## 9.5 len(plan)

含义：

- 技能序列长度。
- 在前面几个关键指标相同的情况下，优先更短方案。

## 9.6 final_cooldown_pressure

```python
sum(cooldown * skill.damage)
```

含义：

- 打完当前 Boss 后，技能 CD 状态的压力。
- 高伤害技能还在很长 CD 中，会导致该值变大。
- 越低越好。

## 9.7 long_cooldown_pressure

```python
skill.damage * (skill.cooldown + 1)
```

含义：

- 使用长 CD 高伤害技能会产生较大压力。
- 用于进一步减少大招浪费。

## 9.8 waits

等待回合数。

等待越少越好。

## 9.9 skill_order

最后的稳定排序。

```python
skill_order = tuple(9999 if item is None else item for item in plan)
```

作用：

- 如果所有评分都一样，让结果稳定可复现。

## 10. future_damage_capacity 估算

函数：

```python
_estimate_future_damage_capacity(skills, cooldowns, rounds)
```

该函数模拟“从打完当前 Boss 后的技能 CD 状态开始，剩余回合内理论最多能打多少伤害”。

伪代码：

```python
total_damage = 0
current_cooldowns = cooldowns

for each round in remaining_rounds:
    ready = 所有 cooldown <= 0 的技能

    if ready:
        choice = 当前可用技能中伤害最高的技能
    else:
        choice = None

    if choice is not None:
        total_damage += skills[choice].damage

    current_cooldowns = _advance_boss_cooldowns(skills, current_cooldowns, choice)

return total_damage
```

注意：

- 这是估算，不是完整未来 Boss 规划。
- 不需要知道后续 Boss 血量。
- 只用于比较“打完当前 Boss 后哪个 CD 状态更适合继续战斗”。
- 计算量比完整未来 DP 小很多，适合实时后端使用。

## 11. known_sequence 整体规划

复活后或血量已知时，使用：

```python
_plan_boss_sequence(skills, known_healths, round_limit)
```

此时 `conserve_skills=False`。

特点：

- DP 状态中的 `boss_idx` 会真实跨 Boss 推进。
- 打死当前 Boss 后，`remaining_health` 切换为下一只 Boss 血量。
- 技能 CD 不刷新，继续继承。
- 直到打完所有已知 Boss 或回合耗尽。

示例：

```text
known_healths = [5, 9]
skills = [[9, 5], [5, 0]]
minRouds = 2
```

如果第一只 Boss 用 9 伤害技能，会浪费大技能：

```text
Boss #1: 9 damage -> 死
Boss #2: 只能用 5 damage -> 打不死
```

DP 会选择：

```text
Boss #1: 用 5 damage 技能
Boss #2: 用 9 damage 技能
```

这样两回合打完。

## 12. 计划如何变成战斗详情

规划只输出技能下标序列。

实际生成战斗过程的是：

```python
_build_boss_rounds(skills, health, plan)
```

它会逐回合生成：

```python
{
    "round": round_no,
    "action": "attack" or "wait",
    "skill_index": used_idx,
    "skill_label": "Skill #N",
    "damage": damage,
    "hp_before": hp_before,
    "hp_after": hp_after,
    "ready_skills": ready,
    "cooldowns_before": cooldowns_before,
    "cooldowns_after": cooldowns_after,
}
```

前端 Boss 战详情就是根据这些 round 数据展示：

- 用了哪个技能
- 造成多少伤害
- Boss 血量如何变化
- 技能 CD 如何变化

## 13. known_sequence 如何拆分到当前 Boss

当整体规划得到了跨 Boss 的完整 plan 后，当前只需要执行当前 Boss 的那一段。

函数：

```python
_first_boss_plan_segment(skills, health, plan)
```

作用：

- 从完整 plan 里截取当前 Boss 被打死前的部分。
- 当前 Boss 打死后停止。
- 后续 Boss 的计划会在下一只 Boss 开始时继续重新计算。

这样做的原因：

- 每只 Boss event 需要单独展示。
- 技能 CD 会在每只 Boss 打完后写回真实状态。
- 下一只 Boss 开始时再根据真实 CD 状态规划。

## 14. 失败计划

如果 DP 在总回合内找不到胜利方案，会返回目前找到的 best partial plan。

best partial 比较规则：

1. 打到更后面的 Boss 更好。
2. 同一个 Boss 时，剩余血量更少更好。
3. 技能序列更长更好。
4. 最后按普通 tie-break。

这样即使失败，也能产生完整战斗过程，前端可以显示：

- 打了多少回合
- 用了哪些技能
- Boss 剩余多少血
- 是否触发复活

## 15. 和复活逻辑的关系

技能规划算法本身不扣价值，也不决定最终是否复活。

它只返回：

```text
本次 Boss 尝试是 win 还是 lose
用了多少回合
技能释放详情
最终技能 CD
```

复活逻辑由 `_handle_boss()` 处理：

1. 如果 `battle["result"] == "win"`，进入下一只 Boss。
2. 如果 `battle["result"] == "lose"`，扣除 `CoinConsumption`。
3. 如果价值足够，复活。
4. 如果价值不足，整局失败。

## 16. 当前高复活成本优化的意义

高复活成本地图中，最危险的问题是：

```text
当前 Boss 虽然能最快打死，
但打完后关键技能进入长 CD，
导致下一只未知 Boss 来不及打死，
最终复活。
```

当前保守规划通过以下方式降低风险：

- 刚好击杀优先，减少伤害浪费。
- 估算打完当前 Boss 后剩余回合的理论输出。
- 尽量保留高频短 CD 技能。
- 尽量降低最终 CD 压力。

目前回归测试中，这些地图可以在第一次复活前完成 Boss 序列：

```text
map/1best_maze_design_汪子策.json
map/2best_maze_design_张志南.json
map/6best_maze_design_郑源.json
map/7best_maze_design_于小航.json
```

## 17. 算法边界

后续修改技能规划时，必须保持以下边界：

1. `current_boss` 模式不能读取后续 Boss 血量。
2. `known_sequence` 模式可以读取已知 Boss 序列。
3. `minRouds` 是整个 Boss 序列的总回合预算。
4. 技能 CD 必须跨 Boss 继承。
5. 复活后技能 CD 才能全部刷新。
6. 规划算法不能直接修改玩家价值。
7. 规划算法不能直接修改迷宫步数。
8. 规划输出必须能生成完整 round 详情，供前端播放。

## 18. 可调优位置

如果之后要继续优化，可以优先改这些地方：

### 18.1 当前 Boss 保守评分

函数：

```python
_conservative_plan_tiebreak()
```

可以调整：

- 是否更重视刚好击杀
- 是否更重视未来理论输出
- 是否更重视保留短 CD 技能
- 是否更重视保留长 CD 大招
- 是否允许多用一两个回合换更好的 CD 状态

### 18.2 未来输出估算

函数：

```python
_estimate_future_damage_capacity()
```

当前是轻量贪心估算。

可以升级为：

- 小规模 DP 估算
- Beam Search
- 根据剩余回合计算技能周期收益
- 根据技能组合估计爆发窗口

注意：不能加入后续 Boss 血量，否则会破坏第一次复活前的信息规则。

### 18.3 状态剪枝

常量：

```python
BOSS_SEQUENCE_STATE_LIMIT = 50000
```

如果技能数量极多，可以降低该值提升速度。

如果需要更高质量，可以提高该值，但可能影响前端等待时间。

### 18.4 等待动作策略

函数：

```python
_boss_planner_choices()
```

当前只在必要时加入等待。

可以研究：

- 更积极等待关键大招
- 根据剩余回合决定是否等待
- 根据当前 Boss 剩余血量决定是否等待

## 19. 简化伪代码

完整规划可以简化理解为：

```text
输入：技能列表、可见 Boss 血量、剩余总回合

初始化：
  状态 = 第 1 个 Boss + 当前技能 CD

for 回合 in 1..剩余总回合:
  新状态集合 = 空

  for 每个状态:
    for 每个可选动作:
      复制技能序列
      如果动作是技能：
        当前 Boss 扣血
      如果当前 Boss 死亡：
        切到下一只 Boss
      推进技能 CD
      保存更优状态

  如果出现打完所有可见 Boss 的方案:
    如果是 known_sequence:
      返回最短胜利方案
    如果是 current_boss:
      在胜利方案中选择最保守方案

  如果状态太多:
    剪枝

如果没有胜利方案:
  返回当前最接近成功的方案
```

## 20. 快速定位代码

| 功能 | 函数 |
|---|---|
| 单只 Boss 战模拟 | `simulate_boss_battle()` |
| Boss 序列规划入口 | `_plan_boss_sequence()` |
| 当前 Boss 保守评分 | `_conservative_plan_tiebreak()` |
| 未来理论输出估算 | `_estimate_future_damage_capacity()` |
| 技能候选生成 | `_boss_planner_choices()` |
| 技能 CD 推进 | `_advance_boss_cooldowns()` |
| 计划转 round 详情 | `_build_boss_rounds()` |
| 已知序列截取当前 Boss 段 | `_first_boss_plan_segment()` |
| Boss 主状态机 | `_handle_boss()` |
