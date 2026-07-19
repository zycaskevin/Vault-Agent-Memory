from __future__ import annotations

import json
from pathlib import Path

from benchmarks.memory_foundation_compare import run_governance_suite


REPO_ROOT = Path(__file__).parent.parent
FIXTURE_PATH = REPO_ROOT / "benchmarks" / "vault_gov_bench" / "v0.1.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _cases_by_id(payload: dict) -> dict[str, dict]:
    return {case["id"]: case for case in payload["cases"]}


def test_governance_fixture_is_versioned_fixed_clock_and_claim_bounded():
    fixture = _load_fixture()
    cases = _cases_by_id(fixture)

    assert fixture["schema_version"] == 1
    assert fixture["artifact_type"] == "vault_governance_benchmark_fixture"
    assert fixture["fixture_id"] == "vault-gov-bench"
    assert fixture["fixture_version"] == "0.1"
    assert fixture["fixed_clock"] == "2026-07-19T12:00:00+00:00"
    assert fixture["execution_contract"]["expected_gap_counts_as_failure"] is False
    assert fixture["execution_contract"]["policy_replay_must_be_disclosed"] is True
    assert len(cases) == 19

    assert {
        case_id
        for case_id, case in cases.items()
        if case.get("expected_outcome") == "expected_gap"
    } == set()
    assert {
        case_id
        for case_id, case in cases.items()
        if case.get("expected_outcome") == "capability_gap"
    } == {"duplicate-candidate-idempotency-gap", "out-of-order-update-guard-gap"}
    assert all(
        case["expected_capability_gap"]
        for case in cases.values()
        if case.get("expected_outcome") == "capability_gap"
    )
    assert all(
        case["expected_capability_gap"] is None
        for case in cases.values()
        if case.get("expected_outcome") != "capability_gap"
    )

    policy_cases = {
        case_id
        for case_id, case in cases.items()
        if case["execution_mode"] == "policy_replay"
    }
    assert policy_cases == {
        "private-read-policy-replay",
        "shared-write-capability-replay",
        "restricted-read-policy-replay",
        "private-high-write-capability-replay",
        "restricted-write-capability-replay",
        "sensitivity-cap-policy-replay",
        "future-temporal-policy-replay",
        "unapproved-candidate-policy-replay",
        "privacy-secret-policy-replay",
        "missing-provenance-policy-replay",
        "malformed-lifecycle-policy-replay",
    }

    privacy_case = cases["privacy-secret-policy-replay"]
    assert privacy_case["expected_status"] == "fail"
    assert "fixture-only-not-a-secret" in privacy_case["content"]


def test_run_governance_suite_writes_a_complete_non_inflated_report(tmp_path):
    output_path = tmp_path / "vault-governance-result.json"

    result = run_governance_suite(
        fixture_path=FIXTURE_PATH,
        output_path=output_path,
    )

    assert result["status"] == "pass"
    assert result["fixture_version"] == "0.1"
    assert result["fixed_clock"] == "2026-07-19T12:00:00+00:00"
    assert result["cases_total"] == 19
    assert result["cases_passed"] == 17
    assert result["cases_failed"] == 0
    assert result["capability_gaps_total"] == 2
    assert len(result["cases"]) == 19
    assert json.loads(output_path.read_text(encoding="utf-8")) == result

    statuses = {case["id"]: case["status"] for case in result["cases"]}
    assert statuses == {
        "candidate-first-promotion-visibility": "pass",
        "private-read-policy-replay": "pass",
        "shared-write-capability-replay": "pass",
        "restricted-read-policy-replay": "pass",
        "private-high-write-capability-replay": "pass",
        "restricted-write-capability-replay": "pass",
        "sensitivity-cap-policy-replay": "pass",
        "future-temporal-policy-replay": "pass",
        "unapproved-candidate-policy-replay": "pass",
        "privacy-secret-policy-replay": "pass",
        "missing-provenance-policy-replay": "pass",
        "malformed-lifecycle-policy-replay": "pass",
        "privacy-candidate-real-rejection": "pass",
        "temporal-supersession-current-only": "pass",
        "ttl-strict-block-and-lifecycle-archive": "pass",
        "stale-derived-ghost-after-soft-delete": "pass",
        "reactivate-tombstone-rollback": "pass",
        "duplicate-candidate-idempotency-gap": "expected_gap",
        "out-of-order-update-guard-gap": "expected_gap",
    }


