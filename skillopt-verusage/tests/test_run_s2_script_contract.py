from pathlib import Path


def test_glm_rate_limit_retry_is_enabled_for_both_actor_profiles() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_s2_fixed_test20.sh"
    ).read_text(encoding="utf-8")
    glm_case = script.split("  glm)", 1)[1].split("  qwen)", 1)[0]
    profile_branch = glm_case.split(
        'if [[ "$ACTOR_PROFILE" == "cross_provider_20260819" ]]', 1
    )[0]
    assert "--rate-limit-retries 12" in profile_branch
    assert "--rate-limit-backoff-seconds 1" in profile_branch
    assert "--rate-limit-max-backoff-seconds 30" in profile_branch


def test_bridge_runs_enable_trace2skill_isolation_by_default() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_s2_fixed_test20.sh"
    ).read_text(encoding="utf-8")
    assert '${SKILLOPT_ACTOR_ISOLATION:-1}' in script
    assert '--actor-isolation-scratch-root "$ACTOR_SCRATCH_ROOT"' in script
    assert '$(dirname "$(dirname "$EVAL_VERUS_BIN")")' in script
    assert '--actor-isolation-verus-root "$ACTOR_VERUS_ROOT"' in script
    assert '$(dirname "$CARGO_HOME")/rustup' in script
    assert 'ACTOR_RUST_ROOT="$(dirname "$CARGO_HOME")"' in script
    assert '--actor-isolation-rust-root "$ACTOR_RUST_ROOT"' in script


def test_trace2skill_bundle_has_a_direct_fixed_test_handoff() -> None:
    script = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_s2_fixed_test20.sh"
    ).read_text(encoding="utf-8")
    assert "{blank|s1|s2|trace2skill}" in script
    assert 'SKILL_INPUT_FLAGS=(--skill-dir "$EXTERNAL_SKILL_PATH")' in script
    assert "skillopt_verusage.skill_artifact" in script
    assert 'if [[ "$SKILL_LABEL" == "blank" ]]' in script
