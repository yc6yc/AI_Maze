(function () {
  async function request(method, path, body) {
    const options = { method, headers: {} };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
    const res = await fetch(path, options);
    let data = null;
    const text = await res.text();
    if (text) {
      data = JSON.parse(text);
    }
    if (!res.ok) {
      throw new Error((data && data.detail) || res.statusText);
    }
    return data;
  }

  window.mazeApi = {
    getMaps() {
      return request("GET", "/api/maps");
    },
    getMap(name) {
      return request("GET", `/api/maps/${encodeURIComponent(name)}`);
    },
    uploadMap(file) {
      const body = new FormData();
      body.append("file", file);
      return fetch("/api/maps/upload", { method: "POST", body }).then(async (res) => {
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || res.statusText);
        }
        return data;
      });
    },
    startSim(map, agent, config, bossSetup) {
      return request("POST", "/api/sim/start", { map, agent, config, ...(bossSetup || {}) });
    },
    startRunSim(map, agent, config, bossSetup, maxRounds) {
      return request("POST", "/api/sim/start-run", { map, agent, config, max_rounds: maxRounds, ...(bossSetup || {}) });
    },
    stepSim(sid) {
      return request("POST", `/api/sim/${sid}/step`);
    },
    runSim(sid, maxRounds) {
      return request("POST", `/api/sim/${sid}/run`, { max_rounds: maxRounds });
    },
    submitBossHealth(sid, bossHealth, revealAll) {
      return request("POST", `/api/sim/${sid}/bosses/input`, {
        boss_health: bossHealth,
        boss_healths_revealed: !!revealAll,
      });
    },
    deleteSim(sid) {
      return request("DELETE", `/api/sim/${sid}`);
    },
    runEval(payload) {
      return request("POST", "/api/eval/run", payload);
    },
    getConfig() {
      return request("GET", "/api/config");
    },
    setConfig(payload) {
      return request("PUT", "/api/config", payload);
    },
  };
})();
