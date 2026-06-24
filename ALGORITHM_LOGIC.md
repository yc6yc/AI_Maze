# 网页端三种算法逻辑文档

## 地图数据结构

```javascript
// data 对象
{
  maze: string[][],        // 二维数组, 元素: "#"墙 "S"起点 "E"出口 "B"Boss "T"陷阱 "C"/"G"金币 " "空地
  B: number[],             // Boss 血量列表
  PlayerSkills: number[][], // [damage, cooldown][]
  minRouds: number,        // Boss 战回合限制
  CoinConsumption: number   // 复活消耗金币
}
```

## 公用常量

```javascript
COIN_VALUE = 50       // 金币价值
TRAP_DAMAGE = 30      // 陷阱伤害
VIEW_RADIUS = 1       // 3×3 视野
COMPARE_MAX_STEPS = 500
COMPARE_MAX_STUCK = 20
```

---

## 公用函数

### `revealFog(fogMap, groundTruth, pos, viewRadius)`
- 以 `pos` 为中心，`viewRadius=1` 半径（3×3），将 `groundTruth` 内容复制到 `fogMap`
- 仅此函数接触 `groundTruth`

### `isWalkableFog(cell)`
- `return cell !== null && cell !== "#"`
- `null` = 未探索（不可行走），`#` = 墙

### `neighborsFog(fogMap, pos)`
- 返回 4 方向邻居（上下左右），仅保留 `isWalkableFog` 通过的格子

### `runBossBattle(bossHpList, rawSkills, minRounds, coinConsumption, startingCoins)`
- 每次尝试最多 `minRounds` 回合
- 每回合贪心选**最高伤害可用技能**（冷却为 0 的技能）
- 未能在 `minRounds` 内击败 → 扣 `coinConsumption`，重置技能冷却，重试
- 返回 `{ won, coinsAfter, totalTurns, reviveCount, coinCost, skillSequenceLengths, skillSequences }`

### 去重逻辑（新增）
```javascript
// 去除 path 中连续重复的坐标（卡住帧）
for (var i = 0; i < rawPath.length; i++) {
  if (i === 0 || rawPath[i][0] !== deduped[last][0] || rawPath[i][1] !== deduped[last][1]) {
    deduped.push(rawPath[i]);
  }
}
```

---

## 算法 A：纯 3×3 局部贪心 (`simulateLocalGreedy`)

### 核心思想
每步只看当前 3×3 的 8 个邻居格，打分选最高正分移动。无全局记忆，O(1)/步。

### 参数
```javascript
ALGO_A_CONFIG = {
  coin_value: 50,       // 金币价值
  trap_penalty: 30,     // 陷阱惩罚
  step_cost: 10.0,      // 每步机会成本
  explore_bonus: 8.0,   // 未探索直接邻居的探索奖励
  visited_penalty: 3.0, // 回访惩罚
  w_backtrack: 2.0,     // 回头路额外惩罚
}
```

### 主循环（每步）

```
1. 记录 Frame（fog 状态）
2. 处理当前格效果（step>0 时）:
   - C/G → coins += 50, 格子变空
   - T   → coins -= 30, 格子变空
   - B   → 调用 runBossBattle, 格子变空
   - E   → reachedExit = true, break
3. 评分 3×3 邻居 → 选最高正分移动（Phase 1）
   如无正分 → Phase 2 强制选负分最小的可行格（回溯逃生）
4. 揭露 fog（旧位置 prevPos 的 3×3）
5. 去重后计算: score = coins / moveSteps
```

### 评分公式 (`cellScoreA` + `score3x3`)

```
对 3×3 内每个邻居 (nr, nc):
  dist = |dr| + |dc|  (1 或 2)

  dist=1（直接邻居）:
    cell = fogMap[nr][nc]
    if cell === null (未探索):
      score = explore_bonus (8.0)
      if (nr,nc) === prevPos: score -= w_backtrack (2.0)
    elif !isWalkableFog(cell):
      continue (跳过已知墙)
    else:
      score = cellScoreA(nr, nc, fogMap, dist)
        = (raw_value - dist×step_cost) / dist
          where raw_value = coin_value for C/G, -trap_penalty for T, 0 for empty
        - visited_penalty (3.0) if visited
        - w_backtrack (2.0) if equals prevPos

  dist=2（对角邻居）:
    必须 isWalkableFog 且至少一个中转格 walkable
    score = cellScoreA(nr, nc, fogMap, dist)
```

### 两阶段移动

```
Phase 1: 尝试正分候选（explore > 0 或 coin > 0）
  for candidates sorted by score desc:
    if score <= 0: break
    调用 firstStepA 获取第一步
    if groundTruth[step] !== "#": 移动

Phase 2: 无正分可用 → 强制回溯
  for all candidates:
    选第一个 groundTruth 非墙的格 → 移动
    usedFallback = true

卡住计数:
  moved=false 或 usedFallback → stuckCount++
  stuckCount >= 20 → 终止
```

### 揭露时机
- 在循环末尾揭露 **prevPos**（旧位置），而非 pos（新位置）
- 原因：揭露旧位置使得前进方向仍有未探索格 → `explore_bonus` 可持续触发

---

## 算法 B：记忆增强全局贪心 (`simulateGlobalGreedy`)

### 核心思想
维护 fogMap（所有已揭露格子），每步 Dijkstra 遍历全图已知区域枚举候选目标（金币/前沿/Boss/出口），选最优目标走第一步，下回合重新评估。O(R log R)/步。

