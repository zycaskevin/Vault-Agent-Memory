from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/subject-distillation"
MANIFEST = SPEC / "baseline-manifest.json"
SCHEMA = SPEC / "schema.v15.sql"
VALIDATOR = ROOT / "scripts/validate_subject_baseline.py"
CANONICAL = [
    "specs/subject-distillation/requirements.md",
    "specs/subject-distillation/design.md",
    "specs/subject-distillation/tasks.md",
    "specs/subject-distillation/traceability.md",
    "specs/subject-distillation/schema.v15.sql",
]
EXPECTED = {
    "table": {
        "decision_episode_events",
        "decision_episodes",
        "subject_access_grants",
        "subject_aliases",
        "subject_assertion_evidence",
        "subject_assertions",
        "subject_auth_bindings",
        "subject_candidate_payloads",
        "subject_candidate_reviews",
        "subject_context_pack_entries",
        "subject_context_pack_runs",
        "subject_counterparty_controls",
        "subject_delegation_rules",
        "subject_evaluation_cases",
        "subject_evaluation_events",
        "subject_evaluation_gates",
        "subject_evaluation_prediction_assessments",
        "subject_evaluation_signoffs",
        "subject_events",
        "subject_evidence",
        "subject_installation",
        "subject_model_entries",
        "subject_models",
        "subject_payload_objects",
        "subject_policies",
        "subject_principals",
        "subject_purge_jobs",
        "subject_relationships",
        "subject_role_grants",
        "subjects",
    },
    "index": {
        "ix_decision_episode_subject_domain",
        "ix_decision_event_episode_kind",
        "ix_subject_access_lookup",
        "ix_subject_alias_lookup",
        "ix_subject_assertion_current",
        "ix_subject_assertion_evidence_evidence",
        "ix_subject_assertion_owner_namespace",
        "ix_subject_auth_principal_status",
        "ix_subject_candidate_review_candidate",
        "ix_subject_candidate_subject_kind",
        "ix_subject_counterparty_scope",
        "ix_subject_delegation_lookup",
        "ix_subject_eval_case_domain",
        "ix_subject_eval_event_case",
        "ix_subject_eval_prediction_case",
        "ix_subject_events_actor_time",
        "ix_subject_events_subject_time",
        "ix_subject_evidence_subject_state",
        "ix_subject_model_entry_source",
        "ix_subject_pack_subject_consumer",
        "ix_subject_payload_subject_state",
        "ix_subject_purge_state",
        "ix_subject_relationship_from_time",
        "ix_subject_relationship_to_time",
        "ix_subject_role_subject_role",
        "ix_subjects_type_lifecycle",
        "ux_subject_auth_active_fingerprint",
        "ux_subject_counterparty_current",
        "ux_subject_counterparty_deletion_request_event",
        "ux_subject_model_current",
        "ux_subject_payload_active_ref",
        "ux_subject_policy_current",
        "ux_subject_role_active",
        "ux_subjects_one_active_root",
    },
    "view": {"subject_evaluation_scorecard_v1"},
}


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA.read_text())
    assert db.execute("PRAGMA foreign_keys").fetchone() == (1,)
    return db


def run_validator(root: Path, manifest: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--repo-root",
            str(root),
            "--manifest",
            str(manifest or root / "specs/subject-distillation/baseline-manifest.json"),
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    for relative in CANONICAL:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    manifest = tmp_path / "specs/subject-distillation/baseline-manifest.json"
    shutil.copyfile(MANIFEST, manifest)
    return tmp_path, manifest, json.loads(manifest.read_text())


def write_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def validator_module():
    spec = importlib.util.spec_from_file_location("subject_baseline_validator", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exact_normative_id_sets_and_no_duplicates() -> None:
    requirements = (SPEC / "requirements.md").read_text()
    tasks = (SPEC / "tasks.md").read_text()
    r_ids = re.findall(r"^### (R-SD-\d{3})\b", requirements, re.MULTILINE)
    t_ids = re.findall(r"^### (T-\d{3})\b", tasks, re.MULTILINE)
    e_ids = re.findall(r"^### (E-(?:P|O|F)-\d{3})\b", requirements, re.MULTILINE)
    assert r_ids == [f"R-SD-{n:03d}" for n in range(1, 27)]
    assert t_ids == [f"T-{n:03d}" for n in range(1, 34)]
    assert e_ids == [
        *(f"E-P-{n:03d}" for n in range(1, 19)),
        *(f"E-O-{n:03d}" for n in range(1, 6)),
        *(f"E-F-{n:03d}" for n in range(1, 21)),
    ]
    assert len(set(r_ids)) == 26 and len(set(t_ids)) == 33 and len(set(e_ids)) == 43
    assert set(re.findall(r"^- \[[ xX]\]", tasks, re.MULTILINE)) <= {"- [ ]"}
    assert "checkbox" in tasks.lower() and "execution status" in tasks.lower()


def test_traceability_exact_rows_valid_edges_and_task_coverage() -> None:
    trace = (SPEC / "traceability.md").read_text()
    rows = re.findall(
        r"^\| (E-(?:P|O|F)-\d{3}) \|.*?\| (T-[^|]+) \| (`tests/[^|]+) \|$", trace, re.MULTILINE
    )
    expected_e = {
        *(f"E-P-{n:03d}" for n in range(1, 19)),
        *(f"E-O-{n:03d}" for n in range(1, 6)),
        *(f"E-F-{n:03d}" for n in range(1, 21)),
    }
    assert len(rows) == 43 and {row[0] for row in rows} == expected_e
    mapped_tasks: set[str] = set()
    for _, task_cell, test_cell in rows:
        task_ids = set(re.findall(r"T-\d{3}", task_cell))
        test_paths = re.findall(r"tests/[A-Za-z0-9_./-]+\.py", test_cell)
        assert task_ids and test_paths
        assert task_ids <= {f"T-{n:03d}" for n in range(1, 34)}
        mapped_tasks |= task_ids
    requirement_ids = {f"R-SD-{n:03d}" for n in range(1, 27)}
    assert set(re.findall(r"\bR-SD-\d{3}\b", trace)) <= requirement_ids
    assert mapped_tasks <= {f"T-{n:03d}" for n in range(1, 34)}
    task_contract = (SPEC / "tasks.md").read_text()
    assert set(re.findall(r"^### (T-\d{3})\b", task_contract, re.MULTILINE)) == {
        f"T-{n:03d}" for n in range(1, 34)
    }


def test_full_schema_exact_inventory_empty_and_foreign_keys_on() -> None:
    db = connection()
    for kind in ("table", "index", "view"):
        actual = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%'", (kind,)
            )
        }
        assert actual == EXPECTED[kind]
    triggers = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
    assert len(triggers) == 99
    assert all(
        db.execute(f'SELECT count(*) FROM "{table}"').fetchone() == (0,)
        for table in EXPECTED["table"]
    )


