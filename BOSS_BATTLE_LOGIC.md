# Boss 战斗逻辑文档

本文档描述当前项目中的 Boss 战斗规则、自动/手动血量读取方式、复活机制、技能冷却规则、技能规划算法以及前端/API 对接方式。

当前实现的核心文件：

- `eval/simulator.py`：Boss 战主逻辑、技能规划、复活、手动输入状态机
- `api/routers/sim.py`：前端调用的模拟、手动输入、重新规划 API
- `frontend/index.html`：Boss 输入面板和 Boss 战详情展示
- `frontend/static/js/app.js`：前端交互、播放流程、调用 API
- `frontend/static/js/api.js`：API 请求封装

## 1. 核心概念

### 1.1 价值

项目中显示的 `coins` / `value` / `total_value` 本质上都是“当前价值”。

默认规则：

- 金币格 `C` / `G`：价值 `+50`
- 陷阱格 `T`：价值 `-30`
- Boss 复活消耗：扣除地图字段 `CoinConsumption`

代码常量位于 `eval/simulator.py`：

```python
COIN_VALUE = 50
TRAP_DAMAGE = 30
```

### 1.2 Boss 数量和血量

Boss 血量序列来自地图字段：

```json
"B": [220, 710, 1010, 420, 220]
```

含义：

- Boss 数量等于数组长度。
- 数组顺序就是 Boss 出现顺序。
- 地图上可以只有一个 `B` 格子，但它可以连续触发多只 Boss。
- Boss 是一个一个打，不会一次性把所有 Boss 展示给玩家。

### 1.3 技能格式

技能来自地图字段：

```json
"PlayerSkills": [[12, 4], [5, 2], [2, 0]]
```

每个技能格式：

```text
[伤害, 冷却回合数]
```

例如 `[12, 4]` 表示：

- 使用时造成 `12` 点伤害。
- 使用该技能的当前回合算第 1 回合。
- 之后还要经过 4 个完整回合。
- 第 6 回合才能再次使用这个技能。

Boss 不会攻击。玩家每次使用一个技能，或等待一回合，都算 Boss 战的 1 个回合。

## 2. Boss 血量来源

当前有两种模式：自动读取和手动输入。两种模式互相独立，不互相污染状态。

### 2.1 自动读取模式

触发条件：

- 前端选择 `AUTO`
- 或 `boss_source = auto` 且地图中存在非空 `"B": [...]`

规则：

- 后端读取地图中的 Boss 血量数组。
- Boss 血量序列保存到 `boss_health_sequence`。
- 即使后端已经拿到了完整数组，第一次战斗时 AI 仍然按“只知道当前 Boss 血量”的规则规划。
- 后续 Boss 血量不会提前暴露给前端展示，也不会被当前 Boss 规划算法使用。

### 2.2 手动输入模式

触发条件：

- 前端选择 `MANUAL`
- 或 `boss_source = auto` 且地图没有非空 `"B": [...]`

规则：

- 启动时不需要输入 Boss 数量。
- 启动时不需要输入 Boss 血量。
- AI 先按迷宫算法探索。
- AI 到达 `B` 位置后暂停，状态变成 `awaiting_boss_input = true`。
- 前端输入当前 Boss 血量后，后端立刻打当前 Boss。
- 打完后继续等待下一只 Boss 血量。
- 输入 `-1` 表示当前 Boss 点输入结束，AI 清掉该 `B` 点并继续探索迷宫。

手动输入模式下，如果地图本身也有 `"B": [...]`，该数组不会参与手动战斗。手动输入的数据和地图数组互不干扰。

## 3. 血量可见性规则

当前规则强调“不偷看后续 Boss 血量”。

### 3.1 第一次复活前

无论自动模式还是手动模式，第一次复活前都遵守：

- 当前 Boss 血量可见。
- 已击败 Boss 的血量记录可见。
- 后续 Boss 血量不可见。
- 当前 Boss 的技能规划只使用当前 Boss 血量。

代码路径：

```python
if not self.all_boss_healths_revealed:
    battle = simulate_boss_battle(
        self.ctx.player.skills,
        health,
        round_limit,
        conserve_skills=True,
    )
```

对应状态：

```text
planning_mode = "current_boss"
planning_strategy = "conservative_current_boss"
planned_boss_healths = [当前 Boss 血量]
```

### 3.2 复活后