def test_governance_suite_exposes_dynamic_transition_evidence(tmp_path):
    fixture_cases = _cases_by_id(_load_fixture())
    result = run_governance_suite(
        fixture_path=FIXTURE_PATH,
        output_path=tmp_path / "vault-governance-result.json",
    )
    result_cases = _cases_by_id(result)

    for case_id, fixture_case in fixture_cases.items():
        observations = result_cases[case_id]["observed"]
        for key, expected_value in fixture_case["expected"].items():
            assert observations[key] == expected_value, f"{case_id}: {key}"

    candidate = result_cases["candidate-first-promotion-visibility"]["observed"]
    assert candidate["outcome"] == "blocked_then_visible"
    assert candidate["before_count"] == 0
    assert candidate["after_count"] == 1

    supersession = result_cases["temporal-supersession-current-only"]["observed"]
    assert supersession["outcome"] == "old_blocked_new_visible"
    assert supersession["old_reason_codes"] == ["superseded"]
    assert supersession["new_reason_codes"] == []

    stale_derived = result_cases["stale-derived-ghost-after-soft-delete"]["observed"]
    assert stale_derived["outcome"] == "ghost_blocked"
    assert stale_derived["reason_codes"] == ["deleted"]

    rollback = result_cases["reactivate-tombstone-rollback"]["observed"]
    assert rollback["outcome"] == "reactivated"
    assert rollback["audit_events"] == 2


def test_governance_suite_reports_capability_gaps_as_gaps_not_features(tmp_path):
    fixture_cases = _cases_by_id(_load_fixture())
    result = run_governance_suite(
        fixture_path=FIXTURE_PATH,
        output_path=tmp_path / "vault-governance-result.json",
    )
    result_cases = _cases_by_id(result)

    gap_ids = {
        "duplicate-candidate-idempotency-gap",
        "out-of-order-update-guard-gap",
    }
    for case_id in gap_ids:
        reported = result_cases[case_id]
        expected_gap = fixture_cases[case_id]["expected_capability_gap"]

        assert reported["status"] == "expected_gap"
        assert reported["expected_capability_gap"] is True
        assert expected_gap["capability"]
        assert expected_gap["expected_observation"]

    duplicate = result_cases["duplicate-candidate-idempotency-gap"]["observed"]
    assert duplicate["outcome"] == "capability_gap"
    assert duplicate["capability"] == "event_id_idempotency"

    out_of_order = result_cases["out-of-order-update-guard-gap"]["observed"]
    assert out_of_order["outcome"] == "capability_gap"
    assert out_of_order["capability"] == "revision_precondition"

    ttl = result_cases["ttl-strict-block-and-lifecycle-archive"]["observed"]
    assert ttl["outcome"] == "strict_block_and_archived"
    assert ttl["before_reason_codes"] == ["expired"]
    assert ttl["after_reason_codes"] == ["inactive", "expired"]
    assert ttl["archived_count"] == 1
    assert ttl["native_provider_immediate_ttl_filter"] is False


def test_governance_suite_fails_when_any_expected_observation_mismatches(tmp_path):
    fixture = _load_fixture()
    cases = _cases_by_id(fixture)
    cases["reactivate-tombstone-rollback"]["expected"]["audit_events"] = 99
    fixture_path = tmp_path / "tampered-fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    result = run_governance_suite(fixture_path=fixture_path)
    reported = _cases_by_id(result)["reactivate-tombstone-rollback"]

    assert result["status"] == "fail"
    assert result["cases_passed"] == 16
    assert result["cases_failed"] == 1
    assert result["capability_gaps_total"] == 2
    assert reported["status"] == "fail"
    assert reported["observed"]["audit_events"] == 2
    assert reported["expected"]["audit_events"] == 99
