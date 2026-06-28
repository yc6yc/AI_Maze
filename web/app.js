const els = {
  canvas: document.getElementById("mazeCanvas"),
  mapName: document.getElementById("mapName"),
  loadSampleBtn: document.getElementById("loadSampleBtn"),
  fileInput: document.getElementById("fileInput"),
  runBtn: document.getElementById("runBtn"),
  playBtn: document.getElementById("playBtn"),
  bossLayer: document.getElementById("bossLayer"),
  stepsText: document.getElementById("stepsText"),
  coinsText: document.getElementById("coinsText"),
  scoreText: document.getElementById("scoreText"),
  phaseText: document.getElementById("phaseText"),
  eventList: document.getElementById("eventList"),
};

const state = {
  mapData: null,
  frames: [],
  frameIndex: 0,
  playing: false,
  timer: null,
  route: [],
};

const DEFAULT_MAP = {
  maze: [
    ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
    ["#", "S", " ", "C", "#", " ", " ", "C", " ", "B", "E", "#"],
    ["#", " ", "#", " ", "#", " ", "#", "#", " ", "#", " ", "#"],
    ["#", " ", "#", " ", " ", " ", "T", " ", " ", "#", " ", "#"],
    ["#", "C", " ", "#", "#", " ", "#", " ", "C", " ", " ", "#"],
    ["#", "#", " ", " ", "T", " ", "#", " ", "#", "#", " ", "#"],
    ["#", " ", " ", "#", " ", " ", " ", " ", " ", " ", " ", "#"],
    ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
  ],
  B: [70],
  PlayerSkills: [[20, 1], [35, 3], [12, 0]],
  minRouds: 6,
  CoinConsumption: 25,
};

function cellRand(r, c, seed = 91) {
  let n = (r + 1) * 1103515245 + (c + 1) * 12345 + seed * 2654435761;
  n = (n ^ (n >>> 15)) >>> 0;
  return n / 4294967295;
}

function normalizeMapData(data) {
  const bosses = Array.isArray(data.B) ? data.B.map((value) => Number(value)).filter((value) => value > 0) : [];
  return {
    maze: data.maze,
    bosses,
    skills: data.PlayerSkills || [],
    minRounds: data.minRouds || 20,
    coinConsumption: data.CoinConsumption || 0,
  };
}

function findCell(grid, cell) {
  for (let r = 0; r < grid.length; r += 1) {
    for (let c = 0; c < grid[r].length; c += 1) {
      if (grid[r][c] === cell) return [r, c];
    }
  }
  return null;
}

function cloneGrid(grid) {
  return grid.map((row) => row.slice());
}

function buildCombatSkillStates(skillDefs) {
  return skillDefs.map((skill, idx) => ({
    skill_index: idx,
    damage: Number(skill[0] ?? skill.damage ?? 0),
    cooldown: Number(skill[1] ?? skill.cooldown ?? 0),
    remaining: Number(skill.remaining ?? skill.remaining_cooldown ?? 0),
  }));
}

function cooldownKey(cooldowns) {
  return cooldowns.join(",");
}

function advanceCombatCooldowns(skills, cooldowns, usedPos) {
  const next = cooldowns.slice();
  if (usedPos !== null) next[usedPos] = skills[usedPos].cooldown;
  for (let idx = 0; idx < next.length; idx += 1) {
    if (idx !== usedPos && next[idx] > 0) next[idx] -= 1;
    if (next[idx] < 0) next[idx] = 0;
  }
  return next;
}

function planCombat(skills, health, maxRounds) {
  return planBossSequence(skills, [health], maxRounds);
}

function plannerChoices(skills, cooldowns) {
  const ready = cooldowns.map((cooldown, idx) => ({ cooldown, idx })).filter((item) => item.cooldown <= 0).map((item) => item.idx);
  const choices = [];
  for (const idx of ready.sort((a, b) => skills[b].damage - skills[a].damage || skills[a].cooldown - skills[b].cooldown || a - b)) {
    const skill = skills[idx];
    const dominated = ready.some((otherIdx) => {
      if (otherIdx === idx) return false;
      const other = skills[otherIdx];
      return other.damage >= skill.damage && other.cooldown <= skill.cooldown
        && (other.damage > skill.damage || other.cooldown < skill.cooldown || otherIdx < idx);
    });
    if (!dominated) choices.push(idx);
  }
  if (!choices.length || cooldowns.some((cooldown) => cooldown > 0)) choices.push(null);
  return choices;
}

