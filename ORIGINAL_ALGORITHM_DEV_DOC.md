# Original 算法开发文档（Fog-constrained A* Planner）

> 本文档面向后端开发者，用于复现前端 `web/app.js` 中的 **Original 算法**（`simulateFogOriginal`）。
> 每个逻辑块都标注了对应的 Python 后端文件和行号，确保前后端完全一致。

---

## 一、算法概述

### 1.1 定位

Original 算法是一个**严格遵守战争迷雾（FOV）约束的在线规划器**。它不读取完整地图（`groundTruth`），只通过 3×3 视野逐步揭露迷宫。

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

---
## 二、对应文件映射

| 模块 | 前端 JS 文件 | 后端 Python 文件 |
|------|------------|----------------|
| **主模拟逻辑** | `web/app.js` → `simulateFogOriginal()` (line 796) | **无直接对应**（此为集成函数，Python 端由 `eval/simulator.py` + `CompositeAgent` 协作实现） |
| **FOV 揭露** | `web/app.js` → `revealFog()` (line 791) | `eval/simulator.py` → `_reveal_fov()` (line 240) |
| **迷雾初始化** | `web/app.js` → `initFogMap()` (line 766) | `core/state.py` → `MazeState.__init__()` |
| **迷雾行走判定** | `web/app.js` → `isWalkableFog()` (line 771) | `core/state.py` → `MazeState.is_walkable()` (line 108) |
| **邻居获取（迷雾版）** | `web/app.js` → `neighborsFog()` (line 776) | `core/state.py` → `MazeState.neighbors()` |
| **Dijkstra（迷雾加权版）** | `web/app.js` → `dijkstraFog()` (line 865) | `core/pathfinding.py` → `dijkstra()` (line 98) |
| **路径还原** | `web/app.js` → `extractPathFog()` (line 902) | `core/pathfinding.py` → `extract_path()` (line 135) |
| **前沿检测** | `web/app.js` → 内联在 `simulateFogOriginal()` 中 (line 976-988) | `agents/global_greedy.py` → `_find_frontiers()` (line 193) |
| **Boss 战斗模拟** | `web/app.js` → `runBossBattle()` (line 1205) | `agents/combat_agent.py` + 外部 Boss 处理器 |
| **格效果处理** | `web/app.js` → 内联在循环中 (line 838-870) | `eval/simulator.py` → `_step()` (line 132) |
| **路径去重** | `web/app.js` → 内联在循环后 (line 1059-1063) | **无对应**（JS 特有，防止卡住帧虚高步数） |

---

## 三、数据结构

### 3.1 输入数据格式

```javascript
// 前端: data 对象
{
  maze: string[][],        // 二维数组, 元素: "#"墙 "S"起点 "E"出口 "B"Boss "T"陷阱 "C"/"G"金币 " "空地 "L"锁
  B: number[],             // Boss 血量序列，按顺序击败
  PlayerSkills: number[][],// [damage, cooldown][]
  minRouds: number,        // Boss 战每Boss回合限制
  CoinConsumption: number  // 复活消耗价值量
}
```

### 3.2 内部状态

```javascript
// 前端: 模拟器内部状态
groundTruth = cloneGrid(data.maze);   // 完整地图副本（模拟器持有，Agent 不可读）
fogMap     = initFogMap(rows, cols);  // 全 null 二维数组（Agent 的唯一信息来源）
pos        = {r: startR, c: startC}; // 当前位置
coins      = 0;                       // 累计价值（金币×50 - 陷阱×30 - 复活×CoinConsumption）
moveSteps  = 0;                       // 有效移动次数
triggeredTraps = new Set();           // 已触发陷阱集合
recentKeys = {};                      // 最近 8 步位置记录（防震荡）
```

### 3.3 输出数据格式