复活后认为已知当前已经出现过的 Boss 血量。

自动模式：

- 复活后 `all_boss_healths_revealed = true`。
- 因为自动模式本来持有完整地图数组，所以复活后可以按剩余 Boss 序列整体规划。
- 重新从 Boss #1 开始打。

手动模式：

- 复活后 `all_boss_healths_revealed = true`。
- 已经手动输入过的 Boss 血量都变成已知。
- 不会让玩家继续输入新 Boss。
- 必须点击“重新规划挑战已知 Boss”。
- 重新规划会从 Boss #1 开始挑战已知 Boss 序列。
- 重新规划成功后，继续等待下一只 Boss 血量。

### 3.3 已知序列规划

当 `all_boss_healths_revealed = true` 时，后端使用已知 Boss 序列整体规划：

```python
known_healths = self.boss_health_sequence[health_idx:]
sequence_plan = _plan_boss_sequence(self.ctx.player.skills, known_healths, round_limit)
```

对应状态：

```text
planning_mode = "known_sequence"
planned_boss_healths = 当前 Boss 到最后一个已知 Boss 的血量序列
```

## 4. minRouds 总回合规则

地图字段：

```json
"minRouds": 15
```

当前含义：

- `minRouds` 是从 Boss #1 打到最后一个 Boss 的总回合上限。
- 不是每只 Boss 单独拥有 `minRouds` 回合。

示例：

```text
minRouds = 15
Boss #1 用 1 回合
Boss #2 用 4 回合
Boss #3 用 7 回合
Boss #4 用 2 回合
Boss #5 用 1 回合
总回合 = 1 + 4 + 7 + 2 + 1 = 15
```

如果打当前 Boss 前已经用了 `total_rounds_used` 回合，则当前 Boss 的可用回合数为：

```python
rounds_remaining = max(self.min_rounds - total_rounds_used, 0)
```

Boss event 中会记录：

- `round_limit`：当前 Boss 开打前剩余可用回合
- `total_rounds_before`：当前 Boss 开打前累计 Boss 回合
- `total_rounds_used`：当前 Boss 打完后累计 Boss 回合
- `rounds_remaining_before`
- `rounds_remaining_after`

## 5. 技能冷却规则

Boss 战中每一回合只会出现两种动作：

- `attack`：使用一个技能
- `wait`：等待一回合

冷却推进函数：

```python
def _advance_boss_cooldowns(skills, cooldowns, used_idx):
    next_cooldowns = list(cooldowns)
    if used_idx is not None:
        next_cooldowns[used_idx] = skills[used_idx].cooldown
    for idx, cooldown in enumerate(next_cooldowns):
        if idx != used_idx and cooldown > 0:
            next_cooldowns[idx] = cooldown - 1
    return tuple(max(cooldown, 0) for cooldown in next_cooldowns)
```

解释：

- 本回合使用的技能先被设置为自己的完整冷却值。
- 没有使用的技能，如果冷却大于 0，则减少 1。
- 等待回合时，没有技能被使用，所有冷却中的技能减少 1。
- 冷却不会变成负数。

每轮 Boss 详情中会记录：

- `round`
- `action`
- `skill_index`
- `skill_label`
- `damage`
- `hp_before`
- `hp_after`
- `ready_skills`
- `cooldowns_before`
- `cooldowns_after`

## 6. Boss 战主流程

核心入口：

```python
_handle_boss(pos)
```

流程：

1. 读取当前累计 Boss 回合 `boss_total_rounds_used`。
2. 根据 `defeated_boss_count` 找到当前 Boss 序号。
3. 读取当前 Boss 血量。
4. 计算剩余回合 `round_limit`。
5. 调用 `_boss_battle_trace()` 生成技能释放计划和战斗过程。
6. 将战斗后的技能 CD 写回玩家状态。
7. 如果胜利：
   - 增加 `defeated_boss_count`
   - 更新 `boss_total_rounds_used`
   - 记录 Boss event
   - 如果还有 Boss，继续打下一只
8. 如果失败：
   - 扣除复活价值
   - 判断是否可以复活
   - 如果不能复活，整局失败
   - 如果可以复活，根据自动/手动模式进入不同复活流程

Boss 战过程中玩家不会在迷宫中移动。

## 7. 复活逻辑

地图字段：

```json
"CoinConsumption": 150
```

含义：

