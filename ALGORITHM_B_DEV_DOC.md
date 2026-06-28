# 算法 B 开发文档（全局贪心 FOG Planner）

> 本文档面向后端开发者，用于复现前端 `web/app.js` 中的**算法 B**（`simulateGlobalGreedy`）。
> 每个逻辑块都标注了对应的前端 JS 行号和对应 Python 后端文件，确保前后端一致。

---

## 一、算法概述

### 1.1 定位

算法 B 是一个**严格遵守战争迷雾（FOV）约束的全局贪心在线规划器**。每步基于 fogMap 中所有已揭露的已知区域，用 Dijkstra 搜索所有候选目标（金币 / 前沿 / Boss / 出口），选用价值最高的目标走第一步，下一回合重新评估。

### 1.2 优化目标

```
coin_step_ratio = final_coin / move_steps
final_coin = 收集金币数 × 50 - 触发陷阱数 × 30 - Boss复活次数 × CoinConsumption
```

### 1.3 关键约束

| 约束 | 说明 |
|------|------|
| 战争迷雾 | Agent 只能读 `fogMap`，`fogMap[r][c]===null` = 未知，不可走 |
| 视野 | `VIEW_RADIUS = 1`，每次移动后只揭露当前格 3×3 |
| Boss 未知 | Agent 不知道 Boss 数量和血量，走到 B 格才触发战斗 |
| 出口条件 | 所有 Boss 击败后，E 格才能通关 |
| 每步重规划 | 每步取最优候选的第一步，下一步重新 Dijkstra 扫描 |

---

## 二、对应文件映射

| 模块 | 前端 JS 文件（行号） | 后端 Python 文件 |
|------|------------------|----------------|
| **全局贪心决策器** | `web/app.js` → `simulateGlobalGreedy()` (line 1714) | `agents/global_greedy.py` → `GlobalGreedyAgent.decide()` (line 70) |
| **配置常量** | `web/app.js` → `ALGO_B_CONFIG` (line 45) | `config.json` → `global` 节 |
| **FOV 揭露** | `web/app.js` → `revealFog()` (line 791) | `eval/simulator.py` → `_reveal_fov()` (line 240) |
| **迷雾初始化** | `web/app.js` → `initFogMap()` (line 766) | `core/state.py` → `MazeState.__init__()` |
| **迷雾行走判定** | `web/app.js` → `isWalkableFog()` (line 771) | `core/state.py` → `MazeState.is_walkable()` (line 108) |
| **邻居获取（迷雾版）** | `web/app.js` → `neighborsFog()` (line 776) | `core/state.py` → `MazeState.neighbors()` |
| **Dijkstra（陷阱加权）** | `web/app.js` → `dijkstraFog()` (line 865) | `core/pathfinding.py` → `dijkstra()` (line 98) |
| **路径还原** | `web/app.js` → `extractPathFog()` (line 902) | `core/pathfinding.py` → `extract_path()` (line 135) |
| **候选枚举** | `web/app.js` → `enumerateCandidatesB()` (line 1625) | `agents/global_greedy.py` → `_enumerate_candidates()` (line 94) |
| **Boss 检测** | `web/app.js` → `scanBossesB()` (line 1549) | `agents/global_greedy.py` → `_scan_bosses()` (line 185) |
| **前沿检测** | `web/app.js` → `findFrontiersB()` (line 1561) | `agents/global_greedy.py` → `_find_frontiers()` (line 193) |
| **未知邻居计数** | `web/app.js` → `countUnknownNeighborsB()` (line 1583) | `agents/global_greedy.py` → `_count_unknown_neighbors()` (line 203) |
| **探索比例** | `web/app.js` → `exploredRatioB()` (line 1597) | `agents/global_greedy.py` → `_explored_ratio()` (line 206) |
| **强制收集判断** | `web/app.js` → `shouldForceCollectB()` (line 1609) | `agents/global_greedy.py` → `_should_force_collect()` (line 175) |
| **Boss 目标评分** | `web/app.js` → `scoreBossTargetB()` (line 1616) | `agents/global_greedy.py` → `_score_boss_target()` (line 156) |
| **Boss 战斗模拟** | `web/app.js` → `runBossBattle()` (line 1205) | `agents/combat_agent.py` + 外部 Boss 处理器 |
| **格效果处理** | `web/app.js` → 内联在循环中 (line 1755-1819) | `eval/simulator.py` → `_step()` (line 132) |