function planTieBreak(plan) {
  const waits = plan.filter((item) => item === null).length;
  const order = plan.map((item) => (item === null ? 9999 : item)).join(",");
  return `${String(waits).padStart(4, "0")}|${String(plan.length).padStart(4, "0")}|${order}`;
}

function trimSequenceStates(states, limit = 50000) {
  return new Map([...states.entries()].sort((a, b) => {
    if (a[1].bossIdx !== b[1].bossIdx) return b[1].bossIdx - a[1].bossIdx;
    if (a[1].hp !== b[1].hp) return a[1].hp - b[1].hp;
    const cooldownA = a[1].cooldowns.reduce((sum, item) => sum + item, 0);
    const cooldownB = b[1].cooldowns.reduce((sum, item) => sum + item, 0);
    if (cooldownA !== cooldownB) return cooldownA - cooldownB;
    return planTieBreak(a[1].plan).localeCompare(planTieBreak(b[1].plan));
  }).slice(0, limit));
}

function planBossSequence(skills, healths, maxRounds) {
  if (!healths.length || maxRounds <= 0) return [];
  const initialCooldowns = skills.map((skill) => Math.max(skill.remaining, 0));
  let states = new Map([[`0|${cooldownKey(initialCooldowns)}`, { bossIdx: 0, hp: healths[0], cooldowns: initialCooldowns, plan: [] }]]);
  let best = { bossIdx: 0, hp: healths[0], plan: [] };
  for (let roundNo = 1; roundNo <= maxRounds; roundNo += 1) {
    const nextStates = new Map();
    for (const stateItem of states.values()) {
      for (const choice of plannerChoices(skills, stateItem.cooldowns)) {
        const plan = [...stateItem.plan, choice];
        let bossIdx = stateItem.bossIdx;
        let hp = stateItem.hp;
        if (choice !== null) {
          hp -= skills[choice].damage;
          if (hp <= 0) {
            bossIdx += 1;
            if (bossIdx >= healths.length) return plan;
            hp = healths[bossIdx];
          }
        }
        if (bossIdx > best.bossIdx || (bossIdx === best.bossIdx && hp < best.hp) || (
          bossIdx === best.bossIdx && hp === best.hp && plan.length > best.plan.length
        )) {
          best = { bossIdx, hp, plan };
        }
        const cooldowns = advanceCombatCooldowns(skills, stateItem.cooldowns, choice);
        const key = `${bossIdx}|${cooldownKey(cooldowns)}`;
        const existing = nextStates.get(key);
        if (!existing || hp < existing.hp || (hp === existing.hp && planTieBreak(plan) < planTieBreak(existing.plan))) {
          nextStates.set(key, { bossIdx, hp, cooldowns, plan });
        }
      }
    }
    states = nextStates.size > 50000 ? trimSequenceStates(nextStates) : nextStates;
    if (!states.size) break;
  }
  return best.plan;
}

function firstBossPlanSegment(skills, health, plan) {
  let hp = health;
  const segment = [];
  for (const choice of plan) {
    segment.push(choice);
    if (choice !== null) hp -= skills[choice].damage;
    if (hp <= 0) break;
  }
  return segment;
}

function previewBossSequencePlan(skills, healths, plan) {
  let bossIdx = 0;
  let hp = healths[0] || 0;
  let cooldowns = skills.map((skill) => Math.max(skill.remaining, 0));
  for (const choice of plan) {
    if (bossIdx >= healths.length) break;
    if (choice !== null) {
      hp -= skills[choice].damage;
      if (hp <= 0) {
        bossIdx += 1;
        hp = healths[bossIdx] || 0;
      }
    }
    cooldowns = advanceCombatCooldowns(skills, cooldowns, choice);
  }
  return {
    result: bossIdx >= healths.length ? "win" : "lose",
    defeatedCount: bossIdx,
    roundsUsed: plan.length,
    finalCooldowns: cooldowns,
  };
}