```javascript
// 前端: 返回对象
{
  success: boolean,          // 是否通关
  path: number[][],          // 去重后的路径 [[r,c],...]
  path_length: number,       // path 长度（含起点）
  move_steps: number,        // 有效步数 = path_length - 1
  final_coin: number,        // 最终累计价值
  coin_step_ratio: number,   // success ? final_coin/move_steps : 0
  boss_success: boolean,
  boss_total_turns: number,  // Boss 战总技能使用次数
  boss_revive_count: number, // Boss 复活次数
  boss_coin_cost: number,    // Boss 总价值惩罚
  boss_skill_sequence_lengths: number[], // 每次挑战技能数
  boss_skill_sequences: number[][]       // 技能序列
}
```

---

## 四、核心执行流程

### 4.1 主循环（`simulateFogOriginal`）

```
初始化:
  groundTruth = data.maze 深拷贝
  fogMap = 全 null 数组
  pos = 起点坐标
  revealFog(fogMap, groundTruth, pos, 1)    ← 起点揭秘

循环 (step = 0; step < 500; step++):
  ┌─────────────────────────────────────────┐
  │ 1. revealFog(pos, 1)                     │ ← 揭秘当前位置 3×3
  │    Python: simulator.py _reveal_fov()    │
  ├─────────────────────────────────────────┤
  │ 2. 处理当前格效果 (仅 step>0)             │ ← 根据 groundTruth 结算
  │    - C/G: coins+=50, 格子变空           │    Python: simulator.py _step()
  │    - T:  coins-=30, 格子变空            │
  │    - B:  runBossBattle(...), 格子变空    │
  │    - E:  reachedExit=true, break         │
  ├─────────────────────────────────────────┤
  │ 3. 扫描 fogMap 中的可见目标               │ ← 只看已揭露的格子
  │    - 可见金币列表                         │
  │    - 可见 Boss 列表                       │
  │    - 出口坐标                             │
  ├─────────────────────────────────────────┤
  │ 4. 决策下一步 (优先级递减)                │ ← 详见 §4.2
  │    ① Boss已死+出口可见 → 直冲出口         │
  │    ② Boss 可见 → 冲 Boss                 │
  │    ③ 可见金币 → A*评估 + ratio过滤       │
  │    ④ 前沿探索                             │
  │    ⑤ 兜底: 最少访问邻居                   │
  ├─────────────────────────────────────────┤
  │ 5. 执行移动                               │
  │    - 墙壁检查 (groundTruth)               │
  │    - 震荡检测 (recentKeys)                │
  │    - 更新状态 (pos, visited, recentKeys)  │
  └─────────────────────────────────────────┘

退出条件:
  - reachedExit && allBossesDefeated → 通关
  - stuckCount >= 30             → 失败退出
  - step >= 500                  → 超时退出

后处理:
  - 路径去重 (连续重复坐标)
  - moveSteps = dedupedPath.length - 1
  - ratio = success ? coins / moveSteps : 0
```

### 4.2 决策优先级详解

#### 优先级 1：RUSH_EXIT —— Boss 死后直冲出口

```javascript
// 前端 app.js line 891-895
if (allBossesDefeated && exitPos) {
  var dijE = dijkstraFog(fogMap, pos, triggeredTraps, 31);
  targetPath = extractPathFog(dijE.prev, pos, exitPos);
}
```

**判定条件**：
- `allBossesDefeated === true`（所有 Boss 被击败）
- 出口 E 在 fogMap 中可见（`fogMap[r][c] === "E"`）

**对应 Python 逻辑**：
- `eval/simulator.py` → `_step()` line 168-171: `cell == CELL_END and all bosses defeated → _done = True`

#### 优先级 2：RUSH_BOSS —— 发现 Boss 立即冲

```javascript
// 前端 app.js line 897-910
if (!targetPath && visibleBosses.length > 0 && !bossCleared) {
  // 找最近的 Boss
  for each boss in visibleBosses:
    var dijB = dijkstraFog(fogMap, pos, triggeredTraps, 31);
    if (reachable && dist < bestDist):
      记录最短路径
  targetPath = bestBPath;
}
```

**判定条件**：
- fogMap 中可见 `B` 格
- `bossCleared === false`

**对应 Python 逻辑**：
- `agents/global_greedy.py` → `decide()` line 70-92: 枚举候选时 Boss 目标评分最高

#### 优先级 3：COIN_RATIO —— 金币边际收益过滤

