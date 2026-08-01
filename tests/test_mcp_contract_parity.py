"""Fail-closed parity checks for the public MCP memory/search contract."""

import copy
import hashlib
import inspect
import io
import json
from functools import cache
from pathlib import Path

import pytest

from vault import mcp
from vault.db import VaultDB
from vault.mcp import handle_tool_call, run_stdio, select_tools
from vault.mcp_memory import MCP_MEMORY_CANDIDATE_MAX_LIMIT
from vault.mcp_search import MCP_SEARCH_MAX_LIMIT, MCP_SEARCH_MAX_OFFSET
from vault.mcp_tools import PUBLIC_MEMORY_CONTRACT_TOOL_NAMES, TOOLS
from vault.search import SUPPORTED_SEARCH_MODES, UnsupportedSearchModeError, VaultSearch
from vault.search_utils import MAX_SEARCH_QUERY_CHARS

PUBLIC_TOOLS = frozenset(PUBLIC_MEMORY_CONTRACT_TOOL_NAMES)
PROFILE_VISIBILITY = {
    "core": {"vault_search", "vault_read_range", "vault_memory_propose"},
    "review": PUBLIC_TOOLS,
    "remote": {"vault_search", "vault_read_range", "vault_memory_propose"},
    "maintenance": PUBLIC_TOOLS,
    "full": PUBLIC_TOOLS,
}
REQUIRED_INPUTS = {
    "vault_search": ["query"],
    "vault_read_range": ["knowledge_id"],
    "vault_memory_propose": ["title", "content", "reason"],
    "vault_memory_candidates": [],
    "vault_memory_promote": ["candidate_id", "confirm"],
    "vault_memory_review": ["candidate_id", "outcome", "reason"],
}


def _tool(name: str) -> dict:
    matches = [tool for tool in TOOLS if tool["name"] == name]
    assert len(matches) == 1, f"expected exactly one public schema for {name}"
    return matches[0]


def _property(tool_name: str, property_name: str) -> dict:
    return _tool(tool_name)["inputSchema"]["properties"][property_name]


def _schema_contract_hash(schema: dict) -> str:
    encoded = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@cache
def _documented_contract() -> dict:
    text = (Path(__file__).parents[1] / "docs" / "mcp_public_memory_contract.md").read_text()
    raw = text.split("<!-- contract-json-start -->", 1)[1].split(
        "<!-- contract-json-end -->", 1
    )[0]
    return json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())


def _assert_documented_output_keys(contract: dict, payload: object) -> None:
    if contract["output"]["envelope"] == "search_result_json":
        assert contract["output"]["projection_dependent"] is True
        assert contract["output"]["keys"] == []
        assert isinstance(payload, list)
        return
    assert isinstance(payload, dict)
    assert set(contract["output"]["keys"]) <= payload.keys()


def _assert_documented_search_projection(
    contract: dict, payload: object, requested_fields: list[str]
) -> None:
    _assert_documented_output_keys(contract, payload)
    assert isinstance(payload, list) and payload
    expected_keys = set(contract["output"]["keys"]) | set(requested_fields)
    assert all(set(record) == expected_keys for record in payload)


def _stdio_call(monkeypatch, capsys, name: str, arguments: dict) -> dict:
    request = {
        "jsonrpc": "2.0",
        "id": 412,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    monkeypatch.setattr(mcp.sys, "stdin", io.StringIO(json.dumps(request) + "\n"))
    run_stdio()
    return json.loads(capsys.readouterr().out)


@pytest.fixture(autouse=True)
def isolate_mcp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp, "DB_PATH", str(tmp_path / "vault.db"))


def test_public_tool_names_required_inputs_and_dispatch_are_in_parity():
    advertised = {tool["name"] for tool in TOOLS}
    assert PUBLIC_TOOLS <= advertised

    for name, required in REQUIRED_INPUTS.items():
        assert _tool(name)["inputSchema"].get("required", []) == required



