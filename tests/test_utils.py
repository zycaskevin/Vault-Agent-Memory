from __future__ import annotations

from pathlib import Path

from vault.utils import as_list, clean_string_list, jsonable


def test_as_list_preserves_existing_list_and_item_types():
    values = [1, "two"]

    assert as_list(values) is values
    assert as_list(None) == []
    assert as_list("one") == ["one"]
    assert as_list(3) == [3]


def test_clean_string_list_trims_and_drops_empty_items():
    assert clean_string_list(None) == []
    assert clean_string_list("") == []
    assert clean_string_list("  next  ") == ["next"]
    assert clean_string_list(["  a", "", " b ", None]) == ["a", "b", "None"]
    assert clean_string_list(42) == ["42"]


def test_jsonable_converts_nested_non_json_values():
    payload = {"path": Path("notes/today.md"), "items": (Path("a"), 2)}

    assert jsonable(payload) == {"path": "notes/today.md", "items": ["a", 2]}