function buildRoundsFromPlan(skills, initialHealth, plan) {
  let hp = initialHealth;
  let cooldowns = skills.map((skill) => Math.max(skill.remaining, 0));
  const rounds = [];
  for (let roundNo = 1; roundNo <= plan.length && hp > 0; roundNo += 1) {
    const usedPos = plan[roundNo - 1];
    const cooldownsBefore = cooldowns.slice();
    const ready = cooldowns.map((cooldown, idx) => ({ cooldown, idx })).filter((item) => item.cooldown <= 0).map((item) => skills[item.idx].skill_index);
    const hpBefore = hp;
    if (usedPos !== null) {
      const chosen = skills[usedPos];
      hp = Math.max(0, hp - chosen.damage);
      rounds.push({
        round: roundNo,
        action: "attack",
        skill_index: chosen.skill_index,
        skill_label: `Skill #${chosen.skill_index + 1}`,
        damage: chosen.damage,
        hp_before: hpBefore,
        hp_after: hp,
        ready_skills: ready,
        cooldowns_before: cooldownsBefore,
      });
    } else {
      rounds.push({
        round: roundNo,
        action: "wait",
        skill_index: null,
        skill_label: null,
        damage: 0,
        hp_before: hpBefore,
        hp_after: hp,
        ready_skills: ready,
        cooldowns_before: cooldownsBefore,
      });
    }
    cooldowns = advanceCombatCooldowns(skills, cooldowns, usedPos);
    rounds[rounds.length - 1].cooldowns_after = cooldowns.slice();
  }
  return { hp, rounds, finalCooldowns: cooldowns };
}

function buildCombatEvent(normalized, bossOrderIndex, skills = buildCombatSkillStates(normalized.skills), roundLimit = normalized.minRounds, allBossHealthsKnown = false) {
  const skillDefs = skills.map((skill) => ({
    skill_index: skill.skill_index,
    damage: skill.damage,
    cooldown: skill.cooldown,
    initial_remaining_cooldown: skill.remaining,
  }));
  const initialHealth = Number(normalized.bosses[bossOrderIndex] || 70);
  const plannedHealths = allBossHealthsKnown ? normalized.bosses.slice(bossOrderIndex).map((value) => Number(value || 70)) : [initialHealth];
  const sequencePlan = allBossHealthsKnown ? planBossSequence(skills, plannedHealths, roundLimit) : planCombat(skills, initialHealth, roundLimit);
  const plan = allBossHealthsKnown ? firstBossPlanSegment(skills, initialHealth, sequencePlan) : sequencePlan;
  const sequencePreview = previewBossSequencePlan(skills, plannedHealths, sequencePlan);
  const { hp, rounds, finalCooldowns } = buildRoundsFromPlan(skills, initialHealth, plan);
  for (let idx = 0; idx < skills.length; idx += 1) {
    skills[idx].remaining = finalCooldowns[idx] || 0;
  }
  return {
    type: "boss",
    result: hp <= 0 ? "win" : "lose",
    boss_index: bossOrderIndex,
    encounter_order: bossOrderIndex + 1,
    health: initialHealth,
    initial_health: initialHealth,
    remaining_health: hp,
    total_damage: initialHealth - hp,
    rounds_used: rounds.length,
    max_rounds: normalized.minRounds,
    total_max_rounds: normalized.minRounds,
    round_limit: roundLimit,
    rounds,
    skills: skillDefs,
    final_cooldowns: finalCooldowns,
    planning_mode: allBossHealthsKnown ? "known_sequence" : "current_boss",
    planned_boss_orders: plannedHealths.map((_health, idx) => bossOrderIndex + idx + 1),
    planned_boss_healths: plannedHealths,
    planned_sequence_rounds: sequencePreview.roundsUsed,
    planned_sequence_result: sequencePreview.result,
    planned_sequence_defeated: sequencePreview.defeatedCount,
    message: hp <= 0 ? "boss defeated" : "boss challenge failed",
  };
}

