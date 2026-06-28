const els = {
  canvas: document.getElementById("bossCanvas"),
  player: document.getElementById("playerActor"),
  boss: document.getElementById("bossActor"),
  damage: document.getElementById("damageText"),
  phase: document.getElementById("battlePhase"),
  hp: document.getElementById("bossHp"),
  field: document.querySelector(".battlefield"),
  log: document.getElementById("battleLog"),
};

const state = {
  frames: [],
  index: 0,
  timer: null,
};

function normalizeMapData(raw) {
  const data = raw?.mapData || raw?.state || raw || {};
  const event = raw?.event || raw?.frame?.bossEvent || null;
  return {
    bossHealth: Number(event?.initial_health || event?.health || (data.B && data.B[0]) || 70),
    remainingHealth: Number(event?.remaining_health ?? 0),
    skills: data.PlayerSkills || data.skills || [[20, 1], [35, 3], [12, 0]],
    minRounds: Number(event?.max_rounds || data.minRouds || data.minRounds || 6),
    coinConsumption: Number(data.CoinConsumption || data.coinConsumption || 0),
    result: event?.result || (raw?.frame?.bossDefeated ? "win" : "win"),
    rounds: event?.rounds || null,
    totalDamage: Number(event?.total_damage || 0),
    encounterOrder: Number(event?.encounter_order || 1),
    attempt: Number(event?.attempt || 1),
    coinsBefore: Number(event?.value_before ?? event?.coins_before ?? 0),
    coinsAfter: Number(event?.value_after ?? event?.coins_after ?? event?.value_before ?? event?.coins_before ?? 0),
    reviveCost: Number(event?.revive_cost ?? event?.revive?.cost ?? event?.cost ?? 0),
    revived: Boolean(event?.revived || event?.revive?.used),
  };
}

function buildInitialSkillStates(skills) {
  return skills.map((skill) => ({
    damage: Number(skill[0] ?? skill.damage ?? 0),
    cooldown: Number(skill[1] ?? skill.cooldown ?? 0),
    remaining: 0,
  }));
}

function decideCombat(skills) {
  const ready = skills.map((skill, idx) => ({ skill, idx })).filter((item) => item.skill.remaining <= 0);
  if (!ready.length) return null;
  return ready.sort((a, b) => b.skill.damage - a.skill.damage)[0];
}

function cooldownKey(cooldowns) {
  return cooldowns.join(",");
}

function advanceCooldowns(skills, cooldowns, usedIdx) {
  const next = cooldowns.slice();
  if (usedIdx !== null) next[usedIdx] = skills[usedIdx].cooldown;
  for (let idx = 0; idx < next.length; idx += 1) {
    if (idx !== usedIdx && next[idx] > 0) next[idx] -= 1;
    if (next[idx] < 0) next[idx] = 0;
  }
  return next;
}

function planCombat(skills, health, maxRounds) {
  const initialCooldowns = skills.map((skill) => Math.max(skill.remaining, 0));
  let states = new Map([[cooldownKey(initialCooldowns), { cooldowns: initialCooldowns, damage: 0, plan: [] }]]);
  let best = { damage: 0, plan: [] };
  for (let round = 1; round <= maxRounds; round += 1) {
    const nextStates = new Map();
    for (const stateItem of states.values()) {
      const ready = stateItem.cooldowns.map((cooldown, idx) => ({ cooldown, idx })).filter((item) => item.cooldown <= 0).map((item) => item.idx);
      const choices = ready.length ? ready.sort((a, b) => skills[b].damage - skills[a].damage || a - b) : [null];
      for (const choice of choices) {
        const damage = stateItem.damage + (choice === null ? 0 : skills[choice].damage);
        const plan = [...stateItem.plan, choice];
        if (damage > best.damage || (damage === best.damage && plan.length > best.plan.length)) best = { damage, plan };
        if (damage >= health) return plan;
        const cooldowns = advanceCooldowns(skills, stateItem.cooldowns, choice);
        const key = cooldownKey(cooldowns);
        const existing = nextStates.get(key);
        if (!existing || damage > existing.damage) {
          nextStates.set(key, { cooldowns, damage, plan });
        }
      }
    }
    states = nextStates;
    if (!states.size) break;
  }
  return best.plan;
}

