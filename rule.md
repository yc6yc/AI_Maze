# AI Maze 寻路规则详解

> 本文档描述 `CompositeAgent`（组合决策器）控制下，**局部贪心**与**全局规划**的完整运作规则，以及两者之间的切换逻辑。
>
> 坐标系：`(row, col)`，左上角为 `(1,1)`，向下 row 增大，向右 col 增大。

---

## 一、游戏基础规则

| 格子类型 | 符号 | 效果 |
|---------|------|------|
| 起点 | `S` | 玩家出生点，BOSS 失败后回到此处 |
| 终点 | `E` | 所有 BOSS 击败后到达即通关 |
| 金币 | `C` / `G` | 拾取 +50 金币，格子变为空地 |
| 陷阱 | `T` | 首次踩踏 -30 金币，格子变为空地（只触发一次） |
| BOSS | `B` | 到达后进入战斗阶段 |
| 墙壁 | `#` | 不可进入 |
| 空地 | ` ` | 可通行，无效果 |
| 锁/机关 | `L` | 可通行 |

**评分公式**（越高越好）：

$$\text{score} = \frac{\text{total\_value}}{\text{total\_steps}}$$

$$\text{total\_value} = \text{金币数} \times 50 - \text{触发陷阱数} \times 30 - \text{BOSS失败次数} \times \text{CoinConsumption}$$

---

## 二、视野与迷雾规则（FOV）

- **视野半径 = 1**，即玩家每步能看到以当前位置为中心的 **3×3 区域**（共最多 9 格）。
- 每次移动后，模拟器调用 `_reveal_fov(pos)`，将玩家新位置周围 3×3 格子的真实内容写入 `fog_map`。
- `fog_map[r][c] = None` 表示该格**从未被视野覆盖过**（黑雾）。
- 已揭露的格子内容**永久记住**，不会再次变成迷雾。
- AI 能访问的唯一地图是 `fog_map`，**完全无法直接访问 `ground_truth`**。

**重要推论**：
- 玩家在 `(r, c)` 时，能知道整个 3×3 窗口内所有合法坐标的内容，包括上下左右直接邻居和四个对角邻居。
- 但 `(r+2, c)` 等位置**仍是黑雾**，必须先走到 `(r+1, c)` 才能揭露。
- 因此在当前模拟器规则下，**当前 3×3 视野内不会出现黑雾格**；黑雾只存在于当前 3×3 视野之外，或者从未被任何历史视野覆盖过的位置。
- 这意味着：AI **不可能提前知道两步之外是否是死路**，必须走到近处才能判断。

---

## 三、局部贪心策略（`LocalGreedyAgent`）

### 3.1 总体流程

```
每回合：
  1. 扫描以当前位置为中心的 3×3 窗口，对窗口内每个格子评分
  2. 按评分降序排列，选第一个 score > 0 的格子作为目标
  3. 计算走向目标的第一步（直接邻居直接走，对角邻居走中转格）
  4. 若所有格子 score ≤ 0，返回 STAY（交由 CompositeAgent 处理）
```

### 3.2 3×3 窗口格子分类

以玩家在 `(r, c)` 为中心，窗口内 8 个格子按距离分为两类：

| 类型 | 格子 | 曼哈顿距离 | 到达方式 |
|------|------|-----------|---------|
| 直接邻居 | 上`(r-1,c)` 下`(r+1,c)` 左`(r,c-1)` 右`(r,c+1)` | `dist = 1` | 直接走过去 |
| 对角邻居 | `(r-1,c-1)` `(r-1,c+1)` `(r+1,c-1)` `(r+1,c+1)` | `dist = 2` | 需经过一个中转格 |

### 3.3 格子是否纳入评分的条件

**直接邻居（dist=1）**：
- 正常情况下，直接邻居已经在当前 3×3 视野内，因此一定是已揭露格子，不应该是黑雾。
- `is_walkable(nr, nc) == True`（已揭露且可走格）→ **纳入评分**，按实际内容计算。
- 已揭露为墙（`#`）→ **跳过**。
- 代码中虽然保留了 `fog_map[nr][nc] is None` 的分支，但在当前 3×3 方形视野规则下它通常不会触发；它更像是兼容防御逻辑，而不是正常规则。

