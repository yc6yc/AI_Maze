# AI Maze — 答辩 PPT 大纲

---

## 一、项目背景（第 1 页）

- 课程：算法设计与分析
- 选题：AI 迷宫寻路算法挑战
- 场景：玩家在 3×3 视野（FOV=1）迷雾中探索迷宫、收集金币、击败 BOSS、到达出口
- 核心指标：`score = 总价值 / 总步数`
  - 总价值 = 金币数×50 - 陷阱数×30 - BOSS 失败次数×CoinConsumption
- 核心难点：部分可观测 + 有限视野 + 未知 BOSS 血量/数量

---

## 二、总体架构：流程图（第 2 页）

**四层架构：**
```
┌─────────────────────────────────────────────┐
│  前端层：Vue 3 CDN + Canvas 2D 可视化       │
│  (frontend/index.html + app.js + api.js)    │
├─────────────────────────────────────────────┤
│  API层：FastAPI 路由                        │
│  (api/main.py → sim / maps / eval / config)  │
├─────────────────────────────────────────────┤
│  模拟引擎 + 算法决策层                       │
│  (eval/simulator.py + agents/*.py)           │
├─────────────────────────────────────────────┤
│  核心库层：状态/寻路/地图加载                │
│  (core/state.py + pathfinding.py + ...)     │
└─────────────────────────────────────────────┘
```
- 前端通过 `fetch()` 调用后端 API，算法全部在 Python 运行
- FastAPI 同时托管静态文件和 RESTful API

---

## 三、前端展示（第 3-4 页）

**技术栈：**
- Vue 3 CDN + 原生 JavaScript + Canvas 2D
- 深空霓虹 UI：Frosted glass + Neon glow + 粒子系统
- FastAPI 后端直接托管（不支持 `file://` 打开）

**关键功能：**
| 功能 | 实现方式 |
|------|---------|
| 迷雾可视化 | `fogMap[r][c]===null` 绘制深色格，已揭露格绘制实际内容 |
| 路径回放 | Canvas 绘制：青色半透明 = 全路径，橙色不透明 = 已走路径 |
| BOSS 战斗展示 | 视频叠加层 + 技能序列逐行显示 |
| 算法对比 | 下拉框选择算法 → 运行 → 结果卡片对比 |
| 输出下载 | "下载输出"按钮 → 生成 `output_result.json` |

---

## 四、算法设计与分析

### 4.1 3×3 实时视野下的拾取策略

**视野规则（核心约束）：**
- 视野半径 FOV = 1，Agent 每次只能新揭露当前位置周围的 3×3 范围
- 但所有曾揭露过的格子**永久记录在 fogMap 中**，不会再次迷雾化
- Agent 的决策范围是整个 fogMap（全部已揭露区域），**不限于当前 3×3**

| 概念 | 范围 | 用途 |
|------|:--:|------|
| 实时视野（FOV） | 当前位置 3×3 | 每次移动后揭露新内容 |
| fogMap 记忆 | 全部历史揭露区 | 永久存储，Agent 的完整地图信息 |
| 决策范围 | fogMap 全域 | Dijkstra 规划路径的可行区域 |

**拾取决策流程：**

```
对 fogMap 中每个可见金币：
  1. Dijkstra(pos, coin)，陷阱加权（未触发 T 额外代价 +31）
  2. 路径上未触发陷阱数 → trapCount
  3. netValue = 50 - trapCount × 30

  4. 边际收益过滤：
     if 出口已知:
       baseline = coins / (steps + exitDist)
       coinRatio = (coins + netValue) / (steps + pathLen + coinExitDist)
       if coinRatio < baseline → 跳过
     else:
       if netValue / pathLen < 5.0 → 跳过

  5. 死胡同惩罚：
     if 金币四周 walkable 邻居 ≤ 2:
       代价 × 1.8（往返成本）

  6. 选 coinRatio 最高的金币 → 走第一步
```

**死胡同惩罚（设计亮点）：**
- 死路尽头金币的 walkable 邻居数只有 1~2（来路 + 尽头）
- 捡完必须原路折返 → 真实成本 ≈ 单程 × 1.8
- 自动绕过孤立金币，不针对特定地图

**对应文件：** `agents/local_greedy_policy.py` → `LocalGreedyAgent`

---

### 4.2 BOSS 战策略

**触发流程：**
Agent 走到 `B` 格 → 模拟器调用 `runBossBattle()` → 战斗内部循环

**战斗规则：**

