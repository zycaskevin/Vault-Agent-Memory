import json
from pathlib import Path

from vault.cli import main
from vault.demo_agent_governance import run_agent_governance_demo


def _read_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_agent_governance_demo_runs_full_lifecycle(tmp_path):
    project = tmp_path / "demo-project"

    payload = run_agent_governance_demo(project_dir=project)

    assert payload["ok"] is True
    assert payload["scenario"] == "agent_memory_governance"
    assert payload["lifecycle"] == [
        "propose",
        "review",
        "promote",
        "search",
        "bounded_read",
        "rollback_available",
        "audit",
    ]
    assert payload["candidate_id"].startswith("mem_")
    assert payload["promoted_knowledge_id"] > 0
    assert payload["search_hit"]["id"] == payload["promoted_knowledge_id"]
    assert f"#{payload['promoted_knowledge_id']}" in payload["read_range_citation"]
    assert payload["rollback_available"] is True
    assert payload["rollback"]["verified"] is True
    assert any(event["outcome"] == "promoted" for event in payload["audit_events"])
    assert {scenario["id"] for scenario in payload["demo_scenarios"]} == {
        "consumer_mode",
        "automation_mode",
        "multi_host_sync",
    }
    assert payload["next_action"][0].startswith("Open start-here.md first")

    report = Path(payload["artifacts"]["report_md"])
    assert report.exists()
    assert "memory governance" in report.read_text(encoding="utf-8").lower()
    start_here = Path(payload["artifacts"]["start_here"])
    assert start_here.exists()
    assert "Open These In Order" in start_here.read_text(encoding="utf-8")
    public_script = Path(payload["artifacts"]["public_demo_script"])
    assert public_script.exists()
    assert "memory governance" in public_script.read_text(encoding="utf-8").lower()
    public_script_zh_hant = Path(payload["artifacts"]["public_demo_script_zh_hant"])
    assert public_script_zh_hant.exists()
    assert "受治理的共享記憶" in public_script_zh_hant.read_text(encoding="utf-8")
    public_script_zh_cn = Path(payload["artifacts"]["public_demo_script_zh_cn"])
    assert public_script_zh_cn.exists()
    assert "受治理的共享记忆" in public_script_zh_cn.read_text(encoding="utf-8")
    checklist = Path(payload["artifacts"]["acceptance_checklist"])
    assert checklist.exists()
    assert "bounded read" in checklist.read_text(encoding="utf-8").lower()
    evidence_json = Path(payload["artifacts"]["evidence_summary_json"])
    evidence = json.loads(evidence_json.read_text(encoding="utf-8"))
    assert evidence["ok"] is True
    assert {check["id"] for check in evidence["checks"]} == {
        "candidate_created",
        "promoted_memory_created",
        "search_found_promoted_memory",
        "bounded_read_citation",
        "rollback_verified",
        "audit_event_recorded",
    }
    evidence_md = Path(payload["artifacts"]["evidence_summary_md"])
    assert evidence_md.exists()
    assert "status: `pass`" in evidence_md.read_text(encoding="utf-8").lower()
    scenarios_json = Path(payload["artifacts"]["demo_scenarios_json"])
    scenarios = json.loads(scenarios_json.read_text(encoding="utf-8"))
    assert [scenario["artifact"] for scenario in scenarios] == [
        "consumer-mode-demo.md",
        "automation-mode-demo.md",
        "multi-host-sync-demo.md",
    ]
    consumer = Path(payload["artifacts"]["consumer_mode_demo"])
    assert consumer.exists()
    assert "vault --project-dir" in consumer.read_text(encoding="utf-8")
    automation = Path(payload["artifacts"]["automation_mode_demo"])
    assert automation.exists()
    assert "automation inbox" in automation.read_text(encoding="utf-8")
    multi_host = Path(payload["artifacts"]["multi_host_sync_demo"])
    assert multi_host.exists()
    assert "remote hmac-keys" in multi_host.read_text(encoding="utf-8")
    assert Path(payload["artifacts"]["codex_startup"]).exists()
    assert Path(payload["artifacts"]["claude_code_startup"]).exists()
    assert Path(payload["artifacts"]["hermes_startup"]).exists()


def test_agent_governance_demo_cli_json_with_explicit_project_dir(tmp_path, capsys):
    project = tmp_path / "explicit-demo"

    main(["demo", "agent-governance", "--project-dir", str(project), "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["project_dir"] == str(project.resolve())
    assert payload["temporary_project"] is False
    assert Path(payload["artifacts"]["start_here"]).exists()
    assert Path(payload["artifacts"]["report_json"]).exists()
    assert Path(payload["artifacts"]["snippet_dir"]).is_dir()


def test_agent_governance_demo_cli_without_project_dir_uses_temp_project(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    main(["demo", "agent-governance", "--json"])
    payload = _read_json(capsys)

    assert payload["ok"] is True
    assert payload["temporary_project"] is True
    assert payload["project_dir"] != str(tmp_path)
    assert not (tmp_path / "vault.db").exists()
    assert Path(payload["artifacts"]["report_md"]).exists()