**对角邻居（dist=2）**：
- 正常情况下，对角邻居也已经在当前 3×3 视野内，因此同样不应该是黑雾。
- 必须 `is_walkable(nr, nc) == True`，即对角目标格必须是已揭露且可通行的格子。
- 还必须存在至少一条可通行的中转路径：
  - 中转格1 `(r, nc)`（先横后竖）可走，**或者**
  - 中转格2 `(nr, c)`（先竖后横）可走
- 以上条件都满足才纳入评分，否则跳过

> **关键修正**：当前 3×3 方形视野内不会有黑雾格。这里的 `is_walkable` 主要用于排除墙、边界外位置、以及异常情况下仍未揭露的格子，而不是说正常 3×3 对角格会是黑雾。

### 3.4 评分公式

#### 代码中保留的直接邻居黑雾分支（正常情况下不触发）

```
score = explore_bonus
       - w_backtrack  （若该格是上一步所在位置）
```

- `explore_bonus = 8.0`：走向未知格子的探索奖励（固定值，不除以距离）
- `w_backtrack = 2.0`：对上一步位置施加的回头路惩罚

在当前模拟器中，玩家每次行动后都会揭露当前位置周围完整 3×3，所以局部贪心扫描 3×3 时，直接邻居通常已经是已知格子。也就是说，这个黑雾分支一般不会参与正常决策。

#### 已知可走格（直接邻居 dist=1 或对角邻居 dist=2）

```
raw_value = 金币格: +50
            陷阱格（未触发）: -30
            陷阱格（已触发）: 0
            空地格 / 起点 / 终点 / BOSS 格: 0

movement_cost = dist × step_cost       # step_cost = 10.0

score = (raw_value - movement_cost) / dist
       - visited_penalty  （若该格在历史轨迹中）
       - w_backtrack      （若该格是上一步所在位置）
```

**具体数值举例**：

| 格子类型 | dist | 计算过程 | 最终得分（无修正项） |
|---------|------|---------|-------------------|
| 金币 | 1 | `(50 - 10) / 1` | **+40.0** |
| 金币 | 2 | `(50 - 20) / 2` | **+15.0** |
| 陷阱（未触发） | 1 | `(-30 - 10) / 1` | **-40.0** |
| 空地 | 1 | `(0 - 10) / 1` | **-10.0** |
| 空地 | 2 | `(0 - 20) / 2` | **-10.0** |
| 黑雾（代码兼容分支，正常3×3内不会出现） | 1 | `explore_bonus` | **+8.0** |

> ⚠️ **已知空地的得分永远是负数（-10.0）！** 这是当前评分公式的核心问题：
> 在当前 3×3 视野规则下，局部贪心看到的窗口内通常只有已揭露格子；若周围都是空地，所有空地得分都是 -10。
> 因为 `decide()` 只接受 `score > 0` 的目标，所以局部贪心会返回 `STAY`，随后可能触发全局规划接管。

#### 修正项参数

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `visited_penalty` | 3.0 | 历史走过的格子额外扣分（防止原地打转） |
| `w_backtrack` | 2.0 | 上一步所在位置额外扣分（防止来回折返） |

### 3.5 选目标与走第一步

```python
candidates.sort(key=score, reverse=True)
for best_pos, best_score in candidates:
    if best_score <= 0:
        break           # 所有正收益目标已遍历完
    first_step = _first_step(cur_pos, best_pos)
    if first_step is not None:
        return Action(first_step)   # 走向目标的第一步

return Action("STAY")   # 没有任何 score > 0 的可达目标
```

**对角格的中转逻辑（`_first_step`）**：
- 对角目标 `(tr, tc)` 需要中转格，候选中转格为 `(r, tc)` 和 `(tr, c)`
- 选**第一个** `is_walkable == True` 的中转格作为本回合第一步
- 若两个中转格都不可走，该对角目标不可达，跳过尝试下一个候选

---

## 四、全局规划策略（`GlobalPlannerAgent`）

### 4.1 五阶段状态机

```
EXPLORE ──────────────────────→ COLLECT
   │  发现BOSS但金币不足              │
   │                                 │ 金币凑够缓冲目标
   │  发现BOSS且金币充足且探索充分     ↓
   └──────────────────────────→ RUSH_TO_BOSS ──→ RUSH_TO_EXIT
                                      │  失败且金币不足      ↑（所有BOSS击败）
                                      ↓
                               RETRY_COLLECT
                                      │ 凑够1次重试金币
                                      └──────────────────→ RUSH_TO_BOSS
```