function buildKnownBossHealthRecords(normalized, totalBosses, knownCount, defeatedCount) {
  const count = Math.min(Math.max(knownCount, 0), totalBosses);
  const defeated = Math.min(Math.max(defeatedCount, 0), totalBosses);
  const result = [];
  for (let idx = 0; idx < count; idx += 1) {
    let status = "known";
    if (idx < defeated) {
      status = "defeated";
    } else if (idx === defeated && defeated < totalBosses) {
      status = "current";
    }
    result.push({
      order: idx + 1,
      health: Number(normalized.bosses[idx] || 70),
      status,
    });
  }
  return result;
}

function applyBossReviveCost(value, requiredCost) {
  const cost = Math.max(Number(requiredCost) || 0, 0);
  if (cost <= 0 || value <= 0) return { valueAfter: value, actualCost: 0 };
  if (value <= cost) return { valueAfter: 0, actualCost: value };
  return { valueAfter: value - cost, actualCost: cost };
}

function reveal(grid, revealed, pos) {
  const [pr, pc] = pos;
  for (let r = pr - 1; r <= pr + 1; r += 1) {
    for (let c = pc - 1; c <= pc + 1; c += 1) {
      if (grid[r] && grid[r][c] !== undefined) {
        revealed[r][c] = true;
      }
    }
  }
}

function isWalkable(grid, pos) {
  const [r, c] = pos;
  return grid[r] && [" ", "S", "E", "B", "T", "C", "G", "L"].includes(grid[r][c]);
}

function bfs(grid, start, goals, revealed) {
  const goalKey = new Set(goals.map((p) => p.join(",")));
  const queue = [start];
  const seen = new Set([start.join(",")]);
  const prev = new Map();
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  while (queue.length) {
    const cur = queue.shift();
    if (goalKey.has(cur.join(","))) {
      const path = [cur];
      let key = cur.join(",");
      while (prev.has(key)) {
        const p = prev.get(key);
        path.push(p);
        key = p.join(",");
      }
      return path.reverse();
    }
    for (const [dr, dc] of dirs) {
      const nxt = [cur[0] + dr, cur[1] + dc];
      const key = nxt.join(",");
      if (seen.has(key) || !isWalkable(grid, nxt)) continue;
      if (revealed && !revealed[nxt[0]]?.[nxt[1]]) continue;
      seen.add(key);
      prev.set(key, cur);
      queue.push(nxt);
    }
  }
  return [];
}

function unknownNeighbors(revealed, pos) {
  const [r, c] = pos;
  return [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dr, dc]) => revealed[r + dr]?.[c + dc] === false);
}

