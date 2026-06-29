const { createApp } = Vue;

function storageRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (err) {
    // Nothing to clean up when storage is unavailable.
  }
}

function cellRand(r, c, seed = 17) {
  let n = (r + 1) * 374761393 + (c + 1) * 668265263 + seed * 1442695041;
  n = (n ^ (n >> 13)) * 1274126177;
  return ((n ^ (n >> 16)) >>> 0) / 4294967295;
}

function calcLayout(canvas, rows, cols) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const pad = 18;
  const tile = Math.max(12, Math.floor(Math.min((rect.width - pad * 2) / cols, (rect.height - pad * 2) / rows)));
  return {
    ctx,
    width: rect.width,
    height: rect.height,
    tile,
    originX: (rect.width - tile * cols) / 2,
    originY: (rect.height - tile * rows) / 2,
  };
}

function drawCell(ctx, x, y, tile, cell, r, c) {
  const jitter = cellRand(r, c);
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha = 1;
  if (cell === null || cell === undefined) {
    ctx.fillStyle = "#030308";
    ctx.fillRect(0, 0, tile, tile);
    ctx.fillStyle = `rgba(0, 229, 255, ${0.05 + jitter * 0.06})`;
    ctx.beginPath();
    ctx.arc(tile * (0.25 + jitter * 0.55), tile * (0.25 + cellRand(r, c, 8) * 0.55), tile * 0.05, 0, Math.PI * 2);
    ctx.fill();
  } else if (cell === "#") {
    const grad = ctx.createLinearGradient(0, 0, tile, tile);
    grad.addColorStop(0, "#2b2841");
    grad.addColorStop(1, "#182f3a");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, tile, tile);
  } else {
    ctx.fillStyle = "rgba(30, 23, 42, 0.82)";
    ctx.fillRect(0, 0, tile, tile);
    ctx.fillStyle = `rgba(255,255,255,${0.025 + jitter * 0.035})`;
    ctx.fillRect(tile * 0.12, tile * 0.12, tile * 0.76, tile * 0.76);
  }
  ctx.strokeStyle = "rgba(255,255,255,0.06)";
  ctx.strokeRect(0.5, 0.5, tile - 1, tile - 1);

  const center = tile / 2;
  if (cell === "C" || cell === "G") {
    ctx.fillStyle = "#ffaa00";
    ctx.shadowColor = "#ffaa00";
    ctx.shadowBlur = 14;
    ctx.beginPath();
    ctx.arc(center, center, tile * 0.22, 0, Math.PI * 2);
    ctx.fill();
  } else if (cell === "T") {
    ctx.fillStyle = "#ff7a1a";
    ctx.shadowColor = "#ff3355";
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.moveTo(center, tile * 0.22);
    ctx.lineTo(tile * 0.78, tile * 0.74);
    ctx.lineTo(tile * 0.22, tile * 0.74);
    ctx.closePath();
    ctx.fill();
  } else if (cell === "B") {
    ctx.fillStyle = "#ff3355";
    ctx.shadowColor = "#ff3355";
    ctx.shadowBlur = 16;
    ctx.fillRect(tile * 0.28, tile * 0.28, tile * 0.44, tile * 0.44);
  } else if (cell === "E") {
    ctx.strokeStyle = "#ffaa00";
    ctx.lineWidth = Math.max(2, tile * 0.08);
    ctx.shadowColor = "#ffaa00";
    ctx.shadowBlur = 14;
    ctx.strokeRect(tile * 0.24, tile * 0.24, tile * 0.52, tile * 0.52);
  } else if (cell === "S") {
    ctx.fillStyle = "#00e5ff";
    ctx.globalAlpha = 0.7;
    ctx.fillRect(tile * 0.28, tile * 0.28, tile * 0.44, tile * 0.44);
  }
  ctx.restore();
}

