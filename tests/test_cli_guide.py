import json

from vault.cli import main


def test_cli_guide_defaults_to_human_surface(capsys):
    main(["guide"])

    out = capsys.readouterr().out
    assert "Vault-for-LLM guide" in out
    assert "Intent shortcuts" in out
    assert "For humans, keep the surface small" in out
    assert "vault quickstart" in out
    assert "vault daily-report" in out


def test_cli_guide_agent_json_lists_mcp_profiles(capsys):
    main(["guide", "--mode", "agent", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["mode"] == "agent"
    assert payload["intent"] == "all"
    assert "everyday_entrypoints" not in payload
    assert [row["profile"] for row in payload["agent_mcp_profiles"]] == [
        "core",
        "review",
        "maintenance",
        "full",
    ]


def test_cli_guide_all_pretty_includes_all_surfaces(capsys):
    main(["guide", "--mode", "all", "--pretty"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "all"
    assert payload["everyday_entrypoints"]
    assert any(row["command"] == "vault daily-report" for row in payload["everyday_entrypoints"])
    assert payload["agent_mcp_profiles"]
    assert payload["maintenance_entrypoints"]


def test_cli_guide_human_intent_skills_is_small(capsys):
    main(["guide", "--intent", "skills", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "human"
    assert payload["intent"] == "skills"
    assert payload["everyday_entrypoints"] == []
    assert [row["command"] for row in payload["maintenance_entrypoints"]] == [
        "vault skill upgrade-plan --installed-file installed-skills.json"
    ]


def test_cli_guide_install_prints_copy_paste_agent_prompt(capsys):
    main(["guide", "--intent", "install"])

    out = capsys.readouterr().out
    assert "Copy this to your agent" in out
    assert "Use the agent-assisted governed-auto memory mode" in out
    assert "vault quickstart" in out
    assert "Do not show advanced CLI flags unless I ask" in out
    assert "The agent should ask only" in out
    assert "independent vault or shared vault" in out


def test_cli_guide_install_json_has_consumer_contract(capsys):
    main(["guide", "--intent", "install", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["intent"] == "install"
    assert payload["agent_install_prompt"].startswith("Install Vault-for-LLM")
    contract = payload["consumer_install_contract"]
    assert contract["audience"] == "consumer"
    assert contract["memory_mode"] == "governed-auto"
    assert len(contract["human_questions"]) == 4
    assert any("low-risk" in item for item in contract["agent_must_do"])