---

## 三、数据结构

### 3.1 输入数据格式

```javascript
{
  maze: string[][],        // "#"墙 "S"起点 "E"出口 "B"Boss "T"陷阱 "C"/"G"金币 " "空地 "L"锁
  B: number[],             // Boss 血量序列
  PlayerSkills: number[][],// [damage, cooldown][]
  minRouds: number,        // Boss 战每Boss回合限制
  CoinConsumption: number  // 复活消耗价值量
}
```

### 3.2 配置常量

```javascript
// 前端 app.js line 45
const ALGO_B_CONFIG = {
  coin_value: 50.0,          // 金币价值
  frontier_value: 14.0,      // 前沿基础价值
  boss_value: 120.0,         // Boss 目标基础价值
  exit_value: 1000000.0,     // 出口目标价值（极高，确保Boss击败后优先冲出口）
  trap_step_cost: 31.0,      // Dijkstra 中陷阱额外代价
  target_retry_buffer: 1,    // Boss 金币缓冲系数
  frontier_unknown_weight: 4.0,  // 前沿每个未知邻居的额外权重
  revisit_penalty: 0.15,     // 回访惩罚系数
  min_explore_before_boss: 0.25, // Boss 前最低探索比例
};
```

### 3.3 内部状态

```javascript
// 模拟器内部状态
groundTruth = cloneGrid(data.maze);   // 完整地图（Agent 不可读）
fogMap     = initFogMap(rows, cols);  // 全 null 数组（Agent 唯一信息来源）
pos        = {r: startR, c: startC}; // 当前位置
coins      = 0;                       // 累计价值
visitCount = {};                       // 位置访问次数计数器 {key: count}
lastDir    = null;                    // 上一步移动方向 {dr, dc}（用于方向动量）
```

### 3.4 输出数据格式

```javascript
{
  success: boolean,          // 是否通关
  path: number[][],          // 去重后路径
  path_length: number,       // 路径长度（含起点）
  move_steps: number,        // 有效步数
  final_coin: number,        // 最终价值
  coin_step_ratio: number,   // success ? final_coin/move_steps : 0
  boss_success: boolean,
  boss_total_turns: number,
  boss_revive_count: number,
  boss_coin_cost: number,
  boss_skill_sequence_lengths: number[],
  boss_skill_sequences: number[][]
}
```

---

## 四、核心执行流程

### 4.1 主循环（`simulateGlobalGreedy`）