function simulateStatic(data) {
  const normalized = normalizeMapData(data);
  const grid = cloneGrid(normalized.maze);
  const rows = grid.length;
  const cols = grid[0].length;
  const revealed = Array.from({ length: rows }, () => Array(cols).fill(false));
  const start = findCell(grid, "S");
  const exit = findCell(grid, "E");
  let pos = start;
  let coins = 0;
  let bossDefeated = false;
  let defeatedBossCount = 0;
  let allBossHealthsKnown = false;
  let totalBossRoundsUsed = 0;
  const bossAttemptCounts = new Map();
  const combatSkills = buildCombatSkillStates(normalized.skills);
  const totalBosses = Math.max(normalized.bosses.length, grid.reduce((sum, row) => sum + row.filter((cell) => cell === "B").length, 0));
  const frames = [];
  const route = [start];

  function pushFrame(phase, event, extra = {}) {
    reveal(grid, revealed, pos);
    const fog = grid.map((row, r) => row.map((cell, c) => (revealed[r][c] ? cell : null)));
    frames.push({
      pos: pos.slice(),
      coins,
      value: coins,
      phase,
      event,
      grid: fog,
      revealed: revealed.map((row) => row.slice()),
      bossDefeated,
      ...extra,
    });
  }

  function resolveBossAtCurrentCell() {
    let finalEvent = null;
    while (defeatedBossCount < totalBosses) {
      const bossOrderIndex = defeatedBossCount;
      const attempt = (bossAttemptCounts.get(bossOrderIndex) || 0) + 1;
      bossAttemptCounts.set(bossOrderIndex, attempt);
      const valueBefore = coins;
      const roundsRemaining = Math.max(normalized.minRounds - totalBossRoundsUsed, 0);
      const bossEvent = buildCombatEvent(normalized, bossOrderIndex, combatSkills, roundsRemaining, allBossHealthsKnown);
      bossEvent.attempt = attempt;
      bossEvent.total_rounds_before = totalBossRoundsUsed;
      bossEvent.total_rounds_used = totalBossRoundsUsed + bossEvent.rounds_used;
      bossEvent.rounds_remaining_before = roundsRemaining;
      bossEvent.rounds_remaining_after = Math.max(normalized.minRounds - bossEvent.total_rounds_used, 0);
      bossEvent.coins_before = valueBefore;
      bossEvent.value_before = valueBefore;
      bossEvent.coins_after = valueBefore;
      bossEvent.value_after = valueBefore;
      bossEvent.revived = false;
      bossEvent.revive_cost = 0;
      bossEvent.required_revive_cost = normalized.coinConsumption;
      bossEvent.revive = {
        used: false,
        cost: 0,
        required_cost: normalized.coinConsumption,
        coins_before: valueBefore,
        coins_after: valueBefore,
        value_before: valueBefore,
        value_after: valueBefore,
      };
      if (bossEvent.result === "win") {
        totalBossRoundsUsed = bossEvent.total_rounds_used;
        defeatedBossCount += 1;
        bossDefeated = defeatedBossCount >= totalBosses;
        bossEvent.message = "boss defeated";
        finalEvent = bossEvent;
        pushFrame("boss", "boss defeated", { bossEvent });
        return { won: true, event: finalEvent };
      }

      const revive = applyBossReviveCost(valueBefore, normalized.coinConsumption);
      coins = revive.valueAfter;
      const canRevive = normalized.coinConsumption > 0 && coins > 0;
      bossEvent.coins_after = coins;
      bossEvent.value_after = coins;
      bossEvent.revived = canRevive;
      bossEvent.revive_cost = revive.actualCost;
      bossEvent.coins_delta = coins - valueBefore;
      bossEvent.value_delta = coins - valueBefore;
      bossEvent.revive = {
        used: canRevive,
        cost: revive.actualCost,
        required_cost: normalized.coinConsumption,
        coins_before: valueBefore,
        coins_after: coins,
        value_before: valueBefore,
        value_after: coins,
      };
      bossEvent.message = canRevive ? "boss challenge failed, revived; restarted from Boss #1" : "boss challenge failed, value exhausted";
      bossEvent.rounds_reset_on_revive = canRevive;
      bossEvent.boss_sequence_reset_on_revive = canRevive;
      bossEvent.restart_boss_order = canRevive ? 1 : null;
      bossEvent.skill_cooldowns_reset_on_revive = canRevive;
      bossEvent.cooldowns_after_revive = canRevive ? combatSkills.map(() => 0) : null;
      bossEvent.boss_healths_revealed_on_revive = canRevive;
      bossEvent.known_boss_healths_after_revive = canRevive ? buildKnownBossHealthRecords(normalized, totalBosses, totalBosses, 0) : null;
      finalEvent = bossEvent;
      pushFrame("boss", canRevive ? "boss revived" : "boss failed", { bossEvent });
      if (!canRevive) return { won: false, event: finalEvent };
      for (const skill of combatSkills) {
        skill.remaining = 0;
      }
      allBossHealthsKnown = true;
      defeatedBossCount = 0;
      bossDefeated = false;
      totalBossRoundsUsed = 0;
    }
    return { won: true, event: finalEvent };
  }

  pushFrame("start", "simulation started");
  for (let step = 0; step < 420; step += 1) {
    if (grid[pos[0]][pos[1]] === "B" && defeatedBossCount < totalBosses) {
      const result = resolveBossAtCurrentCell();
      if (bossDefeated) grid[pos[0]][pos[1]] = " ";
      if (!result.won) break;
      continue;
    }

    const visibleCoins = [];
    const visibleBosses = [];
    const frontiers = [];
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        if (!revealed[r][c]) continue;
        const cell = grid[r][c];
        if (cell === "C" || cell === "G") visibleCoins.push([r, c]);
        if (cell === "B") visibleBosses.push([r, c]);
        if (isWalkable(grid, [r, c]) && unknownNeighbors(revealed, [r, c])) frontiers.push([r, c]);
      }
    }

    let targets = visibleCoins;
    if (!targets.length && visibleBosses.length) targets = visibleBosses;
    if (!targets.length && defeatedBossCount >= totalBosses && revealed[exit[0]][exit[1]]) targets = [exit];
    if (!targets.length) targets = frontiers;
    const path = bfs(grid, pos, targets, revealed);
    if (path.length < 2) {
      pushFrame("stuck", "no reachable target");
      break;
    }
    pos = path[1];
    route.push(pos);
    const [r, c] = pos;
    let event = "moved";
    if (grid[r][c] === "C" || grid[r][c] === "G") {
      coins += 50;
      grid[r][c] = " ";
      event = "collected coin";
    } else if (grid[r][c] === "T") {
      coins -= 30;
      grid[r][c] = " ";
      event = "triggered trap";
    } else if (grid[r][c] === "B") {
      const result = resolveBossAtCurrentCell();
      if (bossDefeated) grid[r][c] = " ";
      if (!result.won) break;
      continue;
    } else if (grid[r][c] === "E" && defeatedBossCount >= totalBosses) {
      pushFrame("win", "exit reached");
      break;
    }
    pushFrame("run", event);
  }

  const last = frames[frames.length - 1] || {};
  const bossFailed = last.bossEvent?.result === "lose" && !last.bossEvent?.revived;
  return {
    frames,
    route,
    score: (last.value ?? last.coins ?? 0) / Math.max(frames.length - 1, 1),
    totalSteps: frames.length - 1,
    totalValue: last.value ?? last.coins ?? 0,
    coins: last.coins || 0,
    value: last.value ?? last.coins ?? 0,
    bossDefeated,
    outputResult: last.phase === "win" ? "win" : bossFailed ? "lose" : "running",
  };
}

