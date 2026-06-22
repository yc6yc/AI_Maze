(() => {
  const MAP_DIR = "../map/";
  const MAP_FILE_LIST = ["maze_15_15.json","maze.json","1.json","2.json","3.json","4.json"];
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

  // ============================================================
  // Algorithm Comparison — Config & Constants
  // ============================================================
  const ALGO_A_CONFIG = {
    coin_value: 50,
    trap_penalty: 30,
    step_cost: 10.0,
    explore_bonus: 8.0,
    visited_penalty: 3.0,
    w_backtrack: 2.0,
  };

  const ALGO_B_CONFIG = {
    coin_value: 50.0,
    frontier_value: 14.0,
    boss_value: 120.0,
    exit_value: 1000000.0,
    trap_step_cost: 31.0,
    target_retry_buffer: 1,
    frontier_unknown_weight: 4.0,
    revisit_penalty: 0.15,
    min_explore_before_boss: 0.25,
  };

  const COMPARE_MAX_STEPS = 500;
  const COMPARE_MAX_STUCK = 20;

  const TILE = {
    "#": {
      label: "Wall",
      color: "#14101f",
      stroke: "#0a0815",
      weight: "Impassable",
      asset: "../viz/assets/wall.png",
    },
    " ": {
      label: "Path",
      color: "#0c0b18",
      stroke: "#1a1630",
      weight: "1",
      asset: "../viz/assets/floor.png",
    },
    S: {
      label: "Start",
      color: "#00e5ff",
      stroke: "#005a6e",
      weight: "1",
      asset: "../viz/assets/floor.png",
    },
    E: {
      label: "Exit",
      color: "#ffaa00",
      stroke: "#6e4a00",
      weight: "Goal",
      asset: "../viz/assets/exit.png",
    },
    B: {
      label: "Boss",
      color: "#ff3355",
      stroke: "#801020",
      weight: "Combat",
      asset: "../viz/assets/boss.png",
    },
    T: {
      label: "Trap",
      color: "#ff7700",
      stroke: "#803800",
      weight: `+${TRAP_DAMAGE}`,
      asset: "../viz/assets/trap.png",
    },
    C: {
      label: "Coin",
      color: "#ffaa00",
      stroke: "#6e4a00",
      weight: `+${COIN_VALUE}`,
      asset: "../viz/assets/coin.png",
    },
    G: {
      label: "Coin",
      color: "#ffaa00",
      stroke: "#6e4a00",
      weight: `+${COIN_VALUE}`,
      asset: "../viz/assets/coin.png",
    },
    L: {
      label: "Mech",
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
    actorPlayer: document.getElementById("actorPlayer"),
    actorBoss: document.getElementById("actorBoss"),
    canvasStack: document.getElementById("canvasStack"),
    battleEffects: document.getElementById("battleEffects"),
    slashBeam: document.getElementById("slashBeam"),
    damagePop: document.getElementById("damagePop"),
    particleBurst: document.getElementById("particleBurst"),
    battlePrompt: document.getElementById("battlePrompt"),
    enterBattleBtn: document.getElementById("enterBattleBtn"),
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
    battleDataBtn: document.getElementById("battleDataBtn"),
    battleDataPanel: document.getElementById("battleDataPanel"),
    closeBattleDataBtn: document.getElementById("closeBattleDataBtn"),
    bdHit: document.getElementById("bdHit"),
    bdPhase: document.getElementById("bdPhase"),
    bdRound: document.getElementById("bdRound"),
    bdCoins: document.getElementById("bdCoins"),
    bdPlayerAction: document.getElementById("bdPlayerAction"),
    bdBossAction: document.getElementById("bdBossAction"),
    bdEffect: document.getElementById("bdEffect"),
    bdScreen: document.getElementById("bdScreen"),
    bdEventList: document.getElementById("bdEventList"),
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
    compareResult: null,
    _originalFrames: null,
    _originalRoute: null,
    battleDataOpen: false,
    battleHitCount: 0,
    battleTotalHits: 5,
    battleEventLog: [],
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

  // ---- Actor panel & battle transition ----
  function showActors() {
    if (els.actorPlayer) els.actorPlayer.classList.add("visible");
    if (els.actorBoss) els.actorBoss.classList.add("visible");
  }
  function hideActors() {
    if (els.actorPlayer) els.actorPlayer.classList.remove("visible");
    if (els.actorBoss) els.actorBoss.classList.remove("visible");
  }
  function showBattlePrompt() {
    if (els.battlePrompt) els.battlePrompt.classList.remove("hidden");
  }
  function hideBattlePrompt() {
    if (els.battlePrompt) els.battlePrompt.classList.add("hidden");
  }
  // ---- Real Boss Battle Animation (SVG actors + CSS) ----
  function clearBattleClasses() {
    if (els.actorPlayer) {
      els.actorPlayer.classList.remove("battle-charge", "battle-dash", "battle-attack", "battle-recover", "melee-counter-hit");
    }
    if (els.actorBoss) {
      els.actorBoss.classList.remove("battle-hit", "battle-defeated", "battle-dash");
    }
    if (els.slashBeam) els.slashBeam.classList.remove("animate");
    if (els.damagePop) els.damagePop.classList.remove("animate");
    if (els.particleBurst) els.particleBurst.classList.remove("animate");
    if (els.battleEffects) els.battleEffects.classList.remove("active");
    document.body.classList.remove("screen-shake");
    document.body.classList.remove("melee-mode");
  }

  function resetHitClasses() {
    if (els.actorPlayer) {
      els.actorPlayer.classList.remove("battle-charge", "battle-dash", "battle-attack", "battle-recover", "melee-counter-hit");
    }
    if (els.actorBoss) {
      els.actorBoss.classList.remove("battle-hit", "battle-defeated", "battle-dash");
    }
    if (els.slashBeam) els.slashBeam.classList.remove("animate");
    if (els.damagePop) els.damagePop.classList.remove("animate");
    if (els.particleBurst) els.particleBurst.classList.remove("animate");
    document.body.classList.remove("screen-shake");
  }

  function startSvgBattleSequence() {
    const player = els.actorPlayer;
    const boss = els.actorBoss;
    if (!player || !boss) return;

    resetHitClasses();
    if (els.battleEffects) els.battleEffects.classList.add("active");

    const hits = 5;
    const cycleMs = 5000;
    let hit = 0;

    function doOneHit() {
      if (hit >= hits) {
        // Final recovery
        updateBattleData("Recovery", "Recovering", "Defeated", "None", "Stable");
        setTimeout(function() {
          resetHitClasses();
          player.classList.add("battle-recover");
          setTimeout(function() {
            clearBattleClasses();
            exitBattleMode();
            startPlayback();
          }, 2500);
        }, 1000);
        return;
      }

      state.battleHitCount = hit + 1;
      resetHitClasses();
      player.classList.add("battle-charge");
      updateBattleData("Charge", "Charging sword", "Bracing", "Sword glow", "Stable");

      // 2s charge → dash
      setTimeout(function() {
        player.classList.remove("battle-charge");
        player.classList.add("battle-dash");
        updateBattleData("Dash", "Lunging forward", "Bracing", "Dash", "Stable");
      }, 2000);

      // 3.2s dash → attack + slash beam + screen shake
      setTimeout(function() {
        player.classList.remove("battle-dash");
        player.classList.add("battle-attack");
        if (els.slashBeam) { els.slashBeam.classList.remove("animate"); void els.slashBeam.offsetWidth; els.slashBeam.classList.add("animate"); }
        document.body.classList.add("screen-shake");
        setTimeout(function() { document.body.classList.remove("screen-shake"); }, 600);
        updateBattleData("Attack", "Slashing", "Hit", "Slash beam", "Shaking");
      }, 3200);

      // 3.8s boss hit + damage pop + particles
      setTimeout(function() {
        boss.classList.add("battle-hit");
        if (els.damagePop) { els.damagePop.classList.remove("animate"); void els.damagePop.offsetWidth; els.damagePop.classList.add("animate"); }
        if (els.particleBurst) { els.particleBurst.classList.remove("animate"); void els.particleBurst.offsetWidth; els.particleBurst.classList.add("animate"); }
        updateBattleData("Impact", "Slash connected", "Staggering", "DMG + Particles", "Shaking");
      }, 3800);

      // Boss counter (40% on hit 3+)
      if (hit >= 2 && Math.random() < 0.4) {
        setTimeout(function() {
          resetHitClasses();
          boss.classList.add("battle-dash");
          updateBattleData("Counter Windup", "Vulnerable", "Counter-attacking", "Boss lunge", "Stable");
          setTimeout(function() {
            player.classList.add("melee-counter-hit");
            document.body.classList.add("screen-shake");
            setTimeout(function() { document.body.classList.remove("screen-shake"); }, 600);
            updateBattleData("Counter Hit!", "Knocked back", "Counter strike", "Knockback", "Shaking");
            setTimeout(function() {
              resetHitClasses();
              hit++;
              doOneHit();
            }, 1600);
          }, 800);
        }, 4300);
      } else {
        setTimeout(function() {
          boss.classList.remove("battle-hit");
          player.classList.remove("battle-attack");
          hit++;
          doOneHit();
        }, cycleMs);
      }
    }

    doOneHit();
  }

  function updateBattleData(phase, playerAction, bossAction, effect, screen) {
    if (!els.bdHit) return;
    els.bdHit.textContent = state.battleHitCount + " / " + state.battleTotalHits;
    els.bdPhase.textContent = phase || "Idle";
    var frame = state.frames[state.frameIndex];
    els.bdRound.textContent = frame ? String(frame.round || 0) : "0";
    els.bdCoins.textContent = frame ? String(frame.coins || 0) : "0";
    els.bdPlayerAction.textContent = playerAction || "Idle";
    els.bdBossAction.textContent = bossAction || "Idle";
    els.bdEffect.textContent = effect || "None";
    els.bdScreen.textContent = screen || "Stable";

    if (phase && phase !== "Idle") {
      var msg = "[" + state.battleHitCount + "] " + (playerAction || phase);
      if (bossAction && bossAction !== "Idle") msg += " / Boss: " + bossAction;
      if (effect && effect !== "None") msg += " / " + effect;
      state.battleEventLog.unshift(msg);
      if (state.battleEventLog.length > 30) state.battleEventLog.pop();
      renderBattleEvents();
    }
  }

  function renderBattleEvents() {
    if (!els.bdEventList) return;
    els.bdEventList.innerHTML = "";
    state.battleEventLog.forEach(function(msg, i) {
      var li = document.createElement("li");
      li.innerHTML = '<span class="event-round" style="color:var(--cyan);font-weight:700;min-width:24px;">' + (i + 1) + "</span><span style='color:var(--text-dim);'>" + msg + "</span>";
      els.bdEventList.appendChild(li);
    });
  }

  function toggleBattleDataPanel() {
    state.battleDataOpen = !state.battleDataOpen;
    if (els.battleDataPanel) els.battleDataPanel.classList.toggle("hidden", !state.battleDataOpen);
  }

  function enterBattleMode() {
    hideBattlePrompt();
    if (els.canvasStack) els.canvasStack.classList.add("hidden");
    document.body.classList.add("melee-mode");
    state.battleHitCount = 0;
    state.battleEventLog = [];
    if (els.battleDataBtn) els.battleDataBtn.hidden = false;
    bgmCrossfade(bgmEls.boss);
    startSvgBattleSequence();
  }

  function exitBattleMode() {
    clearBattleClasses();
    if (els.canvasStack) els.canvasStack.classList.remove("hidden");
    if (els.battleDataBtn) els.battleDataBtn.hidden = true;
    if (els.battleDataPanel) els.battleDataPanel.classList.add("hidden");
    state.battleDataOpen = false;
    bgmCrossfade(bgmEls.maze);
    draw();
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

    notes.set(keyOf(start), "Starting exploration from entrance");

    while (current && coins.length) {
      const pick = bestNextTarget(grid, current, coins);
      if (!pick) break;
      appendPath(route, pick.path);
      notes.set(keyOf(pick.target), "Plan to collect coin");
      grid[pick.target.r][pick.target.c] = " ";
      current = pick.target;
      coins = coins.filter((coin) => coin.r !== pick.target.r || coin.c !== pick.target.c);
    }

    let bosses = findCells(grid, ["B"]);
    while (current && bosses.length) {
      const pick = bestNextTarget(grid, current, bosses);
      if (!pick) break;
      appendPath(route, pick.path);
      notes.set(keyOf(pick.target), "Entering Boss combat");
      grid[pick.target.r][pick.target.c] = " ";
      current = pick.target;
      bosses = bosses.filter((boss) => boss.r !== pick.target.r || boss.c !== pick.target.c);
    }

    if (current && exit) {
      const exitPath = findPath(grid, current, exit, { avoidTraps: false, avoidBoss: false });
      if (exitPath) {
        appendPath(route, exitPath);
        notes.set(keyOf(exit), "Reached exit");
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
      let phase = "Exploring";
      let event = notes.get(keyOf(pos)) || "";

      revealAround(revealed, grid, pos);
      heat[pos.r][pos.c] += 1;

      if (index > 0 && (currentCell === "C" || currentCell === "G")) {
        coins += COIN_VALUE;
        mutable[pos.r][pos.c] = " ";
        event = `Collected coin, coins +${COIN_VALUE}`;
        phase = "Resource Collect";
      } else if (index > 0 && currentCell === "T" && !triggered.has(keyOf(pos))) {
        coins -= TRAP_DAMAGE;
        triggered.add(keyOf(pos));
        mutable[pos.r][pos.c] = " ";
        event = `Trap triggered, coins -${TRAP_DAMAGE}`;
        phase = "Risk Handling";
      } else if (index > 0 && currentCell === "B") {
        bossCount += 1;
        mutable[pos.r][pos.c] = " ";
        event = "Boss defeated, path opened";
        phase = "Boss Combat";
      } else if (sourceCell === "E") {
        phase = "Complete";
        event = "Reached exit";
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
  // ============================================================
  // Shared FOG simulation utilities
  // ============================================================

  function initFogMap(rows, cols) {
    return Array.from({ length: rows }, function () { return Array(cols).fill(null); });
  }

  // isWalkableFog: None (null) → not walkable (enforces FOG constraint)
  function isWalkableFog(cell) {
    return cell !== null && cell !== "#";
  }

  // neighborsFog: 4-directional neighbors using fog_map (null = impassable)
  function neighborsFog(fogMap, pos) {
    var dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    var result = [];
    for (var d = 0; d < dirs.length; d++) {
      var nr = pos.r + dirs[d][0];
      var nc = pos.c + dirs[d][1];
      if (nr >= 0 && nc >= 0 && nr < fogMap.length && nc < fogMap[0].length) {
        if (isWalkableFog(fogMap[nr][nc])) {
          result.push({ r: nr, c: nc });
        }
      }
    }
    return result;
  }

  function revealFog(fogMap, groundTruth, pos, viewRadius) {
    for (var dr = -viewRadius; dr <= viewRadius; dr++) {
      for (var dc = -viewRadius; dc <= viewRadius; dc++) {
        var nr = pos.r + dr;
        var nc = pos.c + dc;
        if (nr >= 0 && nc >= 0 && nr < fogMap.length && nc < fogMap[0].length) {
          fogMap[nr][nc] = groundTruth[nr][nc];
        }
      }
    }
  }

  function getRevealedSet(fogMap) {
    var revealed = new Set();
    for (var r = 0; r < fogMap.length; r++) {
      for (var c = 0; c < fogMap[0].length; c++) {
        if (fogMap[r][c] !== null) {
          revealed.add(keyOf({ r: r, c: c }));
        }
      }
    }
    return revealed;
  }

  function findStartPos(grid) {
    for (var r = 0; r < grid.length; r++) {
      for (var c = 0; c < grid[0].length; c++) {
        if (grid[r][c] === "S") return { r: r, c: c };
      }
    }
    return null;
  }

  // ============================================================
  // Dijkstra (port of core/pathfinding.py dijkstra)
  // Used by Algorithm B (GlobalGreedyAgent)
  // ============================================================
  function dijkstraFog(fogMap, start, triggeredTraps, trapStepCost) {
    var dist = {};
    var prev = {};
    var sk = keyOf(start);
    dist[sk] = 0;
    prev[sk] = null;
    var heap = [[0, start]];

    while (heap.length) {
      // Extract min (simple sort — maze sizes are small, <10000 cells)
      heap.sort(function (a, b) { return a[0] - b[0]; });
      var curEntry = heap.shift();
      var d = curEntry[0];
      var cur = curEntry[1];
      var ck = keyOf(cur);
      if (d > (dist[ck] !== undefined ? dist[ck] : Infinity)) continue;

      var nbrs = neighborsFog(fogMap, cur);
      for (var i = 0; i < nbrs.length; i++) {
        var next = nbrs[i];
        var nk = keyOf(next);
        var cell = fogMap[next.r][next.c];
        var weight = 1.0;
        if (cell === "T" && !triggeredTraps.has(nk)) {
          weight = 1.0 + trapStepCost;
        }
        var nd = d + weight;
        if (nd < (dist[nk] !== undefined ? dist[nk] : Infinity)) {
          dist[nk] = nd;
          prev[nk] = cur;
          heap.push([nd, next]);
        }
      }
    }

    return { dist: dist, prev: prev };
  }

  function extractPathFog(prev, start, goal) {
    var gk = keyOf(goal);
    if (!(gk in prev)) return null;
    var path = [];
    var cur = goal;
    while (cur) {
      path.push(cur);
      var ck = keyOf(cur);
      cur = prev[ck];
    }
    path.reverse();
    return path;
  }

  // ============================================================
  // Boss battle simulation (port of boss.js buildFrames combat logic)
  // Deterministic, no animation — returns { won, coinsAfter }
  // ============================================================
  function runBossBattle(bossHpList, rawSkills, minRounds, coinConsumption, startingCoins) {
    var coins = startingCoins;
    var skills = rawSkills.map(function (pair) {
      return { damage: pair[0], cooldown: pair[1], remainingCd: 0 };
    });

    for (var b = 0; b < bossHpList.length; b++) {
      var bossHp = bossHpList[b];

      while (bossHp > 0 && coins >= 0) {
        // One attempt: up to minRounds rounds
        for (var attackRound = 1; attackRound <= minRounds; attackRound++) {
          // Greedy: pick highest-damage available skill
          var bestIdx = null;
          var bestDamage = -1;
          for (var si = 0; si < skills.length; si++) {
            if (skills[si].remainingCd === 0 && skills[si].damage > bestDamage) {
              bestDamage = skills[si].damage;
              bestIdx = si;
            }
          }

          if (bestIdx !== null) {
            bossHp -= skills[bestIdx].damage;
            skills[bestIdx].remainingCd = skills[bestIdx].cooldown;
          }

          // Tick cooldowns
          for (var si2 = 0; si2 < skills.length; si2++) {
            if (skills[si2].remainingCd > 0) skills[si2].remainingCd -= 1;
          }

          if (bossHp <= 0) break;
        }

        if (bossHp > 0) {
          // Ran out of minRounds — deduct coins and retry
          coins -= coinConsumption;
          if (coins < 0) {
            return { won: false, coinsAfter: Math.max(0, coins + coinConsumption) };
          }
          // Reset skills for retry
          for (var si3 = 0; si3 < skills.length; si3++) {
            skills[si3].remainingCd = 0;
          }
        }
      }
    }

    return { won: true, coinsAfter: coins };
  }

  // ============================================================
  // Algorithm A: simulateLocalGreedy
  // Port of agents/local_greedy_policy.py — LocalGreedyAgent
  //
  // Core logic:
  //   1. Scan 3x3 window (8 neighbors)
  //   2. Score each neighbor with _cell_score() formula
  //   3. Pick highest positive score → move one step
  //   4. No positive score → STAY (stuck counter)
  //   5. Only uses fog_map (FOG constraint)
  // ============================================================

  function cellScoreA(r, c, fogMap, triggeredTraps, dist, visited, prevPos, cfg) {
    var cell = fogMap[r][c];

    // Raw game value (port of _cell_score lines 197-205)
    var rawValue = 0.0;
    if (cell === "C" || cell === "G") {
      rawValue = cfg.coin_value;          // +50
    } else if (cell === "T" && !triggeredTraps.has(keyOf({ r: r, c: c }))) {
      rawValue = -cfg.trap_penalty;        // -30 (triggered traps don't repeat)
    }
    // cell === null won't reach here (handled in score3x3)

    // Movement opportunity cost: dist * step_cost (line 209)
    var movementCost = dist * cfg.step_cost;

    // Score = (raw_value - movement_cost) / dist (line 214)
    var score = (rawValue - movementCost) / dist;

    // Penalty corrections (lines 217-221, absolute, NOT divided by dist)
    if (visited && visited.has(keyOf({ r: r, c: c }))) {
      score -= cfg.visited_penalty;
    }
    if (prevPos && r === prevPos.r && c === prevPos.c) {
      score -= cfg.w_backtrack;
    }

    return score;
  }

  function score3x3(r, c, fogMap, triggeredTraps, visited, prevPos, cfg) {
    // Port of _score_3x3 (lines 99-160)
    var results = [];

    for (var dr = -1; dr <= 1; dr++) {
      for (var dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        var nr = r + dr;
        var nc = c + dc;
        if (nr < 0 || nc < 0 || nr >= fogMap.length || nc >= fogMap[0].length) continue;

        var dist = Math.abs(dr) + Math.abs(dc);  // 1 or 2

        if (dist === 1) {
          // Direct neighbor: walkable OR unexplored (fogMap=null) included (line 134-147)
          var cell = fogMap[nr][nc];
          if (cell === null) {
            // Unexplored direct neighbor: explore_bonus only (line 138-143)
            var escore = cfg.explore_bonus;
            if (prevPos && nr === prevPos.r && nc === prevPos.c) {
              escore -= cfg.w_backtrack;
            }
            results.push([{ r: nr, c: nc }, escore]);
            continue;
          } else if (!isWalkableFog(cell)) {
            continue;  // Known wall (line 145-146)
          }
        } else {
          // Diagonal (dist=2): must be actually walkable (line 149-155)
          if (!isWalkableFog(fogMap[nr][nc])) continue;
          var mid1 = fogMap[r][nc];
          var mid2 = fogMap[nr][c];
          if (!isWalkableFog(mid1) && !isWalkableFog(mid2)) continue;
        }

        var score = cellScoreA(nr, nc, fogMap, triggeredTraps, dist, visited, prevPos, cfg);
        results.push([{ r: nr, c: nc }, score]);
      }
    }

    return results;
  }

  function firstStepA(r, c, target, fogMap) {
    // Port of _first_step (lines 239-268)
    var tr = target.r;
    var tc = target.c;
    var dist = Math.abs(tr - r) + Math.abs(tc - c);

    if (dist === 1) {
      return target;  // Direct neighbor, step directly
    }

    // Diagonal: find walkable intermediate cell (lines 261-266)
    var candidates = [{ r: r, c: tc }, { r: tr, c: c }];
    for (var i = 0; i < candidates.length; i++) {
      var mid = candidates[i];
      if (mid.r >= 0 && mid.c >= 0 && mid.r < fogMap.length && mid.c < fogMap[0].length &&
          isWalkableFog(fogMap[mid.r][mid.c])) {
        return mid;  // Step to intermediate cell
      }
    }

    return null;  // Both intermediate cells are walls
  }

  function simulateLocalGreedy(data) {
    var rows = data.maze.length;
    var cols = data.maze[0].length;
    var groundTruth = cloneGrid(data.maze);
    var fogMap = initFogMap(rows, cols);
    var viewRadius = 1;

    var pos = findStartPos(groundTruth);
    if (!pos) return { frames: [], route: [], score: 0, totalSteps: 0, totalValue: 0 };

    var coins = 0;
    var triggeredTraps = new Set();
    var visited = new Set();
    var prevPos = null;
    var frames = [];
    var bossDefeated = 0;
    var bossHpList = Array.isArray(data.B) ? data.B.slice() : [];
    var allBossesDefeated = bossHpList.length === 0;
    var stuckCount = 0;
    var cfg = ALGO_A_CONFIG;

    visited.add(keyOf(pos));

    for (var step = 0; step < COMPARE_MAX_STEPS; step++) {
      var currentCell = groundTruth[pos.r][pos.c];
      var event = "";
      var phase = "Exploring";
      var bossEncounter = null;

      // Record frame (fog state BEFORE scoring this step)
      var revealedSet2 = getRevealedSet(fogMap);
      frames.push({
        round: step, pos: { r: pos.r, c: pos.c }, coins: coins,
        bossCount: bossDefeated, phase: phase, event: event,
        sourceCell: data.maze[pos.r][pos.c],
        bossEncounter: bossEncounter,
        grid: cloneGrid(groundTruth), revealed: new Set(revealedSet2),
        heat: [], exploredRatio: revealedSet2.size / (rows * cols),
      });

      // Handle current cell (coin / trap / boss / exit)
      if (step > 0) {
        if (currentCell === "C" || currentCell === "G") {
          coins += COIN_VALUE;
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
          event = "Collected coin, coins +" + COIN_VALUE;
          phase = "Resource Collect";
        } else if (currentCell === "T" && !triggeredTraps.has(keyOf(pos))) {
          coins -= TRAP_DAMAGE;
          triggeredTraps.add(keyOf(pos));
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
          event = "Trap triggered, coins -" + TRAP_DAMAGE;
          phase = "Risk Handling";
        } else if (currentCell === "B" && bossHpList.length > 0) {
          var bossHp = bossHpList.shift();
          var battleResult = runBossBattle(
            [bossHp],
            data.PlayerSkills || [[8, 4], [2, 0], [4, 2], [6, 3]],
            data.minRouds || 20,
            data.CoinConsumption || 5,
            coins
          );
          coins = battleResult.coinsAfter;
          if (battleResult.won) {
            bossDefeated += 1;
            bossEncounter = { bossIndex: bossDefeated, bossTotal: (Array.isArray(data.B) ? data.B.length : 0) };
            event = "Boss " + bossDefeated + " defeated";
            phase = "Boss Combat";
            if (bossHpList.length === 0) allBossesDefeated = true;
          } else {
            event = "Boss combat failed, coins remaining " + coins;
            phase = "Boss Combat";
          }
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
        } else if (currentCell === "E" && allBossesDefeated) {
          frames[frames.length - 1].event = "Reached exit";
          frames[frames.length - 1].phase = "Complete";
          break;
        }
        // Update the frame we just recorded with the event/phase from cell handling
        if (event) frames[frames.length - 1].event = event;
        if (phase !== "Exploring") frames[frames.length - 1].phase = phase;
        if (bossEncounter) frames[frames.length - 1].bossEncounter = bossEncounter;
        // Also update coins and bossCount on the frame after cell handling
        frames[frames.length - 1].coins = coins;
        frames[frames.length - 1].bossCount = bossDefeated;
        // Update grid to reflect cell changes
        frames[frames.length - 1].grid = cloneGrid(groundTruth);
      }

      // Check exit
      if (currentCell === "E" && allBossesDefeated) break;

      // Score 3x3 and decide next move (BEFORE revealing — so unexplored cells
      // at the edge of the fog still get explore_bonus)
      var candidates = score3x3(pos.r, pos.c, fogMap, triggeredTraps, visited, prevPos, cfg);
      candidates.sort(function (a, b) { return b[1] - a[1]; });

      var moved = false;
      var usedFallback = false;
      // Phase 1: try positive-score candidates (explore / collect)
      for (var ci = 0; ci < candidates.length; ci++) {
        var target = candidates[ci][0];
        var candidateScore = candidates[ci][1];
        if (candidateScore <= 0) break;
        var first = firstStepA(pos.r, pos.c, target, fogMap);
        if (first && first.r >= 0 && first.r < rows && first.c >= 0 && first.c < cols
            && groundTruth[first.r][first.c] !== "#") {
          prevPos = { r: pos.r, c: pos.c };
          pos = first;
          visited.add(keyOf(first));
          moved = true;
          break;
        }
      }
      // Phase 2: no positive candidate worked → pick the best available
      // (least-negative) walkable neighbor. This prevents the agent from
      // getting permanently stuck at dead ends in standalone mode.
      // In the Python ecosystem, the CompositeAgent would switch to
      // GlobalPlanner here; standalone, we force backtracking.
      if (!moved) {
        for (var cj = 0; cj < candidates.length; cj++) {
          var ftarget = candidates[cj][0];
          var ffirst = firstStepA(pos.r, pos.c, ftarget, fogMap);
          if (ffirst && ffirst.r >= 0 && ffirst.r < rows && ffirst.c >= 0 && ffirst.c < cols
              && groundTruth[ffirst.r][ffirst.c] !== "#") {
            prevPos = { r: pos.r, c: pos.c };
            pos = ffirst;
            visited.add(keyOf(ffirst));
            moved = true;
            usedFallback = true;
            break;
          }
        }
      }

      if (!moved) {
        stuckCount += 1;
        if (stuckCount >= COMPARE_MAX_STUCK) break;
      } else if (usedFallback) {
        // Consecutive fallback moves = effectively stuck (just going in circles)
        stuckCount += 1;
        if (stuckCount >= COMPARE_MAX_STUCK) break;
      } else {
        stuckCount = 0;
      }

      // Reveal 3x3 around PREVIOUS position (where the agent LEFT).
      // This creates unexplored cells at the forward edge of the fog so that
      // the next scoring still has unexplored neighbors to trigger explore_bonus.
      // Matches Python LocalSimulator where _reveal_fov happens in _finish_maze_step
      // (after the move), but the key difference is we reveal at the OLD position
      // so the 8-neighbor scoring window extends beyond the revealed area.
      var revealTarget = prevPos || pos;
      revealFog(fogMap, groundTruth, revealTarget, viewRadius);
    }

    var totalSteps = frames.length;
    var totalValue = coins;
    var score = totalSteps > 0 ? totalValue / totalSteps : 0;

    return {
      frames: frames, route: frames.map(function (f) { return f.pos; }),
      score: score, totalSteps: totalSteps, totalValue: totalValue,
      coins: coins, bossDefeated: bossDefeated,
    };
  }

  // ============================================================
  // Algorithm B: simulateGlobalGreedy
  // Port of agents/global_greedy.py — GlobalGreedyAgent
  //
  // Core logic:
  //   1. Maintain fog_map (all revealed cells)
  //   2. Each step: Dijkstra from current pos through known walkable cells
  //   3. Enumerate all candidates (coins / frontiers / boss / exit) in fog_map
  //   4. Score each: value / path_cost - revisit_penalty
  //   5. Take first step of best path, re-evaluate next turn
  // ============================================================

  function scanBossesB(fogMap) {
    var known = [];
    for (var r = 0; r < fogMap.length; r++) {
      for (var c = 0; c < fogMap[0].length; c++) {
        if (fogMap[r][c] === "B") {
          known.push({ r: r, c: c });
        }
      }
    }
    return known;
  }

  function findFrontiersB(fogMap) {
    // Port of _find_frontiers (lines 193-201)
    var frontiers = [];
    var dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    for (var r = 0; r < fogMap.length; r++) {
      for (var c = 0; c < fogMap[0].length; c++) {
        if (!isWalkableFog(fogMap[r][c])) continue;
        for (var d = 0; d < dirs.length; d++) {
          var nr = r + dirs[d][0];
          var nc = c + dirs[d][1];
          if (nr >= 0 && nc >= 0 && nr < fogMap.length && nc < fogMap[0].length) {
            if (fogMap[nr][nc] === null) {
              frontiers.push({ r: r, c: c });
              break;
            }
          }
        }
      }
    }
    return frontiers;
  }

  function countUnknownNeighborsB(fogMap, pos) {
    // Port of _count_unknown_neighbors (lines 203-204)
    var count = 0;
    var dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
    for (var d = 0; d < dirs.length; d++) {
      var nr = pos.r + dirs[d][0];
      var nc = pos.c + dirs[d][1];
      if (nr >= 0 && nc >= 0 && nr < fogMap.length && nc < fogMap[0].length) {
        if (fogMap[nr][nc] === null) count += 1;
      }
    }
    return count;
  }

  function exploredRatioB(fogMap) {
    // Port of _explored_ratio (lines 206-214)
    var total = fogMap.length * fogMap[0].length;
    var explored = 0;
    for (var r = 0; r < fogMap.length; r++) {
      for (var c = 0; c < fogMap[0].length; c++) {
        if (fogMap[r][c] !== null) explored += 1;
      }
    }
    return total ? explored / total : 0;
  }

  function shouldForceCollectB(knownBosses, coins, coinConsumption, cfg) {
    // Port of _should_force_collect (lines 175-179)
    if (!knownBosses.length) return false;
    var need = Math.max(coinConsumption * cfg.target_retry_buffer, coinConsumption);
    return coins < need;
  }

  function scoreBossTargetB(distanceCost, coins, knownBosses, fogMap, coinConsumption, cfg) {
    // Port of _score_boss_target (lines 156-173)
    if (!knownBosses.length) return -1e9;

    var need = Math.max(coinConsumption * cfg.target_retry_buffer, coinConsumption);
    var exploredRatio = exploredRatioB(fogMap);
    var ready = coins >= need;

    var base = cfg.boss_value / Math.max(distanceCost, 1.0);
    if (ready) {
      base += 40.0;
    } else {
      base -= Math.max(0, need - coins);
    }

    if (exploredRatio < cfg.min_explore_before_boss && !ready) {
      base -= 25.0;
    }
    return base;
  }

  function enumerateCandidatesB(fogMap, pos, triggeredTraps, visitCount, coins, cfg, data, allBossesDefeated, knownBosses) {
    // Port of _enumerate_candidates (lines 94-154)

    // Run Dijkstra from current position (with trap weighting)
    var dijkstraResult = dijkstraFog(fogMap, pos, triggeredTraps, cfg.trap_step_cost);
    var dist = dijkstraResult.dist;
    var prev = dijkstraResult.prev;

    var candidates = [];

    // Scan all revealed cells for coin / boss / exit targets
    for (var r = 0; r < fogMap.length; r++) {
      for (var c = 0; c < fogMap[0].length; c++) {
        var cell = fogMap[r][c];
        var target = { r: r, c: c };
        var tk = keyOf(target);
        if (cell === null || (r === pos.r && c === pos.c)) continue;
        if (!(tk in dist)) continue;

        var path = extractPathFog(prev, pos, target);
        if (!path || path.length < 2) continue;
        var movePath = path.slice(1);  // exclude start position
        if (!movePath.length) continue;

        var distanceCost = dist[tk];
        var revisitPenalty = cfg.revisit_penalty * (visitCount[tk] || 0);

        if (cell === "C" || cell === "G") {
          // Coin target (lines 127-131)
          var coinScore = cfg.coin_value / Math.max(distanceCost, 1.0) - revisitPenalty;
          if (shouldForceCollectB(knownBosses, coins, data.CoinConsumption || 5, cfg)) {
            coinScore += 20.0;
          }
          candidates.push(["coin", target, coinScore, movePath]);
        } else if (cell === "B") {
          // Boss target (lines 132-134)
          var bossScore = scoreBossTargetB(distanceCost, coins, knownBosses, fogMap, data.CoinConsumption || 5, cfg) - revisitPenalty;
          candidates.push(["boss", target, bossScore, movePath]);
        } else if (cell === "E" && allBossesDefeated) {
          // Exit target (lines 135-137)
          var exitScore = cfg.exit_value / Math.max(distanceCost, 1.0);
          candidates.push(["exit", target, exitScore, movePath]);
        }
      }
    }

    // Frontier targets (lines 139-152)
    var frontiers = findFrontiersB(fogMap);
    for (var fi = 0; fi < frontiers.length; fi++) {
      var frontier = frontiers[fi];
      var fk = keyOf(frontier);
      if (frontier.r === pos.r && frontier.c === pos.c) continue;
      if (!(fk in dist)) continue;

      var fpath = extractPathFog(prev, pos, frontier);
      if (!fpath || fpath.length < 2) continue;
      var fmovePath = fpath.slice(1);
      if (!fmovePath.length) continue;

      var fdistanceCost = dist[fk];
      var unknownCount = countUnknownNeighborsB(fogMap, frontier);
      var rawValue = cfg.frontier_value + cfg.frontier_unknown_weight * unknownCount;
      var frontierScore = rawValue / Math.max(fdistanceCost, 1.0) - cfg.revisit_penalty * (visitCount[fk] || 0);
      candidates.push(["frontier", frontier, frontierScore, fmovePath]);
    }

    return candidates;
  }

  function simulateGlobalGreedy(data) {
    var rows = data.maze.length;
    var cols = data.maze[0].length;
    var groundTruth = cloneGrid(data.maze);
    var fogMap = initFogMap(rows, cols);
    var viewRadius = 1;

    var pos = findStartPos(groundTruth);
    if (!pos) return { frames: [], route: [], score: 0, totalSteps: 0, totalValue: 0 };

    var coins = 0;
    var triggeredTraps = new Set();
    var visitCount = {};
    var frames = [];
    var bossDefeated = 0;
    var bossHpList = Array.isArray(data.B) ? data.B.slice() : [];
    var allBossesDefeated = bossHpList.length === 0;
    var stuckCount = 0;
    var cfg = ALGO_B_CONFIG;

    // Initial reveal at start position so the first frame shows something
    revealFog(fogMap, groundTruth, pos, viewRadius);
    visitCount[keyOf(pos)] = 1;

    var knownBosses = [];

    for (var step = 0; step < COMPARE_MAX_STEPS; step++) {
      // ── Step A: Reveal 3×3 at current position FIRST ──────────
      // This must happen BEFORE frame recording so the viewer sees
      // exactly what the agent knows — no "hidden" knowledge.
      // (For step 0 this is redundant with the initial reveal above.)
      revealFog(fogMap, groundTruth, pos, viewRadius);

      // ── Step B: Handle current cell (coin / trap / boss / exit) ─
      var currentCell = groundTruth[pos.r][pos.c];
      var event = "";
      var phase = "Exploring";
      var bossEncounter = null;

      if (step > 0) {
        if (currentCell === "C" || currentCell === "G") {
          coins += COIN_VALUE;
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
          event = "Collected coin, coins +" + COIN_VALUE;
          phase = "Resource Collect";
        } else if (currentCell === "T" && !triggeredTraps.has(keyOf(pos))) {
          coins -= TRAP_DAMAGE;
          triggeredTraps.add(keyOf(pos));
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
          event = "Trap triggered, coins -" + TRAP_DAMAGE;
          phase = "Risk Handling";
        } else if (currentCell === "B" && bossHpList.length > 0) {
          var bossHp = bossHpList.shift();
          var battleResult = runBossBattle(
            [bossHp],
            data.PlayerSkills || [[8, 4], [2, 0], [4, 2], [6, 3]],
            data.minRouds || 20,
            data.CoinConsumption || 5,
            coins
          );
          coins = battleResult.coinsAfter;
          if (battleResult.won) {
            bossDefeated += 1;
            bossEncounter = { bossIndex: bossDefeated, bossTotal: (Array.isArray(data.B) ? data.B.length : 0) };
            event = "Boss " + bossDefeated + " defeated";
            phase = "Boss Combat";
            if (bossHpList.length === 0) allBossesDefeated = true;
          } else {
            event = "Boss combat failed, coins remaining " + coins;
            phase = "Boss Combat";
          }
          groundTruth[pos.r][pos.c] = " ";
          fogMap[pos.r][pos.c] = " ";
        } else if (currentCell === "E" && allBossesDefeated) {
          // Record final frame before breaking
          var revealedSetE = getRevealedSet(fogMap);
          frames.push({
            round: step, pos: { r: pos.r, c: pos.c }, coins: coins,
            bossCount: bossDefeated, phase: "Complete", event: "Reached exit",
            sourceCell: "E", bossEncounter: null,
            grid: cloneGrid(groundTruth), revealed: new Set(revealedSetE),
            heat: [], exploredRatio: revealedSetE.size / (rows * cols),
          });
          break;
        }
      }

      // ── Step C: Record frame (fog ALREADY expanded by Step A) ──
      var revealedSet2 = getRevealedSet(fogMap);
      frames.push({
        round: step, pos: { r: pos.r, c: pos.c }, coins: coins,
        bossCount: bossDefeated, phase: phase, event: event,
        sourceCell: data.maze[pos.r][pos.c],
        bossEncounter: bossEncounter,
        grid: cloneGrid(groundTruth), revealed: new Set(revealedSet2),
        heat: [], exploredRatio: revealedSet2.size / (rows * cols),
      });

      // Update frame with cell-handling results (coins/phase/grid may have changed)
      if (event) frames[frames.length - 1].event = event;
      if (phase !== "Exploring") frames[frames.length - 1].phase = phase;
      if (bossEncounter) frames[frames.length - 1].bossEncounter = bossEncounter;
      frames[frames.length - 1].coins = coins;
      frames[frames.length - 1].bossCount = bossDefeated;
      frames[frames.length - 1].grid = cloneGrid(groundTruth);

      if (currentCell === "E" && allBossesDefeated) break;

      // ── Step D: Score, decide, move ──────────────────────────
      // Scan known bosses in fog_map (port of _scan_bosses)
      knownBosses = scanBossesB(fogMap);

      // Mark current visit (port of _mark_current_visit)
      var pk = keyOf(pos);
      visitCount[pk] = (visitCount[pk] || 0) + 1;

      // Enumerate candidates
      var candidates = enumerateCandidatesB(fogMap, pos, triggeredTraps, visitCount, coins, cfg, data, allBossesDefeated, knownBosses);

      // ── DEBUG: log agent knowledge each step ─────────────────
      if (window.DEBUG_ALGO_B) {
        var revealedCount = 0;
        for (var drr = 0; drr < rows; drr++) {
          for (var dcc = 0; dcc < cols; dcc++) {
            if (fogMap[drr][dcc] !== null) revealedCount++;
          }
        }
        console.group("Step " + step + " | pos=(" + pos.r + "," + pos.c + ") | revealed=" + revealedCount + "/" + (rows*cols));
        // Print the top 5 candidates
        var sortedForDebug = candidates.slice().sort(function(a,b){return b[2]-a[2];});
        for (var di = 0; di < Math.min(5, sortedForDebug.length); di++) {
          var dc = sortedForDebug[di];
          console.log("  #" + (di+1) + " " + dc[0] + " @(" + dc[1].r + "," + dc[1].c + ") score=" + dc[2].toFixed(2) + " pathLen=" + (dc[3] ? dc[3].length : 0) + " path=" + JSON.stringify(dc[3]));
        }
        // Also log dijkstra dist for immediate neighbors
        var dj = dijkstraFog(fogMap, pos, triggeredTraps, cfg.trap_step_cost);
        var nbrs4 = [[-1,0],[1,0],[0,-1],[0,1]];
        for (var dni = 0; dni < nbrs4.length; dni++) {
          var nr = pos.r + nbrs4[dni][0], nc = pos.c + nbrs4[dni][1];
          if (nr >= 0 && nc >= 0 && nr < rows && nc < cols) {
            var nk = nr + "," + nc;
            var dval = (nk in dj.dist) ? dj.dist[nk].toFixed(1) : "unreachable";
            console.log("  Dijkstra neighbor (" + nr + "," + nc + ")=" + dval + " fog=" + (fogMap[nr][nc] === null ? "null" : fogMap[nr][nc]) + " GT=" + groundTruth[nr][nc]);
          }
        }
        // Print mini fog_map (only rows with revealed cells)
        var miniRows = [];
        for (var drr = 0; drr < rows; drr++) {
          var rowStr = "";
          var hasRevealed = false;
          for (var dcc = 0; dcc < cols; dcc++) {
            var c = fogMap[drr][dcc];
            if (c === null) { rowStr += "?"; }
            else if (c === "#") { rowStr += "#"; }
            else if (c === " ") { rowStr += "."; }
            else { rowStr += c; hasRevealed = true; }
            if (c !== null) hasRevealed = true;
          }
          if (hasRevealed) miniRows.push("  R" + drr + ": " + rowStr);
        }
        console.log(miniRows.join("\n"));
        // Print groundTruth for comparison (what SHOULD be at known positions)
        var gtRows = [];
        for (var drr = 0; drr < rows; drr++) {
          var hasGT = false;
          var rowStr = "";
          for (var dcc = 0; dcc < cols; dcc++) {
            if (fogMap[drr][dcc] !== null) {
              rowStr += groundTruth[drr][dcc];
              hasGT = true;
            } else {
              rowStr += "?";
            }
          }
          if (hasGT) gtRows.push("  GT" + drr + ": " + rowStr);
        }
        console.log(gtRows.join("\n"));
        // Print full groundTruth map for reference
        var fullGT = [];
        for (var drr = 0; drr < rows; drr++) {
          fullGT.push("  GT" + drr + ": " + JSON.stringify(groundTruth[drr]));
        }
        console.log("--- FULL GROUND TRUTH ---");
        console.log(fullGT.join("\n"));
        console.log("--- END ---");
        console.groupEnd();
      }

      if (!candidates.length) {
        stuckCount += 1;
        if (stuckCount >= COMPARE_MAX_STUCK) break;
        continue;
      }

      // Sort by score desc, pick best (port of decide() lines 81-84)
      candidates.sort(function (a, b) { return b[2] - a[2]; });
      var best = candidates[0];
      var bestPath = best[3];

      if (!bestPath || !bestPath.length) {
        stuckCount += 1;
        if (stuckCount >= COMPARE_MAX_STUCK) break;
        continue;
      }

      // Take first step of best path (port of line 92)
      pos = bestPath[0];
      stuckCount = 0;
    }

    var totalSteps = frames.length;
    var totalValue = coins;
    var score = totalSteps > 0 ? totalValue / totalSteps : 0;

    return {
      frames: frames, route: frames.map(function (f) { return f.pos; }),
      score: score, totalSteps: totalSteps, totalValue: totalValue,
      coins: coins, bossDefeated: bossDefeated,
    };
  }

  // ============================================================
  // Comparison runner & UI integration
  // ============================================================

  function runComparison() {
    if (!state.data) {
      alert("Please import or load a map first");
      return;
    }

    var data = state.data;
    var resultA, resultB;

    // Run Algorithm A (local 3x3 greedy)
    var startA = performance.now();
    resultA = simulateLocalGreedy(data);
    var timeA = performance.now() - startA;

    // Run Algorithm B (global memory-based greedy)
    var startB = performance.now();
    resultB = simulateGlobalGreedy(data);
    var timeB = performance.now() - startB;

    // Store results
    state.compareResult = {
      algoA: resultA,
      algoB: resultB,
      timeA: timeA,
      timeB: timeB,
      winner: resultA.score > resultB.score ? "A" : (resultB.score > resultA.score ? "B" : "tie"),
    };

    // Show results panel
    renderCompareResults(state.compareResult);
  }

  function renderCompareResults(cr) {
    var panel = document.getElementById("compareResults");
    if (!panel) return;

    var a = cr.algoA;
    var b = cr.algoB;
    var winnerA = cr.winner === "A";
    var winnerB = cr.winner === "B";

    panel.innerHTML =
      '<div class="compare-header">' +
        '<span class="compare-header-kicker">ALGORITHM ARENA</span>' +
        '<span class="compare-header-title">Algorithm Comparison</span>' +
        '<span class="compare-header-sub">Local Greedy <span class="diamond-sep">◆</span> Global Greedy</span>' +
      '</div>' +
      '<div class="compare-cards">' +
        buildCompareCard("A", "Algorithm A · Pure 3x3 Local Greedy", a, cr.timeA, winnerA, "Only sees 3x3 window, O(1)/step") +
        '<div class="compare-vs"><span>VS</span><i class="compare-vs-diamond"></i></div>' +
        buildCompareCard("B", "Algorithm B · Memory-Enhanced Global Greedy", b, cr.timeB, winnerB, "Dijkstra on all revealed tiles, O(R log R)/step") +
      '</div>' +
      '<div class="compare-actions">' +
        '<button class="secondary-btn" data-compare-view="A"><span class="compare-action-mark">◆</span>View Algo A Path</button>' +
        '<button class="secondary-btn" data-compare-view="B"><span class="compare-action-mark">◆</span>View Algo B Path</button>' +
        '<button class="secondary-btn" data-compare-view="original"><span class="compare-action-mark">◇</span>View Original Plan</button>' +
      '</div>';

    panel.hidden = false;

    var overlay = document.getElementById("compareOverlay");
    if (overlay) {
      overlay.hidden = false;
      overlay.classList.remove("is-visible");
      void overlay.offsetWidth;
      overlay.classList.add("is-visible");
    }
  }

  function buildCompareCard(letter, title, result, timeMs, isWinner, desc) {
    var winnerClass = isWinner ? " compare-winner" : "";
    var letterClass = " compare-card-" + letter.toLowerCase();
    var winnerBadge = isWinner ? '<span class="compare-badge"><i></i>WINNER</span>' : "";
    var scoreFormatted = result.score.toFixed(2);

    return (
      '<div class="compare-card' + winnerClass + letterClass + '">' +
        '<div class="compare-card-head">' +
          '<span class="compare-card-letter">' + letter + '</span>' +
          '<div class="compare-card-titles">' +
            '<div class="compare-card-title">' + title + '</div>' +
            '<div class="compare-card-desc">' + desc + '</div>' +
          '</div>' +
          winnerBadge +
        '</div>' +
        '<div class="compare-metrics">' +
          '<div class="compare-metric"><span>总分/总步数</span><strong>' + scoreFormatted + '</strong></div>' +
          '<div class="compare-metric"><span>总步数</span><strong>' + result.totalSteps + '</strong></div>' +
          '<div class="compare-metric"><span>Final Coins</span><strong>' + result.coins + '</strong></div>' +
          '<div class="compare-metric"><span>Bosses Defeated</span><strong>' + (result.bossDefeated || 0) + '</strong></div>' +
          '<div class="compare-metric compare-metric-wide"><span>耗时</span><strong>' + timeMs.toFixed(0) + ' ms</strong></div>' +
        '</div>' +
      '</div>'
    );
  }

  // Expose view-algo switcher to window so onclick works
  window._viewAlgo = function (mode) {
    if (!state.compareResult) return;
    stopPlayback();

    var result, label;
    if (mode === "A") {
      result = state.compareResult.algoA;
      label = "算法 A (纯 3×3)";
    } else if (mode === "B") {
      result = state.compareResult.algoB;
      label = "算法 B (记忆增强)";
    } else {
      // Rebuild original route
      if (!state._originalFrames) {
        var origResult = createFrames(state.data);
        state._originalFrames = origResult.frames;
        state._originalRoute = origResult.route;
      }
      state.frames = state._originalFrames;
      state.route = state._originalRoute;
      label = "Original Plan";
    }

    if (mode === "A" || mode === "B") {
      state.frames = result.frames;
      state.route = result.route;
    }
    state.frameIndex = 0;
    state.grid = cloneGrid(state.data.maze);
    clearTrapHideState();
    clearBossAlert();
    clearBossOverlayCloseTimer();
    clearBossWinAlert();
    clearEffects();
    els.timeline.max = String(Math.max(0, state.frames.length - 1));
    els.timeline.value = "0";
    els.metricRoute.textContent = state.route.length ? String(state.route.length - 1) : "0";
    els.mapName.textContent = (els.mapName.textContent || "").replace(/ \| .*$/, "") + " | " + label;
    updateUi();
    fitCanvas();
    draw();
  };

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
    state.compareResult = null;
    state._originalFrames = null;
    state._originalRoute = null;
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
    showActors();
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
      throw new Error("Maze must contain start S and exit E");
    }
  }

  async function loadDefaultMap() {
    if (window.location.protocol === "file:") {
      initMap(JSON.parse(JSON.stringify(DEFAULT_MAP_DATA)), "Built-in example map");
      els.mapMeta.textContent += " (local file mode)";
      return;
    }

    for (const file of MAP_FILE_LIST) {
      try {
        const url = MAP_DIR + file;
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) continue;
        const data = await response.json();
        initMap(data, file);
        return;
      } catch (error) {
        console.warn("Map candidate failed: " + url, error);
      }
    }

    console.warn("No map files found; using embedded map.");
    initMap(JSON.parse(JSON.stringify(DEFAULT_MAP_DATA)), "Built-in example map");
    els.mapMeta.textContent += " (local file mode)";
  }

  function populateMapSelector() {
    var trigger = document.getElementById("mapSelectorTrigger");
    if (!trigger) return;
    trigger.addEventListener("click", function () {
      els.fileInput.click();
    });
  }

  function initSidebars() {
    var leftTab = document.getElementById("sidebarLeftTab");
    var leftBar = document.getElementById("sidebarLeft");
    var rightTab = document.getElementById("sidebarRightTab");
    var rightBar = document.getElementById("sidebarRight");

    if (leftTab && leftBar) {
      leftTab.addEventListener("click", function (e) {
        e.stopPropagation();
        leftBar.classList.toggle("open");
        if (rightBar) rightBar.classList.remove("open");
      });
    }
    if (rightTab && rightBar) {
      rightTab.addEventListener("click", function (e) {
        e.stopPropagation();
        rightBar.classList.toggle("open");
        if (leftBar) leftBar.classList.remove("open");
      });
    }
    document.addEventListener("click", function () {
      if (leftBar) leftBar.classList.remove("open");
      if (rightBar) rightBar.classList.remove("open");
    });
    if (leftBar) {
      leftBar.addEventListener("click", function (e) { e.stopPropagation(); });
    }
    if (rightBar) {
      rightBar.addEventListener("click", function (e) { e.stopPropagation(); });
    }
  }

  function initEmptyState() {
    stopPlayback();
    state.animPlayerX = null;
    state.animPlayerY = null;
    state.animProgress = null;
    state.animToFrame = null;
    state.animRafId = null;
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
    els.introMeta.textContent = "Select a map to begin";
    els.mapName.textContent = "No map imported";
    els.runState.textContent = "Awaiting import";
    els.metricRound.textContent = "0";
    els.metricCoins.textContent = "0";
    els.metricExplored.textContent = "0%";
    els.metricRoute.textContent = "0";
    els.phaseLabel.textContent = "Awaiting map import";
    els.cellReadout.textContent = "Select a map file";
    els.timeline.max = "0";
    els.timeline.value = "0";
    els.mapMeta.textContent = "Please select a JSON map to begin.";
    try {
      window.localStorage.removeItem(ACTIVE_MAP_CACHE_KEY);
    } catch (error) {
      console.warn("Failed to clear active map cache.", error);
    }
    updateTileInfo(null);
    els.cellReadout.textContent = "Select a map file";
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
    els.introMeta.textContent = `${name} / Coins ${coinCells} / Traps ${trapCells} / Skills ${Array.isArray(data.PlayerSkills) ? data.PlayerSkills.length : 0}`;
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
    return "";
  }

  function fitCanvas() {
    var dpr = window.devicePixelRatio || 1;
    // Read actual rendered CSS size of the canvas (works even when parent has opacity:0)
    var rectW = els.canvas.clientWidth;
    var rectH = els.canvas.clientHeight;

    // Fallback if clientWidth/Height is 0 (e.g. element not in layout yet)
    if (!rectW || !rectH) {
      var topH = 50;
      var bottomH = 50;
      var topEl = document.querySelector(".topbar-area");
      var bottomEl = document.querySelector(".bottombar-area");
      if (topEl) topH = topEl.getBoundingClientRect().height || 50;
      if (bottomEl) bottomH = bottomEl.getBoundingClientRect().height || 50;
      rectW = Math.max(400, window.innerWidth - 20);
      rectH = Math.max(400, window.innerHeight - topH - bottomH - 10);
    }

    var w = rectW;
    var h = rectH;

    var targetWidth = Math.floor(w * dpr);
    var targetHeight = Math.floor(h * dpr);
    // Only mutate canvas internal size when it actually changes — resetting wipes the context
    if (els.canvas.width !== targetWidth || els.canvas.height !== targetHeight) {
      els.canvas.width = targetWidth;
      els.canvas.height = targetHeight;
    }

    state.layout.dpr = dpr;
    state.layout.width = els.canvas.width;
    state.layout.height = els.canvas.height;

    if (state.grid.length) {
      var rows = state.grid.length;
      var cols = state.grid[0].length;
      var pad = Math.max(8, Math.min(w, h) * 0.02);
      var tilePx = Math.floor(Math.min((w - pad * 2) / cols, (h - pad * 2) / rows));
      if (tilePx < 2) tilePx = 2;
      state.layout.tile = tilePx * dpr;
      state.layout.originX = Math.floor((w * dpr - state.layout.tile * cols) / 2);
      state.layout.originY = Math.floor((h * dpr - state.layout.tile * rows) / 2);
    }

  }

  function currentFrame() {
    return state.frames[state.frameIndex] || null;
  }

  function shouldReveal(frame, r, c) {
    if (!state.showFog || state.mode === "full") return true;
    if (!frame) return false;
    return frame.revealed.has(`${r},${c}`);
  }

  function draw() {
    try {
      fitCanvas();
      ctx.clearRect(0, 0, state.layout.width, state.layout.height);

      if (!state.grid.length) {
        drawEmptyState("Please import a JSON map to begin");
        return;
      }

      var frame = currentFrame();
      var cellFrame = state.animToFrame || frame;
      drawBoardBackground();
      drawCells(cellFrame);
      if (cellFrame && state.showFog && state.mode !== "full") drawFogEdges(cellFrame);
      if (state.showPath && state.route.length > 1) drawPath(frame);
      drawFocus(frame);
      drawEffects(frame);
      drawHover();
      drawPaperGrain();
    } catch (e) {
      console.warn("Draw error:", e);
    }
  }

  function drawEmptyState(message) {
    fitCanvas();
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "rgba(6,5,10,0.85)";
    ctx.fillRect(0, 0, state.layout.width, state.layout.height);
    ctx.fillStyle = "#7a7590";
    ctx.font = `${14 * state.layout.dpr}px "Courier New", monospace`;
    ctx.textAlign = "center";
    ctx.fillText(message, state.layout.width / 2, state.layout.height / 2);
  }

  function drawBoardBackground() {
    var rows = state.grid.length;
    var cols = state.grid[0].length;
    var tile = state.layout.tile;
    var ox = state.layout.originX;
    var oy = state.layout.originY;
    // Clear to transparent so CSS deep-space background shows through
    ctx.clearRect(0, 0, state.layout.width, state.layout.height);
    if (!tile) return;
    // Warm paper grain dots at every cell center (sumi-e style)
    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        var cx = ox + c * tile + tile/2;
        var cy = oy + r * tile + tile/2;
        ctx.fillStyle = 'rgba(170, 160, 150, 0.065)';
        ctx.fillRect(cx - 0.5, cy - 0.5, 1, 1);
      }
    }
  }

  function drawCells(frame) {
    const rows = state.grid.length;
    const cols = state.grid[0].length;
    const visibleGrid = frame ? frame.grid : state.grid;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const revealed = shouldReveal(frame, r, c);
        const trapHidden = state.hiddenTraps.has(`${r},${c}`);
        const cell = revealed ? (trapHidden ? " " : visibleGrid[r][c]) : null;
        drawTile(r, c, cell, frame);
      }
    }
  }

  // ============================================================
  // Watercolor / Sumi-e ink-wash helpers (Gris + Okami style)
  // ============================================================
  function cellRand(r, c, seed) {
    var n = Math.sin(r * 12.9898 + c * 78.233 + seed * 43.123) * 43758.5453;
    return n - Math.floor(n);
  }
  function inkWash(x, y, w, h, cx, cy, r0, r1, stops) {
    var grad = ctx.createRadialGradient(cx, cy, r0, cx, cy, r1);
    stops.forEach(function(s) { grad.addColorStop(s[0], s[1]); });
    ctx.fillStyle = grad;
    ctx.fillRect(x, y, w, h);
  }

  function drawTile(r, c, cell, frame) {
    const { originX, originY, tile, dpr } = state.layout;
    const x = originX + c * tile;
    const y = originY + r * tile;

    if (cell === null) {
      // Fog — dark paper with faint grain dot only
      var fcx = x + tile/2, fcy = y + tile/2;
      var grain = ctx.createRadialGradient(fcx, fcy, 0, fcx, fcy, tile*0.08);
      grain.addColorStop(0, 'rgba(180, 170, 160, 0.04)');
      grain.addColorStop(1, 'rgba(180, 170, 160, 0)');
      ctx.fillStyle = grain;
      ctx.fillRect(x + tile*0.35, y + tile*0.35, tile*0.3, tile*0.3);
      return;
    }

    // Organic offset for watercolor bleeding (deterministic per cell)
    var offX = (cellRand(r, c, 1) - 0.5) * tile * 0.35;
    var offY = (cellRand(r, c, 2) - 0.5) * tile * 0.35;
    var bleed = tile * 0.75; // how far color bleeds past cell edge

    if (cell === "#") {
      // Wall — continuous watercolor block with smooth organic color variation
      // Smooth global gradient across the entire wall mass
      var rows = state.grid.length, cols = state.grid[0].length;
      var nx = c / Math.max(1, cols - 1); // 0 ~ 1 left-to-right
      var ny = r / Math.max(1, rows - 1); // 0 ~ 1 top-to-bottom
      var br = 60 + nx * 70 + ny * 30;
      var bg = 55 + nx * 40 + ny * 50;
      var bb = 95 + nx * 55 + ny * 45;
      ctx.fillStyle = 'rgba(' + (br|0) + ',' + (bg|0) + ',' + (bb|0) + ',0.95)';
      ctx.fillRect(x - 0.5, y - 0.5, tile + 1, tile + 1);


    } else {
      // Floor — brighter base so corridors are clearly visible against deep-space bg
      var fcx = x + tile/2 + offX*0.2, fcy = y + tile/2 + offY*0.2;
      // Solid base wash (noticeably lighter than background)
      ctx.fillStyle = 'rgba(58, 54, 80, 0.45)';
      ctx.fillRect(x, y, tile, tile);
      // Soft watercolor center variation
      inkWash(x, y, tile, tile,
        fcx, fcy, 0, tile*0.32,
        [[0, 'rgba(68, 64, 92, 0.22)'],
         [0.6, 'rgba(60, 56, 84, 0.10)'],
         [1, 'rgba(52, 48, 76, 0)']]);

      // Grain dot
      var grain = ctx.createRadialGradient(fcx, fcy, 0, fcx, fcy, tile*0.1);
      grain.addColorStop(0, 'rgba(185, 175, 165, 0.20)');
      grain.addColorStop(1, 'rgba(185, 175, 165, 0)');
      ctx.fillStyle = grain;
      ctx.fillRect(x + tile*0.3, y + tile*0.3, tile*0.4, tile*0.4);

      const isVisited = state.route.length && state.route.slice(0, state.frameIndex + 1).some(function(p) { return p.r === r && p.c === c; });
      if (isVisited) {
        // Visited path — stronger rose tint
        inkWash(x, y, tile, tile,
          x + tile/2 + offX*0.3, y + tile/2 + offY*0.3, 0, tile*0.35,
          [[0, 'rgba(200, 110, 138, 0.28)'],
           [0.6, 'rgba(175, 95, 120, 0.14)'],
           [1, 'rgba(150, 80, 105, 0)']]);
      }
    }

    drawCellIcon(cell, x, y, tile);
  }

  function drawCellIcon(cell, x, y, tile) {
    var cx = x + tile/2, cy = y + tile/2, dpr = state.layout.dpr;
    var iconR = tile * 0.2;

    if (cell === "S") {
      // Start — bright teal ink spot + sumi-e diamond
      inkWash(x - tile*0.1, y - tile*0.1, tile*1.2, tile*1.2,
        cx + (cellRand(0,0,5)-0.5)*tile*0.15, cy + (cellRand(0,0,6)-0.5)*tile*0.15,
        0, tile*0.45,
        [[0, 'rgba(100, 210, 210, 0.50)'],
         [0.5, 'rgba(80, 180, 180, 0.26)'],
         [1, 'rgba(60, 150, 150, 0)']]);
      ctx.strokeStyle = 'rgba(140, 235, 235, 0.85)';
      ctx.lineWidth = 1.4 * dpr;
      ctx.beginPath();
      ctx.moveTo(cx, cy - iconR);
      ctx.lineTo(cx + iconR, cy);
      ctx.lineTo(cx, cy + iconR);
      ctx.lineTo(cx - iconR, cy);
      ctx.closePath();
      ctx.stroke();
    } else if (cell === "E") {
      // Exit — bright amber ink spot + square core
      inkWash(x - tile*0.1, y - tile*0.1, tile*1.2, tile*1.2,
        cx + (cellRand(0,0,7)-0.5)*tile*0.15, cy + (cellRand(0,0,8)-0.5)*tile*0.15,
        0, tile*0.45,
        [[0, 'rgba(220, 175, 105, 0.45)'],
         [0.5, 'rgba(190, 150, 85, 0.24)'],
         [1, 'rgba(160, 125, 65, 0)']]);
      var es = tile * 0.24;
      inkWash(cx - es*2, cy - es*2, es*4, es*4,
        cx, cy, 0, es*1.3,
        [[0, 'rgba(245, 200, 125, 0.78)'],
         [1, 'rgba(245, 200, 125, 0)']]);
    } else if (cell === "B") {
      // Boss — bright crimson ink spot + hex glyph
      inkWash(x - tile*0.1, y - tile*0.1, tile*1.2, tile*1.2,
        cx + (cellRand(0,0,9)-0.5)*tile*0.15, cy + (cellRand(0,0,10)-0.5)*tile*0.15,
        0, tile*0.45,
        [[0, 'rgba(210, 85, 85, 0.42)'],
         [0.5, 'rgba(180, 70, 70, 0.22)'],
         [1, 'rgba(150, 55, 55, 0)']]);
      ctx.fillStyle = 'rgba(235, 110, 110, 0.90)';
      ctx.font = `${tile*0.55}px monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('⬡', cx, cy);
    } else if (cell === "T") {
      // Trap — bright ochre ink spot + X mark
      inkWash(x - tile*0.1, y - tile*0.1, tile*1.2, tile*1.2,
        cx + (cellRand(0,0,11)-0.5)*tile*0.15, cy + (cellRand(0,0,12)-0.5)*tile*0.15,
        0, tile*0.45,
        [[0, 'rgba(210, 170, 75, 0.38)'],
         [0.5, 'rgba(180, 145, 60, 0.20)'],
         [1, 'rgba(150, 120, 48, 0)']]);
      ctx.strokeStyle = 'rgba(225, 185, 85, 0.75)';
      ctx.lineWidth = 1.2 * dpr;
      var ts = tile * 0.14;
      ctx.strokeRect(cx - ts, cy - ts, ts*2, ts*2);
      ctx.beginPath();
      ctx.moveTo(cx - ts, cy - ts);
      ctx.lineTo(cx + ts, cy + ts);
      ctx.moveTo(cx + ts, cy - ts);
      ctx.lineTo(cx - ts, cy + ts);
      ctx.stroke();
    } else if (cell === "C" || cell === "G") {
      // Coin — bright gold ink spot + strong glowing core
      inkWash(x - tile*0.1, y - tile*0.1, tile*1.2, tile*1.2,
        cx + (cellRand(0,0,13)-0.5)*tile*0.15, cy + (cellRand(0,0,14)-0.5)*tile*0.15,
        0, tile*0.45,
        [[0, 'rgba(230, 195, 80, 0.45)'],
         [0.5, 'rgba(200, 170, 65, 0.24)'],
         [1, 'rgba(170, 145, 50, 0)']]);
      inkWash(cx - tile*0.2, cy - tile*0.2, tile*0.4, tile*0.4,
        cx, cy, 0, tile*0.2,
        [[0, 'rgba(255, 225, 120, 0.92)'],
         [1, 'rgba(255, 225, 120, 0)']]);
    }
  }

  function drawFogEdges(frame) {
    if (!state.showFog || state.mode === "full" || !frame) return;
    var rows = state.grid.length;
    var cols = state.grid[0].length;
    var { originX, originY, tile } = state.layout;
    var dirs = [[-1,0],[1,0],[0,-1],[0,1]];

    for (var r = 0; r < rows; r++) {
      for (var c = 0; c < cols; c++) {
        if (!shouldReveal(frame, r, c)) continue;
        for (var d = 0; d < dirs.length; d++) {
          var nr = r + dirs[d][0], nc = c + dirs[d][1];
          if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && !shouldReveal(frame, nr, nc)) {
            var fx = originX + c * tile, fy = originY + r * tile;
            var ex = fx + tile*0.5, ey = fy + tile*0.5;
            if (dirs[d][1] === -1) ex = fx;
            if (dirs[d][1] === 1)  ex = fx + tile;
            if (dirs[d][0] === -1) ey = fy;
            if (dirs[d][0] === 1)  ey = fy + tile;
            // Ink-wash glow at fog boundary (visible warm gray)
            var glow = ctx.createRadialGradient(ex, ey, 0, ex, ey, tile*0.4);
            glow.addColorStop(0, 'rgba(160, 150, 175, 0.22)');
            glow.addColorStop(1, 'rgba(160, 150, 175, 0)');
            ctx.fillStyle = glow;
            ctx.fillRect(ex - tile*0.4, ey - tile*0.4, tile*0.8, tile*0.8);
          }
        }
      }
    }
  }

  function drawPath(frame) {
    const { originX, originY, tile } = state.layout;

    // Visited path cell overlays — diluted rose ink wash
    if (frame && state.frameIndex >= 0) {
      for (var i = 0; i <= state.frameIndex; i++) {
        var p = state.route[i];
        var px = originX + p.c * tile + tile/2;
        var py = originY + p.r * tile + tile/2;
        var offX = (cellRand(p.r, p.c, 20) - 0.5) * tile * 0.25;
        var offY = (cellRand(p.r, p.c, 21) - 0.5) * tile * 0.25;
        var baseAlpha = (state.grid[p.r] && state.grid[p.r][p.c] !== "#") ? 0.07 : 0.04;
        inkWash(px - tile*0.5, py - tile*0.5, tile, tile,
          px + offX, py + offY, 0, tile*0.55,
          [[0, 'rgba(170, 90, 110, ' + baseAlpha + ')'],
           [0.5, 'rgba(140, 70, 90, ' + (baseAlpha*0.5) + ')'],
           [1, 'rgba(110, 50, 70, 0)']]);
      }
    }

    var toPoint = function(pos) { return { x: originX + pos.c * tile + tile/2, y: originY + pos.r * tile + tile/2 }; };

    if (frame) {
      // Traveled route — strong rose ink line
      drawRouteSegment(state.route, 0, state.frameIndex, 'rgba(195, 110, 140, 0.85)', Math.max(3, tile*0.14), toPoint);
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
    const { originX, originY, tile, dpr } = state.layout;

    var pc, pr;
    if (state.animPlayerX != null) {
      pc = state.animPlayerX; pr = state.animPlayerY;
    } else {
      pc = frame.pos.c; pr = frame.pos.r;
    }

    const x = originX + pc * tile;
    const y = originY + pr * tile;
    const cx = x + tile / 2, cy = y + tile / 2;

    // Player ambient glow — bright rose ink wash
    var glowGrad = ctx.createRadialGradient(cx, cy, tile*0.1, cx, cy, tile*0.8);
    glowGrad.addColorStop(0, 'rgba(210, 110, 145, 0.35)');
    glowGrad.addColorStop(1, 'rgba(210, 110, 145, 0)');
    ctx.fillStyle = glowGrad;
    ctx.fillRect(x - tile*0.3, y - tile*0.3, tile*1.6, tile*1.6);

    var player = state.assets.player;
    if (state.showSprites && player && player.complete) {
      ctx.drawImage(player, x + tile*0.08, y + tile*0.08, tile*0.84, tile*0.84);
    } else {
      // Player diamond — bright sumi-e ink style (crimson)
      ctx.save();
      ctx.shadowColor = 'rgba(200, 90, 125, 0.45)';
      ctx.shadowBlur = 10 * dpr;
      ctx.fillStyle = 'rgba(225, 115, 150, 0.92)';
      ctx.beginPath();
      var ds = tile * 0.22;
      ctx.moveTo(cx, cy - ds);
      ctx.lineTo(cx + ds*0.8, cy);
      ctx.lineTo(cx, cy + ds*0.6);
      ctx.lineTo(cx - ds*0.8, cy);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    if (state.showFog && state.mode !== "full") {
      ctx.strokeStyle = "rgba(0,229,255,0.35)";
      ctx.lineWidth = Math.max(1.5, dpr);
      var size = tile * (VIEW_RADIUS * 2 + 1);
      ctx.strokeRect(x - tile*VIEW_RADIUS, y - tile*VIEW_RADIUS, size, size);
    }
  }

  function drawHover() {
    const target = state.hovered || state.selected;
    if (!target || !state.grid.length) return;
    const { originX, originY, tile } = state.layout;
    const x = originX + target.c * tile;
    const y = originY + target.r * tile;
    ctx.strokeStyle = 'rgba(160, 150, 170, 0.45)';
    ctx.lineWidth = Math.max(1.2, tile * 0.04);
    ctx.strokeRect(x + 2, y + 2, tile - 4, tile - 4);
  }

  // Paper grain overlay — very subtle noise texture, sparse samples so it does not blur edges
  function drawPaperGrain() {
    var w = state.layout.width, h = state.layout.height;
    var imgData = ctx.getImageData(0, 0, w, h);
    var data = imgData.data;
    var seed = 7.731;
    for (var i = 0; i < data.length; i += 40) {
      var px = (i / 4) % w;
      var py = Math.floor((i / 4) / w);
      var n = Math.sin(px * 0.13 + py * 0.07 + seed) * 43758.5453;
      n = (n - Math.floor(n) - 0.5) * 3;
      data[i] = Math.min(255, Math.max(0, data[i] + n));
      data[i+1] = Math.min(255, Math.max(0, data[i+1] + n));
      data[i+2] = Math.min(255, Math.max(0, data[i+2] + n));
    }
    ctx.putImageData(imgData, 0, 0);
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
      els.runState.textContent = "Standby";
      return;
    }

    els.metricRound.textContent = String(frame.round);
    els.metricCoins.textContent = String(frame.coins);
    els.metricExplored.textContent = `${Math.round(frame.exploredRatio * 100)}%`;
    els.metricRoute.textContent = String(routeLength);
    els.phaseLabel.textContent = frame.phase;
    els.runState.textContent = state.playing ? "Playing" : "Paused";
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
      els.cellReadout.textContent = "Hover tile for info";
      return;
    }

    const frame = currentFrame();
    const visibleGrid = frame ? frame.grid : state.grid;
    const revealed = !frame || shouldReveal(frame, pos.r, pos.c);
    const cell = revealed ? visibleGrid[pos.r][pos.c] : null;
    const info = cell === null ? { label: "Unknown", weight: "-", color: "#05040a" } : (TILE[cell] || TILE[" "]);
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
      ["#", "Wall"],
      ["S", "Start"],
      ["E", "Exit"],
      ["B", "Boss"],
      ["T", "Trap"],
      ["G", "Coin"],
      [" ", "Path"],
      [null, "Unknown"],
    ];
    els.legendGrid.innerHTML = "";
    entries.forEach(([cell, label]) => {
      const item = document.createElement("div");
      const swatch = document.createElement("span");
      const text = document.createElement("span");
      item.className = "legend-item";
      swatch.className = "legend-swatch";
      swatch.style.background = cell === null ? "#05040a" : (TILE[cell] || TILE[" "]).color;
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
    state.animPlayerX = null;
    state.animPlayerY = null;
    state.animProgress = null;
    state.animToFrame = null;
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
    state.animRafId = null;
    state.lastFrameTime = 0;
    els.runState.textContent = "Playing";
    els.playBtn.textContent = "Ⅱ";
    scheduleTick();
  }

  // ---- BGM ----
  var bgmEls = {
    intro: document.getElementById('bgmIntro'),
    maze: document.getElementById('bgmMaze'),
    boss: document.getElementById('bgmBoss'),
  };
  var bgmState = { current: null, fadeTimer: null };

  function bgmPlay(el) {
    if (!el) return;
    el.volume = 0.35;
    el.currentTime = 0;
    el.play().catch(function(){});
    bgmState.current = el;
  }

  function bgmCrossfade(toEl, duration) {
    duration = duration || 700;
    if (bgmState.fadeTimer) { clearInterval(bgmState.fadeTimer); bgmState.fadeTimer = null; }
    if (!toEl || bgmState.current === toEl) return;
    var from = bgmState.current;
    var startVol = from ? from.volume : 0.35;
    toEl.volume = 0;
    toEl.play().catch(function(){});
    var steps = 20, stepTime = duration / steps, i = 0;
    bgmState.fadeTimer = setInterval(function() {
      i++;
      var t = i / steps;
      if (from) from.volume = Math.max(0, startVol * (1 - t));
      toEl.volume = Math.min(0.35, 0.35 * t);
      if (i >= steps) {
        clearInterval(bgmState.fadeTimer);
        bgmState.fadeTimer = null;
        if (from) { from.pause(); from.currentTime = 0; }
        bgmState.current = toEl;
      }
    }, stepTime);
  }

  function bgmStopAll() {
    if (bgmState.fadeTimer) { clearInterval(bgmState.fadeTimer); bgmState.fadeTimer = null; }
    [bgmEls.intro, bgmEls.maze, bgmEls.boss].forEach(function(el) {
      if (el) { el.pause(); el.currentTime = 0; }
    });
    bgmState.current = null;
  }

  function stopPlayback() {
    state.playing = false;
    if (state.timer) window.clearTimeout(state.timer);
    state.timer = null;
    if (state.animRafId) { window.cancelAnimationFrame(state.animRafId); state.animRafId = null; }
    els.playBtn.textContent = "▶";
    if (state.frames.length) els.runState.textContent = "Paused";
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
    var frame = currentFrame();
    if (!frame) { state.timer = window.setTimeout(scheduleTick, 100); return; }

    var stepDelay = Math.max(80, 800 / state.speed);
    var nextIdx = state.frameIndex + 1;
    if (nextIdx >= state.frames.length) { stopPlayback(); return; }

    var nextFrame = state.frames[nextIdx];
    var isSamePos = nextFrame.pos.r === frame.pos.r && nextFrame.pos.c === frame.pos.c;
    if (isSamePos) {
      setFrame(nextIdx);
      state.timer = window.setTimeout(scheduleTick, stepDelay * 0.3);
      return;
    }

    state.animRafId = window.requestAnimationFrame(function (timestamp) {
      animateStep(frame, nextFrame, nextIdx, timestamp, stepDelay);
    });
  }

  function animateStep(fromFrame, toFrame, toIdx, startTime, duration) {
    var elapsed = performance.now() - startTime;
    var t = Math.min(1, elapsed / duration);
    var eased = 1 - Math.pow(1 - t, 3);

    var fromX = fromFrame.pos.c, fromY = fromFrame.pos.r;
    var toX = toFrame.pos.c, toY = toFrame.pos.r;
    state.animPlayerX = fromX + (toX - fromX) * eased;
    state.animPlayerY = fromY + (toY - fromY) * eased;
    state.animProgress = eased;
    state.animToFrame = toFrame;

    draw();
    updateUi();

    if (t < 1) {
      state.animRafId = window.requestAnimationFrame(function () {
        animateStep(fromFrame, toFrame, toIdx, startTime, duration);
      });
    } else {
      state.animPlayerX = null;
      state.animPlayerY = null;
      state.animProgress = null;
      state.animToFrame = null;
      setFrame(toIdx);
      state.timer = window.setTimeout(scheduleTick, Math.max(30, duration * 0.15));
    }
  }

  function reset() {
    stopPlayback();
    closeBossOverlay(false);
    exitBattleMode();
    hideBattlePrompt();
    resetBossBattleReplayState();
    setFrame(0);
    showActors();
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
    els.bossWinMeta.textContent = outcome.bossIndex ? `Boss ${outcome.bossIndex} defeated` : "Boss defeated";
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
    bgmStopAll(); // iframe has its own BGM
    document.body.classList.add("overlay-open");
    els.bossOverlay.hidden = false;
    els.bossOverlay.setAttribute("aria-hidden", "false");
    els.bossOverlayTitle.textContent = `Boss ${payload.bossIndex} in combat`;
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
    bgmCrossfade(bgmEls.maze); // resume maze BGM after overlay closes
    if (shouldResume) startPlayback();
  }

  function maybeTriggerBossBattle() {
    const frame = currentFrame();
    if (!frame?.bossEncounter || state.bossBattleActive || state.bossAlertTimer) return;
    if (state.bossBattleQueue.includes(state.frameIndex)) return;
    state.bossBattleQueue.push(state.frameIndex);
    stopPlayback();
    showBattlePrompt();
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
    els.bossOverlayTitle.textContent = `Boss ${data.bossIndex ?? ""} battle${status}`;
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
    bgmCrossfade(bgmEls.maze);
    document.body.classList.add("intro-leaving");
    window.setTimeout(function () {
      document.body.classList.remove("intro-active", "intro-leaving");
      els.canvas.offsetHeight; // force reflow
      fitCanvas();
      draw();
      showActors();
      startPlayback();
    }, 600);
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
    els.emptyImportBtn.addEventListener("click", function () { els.fileInput.click(); });

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
    if (els.enterBattleBtn) {
      els.enterBattleBtn.addEventListener("click", () => {
        enterBattleMode();
      });
    }
    if (els.battleDataBtn) {
      els.battleDataBtn.addEventListener("click", toggleBattleDataPanel);
    }
    if (els.closeBattleDataBtn) {
      els.closeBattleDataBtn.addEventListener("click", toggleBattleDataPanel);
    }

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

    // Algorithm comparison button
    var runCompareBtn = document.getElementById("runCompareBtn");
    if (runCompareBtn) {
      runCompareBtn.addEventListener("click", function () {
        runComparison();
      });
    }

    // Compare overlay: close controls + view-switch buttons (event delegation)
    var compareOverlay = document.getElementById("compareOverlay");
    var comparePanel = document.getElementById("compareResults");
    function closeCompareOverlay() {
      if (compareOverlay) {
        compareOverlay.hidden = true;
        compareOverlay.classList.remove("is-visible");
      }
    }
    if (compareOverlay) {
      compareOverlay.addEventListener("click", function (e) {
        if (e.target === compareOverlay || e.target.classList.contains("compare-overlay-backdrop")) {
          closeCompareOverlay();
        }
      });
      var closeCompareBtn = document.getElementById("closeCompareOverlayBtn");
      if (closeCompareBtn) closeCompareBtn.addEventListener("click", closeCompareOverlay);
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && compareOverlay && !compareOverlay.hidden) closeCompareOverlay();
    });
    if (comparePanel) {
      comparePanel.addEventListener("click", function (e) {
        var btn = e.target.closest("[data-compare-view]");
        if (!btn) return;
        var mode = btn.getAttribute("data-compare-view");
        window._viewAlgo(mode);
        closeCompareOverlay();
      });
    }
    els.fileInput.addEventListener("change", async (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      try {
        const data = JSON.parse(await file.text());
        initMap(data, file.name);
      } catch (error) {
        els.mapMeta.textContent = `Import failed: ${error.message}`;
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

    // Use ResizeObserver to detect stage-area size changes (sidebar open/close, transitions, etc.)
    if (typeof ResizeObserver !== "undefined" && els.canvas.parentElement) {
      var ro = new ResizeObserver(function () {
        fitCanvas();
        draw();
      });
      ro.observe(els.canvas.parentElement);
    }
  }

  loadAssets();
  renderLegend();
  bindEvents();
  populateMapSelector();
  initSidebars();
  initEmptyState();
  ensureBossFrameLoaded();

  // Start intro BGM on first user interaction (browser autoplay policy)
  document.addEventListener('click', function bgmInitClick() {
    document.removeEventListener('click', bgmInitClick);
    if (!bgmState.current) bgmPlay(bgmEls.intro);
  }, { once: true });

  // Expose for testing / debugging
  window._battleTest = { enterBattleMode, exitBattleMode, showBattlePrompt };
})();