### 参数
```javascript
ALGO_B_CONFIG = {
  coin_value: 50.0,
  frontier_value: 14.0,          // 前沿基础价值
  boss_value: 120.0,             // Boss 目标价值
  exit_value: 1000000.0,         // 出口目标价值
  trap_step_cost: 31.0,          // Dijkstra 中陷阱的边权 (1.0 + 31.0 = 32.0)
  target_retry_buffer: 1,        // Boss 金币缓冲系数
  frontier_unknown_weight: 4.0,  // 前沿每个未知邻居的权重
  revisit_penalty: 0.15,         // 回访惩罚系数
  min_explore_before_boss: 0.25, // 打 Boss 前最低探索比例
}
```

### 主循环（每步）

```
1. 揭露当前 pos 的 3×3 (fogMap ← groundTruth)
2. 处理当前格效果（同算法 A）
3. 记录 Frame（fog 已更新）
4. Dijkstra 从 pos 出发，遍历 fogMap 所有已知 walkable 格
5. 枚举候选目标 → 评分 → 选最高分 → 走第一步
6. 去重后计算: score = coins / moveSteps
```

### 候选枚举 (`enumerateCandidatesB`)

遍历 fogMap **所有非 null 格**，Dijkstra 可达的格中，按类型评分：

```
Coin (C/G):
  score = coin_value(50) / max(distanceCost, 1.0) - revisit_penalty
  if should_force_collect: score += 20.0

Boss (B):
  score = scoreBossTarget(distanceCost, coins, ...) - revisit_penalty
  // 包含: readiness check, explore ratio penalty, 金币检查

Exit (E):
  仅在 bosses_cleared 时考虑
  score = exit_value(1000000) / max(distanceCost, 1.0)

Frontier (已知 walkable 且邻接 null 的格):
  rawValue = frontier_value(14.0) + frontier_unknown_weight(4.0) × unknownNeighbors
  score = rawValue / max(distanceCost, 1.0) - revisit_penalty
```

### Dijkstra 陷阱加权

```javascript
// dijkstraFog 中的边权:
if cell === "T" && !triggered:
  weight = 1.0 + trap_step_cost(31.0)  // = 32.0 — 极大惩罚走陷阱
else:
  weight = 1.0
```

### 前沿检测 (`findFrontiersB`)

```javascript
for all r,c in fogMap:
  if isWalkableFog(fogMap[r][c])           // 已知可行走
     && any 4-direction neighbor is null:   // 邻接未探索
    → 这是一个前沿格
```

### `shouldForceCollect`（强制收集模式）

```javascript
if knownBosses.length > 0:
  need = max(CoinConsumption × target_retry_buffer, CoinConsumption)
  return coins < need  // 金币不够打 Boss 时需要强制收集
```

### `scoreBossTarget`

```javascript
base = boss_value(120) / max(distanceCost, 1.0)
if ready (coins >= need):
  base += 40.0
else:
  base -= max(0, need - coins)  // 金币不够时惩罚
if exploredRatio < min_explore_before_boss && !ready:
  base -= 25.0  // 探索不足时额外惩罚
```

---

## 算法 O：原始规划 (`createFrames` / `buildPlannedRoute`)

### 核心思想
**使用完整地图知识**，A* 全局规划路径：先收集所有金币 → 击败所有 Boss → 走出口。**无战争迷雾限制**。

### 规划逻辑 (`buildPlannedRoute`)

```
1. findCells 找到所有 C/G 金币位置
2. while 还有金币:
     bestNextTarget: A* 找最近金币 → 添加到 route → 标记格为空 → 继续
3. findCells 找到所有 B Boss 位置
4. while 还有 Boss:
     bestNextTarget: A* 找最近 Boss → 添加到 route → 标记格为空 → 继续
5. A* 从当前位置到出口 E
```

### 金币计算
- 每经过一个 C/G → `coins += 50`，格变为空
- 每经过一个 T → `coins -= 30`，格变为空（触发后不会重复扣）
- **Boss 战不模拟**（标记"击败"直接通过，不扣复活金币）

### 寻路
- 使用 A*（曼哈顿距离启发式）
- 仅通过 `isWalkable(cell)` 为 true 的格（`cell !== "#"`）
- 完全无视战争迷雾

### 帧生成 (`createFrames`)
- 对 route 中每个位置生成一帧
- 3×3 揭露（`revealAround`）

---

## 三种算法对比

| 维度 | 算法 A | 算法 B | 算法 O |
|------|:---:|:---:|:---:|
| 视野 | 仅 8 邻居 | fogMap 全域 | 全图可见 |
| 寻路 | 无（单步贪心） | Dijkstra 遍历已知区 | A* 全图 |
| 记忆 | 无 | 持久 fogMap | 不需要（全知） |
| 逃出死胡同 | Phase 2 强制回溯 | Dijkstra 自动找前沿 | 全图路径 |
| Boss 模拟 | ✅ 完整模拟 | ✅ 完整模拟 | ❌ 不模拟 |
| 陷阱处理 | 评分惩罚 -40 | Dijkstra 权重 32.0 | 不计入路径（硬通过） |
| 每步复杂度 | O(1) | O(R log R) | O(N log N) |
| 得分公式 | coins / moveSteps | coins / moveSteps | finalCoin / moveSteps |

## 得分公式（统一）

```
moveSteps = deduped_path.length - 1  (去重后，不含起点)
score = finalCoin / moveSteps         (总价值 ÷ 移动步数)
```

## 已知问题

1. **算法 A 空地负分** — 已知空格 score = (0-10)/1 = -10，拒绝穿越开阔走廊，需 Phase 2 兜底
2. **算法 B 追金币入死胡同** — 贪心追最高分金币可能走入无法逃出的位置（如 maze_7_7 的 (5,1)）
3. **算法 O Boss 不模拟** — 原始规划的 `final_coin` 不含 Boss 复活开销，比分虚高
4. **卡住帧虚高步数** — 已通过去重修复