### 4.2 各阶段行为

#### EXPLORE（探索阶段）

- **目标**：揭露尽可能多的地图，同时寻找 BOSS 位置
- **寻路方法**：`_bfs_to_frontier`——BFS 在**已知格子**中扩展，找到最近的**前沿格子**
- **前沿格子定义**：已知可行且至少有一个直接邻居是黑雾（`fog_map == None`）
- **BFS 约束**：只经过 `is_walkable == True` 的格子（严格遵守迷雾，不走入未知区域）
- **路径内容**：从当前位置到前沿格子的完整格子列表（含前沿格子本身）
- **无前沿时**：已知区域内找不到任何前沿格，转为 COLLECT 阶段

#### COLLECT（专项收集阶段）

- **目标**：收集足够金币（`retry_buffer × CoinConsumption`）
- **寻路方法**：`_best_coin_target` 选最近金币，用 Dijkstra 规划路径（考虑陷阱代价）
- **无金币时**：`fog_map` 中找不到任何金币格，强制切换到 RUSH_TO_BOSS

#### RUSH_TO_BOSS（冲向BOSS阶段）

- **目标**：快速到达已知的 BOSS 位置
- **寻路方法**：Dijkstra + 陷阱代价权重，自动权衡绕路代价 vs 踩陷阱代价
- **陷阱权重**：踩一次陷阱的代价 = `1步 + trap_step_cost（默认31）`，若绕路步数 < 31 则自动绕开
- **BOSS位置未知时**：回退到 EXPLORE 阶段

#### RUSH_TO_EXIT（冲向出口阶段）

- **触发条件**：`fog_map` 中所有已知 BOSS 格均消失（被击败）且曾击败过至少一个
- **目标**：以最短步数到达终点 `E`
- **寻路方法**：A*（不考虑陷阱，追求步数最短）
- **不可逆**：进入此阶段后不会切换回其他阶段

#### RETRY_COLLECT（失败重试收集阶段）

- **触发条件**：BOSS 战失败（金币骤降约 CoinConsumption）且剩余金币 < CoinConsumption
- **目标**：收集至少 1 次重试所需的金币
- **寻路方法**：与 COLLECT 相同（Dijkstra + 陷阱代价）
- **完成条件**：`coins >= CoinConsumption`，切回 RUSH_TO_BOSS

### 4.3 阶段切换条件详表

| 当前阶段 | 切换到 | 触发条件 |
|---------|--------|---------|
| EXPLORE | COLLECT | 已知区域内无前沿格（地图全部探索完） |
| EXPLORE | RUSH_TO_BOSS | 发现BOSS + 金币 ≥ 缓冲目标 + 探索比例 ≥ 40% |
| COLLECT | RUSH_TO_BOSS | 金币 ≥ `retry_buffer × CoinConsumption` 且满足探索条件 |
| COLLECT | RUSH_TO_BOSS | 地图内无金币可收集（强制冲） |
| RUSH_TO_BOSS | RETRY_COLLECT | 战斗失败 + 剩余金币 < CoinConsumption |
| RUSH_TO_BOSS | EXPLORE | BOSS 位置未知（路径规划失败时回退） |
| RETRY_COLLECT | RUSH_TO_BOSS | 金币 ≥ CoinConsumption |
| 任意阶段 | RUSH_TO_BOSS | 剩余步数 ≤ `rush_round_threshold（50）` 且已知BOSS位置 |
| 任意阶段 | RUSH_TO_EXIT | 所有已知BOSS消失 + 曾击败过≥1个 |

### 4.4 BOSS 位置追踪

- 每回合调用 `_scan_boss`，扫描 `fog_map` 中所有 `CELL_BOSS` 格子
- 支持多 BOSS 地图：维护 `_all_boss_pos` 列表
- BOSS 被击败后格子变为空地，从列表中自动移除
- 当前追踪目标 `_known_boss_pos`：若目标消失则自动切换列表中的下一个

### 4.5 路径执行机制

全局规划器维护一个路径缓存 `self._path`，每回合从中 `pop(0)` 取出下一步：