```javascript
// 前端 app.js line 912-972
```

这是 Original 算法的**核心创新**。分两步：

**Step 3a: 基线计算**
```javascript
// 出口已知时：
exitDist = dijkstraFog(pos, exit).距离;
baselineRatio = coins / (moveSteps + exitDist);
// 含义: "如果我现在停手，直奔出口，最终的 ratio 是多少？"

// 出口未知时：
baselineRatio = 0;  // 无法计算基线，改用阈值过滤
```

**Step 3b: 每个金币评估**
```javascript
对每个 fogMap 中可见的金币:
  if (!reachable) continue;

  distToCoin = 路径长度 - 1;
  trapCount = 路径上未触发的陷阱数量;
  netValue = 50 - trapCount × 30;  // 真实净收益

  // 过滤 1: 不拿亏钱的金币
  if (netValue <= 0) continue;

  // 过滤 2: 出口未知时，要求每步收益 >= 5.0
  gainPerStep = netValue / max(distToCoin, 1);
  if (!exitKnown && gainPerStep < 5.0) continue;

  // 计算拿了之后从金币到出口的 ratio
  distCoinToExit = dijkstraFog(coinPos, exit).距离;
  coinRatio = (coins + netValue) / (moveSteps + distToCoin + distCoinToExit);

  // 贪心选 coinRatio 最大的金币
  if (coinRatio > bestCoinScore): bestCoinPath = coinPath;

// 最终判断: 只有 coinRatio > baselineRatio 才拿
if (bestCoinPath && bestCoinRatio > baselineRatio):
  targetPath = bestCoinPath;
```

**核心思想**：不是问"这枚金币值得拿吗"，而是问**"拿这枚金币能让最终的 coin_step_ratio 比现在直奔出口更高吗？"**

**对应 Python 逻辑**：**无直接对应**。这是为 Original 算法专门设计的边际收益过滤器。Python 的 `GlobalGreedyAgent` 使用 `coin_value / distanceCost` 评分（`agents/global_greedy.py` line 128），不进行 ratio 基线比较。

#### 优先级 4：FRONTIER —— 前沿探索

```javascript
// 前端 app.js line 974-1005
前沿定义: fogMap[r][c] 已知 walkable 且四方向邻接 null

评分公式:
  fScore = (unknownCount × 4 + 8) / max(dist, 1)
  if (回溯到 lastPos): fScore -= 5
```

**对应 Python 逻辑**：
- `agents/global_greedy.py` → `_find_frontiers()` (line 193-201)
- `agents/global_greedy.py` → `_enumerate_candidates()` (line 139-152)

#### 优先级 5：FALLBACK —— 兜底移动

```javascript
// 前端 app.js line 1007-1024
选 least-visited 邻居:
  score = -visited[neighbor] × 2
  if (陷阱未触发): score -= 100
  if (回溯): score -= 3
  if (近期位置): score -= 5
```

**对应 Python 逻辑**：
- `agents/local_greedy_policy.py` → `decide()` line 94: 无候选时返回 `Action(move="STAY")`
- Python 端由 `CompositeAgent` 兜底切换全局规划，无此 fallback 逻辑

---

## 五、关键子函数详解

### 5.1 revealFog — FOV 揭露

```javascript
// 前端 app.js line 791
function revealFog(fogMap, groundTruth, pos, viewRadius) {
  for dr in [-1,0,1]:
    for dc in [-1,0,1]:
      nr = pos.r + dr; nc = pos.c + dc;
      if inBounds: fogMap[nr][nc] = groundTruth[nr][nc];
}
```

对应 Python：`eval/simulator.py` → `_reveal_fov()` (line 240-246)

### 5.2 isWalkableFog — 迷雾行走判定

```javascript
// 前端 app.js line 771
function isWalkableFog(cell) {
  return cell !== null && cell !== "#";
}
```

对应 Python：`core/state.py` → `MazeState.is_walkable()` (line 108-112)

### 5.3 dijkstraFog — 迷雾版 Dijkstra

