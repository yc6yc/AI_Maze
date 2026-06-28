from __future__ import annotations

from abc import ABC, abstractmethod

from core.state import Action, GameContext


class BaseAgent(ABC):
    @abstractmethod
    def decide(self, ctx: GameContext) -> Action:
        raise NotImplementedError