```
初始化:
  groundTruth = data.maze 深拷贝
  fogMap = 全 null 数组
  pos = 起点坐标
  revealFog(fogMap, groundTruth, pos, 1)        ← 起点揭秘
  visitCount[pos] = 1

循环 (step = 0; step < 500; step++):
  ┌────────────────────────────────────────────┐
  │ Step A: revealFog(pos, 1)                   │ ← 揭秘当前位置 3×3
  │          前端: line 1753                    │    Python: _reveal_fov(pos)
  ├────────────────────────────────────────────┤
  │ Step B: 处理当前格效果 (仅 step>0)          │ ← 根据 groundTruth 结算
  │   C/G → coins+=50, 格子变空                │    Python: _step()
  │   T   → coins-=30, 格子变空                │
  │   B   → runBossBattle(bossHpList), 格子变空 │
  │   E   → reachedExit=true, break             │
  │   前端: line 1761-1819                     │
  ├────────────────────────────────────────────┤
  │ Step C: 记录帧                              │
  │   前端: line 1822-1839                     │
  ├────────────────────────────────────────────┤
  │ Step D: 决策下一步                          │
  │   1. scanBossesB(fogMap) → knownBosses     │   前端: line 1845
  │   2. visitCount[pk]++                      │   前端: line 1848-1849
  │   3. enumerateCandidatesB(...) → candidates │   前端: line 1860
  │   4. 方向动量（前沿 +6/-4）                   │   前端: line 1930-1942
  │   5. 候选第一步回访抑制 (-3/-8)              │   前端: line 1944-1951
  │   6. 排序选最高分 → bestPath[0] 为下一步     │   前端: line 1953-1956
  │   7. lastDir = 新方向                       │   前端: line 1961
  │   8. pos = bestPath[0]                      │   前端: line 1964
  └────────────────────────────────────────────┘

退出条件:
  - reachedExit && allBossesDefeated → 通关
  - stuckCount >= COMPARE_MAX_STUCK → 失败
  - step >= COMPARE_MAX_STEPS → 超时
```

### 4.2 候选枚举（`enumerateCandidatesB`）

函数位于 `web/app.js` line 1625。对 fogMap 做全图扫描，Dijkstra 可达的格子分四类评分：

```
1. Dijkstra(fogMap, pos) — 陷阱加权 weight_fn
   - 已知 walkable:  weight = 1.0
   - 未触发陷阱 T:   weight = 1.0 + 31.0 = 32.0

2. 遍历 fogMap 所有非 null 格:
   if !reachable || cell == pos: continue

   ┌─ Coin (C/G): ──────────────────────────────────────┐
   │ 死胡同检测: count 4-direction walkable neighbors    │
   │   if walkableNbrs ≤ 2: effectiveDist = dist × 1.8   │
   │   else:               effectiveDist = dist           │
   │ coinScore = 50 / max(effectiveDist, 1) - revisit     │
   │ if shouldForceCollect: coinScore += 20               │
   │ 前端: line 1652-1667                               │
   ├─────────────────────────────────────────────────────┤
   │ Boss (B):                                           │
   │ bossScore = scoreBossTargetB(dist, coins, ...) - revis│
   │ 前端: line 1668-1671                               │
   ├─────────────────────────────────────────────────────┤
   │ Exit (E): 仅 allBossesDefeated 时                   │
   │ exitScore = 1000000 / max(dist, 1)                  │
   │ 前端: line 1672-1675                               │
   └─────────────────────────────────────────────────────┘

3. Frontier (前沿): 已知 walkable 且邻接 null 的格
   如果出口 E 可见且 Boss 已死 → 前沿全部跳过（不再探索）
   否则:
   rawValue = 14.0 + 4.0 × unknownCount
   score = rawValue / max(dist, 1)
         - 3.0 × visitCount[前沿]
         - 5.0 × visitCount[前沿第一步]
   前端: line 1680-1709
```

### 4.3 死胡同往返惩罚

```javascript
// 前端 line 1655-1662
// 数金币格四周已知 walkable 邻居
var walkableNbrs = 0;
for (var nd = 0; nd < 4; nd++) {
  if (isWalkableFog(fogMap[neighbor])) walkableNbrs++;
}
// 邻居 ≤ 2 → 很可能是死胡同尽头，代价 ×1.8（往返）
var effectiveDist = (walkableNbrs <= 2) ? distanceCost * 1.8 : distanceCost;
```

**Python 无对应**——这是为 B 算法专门设计的泛化优化，基于 fogMap 已知拓扑，不针对特定地图。

### 4.4 方向动量（仅对前沿）

```javascript
// 前端 line 1930-1942
if (lastDir) {
  for each frontier candidate:
    if 第一步方向 == lastDir:      score += 6.0   // 继续向前：奖励
    if 第一步方向 == -lastDir:     score -= 4.0   // 反向回退：惩罚
}
// 金币候选和 Boss 候选不受影响
```