def test_parent_subject_identity_update_fails_closed() -> None:
    db = connection()
    db.execute(
        "INSERT INTO subject_principals VALUES('p','human','active',NULL,'2026-01-01','2026-01-01')"
    )
    db.execute(
        "INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'2026-01-01',NULL,'2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="subject_lifecycle_transition_forbidden"):
        db.execute("UPDATE subjects SET subject_type='organization' WHERE subject_id='s'")
    assert db.execute("SELECT subject_type FROM subjects WHERE subject_id='s'").fetchone() == (
        "person",
    )


def test_authorization_chain_and_pack_identity_are_physically_bound() -> None:
    db = connection()
    db.executemany(
        "INSERT INTO subject_principals VALUES(?,?,'active',NULL,'t0','t0')",
        (("owner", "human"), ("consumer", "agent")),
    )
    db.execute("INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'t0',NULL,'t0')")
    db.execute(
        "INSERT INTO subject_events VALUES('role-event','auth.role_grant.issued','s','owner','subject',NULL,NULL,'t0','t0','a0')"
    )
    db.execute(
        "INSERT INTO subject_role_grants VALUES('role','owner','s','subject','','fixture',1,'owner','role-event','t0',NULL,NULL,NULL,'t0')"
    )
    for kind in ("model", "access"):
        db.execute(
            "INSERT INTO subject_payload_objects VALUES(?, 's','policy_rules','local_private_fs',?,1,'mac',NULL,'active','t0','t0',NULL)",
            (f"payload-{kind}", f"ref-{kind}"),
        )
        db.execute(
            "INSERT INTO subject_policies VALUES(?, 's',?,1,?,'draft',NULL,'t1',NULL,NULL,'t0')",
            (f"policy-{kind}", kind, f"payload-{kind}"),
        )
        db.execute(
            "INSERT INTO subject_events VALUES(?, 'policy.approved','s','owner','subject',NULL,NULL,'t1','t1',?)",
            (f"approve-{kind}", f"audit-{kind}"),
        )
        db.execute(
            "UPDATE subject_policies SET status='sealed', approved_event_id=? WHERE policy_id=?",
            (f"approve-{kind}", f"policy-{kind}"),
        )
    db.execute(
        "INSERT INTO subject_models VALUES('model','s',1,'draft','t2','t0','t2','policy-model','owner',0,0,0,0,1.0,'known','mac',NULL,'t2')"
    )
    db.execute("UPDATE subject_models SET status='sealed' WHERE model_id='model'")
    db.execute(
        "INSERT INTO subject_events VALUES('grant-event','auth.access_grant.issued','s','owner','subject',NULL,NULL,'t2','t2','grant-audit')"
    )
    db.execute(
        "INSERT INTO subject_access_grants VALUES('grant','s','consumer','support',NULL,'task','choices','descriptive','private','policy-access','owner','grant-event','t1','t9',NULL,NULL,'t2')"
    )
    pack_sql = """INSERT INTO subject_context_pack_runs(
        pack_run_id,subject_id,model_id,access_grant_id,consumer_principal_id,purpose_code,
        task_ref,policy_id,generated_at) VALUES(?,?,?,?,?,?,?,?,?)"""
    db.execute(pack_sql, ("ok", "s", "model", "grant", "consumer", "support", "task", "policy-model", "t3"))
    db.execute(
        "UPDATE subject_context_pack_runs SET state='sealed',content_integrity_mac='mac',sealed_at='t4' WHERE pack_run_id='ok'"
    )
    assert db.execute("SELECT state FROM subject_context_pack_runs WHERE pack_run_id='ok'").fetchone() == ("sealed",)
    db.execute(pack_sql, ("bad", "s", "model", "grant", "consumer", "wrong", "task", "policy-model", "t3"))
    with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_pack_seal"):
        db.execute(
            "UPDATE subject_context_pack_runs SET state='sealed',content_integrity_mac='mac',sealed_at='t4' WHERE pack_run_id='bad'"
        )
    assert db.execute("SELECT state FROM subject_context_pack_runs WHERE pack_run_id='bad'").fetchone() == ("draft",)
    mutations = {
        "consumer": "consumer_principal_id='owner'",
        "purpose": "purpose_code='billing'",
        "task": "task_ref='other-task'",
        "policy_chain": "policy_id='policy-access'",
        "model_chain": "model_id='missing-model'",
        "subject": "subject_id='missing-subject'",
        "generated_time": "generated_at='t0'",
        "sealed_time": "sealed_at='t0'",
    }
    for index, mutation in enumerate(mutations.items()):
        name, assignment = mutation
        pack_id = f"bad-{index}"
        db.execute(pack_sql, (pack_id, "s", "model", "grant", "consumer", "support", "task", "policy-model", "t3"))
        with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_pack_seal"):
            db.execute(
                f"UPDATE subject_context_pack_runs SET state='sealed',content_integrity_mac='mac',sealed_at='t4',{assignment} WHERE pack_run_id=?",
                (pack_id,),
            )
        assert db.execute("SELECT state FROM subject_context_pack_runs WHERE pack_run_id=?", (pack_id,)).fetchone() == ("draft",), name
    db.execute(
        "INSERT INTO subject_access_grants VALUES('grant-expired','s','consumer','support',NULL,'task','choices','descriptive','private','policy-access','owner','grant-event','t1','t35',NULL,NULL,'t2')"
    )
    db.execute(
        "INSERT INTO subject_access_grants VALUES('grant-revoked','s','consumer','support',NULL,'task','choices','descriptive','private','policy-access','owner','grant-event','t1','t9',NULL,NULL,'t2')"
    )
    db.execute("INSERT INTO subject_events VALUES('revoke-grant','auth.access_grant.revoked','s','owner','subject',NULL,NULL,'t35','t35','revoke-audit')")
    db.execute("UPDATE subject_access_grants SET revoked_at='t35',revocation_event_id='revoke-grant' WHERE access_grant_id='grant-revoked'")
    for grant_id in ("grant-expired", "grant-revoked"):
        pack_id = f"bad-{grant_id}"
        db.execute(pack_sql, (pack_id, "s", "model", grant_id, "consumer", "support", "task", "policy-model", "t3"))
        with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_pack_seal"):
            db.execute("UPDATE subject_context_pack_runs SET state='sealed',content_integrity_mac='mac',sealed_at='t4' WHERE pack_run_id=?", (pack_id,))
        assert db.execute("SELECT state FROM subject_context_pack_runs WHERE pack_run_id=?", (pack_id,)).fetchone() == ("draft",)


def test_immutable_append_only_and_cross_subject_ownership() -> None:
    db = connection()
    db.execute(
        "INSERT INTO subject_principals VALUES('p','human','active',NULL,'2026-01-01','2026-01-01')"
    )
    db.executemany(
        "INSERT INTO subjects VALUES(?,?,'canonical',0,'active',NULL,'2026-01-01',NULL,'2026-01-01')",
        (("a", "person"), ("b", "person")),
    )
    db.execute(
        "INSERT INTO subject_events VALUES('e','fixture.event','a','p','system',NULL,NULL,'2026-01-01','2026-01-01','audit')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="subject_events_append_only"):
        db.execute("UPDATE subject_events SET event_kind='changed' WHERE event_id='e'")
    assert db.execute("SELECT event_kind FROM subject_events WHERE event_id='e'").fetchone() == ("fixture.event",)
    with pytest.raises(sqlite3.IntegrityError, match="subject_events_append_only"):
        db.execute("DELETE FROM subject_events WHERE event_id='e'")
    db.execute(
        "INSERT INTO subject_payload_objects VALUES('payload','a','private_evidence','local_private_fs','fixture',1,'mac',NULL,'active','2026-01-01','2026-01-01',NULL)"
    )
    db.execute(
        "INSERT INTO subject_evidence VALUES('legal','p','a','private_copy','fixture','ref',NULL,'mac','available','private','2026-01-01',NULL,NULL,'payload',NULL,'2026-01-01')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="subject_evidence_private_payload_scope_invalid"):
        db.execute(
            "INSERT INTO subject_evidence VALUES('ev','p','b','private_copy','fixture','ref',NULL,'mac','available','private','2026-01-01',NULL,NULL,'payload',NULL,'2026-01-01')"
        )
    assert db.execute("SELECT evidence_id FROM subject_evidence ORDER BY evidence_id").fetchall() == [("legal",)]
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_subject_purge_job_legal_order_and_one_field_negatives() -> None:
    db = connection()
    db.execute("INSERT INTO subject_principals VALUES('p','human','active',NULL,'t0','t0')")
    db.execute("INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'t0',NULL,'t0')")
    db.execute("INSERT INTO subject_events VALUES('role','auth.role_grant.issued','s','p','subject',NULL,NULL,'t0','t0','a0')")
    db.execute("INSERT INTO subject_role_grants VALUES('grant','p','s','subject','','fixture',1,'p','role','t0',NULL,NULL,NULL,'t0')")
    db.execute("INSERT INTO subject_events VALUES('request','payload.purge_requested','s','p','subject',NULL,NULL,'t1','t1','a1')")
    db.execute("INSERT INTO subject_payload_objects VALUES('payload','s','private_evidence','local_private_fs','private-ref',8,'mac',NULL,'active','t0','t0',NULL)")
    db.execute("INSERT INTO subject_purge_jobs VALUES('job','payload','p','request','pending',0,NULL,'t1','t1',NULL,NULL,NULL,NULL)")
    with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_purge_job_transition"):
        db.execute("UPDATE subject_purge_jobs SET state='running',attempts=2,updated_at='t2' WHERE purge_job_id='job'")
    assert db.execute("SELECT state,attempts FROM subject_purge_jobs").fetchone() == ("pending", 0)
    db.execute("UPDATE subject_purge_jobs SET state='running',attempts=1,updated_at='t2' WHERE purge_job_id='job'")
    with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_purge_job_transition"):
        db.execute("UPDATE subject_purge_jobs SET parent_fsynced_at='t3',updated_at='t3' WHERE purge_job_id='job'")
    assert db.execute("SELECT object_deleted_at,parent_fsynced_at FROM subject_purge_jobs").fetchone() == (None, None)
    db.execute("UPDATE subject_purge_jobs SET object_deleted_at='t3',updated_at='t3' WHERE purge_job_id='job'")
    with pytest.raises(sqlite3.IntegrityError, match="invalid_subject_purge_job_transition"):
        db.execute("UPDATE subject_purge_jobs SET metadata_cleared_at='t4',updated_at='t4' WHERE purge_job_id='job'")
    db.execute("UPDATE subject_purge_jobs SET parent_fsynced_at='t4',updated_at='t4' WHERE purge_job_id='job'")
    db.execute("UPDATE subject_payload_objects SET lifecycle='purge_pending',updated_at='t5' WHERE payload_id='payload'")
    db.execute("UPDATE subject_payload_objects SET object_ref=NULL,byte_count=0,integrity_mac=NULL,updated_at='t6' WHERE payload_id='payload'")
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed: state <> 'succeeded'"):
        db.execute("UPDATE subject_purge_jobs SET state='succeeded',metadata_cleared_at='t5',completed_at='t4',updated_at='t5' WHERE purge_job_id='job'")
    db.execute("UPDATE subject_purge_jobs SET state='succeeded',metadata_cleared_at='t5',completed_at='t6',updated_at='t6' WHERE purge_job_id='job'")
    db.execute("UPDATE subject_payload_objects SET lifecycle='purged',purged_at='t7',updated_at='t7' WHERE payload_id='payload'")
    assert db.execute("SELECT state,object_deleted_at,parent_fsynced_at,metadata_cleared_at,completed_at FROM subject_purge_jobs").fetchone() == ("succeeded", "t3", "t4", "t5", "t6")
    assert db.execute("SELECT lifecycle,object_ref,byte_count FROM subject_payload_objects").fetchone() == ("purged", None, 0)


def test_legal_hold_deletion_ordering_and_counterparty_boundaries() -> None:
    db = connection()
    db.executemany(
        "INSERT INTO subject_principals VALUES(?, 'human','active',NULL,'t0','t0')",
        (("pa",), ("pb",)),
    )
    db.executemany(
        "INSERT INTO subjects VALUES(?,?,'canonical',0,'active',NULL,'t0',NULL,'t0')",
        (("a", "person"), ("b", "person")),
    )
    for subject, principal in (("a", "pa"), ("b", "pb")):
        db.execute(
            "INSERT INTO subject_events VALUES(?, 'auth.role_grant.issued',?,?,'subject',NULL,NULL,'t0','t0',?)",
            (f"role-{subject}", subject, principal, f"audit-role-{subject}"),
        )
        db.execute(
            "INSERT INTO subject_role_grants VALUES(?,?,?,'subject','','fixture',1,?,?, 't0',NULL,NULL,NULL,'t0')",
            (f"grant-{subject}", principal, subject, principal, f"role-{subject}"),
        )
    db.execute(
        "INSERT INTO subject_events VALUES('relationship-event','relationship.recorded','a','pa','subject',NULL,NULL,'t1','t1','audit-r')"
    )
    db.execute(
        "INSERT INTO subject_relationships VALUES('r','a','b','customer','owner','counterparty','active','private','relationship-event','active',NULL,'t1',NULL,'t1')"
    )
    db.execute(
        "INSERT INTO subject_events VALUES('authority','counterparty.perspective_authorized','a','pa','subject',NULL,NULL,'t2','t2','audit-a')"
    )
    insert = """INSERT INTO subject_counterparty_controls(
        counterparty_control_id,primary_subject_id,counterparty_subject_id,relationship_id,
        processing_basis,authority_event_id,purpose_code,allow_store,allow_model,allow_export,
        export_mode,retention_until,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    db.execute(
        insert,
        ("c", "a", "b", "r", "subject_perspective_only", "authority", "support", 1, 0, 0, "none", "t9", "t2"),
    )
    assert db.execute("SELECT deletion_state FROM subject_counterparty_controls").fetchone() == ("active",)
    db.execute(
        "INSERT INTO subject_events VALUES('wrong-authority','counterparty.perspective_authorized','b','pb','subject',NULL,NULL,'t2','t2','audit-w')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="subject_counterparty_authority_event_mismatch"):
        db.execute(
            insert,
            ("bad", "a", "b", "r", "subject_perspective_only", "wrong-authority", "billing", 1, 0, 0, "none", "t9", "t2"),
        )
    with pytest.raises(sqlite3.IntegrityError, match="subject_counterparty_control_update_forbidden"):
        db.execute("UPDATE subject_counterparty_controls SET retention_until='t8' WHERE counterparty_control_id='c'")
    with pytest.raises(sqlite3.IntegrityError, match="subject_counterparty_history_retained"):
        db.execute("DELETE FROM subject_counterparty_controls WHERE counterparty_control_id='c'")
    db.execute("INSERT INTO subject_payload_objects VALUES('hold-rules','a','policy_rules','local_private_fs','hold-rules',1,'mac',NULL,'active','t0','t0',NULL)")
    db.execute("INSERT INTO subject_policies VALUES('hold-policy','a','counterparty',1,'hold-rules','draft',NULL,'t1',NULL,NULL,'t0')")
    db.execute("INSERT INTO subject_events VALUES('hold-approve','policy.approved','a','pa','subject',NULL,NULL,'t1','t1','audit-hp')")
    db.execute("UPDATE subject_policies SET status='sealed',approved_event_id='hold-approve' WHERE policy_id='hold-policy'")
    db.execute("INSERT INTO subject_principals VALUES('ph','human','active',NULL,'t0','t0')")
    db.execute("INSERT INTO subject_events VALUES('role-h','auth.role_grant.issued','a','pa','subject',NULL,NULL,'t1','t1','audit-rh')")
    db.execute("INSERT INTO subject_role_grants VALUES('grant-h','ph','a','authority_source','','fixture',1,'pa','role-h','t1',NULL,NULL,NULL,'t1')")
    db.execute("INSERT INTO subject_events VALUES('hold-event','counterparty.legal_hold_created','a','ph','authority_source',NULL,NULL,'t2','t2','audit-h')")
    held_insert = """INSERT INTO subject_counterparty_controls(
        counterparty_control_id,primary_subject_id,counterparty_subject_id,relationship_id,
        processing_basis,authority_event_id,purpose_code,allow_store,allow_model,allow_export,
        export_mode,retention_until,legal_hold_until,legal_hold_authority_event_id,
        legal_hold_policy_id,legal_hold_policy_version,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    db.execute(held_insert, ("held", "a", "b", "r", "subject_perspective_only", "authority", "legal", 1, 0, 0, "none", "u9", "u9", "hold-event", "hold-policy", 1, "t2"))
    db.execute("INSERT INTO subject_events VALUES('delete-request','counterparty.deletion_requested','a','pa','subject',NULL,NULL,'t3','t3','audit-dr')")
    db.execute("UPDATE subject_counterparty_controls SET deletion_state='purge_pending',deletion_requested_event_id='delete-request' WHERE counterparty_control_id='held'")
    db.execute("INSERT INTO subject_principals VALUES('pc','human','active',NULL,'t0','t0')")
    db.execute("INSERT INTO subject_events VALUES('role-c','auth.role_grant.issued','a','pa','subject',NULL,NULL,'t0','t0','audit-rc')")
    db.execute("INSERT INTO subject_role_grants VALUES('grant-c','pc','a','controller','','fixture',1,'pa','role-c','t0',NULL,NULL,NULL,'t0')")
    db.execute("INSERT INTO subject_events VALUES('delete-too-soon','counterparty.deletion_completed','a','pc','controller',NULL,NULL,'t4','t4','audit-ds')")
    with pytest.raises(sqlite3.IntegrityError, match="subject_counterparty_lifecycle_event_mismatch"):
        db.execute("UPDATE subject_counterparty_controls SET deletion_state='purged',deletion_completed_event_id='delete-too-soon' WHERE counterparty_control_id='held'")
    assert db.execute("SELECT deletion_state,deletion_completed_event_id FROM subject_counterparty_controls WHERE counterparty_control_id='held'").fetchone() == ("purge_pending", None)
    db.execute("INSERT INTO subject_events VALUES('delete-after-hold','counterparty.deletion_completed','a','pc','controller',NULL,NULL,'v0','v0','audit-da')")
    db.execute("UPDATE subject_counterparty_controls SET deletion_state='purged',deletion_completed_event_id='delete-after-hold' WHERE counterparty_control_id='held'")
    assert db.execute("SELECT deletion_state FROM subject_counterparty_controls WHERE counterparty_control_id='held'").fetchone() == ("purged",)


def test_decision_projection_append_only_and_evaluation_closure_guards() -> None:
    db = connection()
    db.execute("INSERT INTO subject_principals VALUES('p','human','active',NULL,'t0','t0')")
    db.executemany(
        "INSERT INTO subjects VALUES(?, 'person','canonical',0,'active',NULL,'t0',NULL,'t0')",
        (("s",), ("other",)),
    )
    db.execute(
        "INSERT INTO subject_events VALUES('role-event','auth.role_grant.issued','s','p','subject',NULL,NULL,'t0','t0','a0')"
    )
    db.execute(
        "INSERT INTO subject_role_grants VALUES('role','p','s','subject','choices','fixture',1,'p','role-event','t0',NULL,NULL,NULL,'t0')"
    )
    db.execute(
        "INSERT INTO subject_events VALUES('episode','decision.episode_created','s','p','subject',NULL,NULL,'t1','t1','a1')"
    )
    db.execute(
        "INSERT INTO decision_episodes VALUES('d','s','choices','open','unreviewed','episode','mac0',0,'t1')"
    )
    db.execute(
        "INSERT INTO subject_events VALUES('created','decision.created','s','p','subject',NULL,NULL,'t2','t2','a2')"
    )
    db.execute(
        "INSERT INTO decision_episode_events VALUES('de1','d',1,'created','p','subject','created',NULL,NULL,'t2','t2')"
    )
    db.execute(
        "UPDATE decision_episodes SET projected_through_sequence=1, projection_integrity_mac='mac1' WHERE episode_id='d'"
    )
    assert db.execute("SELECT projected_through_sequence FROM decision_episodes").fetchone() == (1,)
    with pytest.raises(sqlite3.IntegrityError, match="decision_episode_projection_update_forbidden"):
        db.execute("UPDATE decision_episodes SET projection_integrity_mac='bypass' WHERE episode_id='d'")
    with pytest.raises(sqlite3.IntegrityError, match="decision_events_append_only"):
        db.execute("UPDATE decision_episode_events SET source_ref='changed' WHERE decision_event_id='de1'")
    with pytest.raises(sqlite3.IntegrityError, match="decision_events_append_only"):
        db.execute("DELETE FROM decision_episode_events WHERE decision_event_id='de1'")
    db.execute(
        "INSERT INTO subject_events VALUES('wrong-subject','decision.context_set','other','p','subject',NULL,NULL,'t3','t3','a3')"
    )
    with pytest.raises(
        sqlite3.IntegrityError, match="decision_event_authority_sequence_or_payload_invalid"
    ):
        db.execute(
            "INSERT INTO decision_episode_events VALUES('de2','d',2,'context_set','p','subject','wrong-subject',NULL,NULL,'t3','t3')"
        )


def test_evaluation_gate_positive_freeze_and_missing_hash_udf_fails_closed() -> None:
    db = connection()
    db.create_function(
        "subject_sha256", 1, lambda value: hashlib.sha256(value.encode()).hexdigest(), deterministic=True
    )
    db.execute("INSERT INTO subject_principals VALUES('p','human','active',NULL,'t0','t0')")
    db.execute(
        "INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'t0',NULL,'t0')"
    )
    sha = "0" * 64
    db.execute(
        """INSERT INTO subject_evaluation_gates(
        gate_id,subject_id,gate_version,manifest_sha256,eligibility_rules_version,
        eligibility_rules_sha256,exclusion_rules_version,exclusion_rules_sha256,rounding_rule,
        hard_failure_rules_version,hard_failure_rules_sha256,scoring_definitions_version,
        scoring_definitions_sha256,reviewer_authority_code,created_at)
        VALUES('g','s',1,?,'v1',?,'v1',?,'ceil','v1',?,'v1',?,'fresh','t0')""",
        (sha, sha, sha, sha, sha),
    )
    db.execute(
        "INSERT INTO subject_evaluation_cases VALUES('c','g','mac','domain',0,0,0,0,1,NULL,'preregistered',NULL,'t0')"
    )
    db.execute("UPDATE subject_evaluation_gates SET state='frozen', frozen_at='t1' WHERE gate_id='g'")
    db.execute(
        "UPDATE subject_evaluation_cases SET completion_state='incomplete', disposition_at='t2' WHERE evaluation_case_id='c'"
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_incomplete"):
        db.execute(
            "UPDATE subject_evaluation_gates SET state='closed',closed_at='t3',scorecard_sha256=?,verdict='blocked' WHERE gate_id='g'",
            (sha,),
        )
    assert db.execute("SELECT state FROM subject_evaluation_gates").fetchone() == ("frozen",)

    earned = connection()
    earned.create_function(
        "subject_sha256", 1, lambda value: hashlib.sha256(value.encode()).hexdigest(), deterministic=True
    )
    earned.executemany(
        "INSERT INTO subject_principals VALUES(?,?,'active',NULL,'t0','t0')",
        (("subject", "human"), ("controller", "human"), ("reviewer", "human")),
    )
    earned.execute("INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'t0',NULL,'t0')")
    for principal, role in (("subject", "subject"), ("controller", "controller"), ("reviewer", "reviewer")):
        issuer = "subject"
        earned.execute(
            "INSERT INTO subject_events VALUES(?, 'auth.role_grant.issued','s',?,?,NULL,NULL,'t0','t0',?)",
            (f"role-{role}", issuer, "subject", f"audit-{role}"),
        )
        earned.execute(
            "INSERT INTO subject_role_grants VALUES(?,?,?,?,?,'fresh',1,?,?, 't0',NULL,NULL,NULL,'t0')",
            (f"grant-{role}", principal, "s", role, "", issuer, f"role-{role}"),
        )
    earned.execute(
        """INSERT INTO subject_evaluation_gates(
        gate_id,subject_id,gate_version,manifest_sha256,eligibility_rules_version,
        eligibility_rules_sha256,exclusion_rules_version,exclusion_rules_sha256,rounding_rule,
        hard_failure_rules_version,hard_failure_rules_sha256,scoring_definitions_version,
        scoring_definitions_sha256,reviewer_authority_code,created_at)
        VALUES('pass','s',1,?,'v1',?,'v1',?,'ceil','v1',?,'v1',?,'fresh','t0')""",
        (sha, sha, sha, sha, sha),
    )
    cases = []
    for index in range(20):
        domain = ("health", "finance", "travel")[min(index // 5, 2)]
        cases.append((f"c{index:02d}", "pass", f"mac{index:02d}", domain, int(index < 5), int(index < 3), 0, 0, 1, None, "preregistered", None, "t0"))
    earned.executemany("INSERT INTO subject_evaluation_cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", cases)
    earned.execute("UPDATE subject_evaluation_gates SET state='frozen',frozen_at='t1' WHERE gate_id='pass'")
    earned.execute("UPDATE subject_evaluation_cases SET completion_state='completed',disposition_at='t2' WHERE gate_id='pass'")

    # Evaluation evidence is accepted only from a currently active principal, even
    # when that principal still has an event-time-valid same-subject grant.
    earned.execute("SAVEPOINT inactive_insert_guards")
    for principal in ("subject", "reviewer"):
        earned.execute(
            "INSERT INTO subject_events VALUES(?, 'auth.binding.issued','s','subject','subject',NULL,NULL,'t05','t05',?)",
            (f"binding-{principal}", f"audit-binding-{principal}"),
        )
        earned.execute(
            "INSERT INTO subject_auth_bindings VALUES(?,?, 'subject','cli_capability','scrypt',?,?,16384,8,1,?,?,'active',NULL,NULL,NULL,'t05')",
            (f"binding-{principal}", principal, "s" * 22, "d" * 43,
             f"fingerprint-{principal}", f"binding-{principal}"),
        )
        earned.execute(
            "INSERT INTO subject_events VALUES(?, 'principal.suspended',NULL,?,'subject',NULL,NULL,'t15','t15',?)",
            (f"suspend-{principal}", principal, f"audit-suspend-{principal}"),
        )
        earned.execute(
            "UPDATE subject_principals SET status='suspended',status_event_id=?,updated_at='t15' WHERE principal_id=?",
            (f"suspend-{principal}", principal),
        )
    with pytest.raises(sqlite3.IntegrityError, match="unauthorized"):
        earned.execute(
            "INSERT INTO subject_evaluation_events VALUES('inactive-event','pass','c00','utility',1,1,'ok','subject','fixture','t2','audit-inactive-event')"
        )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_unauthorized"):
        earned.execute(
            "INSERT INTO subject_evaluation_prediction_assessments VALUES('inactive-assessment','pass','c00','not_emitted',NULL,NULL,NULL,NULL,'subject','fixture','t2','t2','audit-inactive-assessment')"
        )
    with pytest.raises(sqlite3.IntegrityError, match="signoff"):
        earned.execute(
            "INSERT INTO subject_evaluation_signoffs VALUES('inactive-signoff','pass','fresh_reviewer','reviewer','approve',?,'t2')",
            (sha,),
        )
    earned.execute("ROLLBACK TO inactive_insert_guards")
    earned.execute("RELEASE inactive_insert_guards")
    events = []
    for index in range(20):
        case_id = f"c{index:02d}"
        for event_type in ("utility", "reason_alignment"):
            rejected_rationale = index == 1 and event_type == "reason_alignment"
            events.append((f"{case_id}-{event_type}", "pass", case_id, event_type,
                           0.0 if rejected_rationale else 1.0, 0 if rejected_rationale else 1,
                           "rejected" if rejected_rationale else "ok", "subject", "fixture", "t2",
                           f"audit-{case_id}-{event_type}"))
        events.append((f"{case_id}-hard", "pass", case_id, "hard_failure", None, 1, "none", "subject", "fixture", "t2", f"audit-{case_id}-hard"))
        if index < 5:
            events.append((f"{case_id}-abstain", "pass", case_id, "abstention", 1.0, 1, "ok", "subject", "fixture", "t2", f"audit-{case_id}-abstain"))
    earned.executemany("INSERT INTO subject_evaluation_events VALUES(?,?,?,?,?,?,?,?,?,?,?)", events)
    earned.execute("SAVEPOINT missing_prediction_assessments")
    missing_score = earned.execute(
        "SELECT scorecard_sha256 FROM subject_evaluation_scorecard_v1 WHERE gate_id='pass'"
    ).fetchone()[0]
    earned.executemany(
        "INSERT INTO subject_evaluation_signoffs VALUES(?,?,?,?,?,?,?)",
        (("missing-sign-subject", "pass", "subject", "subject", "approve", missing_score, "t3"),
         ("missing-sign-reviewer", "pass", "fresh_reviewer", "reviewer", "approve", missing_score, "t3")),
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_incomplete"):
        earned.execute(
            "UPDATE subject_evaluation_gates SET state='closed',closed_at='t4',scorecard_sha256=?,verdict='pass' WHERE gate_id='pass'",
            (missing_score,),
        )
    earned.execute("ROLLBACK TO missing_prediction_assessments")
    earned.execute("RELEASE missing_prediction_assessments")
    choice_a, choice_b = "a" * 64, "b" * 64
    with pytest.raises(sqlite3.IntegrityError):
        earned.execute(
            "INSERT INTO subject_evaluation_prediction_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("bad-correctness", "pass", "c00", "reviewed", choice_a, 0.9, choice_b, 1,
             "subject", "fixture", "t2", "t2", "audit-bad-correctness"),
        )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_unauthorized"):
        earned.execute(
            "INSERT INTO subject_evaluation_prediction_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("unauthorized", "pass", "c00", "not_emitted", None, None, None, None,
             "reviewer", "fixture", "t2", "t2", "audit-unauthorized"),
        )
    earned.execute("INSERT INTO subject_principals VALUES('expired-reviewer','human','active',NULL,'t0','t0')")
    earned.execute(
        "INSERT INTO subject_events VALUES('role-expired-reviewer','auth.role_grant.issued','s','subject','subject',NULL,NULL,'t0','t0','audit-expired-reviewer')"
    )
    earned.execute(
        """INSERT INTO subject_role_grants VALUES(
        'grant-expired-reviewer','expired-reviewer','s','subject','','fresh',1,
        'subject','role-expired-reviewer','t0','t3',NULL,NULL,'t0')"""
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_unauthorized"):
        earned.execute(
            "INSERT INTO subject_evaluation_prediction_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("expired-at-review", "pass", "c00", "reviewed", choice_a, 0.9, choice_a, 1,
             "expired-reviewer", "fixture", "t2", "t3", "audit-expired-at-review"),
        )
    assessments = []
    for index in range(20):
        common = (f"prediction-{index:02d}", "pass", f"c{index:02d}")
        if index == 1:  # high-confidence correct
            evidence = ("reviewed", choice_a, 0.9, choice_a, 1)
        elif index == 2:  # low-confidence wrong
            evidence = ("reviewed", choice_a, 0.5, choice_b, 0)
        elif index == 3:  # exactly-threshold wrong is legal: the rule is strictly above
            evidence = ("reviewed", choice_a, 0.8, choice_b, 0)
        else:  # no prediction is reported but excluded from the hard-failure denominator
            evidence = ("not_emitted", None, None, None, None)
        assessments.append((*common, *evidence, "subject", "fixture", "t2", "t2", f"audit-prediction-{index:02d}"))
    earned.executemany(
        "INSERT INTO subject_evaluation_prediction_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        assessments,
    )
    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        earned.execute(
            "UPDATE subject_evaluation_prediction_assessments SET source_ref='changed' WHERE prediction_assessment_id='prediction-00'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="append_only"):
        earned.execute(
            "DELETE FROM subject_evaluation_prediction_assessments WHERE prediction_assessment_id='prediction-00'"
        )
    score = earned.execute("SELECT scorecard_sha256 FROM subject_evaluation_scorecard_v1 WHERE gate_id='pass'").fetchone()[0]
    assert score != missing_score
    earned.executemany(
        "INSERT INTO subject_evaluation_signoffs VALUES(?,?,?,?,?,?,?)",
        (("sign-controller", "pass", "controller", "controller", "approve", score, "t3"),
         ("sign-reviewer", "pass", "fresh_reviewer", "reviewer", "approve", score, "t3")),
    )

    # Later grant edits must be reinterpreted on the final timeline at close.
    earned.execute("SAVEPOINT retroactive_grant_revocation")
    earned.execute(
        "INSERT INTO subject_events VALUES('revoke-subject-retro','auth.role_grant.revoked','s','controller','controller',NULL,NULL,'t2','t2','audit-revoke-subject-retro')"
    )
    earned.execute(
        "UPDATE subject_role_grants SET revoked_at='t2',revocation_event_id='revoke-subject-retro' WHERE role_grant_id='grant-subject'"
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_incomplete"):
        earned.execute("UPDATE subject_evaluation_gates SET state='closed',closed_at='t4',scorecard_sha256=?,verdict='pass' WHERE gate_id='pass'", (score,))
    earned.execute("ROLLBACK TO retroactive_grant_revocation")
    earned.execute("RELEASE retroactive_grant_revocation")

    earned.execute("SAVEPOINT inactive_principal_at_close")
    earned.execute(
        "INSERT INTO subject_events VALUES('binding-subject-close','auth.binding.issued','s','subject','subject',NULL,NULL,'t05','t05','audit-binding-subject-close')"
    )
    earned.execute(
        "INSERT INTO subject_auth_bindings VALUES('binding-subject-close','subject','subject','cli_capability','scrypt',?,?,16384,8,1,'fingerprint-subject-close','binding-subject-close','active',NULL,NULL,NULL,'t05')",
        ("s" * 22, "d" * 43),
    )
    earned.execute(
        "INSERT INTO subject_events VALUES('suspend-subject-close','principal.suspended',NULL,'subject','subject',NULL,NULL,'t35','t35','audit-suspend-subject-close')"
    )
    earned.execute(
        "UPDATE subject_principals SET status='suspended',status_event_id='suspend-subject-close',updated_at='t35' WHERE principal_id='subject'"
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_incomplete"):
        earned.execute("UPDATE subject_evaluation_gates SET state='closed',closed_at='t4',scorecard_sha256=?,verdict='pass' WHERE gate_id='pass'", (score,))
    earned.execute("ROLLBACK TO inactive_principal_at_close")
    earned.execute("RELEASE inactive_principal_at_close")

    # Revocation strictly after the subject's evidence times preserves historical
    # authority; the independent controller signoff remains valid for closure.
    earned.execute(
        "INSERT INTO subject_events VALUES('revoke-subject-later','auth.role_grant.revoked','s','controller','controller',NULL,NULL,'t25','t25','audit-revoke-subject-later')"
    )
    earned.execute(
        "UPDATE subject_role_grants SET revoked_at='t25',revocation_event_id='revoke-subject-later' WHERE role_grant_id='grant-subject'"
    )
    earned.execute("UPDATE subject_evaluation_gates SET state='closed',closed_at='t4',scorecard_sha256=?,verdict='pass' WHERE gate_id='pass'", (score,))
    assert earned.execute("SELECT state,scorecard_sha256,verdict FROM subject_evaluation_gates").fetchone() == ("closed", score, "pass")
    assert earned.execute("SELECT scorecard_sha256 FROM subject_evaluation_scorecard_v1").fetchone() == (score,)

    # A second otherwise-earned gate cannot close PASS with one mechanically wrong
    # subject-choice prediction strictly above the frozen threshold.
    earned.execute(
        """INSERT INTO subject_evaluation_gates(
        gate_id,subject_id,gate_version,manifest_sha256,eligibility_rules_version,
        eligibility_rules_sha256,exclusion_rules_version,exclusion_rules_sha256,rounding_rule,
        hard_failure_rules_version,hard_failure_rules_sha256,scoring_definitions_version,
        scoring_definitions_sha256,reviewer_authority_code,created_at)
        VALUES('bad','s',2,?,'v1',?,'v1',?,'ceil','v1',?,'v1',?,'fresh','t0')""",
        (sha, sha, sha, sha, sha),
    )
    bad_cases = [
        (f"b{index:02d}", "bad", f"badmac{index:02d}", ("health", "finance", "travel")[min(index // 5, 2)],
         int(index < 5), int(index < 3), 0, 0, 1, None, "preregistered", None, "t0")
        for index in range(20)
    ]
    earned.executemany("INSERT INTO subject_evaluation_cases VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", bad_cases)
    earned.execute("UPDATE subject_evaluation_gates SET state='frozen',frozen_at='t1' WHERE gate_id='bad'")
    earned.execute("UPDATE subject_evaluation_cases SET completion_state='completed',disposition_at='t2' WHERE gate_id='bad'")
    bad_events = []
    for index in range(20):
        case_id = f"b{index:02d}"
        for event_type in ("utility", "reason_alignment"):
            bad_events.append((f"{case_id}-{event_type}", "bad", case_id, event_type, 1.0, 1, "ok", "subject", "fixture", "t2", f"audit-{case_id}-{event_type}"))
        bad_events.append((f"{case_id}-hard", "bad", case_id, "hard_failure", None, 1, "none", "subject", "fixture", "t2", f"audit-{case_id}-hard"))
        if index < 5:
            bad_events.append((f"{case_id}-abstain", "bad", case_id, "abstention", 1.0, 1, "ok", "subject", "fixture", "t2", f"audit-{case_id}-abstain"))
    earned.executemany("INSERT INTO subject_evaluation_events VALUES(?,?,?,?,?,?,?,?,?,?,?)", bad_events)
    bad_assessments = []
    for index in range(20):
        evidence = ("reviewed", choice_a, 0.81, choice_b, 0) if index == 0 else ("not_emitted", None, None, None, None)
        bad_assessments.append((f"bad-prediction-{index:02d}", "bad", f"b{index:02d}", *evidence,
                                "subject", "fixture", "t2", "t2", f"audit-bad-prediction-{index:02d}"))
    earned.executemany("INSERT INTO subject_evaluation_prediction_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", bad_assessments)
    bad_score = earned.execute("SELECT scorecard_sha256 FROM subject_evaluation_scorecard_v1 WHERE gate_id='bad'").fetchone()[0]
    earned.executemany(
        "INSERT INTO subject_evaluation_signoffs VALUES(?,?,?,?,?,?,?)",
        (("bad-sign-controller", "bad", "controller", "controller", "approve", bad_score, "t3"),
         ("bad-sign-reviewer", "bad", "fresh_reviewer", "reviewer", "approve", bad_score, "t3")),
    )
    with pytest.raises(sqlite3.IntegrityError, match="invalid_or_incomplete"):
        earned.execute(
            "UPDATE subject_evaluation_gates SET state='closed',closed_at='t4',scorecard_sha256=?,verdict='pass' WHERE gate_id='bad'",
            (bad_score,),
        )

    missing_udf = connection()
    missing_udf.execute("INSERT INTO subject_principals VALUES('p','human','active',NULL,'t0','t0')")
    missing_udf.execute(
        "INSERT INTO subjects VALUES('s','person','canonical',0,'active',NULL,'t0',NULL,'t0')"
    )
    missing_udf.execute(
        """INSERT INTO subject_evaluation_gates(
        gate_id,subject_id,gate_version,manifest_sha256,eligibility_rules_version,
        eligibility_rules_sha256,exclusion_rules_version,exclusion_rules_sha256,rounding_rule,
        hard_failure_rules_version,hard_failure_rules_sha256,scoring_definitions_version,
        scoring_definitions_sha256,reviewer_authority_code,created_at)
        VALUES('g','s',1,?,'v1',?,'v1',?,'ceil','v1',?,'v1',?,'fresh','t0')""",
        (sha, sha, sha, sha, sha),
    )
    with pytest.raises(sqlite3.OperationalError, match="no such function: subject_sha256"):
        missing_udf.execute(
            "UPDATE subject_evaluation_gates SET state='frozen', frozen_at='t1' WHERE gate_id='g'"
        )


def test_checked_in_manifest_hash_size_domain_and_closure() -> None:
    result = run_validator(ROOT, MANIFEST)
    assert result.returncode == 0, result.stderr
    data = json.loads(MANIFEST.read_text())
    assert [entry["path"] for entry in data["files"]] == CANONICAL
    payload = bytearray(b"subject-distillation-baseline-v1\n")
    for entry in data["files"]:
        raw = (ROOT / entry["path"]).read_bytes()
        assert (entry["sha256"], entry["size_bytes"]) == (hashlib.sha256(raw).hexdigest(), len(raw))
        payload += (
            entry["path"].encode()
            + b"\0"
            + entry["sha256"].encode()
            + b"\0"
            + str(entry["size_bytes"]).encode()
            + b"\n"
        )
    digest = hashlib.sha256(payload).hexdigest()
    assert data["closure"] == {"full_digest": digest, "baseline_id": digest[:16]}


@pytest.mark.parametrize(
    "mode", ["missing", "extra", "reordered", "path", "size", "hash", "domain", "closure", "type"]
)
def test_manifest_mutations_fail_closed(tmp_path: Path, mode: str) -> None:
    root, manifest, data = fixture(tmp_path)
    if mode == "missing":
        data["files"].pop()
    elif mode == "extra":
        data["files"].append(dict(data["files"][0]))
    elif mode == "reordered":
        data["files"][0], data["files"][1] = data["files"][1], data["files"][0]
    elif mode == "path":
        data["files"][0]["path"] = "../escape"
    elif mode == "size":
        data["files"][0]["size_bytes"] += 1
    elif mode == "hash":
        data["files"][0]["sha256"] = "0" * 64
    elif mode == "domain":
        data["algorithm"]["domain_separator_utf8_hex"] = "00"
    elif mode == "closure":
        data["closure"]["full_digest"] = "0" * 64
    else:
        data["schema_version"] = True
    write_manifest(manifest, data)
    assert run_validator(root).returncode == 1


def test_duplicate_keys_and_symlinks_fail_closed(tmp_path: Path) -> None:
    root, manifest, _ = fixture(tmp_path / "duplicate")
    manifest.write_text('{"schema_version":1,"schema_version":1}')
    assert run_validator(root).returncode == 1
    root, manifest, _ = fixture(tmp_path / "target")
    target = root / CANONICAL[0]
    copy = tmp_path / "copy.md"
    shutil.copyfile(target, copy)
    target.unlink()
    target.symlink_to(copy)
    assert run_validator(root, manifest).returncode == 1


def test_manifest_and_canonical_size_limits_are_bounded(tmp_path: Path) -> None:
    root, manifest, data = fixture(tmp_path / "manifest-large")
    manifest.write_bytes(b"{" + b" " * (64 * 1024))
    result = run_validator(root, manifest)
    assert result.returncode == 1
    assert json.loads(result.stdout)["code"] == "manifest_too_large"

    root, manifest, data = fixture(tmp_path / "canonical-large")
    target = root / CANONICAL[0]
    target.write_bytes(b"x" * (512 * 1024 + 1))
    data["files"][0]["size_bytes"] = 512 * 1024 + 1
    write_manifest(manifest, data)
    result = run_validator(root, manifest)
    assert result.returncode == 1
    assert json.loads(result.stdout)["code"] == "canonical_file_too_large"


@pytest.mark.parametrize("kind", ["final_symlink", "ancestor_symlink", "directory", "hardlink"])
def test_hostile_manifest_objects_fail_closed(tmp_path: Path, kind: str) -> None:
    root, manifest, _ = fixture(tmp_path / kind)
    if kind == "final_symlink":
        saved = tmp_path / "saved-manifest"
        manifest.rename(saved)
        manifest.symlink_to(saved)
    elif kind == "ancestor_symlink":
        specs = root / "specs"
        saved = tmp_path / "saved-specs"
        specs.rename(saved)
        specs.symlink_to(saved, target_is_directory=True)
    elif kind == "directory":
        manifest.unlink()
        manifest.mkdir()
    else:
        saved = tmp_path / "linked-manifest"
        os.link(manifest, saved)
    result = run_validator(root, manifest)
    assert result.returncode == 1
    assert json.loads(result.stdout)["code"] == "manifest_file_invalid"


@pytest.mark.parametrize("kind", ["final_symlink", "ancestor_symlink", "hardlink"])
def test_hostile_canonical_objects_fail_closed(tmp_path: Path, kind: str) -> None:
    root, manifest, _ = fixture(tmp_path / kind)
    target = root / CANONICAL[0]
    if kind == "final_symlink":
        saved = tmp_path / "saved-canonical"
        target.rename(saved)
        target.symlink_to(saved)
    elif kind == "ancestor_symlink":
        directory = target.parent
        saved = tmp_path / "saved-subject-distillation"
        directory.rename(saved)
        directory.symlink_to(saved, target_is_directory=True)
    else:
        os.link(target, tmp_path / "linked-canonical")
    result = run_validator(root, manifest)
    assert result.returncode == 1
    expected = "manifest_file_invalid" if kind == "ancestor_symlink" else "canonical_file_invalid"
    assert json.loads(result.stdout)["code"] == expected


def test_descriptor_path_identity_swap_during_read_fails_closed(tmp_path: Path, monkeypatch) -> None:
    root, manifest, _ = fixture(tmp_path)
    validator = validator_module()
    original_read = validator.os.read
    swapped = False

    def swapping_read(fd: int, size: int) -> bytes:
        nonlocal swapped
        data = original_read(fd, size)
        if not swapped:
            replacement = manifest.with_suffix(".replacement")
            replacement.write_bytes(manifest.read_bytes())
            os.replace(replacement, manifest)
            swapped = True
        return data

    monkeypatch.setattr(validator.os, "read", swapping_read)
    with pytest.raises(validator.ValidationError, match="manifest_file_invalid"):
        validator.validate(manifest, root)


@pytest.mark.parametrize("kind", ["hardlink", "directory"])
def test_repeated_rejects_do_not_leak_descriptors(tmp_path: Path, kind: str) -> None:
    proc_fds = Path("/proc/self/fd")
    if not proc_fds.is_dir():
        pytest.skip("/proc/self/fd unavailable")
    root, manifest, _ = fixture(tmp_path)
    if kind == "hardlink":
        os.link(manifest, tmp_path / "manifest-link")
    else:
        manifest.unlink()
        manifest.mkdir()
    validator = validator_module()
    before = len(list(proc_fds.iterdir()))
    for _ in range(20):
        with pytest.raises(validator.ValidationError, match="manifest_file_invalid"):
            validator.validate(manifest, root)
    assert len(list(proc_fds.iterdir())) == before


def test_manifest_replacement_after_read_fails_final_audit(tmp_path: Path, monkeypatch) -> None:
    root, manifest, _ = fixture(tmp_path)
    validator = validator_module()
    original = validator._load_manifest

    def replace_after_read(handle):
        data = original(handle)
        replacement = manifest.with_suffix(".replacement")
        replacement.write_bytes(manifest.read_bytes())
        os.replace(replacement, manifest)
        return data

    monkeypatch.setattr(validator, "_load_manifest", replace_after_read)
    with pytest.raises(validator.ValidationError, match="manifest_file_invalid"):
        validator.validate(manifest, root)


@pytest.mark.parametrize("timing", ["during_read", "after_hash"])
def test_first_canonical_replacement_fails_final_audit(
    tmp_path: Path, monkeypatch, timing: str
) -> None:
    root, manifest, _ = fixture(tmp_path)
    target = root / CANONICAL[0]
    validator = validator_module()
    target_identity = (target.stat().st_dev, target.stat().st_ino)

    def replace() -> None:
        replacement = target.with_suffix(".replacement")
        replacement.write_bytes(target.read_bytes())
        os.replace(replacement, target)

    if timing == "during_read":
        original = validator.os.read
        changed = False

        def scheduled_read(fd: int, size: int) -> bytes:
            nonlocal changed
            raw = original(fd, size)
            info = os.fstat(fd)
            if not changed and (info.st_dev, info.st_ino) == target_identity:
                replace()
                changed = True
            return raw

        monkeypatch.setattr(validator.os, "read", scheduled_read)
    else:
        original_hash = validator._bounded_hash
        changed = False

        def scheduled_hash(fd: int, maximum: int):
            nonlocal changed
            result = original_hash(fd, maximum)
            if not changed:
                replace()
                changed = True
            return result

        monkeypatch.setattr(validator, "_bounded_hash", scheduled_hash)
    with pytest.raises(validator.ValidationError, match="(?:manifest|canonical)_file_invalid"):
        validator.validate(manifest, root)


def test_canonical_ancestor_replacement_after_hash_fails_final_audit(
    tmp_path: Path, monkeypatch
) -> None:
    root, manifest, _ = fixture(tmp_path)
    validator = validator_module()
    original_hash = validator._bounded_hash
    changed = False

    def scheduled_hash(fd: int, maximum: int):
        nonlocal changed
        result = original_hash(fd, maximum)
        if not changed:
            directory = root / "specs/subject-distillation"
            saved = root / "saved-subject-distillation"
            directory.rename(saved)
            shutil.copytree(saved, directory)
            changed = True
        return result

    monkeypatch.setattr(validator, "_bounded_hash", scheduled_hash)
    with pytest.raises(validator.ValidationError, match="(?:manifest|canonical)_file_invalid"):
        validator.validate(manifest, root)


def test_repo_root_path_replacement_with_symlink_fails_final_audit(
    tmp_path: Path, monkeypatch
) -> None:
    root, manifest, _ = fixture(tmp_path / "repo")
    validator = validator_module()
    original = validator._load_manifest

    def replace_root_after_open(handle):
        data = original(handle)
        saved = tmp_path / "saved-repo"
        root.rename(saved)
        root.symlink_to(saved, target_is_directory=True)
        return data

    monkeypatch.setattr(validator, "_load_manifest", replace_root_after_open)
    with pytest.raises(validator.ValidationError, match="repo_root_invalid"):
        validator.validate(manifest, root)


def test_unsupported_secure_filesystem_capability_fails_closed(tmp_path: Path, monkeypatch) -> None:
    root, manifest, _ = fixture(tmp_path)
    validator = validator_module()
    monkeypatch.setattr(validator.os, "supports_dir_fd", set())
    with pytest.raises(validator.ValidationError, match="secure_filesystem_unavailable"):
        validator.validate(manifest, root)


def test_aggregate_canonical_limit_fails_independently(tmp_path: Path, monkeypatch) -> None:
    root, manifest, data = fixture(tmp_path)
    validator = validator_module()
    largest = max(entry["size_bytes"] for entry in data["files"])
    monkeypatch.setattr(validator, "CANONICAL_MAX_BYTES", largest + 1)
    monkeypatch.setattr(validator, "CANONICAL_TOTAL_MAX_BYTES", largest + 1)
    with pytest.raises(validator.ValidationError, match="canonical_file_too_large"):
        validator.validate(manifest, root)


def test_diagnostics_are_bounded_and_do_not_echo_input(tmp_path: Path) -> None:
    sentinel = "UNSAFE-SENTINEL-VALUE"
    root, manifest, data = fixture(tmp_path)
    data["files"][0]["path"] = sentinel
    write_manifest(manifest, data)
    result = run_validator(root, manifest)
    combined = result.stdout + result.stderr
    assert result.returncode == 1 and len(combined) < 256
    assert sentinel not in combined


def test_cli_usage_missing_manifest_and_alternate_manifest_path(tmp_path: Path) -> None:
    malformed = subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root"], text=True, capture_output=True, check=False
    )
    assert malformed.returncode == 2
    assert len(malformed.stderr) < 2048
    root, manifest, _ = fixture(tmp_path)
    manifest.unlink()
    missing = run_validator(root, manifest)
    assert missing.returncode == 1
    assert json.loads(missing.stdout)["code"] == "manifest_file_invalid"
    alternate = root / "alternate.json"
    shutil.copyfile(MANIFEST, alternate)
    rejected = run_validator(root, alternate)
    assert json.loads(rejected.stdout)["code"] == "manifest_path_invalid"
    root, manifest, _ = fixture(tmp_path / "parent")
    real = root / "specs"
    alias = tmp_path / "specs-real"
    real.rename(alias)
    real.symlink_to(alias, target_is_directory=True)
    assert run_validator(root, manifest).returncode == 1


def test_public_package_has_no_stale_private_governance_metadata() -> None:
    paths = [ROOT / p for p in CANONICAL] + [
        MANIFEST,
        VALIDATOR,
        ROOT / "docs/subject-distillation.md",
        ROOT / "tests/test_subject_baseline.py",
    ]
    forbidden = (
        "88" + "cffa9",
        r"\bI" + r"A-[A-Za-z0-9-]+\b",
        r"\bArt" + r"hur\b",
        r"review" + r"-manifest\.json",
        "/ho" + "me/",
        "/Us" + "ers/",
        "owner" + "-only",
        r"R[0-9]+" + r"-P[0-9]+",
        r"\b" + "Rou" + "nd" + r"s?\b",
        r"\b" + "Supple" + "mental" + r"\s+set\b",
        r"\b" + "SUP" + r"-[0-9]",
        "p1" + r"_[0-9]",
        r"\bP1\s+" + "supplemental" + r"\b",
        r"\bP1\s+" + "repair" + r"s?\b",
    )
    for path in paths:
        for pattern in forbidden:
            assert not re.search(pattern, path.read_text(), re.IGNORECASE), (path, pattern)
    canonical_text = "\n".join(path.read_text() for path in paths)
    for forbidden_contract in (
        "Nan" + "cy",
        "--require-implementation-" + "authorized",
        "applicable design " + "lane",
        "applicable plan " + "lane",
        "hash-locked review " + "evidence",
        "Historical review " + "evidence",
        "mechanical_gates_" + "replayed",
    ):
        assert forbidden_contract.lower() not in canonical_text.lower()
    assert not re.search(r"baseline-manifest[^\n]{0,120}\bPASS\b", canonical_text, re.IGNORECASE)
    assert "verify_subject_implementation_authorization.py" in (SPEC / "tasks.md").read_text()
    docs = (ROOT / "docs/subject-distillation.md").read_text()
    assert all(
        term in docs
        for term in (
            "#417",
            "#410",
            "extensible",
            "Organization contract/SBE-only",
            "Runtime is not implemented",
        )
    )