```python
def decide(ctx):
    # 更新各种状态
    _scan_boss / _detect_failure / _detect_boss_defeated / _update_phase

    # 路径为空，或下一个格子已不可走（如被陷阱触发变化）→ 重新规划
    if not self._path or not ctx.maze.is_walkable(*self._path[0]):
        self._replan(ctx)

    if not self._path:
        return STAY

    next_pos = self._path.pop(0)
    return Action(next_pos)
```

**路径全部走完或中途失效时**，自动触发 `_replan` 重新规划。

---

## 五、局部与全局的切换规则（`CompositeAgent`）

### 5.1 决策优先级（从高到低）

```
优先级1：战斗状态（CombatAgent）
   ↓ 非战斗状态
优先级2：全局RUSH阶段（RUSH_TO_BOSS / RUSH_TO_EXIT）
   ↓ 非RUSH阶段
优先级3：全局规划器主导（_global_active == True）
   ↓ 局部有正收益 → 切回局部
优先级4：局部贪心（主力）
   ↓ 连续STAY次数超阈值 → 切换到全局
```

### 5.2 局部 → 全局 的切换条件

**触发条件**：局部贪心连续返回 `STAY` 达到 `stuck_threshold（默认2）` 次

```
第1次 STAY：_stuck_count = 1，仍由局部贪心决策（实际输出 STAY）
第2次 STAY：_stuck_count = 2 ≥ stuck_threshold → 切换全局
             _global_active = True，_stuck_count = 0
             清空全局路径缓存（_path = []），强制重新规划
```

**为什么是 2 次？** `stuck_threshold=2` 意味着局部贪心看不到任何 `score > 0` 的格子，连续 2 次都无法行动，才判定为真正卡住。

> 注意：局部贪心返回 STAY 并不代表玩家不动，而是 CompositeAgent 第 1 次 STAY 时仍输出 STAY（玩家原地），第 2 次才切换为全局规划的实际移动指令。

### 5.3 全局 → 局部 的切换条件

**触发条件**：全局规划器主导时（`_global_active == True`），每回合检查局部贪心的 `_score_3x3` 结果，**只要有任意一个格子 `score > 0`** 就立即切回局部。

```python
candidates = local_greedy._score_3x3(r, c, ctx.maze)
has_local_reward = any(score > 0 for _, score in candidates)
if has_local_reward:
    _global_active = False
    _stuck_count = 0
    global_planner._path = []   # 清空全局路径（下次激活时重新规划）
    # 本回合由局部贪心接管
```

**什么情况下 `score > 0`？**
- 视野内有**金币格**（dist=1 时 score=40，dist=2 时 score=15）
- 理论上代码兼容了**黑雾直接邻居**（score = explore_bonus = 8.0），但在当前完整 3×3 视野规则下，当前窗口内正常不会出现黑雾直接邻居。
- 注意：已知空地 score = -10，**不会触发切回局部**

### 5.4 RUSH 阶段不被局部打断

```python
if global_planner.phase in (Phase.RUSH_TO_BOSS, Phase.RUSH_TO_EXIT):
    _global_active = True
    _stuck_count = 0
    return global_planner.decide(ctx)   # 直接执行，不检查局部
```

RUSH 阶段目标明确（冲向特定位置），不应被局部的"顺路拾取"打断，否则会导致路径反复中断、绕路。

### 5.5 完整决策流程图

```
每回合 CompositeAgent.decide(ctx)
│
├─ [战斗检测] CombatAgent.should_fight(ctx) == True?
│   └─ Yes → 返回战斗动作，重置 _stuck_count
│
├─ [RUSH检测] global_planner.phase ∈ {RUSH_TO_BOSS, RUSH_TO_EXIT}?
│   └─ Yes → _global_active=True, 返回全局规划动作
│
├─ [全局主导检测] _global_active == True?
│   ├─ 计算 _score_3x3 结果
│   ├─ 有 score > 0 的格子?
│   │   └─ Yes → _global_active=False, 切回局部贪心（继续往下）
│   └─ 无 score > 0 → 返回全局规划动作
│
└─ [局部贪心] local_greedy.decide(ctx)
    ├─ 返回非STAY动作 → _stuck_count=0，执行
    └─ 返回STAY → _stuck_count++
        └─ _stuck_count >= stuck_threshold(2)?
            ├─ Yes → _global_active=True，_stuck_count=0，返回全局规划动作
            └─ No  → 执行STAY（玩家本回合原地不动）
```