function buildFrames(data) {
  if (Array.isArray(data.rounds) && data.rounds.length) {
    const frames = [{ phase: "approach", hp: data.bossHealth, damage: 0 }];
    for (const round of data.rounds) {
      if (round.action === "attack") {
        frames.push({ phase: "slash", hp: round.hp_before, damage: round.damage, round });
        frames.push({ phase: "impact", hp: round.hp_after, damage: round.damage, round, shake: true });
        frames.push({ phase: "recoil", hp: round.hp_after, damage: 0, round });
      } else {
        frames.push({ phase: "idle", hp: round.hp_after, damage: 0, round });
      }
    }
    frames.push({ phase: data.result === "win" ? "defeated" : "failed", hp: data.remainingHealth, damage: 0 });
    return frames;
  }

  const skills = buildInitialSkillStates(data.skills);
  let hp = data.bossHealth;
  const frames = [{ phase: "approach", hp, damage: 0 }];
  let cooldowns = skills.map((skill) => Math.max(skill.remaining, 0));
  const plan = planCombat(skills, hp, data.minRounds);
  for (const usedIdx of plan) {
    if (hp <= 0) break;
    if (usedIdx === null) {
      frames.push({ phase: "idle", hp, damage: 0 });
    } else {
      const skill = skills[usedIdx];
      hp = Math.max(0, hp - skill.damage);
      frames.push({ phase: "slash", hp, damage: skill.damage });
      frames.push({ phase: "impact", hp, damage: skill.damage, shake: true });
      frames.push({ phase: "recoil", hp, damage: 0 });
    }
    cooldowns = advanceCooldowns(skills, cooldowns, usedIdx);
  }
  frames.push({ phase: hp <= 0 ? "defeated" : "failed", hp, damage: 0 });
  return frames;
}

function renderBattleLog(data) {
  if (!els.log) return;
  els.log.innerHTML = "";
  const summary = document.createElement("li");
  summary.className = "summary";
  summary.innerHTML = `<span>B${data.encounterOrder}</span><p>attempt ${data.attempt} / value ${data.coinsBefore} -> ${data.coinsAfter} / cost ${data.reviveCost}</p>`;
  els.log.appendChild(summary);
  const rounds = Array.isArray(data.rounds) ? data.rounds : [];
  for (const round of rounds) {
    const li = document.createElement("li");
    li.dataset.round = String(round.round);
    li.innerHTML = round.action === "attack"
      ? `<span>R${round.round}</span><p>${round.skill_label} / -${round.damage} HP ${round.hp_before} -> ${round.hp_after}</p>`
      : `<span>R${round.round}</span><p>wait / HP ${round.hp_before}</p>`;
    els.log.appendChild(li);
  }
}

function calcCanvas() {
  const rect = els.canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  els.canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  els.canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = els.canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width: rect.width, height: rect.height };
}

function draw() {
  const { ctx, width, height } = calcCanvas();
  const grad = ctx.createLinearGradient(0, 0, width, height);
  grad.addColorStop(0, "rgba(0,229,255,0.08)");
  grad.addColorStop(0.5, "rgba(255,45,149,0.12)");
  grad.addColorStop(1, "rgba(255,170,0,0.06)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.05)";
  for (let x = 0; x < width; x += 28) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y < height; y += 28) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function setActorAnim(frame) {
  els.player.className = "actor player-actor";
  els.boss.className = "actor boss-actor";
  els.field.classList.remove("screen-shake");
  if (frame.phase === "slash" || frame.phase === "impact") {
    els.player.classList.add("slash");
  }
  if (frame.phase === "impact") {
    els.boss.classList.add("impact");
    els.damage.textContent = `-${frame.damage}`;
    els.damage.classList.remove("show");
    void els.damage.offsetWidth;
    els.damage.classList.add("show");
  }
  if (frame.shake) {
    els.field.classList.remove("screen-shake");
    void els.field.offsetWidth;
    els.field.classList.add("screen-shake");
  }
}

function setFrame(index) {
  state.index = Math.max(0, Math.min(index, state.frames.length - 1));
  const frame = state.frames[state.index];
  draw();
  setActorAnim(frame);
  const skillText = frame.round?.skill_label ? ` · ${frame.round.skill_label}` : "";
  els.phase.textContent = `${frame.phase}${skillText}`;
  els.hp.textContent = `HP ${frame.hp}`;
  if (els.log) {
    for (const item of els.log.children) {
      item.classList.toggle("active", frame.round && item.dataset.round === String(frame.round.round));
    }
  }
}

function frameDelay(frame) {
  if (frame.phase === "impact") return 520;
  if (frame.phase === "defeated" || frame.phase === "failed") return 900;
  return 360;
}

function scheduleTick() {
  clearTimeout(state.timer);
  const frame = state.frames[state.index];
  if (state.index >= state.frames.length - 1) {
    window.parent?.postMessage({ type: "maze-boss-complete", payload: frame }, "*");
    return;
  }
  state.timer = setTimeout(() => {
    setFrame(state.index + 1);
    scheduleTick();
  }, frameDelay(frame));
}

function init(payload) {
  clearTimeout(state.timer);
  state.index = 0;
  const data = normalizeMapData(payload);
  state.frames = buildFrames(data);
  renderBattleLog(data);
  setFrame(0);
  window.parent?.postMessage({ type: "maze-boss-ready" }, "*");
  scheduleTick();
}

window.addEventListener("message", (event) => {
  if (event.data?.type === "maze-start-boss-battle") {
    init(event.data.payload);
  }
});
window.addEventListener("resize", () => setFrame(state.index));

const isEmbedded = new URLSearchParams(window.location.search).get("embed") === "1";
if (isEmbedded) {
  init({});
} else {
  try {
    const stored = JSON.parse(window.localStorage.getItem("ai_maze_active_map") || "{}");
    init(stored);
  } catch (_err) {
    init({});
  }
}