```
for each boss HP in data.B:
  while bossHp > 0:
    for round = 1 to minRounds:
      贪心选最高伤害可用技能
      扣血，更新冷却
    if 未击败: coins -= CoinConsumption → 重置冷却 → 从当前Boss重试

全部击败 → return won: True
金币不足复活 → return won: False
```

**技能选择 + 冷却规则：**

```
每回合：选 remainingCd == 0 中 damage 最高的
  同伤害 → tie-break by 更低的 cooldown

使用技能 i 后：
  所有技能 remainingCd -= 1（不低于 0）
  技能 i.remainingCd = skill[i].cooldown
```

**Agent 的知识限制：**
- Agent **不知道 Boss 数量和血量**，走到 B 格才知道"这里有 Boss"
- 血量序列由模拟器持有，Agent 只选技能

**0 复活最优序列（算法 E 专用）：**
- BFS 状态空间：(turn, bossIndex, hp, cooldowns[])
- 搜索 minRounds 内击败全部 Boss 的最短序列
- 状态上限 20 万 → 超时回退贪心

**对应文件：** `agents/combat_agent.py` → `CombatAgent`

---

### 4.3 整体迷宫探险策略（五优先级系统）

每一步严格按以下优先级递进决策：

```
P1 — 出口冲刺：
  条件：BOSS 全体击败 + 出口在 fogMap 中可见
  动作：Dijkstra 直达出口
  评分：exit_value(1_000_000) / dist
  不在本阶段绕路拿金币或探索。

P2 — 冲向 BOSS：
  条件：fogMap 中可见 "B" 格 + BOSS 未击败
  动作：选最近可达 BOSS，走 Dijkstra 路径第一步

P3 — 金币收集（边际收益驱动）：
  条件：fogMap 中有可见金币
  评分：coinRatio vs baselineRatio
  + 死胡同惩罚（walkableNbrs ≤ 2 → ×1.8）

P4 — 前沿探索：
  条件：已知 walkable 格邻接 null
  评分：(14 + 4 × 未知邻格数) / dist - 回访惩罚

P5 — 兜底回退：
  条件：无任何候选
  动作：选最少访问的、非回头、非陷阱的邻居
```

**核心增强：（设计亮点）**

| 增强 | 实现方式 | 效果 |
|------|---------|------|
| 方向动量 | lastDir：前沿同方向 +6，反方向 -4 | 岔路震荡减少约 3 倍 |
| 前沿回访抑制 | 目标回访 ≥3 → -8；第一步回访 ≥2 → -3 | 同一分支不进入第三次 |
| 死胡同惩罚 | walkableNbrs ≤ 2 → cost ×1.8 | 自动绕过尽头低效金币 |
| 边际收益过滤 | coinRatio vs baselineRatio | 只选能提高终分的金币 |

---

### 4.4 测试结果分析

**测试地图集：**

| 地图 | 尺寸 | BOSS 数 | minRounds | 特点 |
|------|:--:|:--:|:--:|------|
| maze_7_7 | 7×7 | 4 | 15 | 小密集，多个死角 |
| maze_15_15_1 | 15×15 | 7 | 45 | 陷阱后的 2 金币分支 |
| maze_15_15_2 | 15×15 | 5 | 22 | 窄通道 + 主线双陷阱 |
| response_地图 | 15×15 | — | 175 | 大量金币陷阱混合 |

**核心算法对比表：**

| 算法 | 策略 | 7×7 (ratio) | 15×15_2 (ratio) | 大图 (ratio) |
|:----:|------|:--:|:--:|:--:|
| F（全图 A*） | 全图已知 → 全局 A* | 7.06 | 3.33 | 11.77 |
| E（最优回放） | 地图识别 + 预设路径 | 7.06 | 3.33 | — |
| Original（fog） | Dijkstra + 边际收益过滤 | 7.06 | 3.33 | 8.37 |
| B Enhanced | 全局贪心 + 5 项增强 | 7.06 | 3.33 | 8.63 |

**关键结论：**
1. 迷雾约束导致步数增加约 1.5× ~ 2×（对比全图版 F）
2. 死胡同惩罚 + 边际收益过滤是雾中最高效的泛化增强
3. 方向动量和前沿回访抑制有效减少岔路震荡
4. BOSS 战贪心最高伤害 + 0 复活即可稳定通关大部分地图
5. 小图上接近全图上界（F），大图上为全图上界的 70%~75%

---

## 五、效果展示与演示（第 5-6 页）

- 网页端运行演示（选择地图 → 选择算法 → 运行/播放）
- 路径回放 + 迷雾逐步揭露
- BOSS 战斗实况展示（视频叠加 + 技能序列）
- 多算法一键对比
- 输出 JSON 下载