function renderMaze(canvas, state, path = []) {
  if (!canvas || !state || !state.fog_map) {
    return;
  }
  const rows = state.fog_map.length;
  const cols = state.fog_map[0].length;
  const { ctx, width, height, tile, originX, originY } = calcLayout(canvas, rows, cols);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(5,4,10,0.7)";
  ctx.fillRect(0, 0, width, height);

  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      drawCell(ctx, originX + c * tile, originY + r * tile, tile, state.fog_map[r][c], r, c);
    }
  }

  if (path.length > 1) {
    ctx.save();
    ctx.strokeStyle = "rgba(242, 165, 65, 0.88)";
    ctx.lineWidth = Math.max(3, tile * 0.16);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.shadowColor = "rgba(255, 170, 0, 0.35)";
    ctx.shadowBlur = 14;
    ctx.beginPath();
    for (let idx = 0; idx < path.length; idx += 1) {
      const [r, c] = path[idx];
      const x = originX + c * tile + tile / 2;
      const y = originY + r * tile + tile / 2;
      if (idx === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.restore();
  }

  const [pr, pc] = state.pos;
  const px = originX + pc * tile + tile / 2;
  const py = originY + pr * tile + tile / 2;
  ctx.save();
  ctx.shadowColor = "#00e5ff";
  ctx.shadowBlur = 24;
  ctx.fillStyle = "#f4f7fb";
  ctx.beginPath();
  ctx.arc(px, py, tile * 0.28, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ff2d95";
  ctx.beginPath();
  ctx.arc(px, py, tile * 0.12, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

createApp({
  data() {
    return {
      loggedIn: false,
      maps: [],
      selectedMap: "sample.json",
      selectedMapData: null,
      currentMap: "",
      selectedAgent: "fog_original",
      bossSourceMode: "map",
      manualBossHealthDraft: null,
      manualBossHealths: [],
      manualBossInputClosed: false,
      manualBossStreamStatus: "",
      sessionId: "",
      state: null,
      finalState: null,
      frames: [],
      playIndex: 0,
      eventLog: [],
      busy: false,
      playing: false,
      speed: 280,
      timer: null,
      statusText: "ready",
      bossOverlay: false,
      bossDetail: null,
      lastBossEventCountShown: 0,
      bossVideoSrc: "",
      bossVideoTitle: "BOSS ENCOUNTER",
      bossVideoTimer: null,
      bossVideoQueue: [],
      activeBgm: "",
    };
  },
  computed: {
    scoreText() {
      if (!this.state || !this.state.step) {
        return "0.00";
      }
      const value = this.state.value ?? this.state.coins ?? 0;
      return (value / Math.max(this.state.step, 1)).toFixed(2);
    },
    mapHasBossArray() {
      if (!this.selectedMapData) {
        return false;
      }
      if (this.selectedMapData.boss_healths_available === true || this.selectedMapData.boss_healths_hidden === true) {
        return true;
      }
      if (this.selectedMapData.boss_healths_available === false) {
        return false;
      }
      return Array.isArray(this.selectedMapData?.B) && this.selectedMapData.B.length > 0;
    },
    knownBossHealths() {
      return this.state?.known_boss_healths || [];
    },
    defeatedBossHealths() {
      return this.knownBossHealths.filter((boss) => boss.status === "defeated");
    },
    futureKnownBossHealths() {
      return this.knownBossHealths.filter((boss) => boss.status === "known");
    },
    currentKnownBoss() {
      return this.state?.current_boss_health || this.knownBossHealths.find((boss) => boss.status === "current") || null;
    },
    playbackText() {
      if (!this.frames.length) {
        return "0 / 0";
      }
      return `${this.playIndex + 1} / ${this.frames.length}`;
    },
    travelledPath() {
      return this.frames.slice(0, this.playIndex + 1).map((frame) => frame.pos).filter(Boolean);
    },
    bossFlow() {
      const events = this.finalState?.boss_events || this.state?.boss_events || [];
      return events.map((event, idx) => {
        const reviveCost = Number(event.revive_cost ?? event.revive?.cost ?? event.cost ?? 0);
        return {
          ...event,
          flowIndex: idx + 1,
          reviveCost,
          valueBefore: event.value_before ?? event.coins_before ?? 0,
          valueAfter: event.value_after ?? event.coins_after ?? 0,
          resultText: event.result === "win" ? "胜利" : "失败",
          planningText: event.planning_mode === "known_sequence" ? "全 Boss 序列规划" : "当前 Boss 规划",
        };
      });
    },
  },
  mounted() {
    this.loadMaps();
    window.addEventListener("resize", this.render);
    if (!this.loggedIn) {
      this.$nextTick(this.startIntroVideo);
    }
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.render);
    this.clearTimer();
    this.stopBgm();
  },
  methods: {
    startIntroVideo() {
      const video = this.$refs.introVideo;
      if (!video) {
        return;
      }
      video.muted = false;
      video.volume = 1;
      video.play().catch(() => {
        video.muted = true;
        video.play().catch(() => {});
      });
    },
    enableIntroAudio() {
      const video = this.$refs.introVideo;
      if (!video) {
        return;
      }
      video.muted = false;
      video.volume = 1;
      video.play().catch(() => {});
    },
    login() {
      this.enableIntroAudio();
      this.loggedIn = true;
      this.$nextTick(this.render);
    },
    async logout() {
      storageRemove("ai_maze_started");
      storageRemove("ai_maze_logged_in");
      this.loggedIn = false;
      this.stopBgm();
      await this.resetSession();
    },
    audioRef(name) {
      return this.$refs[name] || null;
    },
    playAudio(audio, volume = 0.6) {
      if (!audio) {
        return;
      }
      audio.volume = volume;
      audio.loop = true;
      audio.play().catch(() => {});
    },
    pauseAudio(audio) {
      if (!audio) {
        return;
      }
      audio.pause();
    },
    playMazeBgm() {
      const mazeAudio = this.audioRef("mazeBgm");
      const bossAudio = this.audioRef("bossBgm");
      this.pauseAudio(bossAudio);
      this.playAudio(mazeAudio, 0.52);
      this.activeBgm = "maze";
    },
    playBossBgm() {
      const mazeAudio = this.audioRef("mazeBgm");
      const bossAudio = this.audioRef("bossBgm");
      this.pauseAudio(mazeAudio);
      this.playAudio(bossAudio, 0.68);
      this.activeBgm = "boss";
    },
    stopBgm() {
      this.pauseAudio(this.audioRef("mazeBgm"));
      this.pauseAudio(this.audioRef("bossBgm"));
      this.activeBgm = "";
    },
    particleStyle(n) {
      const left = (n * 37) % 100;
      const delay = -((n * 0.73) % 8);
      const duration = 9 + (n % 11);
      const size = 1 + (n % 4);
      const colors = ["var(--magenta)", "var(--cyan)", "var(--gold)"];
      return {
        left: `${left}%`,
        width: `${size}px`,
        height: `${size}px`,
        color: colors[n % colors.length],
        animationDelay: `${delay}s`,
        animationDuration: `${duration}s`,
      };
    },
    async loadMaps() {
      try {
        const data = await mazeApi.getMaps();
        this.maps = data.maps || [];
        if (this.maps.length && !this.maps.includes(this.selectedMap)) {
          this.selectedMap = this.maps[0];
        }
        await this.loadMapInfo();
      } catch (err) {
        this.statusText = err.message;
      }
    },
    async loadMapInfo() {
      if (!this.selectedMap) {
        this.selectedMapData = null;
        return;
      }
      try {
        this.selectedMapData = await mazeApi.getMap(this.selectedMap);
        this.initBossSourceMode();
        this.statusText = this.mapHasBossArray ? "ready: 自动读取可用" : "ready: 需要手动输入 Boss";
      } catch (err) {
        this.selectedMapData = null;
        this.initBossSourceMode();
        this.statusText = err.message;
      }
    },
    async handleMapChange() {
      this.selectedMapData = null;
      this.statusText = "loading map";
      await this.resetSession();
      await this.loadMapInfo();
    },
    async uploadSelectedMap(evt) {
      const file = evt.target.files[0];
      if (!file) {
        return;
      }
      this.busy = true;
      try {
        const data = await mazeApi.uploadMap(file);
        await this.loadMaps();
        this.selectedMap = data.name;
        await this.resetSession();
        await this.loadMapInfo();
        this.statusText = "uploaded";
      } catch (err) {
        this.statusText = err.message;
      } finally {
        this.busy = false;
        evt.target.value = "";
      }
    },
    async enterGame() {
      if (this.bossSourceMode === "manual") {
        await this.runManualBossSequence();
        return;
      }
      this.busy = true;
      this.clearTimer();
      this.playMazeBgm();
      try {
        if (this.sessionId) {
          await mazeApi.deleteSim(this.sessionId);
        }
        const data = await mazeApi.startRunSim(
          this.selectedMap,
          this.selectedAgent,
          undefined,
          this.bossSetupPayload()
        );
        this.sessionId = data.session_id;
        this.currentMap = this.selectedMap;
        this.eventLog = [];
        this.loadPlayback(data.state);
        if (this.frames.length > 1) {
          this.playing = true;
          this.statusText = "playing";
          this.scheduleStep();
        } else {
          this.statusText = data.state?.result || "done";
        }
      } catch (err) {
        this.statusText = err.message;
      } finally {
        this.busy = false;
      }
    },
    async stepOnce() {
      if (!this.frames.length || this.busy) {
        return;
      }
      this.showFrame(Math.min(this.playIndex + 1, this.frames.length - 1));
    },
    async runAll() {
      if (!this.frames.length) {
        return;
      }
      this.clearTimer();
      this.playing = false;
      this.showFrame(this.frames.length - 1);
    },
    async resetSession() {
      this.clearTimer();
      this.clearBossVideoTimer();
      this.playing = false;
      if (this.loggedIn) {
        this.playMazeBgm();
      }
      if (this.sessionId) {
        try {
          await mazeApi.deleteSim(this.sessionId);
        } catch (err) {
          this.statusText = err.message;
        }
      }
      this.sessionId = "";
      this.state = null;
      this.finalState = null;
      this.frames = [];
      this.playIndex = 0;
      this.eventLog = [];
      this.bossDetail = null;
      this.lastBossEventCountShown = 0;
      this.bossOverlay = false;
      this.bossVideoSrc = "";
      this.bossVideoQueue = [];
      this.statusText = "ready";
      this.render();
    },
    togglePlay() {
      this.playing = !this.playing;
      if (this.playing) {
        this.playMazeBgm();
        this.scheduleStep();
      } else {
        this.clearTimer();
      }
    },
    scheduleStep() {
      this.clearTimer();
      if (!this.playing || !this.frames.length || this.playIndex >= this.frames.length - 1) {
        this.playing = false;
        return;
      }
      this.timer = setTimeout(async () => {
        this.showFrame(this.playIndex + 1);
        this.scheduleStep();
      }, this.speed);
    },
    clearTimer() {
      if (this.timer) {
        clearTimeout(this.timer);
        this.timer = null;
      }
    },
    clearBossVideoTimer() {
      if (this.bossVideoTimer) {
        clearTimeout(this.bossVideoTimer);
        this.bossVideoTimer = null;
      }
    },
    applyState(state) {
      this.state = state;
      if (state?.event) {
        this.eventLog.unshift({ step: state.step, message: this.formatEventMessage(state.event) });
        this.eventLog = this.eventLog.slice(0, 40);
      }
      const bossEvents = Array.isArray(state?.boss_events) ? state.boss_events : [];
      const newBossEvents = bossEvents.slice(this.lastBossEventCountShown);
      if (newBossEvents.length) {
        this.lastBossEventCountShown = bossEvents.length;
        this.showBossSequence(newBossEvents);
      }
      this.$nextTick(this.render);
    },
    loadPlayback(finalState) {
      this.finalState = finalState;
      const history = Array.isArray(finalState?.history) ? finalState.history : [];
      this.frames = history.length ? history : [finalState];
      this.playIndex = 0;
      this.eventLog = [];
      this.bossDetail = null;
      this.lastBossEventCountShown = 0;
      this.bossVideoQueue = [];
      this.showFrame(0);
    },
    extendPlayback(finalState) {
      const history = Array.isArray(finalState?.history) ? finalState.history : [];
      const nextFrames = history.length ? history : [finalState];
      const previousLength = this.frames.length;
      this.finalState = finalState;
      this.frames = nextFrames;
      if (previousLength <= 0) {
        this.playIndex = 0;
        this.showFrame(0);
        return 0;
      }
      this.playIndex = Math.max(0, Math.min(previousLength - 1, this.frames.length - 1));
      this.state = this.frames[this.playIndex] || finalState;
      this.$nextTick(this.render);
      return Math.max(0, Math.min(previousLength, this.frames.length - 1));
    },
    showFrame(index) {
      if (!this.frames.length) {
        return;
      }
      const nextIndex = Math.max(0, Math.min(index, this.frames.length - 1));
      this.playIndex = nextIndex;
      this.applyState(this.frames[nextIndex]);
      if (nextIndex >= this.frames.length - 1) {
        this.playing = false;
        this.clearTimer();
        this.statusText = this.finalState?.result || this.state?.result || "done";
      } else {
        this.statusText = "playing";
      }
    },
    showBossSequence(events) {
      this.clearBossVideoTimer();
      this.bossVideoQueue = events.slice();
      this.playBossBgm();
      this.playNextBossVideo();
    },
    playNextBossVideo() {
      const event = this.bossVideoQueue.shift();
      if (!event) {
        this.bossOverlay = false;
        if (this.loggedIn) {
          this.playMazeBgm();
        }
        return;
      }
      this.showBoss(event);
    },
    showBoss(event) {
      this.bossOverlay = true;
      this.bossDetail = event;
      const videoIndex = ((Number(event.encounter_order || 1) - 1) % 7) + 1;
      this.clearBossVideoTimer();
      this.bossVideoSrc = `/resources/${videoIndex}.mp4`;
      this.bossVideoTitle = `Boss #${event.encounter_order || 1} · 第 ${event.attempt || 1} 次 · ${event.result === "win" ? "胜利" : "失败"}`;
      this.$nextTick(() => {
        this.playBossVideo(event);
      });
    },
    playBossVideo(event) {
      const video = this.$refs.bossVideo;
      if (!video) {
        return;
      }
      const rounds = event.rounds?.length || event.rounds_used || 1;
      const targetMs = Math.max(1800, Math.min(9000, 800 + rounds * Math.max(this.speed, 80) * 1.8));
      const close = () => {
        this.playNextBossVideo();
      };
      const configure = () => {
        const durationMs = Number.isFinite(video.duration) && video.duration > 0 ? video.duration * 1000 : targetMs;
        video.playbackRate = Math.min(4, Math.max(0.25, durationMs / targetMs));
        video.currentTime = 0;
        video.play().catch(() => {});
      };
      video.onloadedmetadata = configure;
      video.onended = close;
      if (video.readyState >= 1) {
        configure();
      }
      this.bossVideoTimer = window.setTimeout(close, targetMs + 220);
    },
    formatEventMessage(event) {
      if (event.type === "boss") {
        const before = event.value_before ?? event.coins_before;
        const after = event.value_after ?? event.coins_after;
        return `Boss #${event.encounter_order} 第 ${event.attempt || 1} 次: ${event.message}, ${event.total_damage}/${event.initial_health} damage, 价值 ${before}→${after}`;
      }
      return event.message || event.type;
    },
    formatCooldowns(values) {
      if (!Array.isArray(values) || !values.length) {
        return "-";
      }
      return values.map((value, idx) => `#${idx + 1}:${value}`).join(" ");
    },
    downloadOutput() {
      if (!this.finalState) return;
      const fs = this.finalState;
      const history = Array.isArray(fs.history) ? fs.history : [];
      const path = history.map(h => h.pos);
      if (!path.length && fs.pos) path.push(fs.pos);
      const deduped = [];
      for (let i = 0; i < path.length; i++) {
        if (i === 0 || path[i][0] !== deduped[deduped.length - 1][0] || path[i][1] !== deduped[deduped.length - 1][1]) {
          deduped.push([...path[i]]);
        }
      }
      const moveSteps = Math.max(0, deduped.length - 1);
      const finalCoin = fs.value ?? fs.coins ?? 0;
      const bossEvents = Array.isArray(fs.boss_events) ? fs.boss_events : [];
      const bossWon = bossEvents.length > 0 ? bossEvents.some(e => e.result === 'win') : false;
      const totalTurns = bossEvents.reduce((s, e) => s + (e.total_rounds_used ?? e.rounds_used ?? 0), 0);
      const reviveCount = bossEvents.reduce((s, e) => s + (e.result === 'lose' ? 1 : 0), 0);
      const coinCost = bossEvents.reduce((s, e) => s + (e.revive_cost ?? e.revive?.cost ?? 0), 0);
      const skillSeqs = [];
      const skillSeqLens = [];
      for (const bf of this.bossFlow) {
        const rounds = Array.isArray(bf.rounds) ? bf.rounds : [];
        const seq = rounds.filter(r => r.action === 'attack').map(r => typeof r.skill_index === 'number' ? r.skill_index : -1);
        if (seq.length) { skillSeqs.push(seq); skillSeqLens.push(seq.length); }
      }
      const output = {
        success: fs.result === 'win',
        path: deduped, path_length: deduped.length, move_steps: moveSteps,
        final_coin: finalCoin,
        coin_step_ratio: (fs.result === 'win' && moveSteps > 0) ? finalCoin / moveSteps : 0,
        boss_success: bossWon, boss_total_turns: totalTurns,
        boss_revive_count: reviveCount, boss_coin_cost: coinCost,
        boss_skill_sequence_lengths: skillSeqLens, boss_skill_sequences: skillSeqs
      };
      const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `output_result_${this.selectedAgent}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    initBossSourceMode() {
      if (this.mapHasBossArray) {
        this.bossSourceMode = "map";
      } else {
        this.bossSourceMode = "manual";
      }
      this.resetManualBossStream();
    },
    setBossSourceMode(mode) {
      if (mode === "map" && !this.mapHasBossArray) {
        this.statusText = "当前地图没有 Boss 血量数组";
        return;
      }
      this.bossSourceMode = mode;
      this.resetManualBossStream();
    },
    resetManualBossStream() {
      this.manualBossHealthDraft = null;
      this.manualBossHealths = [];
      this.manualBossInputClosed = false;
      this.manualBossStreamStatus = "";
    },
    readManualBossDraft() {
      const health = Number(this.manualBossHealthDraft);
      if (!Number.isFinite(health) || (health <= 0 && health !== -1)) {
        throw new Error("请输入当前 Boss 血量，或输入 -1 表示结束当前 Boss 输入");
      }
      return Math.floor(health);
    },
    hasManualBossDraft() {
      return this.manualBossHealthDraft !== null && this.manualBossHealthDraft !== "" && this.manualBossHealthDraft !== undefined;
    },
    async fightManualBoss() {
      if (this.bossSourceMode !== "manual" || this.busy) {
        return;
      }
      await this.submitManualBossInput();
    },
    async finishManualBossInput() {
      if (this.bossSourceMode !== "manual" || this.busy) {
        return;
      }
      await this.submitManualBossInput(-1);
    },
    async runManualBossSequence() {
      if (!this.sessionId) {
        await this.startManualExploration();
        return;
      }
      if (this.state?.awaiting_boss_input) {
        this.manualBossStreamStatus = "已到达 Boss 位置，请在左侧输入当前 Boss 血量";
        this.statusText = "waiting boss input";
        return;
      }
      await this.continueManualExploration();
    },
    async startManualExploration() {
      this.busy = true;
      this.clearTimer();
      this.playMazeBgm();
      try {
        if (this.sessionId) {
          await mazeApi.deleteSim(this.sessionId);
        }
        const data = await mazeApi.startRunSim(
          this.selectedMap,
          this.selectedAgent,
          undefined,
          { boss_source: "manual" }
        );
        this.sessionId = data.session_id;
        this.currentMap = this.selectedMap;
        this.eventLog = [];
        this.loadPlayback(data.state);
        this.manualBossInputClosed = false;
        this.manualBossStreamStatus = data.state?.awaiting_boss_input
          ? "AI 已到达 Boss 位置，请输入当前 Boss 血量"
          : data.state?.result || "探索完成";
        if (this.frames.length > 1) {
          this.playing = true;
          this.statusText = "playing";
          this.scheduleStep();
        } else {
          this.statusText = data.state?.result || "done";
        }
      } catch (err) {
        this.statusText = err.message;
        this.manualBossStreamStatus = err.message;
      } finally {
        this.busy = false;
      }
    },
    async submitManualBossInput(value) {
      if (!this.sessionId) {
        await this.startManualExploration();
        return;
      }
      const health = value ?? this.readManualBossDraft();
      if (health !== -1) {
        this.manualBossHealths.push(health);
      }
      this.manualBossHealthDraft = null;
      this.busy = true;
      this.clearTimer();
      try {
        const data = await mazeApi.submitBossHealth(this.sessionId, health, health === -1);
        this.currentMap = this.selectedMap;
        const nextIndex = this.extendPlayback(data.state);
        if (Number.isInteger(nextIndex)) {
          this.playIndex = Math.max(0, nextIndex - 1);
        }
        if (health === -1) {
          this.manualBossInputClosed = true;
          this.manualBossStreamStatus = "当前 Boss 输入结束，AI 将继续探索迷宫";
          await this.continueManualExploration();
          return;
        }
        const latestBossEvent = data.state?.boss_events?.[data.state.boss_events.length - 1];
        if (latestBossEvent?.manual_input_required_after_revive) {
          this.manualBossStreamStatus = "当前 Boss 未打过，已扣除复活价值，请重新输入当前 Boss 血量，或输入 -1 结束";
        } else {
          this.manualBossStreamStatus = data.state?.awaiting_boss_input
            ? "当前 Boss 已处理，请继续输入下一个 Boss 血量，或输入 -1 结束"
            : data.state?.result || "Boss 已处理";
        }
        this.playing = true;
        this.statusText = "playing";
        this.scheduleStep();
      } catch (err) {
        this.statusText = err.message;
        this.manualBossStreamStatus = err.message;
      } finally {
        this.busy = false;
      }
    },
    async continueManualExploration() {
      if (!this.sessionId) {
        return;
      }
      const data = await mazeApi.runSim(this.sessionId);
      const nextIndex = this.extendPlayback(data.state);
      if (Number.isInteger(nextIndex)) {
        this.playIndex = Math.max(0, nextIndex - 1);
      }
      this.manualBossInputClosed = false;
      this.manualBossStreamStatus = data.state?.awaiting_boss_input
        ? "AI 已到达下一个 Boss 位置，请输入当前 Boss 血量"
        : data.state?.result || "探索完成";
      this.playing = true;
      this.statusText = "playing";
      this.scheduleStep();
    },
    bossSetupPayload({ revealAll = false } = {}) {
      if (this.bossSourceMode === "map") {
        if (!this.mapHasBossArray) {
          throw new Error("当前地图没有 Boss 血量数组，请选择手动输入");
        }
        return { boss_source: "map" };
      }
      return { boss_source: "manual", boss_healths_revealed: revealAll };
    },
    manualBossPayload({ revealAll = false } = {}) {
      return this.bossSetupPayload({ revealAll });
    },
    countBossCells(maze) {
      return maze.reduce((total, row) => total + row.filter((cell) => cell === "B").length, 0);
    },
    render() {
      renderMaze(this.$refs.mazeCanvas, this.state, this.travelledPath);
    },
  },
}).mount("#app");
