from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

import pytest

from scripts import artifact_audit, artifact_cleanup, public_pr_gate
from scripts import run_subject_identity_test_isolation as identity_isolation


def test_release_readiness_workflow_trigger_and_concurrency_contract():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    trigger_block = workflow.split("on:\n", 1)[1].split("\npermissions:\n", 1)[0]
    push_block = trigger_block.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
    pull_request_block = trigger_block.split("  pull_request:\n", 1)[1]
    concurrency_block = workflow.split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
    test_job = workflow.split("\n  test:\n", 1)[1].split(
        "\n  readme-command-smoke:\n", 1
    )[0]

    assert "  workflow_dispatch:\n" in trigger_block
    assert "    branches:\n      - 'main'\n" in push_block
    assert "      - '**'\n" not in push_block
    assert "    tags:\n      - 'v*'\n" in push_block
    assert "      - 'specs/**'\n" in push_block
    assert "    branches:\n      - 'main'\n" in pull_request_block
    assert "      - 'specs/**'\n" in pull_request_block
    assert "          fetch-depth: 0\n" in test_job
    assert (
        "  group: release-readiness-${{ github.event.pull_request.number || github.ref }}\n"
        in concurrency_block
    )
    assert "  cancel-in-progress: true\n" in concurrency_block


def test_mission_v5_ci_routes_candidate_and_active_controls_without_skips():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    gate_job = workflow.split("\n  governance-merge-gate:\n", 1)[1]
    test_job = workflow.split("\n  test:\n", 1)[1].split(
        "\n  readme-command-smoke:\n", 1
    )[0]
    mission_test = (root / "tests" / "test_subject_development_mission_v5.py").read_text(
        encoding="utf-8"
    )
    runner = (root / "scripts" / "run_subject_development_mission_v5.py").read_text(
        encoding="utf-8"
    )
    rollback = (
        root
        / "evidence/DEP-SDG-012-MISSION-V5-DISPATCH-PHASE-ISOLATION/rollback.md"
    ).read_text(encoding="utf-8")
    rollback_fields: dict[str, str] = {}
    for raw_line in rollback.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        rollback_fields[key.strip().lower()] = value.strip().strip("`")
    required_rollback_fields = {"rollback_version", "target", "command", "verify"}
    forbidden_rollback_tokens = ("todo", "replace", "unavailable", "<", ">")

    assert required_rollback_fields.issubset(rollback_fields)
    assert rollback_fields["rollback_version"] == "1.0"
    assert all(
        rollback_fields[key]
        and not any(
            token in rollback_fields[key].lower()
            for token in forbidden_rollback_tokens
        )
        for key in ("target", "command", "verify")
    )
    assert rollback.count("\ntarget:") == 1
    assert rollback.count("\ncommand:") == 1
    assert rollback.count("\nverify:") == 1
    assert (
        'Path("evidence/DEP-SDG-012-MISSION-V5-DISPATCH-PHASE-ISOLATION/'
        'rollback.md")'
        in rollback_fields["command"]
    )
    assert '.split("```bash\\n",1)[1].split("\\n```",1)[0]' in rollback_fields[
        "command"
    ]
    assert '["/bin/bash","-euo","pipefail","-c",block]' in rollback_fields[
        "command"
    ]
    for value in (
        'git symbolic-ref --quiet --short HEAD)" = main',
        "git status --porcelain=v1 --untracked-files=all",
        "9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0^{tree}",
        "specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json",
        "specs/subject-distillation/.task-authorization.pending",
        "git diff --check",
    ):
        assert value in rollback_fields["verify"]

    assert "continue-on-error" not in gate_job
    assert "--deselect" not in gate_job
    assert test_job.count("--ignore=tests/test_subject_development_mission_v5.py") == 1
    assert (
        test_job.count("--ignore=tests/test_subject_task_authorization_dispatch_v5.py")
        == 1
    )
    assert "Run candidate Mission V5 identity controls" in test_job
    assert "--phase candidate" in test_job
    assert "Run active Mission V5 identity controls" in test_job
    assert "--phase active" in test_job
    assert "validate_mission_activation_candidate(" in mission_test
    assert "validate_mission_activation_delivery(" in mission_test
    assert "replay_commit = protocol_base" in mission_test
    assert "replay_commit = mission.validate_mission_activation_delivery(" in mission_test
    dispatcher_source = (
        root / "tests" / "test_subject_task_authorization_dispatch_v5.py"
    ).read_text(encoding="utf-8")
    dispatcher_tree = ast.parse(dispatcher_source)
    dispatcher_functions = {
        node.name: node
        for node in dispatcher_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    exact_dispatcher_nodes = tuple(
        "tests/test_subject_task_authorization_dispatch_v5.py::" + name
        for name in dispatcher_functions
        if name.startswith("test_")
    )
    assert exact_dispatcher_nodes == identity_isolation.DISPATCHER_NODES
    authorization_test = dispatcher_functions[
        "test_dispatch_accepts_exact_current_mission_phase"
    ]
    authorization_assertions = {
        ast.unparse(node.test)
        for node in ast.walk(authorization_test)
        if isinstance(node, ast.Assert)
    }
    authorization_calls = [
        ast.unparse(node.func)
        for node in ast.walk(authorization_test)
        if isinstance(node, ast.Call)
    ]
    assert "dispatch.validate(ROOT) == expected" in authorization_assertions
    assert authorization_calls.count("dispatch.validate") == 1
    cli_test = dispatcher_functions[
        "test_dispatch_cli_is_exact_and_no_abbreviation"
    ]
    cli_assertions = {
        ast.unparse(node.test)
        for node in ast.walk(cli_test)
        if isinstance(node, ast.Assert)
    }
    cli_calls = [
        ast.unparse(node.func)
        for node in ast.walk(cli_test)
        if isinstance(node, ast.Call)
    ]
    assert "dispatch.main(['--ledger', '--json']) == 0" in cli_assertions
    assert "dispatch.main(['--led', '--json']) == 2" in cli_assertions
    assert cli_calls.count("dispatch.main") == 2
    fixture = dispatcher_functions["_phase_neutral_dispatch_root"]
    phase_branch = next(
        node
        for node in fixture.body
        if isinstance(node, ast.If)
        and ast.unparse(node.test) == "_mission_phase() == CANDIDATE_PHASE"
    )
    candidate_tree = ast.Module(body=phase_branch.body, type_ignores=[])
    active_tree = ast.Module(body=phase_branch.orelse, type_ignores=[])
    candidate_calls = [
        ast.unparse(node.func)
        for node in ast.walk(candidate_tree)
        if isinstance(node, ast.Call)
    ]
    active_calls = [
        ast.unparse(node.func)
        for node in ast.walk(active_tree)
        if isinstance(node, ast.Call)
    ]
    assert candidate_calls.count(
        "mission.validate_mission_activation_candidate"
    ) == 1
    assert "mission.validate_mission_activation_delivery" not in candidate_calls
    assert active_calls.count("mission.validate_mission_activation_delivery") == 1
    candidate_assignments = {
        (ast.unparse(target), ast.unparse(node.value))
        for node in ast.walk(candidate_tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
    }
    assert ("replay_commit", "protocol_base") in candidate_assignments
    assert ("replay_commit", "candidate_commit") in candidate_assignments
    semantic_names = {
        ast.unparse(node)
        for node in ast.walk(dispatcher_tree)
        if isinstance(node, ast.Attribute)
    } | {
        ast.unparse(node.func)
        for node in ast.walk(dispatcher_tree)
        if isinstance(node, ast.Call)
    }
    assert {
        "pytest.mark.skip",
        "pytest.mark.skipif",
        "pytest.mark.xfail",
        "pytest.skip",
        "pytest.xfail",
        "pytest.importorskip",
    }.isdisjoint(semantic_names)
    identity_isolation._validate_dispatcher_source(dispatcher_source)
    assert "def validate_mission_activation_topic(" in runner
    assert "len(deliveries) != 1" in runner
    isolation = (root / "scripts" / "run_subject_identity_test_isolation.py").read_text(
        encoding="utf-8"
    )
    assert "ArgumentParser(allow_abbrev=False)" in isolation
    assert 'choices=("candidate", "active")' in isolation
    assert "SUBJECT_MISSION_V5_PHASE" in isolation
    assert (
        '("tests/test_subject_task_authorization_dispatch_v5.py", 2)' in isolation
    )
    assert sum(count for _path, count in identity_isolation.FILES) == 446
    assert identity_isolation.DISPATCHER_NODES == exact_dispatcher_nodes
    for value in (
        'canonical_origin="https://github.com/zycaskevin/Vault-Agent-Memory.git"',
        'test "$(git symbolic-ref --quiet --short HEAD)" = "main"',
        'git fetch --no-tags origin main',
        'test "$(git rev-parse HEAD)" = "$merge_commit"',
        'test "$(git rev-parse refs/remotes/origin/main)" = "$merge_commit"',
        'test "$(git rev-list --parents -n 1 "$merge_commit")" = "$merge_commit $protocol_base $topic_commit"',
        'test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$topic_commit^{tree}")"',
        'reviewed_source="$(git -C "$rollback_tmp/retained" show "$merge_commit:.sddgov/merge-gate.json"',
        'assert_node_pass candidate candidate-authority "$node_authority"',
        'assert_node_pass active active-authority "$node_authority"',
        'malformed active fixture was not denied',
        'git revert --no-edit -m 1 "$merge_commit"',
        'test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$merge_commit^1^{tree}")"',
        'assert_node_pass candidate reverted-inactive-authority "$node_authority"',
        '"mission_state": "INACTIVE"',
        '"sequence": 6',
        'progress["tasks"]["T-004"] == "PENDING"',
        'not (root / mission.PENDING_PATH).exists()',
        'not (root / mission.MISSION_PROOF_PATH).exists()',
        '-o xfail_strict=true --junitxml="$junit"',
        '"tests": "1", "skipped": "0", "failures": "0", "errors": "0"',
    ):
        assert value in rollback
    assert rollback.index("assert_node_pass active active-cli") < rollback.index(
        'git revert --no-edit -m 1 "$merge_commit"'
    )
    assert rollback.index('git revert --no-edit -m 1 "$merge_commit"') < rollback.index(
        "reverted-inactive-authority"
    )
    proof_installer = rollback.split(
        "install_reviewed_proof_fixture_bytes() {", 1
    )[1].split("\n}", 1)[0]
    baseline_installer = rollback.split("install_reviewed_baseline_bytes() {", 1)[
        1
    ].split("\n}", 1)[0]
    pre_revert = rollback.split("# Phase proof happens before the revert", 1)[1].split(
        "# Only now mutate canonical main", 1
    )[0]
    post_revert = rollback.split("# Only now mutate canonical main", 1)[1]
    assert "run_subject_development_mission_v5.py" not in proof_installer
    assert "run_subject_development_mission_v5.py" in baseline_installer
    assert pre_revert.count("install_reviewed_proof_fixture_bytes") == 3
    assert "install_reviewed_baseline_bytes" not in pre_revert
    assert "install_reviewed_baseline_bytes" in post_revert
    for path in (
        "scripts/update_subject_task_progress_v5.py",
        "scripts/validate_subject_development_mission_v5.py",
        "scripts/validate_subject_task_authorization_dispatch_v5.py",
    ):
        production_tree = ast.parse((root / path).read_text(encoding="utf-8"))
        assert "SUBJECT_MISSION_V5_PHASE" not in {
            node.value
            for node in ast.walk(production_tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }


def test_identity_phase_cli_is_closed_and_exact():
    assert identity_isolation._arguments(["--phase", "candidate"]).phase == "candidate"
    assert identity_isolation._arguments(["--phase", "active"]).phase == "active"
    with pytest.raises(SystemExit):
        identity_isolation._arguments(["--phase", "candid"])
    with pytest.raises(SystemExit):
        identity_isolation._arguments([])


def test_sdg011_pins_exact_sdg010_delivery_and_executable_rollback() -> None:
    root = Path(__file__).resolve().parents[1]
    runner = (root / "scripts/run_subject_development_mission_v5.py").read_text(
        encoding="utf-8"
    )
    rollback = (
        root
        / "evidence/DEP-SDG-010-MISSION-V5-CI-PHASE-ROUTING/rollback.md"
    ).read_text(encoding="utf-8")
    sdg011_release = "9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0"
    historical_workflow = subprocess.check_output(
        ["git", "show", f"{sdg011_release}:.github/workflows/ci.yml"],
        cwd=root,
        text=True,
    )

    exact_values = {
        "SDG010_BASE": "46690372e532c50761f9232ff5b2e20e18779d28",
        "SDG010_TOPIC": "7e155ca8907b31a14d5abadeeeb73e3edac71c14",
        "SDG010_RELEASE": "efa43a4dfb305cd51d8a57a20838be6123ccb514",
        "SDG010_TREE": "781beb6d3f8ef626d058394d14103c9512550637",
        "SDG010_GATE_SHA256": (
            "bd7b1935271533653a1cbae1a35032d444009b4387ffe327e6ed5d5757ed6658"
        ),
        "SDG010_RECEIPT_SHA256": (
            "07ee1f5845be27aa81e7c8b4257d98ec22b7047e3d0e1020583f9acac484ead4"
        ),
    }
    for name, value in exact_values.items():
        assert f'{name} = "{value}"' in runner
    assert '("tests/test_subject_development_mission_v5.py", 90)' in (
        root / "scripts/run_subject_identity_test_isolation.py"
    ).read_text(encoding="utf-8")

    for value in (
        "gh pr view 484",
        'row.get("state")=="MERGED"',
        'row.get("baseRefName")=="main"',
        'row.get("baseRefOid")=="46690372e532c50761f9232ff5b2e20e18779d28"',
        'row.get("headRefName")=="agent/sdg010-mission-v5-ci-phase-routing-v4"',
        'row.get("headRefOid")=="7e155ca8907b31a14d5abadeeeb73e3edac71c14"',
        'merge=="efa43a4dfb305cd51d8a57a20838be6123ccb514"',
        (
            "efa43a4dfb305cd51d8a57a20838be6123ccb514 "
            "46690372e532c50761f9232ff5b2e20e18779d28 "
            "7e155ca8907b31a14d5abadeeeb73e3edac71c14"
        ),
        "7e155ca8907b31a14d5abadeeeb73e3edac71c14^{tree}",
    ):
        assert value in rollback
    assert 'branch="agent/sdg010-mission-v5-ci-phase-routing"' not in rollback
    for digest, path in (
        (
            "05f60c7950ba3c5025fb26f43d18b680ccdbe0ab42c07d1886fa5153ff0dad05",
            "scripts/run_subject_development_mission_v5.py",
        ),
        (
            "de169a26c04130d07219ca427e0fcf34b809868156f815181bac11ea6a0f32a5",
            "scripts/run_subject_identity_test_isolation.py",
        ),
        (
            "fad00cb5058f80fd074553ec399e72a76f91c113d42569a4ce6d606fa301dbc7",
            "evidence/DEP-SDG-010-MISSION-V5-CI-PHASE-ROUTING/rollback.md",
        ),
    ):
        assert f"{digest}  {path}" in historical_workflow


def test_subject_progress_ci_separates_historical_and_current_phases():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    test_job = workflow.split("\n  test:\n", 1)[1].split(
        "\n  readme-command-smoke:\n", 1
    )[0]

    assert test_job.count("      - name: Run current-state tests\n") == 1
    ignored = {
        "tests/test_subject_progress.py",
        "tests/test_subject_task_authorization_dispatch.py",
        "tests/test_subject_development_mission_v4.py",
        "tests/test_subject_task_authorization_dispatch_v4.py",
        "tests/test_subject_development_mission_v5.py",
        "tests/test_subject_task_authorization_dispatch_v5.py",
    }
    for path in ignored:
        assert test_job.count(f"--ignore={path}") == 1
    assert test_job.count("--ignore=") == len(ignored)
    assert "--deselect" not in test_job
    assert "continue-on-error" not in test_job
    assert " -k " not in test_job
    assert "xfail" not in test_job.lower()

    assert (
        "SUBJECT_PRE_T002_CHECKPOINT: "
        "8ec045a7b39c5aa9684f61d9099eb62b3142983d"
    ) in test_job
    assert (
        "T001_PROGRESS_TEST_SHA256: "
        "6be4d93375205ee1f9ba414aa2704ee075ca583050238892d54030e7adadd3e6"
    ) in test_job
    assert (
        "T001_PROGRESS_VALIDATOR_SHA256: "
        "8cb33ef1f9b688be90fb093e0fd4437b245c2a9b2dbac3f3141c65005619416f"
    ) in test_job
    assert (
        "T001_PROGRESS_LEDGER_SHA256: "
        "ab723c1adde2739f54deba7fee85d86a95002f167703354695503363154d30e6"
    ) in test_job
    assert (
        'git merge-base --is-ancestor "$SUBJECT_PRE_T002_CHECKPOINT" HEAD'
        in test_job
    )
    assert (
        'git worktree add --detach "$replay_root" "$SUBJECT_PRE_T002_CHECKPOINT"'
        in test_job
    )
    assert "tests/test_subject_progress.py | sha256sum -c -" in test_job
    assert "scripts/validate_subject_progress.py | sha256sum -c -" in test_job
    assert (
        "specs/subject-distillation/implementation-progress.json | sha256sum -c -"
        in test_job
    )
    assert (
        "PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \\\n"
        "            tests/test_subject_progress.py"
    ) in test_job
    assert (
        "python scripts/validate_subject_progress.py \\\n"
        "            --manifest specs/subject-distillation/baseline-manifest.json"
    ) in test_job
    assert (
        "python scripts/validate_subject_task_authorization_dispatch.py \\\n"
        "            --ledger"
    ) in test_job
    trust_pins = {
        "scripts/validate_subject_task_authorization_dispatch.py": "0e455b726ee09f35283f1975ad30a08d988a71ddc71efb0fd02fdba09a922f33",
        "scripts/run_subject_task_authorization_v3.py": "7076d547be933c30e2e8321a3ee47799794137dfe295e6f09f558373cf959b8c",
        "scripts/update_subject_task_progress_v3.py": "ef0cc8fe7e2fe27928160c28cb92821ac85dbe549acce3f3bf9e7a9528b969ab",
        "scripts/validate_subject_task_authorization_v3.py": "1251ff4f35373ed8a5b54403f971fa54c3bc71b0b062f0caa939ed1415b2f01b",
        "specs/subject-distillation/task-authorization-v3.contract.json": "9ff7ddceffdde6690fce4acf1b1f9d16f2d0f93412f5e5f55d94d118b7af5c5a",
        "specs/subject-distillation/task-authorization-v3.schema.json": "f226e841e2e5442d9a2fe4443762764c984f409699d696e66cbe49aec79177df",
        "specs/subject-distillation/task-scopes/T-003.json": "7bf80b0b2e0abf1a762663ca179361ef65d1bcaa5a2af373697f6a22dca1e359",
        "tests/test_subject_task_authorization_dispatch.py": "8601f9ff2b8475c6c9eda577cd27c26fe3c6665f3cf9ad9174dedb5975448616",
    }
    for path, digest in trust_pins.items():
        assert f"{digest}  {path}" in test_job
    assert "cat <<'EOF' | sha256sum -c -" in test_job
    assert (
        "PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \\\n"
        "            tests/test_subject_task_authorization_dispatch.py"
    ) in test_job
    assert "validate_subject_task_authorization_v2.py \\\n" not in test_job
    assert (
        "SUBJECT_V4_ACTIVATION_CHECKPOINT: "
        "03dcdabc873658cd7de24dfeeef8b85090cf2321"
    ) in test_job
    assert (
        'git worktree add --detach "$replay_root" '
        '"$SUBJECT_V4_ACTIVATION_CHECKPOINT"'
    ) in test_job
    assert (
        "tests/test_subject_development_mission_v4.py \\\n"
        "            tests/test_subject_task_authorization_dispatch_v4.py"
    ) in test_job
    assert (
        "python scripts/validate_subject_task_authorization_dispatch_v5.py \\\n"
        "            --ledger"
    ) in test_job


def test_artifact_audit_classifies_safe_generated_cache(tmp_path: Path):
    pycache = tmp_path / "pkg" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "module.cpython-311.pyc").write_bytes(b"cache")
    pytest_cache = tmp_path / ".pytest_cache"
    pytest_cache.mkdir()
    (pytest_cache / "README.md").write_text("cache", encoding="utf-8")

    report = artifact_audit.audit_repo(tmp_path)

    safe_paths = {item["path"] for item in report["safe_delete"]}
    assert "pkg/__pycache__" in safe_paths
    assert ".pytest_cache" in safe_paths
    assert report["summary"]["safe_delete_files"] == 2
    assert report["summary"]["safe_delete_bytes"] == len(b"cache") + len("cache")


def test_artifact_audit_classifies_graphify_cache_safe_but_full_graph_review(tmp_path: Path):
    cache = tmp_path / "graphify-out" / "cache"
    cache.mkdir(parents=True)
    (cache / "ast.json").write_text("{}", encoding="utf-8")
    (tmp_path / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")

    report = artifact_audit.audit_repo(tmp_path)

    assert any(item["path"] == "graphify-out/cache" for item in report["safe_delete"])
    assert any(item["path"] == "graphify-out" for item in report["needs_review"])


def test_artifact_cleanup_dry_run_does_not_delete_and_execute_deletes_safe_only(tmp_path: Path):
    pycache = tmp_path / "pkg" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "module.pyc").write_bytes(b"cache")
    opencode = tmp_path / ".opencode" / "node_modules"
    opencode.mkdir(parents=True)
    (opencode / "keep.js").write_text("keep", encoding="utf-8")

    dry_run = artifact_cleanup.cleanup_repo(tmp_path, execute=False, include_large=False)
    assert pycache.exists()
    assert dry_run["summary"]["deleted_files"] == 0
    assert any(item["path"] == "pkg/__pycache__" for item in dry_run["would_delete"])
    assert any(item["path"] == ".opencode" for item in dry_run["needs_review"])

    executed = artifact_cleanup.cleanup_repo(tmp_path, execute=True, include_large=False)
    assert not pycache.exists()
    assert opencode.exists()
    assert executed["summary"]["deleted_files"] == 1


def test_artifact_cleanup_keeps_generic_build_dir_for_review(tmp_path: Path):
    build = tmp_path / "pkg" / "build"
    build.mkdir(parents=True)
    (build / "source_of_truth.py").write_text("important", encoding="utf-8")

    dry_run = artifact_cleanup.cleanup_repo(tmp_path, execute=False)
    assert not any(item["path"] == "pkg/build" for item in dry_run["would_delete"])
    assert any(item["path"] == "pkg/build" for item in dry_run["needs_review"])

    artifact_cleanup.cleanup_repo(tmp_path, execute=True)
    assert build.exists()
    assert (build / "source_of_truth.py").exists()


def test_public_pr_gate_flags_forbidden_files_and_private_added_lines():
    home_path = "/".join(["", "home", "example_user", "private"])  # noqa: FLY002
    channel_key = "chat" + "_id"
    channel_value = "oc_" + "123abc"
    diff = f"""diff --git a/PROGRESS.md b/PROGRESS.md
+++ b/PROGRESS.md
@@ -0,0 +1,3 @@
+Internal path {home_path}
+review channel {channel_key} {channel_value}
+normal public text
"""

    report = public_pr_gate.scan_diff(diff, target_visibility="public")

    kinds = {finding["kind"] for finding in report["findings"]}
    assert "forbidden_file" in kinds
    assert "local_path" in kinds
    assert "private_platform_context" in kinds
    assert report["passed"] is False


def test_public_pr_gate_passes_clean_public_diff():
    diff = """diff --git a/docs/example.md b/docs/example.md
+++ b/docs/example.md
@@ -0,0 +1,2 @@
+This is a public-safe example for a local review channel.
+No generic runtime or user-specific path is included.
"""

    report = public_pr_gate.scan_diff(diff, target_visibility="public")

    assert report["passed"] is True
    assert report["findings"] == []


def test_public_pr_gate_flags_deleted_private_payload_and_rename_paths():
    private_dir = "." + "agent-runtime"
    user_path = "/".join(  # noqa: FLY002 - keep scanner fixture non-literal
        ["", "Users", "example_user", "private", "project"]
    )
    secret_key = "ACCESS" + "_TOKEN"
    secret_value = "example" + "_secret_value_123"
    diff = f"""diff --git a/{private_dir}/secret.md b/docs/secret.md
similarity index 100%
rename from {private_dir}/secret.md
rename to docs/secret.md
diff --git a/docs/old.md b/docs/old.md
--- a/docs/old.md
+++ b/docs/old.md
@@ -1,2 +1,2 @@
-{user_path}
-{secret_key}={secret_value}
+public replacement
"""

    report = public_pr_gate.scan_diff(diff, target_visibility="public")

    kinds = {finding["kind"] for finding in report["findings"]}
    assert "forbidden_file" in kinds
    assert "local_path" in kinds
    assert "secret_literal" in kinds
    assert report["passed"] is False


def test_public_pr_gate_cleanup_mode_allows_removing_existing_internal_artifacts():
    private_dir = "." + "agent-runtime"
    user_path = "/".join(  # noqa: FLY002 - keep scanner fixture non-literal
        ["", "home", "example_user", "private", "project"]
    )
    diff = f"""diff --git a/PROGRESS.md b/PROGRESS.md
deleted file mode 100644
--- a/PROGRESS.md
+++ /dev/null
@@ -1,2 +0,0 @@
-{user_path}
-{private_dir}/runtime-note
diff --git a/raw/example.md b/examples/knowledge/example.md
similarity index 100%
rename from raw/example.md
rename to examples/knowledge/example.md
diff --git a/docs/note.md b/docs/note.md
--- a/docs/note.md
+++ b/docs/note.md
@@ -1,2 +1,2 @@
-{private_dir} legacy mention
+public-safe replacement
"""

    strict = public_pr_gate.scan_diff(diff, target_visibility="public")
    cleanup = public_pr_gate.scan_diff(
        diff,
        target_visibility="public",
        allow_cleanup_deletions=True,
    )

    assert strict["passed"] is False
    assert cleanup["passed"] is True
    assert cleanup["findings"] == []


def test_public_pr_gate_flags_internal_data_dirs_worklogs_and_runtime_dbs():
    diff = """diff --git a/raw/private.md b/raw/private.md
+++ b/raw/private.md
@@ -0,0 +1 @@
+synthetic clean text
diff --git a/compiled/private.md b/compiled/private.md
+++ b/compiled/private.md
@@ -0,0 +1 @@
+synthetic clean text
diff --git a/runtime/state.sqlite b/runtime/state.sqlite
+++ b/runtime/state.sqlite
@@ -0,0 +1 @@
+synthetic clean text
diff --git a/vault.db b/vault.db
+++ b/vault.db
@@ -0,0 +1 @@
+synthetic clean text
diff --git a/worklogs/private.md b/worklogs/private.md
+++ b/worklogs/private.md
@@ -0,0 +1 @@
+synthetic clean text
"""

    report = public_pr_gate.scan_diff(diff, target_visibility="public")

    forbidden_paths = {finding["path"] for finding in report["findings"] if finding["kind"] == "forbidden_file"}
    assert {
        "raw/private.md",
        "compiled/private.md",
        "runtime/state.sqlite",
        "vault.db",
        "worklogs/private.md",
    }.issubset(forbidden_paths)
    assert report["passed"] is False


def test_public_pr_gate_flags_windows_user_paths():
    drive_user_path = "C:" + "\\" + "Users" + "\\" + "example_user" + "\\" + "private" + "\\" + "project"
    diff = f"""diff --git a/docs/path.md b/docs/path.md
+++ b/docs/path.md
@@ -0,0 +1 @@
+{drive_user_path}
"""

    report = public_pr_gate.scan_diff(diff, target_visibility="public")

    kinds = {finding["kind"] for finding in report["findings"]}
    assert "local_path" in kinds
    assert report["passed"] is False


def test_public_pr_gate_cli_json_for_stdin(monkeypatch, capsys):
    secret_key = "tok" + "en"
    secret_value = "abc" + "123456"
    monkeypatch.setattr(
        "sys.stdin",
        type("FakeStdin", (), {"read": lambda self: f"+++ b/AUDIT_REPORT.md\n+{secret_key}='{secret_value}'\n"})(),
    )

    code = public_pr_gate.main(["--stdin", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["passed"] is False
    assert {item["kind"] for item in payload["findings"]} >= {"forbidden_file", "secret_literal"}