function calcLayout(canvas, rows, cols) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const tile = Math.max(12, Math.floor(Math.min((rect.width - 36) / cols, (rect.height - 36) / rows)));
  return { ctx, tile, originX: (rect.width - tile * cols) / 2, originY: (rect.height - tile * rows) / 2, width: rect.width, height: rect.height };
}

function drawFrame(frame) {
  if (!frame) return;
  const rows = frame.grid.length;
  const cols = frame.grid[0].length;
  const { ctx, tile, originX, originY, width, height } = calcLayout(els.canvas, rows, cols);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(5,4,10,0.72)";
  ctx.fillRect(0, 0, width, height);
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const cell = frame.grid[r][c];
      const x = originX + c * tile;
      const y = originY + r * tile;
      ctx.fillStyle = cell === null ? "#030308" : cell === "#" ? "#282940" : "rgba(29, 24, 42, 0.9)";
      ctx.fillRect(x, y, tile, tile);
      ctx.strokeStyle = "rgba(255,255,255,0.06)";
      ctx.strokeRect(x + 0.5, y + 0.5, tile - 1, tile - 1);
      if (cell === "C" || cell === "G") {
        ctx.fillStyle = "#ffaa00";
        ctx.shadowColor = "#ffaa00";
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(x + tile / 2, y + tile / 2, tile * 0.22, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      } else if (cell === "B") {
        ctx.fillStyle = "#ff3355";
        ctx.fillRect(x + tile * 0.25, y + tile * 0.25, tile * 0.5, tile * 0.5);
      } else if (cell === "T") {
        ctx.fillStyle = "#ff7a1a";
        ctx.fillRect(x + tile * 0.3, y + tile * 0.3, tile * 0.4, tile * 0.4);
      } else if (cell === "E") {
        ctx.strokeStyle = "#ffaa00";
        ctx.lineWidth = 3;
        ctx.strokeRect(x + tile * 0.25, y + tile * 0.25, tile * 0.5, tile * 0.5);
        ctx.lineWidth = 1;
      }
      if (cell === null && cellRand(r, c) > 0.86) {
        ctx.fillStyle = "rgba(0,229,255,0.12)";
        ctx.fillRect(x + tile * 0.45, y + tile * 0.45, 2, 2);
      }
    }
  }
  const [pr, pc] = frame.pos;
  ctx.fillStyle = "#f4f7fb";
  ctx.shadowColor = "#00e5ff";
  ctx.shadowBlur = 22;
  ctx.beginPath();
  ctx.arc(originX + pc * tile + tile / 2, originY + pr * tile + tile / 2, tile * 0.28, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
  updateMetrics(frame);
}

