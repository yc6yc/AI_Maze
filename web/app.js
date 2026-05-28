(() => {
  const DEFAULT_MAP_CANDIDATES = [
    "../map地图/maze_15_15.json",
    "../map/maze_15_15.json",
    "../maze_15_15.json",
  ];
  const ACTIVE_MAP_CACHE_KEY = "ai_maze_active_map";
  const DEFAULT_MAP_DATA = {
    maze: [
      ["#","#","#","#","#","#","#","#","#","#","#","S","#","#","#"],
      ["#"," ","G","T","G","#"," "," "," "," "," "," "," "," ","#"],
      ["#","#","#","G","#","#","#"," ","#","#","#","#","#","#","#"],
      ["#"," ","T"," "," "," ","#"," "," "," ","#"," ","#","G","#"],
      ["#","#","#"," ","#"," ","#","#","#"," ","#"," ","#","G","#"],
      ["#"," ","G"," ","#"," ","#","G"," "," "," "," ","G","T","#"],
      ["#","#","#"," ","#"," ","#","#","#","#","#","T","#","T","#"],
      ["#"," ","#"," ","#"," ","#"," "," "," "," "," ","#"," ","#"],
      ["#","T","#"," ","#"," ","#","#","#"," ","#","#","#"," ","#"],
      ["#"," "," "," ","#"," "," "," "," "," "," "," ","#"," ","#"],
      ["#"," ","#","#","#","#","#","#","#","#","#","#","#","#","#"],
      ["#"," "," "," ","#","G","#"," ","T"," ","#","G","T"," ","#"],
      ["#","#","#"," ","#","T","#"," ","#","#","#","#","#"," ","#"],
      ["#"," "," "," "," "," "," "," ","B"," "," "," ","T","G","#"],
      ["#","#","#","#","#","#","#","#","#","E","#","#","#","#","#"],
    ],
    B: [11, 13, 9, 15],
    PlayerSkills: [[8, 4], [2, 0], [4, 2], [6, 3]],
    minRouds: 20,
    CoinConsumption: 5,
  };
  const VIEW_RADIUS = 1;
  const COIN_VALUE = 50;
  const TRAP_DAMAGE = 30;
  const TRAP_HIDE_DELAY_MS = 1000;

  const TILE = {
    "#": {
      label: "墙体",
      color: "#2a2f37",
      stroke: "#15191f",
      weight: "不可通行",
      asset: "../viz/assets/wall.png",
    },
    " ": {
      label: "通路",
      color: "#edf2f7",
      stroke: "#cbd5e1",
      weight: "1",
      asset: "../viz/assets/floor.png",
    },
    S: {
      label: "起点",
      color: "#2f9e44",
      stroke: "#1d6f31",
      weight: "1",
      asset: "../viz/assets/floor.png",
    },
    E: {
      label: "出口",
      color: "#6d5dfc",
      stroke: "#3f35b3",
      weight: "目标",
      asset: "../viz/assets/exit.png",
    },
    B: {
      label: "Boss",
      color: "#e4572e",
      stroke: "#a7341b",
      weight: "战斗",
      asset: "../viz/assets/boss.png",
    },
    T: {
      label: "陷阱",
      color: "#f2a541",
      stroke: "#a85f00",
      weight: `+${TRAP_DAMAGE}`,
      asset: "../viz/assets/trap.png",
    },
    C: {
      label: "金币",
      color: "#f7d046",
      stroke: "#a87700",
      weight: `+${COIN_VALUE}`,
      asset: "../viz/assets/coin.png",
    },
    G: {
      label: "金币",
      color: "#f7d046",
      stroke: "#a87700",
      weight: `+${COIN_VALUE}`,
      asset: "../viz/assets/coin.png",
    },
    L: {
      label: "机关",
      color: "#9b5de5",
      stroke: "#6730a8",
      weight: "1",
      asset: "../viz/assets/floor.png",
    },
  };

  const OBJECT_ASSETS = {
    player: "../viz/assets/player.png",
    coin: "../viz/assets/coin.png",
    trap: "../viz/assets/trap.png",
    boss: "../viz/assets/boss.png",
    exit: "../viz/assets/exit.png",
    floor: "../viz/assets/floor.png",
    wall: "../viz/assets/wall.png",
  };
  const EFFECT_SHEETS = {
    boss_enter: "../viz/assets/effects/boss_enter_effect_sheet.png",
    boss_win: "../viz/assets/effects/boss_win_effect_sheet.png",
    boss_lose: "../viz/assets/effects/boss_lose_effect_sheet.png",
    portal_enter: "../viz/assets/effects/portal_enter_effect_sheet.png",
  };

  const els = {
    canvas: document.getElementById("mazeCanvas"),
    emptyMapPrompt: document.getElementById("emptyMapPrompt"),
    emptyImportBtn: document.getElementById("emptyImportBtn"),
    introScreen: document.getElementById("introScreen"),
    startGameBtn: document.getElementById("startGameBtn"),
    introImportBtn: document.getElementById("introImportBtn"),
    introSize: document.getElementById("introSize"),
    introRoute: document.getElementById("introRoute"),
    introBoss: document.getElementById("introBoss"),
    introMiniMap: document.getElementById("introMiniMap"),
    introMeta: document.getElementById("introMeta"),
    mapName: document.getElementById("mapName"),
    runState: document.getElementById("runState"),
    metricRound: document.getElementById("metricRound"),
    metricCoins: document.getElementById("metricCoins"),
    metricExplored: document.getElementById("metricExplored"),
    metricRoute: document.getElementById("metricRoute"),
    phaseLabel: document.getElementById("phaseLabel"),
    cellReadout: document.getElementById("cellReadout"),
    timeline: document.getElementById("timeline"),
    speedRange: document.getElementById("speedRange"),
    speedLabel: document.getElementById("speedLabel"),
    resetBtn: document.getElementById("resetBtn"),
    prevBtn: document.getElementById("prevBtn"),
    playBtn: document.getElementById("playBtn"),
    nextBtn: document.getElementById("nextBtn"),
    loadDefaultBtn: document.getElementById("loadDefaultBtn"),
    fileInput: document.getElementById("fileInput"),
    toggleFog: document.getElementById("toggleFog"),
    togglePath: document.getElementById("togglePath"),
    toggleHeat: document.getElementById("toggleHeat"),
    toggleSprites: document.getElementById("toggleSprites"),
    mapMeta: document.getElementById("mapMeta"),
    tileCoord: document.getElementById("tileCoord"),
    tileType: document.getElementById("tileType"),
    tileWeight: document.getElementById("tileWeight"),
    eventList: document.getElementById("eventList"),
    legendGrid: document.getElementById("legendGrid"),
    bossAlert: document.getElementById("bossAlert"),
    bossAlertTitle: document.getElementById("bossAlertTitle"),
    bossAlertMeta: document.getElementById("bossAlertMeta"),
    bossWinAlert: document.getElementById("bossWinAlert"),
    bossWinMeta: document.getElementById("bossWinMeta"),
    bossOverlay: document.getElementById("bossOverlay"),
    bossOverlayTitle: document.getElementById("bossOverlayTitle"),
    bossOverlayFrame: document.getElementById("bossOverlayFrame"),
    closeBossOverlayBtn: document.getElementById("closeBossOverlayBtn"),
  };

  const ctx = els.canvas.getContext("2d");

  const state = {
    data: null,
    grid: [],
    frames: [],
    route: [],
    frameIndex: 0,
    speed: 5,
    timer: null,
    playing: false,
    mode: "live",
    hovered: null,
    selected: null,
    showFog: true,
    showPath: true,
    showHeat: false,
    showSprites: true,
    assets: {},
    bossBattleActive: false,
    bossBattlePendingFrame: null,
    bossBattleQueue: [],
    bossBattleRequestId: 0,
    bossAutoResume: false,
    bossFrameLoaded: false,
    bossFrameReady: false,
    pendingBossPayload: null,
    pendingBossOutcome: null,
    bossAlertTimer: null,
    bossOverlayCloseTimer: null,
    bossWinAlertTimer: null,
    effectSheets: {},
    activeEffects: [],
    effectRafId: null,
    lastEffectFrameIndex: null,
    hiddenTraps: new Set(),
    trapHideTimers: new Map(),
    layout: {
      dpr: 1,
      width: 0,
      height: 0,
      tile: 0,
      originX: 0,
      originY: 0,
    },
  };

  function keyOf(pos) {
    return `${pos.r},${pos.c}`;
  }

  function parseKey(key) {
    const [r, c] = key.split(",").map(Number);
    return { r, c };
  }

  function cloneGrid(grid) {
    return grid.map((row) => row.slice());
  }

  function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
  }

  function clearTrapHideState() {
    state.trapHideTimers.forEach((timerId) => {
      window.clearTimeout(timerId);
    });
    state.trapHideTimers.clear();
    state.hiddenTraps.clear();
  }

  function clearEffects() {
    state.activeEffects = [];
    if (state.effectRafId) {
      window.cancelAnimationFrame(state.effectRafId);
      state.effectRafId = null;
    }
    state.lastEffectFrameIndex = null;
    state.pendingBossOutcome = null;
  }

  function clearBossAlert() {
    if (state.bossAlertTimer) {
      window.clearTimeout(state.bossAlertTimer);
      state.bossAlertTimer = null;
    }
    els.bossAlert.classList.remove("is-visible");
    els.bossAlert.hidden = true;
    els.bossAlert.setAttribute("aria-hidden", "true");
  }

  function clearBossOverlayCloseTimer() {
    if (!state.bossOverlayCloseTimer) return;
    window.clearTimeout(state.bossOverlayCloseTimer);
    state.bossOverlayCloseTimer = null;
  }

  function clearBossWinAlert() {
    if (state.bossWinAlertTimer) {
      window.clearTimeout(state.bossWinAlertTimer);
      state.bossWinAlertTimer = null;
    }
    els.bossWinAlert.classList.remove("is-visible");
    els.bossWinAlert.hidden = true;
    els.bossWinAlert.setAttribute("aria-hidden", "true");
  }

  function scheduleTrapHide(frame) {
    if (!frame || frame.round <= 0 || frame.sourceCell !== "T") return;
    const trapKey = keyOf(frame.pos);
    if (state.hiddenTraps.has(trapKey) || state.trapHideTimers.has(trapKey)) return;
    const timerId = window.setTimeout(() => {
      state.hiddenTraps.add(trapKey);
      state.trapHideTimers.delete(trapKey);
      draw();
      updateUi();
    }, TRAP_HIDE_DELAY_MS);
    state.trapHideTimers.set(trapKey, timerId);
  }

  function inBounds(grid, r, c) {
    return r >= 0 && c >= 0 && r < grid.length && c < grid[0].length;
  }

  function isWalkable(cell) {
    return cell !== "#";
  }

  function neighbors(grid, pos) {
    return [
      { r: pos.r - 1, c: pos.c },
      { r: pos.r + 1, c: pos.c },
      { r: pos.r, c: pos.c - 1 },
      { r: pos.r, c: pos.c + 1 },
    ].filter((next) => inBounds(grid, next.r, next.c) && isWalkable(grid[next.r][next.c]));
  }

  function findCells(grid, cells) {
    const set = new Set(cells);
    const result = [];
    for (let r = 0; r < grid.length; r += 1) {
      for (let c = 0; c < grid[r].length; c += 1) {
        if (set.has(grid[r][c])) {
          result.push({ r, c, cell: grid[r][c] });
        }
      }
    }
    return result;
  }

  function heuristic(a, b) {
    return Math.abs(a.r - b.r) + Math.abs(a.c - b.c);
  }

  function traversalCost(cell, options = {}) {
    if (cell === "#") return Infinity;
    if (cell === "T") return options.avoidTraps ? 18 : 4;
    if (cell === "B") return options.avoidBoss ? 30 : 3;
    return 1;
  }

  function findPath(grid, start, goal, options = {}) {
    if (!start || !goal) return null;
    const open = new Set([keyOf(start)]);
    const cameFrom = new Map();
    const gScore = new Map([[keyOf(start), 0]]);
    const fScore = new Map([[keyOf(start), heuristic(start, goal)]]);

    while (open.size) {
      let currentKey = null;
      let currentScore = Infinity;
      for (const candidate of open) {
        const score = fScore.get(candidate) ?? Infinity;
        if (score < currentScore) {
          currentKey = candidate;
          currentScore = score;
        }
      }

      const current = parseKey(currentKey);
      if (current.r === goal.r && current.c === goal.c) {
        const path = [goal];
        let walkKey = currentKey;
        while (cameFrom.has(walkKey)) {
          walkKey = cameFrom.get(walkKey);
          path.unshift(parseKey(walkKey));
        }
        return path;
      }

      open.delete(currentKey);
      for (const next of neighbors(grid, current)) {
        const nextKey = keyOf(next);
        const tentative = (gScore.get(currentKey) ?? Infinity) + traversalCost(grid[next.r][next.c], options);
        if (tentative < (gScore.get(nextKey) ?? Infinity)) {
          cameFrom.set(nextKey, currentKey);
          gScore.set(nextKey, tentative);
          fScore.set(nextKey, tentative + heuristic(next, goal));
          open.add(nextKey);
        }
      }
    }

    return null;
  }

  function bestNextTarget(grid, current, targets) {
    let best = null;
    let bestScore = Infinity;
    let bestPath = null;
    for (const target of targets) {
      const path = findPath(grid, current, target, { avoidTraps: true, avoidBoss: true });
      if (!path) continue;
      const trapCount = path.reduce((sum, pos) => sum + (grid[pos.r][pos.c] === "T" ? 1 : 0), 0);
      const score = path.length + trapCount * 10 - (target.cell === "G" || target.cell === "C" ? 2 : 0);
      if (score < bestScore) {
        best = target;
        bestScore = score;
        bestPath = path;
      }
    }
    return best ? { target: best, path: bestPath } : null;
  }

  function buildPlannedRoute(sourceGrid) {
    const grid = cloneGrid(sourceGrid);
    const start = findCells(grid, ["S"])[0];
    const exit = findCells(grid, ["E"])[0];
    const route = start ? [start] : [];
    const notes = new Map();
    let current = start;
    let coins = findCells(grid, ["C", "G"]);

    notes.set(keyOf(start), "从入口开始探索");

    while (current && coins.length) {
      const pick = bestNextTarget(grid, current, coins);
      if (!pick) break;
      appendPath(route, pick.path);
      notes.set(keyOf(pick.target), "规划收集金币");
      grid[pick.target.r][pick.target.c] = " ";
      current = pick.target;
      coins = coins.filter((coin) => coin.r !== pick.target.r || coin.c !== pick.target.c);
    }

    let bosses = findCells(grid, ["B"]);
    while (current && bosses.length) {
      const pick = bestNextTarget(grid, current, bosses);
      if (!pick) break;
      appendPath(route, pick.path);
      notes.set(keyOf(pick.target), "进入 Boss 战斗");
      grid[pick.target.r][pick.target.c] = " ";
      current = pick.target;
      bosses = bosses.filter((boss) => boss.r !== pick.target.r || boss.c !== pick.target.c);
    }

    if (current && exit) {
      const exitPath = findPath(grid, current, exit, { avoidTraps: false, avoidBoss: false });
      if (exitPath) {
        appendPath(route, exitPath);
        notes.set(keyOf(exit), "抵达出口");
      }
    }

    return { route, notes };
  }

  function appendPath(route, path) {
    if (!path || path.length < 2) return;
    for (let i = 1; i < path.length; i += 1) {
      route.push(path[i]);
    }
  }

  function revealAround(revealed, grid, pos) {
    for (let dr = -VIEW_RADIUS; dr <= VIEW_RADIUS; dr += 1) {
      for (let dc = -VIEW_RADIUS; dc <= VIEW_RADIUS; dc += 1) {
        const r = pos.r + dr;
        const c = pos.c + dc;
        if (inBounds(grid, r, c)) {
          revealed.add(`${r},${c}`);
        }
      }
    }
  }

  function createFrames(data) {
    const grid = cloneGrid(data.maze);
    const mutable = cloneGrid(data.maze);
    const { route, notes } = buildPlannedRoute(grid);
    const revealed = new Set();
    const triggered = new Set();
    const heat = Array.from({ length: grid.length }, () => Array(grid[0].length).fill(0));
    const frames = [];
    let coins = 0;
    let bossCount = 0;

    route.forEach((pos, index) => {
      const sourceCell = grid[pos.r][pos.c];
      const currentCell = mutable[pos.r][pos.c];
      let phase = "探索中";
      let event = notes.get(keyOf(pos)) || "";

      revealAround(revealed, grid, pos);
      heat[pos.r][pos.c] += 1;

      if (index > 0 && (currentCell === "C" || currentCell === "G")) {
        coins += COIN_VALUE;
        mutable[pos.r][pos.c] = " ";
        event = `拾取金币，金币 +${COIN_VALUE}`;
        phase = "资源收集";
      } else if (index > 0 && currentCell === "T" && !triggered.has(keyOf(pos))) {
        coins -= TRAP_DAMAGE;
        triggered.add(keyOf(pos));
        mutable[pos.r][pos.c] = " ";
        event = `触发陷阱，金币 -${TRAP_DAMAGE}`;
        phase = "风险处理";
      } else if (index > 0 && currentCell === "B") {
        bossCount += 1;
        mutable[pos.r][pos.c] = " ";
        event = "Boss 已击败，通路打开";
        phase = "Boss 战斗";
      } else if (sourceCell === "E") {
        phase = "已完成";
        event = "抵达出口";
      }

      frames.push({
        round: index,
        pos: { ...pos },
        coins,
        bossCount,
        phase,
        event,
        sourceCell,
        bossEncounter: index > 0 && currentCell === "B"
          ? {
              bossIndex: bossCount,
              bossTotal: Array.isArray(data.B) ? data.B.length : bossCount,
            }
          : null,
        grid: cloneGrid(mutable),
        revealed: new Set(revealed),
        heat: heat.map((row) => row.slice()),
        exploredRatio: revealed.size / (grid.length * grid[0].length),
      });
    });

    return { frames, route };
  }

  function initMap(data, name = "maze_15_15.json") {
    validateMap(data);
    stopPlayback();
    const { frames, route } = createFrames(data);
    state.data = data;
    state.grid = cloneGrid(data.maze);
    state.frames = frames;
    state.route = route;
    state.frameIndex = 0;
    state.hovered = null;
    state.selected = null;
    state.bossBattleActive = false;
    state.bossBattlePendingFrame = null;
    state.bossBattleQueue = [];
    state.bossAutoResume = false;
    clearTrapHideState();
    clearBossAlert();
    clearBossOverlayCloseTimer();
    clearBossWinAlert();
    clearEffects();
    if (els.emptyMapPrompt) els.emptyMapPrompt.hidden = true;

    els.mapName.textContent = name;
    els.timeline.max = String(Math.max(0, frames.length - 1));
    els.timeline.value = "0";
    els.metricRoute.textContent = route.length ? String(route.length - 1) : "0";
    els.mapMeta.textContent = `${data.maze.length} x ${data.maze[0].length}，Boss ${Array.isArray(data.B) ? data.B.length : 0} 个，技能 ${Array.isArray(data.PlayerSkills) ? data.PlayerSkills.length : 0} 个`;
    updateIntroScreen(data, route, name);
    try {
      window.localStorage.setItem(
        ACTIVE_MAP_CACHE_KEY,
        JSON.stringify({
          name,
          data,
          updatedAt: Date.now(),
        })
      );
    } catch (error) {
      console.warn("Failed to cache active map for boss page sync.", error);
    }

    updateUi();
    fitCanvas();
    draw();
  }

  function validateMap(data) {
    if (!data || !Array.isArray(data.maze) || !data.maze.length || !Array.isArray(data.maze[0])) {
      throw new Error("JSON 中缺少 maze 二维数组");
    }
    const width = data.maze[0].length;
    if (!data.maze.every((row) => Array.isArray(row) && row.length === width)) {
      throw new Error("maze 每一行长度必须一致");
    }
    if (!findCells(data.maze, ["S"]).length || !findCells(data.maze, ["E"]).length) {
      throw new Error("maze 需要包含起点 S 和出口 E");
    }
  }

  async function loadDefaultMap() {
    if (window.location.protocol === "file:") {
      initMap(JSON.parse(JSON.stringify(DEFAULT_MAP_DATA)), "内置示例地图");
      els.mapMeta.textContent += "（本地文件模式）";
      return;
    }

    for (const url of DEFAULT_MAP_CANDIDATES) {
      try {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) continue;
        const data = await response.json();
        const mapName = url.split("/").pop() || "maze_15_15.json";
        initMap(data, mapName);
        return;
      } catch (error) {
        console.warn(`Map candidate failed: ${url}`, error);
      }
    }

    console.warn("Default map file could not be loaded; using embedded map.");
    initMap(JSON.parse(JSON.stringify(DEFAULT_MAP_DATA)), "内置示例地图");
    els.mapMeta.textContent += "（本地文件模式）";
  }

  function initEmptyState() {
    stopPlayback();
    state.data = null;
    state.grid = [];
    state.frames = [];
    state.route = [];
    state.frameIndex = 0;
    state.hovered = null;
    state.selected = null;
    state.bossBattleActive = false;
    state.bossBattlePendingFrame = null;
    state.bossBattleQueue = [];
    state.bossAutoResume = false;
    clearTrapHideState();
    clearBossAlert();
    clearBossOverlayCloseTimer();
    clearBossWinAlert();
    clearEffects();

    document.body.classList.remove("intro-leaving");
    document.body.classList.add("intro-active");
    if (els.emptyMapPrompt) els.emptyMapPrompt.hidden = false;
    els.startGameBtn.disabled = true;
    els.introSize.textContent = "--";
    els.introRoute.textContent = "--";
    els.introBoss.textContent = "--";
    els.introMiniMap.innerHTML = "";
    els.introMeta.textContent = "请先导入地图";
    els.mapName.textContent = "未导入地图";
    els.runState.textContent = "等待导入";
    els.metricRound.textContent = "0";
    els.metricCoins.textContent = "0";
    els.metricExplored.textContent = "0%";
    els.metricRoute.textContent = "0";
    els.phaseLabel.textContent = "等待导入地图";
    els.cellReadout.textContent = "请选择地图文件";
    els.timeline.max = "0";
    els.timeline.value = "0";
    els.mapMeta.textContent = "请选择一张 JSON 地图导入以开始游戏。";
    try {
      window.localStorage.removeItem(ACTIVE_MAP_CACHE_KEY);
    } catch (error) {
      console.warn("Failed to clear active map cache.", error);
    }
    updateTileInfo(null);
    els.cellReadout.textContent = "请选择地图文件";
    renderEvents();
    fitCanvas();
    draw();
  }

  function loadAssets() {
    Object.entries(OBJECT_ASSETS).forEach(([name, src]) => {
      const image = new Image();
      image.onload = () => draw();
      image.onerror = () => {
        state.assets[name] = null;
      };
      image.src = src;
      state.assets[name] = image;
    });

    Object.entries(EFFECT_SHEETS).forEach(([name, src]) => {
      const image = new Image();
      image.onload = () => draw();
      image.onerror = () => {
        state.effectSheets[name] = null;
      };
      image.src = src;
      state.effectSheets[name] = image;
    });
  }

  function effectFrames(sheet) {
    if (!sheet || !sheet.naturalWidth || !sheet.naturalHeight) return 0;
    return Math.max(1, Math.floor(sheet.naturalWidth / sheet.naturalHeight));
  }

  function spawnEffect(effectName, pos, scale = 1.42, frameMs = 60) {
    const sheet = state.effectSheets[effectName];
    if (!sheet || !sheet.complete || !sheet.naturalWidth || !sheet.naturalHeight) return;
    const frames = effectFrames(sheet);
    if (!frames) return;
    state.activeEffects.push({
      effectName,
      pos: { ...pos },
      frameIndex: 0,
      startedAt: performance.now(),
      lastAt: performance.now(),
      frameMs,
      frames,
      scale,
      done: false,
    });
    draw();
    if (!state.effectRafId) {
      animateEffects();
    }
  }

  function animateEffects() {
    if (!state.activeEffects.length) {
      state.effectRafId = null;
      return;
    }
    const now = performance.now();
    let changed = false;
    state.activeEffects.forEach((effect) => {
      if (effect.done) return;
      if (now - effect.lastAt < effect.frameMs) return;
      effect.lastAt = now;
      effect.frameIndex += 1;
      changed = true;
      if (effect.frameIndex >= effect.frames) {
        effect.done = true;
      }
    });
    const before = state.activeEffects.length;
    state.activeEffects = state.activeEffects.filter((effect) => !effect.done);
    if (changed || state.activeEffects.length !== before) {
      draw();
      updateUi();
    }
    if (state.activeEffects.length) {
      state.effectRafId = window.requestAnimationFrame(animateEffects);
    } else {
      state.effectRafId = null;
    }
  }

  function updateIntroScreen(data, route, name) {
    const rows = data.maze.length;
    const cols = data.maze[0].length;
    const bossCells = findCells(data.maze, ["B"]).length;
    const coinCells = findCells(data.maze, ["C", "G"]).length;
    const trapCells = findCells(data.maze, ["T"]).length;

    els.introSize.textContent = `${rows} x ${cols}`;
    els.introRoute.textContent = String(Math.max(0, route.length - 1));
    els.introBoss.textContent = String(bossCells);
    els.introMeta.textContent = `${name} / 金币 ${coinCells} / 陷阱 ${trapCells} / 技能 ${Array.isArray(data.PlayerSkills) ? data.PlayerSkills.length : 0}`;
    els.startGameBtn.disabled = false;
    renderIntroMiniMap(data.maze);
  }

  function renderIntroMiniMap(grid) {
    els.introMiniMap.innerHTML = "";
    els.introMiniMap.style.gridTemplateColumns = `repeat(${grid[0].length}, minmax(0, 1fr))`;

    grid.forEach((row, r) => {
      row.forEach((cell, c) => {
        const item = document.createElement("span");
        item.className = `mini-cell ${miniCellClass(cell)}`;
        item.style.animationDelay = `${Math.min(900, (r + c) * 26)}ms`;
        els.introMiniMap.appendChild(item);
      });
    });
  }

  function miniCellClass(cell) {
    if (cell === "#") return "wall";
    if (cell === "S") return "start";
    if (cell === "E") return "exit";
    if (cell === "B") return "boss";
    if (cell === "T") return "trap";
    if (cell === "C" || cell === "G") return "coin";
    return "path";
  }

  function fitCanvas() {
    const rect = els.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(320, Math.floor(rect.width * dpr));
    const height = Math.max(320, Math.floor(rect.height * dpr));
    if (els.canvas.width !== width || els.canvas.height !== height) {
      els.canvas.width = width;
      els.canvas.height = height;
    }
    state.layout.dpr = dpr;
    state.layout.width = width;
    state.layout.height = height;

    if (state.grid.length) {
      const rows = state.grid.length;
      const cols = state.grid[0].length;
      const pad = Math.max(22 * dpr, Math.min(width, height) * 0.04);
      const tile = Math.floor(Math.min((width - pad * 2) / cols, (height - pad * 2) / rows));
      state.layout.tile = tile;
      state.layout.originX = Math.floor((width - tile * cols) / 2);
      state.layout.originY = Math.floor((height - tile * rows) / 2);
    }
  }

  function currentFrame() {
    return state.frames[state.frameIndex] || null;
  }

  function shouldReveal(frame, r, c) {
    if (!state.showFog || state.mode === "full") return true;
    return frame && frame.revealed.has(`${r},${c}`);
  }

  function draw() {
    fitCanvas();
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);

    if (!state.grid.length) {
      drawEmptyState("请选择一张地图导入以开始游戏");
      return;
    }

    const frame = currentFrame();
    drawBoardBackground();
    drawCells(frame);
    if (state.showPath && state.route.length > 1) drawPath(frame);
    drawFocus(frame);
    drawEffects(frame);
    drawHover();
  }

  function drawEmptyState(message) {
    fitCanvas();
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#16191f";
    ctx.fillRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#f5f7fb";
    ctx.font = `${18 * state.layout.dpr}px sans-serif`;
    ctx.textAlign = "center";
    ctx.fillText(message, state.layout.width / 2, state.layout.height / 2);
  }

  function drawBoardBackground() {
    const { originX, originY, tile } = state.layout;
    const rows = state.grid.length;
    const cols = state.grid[0].length;
    ctx.fillStyle = "#171b22";
    ctx.fillRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#0f1319";
    ctx.fillRect(originX - tile * 0.3, originY - tile * 0.3, tile * (cols + 0.6), tile * (rows + 0.6));
  }

  function drawCells(frame) {
    const rows = state.grid.length;
    const cols = state.grid[0].length;
    const visibleGrid = frame ? frame.grid : state.grid;
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        const revealed = shouldReveal(frame, r, c);
        const trapHidden = state.hiddenTraps.has(`${r},${c}`);
        const cell = revealed ? (trapHidden ? " " : visibleGrid[r][c]) : null;
        drawTile(r, c, cell, frame);
      }
    }
  }

  function drawTile(r, c, cell, frame) {
    const { originX, originY, tile } = state.layout;
    const x = originX + c * tile;
    const y = originY + r * tile;

    if (cell === null) {
      ctx.fillStyle = "#11161d";
      ctx.fillRect(x, y, tile, tile);
      ctx.fillStyle = "rgba(255,255,255,0.05)";
      ctx.fillRect(x + tile * 0.18, y + tile * 0.18, tile * 0.64, tile * 0.64);
      drawGridLine(x, y, tile, "rgba(255,255,255,0.05)");
      return;
    }

    const info = TILE[cell] || TILE[" "];
    const floorAsset = state.assets.floor;
    const wallAsset = state.assets.wall;

    if (state.showSprites && cell === "#" && wallAsset && wallAsset.complete) {
      ctx.drawImage(wallAsset, x, y, tile, tile);
    } else if (state.showSprites && floorAsset && floorAsset.complete && cell !== "#") {
      ctx.drawImage(floorAsset, x, y, tile, tile);
    } else {
      ctx.fillStyle = cell === "#" ? TILE["#"].color : TILE[" "].color;
      ctx.fillRect(x, y, tile, tile);
    }

    if (cell === "S") drawBadge(x, y, tile, "S", TILE.S.color);
    if (cell === "E") drawObject("exit", x, y, tile, info);
    if (cell === "B") drawObject("boss", x, y, tile, info);
    if (cell === "T") drawObject("trap", x, y, tile, info);
    if (cell === "C" || cell === "G") drawObject("coin", x, y, tile, info);
    if (cell === "L") drawBadge(x, y, tile, "L", TILE.L.color);

    drawModeOverlay(r, c, x, y, tile, frame);
    drawGridLine(x, y, tile, "rgba(15, 19, 25, 0.22)");
  }

  function drawObject(name, x, y, tile, info) {
    const image = state.assets[name];
    if (state.showSprites && image && image.complete) {
      const inset = tile * 0.12;
      ctx.drawImage(image, x + inset, y + inset, tile - inset * 2, tile - inset * 2);
      return;
    }
    drawBadge(x, y, tile, info.label.slice(0, 1), info.color);
  }

  function drawBadge(x, y, tile, text, color) {
    const radius = tile * 0.3;
    ctx.beginPath();
    ctx.arc(x + tile / 2, y + tile / 2, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.9)";
    ctx.lineWidth = Math.max(1, tile * 0.045);
    ctx.stroke();
    ctx.fillStyle = "#fff";
    ctx.font = `800 ${Math.max(11, tile * 0.34)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, x + tile / 2, y + tile / 2 + tile * 0.02);
  }

  function drawModeOverlay(r, c, x, y, tile, frame) {
    const baseCell = state.grid[r][c];
    const heatValue = frame?.heat?.[r]?.[c] || 0;
    if (state.mode === "risk" && baseCell === "T") {
      ctx.fillStyle = "rgba(228, 87, 46, 0.38)";
      ctx.fillRect(x, y, tile, tile);
    }
    if (state.mode === "reward" && (baseCell === "C" || baseCell === "G")) {
      ctx.fillStyle = "rgba(47, 158, 68, 0.32)";
      ctx.fillRect(x, y, tile, tile);
    }
    if (state.showHeat && heatValue > 0) {
      const alpha = Math.min(0.46, 0.12 + heatValue * 0.07);
      ctx.fillStyle = `rgba(109, 93, 252, ${alpha})`;
      ctx.fillRect(x, y, tile, tile);
    }
  }

  function drawGridLine(x, y, tile, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1, state.layout.dpr);
    ctx.strokeRect(x + 0.5, y + 0.5, tile - 1, tile - 1);
  }

  function drawPath(frame) {
    const { originX, originY, tile } = state.layout;
    const toPoint = (pos) => ({
      x: originX + pos.c * tile + tile / 2,
      y: originY + pos.r * tile + tile / 2,
    });

    drawRouteSegment(state.route, 0, state.route.length - 1, "rgba(15, 139, 141, 0.25)", Math.max(2, tile * 0.12), toPoint);
    if (frame) {
      drawRouteSegment(state.route, 0, state.frameIndex, "rgba(242, 165, 65, 0.88)", Math.max(3, tile * 0.16), toPoint);
    }
  }

  function drawRouteSegment(route, start, end, color, width, toPoint) {
    if (end <= start) return;
    ctx.beginPath();
    for (let i = start; i <= end; i += 1) {
      const p = toPoint(route[i]);
      if (i === start) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
  }

  function drawFocus(frame) {
    if (!frame) return;
    const { originX, originY, tile } = state.layout;
    const x = originX + frame.pos.c * tile;
    const y = originY + frame.pos.r * tile;

    ctx.save();
    ctx.shadowColor = "rgba(242, 165, 65, 0.75)";
    ctx.shadowBlur = tile * 0.5;
    const player = state.assets.player;
    if (state.showSprites && player && player.complete) {
      const inset = tile * 0.06;
      ctx.drawImage(player, x + inset, y + inset, tile - inset * 2, tile - inset * 2);
    } else {
      drawBadge(x, y, tile, "P", "#0f8b8d");
    }
    ctx.restore();

    if (state.showFog && state.mode !== "full") {
      ctx.strokeStyle = "rgba(255,255,255,0.85)";
      ctx.lineWidth = Math.max(2, tile * 0.06);
      const size = tile * (VIEW_RADIUS * 2 + 1);
      ctx.strokeRect(x - tile * VIEW_RADIUS, y - tile * VIEW_RADIUS, size, size);
    }
  }

  function drawHover() {
    const target = state.hovered || state.selected;
    if (!target || !state.grid.length) return;
    const { originX, originY, tile } = state.layout;
    const x = originX + target.c * tile;
    const y = originY + target.r * tile;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(2, tile * 0.055);
    ctx.strokeRect(x + 2, y + 2, tile - 4, tile - 4);
  }

  function drawEffects(frame) {
    if (!frame || !state.activeEffects.length) return;
    const { originX, originY, tile } = state.layout;
    state.activeEffects.forEach((effect) => {
      const sheet = state.effectSheets[effect.effectName];
      if (!sheet || !sheet.complete || !sheet.naturalWidth || !sheet.naturalHeight) return;
      const side = sheet.naturalHeight;
      const sx = Math.min(effect.frameIndex, effect.frames - 1) * side;
      const size = tile * effect.scale;
      const dx = originX + effect.pos.c * tile + (tile - size) / 2;
      const dy = originY + effect.pos.r * tile + (tile - size) / 2;
      ctx.drawImage(sheet, sx, 0, side, side, dx, dy, size, size);
    });
  }

  function updateUi() {
    const frame = currentFrame();
    const routeLength = Math.max(0, state.route.length - 1);
    if (!frame) {
      els.runState.textContent = "待机";
      return;
    }

    els.metricRound.textContent = String(frame.round);
    els.metricCoins.textContent = String(frame.coins);
    els.metricExplored.textContent = `${Math.round(frame.exploredRatio * 100)}%`;
    els.metricRoute.textContent = String(routeLength);
    els.phaseLabel.textContent = frame.phase;
    els.runState.textContent = state.playing ? "播放中" : "已暂停";
    els.timeline.value = String(state.frameIndex);
    els.playBtn.textContent = state.playing ? "Ⅱ" : "▶";

    updateTileInfo(state.hovered || state.selected || frame.pos);
    renderEvents();
  }

  function updateTileInfo(pos) {
    if (!pos || !state.grid.length) {
      els.tileCoord.textContent = "-";
      els.tileType.textContent = "-";
      els.tileWeight.textContent = "-";
      els.cellReadout.textContent = "悬停查看格子";
      return;
    }

    const frame = currentFrame();
    const visibleGrid = frame ? frame.grid : state.grid;
    const revealed = !frame || shouldReveal(frame, pos.r, pos.c);
    const cell = revealed ? visibleGrid[pos.r][pos.c] : null;
    const info = cell === null ? { label: "未知", weight: "-", color: "#11161d" } : (TILE[cell] || TILE[" "]);
    els.tileCoord.textContent = `${pos.r}, ${pos.c}`;
    els.tileType.textContent = info.label;
    els.tileWeight.textContent = info.weight;
    els.cellReadout.textContent = `(${pos.r}, ${pos.c}) ${info.label}`;
  }

  function renderEvents() {
    const events = state.frames
      .filter((frame, index) => index <= state.frameIndex && frame.event)
      .slice(-12)
      .reverse();

    els.eventList.innerHTML = "";
    events.forEach((frame) => {
      const item = document.createElement("li");
      const round = document.createElement("span");
      const copy = document.createElement("span");
      round.className = "event-round";
      copy.className = "event-copy";
      round.textContent = `#${frame.round}`;
      copy.textContent = frame.event;
      item.append(round, copy);
      els.eventList.appendChild(item);
    });
  }

  function renderLegend() {
    const entries = [
      ["#", "墙体"],
      ["S", "起点"],
      ["E", "出口"],
      ["B", "Boss"],
      ["T", "陷阱"],
      ["G", "金币"],
      [" ", "通路"],
      [null, "未知"],
    ];
    els.legendGrid.innerHTML = "";
    entries.forEach(([cell, label]) => {
      const item = document.createElement("div");
      const swatch = document.createElement("span");
      const text = document.createElement("span");
      item.className = "legend-item";
      swatch.className = "legend-swatch";
      swatch.style.background = cell === null ? "#11161d" : (TILE[cell] || TILE[" "]).color;
      text.textContent = label;
      item.append(swatch, text);
      els.legendGrid.appendChild(item);
    });
  }

  function setFrame(index) {
    const previousFrameIndex = state.frameIndex;
    const nextFrameIndex = Math.max(0, Math.min(index, state.frames.length - 1));
    if (nextFrameIndex < previousFrameIndex) {
      state.bossBattleQueue = state.bossBattleQueue.filter((frameIndex) => frameIndex < nextFrameIndex);
      state.pendingBossOutcome = null;
      clearBossAlert();
      clearBossWinAlert();
    }
    state.frameIndex = nextFrameIndex;
    if (state.frameIndex >= state.frames.length - 1) stopPlayback();
    updateUi();
    draw();
    triggerFrameEffects(currentFrame(), previousFrameIndex);
    scheduleTrapHide(currentFrame());
    maybeTriggerBossBattle();
  }

  function step(delta) {
    setFrame(state.frameIndex + delta);
  }

  function resetBossBattleReplayState() {
    state.bossBattleQueue = [];
    state.bossBattlePendingFrame = null;
    state.bossAutoResume = false;
    clearBossAlert();
    clearBossOverlayCloseTimer();
    clearBossWinAlert();
    clearTrapHideState();
    clearEffects();
  }

  function startPlayback() {
    if (!state.frames.length || state.playing) return;
    state.playing = true;
    els.runState.textContent = "播放中";
    els.playBtn.textContent = "Ⅱ";
    scheduleTick();
  }

  function stopPlayback() {
    state.playing = false;
    if (state.timer) window.clearTimeout(state.timer);
    state.timer = null;
    els.playBtn.textContent = "▶";
    if (state.frames.length) els.runState.textContent = "已暂停";
  }

  function togglePlayback() {
    if (state.bossBattleActive) return;
    if (state.playing) stopPlayback();
    else {
      if (state.frameIndex >= state.frames.length - 1) {
        resetBossBattleReplayState();
        setFrame(0);
      }
      startPlayback();
    }
    updateUi();
  }

  function scheduleTick() {
    if (!state.playing || state.bossBattleActive) return;
    state.timer = window.setTimeout(() => {
      setFrame(state.frameIndex + 1);
      scheduleTick();
    }, Math.max(40, 650 / state.speed));
  }

  function reset() {
    stopPlayback();
    closeBossOverlay(false);
    resetBossBattleReplayState();
    setFrame(0);
  }

  function buildBossBattlePayload(frame) {
    const bossIndex = frame?.bossEncounter?.bossIndex ?? 1;
    const bossHp = state.data?.B?.[bossIndex - 1];
    return {
      requestId: `boss-${Date.now()}-${state.bossBattleRequestId += 1}`,
      mapName: `${els.mapName.textContent || "maze_15_15.json"} / Boss ${bossIndex}`,
      mapData: cloneData(state.data || {}),
      startingCoins: frame?.coins ?? 0,
      PlayerSkills: cloneData(state.data?.PlayerSkills || []),
      B: Number.isFinite(Number(bossHp)) ? [Number(bossHp)] : [1],
      minRouds: state.data?.minRouds ?? 1,
      CoinConsumption: state.data?.CoinConsumption ?? 0,
      bossIndex,
      bossTotal: frame?.bossEncounter?.bossTotal ?? 1,
    };
  }

  function ensureBossFrameLoaded() {
    if (state.bossFrameLoaded) return;
    state.bossFrameLoaded = true;
    els.bossOverlayFrame.src = "./boss.html?embed=1";
  }

  function dispatchBossBattle(payload) {
    const win = els.bossOverlayFrame.contentWindow;
    if (!win) {
      state.pendingBossPayload = payload;
      return;
    }
    win.postMessage({ type: "maze-start-boss-battle", payload }, "*");
  }

  function showBossAlert(frame) {
    const bossIndex = frame?.bossEncounter?.bossIndex ?? 1;
    const bossTotal = frame?.bossEncounter?.bossTotal ?? 1;
    els.bossAlertTitle.textContent = "进入 Boss 战";
    els.bossAlertMeta.textContent = `Boss ${bossIndex} / ${bossTotal}`;
    els.bossAlert.hidden = false;
    els.bossAlert.setAttribute("aria-hidden", "false");
    els.bossAlert.classList.remove("is-visible");
    void els.bossAlert.offsetWidth;
    els.bossAlert.classList.add("is-visible");
  }

  function queueBossOverlay(frame) {
    if (!frame || !frame.bossEncounter) return;
    stopPlayback();
    showBossAlert(frame);
    if (state.bossAlertTimer) {
      window.clearTimeout(state.bossAlertTimer);
    }
    state.bossAlertTimer = window.setTimeout(() => {
      state.bossAlertTimer = null;
      clearBossAlert();
      const latest = currentFrame();
      if (latest?.bossEncounter && latest.round === frame.round) {
        openBossOverlay(latest);
      }
    }, 880);
  }

  function playPendingBossOutcomeEffect() {
    if (!state.pendingBossOutcome) return;
    const outcome = state.pendingBossOutcome;
    state.pendingBossOutcome = null;
    const frame = state.frames[outcome.frameIndex] || currentFrame();
    if (!frame?.pos) return;
    spawnEffect(outcome.result === "win" ? "boss_win" : "boss_lose", frame.pos, 1.62, 58);
    if (outcome.result === "win") {
      showBossWinAlert(outcome);
    }
  }

  function showBossWinAlert(outcome) {
    clearBossWinAlert();
    els.bossWinMeta.textContent = outcome.bossIndex ? `Boss ${outcome.bossIndex} 已击败` : "Boss 已击败";
    els.bossWinAlert.hidden = false;
    els.bossWinAlert.setAttribute("aria-hidden", "false");
    void els.bossWinAlert.offsetWidth;
    els.bossWinAlert.classList.add("is-visible");
    state.bossWinAlertTimer = window.setTimeout(() => {
      clearBossWinAlert();
    }, 2100);
  }

  function openBossOverlay(frame) {
    if (!frame || !frame.bossEncounter || state.bossBattleActive) return;
    clearBossAlert();
    const payload = buildBossBattlePayload(frame);
    state.bossBattleActive = true;
    state.bossBattlePendingFrame = state.frameIndex;
    state.bossAutoResume = true;
    stopPlayback();
    document.body.classList.add("overlay-open");
    els.bossOverlay.hidden = false;
    els.bossOverlay.setAttribute("aria-hidden", "false");
    els.bossOverlayTitle.textContent = `Boss ${payload.bossIndex} 战斗中`;
    ensureBossFrameLoaded();
    if (state.bossFrameReady) {
      dispatchBossBattle(payload);
    } else {
      state.pendingBossPayload = payload;
    }
  }

  function closeBossOverlay(resumePlayback = true) {
    if (!state.bossBattleActive && els.bossOverlay.hidden) return;
    clearBossOverlayCloseTimer();
    const shouldResume = resumePlayback && state.bossAutoResume && state.frameIndex < state.frames.length - 1;
    state.bossBattleActive = false;
    state.bossBattlePendingFrame = null;
    els.bossOverlay.hidden = true;
    els.bossOverlay.setAttribute("aria-hidden", "true");
    document.body.classList.remove("overlay-open");
    updateUi();
    draw();
    scheduleTrapHide(currentFrame());
    playPendingBossOutcomeEffect();
    state.bossAutoResume = false;
    if (shouldResume) startPlayback();
  }

  function maybeTriggerBossBattle() {
    const frame = currentFrame();
    if (!frame?.bossEncounter || state.bossBattleActive || state.bossAlertTimer) return;
    if (state.bossBattleQueue.includes(state.frameIndex)) return;
    state.bossBattleQueue.push(state.frameIndex);
    queueBossOverlay(frame);
  }

  function handleBossOverlayMessage(event) {
    const data = event?.data;
    if (!data) return;
    if (data.type === "maze-boss-ready") {
      state.bossFrameReady = true;
      if (state.pendingBossPayload) {
        const payload = state.pendingBossPayload;
        state.pendingBossPayload = null;
        dispatchBossBattle(payload);
      }
      return;
    }
    if (data.type !== "maze-boss-complete") return;
    if (!state.bossBattleActive) return;
    const frame = currentFrame();
    const status = data.result === 1 ? "已结束（胜利）" : "已结束（失败）";
    els.bossOverlayTitle.textContent = `Boss ${data.bossIndex ?? ""} 战斗${status}`;
    state.pendingBossOutcome = {
      result: data.result === 1 ? "win" : "lose",
      frameIndex: state.bossBattlePendingFrame ?? state.frameIndex,
      bossIndex: data.bossIndex ?? frame?.bossEncounter?.bossIndex ?? 1,
      pos: frame?.pos ? { ...frame.pos } : null,
    };
    clearBossOverlayCloseTimer();
    state.bossOverlayCloseTimer = window.setTimeout(() => {
      state.bossOverlayCloseTimer = null;
      closeBossOverlay(true);
    }, 900);
  }

  function triggerFrameEffects(frame, previousFrameIndex) {
    if (!frame) return;
    if (state.lastEffectFrameIndex === state.frameIndex && previousFrameIndex === state.frameIndex) return;
    state.lastEffectFrameIndex = state.frameIndex;
    if (frame.bossEncounter) {
      spawnEffect("boss_enter", frame.pos, 1.48, 58);
    }
    if (frame.sourceCell === "E") {
      spawnEffect("portal_enter", frame.pos, 1.48, 58);
    }
  }

  function enterMaze() {
    if (!state.frames.length || document.body.classList.contains("intro-leaving")) return;
    els.startGameBtn.disabled = true;
    resetBossBattleReplayState();
    setFrame(0);
    document.body.classList.add("intro-leaving");
    window.setTimeout(() => {
      document.body.classList.remove("intro-active", "intro-leaving");
      startPlayback();
    }, 560);
  }

  function openMapImporter() {
    els.fileInput.click();
  }

  function canvasToCell(event) {
    const rect = els.canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) * state.layout.dpr;
    const y = (event.clientY - rect.top) * state.layout.dpr;
    const { originX, originY, tile } = state.layout;
    const c = Math.floor((x - originX) / tile);
    const r = Math.floor((y - originY) / tile);
    if (!state.grid.length || !inBounds(state.grid, r, c)) return null;
    return { r, c };
  }

  function bindEvents() {
    els.startGameBtn.disabled = true;
    els.startGameBtn.addEventListener("click", enterMaze);
    els.emptyImportBtn.addEventListener("click", openMapImporter);
    els.introImportBtn.addEventListener("click", openMapImporter);

    els.playBtn.addEventListener("click", togglePlayback);
    els.resetBtn.addEventListener("click", reset);
    els.prevBtn.addEventListener("click", () => {
      stopPlayback();
      step(-1);
    });
    els.nextBtn.addEventListener("click", () => {
      stopPlayback();
      step(1);
    });
    els.closeBossOverlayBtn.addEventListener("click", () => {
      closeBossOverlay(false);
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

    els.toggleFog.addEventListener("change", (event) => {
      state.showFog = event.target.checked;
      draw();
      updateUi();
    });
    els.togglePath.addEventListener("change", (event) => {
      state.showPath = event.target.checked;
      draw();
    });
    els.toggleHeat.addEventListener("change", (event) => {
      state.showHeat = event.target.checked;
      draw();
    });
    els.toggleSprites.addEventListener("change", (event) => {
      state.showSprites = event.target.checked;
      draw();
    });

    document.querySelectorAll(".segment").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll(".segment").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        state.mode = button.dataset.mode;
        draw();
        updateUi();
      });
    });

    els.loadDefaultBtn.addEventListener("click", loadDefaultMap);
    els.fileInput.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        const data = JSON.parse(await file.text());
        initMap(data, file.name);
      } catch (error) {
        els.mapMeta.textContent = `导入失败：${error.message}`;
      } finally {
        els.fileInput.value = "";
      }
    });

    els.canvas.addEventListener("mousemove", (event) => {
      state.hovered = canvasToCell(event);
      updateTileInfo(state.hovered || state.selected || currentFrame()?.pos);
      draw();
    });
    els.canvas.addEventListener("mouseleave", () => {
      state.hovered = null;
      updateTileInfo(state.selected || currentFrame()?.pos);
      draw();
    });
    els.canvas.addEventListener("click", (event) => {
      state.selected = canvasToCell(event);
      updateTileInfo(state.selected || currentFrame()?.pos);
      draw();
    });

    window.addEventListener("resize", draw);
    window.addEventListener("message", handleBossOverlayMessage);
  }

  loadAssets();
  renderLegend();
  bindEvents();
  initEmptyState();
  ensureBossFrameLoaded();
})();