**Python 无对应**。作用：消除 "向右走→向右走→回头→再向左" 的初始振荡，在不影响金币收集的前提下稳定探索方向。

### 4.5 候选第一步回访抑制

```javascript
// 前端 line 1944-1951
for each candidate:
  var fsk = keyOf(candidate.movePath[0]);
  if visitCount[fsk] >= 3: score -= 8.0   // 严重回访：强力惩罚
  else if visitCount[fsk] >= 2: score -= 3.0 // 近期回访：温和惩罚
```

**Python 无对应**。作用：防止 Agent 在分叉点反复进入同一条岔路。

### 4.6 Boss 目标评分（`scoreBossTargetB`）

```javascript
// 前端 line 1616
function scoreBossTargetB(distanceCost, coins, knownBosses, fogMap, coinConsumption, cfg) {
  if (!knownBosses.length) return -1e9;
  need = max(coinConsumption × 1, coinConsumption);
  exploredRatio = exploredRatioB(fogMap);
  ready = coins >= need;

  base = 120.0 / max(distanceCost, 1);
  if (ready) base += 40.0;           // 金币够：奖励冲 Boss
  else base -= max(0, need - coins);  // 金币不够：惩罚

  if (exploredRatio < 0.25 && !ready) base -= 25.0;  // 探索不足：额外惩罚
  return base;
}
```

### 4.7 强制收集判断（`shouldForceCollectB`）

```javascript
// 前端 line 1609
function shouldForceCollectB(knownBosses, coins, coinConsumption, cfg) {
  if (!knownBosses.length) return false;
  need = max(coinConsumption × 1, coinConsumption);
  return coins < need;  // 金币不够打Boss → 强制收金币
}
```

---

## 五、关键子函数详解

### 5.1 Dijkstra（陷阱加权）

```javascript
// 前端 line 865: dijkstraFog(fogMap, pos, triggeredTraps, 31.0)
权重规则:
  - 已知 walkable 格: weight = 1.0
  - 未触发陷阱 T:    weight = 1.0 + 31.0 = 32.0
  - null (未探索):  不可走（isWalkableFog 过滤）
  - # (墙):         不可走（isWalkableFog 过滤）
```

对应 Python：`core/pathfinding.py` → `dijkstra()` (line 98-131) + `weight_fn` (`agents/global_greedy.py` line 99-103)

### 5.2 Boss 战斗模拟

```javascript
// 前端 line 1205: runBossBattle(bossHpList, skills, minRounds, coinConsumption, coins)
每个 Boss 独立 minRounds 预算:
  for each boss HP:
    while bossHp > 0:
      for round = 1 to minRounds:
        贪心选最高伤害可用技能
        冷却: 使用技能 i → 所有 cd -= 1 → 技能 i cd = cooldown
      未击败 → revive: coins -= CoinConsumption, 冷却重置, 从当前Boss重试
  全部击败 → return {won:true, ...}
```

对应 Python：`agents/combat_agent.py` → `decide_combat()` (line 86-97) + 外部 Boss 处理器

### 5.3 前沿检测（`findFrontiersB`）

```javascript
// 前端 line 1561
前沿定义: fogMap[r][c] 已知 walkable 且四方向邻接 null
扫描 fogMap 全图，对每个已知 walkable 格检查四个方向是否有 null
```

对应 Python：`agents/global_greedy.py` → `_find_frontiers()` (line 193-201)

### 5.4 冷却规则

```
使用技能 i 后:
  1. 所有技能 remainingCd -= 1（不低于 0）
  2. 技能 i 的 remainingCd = 技能冷却值
```

对应 Python：`agents/combat_agent.py` → `can_defeat_in_time()` (line 78-81)

---