---

## 六、迷雾约束验证：AI 是否真的只用 fog_map？

### 局部贪心
- `_score_3x3` 和 `_cell_score` 只访问 `maze.fog_map[r][c]`
- `is_walkable` 方法：`fog_map[r][c] is None` 时返回 `False`（未知格视为不可走）
- ✅ **完全遵守迷雾约束**

### 全局规划
- `_bfs_to_frontier`：BFS 只扩展 `is_walkable == True` 的格子（跳过 None 格）
- `_plan_path → astar / dijkstra`：调用 `maze.is_walkable` 作为可通行判断
- `_scan_boss`：扫描 `fog_map` 而非 `ground_truth`
- ✅ **完全遵守迷雾约束**

### 模拟器（不属于AI，但确认正确性）
- `ground_truth`：完整地图，仅模拟器内部使用，AI 无法访问
- `_step` 中的墙壁判断用 `ground_truth`（物理碰撞逻辑，正确）
- `_reveal_fov`：移动后将 `ground_truth` 内容写入 `fog_map`（正确揭露）
- ✅ **模拟器正确隔离了 AI 视野**

---

## 七、当前已知问题与待修复项

### 问题1：空地 score 为负导致 AI 不穿越已知通道（⚠️ 高优先级）

**现象**：AI 走到某条已揭露通道中时，若局部 3×3 内没有金币等正收益目标，周围空地 score = -10，
导致局部贪心无法选择继续走向已知空地，而是返回 `STAY`，随后可能触发全局规划接管。

**根本原因**：`(raw_value - movement_cost) / dist` 中，`step_cost=10` 使任何空地格得分均为 `-10`。

**期望修复方案**：
```python
# 改为两层结构：
score = raw_value / dist        # 第一层：真实价值率（空地=0，金币=50/dist）
score -= visited_penalty        # 第二层：行为修正（防打转）
score -= w_backtrack            # 第二层：行为修正（防折返）
# 去掉 step_cost 对空地的惩罚
```

这样空地 score = 0，不再是负数，AI 愿意穿越空地继续探索。
黑雾仍然只存在于当前视野外；真正的继续探索应主要由全局规划的前沿搜索负责。

### 问题2：`stuck_threshold=2` 过小导致频繁切换全局

**现象**：局部贪心在走过金币区域后视野内全是已探索空地，score 全为负，
连续 2 次 STAY 立即切全局，全局 EXPLORE 阶段规划一条很长的前沿路径，
走完后又切回局部。频繁切换造成路径不连贯。

**建议**：问题1修复后，空地 score=0（不再触发 STAY），此问题可能自然消失。

### 问题3：文档曾误导为“3×3 内可能存在对角黑雾”（已修正）

在当前模拟器的完整 3×3 方形视野下，玩家当前位置周围 8 个邻居都会被揭露，
因此局部 3×3 内正常不会有黑雾。黑雾只存在于当前视野之外，局部贪心不应该被描述为直接对这些视野外黑雾评分。

---

## 八、配置参数速查（`config.json`）

```json
{
  "local": {
    "coin_value":      50,    // 金币真实价值（匹配游戏规则，勿修改）
    "trap_penalty":    30,    // 陷阱真实扣分（匹配游戏规则，勿修改）
    "step_cost":       10.0,  // 每步机会成本（待移除，见问题1）
    "explore_bonus":   8.0,   // 黑雾直接邻居的探索奖励（可调）
    "visited_penalty": 3.0,   // 历史格子惩罚（可调，防打转）
    "w_backtrack":     2.0    // 回头路惩罚（可调，防折返）
  },
  "global": {
    "w_coin":               2.0,   // 金币权重（_best_coin_target 内部使用）
    "w_trap":               1.5,   // 陷阱权重
    "retry_buffer":         3,     // 预留N次重试金币缓冲（可调）
    "min_explore_ratio":    0.4,   // 切RUSH前最低探索比例（可调）
    "rush_round_threshold": 50,    // 距上限剩余步数不足此值时强制冲BOSS（可调）
    "trap_step_cost":       31     // Dijkstra中陷阱格的额外代价（>30才会绕路）
  },
  "sim": {
    "max_rounds": 500   // 总步数上限
  },
  "composite": {
    "stuck_threshold": 2    // 局部连续STAY多少次切全局（可调）
  }
}
```