- Boss 战失败后，消耗当前价值进行复活。
- 字段名虽然叫 `CoinConsumption`，但当前逻辑按“价值”处理。

### 7.1 扣除规则

扣除函数：

```python
def _consume_revive_value(self, value_before):
    required_cost = max(self.coin_consumption, 0)
    if required_cost <= 0 or value_before <= 0:
        return value_before, 0
    if value_before > 0 and value_before <= required_cost:
        return 0, value_before
    return value_before - required_cost, required_cost
```

规则：

- 如果 `CoinConsumption <= 0`，不能触发有效复活。
- 如果当前价值大于 `CoinConsumption`，扣除完整 `CoinConsumption`。
- 如果当前价值刚好等于 `CoinConsumption`，扣到 0，仍然允许这次复活。
- 如果当前价值小于 `CoinConsumption`，会扣完当前价值，但不足以复活，整局失败。

是否复活成功：

```python
can_revive = required_revive_cost > 0 and actual_cost >= required_revive_cost
```

### 7.2 复活后的共同规则

只要复活成功：

- Boss 序列从 Boss #1 重新开始。
- `defeated_boss_count = 0`
- `boss_total_rounds_used = 0`
- 所有技能 CD 清零。
- `all_boss_healths_revealed = true`
- Boss event 标记：
  - `revived = true`
  - `boss_sequence_reset_on_revive = true`
  - `restart_boss_order = 1`
  - `skill_cooldowns_reset_on_revive = true`

### 7.3 自动模式复活

自动模式下复活后：

- 已知完整 Boss 血量数组。
- 直接从 Boss #1 重新打。
- 使用 `known_sequence` 规划。
- 如果再次失败且价值足够，会继续复活、扣价值、重打。
- 直到成功或价值不足失败。

### 7.4 手动模式复活

手动模式下复活后：

- 扣除复活价值。
- 不会自动继续打新输入的 Boss。
- 当前已经输入过的所有 Boss 血量变为已知。
- `manual_boss_replan_required = true`
- 前端输入框禁用，必须点击“重新规划挑战已知 Boss”。
- 重新规划时从 Boss #1 开始打已知 Boss 序列。
- 如果重新规划成功，继续停在 Boss 输入状态，等待下一只 Boss 血量。
- 如果重新规划仍然超过总回合限制，继续扣复活价值，并要求再次重新规划。

## 8. 手动输入状态机

### 8.1 到达 Boss 点

手动模式下，AI 到达 `B` 点时不会立刻开战，而是进入：

```text
awaiting_boss_input = true
pending_boss_pos = 当前 B 位置
manual_boss_step_pending = true
```

前端显示“已到达 Boss 位置，等待现场键盘输入”。

### 8.2 输入正数血量

输入正数，例如：

```text
72
```

前端调用：

```http
POST /api/sim/{sid}/bosses/input
```

后端行为：

1. 把血量追加到 `boss_health_sequence`。
2. 立即调用 `_handle_boss()`。
3. 打当前已知 Boss 序列中尚未击败的 Boss。
4. 如果成功，继续等待下一只 Boss。
5. 如果失败且可复活，进入 `manual_boss_replan_required`。

### 8.3 输入 -1

输入：

```text
-1
```

表示当前 Boss 点的 Boss 输入结束。

结束要求：

- 所有已输入 Boss 都已经击败。
- 当前没有 `manual_boss_replan_required`。

结束后：

- `awaiting_boss_input = false`
- 清掉当前地图上的 `B` 格
- 将该 Boss 位置加入 `defeated_bosses`
- AI 可以继续探索迷宫

### 8.4 手动模式的迷宫步数

手动模式打 Boss 期间，迷宫步数不变化。

规则：

- AI 进入 Boss 点时，先不立刻增加迷宫步数。
- 每输入一只 Boss 并战斗，不增加迷宫步数。
- 多只 Boss 连续输入和战斗，也不增加迷宫步数。
- 只有输入 `-1` 结束当前 Boss 点输入时，才补记 1 次进入 Boss 点的迷宫步数。

对应字段：

```text
manual_boss_step_pending = true
```

结束输入时：

```python
if self.manual_boss_step_pending:
    self.ctx.step_count += 1
    self.ctx.player.rounds += 1
    self.manual_boss_step_pending = False
```

## 9. 技能规划算法

