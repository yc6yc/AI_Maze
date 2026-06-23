(() => {
  const DEFAULT_MAP_CANDIDATES = [
    "../map地图/maze_15_15.json",
    "../map/maze_15_15.json",
    "../maze_15_15.json",
  ];
  const ACTIVE_MAP_CACHE_KEY = "ai_maze_active_map";
  const DEFAULT_MAP_DATA = {
    maze: [
      ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "S", "#", "#", "#"],
      ["#", " ", "G", "T", "G", "#", " ", " ", " ", " ", " ", " ", " ", " ", "#"],
      ["#", "#", "#", "G", "#", "#", "#", " ", "#", "#", "#", "#", "#", "#", "#"],
      ["#", " ", "T", " ", " ", " ", "#", " ", " ", " ", "#", " ", "#", "G", "#"],
      ["#", "#", "#", " ", "#", " ", "#", "#", "#", " ", "#", " ", "#", "G", "#"],
      ["#", " ", "G", " ", "#", " ", "#", "G", " ", " ", " ", " ", "G", "T", "#"],
      ["#", "#", "#", " ", "#", " ", "#", "#", "#", "#", "#", "T", "#", "T", "#"],
      ["#", " ", "#", " ", "#", " ", "#", " ", " ", " ", " ", " ", "#", " ", "#"],
      ["#", "T", "#", " ", "#", " ", "#", "#", "#", " ", "#", "#", "#", " ", "#"],
      ["#", " ", " ", " ", "#", " ", " ", " ", " ", " ", " ", " ", "#", " ", "#"],
      ["#", " ", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
      ["#", " ", " ", " ", "#", "G", "#", " ", "T", " ", "#", "G", "T", " ", "#"],
      ["#", "#", "#", " ", "#", "T", "#", " ", "#", "#", "#", "#", "#", " ", "#"],
      ["#", " ", " ", " ", " ", " ", " ", " ", "B", " ", " ", " ", "T", "G", "#"],
      ["#", "#", "#", "#", "#", "#", "#", "#", "#", "E", "#", "#", "#", "#", "#"],
    ],
    B: [11, 13, 9, 15],
    PlayerSkills: [[8, 4], [2, 0], [4, 2], [6, 3]],
    minRouds: 20,
    CoinConsumption: 5,
  };

  const els = {
    battleName: document.getElementById("battleName"),
    runState: document.getElementById("runState"),
    phaseLabel: document.getElementById("phaseLabel"),
    metricBoss: document.getElementById("metricBoss"),
    metricAttempt: document.getElementById("metricAttempt"),
    metricRound: document.getElementById("metricRound"),
    metricCoins: document.getElementById("metricCoins"),
    detailBoss: document.getElementById("detailBoss"),
    detailAttempt: document.getElementById("detailAttempt"),
    detailTurn: document.getElementById("detailTurn"),
    detailAction: document.getElementById("detailAction"),
    detailDamage: document.getElementById("detailDamage"),
    detailBossHp: document.getElementById("detailBossHp"),
    skillList: document.getElementById("skillList"),
    eventList: document.getElementById("eventList"),
    timeline: document.getElementById("timeline"),
    speedRange: document.getElementById("speedRange"),
    speedLabel: document.getElementById("speedLabel"),
    playBtn: document.getElementById("playBtn"),
    resetBtn: document.getElementById("resetBtn"),
    prevBtn: document.getElementById("prevBtn"),
    nextBtn: document.getElementById("nextBtn"),
    dataToggleBtn: document.getElementById("dataToggleBtn"),
    dataPanel: document.getElementById("dataPanel"),
    closeDataBtn: document.getElementById("closeDataBtn"),
    canvas: document.getElementById("mazeCanvas"),
    playerHp: document.getElementById("playerHp"),
    bossHp: document.getElementById("bossHp"),
    damageText: document.getElementById("damageText"),
    frameCounter: document.getElementById("frameCounter"),
    actorPlayer: document.querySelector('.actor-panel.actor-player'),
    actorBoss: document.querySelector('.actor-panel.actor-boss'),
    skillEffect: document.getElementById("skillEffect"),
    bgmBoss: document.getElementById("bgmBoss"),
  };

  const ctx = els.canvas.getContext("2d");

  const state = {
    mapData: null, mapName: "maze_15_15.json",
    frames: [], frameIndex: 0, speed: 5, timer: null, playing: false,
    dataPanelOpen: false,
    maze: [], playerPos: { r: 0, c: 0 }, bossPos: { r: 0, c: 0 },
    layout: { dpr: 1, width: 0, height: 0, tile: 0, ox: 0, oy: 0 },
  };

  // ---- Data helpers ----
  function cloneData(data) { return JSON.parse(JSON.stringify(data)); }

  function loadCachedActiveMap() {
    try {
      const raw = window.localStorage.getItem(ACTIVE_MAP_CACHE_KEY);
      if (!raw) return null;
      const cached = JSON.parse(raw);
      if (!cached?.data || !Array.isArray(cached.data.B) || !Array.isArray(cached.data.PlayerSkills)) return null;
      return { data: cached.data, name: cached.name || "Current maze map" };
    } catch { return null; }
  }

  function normalizeMapData(data) {
    if (!data || !Array.isArray(data.B) || !Array.isArray(data.PlayerSkills)) {
      throw new Error("Boss battle data must include B and PlayerSkills");
    }
    const minRounds = Number(data.minRouds ?? data.minRounds ?? 0);
    const coinConsumption = Number(data.CoinConsumption ?? data.coinConsumption ?? 0);
    const bossHps = data.B.map((v) => Number(v));
    const skills = data.PlayerSkills.map((spec, i) => {
      if (!Array.isArray(spec) || spec.length < 2) throw new Error(`PlayerSkills[${i}] format error`);
      return { damage: Number(spec[0]), cooldown: Number(spec[1]), remainingCd: Number(spec[2] ?? 0) };
    });
    return { raw: data, bossHps, skills, minRounds, coinConsumption };
  }

  function buildInitialSkillStates(skills) {
    return skills.map((s) => ({ damage: s.damage, cooldown: s.cooldown, remainingCd: s.remainingCd ?? 0 }));
  }
  function snapshotSkills(skills) {
    return skills.map((s) => ({ damage: s.damage, cooldown: s.cooldown, remainingCd: s.remainingCd }));
  }
  function tickCooldowns(skills) { skills.forEach((s) => { if (s.remainingCd > 0) s.remainingCd -= 1; }); }
  function decideCombat(skills) {
    let bestIdx = null, bestDamage = -1;
    skills.forEach((s, i) => { if (s.remainingCd === 0 && s.damage > bestDamage) { bestDamage = s.damage; bestIdx = i; } });
    return bestIdx;
  }

  // ---- Melee combat frame builder ----
  // Each attack round is now a full melee combo with multiple phases
  function buildMeleePhases(skillIdx, damage, bossHpMax) {
    const phases = [];
    const hasSkill = skillIdx !== null && damage > 0;

    if (!hasSkill) {
      // No skill ready — waiting / idle
      for (let i = 0; i < 60; i++) {
        phases.push({ phase: "idle", action: "wait", flash: false, shake: false });
      }
      return phases;
    }

    // Decide combo length based on damage — extended melee combo
    const isHeavy = damage >= 6;
    const comboCount = isHeavy ? 7 : 5;

    // 1. Approach (rushes in)
    for (let i = 0; i < 18; i++) {
      phases.push({ phase: "approach", action: "dash", flash: false, shake: false });
    }

    // 2. Combo slashes (multiple rapid swings)
    for (let i = 0; i < comboCount; i++) {
      const isLast = i === comboCount - 1;
      for (let j = 0; j < 12; j++) {
        phases.push({ phase: isLast ? "heavy" : "slash", action: "attack", flash: j === 0, shake: false });
      }
    }

    // 3. Impact / hit (damage lands, screen shake + flash)
    for (let i = 0; i < 18; i++) {
      phases.push({ phase: "impact", action: "hit", flash: i < 3, shake: true });
    }

    // 4. Boss recoil (boss staggers left and right)
    for (let i = 0; i < 18; i++) {
      phases.push({ phase: "recoil", action: "recoil", flash: false, shake: false });
    }

    // 5. Boss counter-attack (40% chance — knocks player back)
    const bossCounter = Math.random() < 0.4;
    if (bossCounter) {
      for (let i = 0; i < 12; i++) phases.push({ phase: "counter_windup", action: "counter", flash: false, shake: false });
      for (let i = 0; i < 12; i++) phases.push({ phase: "counter_slash", action: "counter", flash: i === 0, shake: false });
      for (let i = 0; i < 12; i++) phases.push({ phase: "counter_impact", action: "counter_hit", flash: i < 3, shake: true });
      for (let i = 0; i < 12; i++) phases.push({ phase: "counter_recoil", action: "counter_recoil", flash: false, shake: false });
    }

    // 6. Retreat back
    for (let i = 0; i < 18; i++) {
      phases.push({ phase: "retreat", action: "retreat", flash: false, shake: false });
    }

    // 7. Idle / breathe (recovery)
    for (let i = 0; i < 48; i++) {
      phases.push({ phase: "idle", action: "idle", flash: false, shake: false });
    }

    return phases;
  }

  function eventLabel(frame) {
    if (frame.failed) return `Coins exhausted, Boss ${frame.bossIndex} challenge failed`;
    if (frame.retry) return `Failed to defeat Boss within ${frame.minRounds} rounds, -${frame.coinConsumption} coins, retrying`;
    if (frame.skillIdx === null) return `Round ${frame.attackRound} waiting, all skills on cooldown`;
    if (frame.defeated && frame.phase === "impact") return `Combo finished! Boss ${frame.bossIndex} defeated!`;
    if (frame.phase === "impact") return `Heavy strike landed! Damage ${frame.damage}`;
    if (frame.phase === "slash") return `Slash!`;
    if (frame.phase === "heavy") return `Charging heavy strike...`;
    if (frame.phase === "approach") return `Closing in...`;
    if (frame.phase === "retreat") return `Retreating...`;
    if (frame.phase === "counter_impact") return `Boss counter-attack!`;
    if (frame.phase === "recoil") return `Boss recoils...`;
    return "";
  }

  function buildFrames(config, startingCoins) {
    const frames = [];
    const skills = buildInitialSkillStates(config.skills);
    let coins = Math.max(0, Number(startingCoins) || 0);
    let totalRound = 0;
    let shouldStop = false;

    for (let bz = 0; bz < config.bossHps.length; bz++) {
      const bossHpMax = config.bossHps[bz];
      let bossHp = bossHpMax;
      let attempt = 0;
      const bossIndex = bz + 1;

      while (bossHp > 0 && coins >= 0 && !shouldStop) {
        attempt++;
        for (let ar = 1; ar <= config.minRounds; ar++) {
          totalRound++;
          const skillIdx = decideCombat(skills);
          let damage = 0;
          if (skillIdx !== null) {
            damage = skills[skillIdx].damage;
            skills[skillIdx].remainingCd = skills[skillIdx].cooldown;
            bossHp = Math.max(0, bossHp - damage);
          }
          const defeated = bossHp <= 0;
          tickCooldowns(skills);

          // Build melee phase sequence
          const meleePhases = buildMeleePhases(skillIdx, damage, bossHpMax);

          meleePhases.forEach((mp) => {
            frames.push({
              bossIndex, bossTotal: config.bossHps.length, attempt, attackRound: ar, totalRound,
              skillIdx, damage, coins, bossHp, bossHpMax, defeated, retry: false, failed: false,
              skills: snapshotSkills(skills), phase: mp.phase, action: mp.action,
              flash: mp.flash, shake: mp.shake,
              minRounds: config.minRounds, coinConsumption: config.coinConsumption,
              statusText: eventLabel({
                bossIndex, attackRound: ar, skillIdx, damage, defeated,
                phase: mp.phase, retry: false, failed: false
              }),
            });
          });

          if (defeated) break;
        }
        if (bossHp <= 0) break;
        coins -= config.coinConsumption;
        const failed = coins <= 0;
        frames.push({
          bossIndex, bossTotal: config.bossHps.length, attempt, attackRound: config.minRounds, totalRound,
          skillIdx: null, damage: 0, coins: Math.max(coins, 0), bossHp, bossHpMax, defeated: false,
          retry: !failed, failed, skills: snapshotSkills(skills), phase: failed ? "failed" : "retry",
          action: failed ? "failed" : "retry", flash: false, shake: false,
          minRounds: config.minRounds, coinConsumption: config.coinConsumption,
          statusText: failed ? `Coins dropped to 0, Boss ${bossIndex} challenge terminated` : `Challenge timeout, -${config.coinConsumption} coins, retrying same Boss`,
        });
        if (failed) { shouldStop = true; break; }
      }
    }
    return frames;
  }

  // ---- Maze helpers ----
  function findPositions(maze) {
    let sr = 0, sc = 0, br = 0, bc = 0;
    for (let r = 0; r < maze.length; r++) {
      for (let c = 0; c < maze[0].length; c++) {
        if (maze[r][c] === "S") { sr = r; sc = c; }
        if (maze[r][c] === "B") { br = r; bc = c; }
      }
    }
    return { player: { r: sr, c: sc }, boss: { r: br, c: bc } };
  }

  // ---- Canvas drawing ----
  function fitCanvas() {
    const rect = els.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(200, Math.floor(rect.width * dpr));
    const h = Math.max(200, Math.floor(rect.height * dpr));
    if (els.canvas.width !== w || els.canvas.height !== h) {
      els.canvas.width = w; els.canvas.height = h;
    }
    state.layout.dpr = dpr; state.layout.width = w; state.layout.height = h;
    const rows = state.maze.length || 15;
    const cols = state.maze[0]?.length || 15;
    const tile = Math.min(w / cols, h / rows);
    state.layout.tile = tile;
    state.layout.ox = (w - cols * tile) / 2;
    state.layout.oy = (h - rows * tile) / 2;
  }

  function drawMaze(frame) {
    fitCanvas();
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    if (!state.maze.length) return;
    const { tile, ox, oy } = state.layout;
    const rows = state.maze.length;
    const cols = state.maze[0].length;

    // Walls
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = ox + c * tile, y = oy + r * tile;
        if (state.maze[r][c] === "#") {
          ctx.fillStyle = 'rgba(84, 80, 118, 0.95)';
          ctx.fillRect(x - 0.5, y - 0.5, tile + 1, tile + 1);
        } else {
          ctx.fillStyle = 'rgba(58, 54, 80, 0.45)';
          ctx.fillRect(x, y, tile, tile);
        }
      }
    }
    // Special cells
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cell = state.maze[r][c];
        if (cell === "#" || cell === " ") continue;
        const x = ox + c * tile, y = oy + r * tile;
        const cx = x + tile / 2, cy = y + tile / 2, sz = tile * 0.35;
        if (cell === "S") {
          ctx.fillStyle = 'rgba(90, 210, 210, 0.75)';
          ctx.beginPath(); ctx.moveTo(cx, cy - sz); ctx.lineTo(cx + sz * 0.8, cy); ctx.lineTo(cx, cy + sz * 0.6); ctx.lineTo(cx - sz * 0.8, cy); ctx.closePath(); ctx.fill();
        } else if (cell === "E") {
          ctx.fillStyle = 'rgba(245, 190, 90, 0.68)'; ctx.beginPath(); ctx.arc(cx, cy, sz * 0.6, 0, Math.PI * 2); ctx.fill();
        } else if (cell === "B") {
          ctx.fillStyle = 'rgba(220, 65, 95, 0.8)'; ctx.beginPath(); ctx.arc(cx, cy, sz * 0.55, 0, Math.PI * 2); ctx.fill();
        } else if (cell === "C" || cell === "G") {
          ctx.fillStyle = 'rgba(245, 225, 100, 0.68)'; ctx.beginPath(); ctx.arc(cx, cy, sz * 0.4, 0, Math.PI * 2); ctx.fill();
        } else if (cell === "T") {
          ctx.strokeStyle = 'rgba(245, 120, 60, 0.72)'; ctx.lineWidth = 1.5;
          ctx.beginPath(); ctx.moveTo(cx - sz * 0.4, cy - sz * 0.4); ctx.lineTo(cx + sz * 0.4, cy + sz * 0.4); ctx.moveTo(cx + sz * 0.4, cy - sz * 0.4); ctx.lineTo(cx - sz * 0.4, cy + sz * 0.4); ctx.stroke();
        }
      }
    }
    if (frame) {
      drawPosGlow(state.playerPos, 'rgba(0, 229, 255, 0.35)', tile);
      drawPosGlow(state.bossPos, 'rgba(255, 45, 149, 0.35)', tile);
    }
  }

  function drawPosGlow(pos, color, tile) {
    const { ox, oy } = state.layout;
    const x = ox + pos.c * tile + tile / 2;
    const y = oy + pos.r * tile + tile / 2;
    const grad = ctx.createRadialGradient(x, y, 0, x, y, tile * 1.2);
    grad.addColorStop(0, color); grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(x - tile * 1.2, y - tile * 1.2, tile * 2.4, tile * 2.4);
  }

  // ---- Actor CSS animation control ----
  let _lastPhase = null;
  function setActorAnim(frame) {
    if (!frame) return;
    const p = els.actorPlayer;
    const b = els.actorBoss;
    if (!p || !b) return;

    const phase = frame.phase;
    const action = frame.action;

    // Only reset classes when phase changes — prevents CSS animation restart every frame
    if (phase !== _lastPhase) {
      p.className = 'actor-panel actor-player';
      b.className = 'actor-panel actor-boss';

      // Player animation states
      if (phase === 'approach' || action === 'dash') {
        p.classList.add('melee-approach');
      } else if (phase === 'slash' || phase === 'heavy') {
        p.classList.add('melee-slash');
      } else if (phase === 'impact') {
        p.classList.add('melee-impact');
      } else if (phase === 'retreat') {
        p.classList.add('melee-retreat');
      } else if (phase === 'counter_impact') {
        p.classList.add('melee-counter-hit');
      } else {
        p.classList.add('melee-idle');
      }

      // Boss animation states
      if (phase === 'impact' || phase === 'recoil') {
        b.classList.add('boss-hit');
      } else if (phase === 'counter_slash' || phase === 'counter_impact') {
        b.classList.add('boss-counter');
      } else if (phase === 'counter_windup') {
        b.classList.add('boss-windup');
      } else {
        b.classList.add('boss-idle');
      }
    }
    _lastPhase = phase;

    // Screen shake
    if (frame.shake) {
      document.body.classList.add('screen-shake');
      setTimeout(() => document.body.classList.remove('screen-shake'), 500);
    }

    // Flash effect
    if (frame.flash) {
      els.skillEffect.classList.add('flash');
      setTimeout(() => els.skillEffect.classList.remove('flash'), 220);
    }
  }

  function showDamage(amount) {
    if (!amount || amount <= 0) {
      els.damageText.classList.remove("show");
      return;
    }
    els.damageText.textContent = `-${amount}`;
    els.damageText.classList.add("show");
    setTimeout(() => els.damageText.classList.remove("show"), 600);
  }

  // ---- UI updates ----
  function updateActorLabels(frame) {
    if (!frame) return;
    els.playerHp.textContent = `Coins: ${frame.coins}`;
    const hpText = frame.defeated ? "DEFEATED" : frame.failed ? "FAILED" : `HP: ${frame.bossHp}/${frame.bossHpMax}`;
    els.bossHp.textContent = hpText;
    els.bossHp.style.color = frame.defeated ? "var(--green)" : frame.failed ? "var(--red)" : "var(--text-dim)";
  }

  function renderEvents() {
    const events = state.frames
      .map((f, i) => ({ frame: f, index: i }))
      .filter(({ index, frame }) => index <= state.frameIndex && frame.statusText)
      .filter(({ frame }) =>
        frame.phase === "impact" || frame.phase === "slash" || frame.phase === "heavy" ||
        frame.phase === "counter_impact" || frame.phase === "recoil" ||
        frame.retry || frame.failed || frame.phase === "approach"
      )
      .slice(-20).reverse();

    els.eventList.innerHTML = "";
    events.forEach(({ frame }) => {
      const item = document.createElement("li");
      item.className = frame.failed ? "phase-failed" : frame.retry ? "phase-retry" : frame.defeated && frame.phase === "impact" ? "phase-win" : "phase-damage";
      item.innerHTML = `<span class="event-round">#${frame.totalRound}</span><span class="event-copy">${frame.statusText}</span>`;
      els.eventList.appendChild(item);
    });
  }

  function renderSkills(frame) {
    els.skillList.innerHTML = "";
    if (!frame) return;
    frame.skills.forEach((skill, index) => {
      const card = document.createElement("div");
      card.className = `skill-card${frame.skillIdx === index ? " active" : ""}${skill.remainingCd > 0 ? " cooling" : ""}`;
      const ratio = skill.cooldown === 0 ? 1 : (skill.cooldown - skill.remainingCd) / skill.cooldown;
      card.innerHTML = `
        <div class="skill-card-header">
          <strong>S${index}</strong>
          <span class="skill-state ${skill.remainingCd === 0 ? "ready" : ""}">${skill.remainingCd === 0 ? "Ready" : `CD ${skill.remainingCd}`}</span>
        </div>
        <div class="skill-card-meta">
          <span>DMG ${skill.damage}</span>
          <span>CD ${skill.cooldown}</span>
        </div>
        <div class="skill-bar">
          <div class="skill-bar-fill" style="width:${Math.max(0, Math.min(100, ratio * 100))}%"></div>
        </div>`;
      els.skillList.appendChild(card);
    });
  }

  function updateUi() {
    const frame = state.frames[state.frameIndex] || null;
    if (!frame) {
      els.runState.textContent = "Standby";
      return;
    }
    els.runState.textContent = state.playing ? "Playing" : "Paused";
    els.phaseLabel.textContent = frame.failed ? "失败" : frame.retry ? "重试" : frame.defeated ? "击败" : frame.phase;
    els.metricBoss.textContent = `${frame.bossIndex} / ${frame.bossTotal}`;
    els.metricAttempt.textContent = String(frame.attempt);
    els.metricRound.textContent = String(frame.totalRound);
    els.metricCoins.textContent = String(frame.coins);
    els.detailBoss.textContent = `${frame.bossIndex} / ${frame.bossTotal}`;
    els.detailAttempt.textContent = String(frame.attempt);
    els.detailTurn.textContent = `${frame.attackRound} / ${frame.minRounds}`;
    els.detailAction.textContent = frame.skillIdx === null ? "Waiting for cooldown" : `Melee combo S${frame.skillIdx}`;
    els.detailDamage.textContent = String(frame.damage);
    els.detailBossHp.textContent = frame.failed ? "Failed" : frame.retry ? "Retry" : frame.defeated ? "Defeated" : "Fighting";
    els.timeline.value = String(state.frameIndex);
    els.frameCounter.textContent = `${state.frameIndex + 1} / ${state.frames.length}`;
    updateActorLabels(frame);
    renderEvents();
    renderSkills(frame);
  }

  function draw() {
    const frame = state.frames[state.frameIndex] || null;
    drawMaze(frame);
    setActorAnim(frame);
    if (frame && frame.phase === "impact" && frame.damage > 0) {
      showDamage(frame.damage);
    } else if (frame && frame.phase !== "impact") {
      els.damageText.classList.remove("show");
    }
  }

  // ---- Playback ----
  function stopPlayback() {
    state.playing = false;
    if (state.timer) { window.clearTimeout(state.timer); state.timer = null; }
    els.playBtn.textContent = "▶";
    if (state.frames.length) els.runState.textContent = "Paused";
  }

  function setFrame(index) {
    state.frameIndex = Math.max(0, Math.min(index, state.frames.length - 1));
    if (state.frameIndex >= state.frames.length - 1) stopPlayback();
    updateUi();
    draw();
  }

  let _phaseDelaysLogged = {};
  function frameDelay(frame) {
    if (!frame) return 1200;
    const speedFactor = 0.62 + Math.sqrt(Math.max(1, state.speed)) * 0.42;
    // minimums set to ~5× original for true ~15× combat extension (with 3× frame count)
    let minimum = 900;
    if (frame.phase === "approach") minimum = 1000;
    if (frame.phase === "slash") minimum = 800;
    if (frame.phase === "heavy") minimum = 1200;
    if (frame.phase === "impact") minimum = 1750;
    if (frame.phase === "recoil") minimum = 1300;
    if (frame.phase === "counter_windup") minimum = 1000;
    if (frame.phase === "counter_slash") minimum = 1000;
    if (frame.phase === "counter_impact") minimum = 2000;
    if (frame.phase === "counter_recoil") minimum = 1300;
    if (frame.phase === "retreat") minimum = 1000;
    if (frame.phase === "idle") minimum = 700;
    if (frame.retry || frame.failed) minimum = 2000;
    var delay = Math.max(minimum, 1400 / speedFactor);
    if (!_phaseDelaysLogged[frame.phase]) {
      _phaseDelaysLogged[frame.phase] = true;
      console.log("[frameDelay] phase=" + frame.phase + " delay=" + delay.toFixed(0) + "ms  speedFactor=" + speedFactor.toFixed(3));
    }
    return delay;
  }

  function scheduleTick() {
    if (!state.playing || !state.frames.length) return;
    const frame = state.frames[state.frameIndex];
    state.timer = window.setTimeout(() => { setFrame(state.frameIndex + 1); scheduleTick(); }, frameDelay(frame));
  }

  function startPlayback() {
    if (!state.frames.length || state.playing) return;
    state.playing = true;
    els.runState.textContent = "Playing";
    els.playBtn.textContent = "Ⅱ";
    scheduleTick();
  }

  function togglePlayback() {
    if (state.playing) { stopPlayback(); }
    else { if (state.frameIndex >= state.frames.length - 1) setFrame(0); startPlayback(); }
    updateUi();
  }

  function reset() { stopPlayback(); setFrame(0); }

  // ---- Data panel ----
  function toggleDataPanel() {
    state.dataPanelOpen = !state.dataPanelOpen;
    els.dataPanel.classList.toggle("hidden", !state.dataPanelOpen);
  }

  // ---- Init ----
  function initBattle(data, name = "maze_15_15.json") {
    stopPlayback();
    state.mapName = name;
    state.mapData = normalizeMapData(data);
    state.frames = buildFrames(state.mapData, 0);
    state.frameIndex = 0;
    state.maze = data.maze || DEFAULT_MAP_DATA.maze;
    const poses = findPositions(state.maze);
    state.playerPos = poses.player;
    state.bossPos = poses.boss;

    // BGM
    if (els.bgmBoss) { els.bgmBoss.volume = 0.35; els.bgmBoss.currentTime = 0; els.bgmBoss.play().catch(function(){}); }

    // Debug: log frame count and estimated duration
    _phaseDelaysLogged = {};
    var totalFrames = state.frames.length;
    var phaseCounts = {};
    state.frames.forEach(function(f) { phaseCounts[f.phase] = (phaseCounts[f.phase]||0)+1; });
    console.log("[initBattle] Total frames:", totalFrames);
    console.log("[initBattle] Phase counts:", JSON.stringify(phaseCounts));
    console.log("[initBattle] Estimated playback (speed=5): ~" + (totalFrames * 0.6).toFixed(0) + " seconds per full loop");
    console.log("[initBattle] Boss HPs / Skills:", JSON.stringify({ bosses: data.B, skills: data.PlayerSkills }));

    els.battleName.textContent = name;
    els.timeline.max = String(Math.max(0, state.frames.length - 1));
    els.timeline.value = "0";
    updateUi();
    draw();
  }

  async function loadDefaultMap() {
    const cached = loadCachedActiveMap();
    if (cached) { initBattle(cached.data, cached.name); return; }
    if (window.location.protocol === "file:") {
      initBattle(cloneData(DEFAULT_MAP_DATA), "Built-in example map");
      return;
    }
    for (const url of DEFAULT_MAP_CANDIDATES) {
      try {
        const res = await fetch(url, { cache: "no-store" });
        if (!res.ok) continue;
        const data = await res.json();
        initBattle(data, url.split("/").pop() || "maze_15_15.json");
        return;
      } catch (e) { console.warn(`Boss map candidate failed: ${url}`, e); }
    }
    initBattle(cloneData(DEFAULT_MAP_DATA), "Built-in example map");
  }

  // ---- Events ----
  els.playBtn.addEventListener("click", togglePlayback);
  els.resetBtn.addEventListener("click", reset);
  els.prevBtn.addEventListener("click", () => { stopPlayback(); setFrame(state.frameIndex - 1); });
  els.nextBtn.addEventListener("click", () => { stopPlayback(); setFrame(state.frameIndex + 1); });
  els.timeline.addEventListener("input", (e) => { stopPlayback(); setFrame(Number(e.target.value)); });
  els.speedRange.addEventListener("input", (e) => { state.speed = Number(e.target.value); els.speedLabel.textContent = `${state.speed}x`; if (state.playing) { window.clearTimeout(state.timer); scheduleTick(); } });
  els.dataToggleBtn.addEventListener("click", toggleDataPanel);
  els.closeDataBtn.addEventListener("click", toggleDataPanel);
  window.addEventListener("resize", draw);

  loadDefaultMap();
})();
