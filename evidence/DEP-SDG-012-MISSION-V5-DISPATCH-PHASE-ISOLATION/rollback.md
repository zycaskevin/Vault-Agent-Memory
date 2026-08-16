# Rollback

## Trigger

Any candidate authority regression, active replay regression, missing/duplicate
dispatcher node, count drift, CI pin drift, or required verification failure.

## Reversible steps

rollback_version: 1.1
target: the one exact merged Pull Request from agent/sdg012-mission-v5-dispatch-phase-isolation-v2 in zycaskevin/Vault-Agent-Memory

Run the following from the canonical repository. It fails closed unless the
operator is on symbolic `main`, canonical `origin` has the exact HTTPS URL, the
worktree and untracked set are empty, a fresh fetch makes `HEAD` and
`origin/main` equal the one exact delivery merge, and that merge has exact base,
parent order, and topic-tree equality.

```bash
set -euo pipefail
canonical_repo="zycaskevin/Vault-Agent-Memory"
canonical_origin="https://github.com/zycaskevin/Vault-Agent-Memory.git"
branch="agent/sdg012-mission-v5-dispatch-phase-isolation-v2"
protocol_base="9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0"
activation_topic="6e596574f48354cdf6ccdc72bce35d3b6df1c184"
activation_ref="refs/pull/487/head"
node_authority="tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_accepts_exact_current_mission_phase"
node_cli="tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_cli_is_exact_and_no_abbreviation"

test "$(gh repo view --json nameWithOwner --jq .nameWithOwner)" = "$canonical_repo"
test "$(git remote get-url origin)" = "$canonical_origin"
test "$(git remote get-url --push origin)" = "$canonical_origin"
test "$(git symbolic-ref --quiet --short HEAD)" = "main"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch --no-tags origin main
test -z "$(git status --porcelain=v1 --untracked-files=all)"

pr_number="$(gh pr list --repo "$canonical_repo" --head "$branch" --state merged --limit 100 --json number | python -c 'import json,sys; rows=json.load(sys.stdin); assert len(rows)==1, "expected one exact merged PR"; print(rows[0]["number"])')"
pr_json="$(gh pr view "$pr_number" --repo "$canonical_repo" --json state,baseRefName,baseRefOid,headRefName,headRefOid,mergeCommit)"
read -r merge_commit topic_commit <<EOF
$(printf '%s' "$pr_json" | python -c 'import json,sys; row=json.load(sys.stdin); assert row.get("state")=="MERGED"; assert row.get("baseRefName")=="main"; assert row.get("baseRefOid")=="9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0"; assert row.get("headRefName")=="agent/sdg012-mission-v5-dispatch-phase-isolation-v2"; merge=(row.get("mergeCommit") or {}).get("oid"); topic=row.get("headRefOid"); assert isinstance(merge,str) and len(merge)==40; assert isinstance(topic,str) and len(topic)==40; print(merge, topic)')
EOF
test "$(git rev-parse HEAD)" = "$merge_commit"
test "$(git rev-parse refs/remotes/origin/main)" = "$merge_commit"
test "$(git rev-list --parents -n 1 "$merge_commit")" = "$merge_commit $protocol_base $topic_commit"
test "$(git rev-parse "$merge_commit^{tree}")" = "$(git rev-parse "$topic_commit^{tree}")"

rollback_tmp="$(mktemp -d "${TMPDIR:-/tmp}/sdg012-rollback.XXXXXX")"
chmod 700 "$rollback_tmp"
cleanup() { rm -rf -- "$rollback_tmp"; }
trap cleanup EXIT HUP INT TERM
git clone --quiet --no-hardlinks --no-checkout . "$rollback_tmp/retained"
git -C "$rollback_tmp/retained" checkout --quiet --detach "$merge_commit"
git -C "$rollback_tmp/retained" remote set-url origin "$canonical_origin"

reviewed_source="$(git -C "$rollback_tmp/retained" show "$merge_commit:.sddgov/merge-gate.json" | python -c 'import json,sys; gate=json.load(sys.stdin); head=gate.get("head_sha"); assert isinstance(head,str) and len(head)==40; print(head)')"
git -C "$rollback_tmp/retained" merge-base --is-ancestor "$reviewed_source" "$topic_commit"
mkdir -p "$rollback_tmp/bytes/scripts" "$rollback_tmp/bytes/tests"
for path in scripts/run_subject_development_mission_v5.py scripts/run_subject_identity_test_isolation.py tests/test_subject_task_authorization_dispatch_v5.py; do
  git -C "$rollback_tmp/retained" show "$reviewed_source:$path" > "$rollback_tmp/bytes/$path"
  test "$(git -C "$rollback_tmp/retained" show "$reviewed_source:$path" | shasum -a 256 | cut -d ' ' -f 1)" = "$(git -C "$rollback_tmp/retained" show "$merge_commit:$path" | shasum -a 256 | cut -d ' ' -f 1)"
done

assert_node_pass() {
  phase="$1"
  slug="$2"
  node="$3"
  junit="$rollback_tmp/$slug.xml"
  SUBJECT_MISSION_V5_PHASE="$phase" PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider -o xfail_strict=true --junitxml="$junit" "$node"
  JUNIT_XML="$junit" python - <<'PY'
import os
import xml.etree.ElementTree as ET
root = ET.parse(os.environ["JUNIT_XML"]).getroot()
suites = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "testsuite" and node.attrib.get("tests") is not None]
cases = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "testcase"]
assert len(suites) == len(cases) == 1
suite = suites[0]
assert {name: suite.attrib.get(name, "0") for name in ("tests", "skipped", "failures", "errors")} == {"tests": "1", "skipped": "0", "failures": "0", "errors": "0"}
assert not any(child.tag.rsplit("}", 1)[-1] in {"skipped", "failure", "error"} for child in cases[0])
PY
}

install_reviewed_proof_fixture_bytes() {
  install -m 0755 "$rollback_tmp/bytes/scripts/run_subject_identity_test_isolation.py" scripts/run_subject_identity_test_isolation.py
  install -m 0644 "$rollback_tmp/bytes/tests/test_subject_task_authorization_dispatch_v5.py" tests/test_subject_task_authorization_dispatch_v5.py
  python -c 'from pathlib import Path; from scripts import run_subject_identity_test_isolation as h; expected=("tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_accepts_exact_current_mission_phase", "tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_cli_is_exact_and_no_abbreviation"); assert h.DISPATCHER_NODES == expected; h._validate_dispatcher_source(Path("tests/test_subject_task_authorization_dispatch_v5.py").read_text(encoding="utf-8"))'
}

install_reviewed_baseline_bytes() {
  install_reviewed_proof_fixture_bytes
  install -m 0755 "$rollback_tmp/bytes/scripts/run_subject_development_mission_v5.py" scripts/run_subject_development_mission_v5.py
}

restore_fixture_tree() {
  git restore --source=HEAD --staged --worktree -- scripts/run_subject_development_mission_v5.py scripts/run_subject_identity_test_isolation.py tests/test_subject_task_authorization_dispatch_v5.py
}

# Phase proof happens before the revert, using immutable reviewed SDG-012 bytes.
git -C "$rollback_tmp/retained" fetch --no-tags origin "$activation_ref"
test "$(git -C "$rollback_tmp/retained" rev-parse FETCH_HEAD)" = "$activation_topic"
cd "$rollback_tmp/retained"
git checkout --quiet --detach "$activation_topic"
# The Mission proof binds this topic's runner bytes. Retain and hash the reviewed
# SDG-012 runner above, but do not overlay it into proof-bearing topologies.
install_reviewed_proof_fixture_bytes
assert_node_pass candidate candidate-authority "$node_authority"
assert_node_pass candidate candidate-cli "$node_cli"
restore_fixture_tree

active_commit="$(printf '%s\n' 'SDG-012 rollback exact active fixture' | GIT_AUTHOR_NAME=sdg012-rollback GIT_AUTHOR_EMAIL=sdg012-rollback@example.invalid GIT_COMMITTER_NAME=sdg012-rollback GIT_COMMITTER_EMAIL=sdg012-rollback@example.invalid git commit-tree "$activation_topic^{tree}" -p "$protocol_base" -p "$activation_topic")"
git checkout --quiet --detach "$active_commit"
install_reviewed_proof_fixture_bytes
assert_node_pass active active-authority "$node_authority"
assert_node_pass active active-cli "$node_cli"
restore_fixture_tree

malformed_commit="$(printf '%s\n' 'SDG-012 rollback malformed active fixture' | GIT_AUTHOR_NAME=sdg012-rollback GIT_AUTHOR_EMAIL=sdg012-rollback@example.invalid GIT_COMMITTER_NAME=sdg012-rollback GIT_COMMITTER_EMAIL=sdg012-rollback@example.invalid git commit-tree "$protocol_base^{tree}" -p "$protocol_base" -p "$activation_topic")"
git checkout --quiet --detach "$malformed_commit"
install_reviewed_proof_fixture_bytes
git show "$activation_topic:specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json" > "$rollback_tmp/mission-proof.json"
PROTOCOL_BASE="$protocol_base" MISSION_RAW="$rollback_tmp/mission-proof.json" python - <<'PY'
import os
from pathlib import Path
from scripts import run_subject_development_mission_v5 as mission
try:
    mission.validate_mission_activation_delivery(Path.cwd(), protocol_base=os.environ["PROTOCOL_BASE"], mission_raw=Path(os.environ["MISSION_RAW"]).read_bytes())
except mission.Denied:
    pass
else:
    raise AssertionError("malformed active fixture was not denied")
PY

# Only now mutate canonical main. The post-revert proof is explicitly limited
# to base-compatible INACTIVE behavior with the retained reviewed test bytes.
cd - >/dev/null
git revert --no-edit -m 1 "$merge_commit"
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$merge_commit^1^{tree}")"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git clone --quiet --no-hardlinks . "$rollback_tmp/reverted"
cd "$rollback_tmp/reverted"
git remote set-url origin "$canonical_origin"
install_reviewed_baseline_bytes
assert_node_pass candidate reverted-inactive-authority "$node_authority"
assert_node_pass candidate reverted-inactive-cli "$node_cli"
python - <<'PY'
from pathlib import Path
from scripts import run_subject_development_mission_v5 as mission
from scripts import validate_subject_task_authorization_dispatch_v5 as dispatch
root = Path.cwd()
result = dispatch.validate(root)
assert result == {"active": False, "mission_id": None, "mission_state": "INACTIVE", "protocol_version": 5, "sequence": 6, "status": "PASS"}
progress = mission._parse((root / mission.PROGRESS_PATH).read_bytes())
assert len(progress["events"]) == 6
assert progress["tasks"]["T-004"] == "PENDING"
assert not (root / mission.PENDING_PATH).exists()
assert not (root / mission.MISSION_PROOF_PATH).exists()
PY
cd - >/dev/null
git diff --check
test -z "$(git status --porcelain=v1 --untracked-files=all)"
```

The candidate/active/malformed phase proof is deliberately completed before
the revert with the exact reviewed SDG-012 test and outcome harness, while the
Mission proof's own trust-root runner bytes remain untouched. The reviewed
runner is still retained and hash-bound, but it is executed only after revert
on the no-proof baseline. The new tree must equal the delivery merge's
first-parent tree; retained reviewed bytes then establish exact `INACTIVE`,
sequence 6, T-004 `PENDING`, and absent pending/proof files. Every dispatcher
node invocation writes a unique JUnit file and requires exactly one real pass
with zero skips, xfails, failures, or errors.

Never rewrite history. Use only before any proposal/proof is bound to the
SDG-012 release. After that, regenerate authority through the governed protocol
instead of blind revert.
