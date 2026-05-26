(() => {
  const DEFAULT_MAP_URL = "../maze_15_15.json";
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

  const ASSETS = {
    player: "../viz/assets/player.png",
    boss: "./assets/boss.png",
  };

  const TIMELINE = [
    { phase: "windup", motionT: 0.05, durationMs: 56, hitFlash: 0, shake: 0, impactText: null },
    { phase: "attack", motionT: 0.22, durationMs: 50, hitFlash: 0, shake: 0, impactText: null },
    { phase: "lunge", motionT: 0.38, durationMs: 44, hitFlash: 0, shake: 0, impactText: null },
    { phase: "impact", motionT: 0.52, durationMs: 68, hitFlash: 1, shake: 1, impactText: true },
    { phase: "recover", motionT: 0.74, durationMs: 58, hitFlash: 0, shake: 0.25, impactText: null },
    { phase: "idle", motionT: 0.96, durationMs: 72, hitFlash: 0, shake: 0, impactText: null },
  ];

  const PHASE_LABELS = {
    init: "初始化",
    idle: "战斗观察",
    windup: "蓄力",
    attack: "出招",
    lunge: "突进",
    impact: "命中",
    recover: "收招",
    retry: "准备重试",
    failed: "挑战失败",
  };

  const els = {
    introScreen: document.getElementById("introScreen"),
    startBattleBtn: document.getElementById("startBattleBtn"),
    introBossCount: document.getElementById("introBossCount"),
    introSkillCount: document.getElementById("introSkillCount"),
    introRoundCap: document.getElementById("introRoundCap"),
    introSkillPreview: document.getElementById("introSkillPreview"),
    introBossWave: document.getElementById("introBossWave"),
    introMeta: document.getElementById("introMeta"),
    battleName: document.getElementById("battleName"),
    runState: document.getElementById("runState"),
    metricBoss: document.getElementById("metricBoss"),
    metricAttempt: document.getElementById("metricAttempt"),
    metricRound: document.getElementById("metricRound"),
    metricCoins: document.getElementById("metricCoins"),
    phaseLabel: document.getElementById("phaseLabel"),
    battleReadout: document.getElementById("battleReadout"),
    timeline: document.getElementById("timeline"),
    speedRange: document.getElementById("speedRange"),
    speedLabel: document.getElementById("speedLabel"),
    resetBtn: document.getElementById("resetBtn"),
    prevBtn: document.getElementById("prevBtn"),
    playBtn: document.getElementById("playBtn"),
    nextBtn: document.getElementById("nextBtn"),
    toggleTrail: document.getElementById("toggleTrail"),
    toggleGlow: document.getElementById("toggleGlow"),
    toggleSprites: document.getElementById("toggleSprites"),
    togglePulse: document.getElementById("togglePulse"),
    startingCoinsInput: document.getElementById("startingCoinsInput"),
    rebuildBtn: document.getElementById("rebuildBtn"),
    loadDefaultBtn: document.getElementById("loadDefaultBtn"),
    fileInput: document.getElementById("fileInput"),
    mapMeta: document.getElementById("mapMeta"),
    detailBoss: document.getElementById("detailBoss"),
    detailAttempt: document.getElementById("detailAttempt"),
    detailTurn: document.getElementById("detailTurn"),
    detailAction: document.getElementById("detailAction"),
    detailDamage: document.getElementById("detailDamage"),
    detailBossHp: document.getElementById("detailBossHp"),
    skillList: document.getElementById("skillList"),
    eventList: document.getElementById("eventList"),
    canvas: document.getElementById("bossCanvas"),
  };

  const ctx = els.canvas.getContext("2d");

  const state = {
    mapData: null,
    mapName: "maze_15_15.json",
    frames: [],
    frameIndex: 0,
    speed: 5,
    timer: null,
    playing: false,
    mode: "live",
    showTrail: true,
    showGlow: true,
    showSprites: true,
    showPulse: true,
    startingCoins: 0,
    assets: {},
    layout: {
      dpr: 1,
      width: 0,
      height: 0,
      scale: 1,
      offsetX: 0,
      offsetY: 0,
    },
    embedMode: false,
    embedRequestId: null,
  };

  function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
  }

  function parseBattleQuery() {
    const params = new URLSearchParams(window.location.search);
    const payload = params.get("battle");
    if (!payload) return null;
    try {
      const decoded = JSON.parse(payload);
      return decoded && typeof decoded === "object" ? decoded : null;
    } catch (error) {
      console.warn("Invalid boss battle query payload.", error);
      return null;
    }
  }

  function buildBattleConfigFromPayload(payload) {
    if (!payload || !Array.isArray(payload.PlayerSkills) || !Array.isArray(payload.B)) {
      throw new Error("战斗参数缺失");
    }
    return {
      B: payload.B,
      PlayerSkills: payload.PlayerSkills,
      minRouds: payload.minRouds ?? payload.minRounds,
      CoinConsumption: payload.CoinConsumption ?? payload.coinConsumption,
    };
  }

  function notifyBattleComplete() {
    if (!state.embedMode || !state.frames.length) return;
    const last = state.frames[state.frames.length - 1];
    const payload = {
      type: "maze-boss-complete",
      requestId: state.embedRequestId,
      result: last && last.defeated && !last.failed ? 1 : 0,
      bossIndex: last?.bossIndex ?? 1,
      coins: last?.coins ?? state.startingCoins,
    };
    window.parent?.postMessage(payload, "*");
  }

  function normalizeMapData(data) {
    if (!data || !Array.isArray(data.B) || !Array.isArray(data.PlayerSkills)) {
      throw new Error("Boss 战数据需要包含 B 和 PlayerSkills");
    }
    const minRounds = Number(data.minRouds ?? data.minRounds ?? 0);
    const coinConsumption = Number(data.CoinConsumption ?? data.coinConsumption ?? 0);
    if (!Number.isFinite(minRounds) || minRounds <= 0) {
      throw new Error("minRouds 必须是正整数");
    }
    if (!Number.isFinite(coinConsumption) || coinConsumption < 0) {
      throw new Error("CoinConsumption 必须是非负数");
    }
    const bossHps = data.B.map((value) => Number(value));
    if (!bossHps.length || bossHps.some((hp) => !Number.isFinite(hp) || hp <= 0)) {
      throw new Error("B 必须是正整数数组");
    }
    const skills = data.PlayerSkills.map((spec, index) => {
      if (!Array.isArray(spec) || spec.length < 2) {
        throw new Error(`PlayerSkills[${index}] 格式错误`);
      }
      const damage = Number(spec[0]);
      const cooldown = Number(spec[1]);
      const remainingCd = Number(spec[2] ?? 0);
      if (!Number.isFinite(damage) || damage < 0 || !Number.isFinite(cooldown) || cooldown < 0 || !Number.isFinite(remainingCd) || remainingCd < 0) {
        throw new Error(`PlayerSkills[${index}] 数值错误`);
      }
      return { damage, cooldown, remainingCd };
    });
    return {
      raw: data,
      bossHps,
      skills,
      minRounds,
      coinConsumption,
    };
  }

  function buildInitialSkillStates(skills) {
    return skills.map((skill) => ({
      damage: skill.damage,
      cooldown: skill.cooldown,
      remainingCd: skill.remainingCd ?? 0,
    }));
  }

  function snapshotSkills(skills) {
    return skills.map((skill) => ({
      damage: skill.damage,
      cooldown: skill.cooldown,
      remainingCd: skill.remainingCd,
    }));
  }

  function tickCooldowns(skills) {
    skills.forEach((skill) => {
      if (skill.remainingCd > 0) {
        skill.remainingCd -= 1;
      }
    });
  }

  function decideCombat(skills) {
    let bestIdx = null;
    let bestDamage = -1;
    skills.forEach((skill, index) => {
      if (skill.remainingCd === 0 && skill.damage > bestDamage) {
        bestDamage = skill.damage;
        bestIdx = index;
      }
    });
    return bestIdx;
  }

  function phaseLabel(frame) {
    if (!frame) return PHASE_LABELS.init;
    if (frame.failed) return PHASE_LABELS.failed;
    if (frame.retry) return PHASE_LABELS.retry;
    if (frame.defeated && frame.phase === "idle") return "Boss 击破";
    return PHASE_LABELS[frame.phase] || "战斗中";
  }

  function eventLabel(frame) {
    if (frame.failed) return `金币耗尽，Boss ${frame.bossIndex} 挑战失败`;
    if (frame.retry) return `未在 ${frame.minRounds} 轮内击败 Boss，扣除 ${frame.coinConsumption} 金币后重试`;
    if (frame.skillIdx === null) return `第 ${frame.attackRound} 轮等待，技能全部冷却中`;
    if (frame.defeated && frame.phase === "impact") return `技能 S${frame.skillIdx} 命中 ${frame.damage}，Boss 被击败`;
    if (frame.phase === "impact" && frame.damage > 0) return `技能 S${frame.skillIdx} 命中 ${frame.damage}`;
    if (frame.phase === "windup") return `技能 S${frame.skillIdx} 蓄力`;
    return "";
  }

  function buildFrames(config, startingCoins) {
    const frames = [];
    const skills = buildInitialSkillStates(config.skills);
    let coins = Math.max(0, Number(startingCoins) || 0);
    let totalRound = 0;
    let shouldStop = false;

    for (let bossIndexZero = 0; bossIndexZero < config.bossHps.length; bossIndexZero += 1) {
      const bossHpMax = config.bossHps[bossIndexZero];
      let bossHp = bossHpMax;
      let attempt = 0;
      const bossIndex = bossIndexZero + 1;

      while (bossHp > 0 && coins >= 0 && !shouldStop) {
        attempt += 1;

        for (let attackRound = 1; attackRound <= config.minRounds; attackRound += 1) {
          totalRound += 1;
          const skillIdx = decideCombat(skills);
          let damage = 0;

          if (skillIdx !== null) {
            damage = skills[skillIdx].damage;
            skills[skillIdx].remainingCd = skills[skillIdx].cooldown;
            bossHp = Math.max(0, bossHp - damage);
          }

          const defeated = bossHp <= 0;
          tickCooldowns(skills);

          TIMELINE.forEach((step) => {
            const activePhase = damage > 0 ? step.phase : "idle";
            frames.push({
              bossIndex,
              bossTotal: config.bossHps.length,
              attempt,
              attackRound,
              totalRound,
              skillIdx,
              damage,
              coins,
              bossHp,
              bossHpMax,
              defeated,
              retry: false,
              failed: false,
              skills: snapshotSkills(skills),
              phase: activePhase,
              motionT: step.motionT,
              hitFlash: damage > 0 ? step.hitFlash : 0,
              shake: damage > 0 ? step.shake : 0,
              impactText: damage > 0 && step.impactText ? `-${damage}` : null,
              durationMs: step.durationMs,
              minRounds: config.minRounds,
              coinConsumption: config.coinConsumption,
              statusText: eventLabel({
                bossIndex,
                attackRound,
                skillIdx,
                damage,
                defeated,
                phase: activePhase,
                retry: false,
                failed: false,
                minRounds: config.minRounds,
                coinConsumption: config.coinConsumption,
              }),
            });
          });

          if (defeated) {
            break;
          }
        }

        if (bossHp <= 0) {
          break;
        }

        coins -= config.coinConsumption;
        const failed = coins <= 0;
        frames.push({
          bossIndex,
          bossTotal: config.bossHps.length,
          attempt,
          attackRound: config.minRounds,
          totalRound,
          skillIdx: null,
          damage: 0,
          coins: Math.max(coins, 0),
          bossHp,
          bossHpMax,
          defeated: false,
          retry: !failed,
          failed,
          skills: snapshotSkills(skills),
          phase: failed ? "failed" : "retry",
          motionT: 1,
          hitFlash: 0,
          shake: 0,
          impactText: null,
          durationMs: 160,
          minRounds: config.minRounds,
          coinConsumption: config.coinConsumption,
          statusText: failed
            ? `金币降为 0，Boss ${bossIndex} 挑战终止`
            : `挑战超时，扣除 ${config.coinConsumption} 金币后继续挑战同一个 Boss`,
        });

        if (failed) {
          shouldStop = true;
          break;
        }
      }
    }

    return frames;
  }

  function loadAssets() {
    Object.entries(ASSETS).forEach(([name, src]) => {
      const image = new Image();
      image.onload = () => draw();
      image.onerror = () => {
        state.assets[name] = null;
      };
      image.src = src;
      state.assets[name] = image;
    });
  }

  function updateIntro(config) {
    els.introBossCount.textContent = String(config.bossHps.length);
    els.introSkillCount.textContent = String(config.skills.length);
    els.introRoundCap.textContent = String(config.minRounds);
    els.introMeta.textContent = `${state.mapName} / Boss ${config.bossHps.length} 个 / 失败扣币 ${config.coinConsumption}`;
    if (els.startBattleBtn) {
      els.startBattleBtn.disabled = false;
    }

    els.introSkillPreview.innerHTML = "";
    config.skills.slice(0, 6).forEach((skill, index) => {
      const item = document.createElement("div");
      item.className = "intro-skill-chip";
      item.innerHTML = `<strong>S${index}</strong><span>${skill.damage} damage<br />cd ${skill.cooldown}</span>`;
      els.introSkillPreview.appendChild(item);
    });

    els.introBossWave.innerHTML = "";
    config.bossHps.forEach((_, index) => {
      const item = document.createElement("div");
      item.className = "boss-wave-item";
      item.textContent = `B${index + 1}`;
      els.introBossWave.appendChild(item);
    });
  }

  function fitCanvas() {
    const rect = els.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(640, Math.floor(rect.width * dpr));
    const height = Math.max(360, Math.floor(rect.height * dpr));
    if (els.canvas.width !== width || els.canvas.height !== height) {
      els.canvas.width = width;
      els.canvas.height = height;
    }
    state.layout.dpr = dpr;
    state.layout.width = width;
    state.layout.height = height;
    state.layout.scale = Math.min(width / 1280, height / 720);
    state.layout.offsetX = Math.floor((width - 1280 * state.layout.scale) / 2);
    state.layout.offsetY = Math.floor((height - 720 * state.layout.scale) / 2);
  }

  function currentFrame() {
    return state.frames[state.frameIndex] || null;
  }

  function phaseEnergy(frame) {
    if (!frame) return 0;
    if (frame.failed) return 0.88;
    if (frame.retry) return 0.55;
    if (frame.defeated) return 0.7;
    if (frame.damage <= 0) return 0.12;
    return {
      windup: 0.28,
      attack: 0.52,
      lunge: 0.8,
      impact: 1,
      recover: 0.38,
      idle: 0.16,
    }[frame.phase] ?? 0.16;
  }

  function withCanvasSpace(callback) {
    fitCanvas();
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    ctx.setTransform(
      state.layout.scale,
      0,
      0,
      state.layout.scale,
      state.layout.offsetX,
      state.layout.offsetY
    );
    callback();
    ctx.restore();
  }

  function drawRoundedRect(x, y, width, height, radius, fillStyle, strokeStyle = null, lineWidth = 1) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    if (fillStyle) {
      ctx.fillStyle = fillStyle;
      ctx.fill();
    }
    if (strokeStyle) {
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.stroke();
    }
  }

  function drawEmptyState(message) {
    fitCanvas();
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#05060a";
    ctx.fillRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#f5f7fb";
    ctx.font = `${18 * state.layout.dpr}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(message, state.layout.width / 2, state.layout.height / 2);
  }

  function drawBackground(frame) {
    const grad = ctx.createLinearGradient(0, 0, 0, 720);
    grad.addColorStop(0, "#05060a");
    grad.addColorStop(1, "#0b1220");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1280, 720);

    if (state.showGlow) {
      const leftGlow = ctx.createRadialGradient(240, 200, 20, 240, 200, 240);
      leftGlow.addColorStop(0, "rgba(37, 99, 235, 0.24)");
      leftGlow.addColorStop(1, "rgba(37, 99, 235, 0)");
      ctx.fillStyle = leftGlow;
      ctx.fillRect(0, 0, 600, 500);

      const rightGlow = ctx.createRadialGradient(980, 180, 20, 980, 180, 280);
      rightGlow.addColorStop(0, frame && frame.failed ? "rgba(239, 68, 68, 0.26)" : "rgba(220, 38, 38, 0.22)");
      rightGlow.addColorStop(1, "rgba(220, 38, 38, 0)");
      ctx.fillStyle = rightGlow;
      ctx.fillRect(700, 0, 580, 440);
    }

    if (state.mode === "damage") {
      ctx.save();
      ctx.translate(450, 252);
      ctx.rotate(-0.26);
      const slash = ctx.createLinearGradient(-220, 0, 220, 0);
      slash.addColorStop(0, "rgba(245, 158, 11, 0)");
      slash.addColorStop(0.5, "rgba(255, 247, 237, 0.38)");
      slash.addColorStop(1, "rgba(251, 113, 133, 0)");
      ctx.fillStyle = slash;
      ctx.fillRect(-240, -8, 480, 16);
      ctx.restore();
    } else if (state.mode === "cooldown") {
      ctx.strokeStyle = "rgba(96, 165, 250, 0.08)";
      ctx.lineWidth = 1;
      for (let i = 0; i < 6; i += 1) {
        ctx.beginPath();
        ctx.arc(245, 240, 54 + i * 28, 0, Math.PI * 2);
        ctx.stroke();
      }
    } else if (state.mode === "outcome") {
      const outcomeGlow = ctx.createLinearGradient(0, 0, 0, 240);
      const tone = frame?.failed
        ? "rgba(239, 68, 68, 0.22)"
        : frame?.defeated
          ? "rgba(34, 197, 94, 0.2)"
          : frame?.retry
            ? "rgba(245, 158, 11, 0.2)"
            : "rgba(109, 93, 252, 0.16)";
      outcomeGlow.addColorStop(0, tone);
      outcomeGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = outcomeGlow;
      ctx.fillRect(0, 0, 1280, 260);
    }
  }

  function drawArena(frame) {
    drawRoundedRect(56, 72, 810, 566, 22, "#0b1220", "#334155", 2);
    drawRoundedRect(900, 72, 324, 566, 18, "#0f172a", "#334155", 2);

    ctx.save();
    ctx.beginPath();
    drawRoundedRectPath(56, 72, 810, 566, 22);
    ctx.clip();

    const pulse = state.showPulse && frame ? phaseEnergy(frame) : 0.08;
    for (let i = 0; i < 14; i += 1) {
      ctx.strokeStyle = `rgba(255,255,255,${0.02 + i * 0.003})`;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(110 + i * 46, 116);
      ctx.lineTo(54 + i * 46, 620);
      ctx.stroke();
    }

    ctx.fillStyle = "#020617";
    ctx.beginPath();
    ctx.ellipse(455, 518, 340, 54, 0, 0, Math.PI * 2);
    ctx.fill();

    const ringColor = state.mode === "damage"
      ? `rgba(251, 113, 133, ${0.16 + pulse * 0.24})`
      : state.mode === "cooldown"
        ? `rgba(96, 165, 250, ${0.14 + pulse * 0.22})`
        : state.mode === "outcome"
          ? `rgba(34, 197, 94, ${frame?.defeated ? 0.24 + pulse * 0.18 : 0.12 + pulse * 0.16})`
          : `rgba(249, 115, 22, ${0.12 + pulse * 0.2})`;
    ctx.strokeStyle = ringColor;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.ellipse(455, 538, 300, 24, 0, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "rgba(17, 24, 39, 0.88)";
    ctx.beginPath();
    ctx.ellipse(455, 534, 248, 16, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();

    drawRoundedRect(925, 106, 274, 44, 10, "#111827", "#475569", 1.5);
  }

  function drawRoundedRectPath(x, y, width, height, radius) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    ctx.closePath();
  }

  function drawGlow(x, y, radiusX, radiusY, color, alpha) {
    if (!state.showGlow || alpha <= 0) return;
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(radiusX, radiusY);
    const gradient = ctx.createRadialGradient(0, 0, 0.05, 0, 0, 1);
    gradient.addColorStop(0, color.replace("ALPHA", String(alpha)));
    gradient.addColorStop(1, color.replace("ALPHA", "0"));
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, 1, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  function drawActorShadow(x, y, width, height, alpha) {
    ctx.fillStyle = `rgba(2, 6, 23, ${alpha})`;
    ctx.beginPath();
    ctx.ellipse(x, y, width, height, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  function drawSprite(image, x, y, width, height) {
    if (state.showSprites && image && image.complete) {
      ctx.drawImage(image, x, y, width, height);
      return true;
    }
    return false;
  }

  function drawFallbackActor(x, y, radius, fill, label) {
    ctx.fillStyle = fill;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.85)";
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = "800 28px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, x, y + 2);
  }

  function clamp01(value) {
    return Math.max(0, Math.min(1, value));
  }

  function lerp(start, end, amount) {
    return start + (end - start) * amount;
  }

  function easeOut(value) {
    const t = clamp01(value);
    return 1 - (1 - t) * (1 - t);
  }

  function phaseProgress(frame) {
    return {
      windup: 0.08,
      attack: 0.32,
      lunge: 0.62,
      impact: 0.86,
      recover: 1,
      idle: 1,
    }[frame.phase] ?? 0;
  }

  function pointBetween(start, end, amount) {
    return {
      x: lerp(start.x, end.x, amount),
      y: lerp(start.y, end.y, amount),
    };
  }

  function drawSkillDamageText(frame, anchor, color) {
    if (!frame.impactText || !["impact", "recover"].includes(frame.phase)) return;
    const lift = frame.phase === "impact" ? 0 : 18;
    const alpha = frame.phase === "impact" ? 1 : 0.54;
    ctx.save();
    ctx.translate(anchor.x + 18, anchor.y - 112 - lift);
    ctx.rotate(-0.18);
    ctx.globalAlpha = alpha;
    ctx.fillStyle = "rgba(2, 6, 23, 0.38)";
    ctx.font = "900 46px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(frame.impactText, 3, 5);
    ctx.fillStyle = color;
    ctx.fillText(frame.impactText, 0, 0);
    ctx.restore();
  }

  function drawSkillCleave(frame, playerAnchor, bossAnchor) {
    const progress = phaseProgress(frame);
    if (frame.phase === "windup") {
      drawGlow(playerAnchor.x + 28, playerAnchor.y - 32, 42, 42, "rgba(249, 115, 22, ALPHA)", 0.34);
      ctx.strokeStyle = "rgba(255, 247, 237, 0.78)";
      ctx.lineWidth = 5;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(playerAnchor.x + 4, playerAnchor.y + 18);
      ctx.lineTo(playerAnchor.x + 54, playerAnchor.y - 58);
      ctx.stroke();
      return;
    }

    if (progress < 0.2) return;
    const slashProgress = easeOut((progress - 0.2) / 0.62);
    const length = 210 * slashProgress;
    ctx.save();
    ctx.translate(bossAnchor.x + 10, bossAnchor.y - 4);
    ctx.rotate(-0.58);
    [
      { width: 30, color: "rgba(249, 115, 22, 0.2)" },
      { width: 18, color: "rgba(251, 113, 133, 0.28)" },
      { width: 7, color: "rgba(255, 247, 237, 0.88)" },
    ].forEach((layer) => {
      ctx.strokeStyle = layer.color;
      ctx.lineWidth = layer.width;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(-length * 0.62, -38);
      ctx.lineTo(length * 0.52, 42);
      ctx.stroke();
    });
    ctx.restore();

    if (["impact", "recover"].includes(frame.phase)) {
      for (let i = 0; i < 9; i += 1) {
        const angle = -0.9 + i * 0.23;
        const inner = 18 + (i % 3) * 4;
        const outer = 56 + (i % 2) * 16;
        ctx.strokeStyle = i % 2 ? "rgba(254, 240, 138, 0.68)" : "rgba(251, 113, 133, 0.62)";
        ctx.lineWidth = 2.4;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(bossAnchor.x + Math.cos(angle) * inner, bossAnchor.y + Math.sin(angle) * inner);
        ctx.lineTo(bossAnchor.x + Math.cos(angle) * outer, bossAnchor.y + Math.sin(angle) * outer);
        ctx.stroke();
      }
    }
    drawSkillDamageText(frame, bossAnchor, "#fff7ed");
  }

  function drawSkillMissile(frame, playerAnchor, bossAnchor) {
    const progress = phaseProgress(frame);
    if (frame.phase === "windup") {
      drawGlow(playerAnchor.x + 24, playerAnchor.y - 18, 34, 34, "rgba(45, 212, 191, ALPHA)", 0.36);
      ctx.fillStyle = "rgba(153, 246, 228, 0.9)";
      ctx.beginPath();
      ctx.arc(playerAnchor.x + 24, playerAnchor.y - 18, 9, 0, Math.PI * 2);
      ctx.fill();
      return;
    }

    const t = clamp01((progress - 0.16) / 0.72);
    const start = { x: playerAnchor.x + 28, y: playerAnchor.y - 20 };
    const end = { x: bossAnchor.x - 12, y: bossAnchor.y - 18 };
    const orb = pointBetween(start, end, easeOut(t));
    const tail = pointBetween(start, end, clamp01(t - 0.18));

    ctx.strokeStyle = "rgba(45, 212, 191, 0.42)";
    ctx.lineWidth = 8;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(tail.x, tail.y);
    ctx.lineTo(orb.x, orb.y);
    ctx.stroke();

    ctx.strokeStyle = "rgba(191, 219, 254, 0.9)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(tail.x, tail.y);
    ctx.lineTo(orb.x, orb.y);
    ctx.stroke();

    drawGlow(orb.x, orb.y, 26, 26, "rgba(45, 212, 191, ALPHA)", 0.4);
    ctx.fillStyle = "#e0f2fe";
    ctx.beginPath();
    ctx.arc(orb.x, orb.y, 8, 0, Math.PI * 2);
    ctx.fill();

    if (["impact", "recover"].includes(frame.phase)) {
      ctx.strokeStyle = "rgba(125, 211, 252, 0.72)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(end.x, end.y, frame.phase === "impact" ? 34 : 48, 0, Math.PI * 2);
      ctx.stroke();
    }
    drawSkillDamageText(frame, bossAnchor, "#bae6fd");
  }

  function drawSkillPulse(frame, playerAnchor, bossAnchor) {
    const progress = phaseProgress(frame);
    const pulse = easeOut(progress);
    if (frame.phase === "windup") {
      ctx.strokeStyle = "rgba(167, 139, 250, 0.62)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.arc(playerAnchor.x, playerAnchor.y - 10, 34 + pulse * 24, 0, Math.PI * 2);
      ctx.stroke();
    }

    const center = { x: bossAnchor.x, y: bossAnchor.y - 10 };
    for (let i = 0; i < 3; i += 1) {
      const radius = 28 + pulse * (52 + i * 28);
      const alpha = Math.max(0, 0.48 - i * 0.1 - pulse * 0.16);
      ctx.strokeStyle = `rgba(167, 139, 250, ${alpha})`;
      ctx.lineWidth = 5 - i;
      ctx.beginPath();
      ctx.arc(center.x, center.y, radius, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (["impact", "recover"].includes(frame.phase)) {
      drawGlow(center.x, center.y, 92, 92, "rgba(109, 93, 252, ALPHA)", frame.phase === "impact" ? 0.35 : 0.18);
      ctx.fillStyle = frame.phase === "impact" ? "rgba(216, 180, 254, 0.22)" : "rgba(216, 180, 254, 0.1)";
      ctx.beginPath();
      ctx.arc(center.x, center.y, frame.phase === "impact" ? 58 : 76, 0, Math.PI * 2);
      ctx.fill();
    }
    drawSkillDamageText(frame, bossAnchor, "#ddd6fe");
  }

  function drawJaggedBolt(start, end, seed, color, width, alpha) {
    const segments = 7;
    ctx.strokeStyle = color.replace("ALPHA", String(alpha));
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    for (let i = 0; i <= segments; i += 1) {
      const t = i / segments;
      const base = pointBetween(start, end, t);
      const wobble = Math.sin((i + seed) * 2.4) * 18 * (1 - Math.abs(0.5 - t));
      const x = base.x + wobble;
      const y = base.y + Math.cos((i + seed) * 1.7) * 8;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  function drawSkillLightning(frame, playerAnchor, bossAnchor) {
    const progress = phaseProgress(frame);
    if (frame.phase === "windup") {
      drawGlow(playerAnchor.x + 22, playerAnchor.y - 34, 46, 46, "rgba(250, 204, 21, ALPHA)", 0.36);
      for (let i = 0; i < 3; i += 1) {
        drawJaggedBolt(
          { x: playerAnchor.x - 10 + i * 18, y: playerAnchor.y - 72 },
          { x: playerAnchor.x + 22, y: playerAnchor.y - 24 },
          i,
          "rgba(250, 204, 21, ALPHA)",
          2,
          0.62
        );
      }
      return;
    }

    const boltTop = { x: bossAnchor.x + 8, y: 138 };
    const boltEnd = { x: bossAnchor.x, y: bossAnchor.y - 18 };
    const alpha = frame.phase === "recover" ? 0.38 : 0.86;
    drawJaggedBolt(boltTop, boltEnd, frame.totalRound, "rgba(250, 204, 21, ALPHA)", 8, alpha * 0.35);
    drawJaggedBolt(boltTop, boltEnd, frame.totalRound + 3, "rgba(255, 247, 237, ALPHA)", 3, alpha);
    drawJaggedBolt({ x: playerAnchor.x + 42, y: playerAnchor.y - 30 }, boltEnd, frame.totalRound + 5, "rgba(125, 211, 252, ALPHA)", 3, alpha * 0.58);

    if (["impact", "recover"].includes(frame.phase)) {
      for (let i = 0; i < 10; i += 1) {
        const angle = i * (Math.PI * 2 / 10);
        const len = frame.phase === "impact" ? 62 : 42;
        ctx.strokeStyle = i % 2 ? "rgba(250, 204, 21, 0.68)" : "rgba(191, 219, 254, 0.58)";
        ctx.lineWidth = 2.2;
        ctx.beginPath();
        ctx.moveTo(bossAnchor.x, bossAnchor.y - 16);
        ctx.lineTo(bossAnchor.x + Math.cos(angle) * len, bossAnchor.y - 16 + Math.sin(angle) * len);
        ctx.stroke();
      }
    }
    drawSkillDamageText(frame, bossAnchor, "#fef08a");
  }

  function drawSkillAnimation(frame, playerAnchor, bossAnchor) {
    if (frame.skillIdx === null || frame.damage <= 0) return;
    const skillType = frame.skillIdx % 4;
    if (skillType === 0) drawSkillCleave(frame, playerAnchor, bossAnchor);
    else if (skillType === 1) drawSkillMissile(frame, playerAnchor, bossAnchor);
    else if (skillType === 2) drawSkillPulse(frame, playerAnchor, bossAnchor);
    else drawSkillLightning(frame, playerAnchor, bossAnchor);
  }

  function drawBanner(frame) {
    let label = "";
    let face = "";
    let edge = "";
    let text = "";
    if (frame.failed) {
      label = "DEFEAT";
      face = "#450a0a";
      edge = "#ef4444";
      text = "#fee2e2";
    } else if (frame.retry) {
      label = "RETRY";
      face = "#431407";
      edge = "#f59e0b";
      text = "#fef3c7";
    } else if (frame.defeated) {
      label = "BOSS DOWN";
      face = "#052e16";
      edge = "#22c55e";
      text = "#dcfce7";
    }
    if (!label) return;
    drawRoundedRect(314, 18, 176, 38, 10, face, edge, 2);
    ctx.fillStyle = text;
    ctx.font = "900 18px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, 402, 37);
  }

  function drawProgressBar(x, y, width, height, ratio, fill, bg) {
    drawRoundedRect(x, y, width, height, 10, bg, "#475569", 1);
    const clamped = Math.max(0, Math.min(1, ratio));
    if (clamped <= 0) return;
    drawRoundedRect(x + 2, y + 2, Math.max(0, width * clamped - 4), Math.max(0, height - 4), 8, fill);
    ctx.fillStyle = "rgba(255,255,255,0.12)";
    ctx.fillRect(x + 3, y + height * 0.58, Math.max(0, width * clamped - 6), Math.max(2, height * 0.16));
  }

  function drawArenaActors(frame) {
    const energy = phaseEnergy(frame);
    const playerX = 120;
    const playerY = 196;
    const playerW = 230;
    const playerH = 350;
    const bossW = 300;
    const bossH = 350;
    const bossX = 506;
    const bossY = 196 + (frame.defeated ? 8 : 0);
    const playerAnchor = { x: playerX + 132, y: playerY + 178 };
    const bossAnchor = { x: bossX + 150, y: bossY + 168 };

    drawGlow(playerX + 118, playerY + 178, 112, 96, "rgba(37, 99, 235, ALPHA)", 0.26 + energy * 0.08);
    drawGlow(bossX + 150, bossY + 190, 150, 132, "rgba(220, 38, 38, ALPHA)", 0.2 + energy * 0.18);

    if (state.mode === "cooldown") {
      const readyCount = frame.skills.filter((skill) => skill.remainingCd === 0).length;
      for (let i = 0; i < frame.skills.length; i += 1) {
        const radius = 76 + i * 18;
        ctx.strokeStyle = i < readyCount ? "rgba(96, 165, 250, 0.24)" : "rgba(148, 163, 184, 0.12)";
        ctx.lineWidth = i < readyCount ? 3 : 2;
        ctx.beginPath();
        ctx.arc(playerX + 116, playerY + 180, radius, -Math.PI * 0.75, Math.PI * 0.1);
        ctx.stroke();
      }
    }

    drawActorShadow(playerX + 110, 534, 82, 16, 0.72);
    drawActorShadow(bossX + 150, 534, 104, 18, 0.78);

    if (!drawSprite(state.assets.player, playerX, playerY, playerW, playerH)) {
      drawFallbackActor(playerX + 115, playerY + 160, 56, "#60a5fa", "P");
    }

    ctx.save();
    if (frame.hitFlash > 0) {
      ctx.globalAlpha = 0.86;
    }
    const bossDrawn = drawSprite(state.assets.boss, bossX, bossY, bossW, bossH);
    ctx.restore();
    if (!bossDrawn) {
      drawFallbackActor(bossX + 150, bossY + 172, 66, "#ef4444", "B");
    }
    if (frame.hitFlash > 0) {
      ctx.fillStyle = `rgba(255,255,255,${0.16 + frame.hitFlash * 0.16})`;
      ctx.beginPath();
      ctx.ellipse(bossX + 150, bossY + 174, 104, 128, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    if (state.mode === "outcome" && (frame.failed || frame.retry || frame.defeated)) {
      const overlay = frame.failed
        ? "rgba(239, 68, 68, 0.18)"
        : frame.retry
          ? "rgba(245, 158, 11, 0.16)"
          : "rgba(34, 197, 94, 0.16)";
      ctx.fillStyle = overlay;
      ctx.beginPath();
      ctx.ellipse(bossX + 150, bossY + 174, 124, 148, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    drawSkillAnimation(frame, playerAnchor, bossAnchor);

    drawRoundedRect(88, 20, 154, 34, 9, "#0f172a", "#3b82f6", 1.5);
    drawRoundedRect(582, 12, 258, 54, 10, "#2b0a12", "#fb7185", 1.5);
    ctx.fillStyle = "#eff6ff";
    ctx.font = "700 16px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("PLAYER", 165, 37);
    ctx.fillStyle = "#ffe4e6";
    ctx.font = "700 14px sans-serif";
    ctx.fillText("DEMON SLIME", 711, 27);

    ctx.textAlign = "left";
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "500 16px sans-serif";
    ctx.fillText(`Coins ${frame.coins}`, 108, 654);
    ctx.fillText(`Action ${frame.skillIdx === null ? "WAIT" : `Skill ${frame.skillIdx}`}`, 288, 654);
    ctx.fillStyle = "#fca5a5";
    ctx.fillText(`Damage ${frame.damage}`, 546, 654);

    ctx.fillStyle = "#f8fafc";
    ctx.font = "600 13px sans-serif";
    ctx.textAlign = "left";
    ctx.fillText("UNKNOWN TARGET STATUS", 604, 48);
  }

  function drawSidePanel(frame) {
    const status = frame.failed ? "Failed" : frame.retry ? "Retry" : frame.defeated ? "Boss Down" : "Fighting";
    const color = frame.failed ? "#ef4444" : frame.retry ? "#f59e0b" : frame.defeated ? "#22c55e" : "#60a5fa";
    ctx.fillStyle = "#f8fafc";
    ctx.font = "700 18px sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("BATTLE FLOW", 948, 128);
    ctx.textAlign = "center";
    ctx.fillStyle = color;
    ctx.font = "700 24px sans-serif";
    ctx.fillText(status, 1062, 182);

    ctx.textAlign = "left";
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "500 17px sans-serif";
    ctx.fillText(`Attempt ${frame.attempt}`, 938, 238);
    ctx.fillText(`Turn ${frame.attackRound}`, 1092, 238);
    ctx.fillText(`Boss ${frame.bossIndex}/${frame.bossTotal}`, 938, 286);
    ctx.fillStyle = "#f8fafc";
    ctx.font = "700 18px sans-serif";
    ctx.fillText("Skills", 938, 342);

    let skillY = 388;
    frame.skills.forEach((skill, index) => {
      if (skillY > 584) return;
      const ready = skill.remainingCd === 0;
      const skillBg = state.mode === "cooldown" && ready
        ? "#06233a"
        : state.mode === "damage" && frame.skillIdx === index
          ? "#2b0a12"
          : ready
            ? "#0b1220"
            : "#111827";
      drawRoundedRect(930, skillY - 24, 276, 38, 10, skillBg, "#1e293b", 1);
      ctx.fillStyle = "#f8fafc";
      ctx.font = "600 14px sans-serif";
      ctx.fillText(`S${index}`, 944, skillY - 1);
      ctx.fillStyle = "#cbd5e1";
      ctx.fillText(`${skill.damage} dmg`, 990, skillY - 1);
      ctx.fillStyle = ready ? "#22c55e" : "#94a3b8";
      ctx.fillText(`cd ${skill.remainingCd}/${skill.cooldown}`, 1092, skillY - 1);
      const ratio = skill.cooldown === 0 ? 1 : (skill.cooldown - skill.remainingCd) / skill.cooldown;
      drawProgressBar(1094, skillY + 6, 98, 10, ratio, ready ? "#22c55e" : "#64748b", "#111827");
      skillY += 52;
    });
  }

  function drawFrame(frame) {
    drawBackground(frame);
    drawArena(frame);
    drawArenaActors(frame);
    drawSidePanel(frame);
    drawBanner(frame);
  }

  function draw() {
    if (!state.frames.length) {
      drawEmptyState("等待 Boss 战数据");
      return;
    }
    const frame = currentFrame();
    withCanvasSpace(() => {
      drawFrame(frame);
    });
  }

  function renderEvents() {
    const events = state.frames
      .map((frame, index) => ({ frame, index }))
      .filter(({ index, frame }) => index <= state.frameIndex && frame.statusText)
      .filter(({ frame }) => frame.phase === "impact" || frame.retry || frame.failed || frame.phase === "windup")
      .slice(-12)
      .reverse();

    els.eventList.innerHTML = "";
    events.forEach(({ frame }) => {
      const item = document.createElement("li");
      item.className = frame.failed
        ? "phase-failed"
        : frame.retry
          ? "phase-retry"
          : frame.defeated && frame.phase === "impact"
            ? "phase-win"
            : "phase-damage";
      const round = document.createElement("span");
      const copy = document.createElement("span");
      round.className = "event-round";
      copy.className = "event-copy";
      round.textContent = `#${frame.totalRound}`;
      copy.textContent = frame.statusText;
      item.append(round, copy);
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
          <span class="skill-state ${skill.remainingCd === 0 ? "ready" : ""}">${skill.remainingCd === 0 ? "READY" : `CD ${skill.remainingCd}`}</span>
        </div>
        <div class="skill-card-meta">
          <span>${skill.damage} damage</span>
          <span>cooldown ${skill.cooldown}</span>
        </div>
        <div class="skill-bar">
          <div class="skill-bar-fill" style="width:${Math.max(0, Math.min(100, ratio * 100))}%"></div>
        </div>
      `;
      els.skillList.appendChild(card);
    });
  }

  function updateReadout(frame) {
    if (!frame) {
      els.battleReadout.textContent = "等待战斗数据";
      return;
    }
    const action = frame.skillIdx === null ? "WAIT" : `S${frame.skillIdx}`;
    const suffix = frame.failed ? " / 失败" : frame.retry ? " / 重试" : frame.defeated ? " / 击破" : "";
    els.battleReadout.textContent = `B${frame.bossIndex} · Attempt ${frame.attempt} · Turn ${frame.attackRound} · ${action}${suffix}`;
  }

  function updateUi() {
    const frame = currentFrame();
    if (!frame) {
      els.runState.textContent = "待机";
      return;
    }
    els.runState.textContent = state.playing ? "播放中" : "已暂停";
    els.metricBoss.textContent = `${frame.bossIndex} / ${frame.bossTotal}`;
    els.metricAttempt.textContent = String(frame.attempt);
    els.metricRound.textContent = String(frame.totalRound);
    els.metricCoins.textContent = String(frame.coins);
    els.phaseLabel.textContent = phaseLabel(frame);
    els.timeline.value = String(state.frameIndex);
    els.playBtn.textContent = state.playing ? "Ⅱ" : "▶";
    els.detailBoss.textContent = `${frame.bossIndex} / ${frame.bossTotal}`;
    els.detailAttempt.textContent = String(frame.attempt);
    els.detailTurn.textContent = `${frame.attackRound} / ${frame.minRounds}`;
    els.detailAction.textContent = frame.skillIdx === null ? "等待" : `技能 S${frame.skillIdx}`;
    els.detailDamage.textContent = String(frame.damage);
    els.detailBossHp.textContent = frame.defeated ? "已击破" : "未知";
    updateReadout(frame);
    renderEvents();
    renderSkills(frame);
  }

  function stopPlayback() {
    state.playing = false;
    if (state.timer) {
      window.clearTimeout(state.timer);
      state.timer = null;
    }
    els.playBtn.textContent = "▶";
    if (state.frames.length) {
      els.runState.textContent = "已暂停";
    }
  }

  function setFrame(index) {
    state.frameIndex = Math.max(0, Math.min(index, state.frames.length - 1));
    if (state.frameIndex >= state.frames.length - 1) {
      stopPlayback();
      notifyBattleComplete();
    }
    updateUi();
    draw();
  }

  function scheduleTick() {
    if (!state.playing || !state.frames.length) return;
    const frame = currentFrame();
    const baseDelay = Math.max(34, 680 / state.speed);
    const frameDelay = frame ? Math.max(32, frame.durationMs / Math.max(1, state.speed * 0.36)) : baseDelay;
    state.timer = window.setTimeout(() => {
      setFrame(state.frameIndex + 1);
      scheduleTick();
    }, Math.min(baseDelay, frameDelay));
  }

  function startPlayback() {
    if (!state.frames.length || state.playing) return;
    state.playing = true;
    els.runState.textContent = "播放中";
    els.playBtn.textContent = "Ⅱ";
    scheduleTick();
  }

  function togglePlayback() {
    if (state.playing) {
      stopPlayback();
    } else {
      if (state.frameIndex >= state.frames.length - 1) {
        setFrame(0);
      }
      startPlayback();
    }
    updateUi();
  }

  function reset() {
    stopPlayback();
    setFrame(0);
  }

  function enterBattle() {
    if (!state.frames.length || document.body.classList.contains("intro-leaving")) return;
    if (els.startBattleBtn) {
      els.startBattleBtn.disabled = true;
    }
    setFrame(0);
    document.body.classList.add("intro-leaving");
    window.setTimeout(() => {
      document.body.classList.remove("intro-active", "intro-leaving");
      startPlayback();
    }, 560);
  }

  function initBattle(data, name = "maze_15_15.json") {
    stopPlayback();
    state.mapName = name;
    state.mapData = normalizeMapData(data);
    state.startingCoins = Math.max(0, Number(els.startingCoinsInput.value) || 0);
    state.frames = buildFrames(state.mapData, state.startingCoins);
    state.frameIndex = 0;

    els.battleName.textContent = name;
    els.timeline.max = String(Math.max(0, state.frames.length - 1));
    els.timeline.value = "0";
    els.mapMeta.textContent = `Boss ${state.mapData.bossHps.length} 个，技能 ${state.mapData.skills.length} 个，回合上限 ${state.mapData.minRounds}，失败扣币 ${state.mapData.coinConsumption}`;
    updateIntro(state.mapData);
    updateUi();
    draw();
  }

  function initEmbeddedBattle(payload) {
    const config = buildBattleConfigFromPayload(payload);
    state.embedMode = true;
    state.embedRequestId = payload.requestId ?? null;
    state.startingCoins = Math.max(0, Number(payload.startingCoins) || 0);
    document.body.classList.add("embed-mode");
    if (els.startingCoinsInput) {
      els.startingCoinsInput.value = String(state.startingCoins);
    }
    initBattle(config, payload.mapName || "Boss 战");
    document.body.classList.remove("intro-active", "intro-leaving");
    window.setTimeout(() => {
      if (!state.playing) {
        startPlayback();
      }
    }, 80);
  }

  async function loadDefaultMap() {
    if (window.location.protocol === "file:") {
      initBattle(cloneData(DEFAULT_MAP_DATA), "内置示例地图");
      els.mapMeta.textContent += "（本地文件模式）";
      return;
    }
    try {
      const response = await fetch(DEFAULT_MAP_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      initBattle(data);
    } catch (error) {
      console.warn("Default boss map could not be loaded; using embedded map.", error);
      initBattle(cloneData(DEFAULT_MAP_DATA), "内置示例地图");
      els.mapMeta.textContent += "（本地文件模式）";
    }
  }

  function bindEvents() {
    if (els.startBattleBtn) {
      els.startBattleBtn.disabled = true;
      els.startBattleBtn.addEventListener("click", enterBattle);
    }
    els.playBtn.addEventListener("click", togglePlayback);
    els.resetBtn.addEventListener("click", reset);
    els.prevBtn.addEventListener("click", () => {
      stopPlayback();
      setFrame(state.frameIndex - 1);
    });
    els.nextBtn.addEventListener("click", () => {
      stopPlayback();
      setFrame(state.frameIndex + 1);
    });
    els.timeline.addEventListener("input", (event) => {
      stopPlayback();
      setFrame(Number(event.target.value));
    });
    els.speedRange.addEventListener("input", (event) => {
      state.speed = Number(event.target.value);
      els.speedLabel.textContent = `${state.speed}x`;
      if (state.playing) {
        window.clearTimeout(state.timer);
        scheduleTick();
      }
    });
    els.toggleTrail.addEventListener("change", (event) => {
      state.showTrail = event.target.checked;
      draw();
    });
    els.toggleGlow.addEventListener("change", (event) => {
      state.showGlow = event.target.checked;
      draw();
    });
    els.toggleSprites.addEventListener("change", (event) => {
      state.showSprites = event.target.checked;
      draw();
    });
    els.togglePulse.addEventListener("change", (event) => {
      state.showPulse = event.target.checked;
      draw();
    });
    document.querySelectorAll(".segment").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        state.mode = button.dataset.mode;
        draw();
      });
    });
    els.rebuildBtn.addEventListener("click", () => {
      if (!state.mapData) return;
      initBattle(state.mapData.raw, state.mapName);
    });
    els.startingCoinsInput.addEventListener("change", () => {
      const value = Math.max(0, Number(els.startingCoinsInput.value) || 0);
      els.startingCoinsInput.value = String(value);
    });
    els.loadDefaultBtn.addEventListener("click", loadDefaultMap);
    els.fileInput.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        const data = JSON.parse(await file.text());
        initBattle(data, file.name);
      } catch (error) {
        els.mapMeta.textContent = `导入失败：${error.message}`;
      } finally {
        els.fileInput.value = "";
      }
    });
    window.addEventListener("resize", draw);
  }

  loadAssets();
  bindEvents();

  const embeddedBattle = parseBattleQuery();
  if (embeddedBattle) {
    initEmbeddedBattle(embeddedBattle);
  } else {
    loadDefaultMap();
    window.setTimeout(() => {
      if (!document.body.classList.contains("intro-active")) {
        updateUi();
        draw();
      }
    }, 0);
  }
})();