当前技能规划不是简单贪心，而是动态规划搜索。

核心函数：

```python
_plan_boss_sequence(skills, healths, min_rounds, conserve_skills=False)
```

状态包含：

```text
当前打到第几个 Boss
当前 Boss 剩余血量
所有技能当前 CD
已经选择的技能序列
```

每一层代表 1 个 Boss 战回合。

### 9.1 可选动作

函数：

```python
_boss_planner_choices(skills, cooldowns)
```

候选动作：

- 所有当前可用技能
- 必要时加入 `None`，表示等待一回合

为了减少无意义搜索，会过滤被支配的技能：

如果另一个技能伤害不低于当前技能，冷却不高于当前技能，并且至少一项更优，则当前技能不会进入候选。

### 9.2 普通已知序列规划

用于：

- 复活后自动模式
- 复活后手动模式重新规划
- 显式设置 `boss_healths_revealed = true` 的场景

特点：

- 可以使用当前已知 Boss 序列。
- 目标是在剩余总回合内打完所有已知 Boss。
- 一旦找到能打完的最短回合层，就返回该层中最优方案。

排序规则：

```python
_plan_tiebreak(plan) = (等待次数, 方案长度, 技能顺序)
```

### 9.3 第一次复活前的当前 Boss 保守规划

用于：

- `all_boss_healths_revealed = false`
- 自动模式第一次打 Boss
- 手动模式第一次输入并打 Boss

特点：

- 只传入当前 Boss 血量。
- 不读取后续 Boss 血量。
- 使用 `conserve_skills=True`。
- 目标不是单纯最快打死当前 Boss，而是在不偷看未来血量的前提下，尽量保留后续战斗能力。

当前排序规则：

```text
1. 优先刚好击杀，避免无意义溢出伤害
2. 优先打完当前 Boss 后，剩余回合内理论输出能力更高的 CD 状态
3. 优先少消耗高频短 CD 技能
4. 优先更少 overkill
5. 优先更短方案
6. 优先较低最终 CD 压力
7. 优先较低长 CD 技能压力
8. 优先更少等待
9. 最后按技能下标稳定排序
```

代码字段含义：

```python
exact_kill_penalty
future_damage_capacity
efficient_skill_pressure
overkill
len(plan)
final_cooldown_pressure
long_cooldown_pressure
waits
skill_order
```

其中 `future_damage_capacity` 是一种不看未来 Boss 血量的估算：

- 只根据当前技能 CD 状态、技能伤害、技能冷却和剩余回合数计算。
- 不读取后续 Boss 血量。
- 用贪心方式估算剩余回合最多还能打出多少理论伤害。

这个优化主要用于高复活成本地图，尽量做到第一次不复活。

## 10. 不偷看后续 Boss 血量的保证

第一次复活前，当前 Boss 保守规划调用：

```python
simulate_boss_battle(self.ctx.player.skills, health, round_limit, conserve_skills=True)
```

这里传入的 `health` 是当前 Boss 血量：

```python
health = self.boss_health_sequence[health_idx]
```

此时不会传入：

```python
self.boss_health_sequence[health_idx + 1:]
```

也不会调用：

```python
known_healths = self.boss_health_sequence[health_idx:]
sequence_plan = _plan_boss_sequence(...)
```

只有 `all_boss_healths_revealed = true` 后，才会进入已知序列规划。

因此：

- 自动地图虽然后端持有完整 `"B"` 数组，但第一次复活前规划不会使用后续血量。
- 手动模式本来就只输入当前 Boss，未输入的 Boss 血量不存在，也无法使用。

## 11. Boss event 数据结构

每次 Boss 尝试都会记录一个 event。

重要字段：

```text
type
result
boss_index
encounter_order
attempt
initial_health
remaining_health
total_damage
rounds_used
max_rounds
round_limit
total_rounds_before
total_rounds_used
rounds_remaining_before
rounds_remaining_after
rounds
skills
final_cooldowns
planning_mode
planning_strategy
planned_boss_orders
planned_boss_healths
planned_sequence_result
planned_sequence_rounds
planned_sequence_defeated
value_before
value_after
revived
revive_cost
required_revive_cost
revive
maze_step
```

前端 Boss 战详情面板主要读取：

- `result`
- `encounter_order`
- `attempt`
- `initial_health`
- `remaining_health`
- `total_damage`
- `rounds_used`
- `rounds`
- `value_before`
- `value_after`
- `revive_cost`
- `planning_strategy`
- `planned_boss_orders`

