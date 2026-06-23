# AI Maze — 算法课设项目

> 四人小组 · Python · AI 挑战者方向

---

## 目录结构

```
AI_Maze/
├── core/                        # 【组长/角色1】核心数据结构与共享库
│   ├── state.py                 #   统一状态/动作数据结构（MazeState, PlayerState, Action…）
│   ├── api_adapter.py           #   JSON 解析 & 服务器通信适配器
│   └── pathfinding.py           #   BFS / A* / Dijkstra 寻路库
│
├── agents/                      # 智能体模块
│   ├── base_agent.py            # 【组长/角色1】抽象基类
│   ├── local_greedy_policy.py   # 【角色2】3×3 视野局部贪心拾取
│   ├── global_planner.py        # 【角色3】全局探索/收集/冲刺状态机
│   ├── global_greedy.py         #   记忆增强全局贪心
│   ├── combat_agent.py          # 【角色3】技能战斗决策
│   └── composite_agent.py       # 【组长/角色1】组合调度（集成入口）
│
├── eval/                        # 【角色4】评测工具
│   ├── simulator.py             #   本地离线模拟器（FOG 视野模拟）
│   └── eval_runner.py           #   批量跑图 + 均值/方差统计
│
├── viz/                         # 【角色4/2/3】可视化
│   ├── visualizer.py            #   matplotlib 渲染帧/GIF/路径图
│   └── boss_battle_visualizer.py#   Boss 战可视化
│
├── web/                         # Web 可视化面板 → 详见 web/README.md
├── webapp/                      # 预留 Web 应用目录
│
├── tests/                       # 【角色4】单元测试
│   ├── test_pathfinding.py
│   ├── test_simulator.py
│   ├── test_local_greedy_policy.py
│   └── test_combat_agent.py
│
├── map/                         # 地图 JSON 文件
├── config.json                  # 统一参数配置（权重/阈值，由角色4维护）
├── main.py                      # 一键运行入口
├── requirements.txt
└── README.md
```

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 本地模拟一局
python main.py --mode sim --map maze_15_15.json

# 本地模拟 + 生成 GIF
python main.py --mode sim --map maze_15_15.json --visualize

# 本地模拟 + 弹出窗口可视化
python main.py --mode sim --map maze_15_15.json --visualize-window

# 批量评测（5 次）
python main.py --mode eval --map maze_15_15.json --runs 5

# 单元测试
pytest tests/ -v
```

---

## AI 挑战者视野限制

| 信息 | 可见性 |
|------|--------|
| 地图尺寸 | ✅ 已知 |
| 入口 S 坐标 | ✅ 已知 |
| 玩家技能列表 | ✅ 已知 |
| 复活金币消耗 | ✅ 已知 |
| 地图全貌 | ❌ 不可见（仅 3×3 FOG 探索）|
| BOSS 数量与血量 | ❌ 不可见（击败后方可知）|

模拟器通过 `fog_map` 机制严格实现视野限制，AI Agent 只能读取 `ctx.maze.fog_map`。

---

## 分工指引

| 角色 | 负责模块 |
|------|---------|
| 组长/集成 | `core/`、`agents/base_agent.py`、`agents/composite_agent.py`、`main.py` |
| 局部贪心 | `agents/local_greedy_policy.py` |
| 全局规划 | `agents/global_planner.py`、`agents/combat_agent.py` |
| 评测报告 | `eval/`、`viz/`、`tests/`、`config.json` |

---

## 参数调整

所有权重与策略阈值集中在 `config.json`，由角色4统一记录"参数—分数"表。

```json
{
  "local":  { "w_coin": 1.0, "w_trap": 1.0, "w_dist": 0.5 },
  "global": { "w_coin": 2.0, "w_trap": 1.5, "rush_round_threshold": 5 }
}
```


---

## 里程碑

| 周次 | 目标 |
|------|------|
| W1 | 跑通"无资源迷宫到终点"（BFS/A* + 模拟器）|
| W2 | 局部贪心拾取 + 可视化 GIF |
| W3 | 全局策略融合 + 参数可调 + 状态机 |
| W4 | 批量评测、调参、报告定稿 |