## 六、前后端差异对照表

| 功能 | 前端 JS (web/app.js) | 后端 Python | 是否一致 |
|------|---------------------|-------------|:--:|
| FOV 揭露 | `revealFog()` | `simulator.py:_reveal_fov()` | ✅ |
| 迷雾行走判定 | `isWalkableFog()` | `state.py:MazeState.is_walkable()` | ✅ |
| Dijkstra 陷阱加权 | `dijkstraFog()` | `pathfinding.py:dijkstra()` | ✅ |
| 候选枚举 | `enumerateCandidatesB()` | `global_greedy.py:_enumerate_candidates()` | ✅ |
| Coin 评分 | `50/effectiveDist` | `50/distanceCost` | ⚠️ JS 多了 `effectiveDist` |
| 前沿检测 | `findFrontiersB()` | `global_greedy.py:_find_frontiers()` | ✅ |
| Boss 目标评分 | `scoreBossTargetB()` | `global_greedy.py:_score_boss_target()` | ✅ |
| Boss 战斗 | `runBossBattle()` | `combat_agent.py` + 外部处理器 | ✅ |
| **死胡同往返惩罚** | `walkableNbrs ≤ 2 → ×1.8` | **无对应** | ❌ 前端特有 |
| **方向动量** | 前沿 +6/-4 | **无对应** | ❌ 前端特有 |
| **候选第一步回访抑制** | visitCount ≥ 2: -3, ≥ 3: -8 | **无对应** | ❌ 前端特有 |
| **出口可见前沿抑制** | 出口可见 + Boss死 → 跳过前沿 | **无对应** | ❌ 前端特有 |
| **Boss 全部一次性传入** | `bossHpList.slice()` | 外部处理器 | ⚠️ 架构不同 |

---

## 七、实现建议

### 7.1 后端复现步骤

1. **复用现有模块**：`eval/simulator.py` 的 `_reveal_fov()`、`_step()` 直接可用
2. **新增决策函数**：在 `agents/` 下新建算法文件，实现 `enumerateCandidatesB()` 的完整逻辑
3. **新增优化模块**：
   - 死胡同往返惩罚（§4.3）：在 coin 评分前计算 walkableNbrs
   - 方向动量（§4.4）：维护 lastDir 状态，前沿排序前加减分
   - 候选第一步回访抑制（§4.5）：基于 visitCount 对候选加减分
   - 出口可见前沿抑制（§4.2 第 3 点）：扫描 fogMap 判断 exitVisible
4. **集成到 simulator**：`LocalSimulator.run()` 调用新 Agent 的 `decide()` 即可

### 7.2 关键公式速查

```python
# Coin 评分（含死胡同惩罚）
walkable_nbrs = count_4dir_walkable(fogMap, coin_pos)
effective_dist = distance_cost * 1.8 if walkable_nbrs <= 2 else distance_cost
coin_score = 50.0 / max(effective_dist, 1.0) - revisit_penalty * visit_count[coin_pos]
if should_force_collect: coin_score += 20.0

# 前沿评分（含回访惩罚 + 出口抑制）
if exit_visible and all_bosses_defeated: skip all frontiers
raw_value = 14.0 + 4.0 * unknown_count
frontier_score = raw_value / max(dist, 1) - 3.0 * visit_count[target] - 5.0 * visit_count[first_step]

# 方向动量（仅前沿）
if first_step_dir == last_dir: score += 6.0
if first_step_dir == -last_dir: score -= 4.0

# 候选第一步回访抑制
if visit_count[first_step] >= 3: score -= 8.0
elif visit_count[first_step] >= 2: score -= 3.0

# Boss 目标评分
need = max(coin_consumption, coin_consumption)
ready = coins >= need
base = 120.0 / max(dist, 1)
if ready: base += 40.0 else: base -= max(0, need - coins)
if explored_ratio < 0.25 and not ready: base -= 25.0
```