def test_complete_schema_hash_changes_for_new_nested_constraint():
    schema = copy.deepcopy(_tool("vault_search")["inputSchema"])
    changed = copy.deepcopy(schema)
    changed["properties"]["query"]["minLength"] = 1
    assert _schema_contract_hash(changed) != _schema_contract_hash(schema)


@pytest.mark.parametrize("profile, expected", PROFILE_VISIBILITY.items())
def test_public_tool_profile_visibility(profile, expected):
    visible = {tool["name"] for tool in select_tools(profile)}
    assert visible & PUBLIC_TOOLS == expected


def test_vault_search_schema_matches_runtime_truth():
    runtime_default = inspect.signature(VaultSearch.search).parameters["mode"].default
    mode = _property("vault_search", "mode")

    assert mode == {
        "type": "string",
        "enum": list(SUPPORTED_SEARCH_MODES),
        "description": "搜尋模式（預設 auto）",
        "default": runtime_default,
    }
    assert _property("vault_search", "query")["maxLength"] == MAX_SEARCH_QUERY_CHARS
    assert _property("vault_search", "limit") == {
        "type": "integer",
        "description": "最多回傳幾筆（預設 10）",
        "default": 10,
        "minimum": 1,
        "maximum": MCP_SEARCH_MAX_LIMIT,
    }
    assert _property("vault_search", "offset") == {
        "type": "integer",
        "description": "跳過前 N 筆（分頁用，預設 0）",
        "default": 0,
        "minimum": 0,
        "maximum": MCP_SEARCH_MAX_OFFSET,
    }