## 12. 前端交互

### 12.1 模式按钮

前端有两个 Boss 来源按钮：

- `AUTO`
- `MANUAL`

默认：

```javascript
bossSourceMode: "map"
```

如果地图没有 Boss 数组，前端会切到手动输入模式。

### 12.2 自动模式

按钮：

```text
计算并播放
```

行为：

1. 调用 `/api/sim/start-run`。
2. 后端直接跑完整个迷宫探索和 Boss 战。
3. 前端按历史帧播放过程。
4. Boss 战详情按 `boss_events` 展示。

### 12.3 手动模式

按钮：

```text
开始/继续探索
```

行为：

1. 调用 `/api/sim/start` 建立会话。
2. 调用 `/api/sim/{sid}/run` 或 step/run 流程让 AI 继续探索。
3. 到达 Boss 点后后端暂停。
4. 前端显示输入框。

手动面板按钮：

- `提交并打当前 Boss`
- `输入 -1 结束`
- `重新规划挑战已知 Boss`

## 13. API

### 13.1 启动会话

```http
POST /api/sim/start
```

请求字段：

```json
{
  "map": "sample",
  "agent": "ensemble",
  "config": {},
  "boss_source": "auto",
  "boss_healths_revealed": false
}
```

`boss_source` 可选值：

- `auto`
- `map`
- `manual`

### 13.2 启动并跑完整流程

```http
POST /api/sim/start-run
```

自动模式常用。

如果 agent 是 `ensemble`，后端会先跑候选迷宫算法，选择迷宫得分最好的算法，然后返回最佳算法的完整播放状态。

### 13.3 手动输入 Boss 血量

```http
POST /api/sim/{sid}/bosses/input
```

输入当前 Boss：

```json
{
  "boss_health": 72,
  "boss_healths_revealed": false
}
```

结束当前 Boss 点：

```json
{
  "boss_health": -1,
  "boss_healths_revealed": false
}
```

### 13.4 手动重新规划

```http
POST /api/sim/{sid}/bosses/replan
```

用于手动模式中复活后重新挑战已知 Boss 序列。

## 14. 失败条件

Boss 战失败会尝试复活。

最终失败条件：

- 当前 Boss 序列无法在剩余总回合内击败。
- 当前价值不足以支付完整 `CoinConsumption`。

失败后：

```text
ctx.done = true
ctx.result = "lose"
```

## 15. 出口条件

出口 `E` 只有在 Boss 条件满足后才能通关。

自动模式：

```text
所有地图 Boss 血量序列都已击败
```

手动模式：

```text
当前 Boss 点输入已用 -1 结束
并且所有已输入 Boss 都已击败
```

如果 Boss 未完成就到达出口，会返回：

```text
exit locked until bosses are defeated
```

## 16. 修改算法时的注意事项

后续如果要继续优化 Boss 战技能算法，建议遵守以下边界：

1. 第一次复活前不能使用后续 Boss 血量。
2. 自动模式和手动模式的血量来源不能互相影响。
3. `minRouds` 必须保持为整个 Boss 序列的总回合上限。
4. 复活后必须从 Boss #1 重新开始。
5. 复活后技能 CD 必须全部清零。
6. 手动模式复活后不能自动继续打新 Boss，必须等待重新规划按钮。
7. 手动模式打 Boss 期间不能增加迷宫步数，只有 `-1` 结束输入时补记一次。
8. Boss 战过程中玩家不能在迷宫中移动。
9. Boss event 必须保留详细 round 信息，供前端展示技能、伤害、CD、价值变化和复活情况。

## 17. 当前高复活成本地图验证

当前回归测试覆盖以下地图的 Boss 规划：

- `map/1best_maze_design_汪子策.json`
- `map/2best_maze_design_张志南.json`
- `map/6best_maze_design_郑源.json`
- `map/7best_maze_design_于小航.json`

测试目标：

- 第一次复活前仍然使用 `current_boss` 模式。
- 不偷看后续 Boss 血量。
- 在总回合 `minRouds` 内击败所有 Boss。
- 不触发复活。

测试位于：

```text
tests/test_simulator.py
```

相关测试名：

```text
test_high_revive_cost_maps_prefer_no_revive_current_boss_plans
```