```javascript
// 前端 app.js line 865
权重规则:
  - 已知 walkable 格: weight = 1.0
  - 未触发陷阱 T:    weight = 1.0 + 31.0
  - null (未探索):  不可走（过滤）
  - # (墙):         不可走（过滤）
```

对应 Python：`core/pathfinding.py` → `dijkstra()` (line 98-131) + `weight_fn`（`agents/global_greedy.py` line 99-103）

### 5.4 runBossBattle — Boss 战斗模拟

```javascript
// 前端 app.js line 1205
每个 Boss 独立 minRounds 预算:
  for each boss HP in bossHpList:
    while bossHp > 0 && coins >= 0:
      for round = 1 to minRounds:
        贪心选最高伤害可用技能
        扣血 + 冷却管理
      未击败 → revive: coins -= CoinConsumption, 重置冷却
  全部击败 → return { won: true, ... }
```

对应 Python：`agents/combat_agent.py` → `decide_combat()` (line 86-97)（一回合决策） + 外部 Boss 处理器（多回合循环）

### 5.5 冷却规则

```
使用技能 i 后:
  1. 所有技能 coolingCd -= 1（不低于 0）
  2. 技能 i 的 coolingCd = 技能冷却值
```

对应 Python：`agents/combat_agent.py` → `can_defeat_in_time()` (line 78-81)

---

## 六、配置常量

```javascript
// 前端 app.js
const COIN_VALUE = 50;       // 金币价值
const TRAP_DAMAGE = 30;      // 陷阱惩罚
const VIEW_RADIUS = 1;       // 视野半径
const COMPARE_MAX_STEPS = 500;
const TRAP_STEP_COST = 31;   // Dijkstra 中陷阱路径权重
```

对应 Python：`eval/simulator.py` (line 24-25) + `config.json`

---

## 七、前后端差异对照表

| 功能 | 前端 JS (web/app.js) | 后端 Python | 是否一致 |
|------|---------------------|-------------|:--:|
| FOV 揭露 | `revealFog()` | `simulator.py:_reveal_fov()` | ✅ |
| 迷雾行走判定 | `isWalkableFog()` | `state.py:MazeState.is_walkable()` | ✅ |
| Dijkstra | `dijkstraFog()` | `pathfinding.py:dijkstra()` | ✅ |
| 路径还原 | `extractPathFog()` | `pathfinding.py:extract_path()` | ✅ |
| 前沿检测 | `循环中内联` | `global_greedy.py:_find_frontiers()` | ✅ |
| Boss 战斗 | `runBossBattle()` | `combat_agent.py` + 外部处理器 | ✅ |
| 格效果处理 | `内联在循环中` | `simulator.py:_step()` | ✅ |
| **边际收益过滤** | `coinRatio vs baselineRatio` | **无对应** | ❌ 前端特有 |
| **震荡检测** | `recentKeys` 防回退震荡 | **无对应** | ❌ 前端特有 |
| **CompositeAgent 调度** | `五个优先级决策` | `composite_agent.py` | ❌ 不同架构 |

---

## 八、实现建议

### 8.1 后端复现步骤

1. **复用现有模块**：`eval/simulator.py` 的 `_reveal_fov()`、`_step()` 直接可用
2. **新增决策函数**：在 `agents/` 下新建 `fog_original_agent.py`，实现 §4.2 的五个优先级
3. **新增边际收益过滤器**：实现 §4.2-优先级 3 的 `coinRatio` 计算逻辑
4. **集成到 simulator**：`LocalSimulator.run()` 调用新 Agent 的 `decide()` 即可

### 8.2 关键公式

```python
# 边际收益（优先级 3 核心）
net_value = 50 - trap_count_on_path * 30

# 出口已知时
exit_dist = dijkstra(pos, exit).distance
baseline_ratio = coins / (move_steps + exit_dist)
coin_exit_dist = dijkstra(coin_pos, exit).distance
coin_ratio = (coins + net_value) / (move_steps + dist_to_coin + coin_exit_dist)

# 出口未知时
gain_per_step = net_value / max(dist_to_coin, 1)
if gain_per_step < 5.0: skip

# 前沿评分
fScore = (unknown_count * 4 + 8) / max(dist, 1)
```
