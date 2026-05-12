"""
base_agent.py — 所有 Agent 的抽象基类
负责人：组长（角色1）
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from core.state import GameContext, Action


class BaseAgent(ABC):
    """
    每回合调用 decide(ctx) 返回一个 Action。
    子类须实现 decide() 方法。
    """

    def __init__(self, name: str = "BaseAgent"):
        self.name = name

    @abstractmethod
    def decide(self, ctx: GameContext) -> Action:
        """
        根据当前游戏上下文决定本回合动作。
        :param ctx: 当前 GameContext（含迷宫、玩家状态等）
        :return: Action
        """
        ...

    def on_episode_start(self, ctx: GameContext):
        """每局开始时的初始化钩子（可选覆盖）"""
        pass

    def on_episode_end(self, ctx: GameContext):
        """每局结束时的收尾钩子（可选覆盖）"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name!r}>"
