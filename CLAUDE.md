# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 项目概述

AI Maze 是一个算法课设项目（四人小组），实现 AI 智能体在**战争迷雾（FOG）**限制下走迷宫：从起点 S 到终点 E，沿途拾取金币、躲避陷阱、击败 BOSS。AI 仅能看到玩家周围 3×3 区域，必须基于不完整信息做决策。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 本地模拟一局
python main.py --mode sim --map maze_15_15.json

# 批量评测（N 次取均值/方差）
python main.py --mode eval --map maze_15_15.json --runs 5

# 单元测试
pytest tests/ -v
```

`main.py` 是唯一入口，`--mode` 支持 `sim` / `eval` / `online`（online 为预留，未实现）。地图文件通过 `map_loader.py` 解析路径，可放在 `map/` 或根目录。

## 核心架构

### 数据模型 (`core/state.py`)

所有核心类型均为 `dataclass`：

- **`MazeState`** — `fog_map`（`Optional[str]` 二维数组，`None` = 未探索，`#`/`C`/`T`/`B`/`E`/` ` = 已揭露）；`is_walkable()` 将 `None` 视为不可行走，强制实现战争迷雾约束
- **`PlayerState`** — 当前位置、金币、技能列表（含冷却追踪）
- **`Action`** — 移动方向（`UP/DOWN/LEFT/RIGHT/STAY`）+ 可选技能索引
- **`GameContext`** — 每回合传给 Agent 的完整上下文：`maze`、`player`、`coin_consumption`、`min_rounds`、`boss_defeated`、`history`、`phase`

**关键约束：Agent 只能访问 `ctx.maze.fog_map`，永远接触不到完整地图。**

### 模拟器 (`eval/simulator.py`)

`LocalSimulator` 持有私有 `ground_truth`，每步通过 `_reveal_fov(pos)` 将玩家周围 3×3 真实内容写入 `fog_map`。陷阱触发扣金币、金币拾取清除格子、BOSS 遭遇暂停调用外部战斗处理器。AI 视野半径由 `config.json` 的 `sim.view_radius` 控制（当前为 1）。

### Agent 分层架构

决策入口是 `CompositeAgent`（`agents/composite_agent.py`），按优先级调度：

1. **最高优先级：战斗** — `CombatAgent.should_fight()` 为真时接管，做技能选择决策
2. **RUSH 阶段不可打断** — 全局规划器处于 `RUSH_TO_BOSS` 或 `RUSH_TO_EXIT` 时直接使用全局规划
3. **全局活跃时检查降级** — 全局规划器当前主导时，检查局部贪心是否有正收益格子；有则切换回局部
4. **局部贪心** — 默认使用 `LocalGreedyAgent`，连续返回 `STAY` 达到 `stuck_threshold` 次（默认 2）后激活全局规划器兜底
5. **全局规划器** — 作为兜底策略

**Sub-agents:**
- **`LocalGreedyAgent`** — 扫描 3×3 窗口，按 `(cell_value - step_cost) / dist` 公式打分，选最高分移动
- **`GlobalPlannerAgent`** — 五阶段状态机：`EXPLORE → COLLECT → RUSH_TO_BOSS → RUSH_TO_EXIT`，另有 `RETRY_COLLECT` 恢复阶段。用 BFS 探索前沿、Dijkstra（带陷阱代价加权）寻路到金币/BOSS、A* 冲刺出口
- **`CombatAgent`** — 贪心选最高伤害技能，可选"记忆模式"追踪失败序列以优化重试
- **`GlobalGreedyAgent`** — 替代策略，每回合重新评估所有已知目标（金币、前沿、BOSS、出口），直接选最优路径的第一步

### 寻路 (`core/pathfinding.py`)

三种算法，均接受 `walkable_fn` 来判断格子是否可行走：BFS（无权最短路径）、A*（曼哈顿距离启发式）、Dijkstra（可选 `weight_fn` 自定义边权，用于陷阱惩罚）。

### 配置 (`config.json`)

所有权重和阈值集中于此，分四段：`local`（局部贪心参数）、`global`（全局规划参数）、`sim`（模拟器参数）、`composite`（调度策略，`strategy` 可为 `hybrid` 或 `direct_global`）。

## 已知问题

1. **空地负分** — 局部贪心对已知空格的评分公式 `(raw_value - movement_cost) / dist` 给出约 -10 分，导致 Agent 拒绝穿越开阔走廊，频繁触发全局规划器
2. **`stuck_threshold=2` 过小** — 问题 1 导致局部贪心频繁返回 `STAY`，阈值 2 使全局规划器被过度激活，路径一致性下降。修复问题 1 后此问题应自然缓解

## 分工指引

| 角色 | 负责模块 |
|------|---------|
| 组长/集成 | `core/`、`agents/base_agent.py`、`agents/composite_agent.py`、`main.py` |
| 局部贪心 | `agents/local_greedy_policy.py` |
| 全局规划 | `agents/global_planner.py`、`agents/combat_agent.py` |
| 评测报告 | `eval/`、`viz/`、`tests/`、`config.json` |