function updateMetrics(frame) {
  const value = frame.value ?? frame.coins ?? 0;
  els.stepsText.textContent = String(state.frameIndex);
  els.coinsText.textContent = String(value);
  els.scoreText.textContent = (value / Math.max(state.frameIndex, 1)).toFixed(2);
  els.phaseText.textContent = frame.phase || "ready";
  if (frame.event) {
    const li = document.createElement("li");
    li.textContent = `${state.frameIndex}: ${frame.event}`;
    els.eventList.prepend(li);
    while (els.eventList.children.length > 32) els.eventList.lastChild.remove();
  }
}

function setFrame(index) {
  state.frameIndex = Math.max(0, Math.min(index, state.frames.length - 1));
  const frame = state.frames[state.frameIndex];
  drawFrame(frame);
  if (frame?.phase === "boss") {
    showBoss(frame);
  }
}

function scheduleTick() {
  clearTimeout(state.timer);
  if (!state.playing) return;
  if (state.frameIndex >= state.frames.length - 1) {
    state.playing = false;
    els.playBtn.textContent = "播放";
    return;
  }
  state.timer = setTimeout(() => {
    setFrame(state.frameIndex + 1);
    scheduleTick();
  }, 180);
}

function showBoss(frame) {
  try {
    window.localStorage.removeItem("ai_maze_active_map");
  } catch (_err) {
    // Boss data is delivered through postMessage in embedded mode.
  }
  els.bossLayer.classList.remove("hidden");
  const iframe = els.bossLayer.querySelector("iframe");
  const payload = { event: frame.bossEvent };
  const message = { type: "maze-start-boss-battle", payload };
  if (iframe?.contentWindow) {
    iframe.contentWindow.postMessage(message, "*");
    iframe.addEventListener("load", () => iframe.contentWindow?.postMessage(message, "*"), { once: true });
  }
  setTimeout(() => els.bossLayer.classList.add("hidden"), frame.bossDefeated ? 3600 : 2600);
}

async function loadSample() {
  try {
    const res = await fetch("../map/sample.json");
    if (!res.ok) throw new Error("sample map unavailable");
    state.mapData = await res.json();
  } catch (_err) {
    state.mapData = DEFAULT_MAP;
  }
  els.mapName.textContent = "sample.json";
  runSimulation();
}

function runSimulation() {
  if (!state.mapData) return;
  clearTimeout(state.timer);
  state.playing = false;
  els.playBtn.textContent = "播放";
  els.eventList.innerHTML = "";
  const result = simulateStatic(state.mapData);
  state.frames = result.frames;
  state.route = result.route;
  setFrame(0);
}

els.loadSampleBtn.addEventListener("click", loadSample);
els.runBtn.addEventListener("click", runSimulation);
els.playBtn.addEventListener("click", () => {
  state.playing = !state.playing;
  els.playBtn.textContent = state.playing ? "暂停" : "播放";
  scheduleTick();
});
els.fileInput.addEventListener("change", async (evt) => {
  const file = evt.target.files[0];
  if (!file) return;
  state.mapData = JSON.parse(await file.text());
  els.mapName.textContent = file.name;
  runSimulation();
});
window.addEventListener("resize", () => drawFrame(state.frames[state.frameIndex]));
loadSample();
