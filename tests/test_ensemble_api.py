from api.routers.sim import ENSEMBLE_CANDIDATE_AGENTS, StartRunRequest, delete_sim, start_and_run_sim


def test_ensemble_start_run_returns_best_candidate_playback() -> None:
    response = start_and_run_sim(StartRunRequest(map="sample.json", agent="ensemble", boss_source="map"))
    try:
        state = response["state"]
        ensemble = response["summary"]["ensemble"]
        candidate_agents = {candidate["agent"] for candidate in ensemble["candidates"]}

        assert ensemble["selected_agent"] in ENSEMBLE_CANDIDATE_AGENTS
        assert set(ENSEMBLE_CANDIDATE_AGENTS).issubset(candidate_agents)
        assert state["ensemble_result"]["selected_agent"] == ensemble["selected_agent"]
        assert len(state["history"]) > 1
    finally:
        delete_sim(response["session_id"])


def test_ensemble_manual_mode_selects_best_explorer_and_waits_for_boss_input() -> None:
    response = start_and_run_sim(StartRunRequest(map="sample.json", agent="ensemble", boss_source="manual"))
    try:
        state = response["state"]
        ensemble = response["summary"]["ensemble"]

        assert ensemble["selected_agent"] in ENSEMBLE_CANDIDATE_AGENTS
        assert state["ensemble_result"]["selected_agent"] == ensemble["selected_agent"]
        assert state["boss_health_source"] == "manual"
        assert state["awaiting_boss_input"] is True
        assert state["pending_boss_pos"] is not None
    finally:
        delete_sim(response["session_id"])