@pytest.mark.parametrize("mode", SUPPORTED_SEARCH_MODES)
def test_every_advertised_search_mode_reaches_handler(monkeypatch, mode):
    captured = {}

    class SyntheticDB:
        def close(self):
            captured["closed"] = True

    class CapturingSearch:
        def search(self, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(mcp, "_get_search", lambda: (SyntheticDB(), CapturingSearch()))
    payload = handle_tool_call("vault_search", {"query": "sample", "mode": mode})
    assert payload.get("failure_mode") != "unsupported_search_mode"
    assert captured["mode"] == mode
    assert captured["closed"] is True


@pytest.mark.parametrize(
    "arguments, expected_limit, expected_offset",
    [
        ({"limit": -1, "offset": -1}, 1, 0),
        ({"limit": 10**9, "offset": 10**9}, MCP_SEARCH_MAX_LIMIT, MCP_SEARCH_MAX_OFFSET),
    ],
)
def test_search_clamping_uses_schema_bounds(
    monkeypatch, arguments, expected_limit, expected_offset
):
    captured = {}

    class SyntheticDB:
        def close(self):
            pass

    class CapturingSearch:
        def search(self, **kwargs):
            captured.update(kwargs)
            return []

    monkeypatch.setattr(mcp, "_get_search", lambda: (SyntheticDB(), CapturingSearch()))
    payload = handle_tool_call("vault_search", {"query": "sample", **arguments})
    assert "result" in payload
    assert expected_limit in {
        _property("vault_search", "limit")["minimum"],
        _property("vault_search", "limit")["maximum"],
    }
    assert expected_offset in {
        _property("vault_search", "offset")["minimum"],
        _property("vault_search", "offset")["maximum"],
    }
    assert captured["limit"] == expected_limit
    assert captured["offset"] == expected_offset


def test_memory_enums_defaults_and_bounds_are_stable():
    assert _property("vault_memory_propose", "mode") == {
        "type": "string",
        "enum": ["candidate", "promote_if_safe"],
        "default": "candidate",
    }
    assert _property("vault_memory_review", "outcome")["enum"] == ["rejected", "blocked"]
    assert _property("vault_memory_candidates", "limit") == {
        "type": "integer",
        "description": "Maximum candidates to return.",
        "default": 50,
        "minimum": 1,
        "maximum": MCP_MEMORY_CANDIDATE_MAX_LIMIT,
    }
    assert _property("vault_memory_promote", "confirm")["default"] is True


def test_unsupported_search_mode_has_typed_runtime_and_mcp_failure(
    tmp_path, monkeypatch, capsys
):
    fragments = ["<", "script", ">", "probe", "</", "script", ">"]
    hostile_mode = "".join(fragments)
    assert hostile_mode not in _property("vault_search", "mode")["enum"]

    with VaultDB(tmp_path / "vault.db") as db, pytest.raises(
        UnsupportedSearchModeError
    ) as raised:
        VaultSearch(db).search("sample", mode=hostile_mode)
    assert isinstance(raised.value, ValueError)
    assert raised.value.mode == hostile_mode
    assert raised.value.supported_modes == SUPPORTED_SEARCH_MODES
    assert "無效的搜尋模式" in str(raised.value)
    assert hostile_mode not in str(raised.value)

    arguments = {"query": "sample", "mode": hostile_mode}
    payload = handle_tool_call("vault_search", arguments)
    assert payload["failure_mode"] == "unsupported_search_mode"
    assert payload["supported_modes"] == list(SUPPORTED_SEARCH_MODES)
    assert payload["next_action"] == {
        "tool": "vault_search",
        "arguments": {"query": "<search query>", "mode": "auto"},
    }
    assert "無效的搜尋模式" in payload["error"]
    assert hostile_mode not in json.dumps(payload)
    assert len(payload["error"]) <= 240

    wire = _stdio_call(monkeypatch, capsys, "vault_search", arguments)["result"]
    assert wire["isError"] is True
    envelope = json.loads(wire["content"][0]["text"])
    assert envelope["failure_mode"] == "unsupported_search_mode"
    assert envelope["supported_modes"] == list(SUPPORTED_SEARCH_MODES)
    assert envelope["next_action"] == payload["next_action"]
    assert hostile_mode not in json.dumps(wire)


def test_success_stdio_result_shape_is_unchanged(monkeypatch, capsys):
    monkeypatch.setattr(
        mcp,
        "handle_tool_call",
        lambda name, arguments: {"result": json.dumps({"status": "synthetic"})},
    )
    wire = _stdio_call(monkeypatch, capsys, "vault_stats", {})["result"]
    assert wire == {
        "content": [{"type": "text", "text": json.dumps({"status": "synthetic"})}]
    }


@pytest.mark.parametrize(
    "dispatcher_payload, expected_text",
    [
        (
            {
                "error": "Unknown tool",
                "failure_mode": "unknown_tool",
                "next_action": {"tool": "tools/list", "arguments": {}},
            },
            "Unknown tool",
        ),
        (
            {
                "error": "Error: synthetic failure",
                "failure_mode": "tool_execution_failed",
                "next_action": {"tool": "vault_search", "arguments": {}},
            },
            "Error: synthetic failure",
        ),
    ],
)
def test_generic_errors_remain_mcp_error_tool_results(
    monkeypatch, capsys, dispatcher_payload, expected_text
):
    monkeypatch.setattr(mcp, "handle_tool_call", lambda name, arguments: dispatcher_payload)
    wire = _stdio_call(monkeypatch, capsys, "synthetic_tool", {})["result"]
    assert wire["isError"] is True
    assert wire["content"][0]["text"] == expected_text


def test_unrelated_dispatch_failure_keeps_generic_error_contract(monkeypatch):
    from vault import mcp

    def fail_get_search():
        raise RuntimeError("synthetic unrelated failure")

    monkeypatch.setattr(mcp, "_get_search", fail_get_search)
    arguments = {"query": "sample"}
    payload = handle_tool_call("vault_search", arguments)
    assert payload == {
        "error": "Error: synthetic unrelated failure",
        "failure_mode": "tool_execution_failed",
        "next_action": {"tool": "vault_search", "arguments": arguments},
    }


def test_documented_contract_matches_schemas_profiles_and_output_envelopes():
    documented = _documented_contract()

    assert tuple(documented) == PUBLIC_MEMORY_CONTRACT_TOOL_NAMES
    for name in PUBLIC_MEMORY_CONTRACT_TOOL_NAMES:
        contract = documented[name]
        schema = _tool(name)["inputSchema"]
        assert contract["properties"] == list(schema["properties"])
        assert contract["required"] == schema.get("required", [])
        assert contract["schema_sha256"] == _schema_contract_hash(schema)
        assert contract["profiles"] == [
            profile for profile, names in PROFILE_VISIBILITY.items() if name in names
        ]
        assert contract["output"]["envelope"] in {"result_json", "search_result_json"}
        if name == "vault_search":
            assert contract["output"]["projection_dependent"] is True
            assert contract["output"]["keys"] == []
        else:
            assert contract["output"]["keys"]

    assert documented["vault_search"]["supported_modes"] == list(
        SUPPORTED_SEARCH_MODES
    )


def test_documented_success_envelopes_match_runtime(tmp_path):
    with VaultDB(tmp_path / "vault.db") as db:
        entry_id = db.add_knowledge(
            title="Synthetic release checklist",
            content_raw="Package the build.\nRun the smoke test.",
        )

    search = json.loads(
        handle_tool_call(
            "vault_search",
            {"query": "Synthetic release checklist", "mode": "basic", "limit": 1},
        )["result"]
    )
    documented = _documented_contract()
    _assert_documented_output_keys(documented["vault_search"], search)

    title_fields = ["title"]
    title_projection = json.loads(
        handle_tool_call(
            "vault_search",
            {
                "query": "Synthetic release checklist",
                "mode": "basic",
                "limit": 1,
                "fields": title_fields,
            },
        )["result"]
    )
    _assert_documented_search_projection(
        documented["vault_search"], title_projection, title_fields
    )

    empty_fields = documented["vault_search"]["output"]["keys"]
    empty_projection = json.loads(
        handle_tool_call(
            "vault_search",
            {
                "query": "Synthetic release checklist",
                "mode": "basic",
                "limit": 1,
                "fields": empty_fields,
            },
        )["result"]
    )
    _assert_documented_search_projection(
        documented["vault_search"], empty_projection, empty_fields
    )

    read = json.loads(
        handle_tool_call(
            "vault_read_range",
            {"knowledge_id": entry_id, "line_start": 1, "line_end": 2},
        )["result"]
    )
    _assert_documented_output_keys(documented["vault_read_range"], read)

    proposed = json.loads(
        handle_tool_call(
            "vault_memory_propose",
            {
                "title": "Synthetic packaging rule",
                "content": "Verify the package in a clean environment before release.",
                "reason": "Preserves a reusable release verification step.",
            },
        )["result"]
    )
    _assert_documented_output_keys(documented["vault_memory_propose"], proposed)

    candidates = json.loads(handle_tool_call("vault_memory_candidates", {})["result"])
    _assert_documented_output_keys(documented["vault_memory_candidates"], candidates)

    promoted = json.loads(
        handle_tool_call(
            "vault_memory_promote",
            {
                "candidate_id": proposed["candidate_id"],
                "confirm": True,
                "compile": False,
                "build_map": False,
            },
        )["result"]
    )
    _assert_documented_output_keys(documented["vault_memory_promote"], promoted)

    review_candidate = json.loads(
        handle_tool_call(
            "vault_memory_propose",
            {
                "title": "Synthetic duplicate cleanup rule",
                "content": "Review duplicate candidates before retaining them.",
                "reason": "Keeps candidate review behavior explicit.",
            },
        )["result"]
    )
    reviewed = json.loads(
        handle_tool_call(
            "vault_memory_review",
            {
                "candidate_id": review_candidate["candidate_id"],
                "outcome": "rejected",
                "reason": "Synthetic review outcome for contract verification.",
            },
        )["result"]
    )
    _assert_documented_output_keys(documented["vault_memory_review"], reviewed)


def test_documented_output_key_comparison_rejects_bogus_key():
    contract = {"output": {"envelope": "result_json", "keys": ["status", "bogus"]}}
    with pytest.raises(AssertionError):
        _assert_documented_output_keys(contract, {"status": "synthetic"})
