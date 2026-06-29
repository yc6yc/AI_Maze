from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from core.map_loader import find_cell, load_json, parse_skills, validate_map_data
from core.state import (
    COIN_CELLS,
    Action,
    Cell,
    GameContext,
    MazeState,
    Move,
    PlayerState,
    Position,
    Skill,
    WALKABLE_CELLS,
    move_to_delta,
    serialize_fog_map,
)


BossHandler = Callable[["LocalSimulator", Position], bool | dict[str, Any]]

COIN_VALUE = 50
TRAP_DAMAGE = 30
VIEW_RADIUS = 1
BOSS_SEQUENCE_STATE_LIMIT = 50000


class LocalSimulator:
    def __init__(
        self,
        data: dict[str, Any],
        *,
        max_steps: int = 500,
        coin_value: int = COIN_VALUE,
        trap_damage: int = TRAP_DAMAGE,
        view_radius: int = VIEW_RADIUS,
        boss_handler: BossHandler | None = None,
        boss_healths: list[int] | None = None,
        boss_source: str | None = None,
        boss_healths_revealed: bool = False,
    ) -> None:
        validate_map_data(data)
        self.data = deepcopy(data)
        self.ground_truth: list[list[str]] = deepcopy(data["maze"])
        self.rows = len(self.ground_truth)
        self.cols = len(self.ground_truth[0])
        self.start = find_cell(self.ground_truth, "S")
        self.end = find_cell(self.ground_truth, "E")
        self.max_steps = max_steps
        self.coin_value = coin_value
        self.trap_damage = trap_damage
        self.view_radius = view_radius
        self.boss_positions = self._scan_bosses()
        map_boss_healths = normalize_boss_healths(data.get("B"))
        requested_boss_source = (boss_source or "auto").lower()
        if requested_boss_source not in {"auto", "map", "manual"}:
            raise ValueError("boss_source must be auto, map, or manual")
        if requested_boss_source == "manual":
            self.boss_health_source = "manual"
            self.boss_health_sequence = normalize_boss_healths(boss_healths)
        elif requested_boss_source == "map":
            if not map_boss_healths:
                raise ValueError("Boss source is map, but the map has no Boss health array")
            self.boss_health_source = "map"
            self.boss_health_sequence = map_boss_healths
        elif map_boss_healths:
            self.boss_health_source = "map"
            self.boss_health_sequence = map_boss_healths
        else:
            self.boss_health_source = "manual"
            self.boss_health_sequence = normalize_boss_healths(boss_healths)
        self._validate_boss_health_sequence()
        self.boss_battle_after_maze = False
        self.awaiting_boss_input = False
        self.pending_boss_pos: Position | None = None
        self.manual_boss_input_closed = False
        self.manual_boss_replan_required = False
        self.min_rounds = int(data.get("minRouds", 20))
        self.coin_consumption = int(data.get("CoinConsumption", 0))
        self.boss_handler = boss_handler
        self.defeated_boss_count = 0
        self.encountered_boss_count = 0
        self.boss_total_rounds_used = 0
        self.boss_attempt_counts: dict[int, int] = {}
        self.last_boss_event: dict[str, Any] | None = None
        self.boss_events: list[dict[str, Any]] = []
        self.all_boss_healths_revealed = bool(boss_healths_revealed)

        fog_map: list[list[Cell]] = [[None for _c in range(self.cols)] for _r in range(self.rows)]
        maze_state = MazeState(
            rows=self.rows,
            cols=self.cols,
            fog_map=fog_map,
            start=self.start,
            end=self.end,
        )
        player = PlayerState(pos=self.start, coins=0, skills=parse_skills(data))
        self.ctx = GameContext(
            maze=maze_state,
            player=player,
            boss_healths=[],
            min_rounds=self.min_rounds,
            coin_consumption=self.coin_consumption,
            max_steps=max_steps,
        )
        self._reveal_fov(self.start)
        self._append_snapshot({"type": "start", "message": "simulation started"})

    @classmethod
    def from_json(cls, path: str | Path, **kwargs: Any) -> "LocalSimulator":
        return cls(load_json(path), **kwargs)

    def step(self, action: Action) -> dict[str, Any]:
        if self.ctx.done or self.awaiting_boss_input:
            return self.snapshot()

        self.last_boss_event = None
        self.ctx.last_event = None
        self.ctx.step_count += 1
        self.ctx.player.rounds += 1
        action = action or Action()
        manual_boss_target = self._manual_boss_input_target(action)
        combat_target = None if manual_boss_target is not None else self._combat_target(action)
        if manual_boss_target is not None:
            self.ctx.player.pos = manual_boss_target
            self._request_manual_boss_input(manual_boss_target)
            self._reveal_fov(manual_boss_target)
        elif combat_target is not None:
            self._handle_boss(combat_target)
            self._reveal_fov(self.ctx.player.pos)
        else:
            self._apply_move(action.normalized_move())

        if self.ctx.step_count >= self.max_steps and not self.ctx.done:
            self.ctx.done = True
            self.ctx.result = "timeout"
            self.ctx.last_event = {"type": "timeout", "message": "maximum steps reached"}

        self._append_snapshot(self.ctx.last_event)
        return self.snapshot()

    def run(self, agent: Any, max_rounds: int | None = None) -> dict[str, Any]:
        limit = max_rounds or self.max_steps
        while not self.ctx.done and not self.awaiting_boss_input and self.ctx.step_count < limit:
            action = agent.decide(self.ctx)
            self.step(action)
        return self.summary()

    def submit_manual_boss_health(self, boss_health: int, *, reveal_all: bool = False) -> dict[str, Any]:
        if self.boss_health_source != "manual":
            raise ValueError("Boss health can only be submitted in manual boss mode")
        if not self.awaiting_boss_input or self.pending_boss_pos is None:
            raise ValueError("The player is not waiting for manual Boss input")
        if self.ctx.done and self.ctx.result == "lose":
            raise ValueError("Cannot submit Boss health after the run has failed")
        if self.manual_boss_replan_required:
            raise ValueError("Known Bosses must be replanned before adding another Boss health")
        if boss_health <= 0:
            raise ValueError("Boss health must be greater than 0")

        self.boss_health_sequence.append(int(boss_health))
        if reveal_all:
            self.all_boss_healths_revealed = True
        self.ctx.boss_defeated = False
        self.awaiting_boss_input = False
        self.manual_boss_input_closed = False
        self.ctx.last_event = None
        self.last_boss_event = None

        self._handle_boss(self.pending_boss_pos)
        if not self.ctx.done:
            self.awaiting_boss_input = True
            if self.manual_boss_replan_required:
                self.ctx.last_event = {
                    "type": "manual_boss_replan_required",
                    "pos": list(self.pending_boss_pos),
                    "message": "known Boss sequence exceeded round limit; replan before entering another Boss",
                    "known_boss_count": len(self.boss_health_sequence),
                }
            else:
                self.ctx.last_event = {
                    "type": "boss_input_required",
                    "pos": list(self.pending_boss_pos),
                    "message": "waiting for next Boss health; input -1 to finish",
                    "known_boss_count": len(self.boss_health_sequence),
                }
        self._append_snapshot(self.ctx.last_event)
        return self.snapshot()

    def replan_manual_boss_sequence(self) -> dict[str, Any]:
        if self.boss_health_source != "manual":
            raise ValueError("Manual Boss replan can only be used in manual boss mode")
        if not self.awaiting_boss_input or self.pending_boss_pos is None:
            raise ValueError("The player is not waiting for manual Boss input")
        if self.ctx.done and self.ctx.result == "lose":
            raise ValueError("Cannot replan Boss sequence after the run has failed")
        if not self.manual_boss_replan_required:
            raise ValueError("There is no manual Boss sequence waiting for replan")
        if not self.boss_health_sequence:
            raise ValueError("There are no known Boss healths to replan")

        self.awaiting_boss_input = False
        self.manual_boss_input_closed = False
        self.all_boss_healths_revealed = True
        self.defeated_boss_count = 0
        self.ctx.boss_defeated = False
        self.boss_total_rounds_used = 0
        self._reset_skill_cooldowns()
        self.ctx.last_event = None
        self.last_boss_event = None

        self._handle_boss(self.pending_boss_pos)
        if not self.ctx.done:
            self.awaiting_boss_input = True
            self.ctx.last_event = {
                "type": "manual_boss_replan_required" if self.manual_boss_replan_required else "boss_input_required",
                "pos": list(self.pending_boss_pos),
                "message": (
                    "known Boss sequence still exceeded round limit; replan again or value will eventually run out"
                    if self.manual_boss_replan_required
                    else "known Boss sequence replanned successfully; waiting for next Boss health"
                ),
                "known_boss_count": len(self.boss_health_sequence),
            }
        self._append_snapshot(self.ctx.last_event)
        return self.snapshot()

    def finish_manual_boss_input(self) -> dict[str, Any]:
        if self.boss_health_source != "manual":
            raise ValueError("Manual Boss input can only be finished in manual boss mode")
        if not self.awaiting_boss_input or self.pending_boss_pos is None:
            raise ValueError("The player is not waiting for manual Boss input")
        if self.ctx.done and self.ctx.result == "lose":
            raise ValueError("Cannot finish Boss input after the run has failed")
        if self.defeated_boss_count < len(self.boss_health_sequence):
            raise ValueError("Known Bosses must be defeated before input can be finished")
        if self.manual_boss_replan_required:
            raise ValueError("Known Bosses must be replanned before input can be finished")

        pos = self.pending_boss_pos
        self.awaiting_boss_input = False
        self.manual_boss_input_closed = True
        self.ctx.maze.defeated_bosses.add(pos)
        r, c = pos
        if self.ground_truth[r][c] == "B":
            self.ground_truth[r][c] = " "
        self.pending_boss_pos = None
        self.ctx.boss_defeated = self._all_bosses_defeated()
        self.ctx.last_event = {
            "type": "boss_input_finished",
            "pos": list(pos),
            "message": "manual Boss input finished; continuing maze exploration",
            "known_boss_count": len(self.boss_health_sequence),
        }
        self._reveal_fov(self.ctx.player.pos)
        self._append_snapshot(self.ctx.last_event)
        return self.snapshot()

    def _apply_move(self, move: str) -> None:
        dr, dc = move_to_delta(move)
        r, c = self.ctx.player.pos
        nxt = (r + dr, c + dc)
        if move == Move.STAY.value:
            self.ctx.last_event = {"type": "wait", "message": "player waited"}
            self._reveal_fov(self.ctx.player.pos)
            return
        if not self._ground_walkable(nxt):
            self.ctx.last_event = {"type": "blocked", "message": f"blocked move to {nxt}"}
            self._reveal_fov(self.ctx.player.pos)
            return

        self.ctx.player.pos = nxt
        self._handle_cell(nxt)
        self._reveal_fov(nxt)

    def _handle_cell(self, pos: Position) -> None:
        r, c = pos
        cell = self.ground_truth[r][c]
        if cell in COIN_CELLS:
            self.ctx.player.coins += self.coin_value
            self.ground_truth[r][c] = " "
            self.ctx.last_event = {
                "type": "coin",
                "pos": list(pos),
                "value": self.coin_value,
                "message": f"collected {self.coin_value} value",
            }
        elif cell == "T":
            self.ctx.player.coins -= self.trap_damage
            self.ground_truth[r][c] = " "
            self.ctx.maze.triggered_traps.add(pos)
            self.ctx.last_event = {
                "type": "trap",
                "pos": list(pos),
                "value": -self.trap_damage,
                "message": f"trap cost {self.trap_damage} value",
            }
        elif cell == "B":
            if self.boss_health_source == "manual":
                self._request_manual_boss_input(pos)
            else:
                self._handle_boss(pos)
        elif cell == "E":
            if self._exit_unlocked():
                self.ctx.done = True
                self.ctx.result = "win"
                self.ctx.boss_defeated = True
                self.ctx.last_event = {"type": "win", "pos": list(pos), "message": "exit reached"}
            else:
                self.ctx.last_event = {
                    "type": "exit_locked",
                    "pos": list(pos),
                    "message": "exit locked until bosses are defeated",
                }
        else:
            self.ctx.last_event = {"type": "move", "pos": list(pos), "message": "moved"}

    def _handle_boss(self, pos: Position) -> None:
        total_rounds_used = self.boss_total_rounds_used
        target_count = self._manual_visible_boss_target_count() if self.boss_health_source == "manual" else None
        while not self._all_bosses_defeated(target_count) and not self.ctx.done:
            health_idx = self._current_boss_index()
            health = self.boss_health_sequence[health_idx]
            self.encountered_boss_count = max(self.encountered_boss_count, health_idx + 1)

            while not self.ctx.done:
                attempt_no = self.boss_attempt_counts.get(health_idx, 0) + 1
                self.boss_attempt_counts[health_idx] = attempt_no
                value_before = self.ctx.player.coins
                rounds_remaining = max(self.min_rounds - total_rounds_used, 0)
                battle = self._boss_battle_trace(health_idx, rounds_remaining)
                if self.boss_handler:
                    handled = self.boss_handler(self, pos)
                    if isinstance(handled, dict):
                        battle = {**battle, **handled}
                    else:
                        battle["result"] = "win" if handled else "lose"
                self._apply_battle_cooldowns(battle)
                total_rounds_after = total_rounds_used + battle["rounds_used"]
                base_event = self._build_boss_event(
                    pos,
                    health_idx,
                    health,
                    attempt_no,
                    value_before,
                    battle,
                    total_rounds_before=total_rounds_used,
                    total_rounds_after=total_rounds_after,
                    round_limit=rounds_remaining,
                )

                if battle["result"] == "win":
                    total_rounds_used = total_rounds_after
                    self.boss_total_rounds_used = total_rounds_used
                    self.defeated_boss_count += 1
                    self.ctx.boss_defeated = self._all_bosses_defeated()
                    if self.boss_health_source == "manual" and self._all_bosses_defeated(target_count):
                        self.manual_boss_replan_required = False
                    if self.boss_health_source != "manual" and self._all_bosses_defeated():
                        self._clear_boss_cells()
                    self.last_boss_event = {
                        **base_event,
                        "coins_after": self.ctx.player.coins,
                        "value_after": self.ctx.player.coins,
                        "message": "boss defeated",
                    }
                    self.ctx.last_event = self.last_boss_event
                    self.boss_events.append(deepcopy(self.last_boss_event))
                    break

                value_after, actual_cost = self._consume_revive_value(value_before)
                self.ctx.player.coins = value_after
                can_revive = self.coin_consumption > 0 and value_after > 0
                manual_replan_wait = self.boss_health_source == "manual" and can_revive
                cooldowns_after_revive = [0 for _skill in self.ctx.player.skills] if can_revive else None
                known_boss_healths_after_revive = (
                    self._boss_health_records(
                        known_count=len(self.boss_health_sequence),
                        defeated_count=0,
                    )
                    if can_revive
                    else None
                )
                self.last_boss_event = {
                    **base_event,
                    "revived": can_revive,
                    "revive_cost": actual_cost,
                    "required_revive_cost": max(self.coin_consumption, 0),
                    "coins_delta": value_after - value_before,
                    "value_delta": value_after - value_before,
                    "revive": {
                        "used": can_revive,
                        "cost": actual_cost,
                        "required_cost": max(self.coin_consumption, 0),
                        "coins_before": value_before,
                        "coins_after": value_after,
                        "value_before": value_before,
                        "value_after": value_after,
                    },
                    "cost": actual_cost,
                    "coins_after": value_after,
                    "value_after": value_after,
                    "message": (
                        "known Boss sequence exceeded total round limit, revived; waiting for manual replan"
                        if manual_replan_wait
                        else
                        "boss challenge failed, revived; restarted from Boss #1"
                        if can_revive
                        else "boss challenge failed, value exhausted"
                    ),
                    "rounds_reset_on_revive": can_revive,
                    "boss_sequence_reset_on_revive": can_revive,
                    "restart_boss_order": 1 if can_revive else None,
                    "skill_cooldowns_reset_on_revive": can_revive,
                    "cooldowns_after_revive": cooldowns_after_revive,
                    "boss_healths_revealed_on_revive": can_revive,
                    "known_boss_healths_after_revive": known_boss_healths_after_revive,
                    "manual_input_required_after_revive": manual_replan_wait,
                    "manual_replan_required_after_revive": manual_replan_wait,
                }
                self.ctx.last_event = self.last_boss_event
                self.boss_events.append(deepcopy(self.last_boss_event))
                if not can_revive:
                    self.boss_total_rounds_used = total_rounds_after
                    self.ctx.done = True
                    self.ctx.result = "lose"
                    break
                self._reset_skill_cooldowns()
                total_rounds_used = 0
                self.boss_total_rounds_used = 0
                if self.boss_health_source == "manual":
                    self.all_boss_healths_revealed = True
                    self.defeated_boss_count = 0
                    self.manual_boss_replan_required = True
                    self.ctx.boss_defeated = self._all_bosses_defeated()
                    return
                self.all_boss_healths_revealed = True
                self.defeated_boss_count = 0
                self.ctx.boss_defeated = False
                break

    def _build_boss_event(
        self,
        pos: Position,
        health_idx: int,
        health: int,
        attempt_no: int,
        value_before: int,
        battle: dict[str, Any],
        *,
        total_rounds_before: int,
        total_rounds_after: int,
        round_limit: int,
    ) -> dict[str, Any]:
        rounds_remaining_after = max(self.min_rounds - total_rounds_after, 0)
        return {
            "type": "boss",
            "result": battle["result"],
            "pos": list(pos),
            "boss_index": health_idx,
            "encounter_order": health_idx + 1,
            "attempt": attempt_no,
            "health": health,
            "initial_health": battle["initial_health"],
            "remaining_health": battle["remaining_health"],
            "total_damage": battle["total_damage"],
            "rounds_used": battle["rounds_used"],
            "max_rounds": self.min_rounds,
            "total_max_rounds": self.min_rounds,
            "round_limit": round_limit,
            "total_rounds_before": total_rounds_before,
            "total_rounds_used": total_rounds_after,
            "rounds_remaining_before": max(self.min_rounds - total_rounds_before, 0),
            "rounds_remaining_after": rounds_remaining_after,
            "rounds": battle["rounds"],
            "skills": battle["skills"],
            "final_cooldowns": battle.get("final_cooldowns", []),
            "planning_mode": battle.get("planning_mode", "current_boss"),
            "planned_boss_orders": battle.get("planned_boss_orders", [health_idx + 1]),
            "planned_boss_healths": battle.get("planned_boss_healths", [health]),
            "planned_sequence_result": battle.get("planned_sequence_result", battle["result"]),
            "planned_sequence_rounds": battle.get("planned_sequence_rounds", battle["rounds_used"]),
            "planned_sequence_defeated": battle.get("planned_sequence_defeated", 1 if battle["result"] == "win" else 0),
            "coins_before": value_before,
            "coins_after": value_before,
            "value_before": value_before,
            "value_after": value_before,
            "revived": False,
            "revive_cost": 0,
            "required_revive_cost": max(self.coin_consumption, 0),
            "coins_delta": 0,
            "value_delta": 0,
            "revive": {
                "used": False,
                "cost": 0,
                "required_cost": max(self.coin_consumption, 0),
                "coins_before": value_before,
                "coins_after": value_before,
                "value_before": value_before,
                "value_after": value_before,
            },
            "maze_step": self.ctx.step_count,
        }

    def _consume_revive_value(self, value_before: int) -> tuple[int, int]:
        required_cost = max(self.coin_consumption, 0)
        if required_cost <= 0 or value_before <= 0:
            return value_before, 0
        if value_before > 0 and value_before <= required_cost:
            return 0, value_before
        return value_before - required_cost, required_cost

    def default_boss_handler(self, pos: Position) -> bool:
        health_idx = self._current_boss_index()
        health = self.boss_health_sequence[health_idx]
        return can_defeat_boss(self.ctx.player.skills, health, self.min_rounds)

    def _boss_battle_trace(self, health_idx: int, round_limit: int) -> dict[str, Any]:
        health = self.boss_health_sequence[health_idx]
        if not self.all_boss_healths_revealed:
            battle = simulate_boss_battle(self.ctx.player.skills, health, round_limit)
            battle["planning_mode"] = "current_boss"
            battle["planned_boss_orders"] = [health_idx + 1]
            battle["planned_boss_healths"] = [health]
            battle["planned_sequence_result"] = battle["result"]
            battle["planned_sequence_rounds"] = battle["rounds_used"]
            battle["planned_sequence_defeated"] = 1 if battle["result"] == "win" else 0
            return battle

        known_healths = self.boss_health_sequence[health_idx:]
        sequence_plan = _plan_boss_sequence(self.ctx.player.skills, known_healths, round_limit)
        current_plan = _first_boss_plan_segment(self.ctx.player.skills, health, sequence_plan)
        battle = _simulate_boss_battle_with_plan(self.ctx.player.skills, health, current_plan)
        sequence_preview = _preview_boss_sequence_plan(self.ctx.player.skills, known_healths, sequence_plan)
        battle["planning_mode"] = "known_sequence"
        battle["planned_boss_orders"] = list(range(health_idx + 1, len(self.boss_health_sequence) + 1))
        battle["planned_boss_healths"] = known_healths
        battle["planned_sequence_result"] = sequence_preview["result"]
        battle["planned_sequence_rounds"] = sequence_preview["rounds_used"]
        battle["planned_sequence_defeated"] = sequence_preview["defeated_count"]
        return battle

    def _apply_battle_cooldowns(self, battle: dict[str, Any]) -> None:
        final_cooldowns = battle.get("final_cooldowns")
        if not isinstance(final_cooldowns, list):
            return
        for skill, cooldown in zip(self.ctx.player.skills, final_cooldowns):
            skill.remaining_cooldown = max(int(cooldown), 0)

    def _reset_skill_cooldowns(self) -> None:
        for skill in self.ctx.player.skills:
            skill.remaining_cooldown = 0

    def _current_boss_index(self) -> int:
        if self._all_bosses_defeated():
            raise ValueError("Boss health sequence is exhausted")
        return self.defeated_boss_count

    def _all_bosses_defeated(self, target_count: int | None = None) -> bool:
        return self.defeated_boss_count >= (len(self.boss_health_sequence) if target_count is None else target_count)

    def _manual_visible_boss_target_count(self) -> int:
        return len(self.boss_health_sequence)

    def _exit_unlocked(self) -> bool:
        if self.boss_health_source == "manual":
            return self.manual_boss_input_closed and self._all_bosses_defeated()
        return self._all_bosses_defeated()

    def _clear_boss_cells(self) -> None:
        for pos in self.boss_positions:
            self.ctx.maze.defeated_bosses.add(pos)
            r, c = pos
            if self.ground_truth[r][c] == "B":
                self.ground_truth[r][c] = " "

    def _neutralize_maze_boss_cells(self) -> None:
        for r, c in self.boss_positions:
            if self.ground_truth[r][c] == "B":
                self.ground_truth[r][c] = " "

    def _validate_boss_health_sequence(self) -> None:
        boss_cell_count = len(self.boss_positions)
        health_count = len(self.boss_health_sequence)
        if boss_cell_count == 0 and health_count == 0:
            return
        if self.boss_health_source == "manual":
            return
        if boss_cell_count == 0 and health_count > 0:
            raise ValueError("Boss healths were provided, but the maze has no B cells")
        if health_count == 0:
            raise ValueError("Boss health array is missing; switch to manual live Boss input")

    def _tick_cooldowns(self, used_skill: int | None = None) -> None:
        for idx, skill in enumerate(self.ctx.player.skills):
            if used_skill == idx:
                skill.remaining_cooldown = skill.cooldown
            elif skill.remaining_cooldown > 0:
                skill.remaining_cooldown -= 1

    def _reveal_fov(self, center: Position) -> None:
        cr, cc = center
        for r in range(cr - self.view_radius, cr + self.view_radius + 1):
            for c in range(cc - self.view_radius, cc + self.view_radius + 1):
                pos = (r, c)
                if not self.ctx.maze.in_bounds(pos):
                    continue
                self.ctx.maze.fog_map[r][c] = self.ground_truth[r][c]

    def _ground_walkable(self, pos: Position) -> bool:
        r, c = pos
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return False
        return self.ground_truth[r][c] in WALKABLE_CELLS

    def _combat_target(self, action: Action) -> Position | None:
        if self._all_bosses_defeated() or self.boss_health_source == "manual":
            return None
        candidates = [self.ctx.player.pos]
        r, c = self.ctx.player.pos
        candidates.extend([(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)])
        for pos in candidates:
            pr, pc = pos
            if not (0 <= pr < self.rows and 0 <= pc < self.cols and self.ground_truth[pr][pc] == "B"):
                continue
            if action.use_skill is not None:
                return pos
            if action.normalized_move() == Move.STAY.value:
                return pos
        return None

    def _manual_boss_input_target(self, action: Action) -> Position | None:
        if self.boss_health_source != "manual" or self.awaiting_boss_input:
            return None
        if action.use_skill is None and action.normalized_move() != Move.STAY.value:
            return None
        r, c = self.ctx.player.pos
        for pos in (self.ctx.player.pos, (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            pr, pc = pos
            if 0 <= pr < self.rows and 0 <= pc < self.cols and self.ground_truth[pr][pc] == "B":
                return pos
        return None

    def _request_manual_boss_input(self, pos: Position) -> None:
        self.awaiting_boss_input = True
        self.manual_boss_input_closed = False
        self.pending_boss_pos = pos
        self.ctx.last_event = {
            "type": "boss_input_required",
            "pos": list(pos),
            "message": "waiting for current Boss health",
            "known_boss_count": len(self.boss_health_sequence),
        }

    def _scan_bosses(self) -> list[Position]:
        result: list[Position] = []
        for r, row in enumerate(self.ground_truth):
            for c, cell in enumerate(row):
                if cell == "B":
                    result.append((r, c))
        return result

    def _append_snapshot(self, event: dict[str, Any] | None) -> None:
        self.ctx.history.append(self.snapshot(event=event, include_history=False))

    def snapshot(self, *, event: dict[str, Any] | None = None, include_history: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "step": self.ctx.step_count,
            "pos": list(self.ctx.player.pos),
            "coins": self.ctx.player.coins,
            "value": self.ctx.player.coins,
            "total_value": self.ctx.player.coins,
            "fog_map": serialize_fog_map(self.ctx.maze.fog_map),
            "done": self.ctx.done,
            "result": self.ctx.result,
            "boss_defeated": self._all_bosses_defeated(),
            "defeated_bosses": [list(pos) for pos in sorted(self.ctx.maze.defeated_bosses)],
            "event": event if event is not None else self.ctx.last_event,
            "boss_event": self.last_boss_event,
            "boss_events": deepcopy(self.boss_events),
            "boss_health_source": self.boss_health_source if (self.boss_health_sequence or self.boss_health_source == "manual") else "none",
            "awaiting_boss_input": self.awaiting_boss_input,
            "pending_boss_pos": list(self.pending_boss_pos) if self.pending_boss_pos else None,
            "manual_boss_input_closed": self.manual_boss_input_closed,
            "manual_boss_replan_required": self.manual_boss_replan_required,
            "encountered_bosses": self.encountered_boss_count,
            "defeated_boss_count": self.defeated_boss_count,
            "all_boss_healths_revealed": self.all_boss_healths_revealed,
            "known_boss_healths": self._known_boss_healths(),
            "current_boss_health": self._current_boss_health(),
            "skills": [
                {
                    "damage": skill.damage,
                    "cooldown": skill.cooldown,
                    "remaining_cooldown": skill.remaining_cooldown,
                }
                for skill in self.ctx.player.skills
            ],
        }
        if include_history:
            data["history"] = self.ctx.history
        return data

    def _known_boss_healths(self) -> list[dict[str, Any]]:
        known_count = len(self.boss_health_sequence) if self.all_boss_healths_revealed else self.encountered_boss_count
        return self._boss_health_records(known_count=known_count, defeated_count=self.defeated_boss_count)

    def _boss_health_records(self, *, known_count: int, defeated_count: int) -> list[dict[str, Any]]:
        known_count = min(max(known_count, 0), len(self.boss_health_sequence))
        defeated_count = min(max(defeated_count, 0), len(self.boss_health_sequence))
        result: list[dict[str, Any]] = []
        for idx, health in enumerate(self.boss_health_sequence[:known_count]):
            if idx < defeated_count:
                status = "defeated"
            elif idx == defeated_count and defeated_count < len(self.boss_health_sequence):
                status = "current"
            else:
                status = "known"
            result.append(
                {
                    "order": idx + 1,
                    "health": health,
                    "status": status,
                }
            )
        return result

    def _current_boss_health(self) -> dict[str, Any] | None:
        if self.defeated_boss_count >= self.encountered_boss_count:
            return None
        idx = self.defeated_boss_count
        if idx >= len(self.boss_health_sequence):
            return None
        return {"order": idx + 1, "health": self.boss_health_sequence[idx], "status": "current"}

    def summary(self) -> dict[str, Any]:
        return {
            **self.snapshot(include_history=False),
            "total_steps": self.ctx.step_count,
            "total_value": self.ctx.player.coins,
            "score": self.ctx.player.coins / max(self.ctx.step_count, 1),
        }


def can_defeat_boss(skills: list[Skill], health: int, min_rounds: int) -> bool:
    return simulate_boss_battle(skills, health, min_rounds)["result"] == "win"


def normalize_boss_healths(raw: Any) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Boss healths must be an array")
    result: list[int] = []
    for idx, value in enumerate(raw):
        try:
            health = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Boss health at index {idx} must be an integer") from exc
        if health <= 0:
            raise ValueError(f"Boss health at index {idx} must be greater than 0")
        result.append(health)
    return result


def simulate_boss_battle(skills: list[Skill], health: int, min_rounds: int) -> dict[str, Any]:
    skill_states = [skill.clone() for skill in skills]
    skill_defs = [
        {
            "skill_index": idx,
            "damage": skill.damage,
            "cooldown": skill.cooldown,
            "initial_remaining_cooldown": skill.remaining_cooldown,
        }
        for idx, skill in enumerate(skill_states)
    ]
    plan = _plan_boss_battle(skill_states, health, min_rounds)
    rounds, remaining, final_cooldowns = _build_boss_rounds(skill_states, health, plan)

    return {
        "result": "win" if remaining <= 0 else "lose",
        "initial_health": health,
        "remaining_health": max(remaining, 0),
        "total_damage": max(health - max(remaining, 0), 0),
        "rounds_used": len(rounds),
        "rounds": rounds,
        "skills": skill_defs,
        "final_cooldowns": final_cooldowns,
    }


def _simulate_boss_battle_with_plan(skills: list[Skill], health: int, plan: list[int | None]) -> dict[str, Any]:
    skill_states = [skill.clone() for skill in skills]
    skill_defs = [
        {
            "skill_index": idx,
            "damage": skill.damage,
            "cooldown": skill.cooldown,
            "initial_remaining_cooldown": skill.remaining_cooldown,
        }
        for idx, skill in enumerate(skill_states)
    ]
    rounds, remaining, final_cooldowns = _build_boss_rounds(skill_states, health, plan)
    return {
        "result": "win" if remaining <= 0 else "lose",
        "initial_health": health,
        "remaining_health": max(remaining, 0),
        "total_damage": max(health - max(remaining, 0), 0),
        "rounds_used": len(rounds),
        "rounds": rounds,
        "skills": skill_defs,
        "final_cooldowns": final_cooldowns,
    }


def _plan_boss_battle(skills: list[Skill], health: int, min_rounds: int) -> list[int | None]:
    return _plan_boss_sequence(skills, [health], min_rounds)


def _plan_boss_sequence(skills: list[Skill], healths: list[int], min_rounds: int) -> list[int | None]:
    max_rounds = max(min_rounds, 0)
    if not healths or max_rounds <= 0:
        return []

    # Dynamic programming over battle rounds. For each layer we keep the best
    # remaining HP reachable for a compact state: current boss + all skill CDs.
    # At the same round, lower remaining HP dominates the same boss/CD state.
    initial_cooldowns = tuple(max(skill.remaining_cooldown, 0) for skill in skills)
    dp: dict[tuple[int, tuple[int, ...]], tuple[int, list[int | None]]] = {
        (0, initial_cooldowns): (healths[0], [])
    }
    best_partial: tuple[int, int, list[int | None]] = (0, healths[0], [])

    for _round_no in range(1, max_rounds + 1):
        next_states: dict[tuple[int, tuple[int, ...]], tuple[int, list[int | None]]] = {}
        winning_plans: list[list[int | None]] = []
        for (boss_idx, cooldowns), (remaining_health, plan) in dp.items():
            for choice in _boss_planner_choices(skills, cooldowns):
                new_plan = [*plan, choice]
                new_boss_idx = boss_idx
                new_remaining = remaining_health
                if choice is not None:
                    new_remaining -= skills[choice].damage
                    if new_remaining <= 0:
                        new_boss_idx += 1
                        if new_boss_idx >= len(healths):
                            winning_plans.append(new_plan)
                            continue
                        new_remaining = healths[new_boss_idx]
                candidate_partial = (new_boss_idx, new_remaining, new_plan)
                if _is_better_boss_partial(candidate_partial, best_partial):
                    best_partial = candidate_partial

                new_cooldowns = _advance_boss_cooldowns(skills, cooldowns, choice)
                key = (new_boss_idx, new_cooldowns)
                _store_boss_dp_state(next_states, key, new_remaining, new_plan)

        if winning_plans:
            return min(winning_plans, key=_plan_tiebreak)
        if len(next_states) > BOSS_SEQUENCE_STATE_LIMIT:
            next_states = _trim_boss_sequence_states(next_states)
        dp = next_states
        if not dp:
            break
    return best_partial[2]


def _store_boss_dp_state(
    states: dict[tuple[int, tuple[int, ...]], tuple[int, list[int | None]]],
    key: tuple[int, tuple[int, ...]],
    remaining_health: int,
    plan: list[int | None],
) -> None:
    current = states.get(key)
    if current is None or remaining_health < current[0] or (
        remaining_health == current[0] and _plan_tiebreak(plan) < _plan_tiebreak(current[1])
    ):
        states[key] = (remaining_health, plan)


def _is_better_boss_partial(
    candidate: tuple[int, int, list[int | None]],
    current: tuple[int, int, list[int | None]],
) -> bool:
    candidate_boss_idx, candidate_remaining, candidate_plan = candidate
    current_boss_idx, current_remaining, current_plan = current
    if candidate_boss_idx != current_boss_idx:
        return candidate_boss_idx > current_boss_idx
    if candidate_remaining != current_remaining:
        return candidate_remaining < current_remaining
    if len(candidate_plan) != len(current_plan):
        return len(candidate_plan) > len(current_plan)
    return _plan_tiebreak(candidate_plan) < _plan_tiebreak(current_plan)


def _boss_planner_choices(skills: list[Skill], cooldowns: tuple[int, ...]) -> list[int | None]:
    ready = [idx for idx, cooldown in enumerate(cooldowns) if cooldown <= 0]
    choices: list[int | None] = []
    for idx in sorted(ready, key=lambda item: (-skills[item].damage, skills[item].cooldown, item)):
        skill = skills[idx]
        dominated = False
        for other_idx in ready:
            if other_idx == idx:
                continue
            other = skills[other_idx]
            if other.damage >= skill.damage and other.cooldown <= skill.cooldown and (
                other.damage > skill.damage or other.cooldown < skill.cooldown or other_idx < idx
            ):
                dominated = True
                break
        if not dominated:
            choices.append(idx)
    if not choices or any(cooldown > 0 for cooldown in cooldowns):
        choices.append(None)
    return choices


def _plan_tiebreak(plan: list[int | None]) -> tuple[int, int, tuple[int, ...]]:
    waits = sum(1 for item in plan if item is None)
    skill_order = tuple(9999 if item is None else item for item in plan)
    return (waits, len(plan), skill_order)


def _trim_boss_sequence_states(
    states: dict[tuple[int, tuple[int, ...]], tuple[int, list[int | None]]],
) -> dict[tuple[int, tuple[int, ...]], tuple[int, list[int | None]]]:
    ranked = sorted(
        states.items(),
        key=lambda item: (
            -item[0][0],
            item[1][0],
            sum(item[0][1]),
            _plan_tiebreak(item[1][1]),
        ),
    )
    return dict(ranked[:BOSS_SEQUENCE_STATE_LIMIT])


def _first_boss_plan_segment(skills: list[Skill], health: int, plan: list[int | None]) -> list[int | None]:
    cooldowns = tuple(max(skill.remaining_cooldown, 0) for skill in skills)
    remaining = health
    segment: list[int | None] = []
    for choice in plan:
        segment.append(choice)
        if choice is not None:
            remaining -= skills[choice].damage
        cooldowns = _advance_boss_cooldowns(skills, cooldowns, choice)
        if remaining <= 0:
            break
    return segment


def _preview_boss_sequence_plan(skills: list[Skill], healths: list[int], plan: list[int | None]) -> dict[str, Any]:
    cooldowns = tuple(max(skill.remaining_cooldown, 0) for skill in skills)
    boss_idx = 0
    remaining = healths[0] if healths else 0
    for choice in plan:
        if boss_idx >= len(healths):
            break
        if choice is not None:
            remaining -= skills[choice].damage
            if remaining <= 0:
                boss_idx += 1
                remaining = healths[boss_idx] if boss_idx < len(healths) else 0
        cooldowns = _advance_boss_cooldowns(skills, cooldowns, choice)
    return {
        "result": "win" if boss_idx >= len(healths) else "lose",
        "rounds_used": len(plan),
        "defeated_count": boss_idx,
        "remaining_health": max(remaining, 0),
        "final_cooldowns": list(cooldowns),
    }


def _advance_boss_cooldowns(skills: list[Skill], cooldowns: tuple[int, ...], used_idx: int | None) -> tuple[int, ...]:
    next_cooldowns = list(cooldowns)
    if used_idx is not None:
        next_cooldowns[used_idx] = skills[used_idx].cooldown
    for idx, cooldown in enumerate(next_cooldowns):
        if idx != used_idx and cooldown > 0:
            next_cooldowns[idx] = cooldown - 1
    return tuple(max(cooldown, 0) for cooldown in next_cooldowns)


def _build_boss_rounds(
    skills: list[Skill],
    health: int,
    plan: list[int | None],
) -> tuple[list[dict[str, Any]], int, list[int]]:
    cooldowns = tuple(max(skill.remaining_cooldown, 0) for skill in skills)
    remaining = health
    rounds: list[dict[str, Any]] = []
    for round_no, used_idx in enumerate(plan, start=1):
        cooldowns_before = list(cooldowns)
        ready = [idx for idx, cooldown in enumerate(cooldowns) if cooldown <= 0]
        hp_before = remaining
        if used_idx is not None:
            damage = skills[used_idx].damage
            remaining -= damage
            action = {
                "round": round_no,
                "action": "attack",
                "skill_index": used_idx,
                "skill_label": f"Skill #{used_idx + 1}",
                "damage": damage,
                "hp_before": hp_before,
                "hp_after": max(remaining, 0),
                "ready_skills": ready,
                "cooldowns_before": cooldowns_before,
            }
        else:
            action = {
                "round": round_no,
                "action": "wait",
                "skill_index": None,
                "skill_label": None,
                "damage": 0,
                "hp_before": hp_before,
                "hp_after": max(remaining, 0),
                "ready_skills": ready,
                "cooldowns_before": cooldowns_before,
            }
        cooldowns = _advance_boss_cooldowns(skills, cooldowns, used_idx)
        action["cooldowns_after"] = list(cooldowns)
        rounds.append(action)
        if remaining <= 0:
            break
    return rounds, remaining, list(cooldowns)
