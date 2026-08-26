from vault.db import VaultDB
from vault.memory import create_candidate, promote_candidate, quality_gate


def _types(result: dict) -> set[str]:
    return {finding["type"] for finding in result["findings"]}


def test_question_cannot_pass_because_reason_says_decision():
    result = quality_gate(
        {
            "title": "產品價值判斷",
            "content": "這是產品真正有價值的功能嗎？",
            "tags": "product,value",
            "reason": "decision from an explicit user rule",
        }
    )

    assert result["status"] == "warn"
    assert result["disposition"] == "review_required"
    assert result["decision_state"] == "question"
    assert "question_only" in _types(result)


def test_meta_instruction_is_not_a_memory_claim():
    result = quality_gate({"title": "候選指令", "content": "記住這段內容", "tags": "memory"})

    assert "meta_instruction_only" in _types(result)
    assert result["future_utility"] == "low"


def test_dangling_fragment_requires_review():
    result = quality_gate(
        {"title": "產品價值", "content": "你的產品真正有價值的是：", "tags": "product,value"}
    )

    assert "dangling_punctuation" in _types(result)
    assert result["semantic_completeness"] == "incomplete"


def test_deictic_fragment_requires_an_anchor():
    result = quality_gate({"title": "操作提醒", "content": "這個要保留下來。", "tags": "operation"})

    assert "deictic_without_anchor" in _types(result)
    assert result["context_dependency"] == "anchor_required"


def test_hash_suffix_title_is_opaque():
    result = quality_gate(
        {
            "title": "Hermes explicit user rule a1b2c3d4e5f6",
            "content": "API retries must stop after three attempts.",
            "tags": "api,retry",
        }
    )

    assert "opaque_title" in _types(result)
    assert result["title_quality"] == "opaque"


def test_long_readable_word_title_is_not_opaque():
    result = quality_gate(
        {
            "title": "Internationalization responsibilities",
            "content": "Internationalization responsibilities must remain explicit.",
            "tags": "localization,ownership",
        }
    )

    assert "opaque_title" not in _types(result)
    assert result["title_quality"] == "readable"


def test_complete_short_rule_can_pass_without_reason_padding():
    result = quality_gate(
        {"title": "API 重試上限", "content": "API 重試最多 3 次。", "tags": "api,retry", "reason": ""}
    )

    assert result["status"] == "pass"
    assert result["semantic_completeness"] == "complete"
    assert result["future_utility"] == "useful"


def test_semantic_fields_are_persisted_inside_legacy_gate_payload(tmp_path):
    with VaultDB(tmp_path / "vault.db") as db:
        created = create_candidate(
            db,
            title="API 重試上限",
            content="API 重試最多 3 次。",
            tags="api,retry",
            reason="Reviewed operational rule.",
            source="test",
        )
        row = db.get_memory_candidate(created["candidate_id"])

    assert created["gate_payload"]["quality"]["policy"] == "semantic-quality"
    assert '"semantic_completeness": "complete"' in row["gate_payload_json"]


def test_warning_candidate_requires_review_before_promotion(tmp_path):
    with VaultDB(tmp_path / "vault.db") as db:
        created = create_candidate(
            db,
            title="產品價值",
            content="你的產品真正有價值的是：",
            tags="product,value",
            reason="Captured from a conversation.",
            source="test",
        )
        promoted = promote_candidate(
            db,
            created["candidate_id"],
            confirm=True,
            project_dir=tmp_path,
        )

        assert created["next_action"]["tool"] == "vault_memory_review"
        assert promoted["status"] == "review_required"
        assert promoted["knowledge_id"] is None
        assert promoted["warning_gates"] == ["quality"]
        assert db.get_memory_candidate(created["candidate_id"])["status"] == "candidate"
        assert db.conn.execute("SELECT COUNT(*) AS n FROM knowledge").fetchone()["n"] == 0
        assert not (tmp_path / "raw").exists()


def test_duplicate_candidate_requires_canonical_choice_before_promotion(tmp_path):
    with VaultDB(tmp_path / "vault.db") as db:
        db.add_knowledge(
            title="API retry ceiling",
            content_raw="API retries must stop after three attempts.",
            source="test",
        )
        created = create_candidate(
            db,
            title="API retry ceiling",
            content="API retries must stop after three attempts.",
            tags="api,retry",
            reason="Repeated source observation.",
            source="test",
        )
        promoted = promote_candidate(
            db,
            created["candidate_id"],
            confirm=True,
            project_dir=tmp_path,
        )

        assert promoted["status"] == "review_required"
        assert "duplicate" in promoted["warning_gates"]
        assert db.conn.execute("SELECT COUNT(*) AS n FROM knowledge").fetchone()["n"] == 1
        assert not (tmp_path / "raw").exists()


def test_clean_candidate_still_promotes_under_strict_contract(tmp_path):
    with VaultDB(tmp_path / "vault.db") as db:
        created = create_candidate(
            db,
            title="API retry ceiling",
            content="API retries must stop after three attempts.",
            tags="api,retry",
            reason="Reviewed operational rule.",
            source="test",
        )
        promoted = promote_candidate(
            db,
            created["candidate_id"],
            confirm=True,
            project_dir=tmp_path,
            compile=False,
        )

        assert created["next_action"]["tool"] == "vault_memory_promote"
        assert promoted["status"] == "promoted"
        assert promoted["knowledge_id"] is not None
