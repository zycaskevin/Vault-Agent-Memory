# Rollback

## Trigger

Any candidate authority regression, active replay regression, missing/duplicate
dispatcher node, count drift, CI pin drift, or required verification failure.

## Reversible steps

rollback_version: 1.0
target: exact merged SDG-012 v4 branch delivery on canonical main before Mission proof use
command: python -c 'from pathlib import Path; import subprocess; p=Path("evidence/DEP-SDG-012-MISSION-V5-DISPATCH-PHASE-ISOLATION/rollback.md"); block=p.read_text(encoding="utf-8").split("```bash\n",1)[1].split("\n```",1)[0]; subprocess.run(["/bin/bash","-euo","pipefail","-c",block],check=True)'
verify: /bin/bash -euo pipefail -c 'test "$(git symbolic-ref --quiet --short HEAD)" = main; test -z "$(git status --porcelain=v1 --untracked-files=all)"; test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse 9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0^{tree})"; test ! -e specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json; test ! -e specs/subject-distillation/.task-authorization.pending; git diff --check'

Run the following from the canonical repository. It fails closed unless the
operator has an external atomic exclusive lease and an explicit owner-channel
confirmation that no Mission proposal has been issued. The lease is held from
the first preflight through revert and postproof. The command also requires
symbolic `main`, canonical `origin`, a fully clean tracked/untracked tree, exact
delivery refs/parents/tree, and absent proof/pending authority. It freshly
fetches and repeats every mutable check immediately before `git revert`.
HUP, INT, and TERM exit with conventional nonzero statuses; only the EXIT trap
performs cleanup, so a signal cannot release the lease and then continue into
the revert.

```bash
set -euo pipefail
canonical_repo="zycaskevin/Vault-Agent-Memory"
canonical_origin="https://github.com/zycaskevin/Vault-Agent-Memory.git"
delivery_branch="agent/sdg012-identity-junit-dispatcher-only-v4"
protocol_base="9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0"
mission_fixture_pr="487"
mission_fixture_branch="agent/mission-v5-activation-post-sdg011"
mission_fixture_topic="6e596574f48354cdf6ccdc72bce35d3b6df1c184"
mission_fixture_ref="refs/pull/487/head"
node_authority="tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_accepts_exact_current_mission_phase"
node_cli="tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_cli_is_exact_and_no_abbreviation"
mission_proof_path="specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json"
rollback_lease="${SDG012_ROLLBACK_LEASE:-}"
rollback_tmp=""
rollback_lease_acquired=0

cleanup() {
  if test -n "$rollback_tmp" && test -d "$rollback_tmp"; then
    rm -rf -- "$rollback_tmp"
  fi
  if test "$rollback_lease_acquired" = 1; then
    rmdir -- "$rollback_lease"
    rollback_lease_acquired=0
  fi
}

on_signal() {
  signal_status="$1"
  trap - HUP INT TERM
  exit "$signal_status"
}

trap cleanup EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

acquire_rollback_lease() {
  test -n "$rollback_lease"
  test "${rollback_lease#/}" != "$rollback_lease"
  test ! -e "$rollback_lease"
  test ! -L "$rollback_lease"
  lease_parent="$(dirname -- "$rollback_lease")"
  test -d "$lease_parent"
  lease_parent_physical="$(cd "$lease_parent" && pwd -P)"
  repo_physical="$(pwd -P)"
  temp_physical="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
  case "$lease_parent_physical/" in
    "$repo_physical/"*|"$temp_physical/"*) return 1 ;;
  esac
  mkdir -m 700 -- "$rollback_lease"
  rollback_lease_acquired=1
}

assert_canonical_delivery() {
  test "$rollback_lease_acquired" = 1
  test -d "$rollback_lease"
  test ! -L "$rollback_lease"
  test "${SDG012_ROLLBACK_NO_PROPOSAL:-}" = "confirmed-no-issued-proposal"
  test "$(git remote get-url origin)" = "$canonical_origin"
  test "$(git remote get-url --push origin)" = "$canonical_origin"
  test "$(git symbolic-ref --quiet --short HEAD)" = "main"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  git fetch --no-tags origin main
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  test "$(git rev-parse HEAD)" = "$delivery_merge_commit"
  test "$(git rev-parse refs/remotes/origin/main)" = "$delivery_merge_commit"
  test "$(git rev-list --parents -n 1 "$delivery_merge_commit")" = "$delivery_merge_commit $protocol_base $delivery_topic_commit"
  test "$(git rev-parse "$delivery_merge_commit^{tree}")" = "$(git rev-parse "$delivery_topic_commit^{tree}")"
  test ! -e specs/subject-distillation/task-authorizations/MISSION-V5-T004-T033.json
  test ! -e specs/subject-distillation/.task-authorization.pending
}

acquire_rollback_lease

test "$(gh repo view --json nameWithOwner --jq .nameWithOwner)" = "$canonical_repo"
test "$(git remote get-url origin)" = "$canonical_origin"
test "$(git remote get-url --push origin)" = "$canonical_origin"
test "$(git symbolic-ref --quiet --short HEAD)" = "main"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch --no-tags origin main
test -z "$(git status --porcelain=v1 --untracked-files=all)"

delivery_pr_number="$(gh pr list --repo "$canonical_repo" --head "$delivery_branch" --state merged --limit 100 --json number | python -c 'import json,sys; rows=json.load(sys.stdin); assert len(rows)==1, "expected one exact merged delivery PR"; number=rows[0].get("number"); assert isinstance(number,int) and number > 0; print(number)')"
delivery_pr_json="$(gh pr view "$delivery_pr_number" --repo "$canonical_repo" --json number,state,baseRefName,baseRefOid,headRefName,headRefOid,mergeCommit)"
read -r delivery_merge_commit delivery_topic_commit <<EOF
$(printf '%s' "$delivery_pr_json" | python -c 'import json,sys; row=json.load(sys.stdin); assert row.get("number")==int(sys.argv[1]); assert row.get("state")=="MERGED"; assert row.get("baseRefName")=="main"; assert row.get("baseRefOid")=="9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0"; assert row.get("headRefName")=="agent/sdg012-identity-junit-dispatcher-only-v4"; merge=(row.get("mergeCommit") or {}).get("oid"); topic=row.get("headRefOid"); assert isinstance(merge,str) and len(merge)==40; assert isinstance(topic,str) and len(topic)==40; print(merge, topic)' "$delivery_pr_number")
EOF
mission_fixture_json="$(gh pr view "$mission_fixture_pr" --repo "$canonical_repo" --json number,state,baseRefName,baseRefOid,headRefName,headRefOid,mergeCommit)"
printf '%s' "$mission_fixture_json" | python -c 'import json,sys; row=json.load(sys.stdin); assert row.get("number")==int(sys.argv[1]); assert row.get("state")=="CLOSED"; assert row.get("baseRefName")=="main"; assert row.get("baseRefOid")==sys.argv[2]; assert row.get("headRefName")==sys.argv[3]; assert row.get("headRefOid")==sys.argv[4]; assert row.get("mergeCommit") is None' "$mission_fixture_pr" "$protocol_base" "$mission_fixture_branch" "$mission_fixture_topic"
assert_canonical_delivery

rollback_tmp="$(mktemp -d "${TMPDIR:-/tmp}/sdg012-rollback.XXXXXX")"
chmod 700 "$rollback_tmp"
git clone --quiet --no-hardlinks --no-checkout . "$rollback_tmp/retained"
git -C "$rollback_tmp/retained" checkout --quiet --detach "$delivery_merge_commit"
git -C "$rollback_tmp/retained" remote set-url origin "$canonical_origin"

reviewed_source="$(git -C "$rollback_tmp/retained" show "$delivery_merge_commit:.sddgov/merge-gate.json" | python -c 'import json,sys; gate=json.load(sys.stdin); head=gate.get("head_sha"); assert isinstance(head,str) and len(head)==40; print(head)')"
git -C "$rollback_tmp/retained" merge-base --is-ancestor "$reviewed_source" "$delivery_topic_commit"
mkdir -p "$rollback_tmp/bytes/scripts" "$rollback_tmp/bytes/tests"
for path in scripts/run_subject_development_mission_v5.py scripts/run_subject_identity_test_isolation.py tests/test_subject_task_authorization_dispatch_v5.py; do
  git -C "$rollback_tmp/retained" show "$reviewed_source:$path" > "$rollback_tmp/bytes/$path"
  test "$(git -C "$rollback_tmp/retained" show "$reviewed_source:$path" | shasum -a 256 | cut -d ' ' -f 1)" = "$(git -C "$rollback_tmp/retained" show "$delivery_merge_commit:$path" | shasum -a 256 | cut -d ' ' -f 1)"
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

assert_malformed_dispatcher_api_denied() {
  NODE_AUTHORITY="$node_authority" NODE_CLI="$node_cli" python - <<'PY'
import os
from pathlib import Path
from scripts import validate_subject_task_authorization_dispatch_v5 as dispatch

assert os.environ["NODE_AUTHORITY"] == "tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_accepts_exact_current_mission_phase"
assert os.environ["NODE_CLI"] == "tests/test_subject_task_authorization_dispatch_v5.py::test_dispatch_cli_is_exact_and_no_abbreviation"
try:
    dispatch.validate(Path.cwd())
except dispatch.Denied:
    pass
else:
    raise AssertionError("malformed dispatcher authority node was not denied")
PY
}

assert_malformed_dispatcher_cli_denied() {
  CLI_PATH="scripts/validate_subject_task_authorization_dispatch_v5.py" python - <<'PY'
import os
import stat
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
cli = root / os.environ["CLI_PATH"]
info = cli.stat(follow_symlinks=False)
assert stat.S_ISREG(info.st_mode)
assert stat.S_IMODE(info.st_mode) == 0o755
assert info.st_nlink == 1
environment = dict(os.environ)
environment.pop("SUBJECT_MISSION_V5_PHASE", None)
environment["PYTHONDONTWRITEBYTECODE"] = "1"
completed = subprocess.run(
    [sys.executable, os.fspath(cli), "--ledger", "--json"],
    cwd=root,
    env=environment,
    capture_output=True,
    check=False,
    timeout=30,
)
assert completed.returncode == 2
assert completed.stdout == b""
assert completed.stderr == b"SUBJECT_TASK_AUTHORIZATION_DISPATCH_V5_DENY\n"
assert b"Traceback" not in completed.stderr
assert b"SUBJECT_TASK_AUTHORIZATION_DISPATCH_V5_ERROR" not in completed.stderr
PY
}

assert_no_proof_dispatcher_inactive() {
  python - <<'PY'
import subprocess
import sys
from pathlib import Path
from scripts import validate_subject_task_authorization_dispatch_v5 as dispatch

root = Path.cwd()
validator_result = dispatch.validator.validate(root)
assert validator_result == {
    "active": False,
    "authorized_tasks": 0,
    "mission_id": None,
    "mission_state": "INACTIVE",
    "sequence": 6,
    "status": "PASS",
}
expected = {
    "active": False,
    "mission_id": None,
    "mission_state": "INACTIVE",
    "protocol_version": 5,
    "sequence": 6,
    "status": "PASS",
}
assert dispatch.validate(root) == expected
completed = subprocess.run(
    [
        sys.executable,
        "scripts/validate_subject_task_authorization_dispatch_v5.py",
        "--ledger",
        "--json",
    ],
    cwd=root,
    capture_output=True,
    check=False,
    timeout=30,
)
assert completed.returncode == 0
assert completed.stdout == dispatch.mission.canonical(expected)
assert completed.stderr == b""
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
git -C "$rollback_tmp/retained" fetch --no-tags origin "$mission_fixture_ref"
test "$(git -C "$rollback_tmp/retained" rev-parse FETCH_HEAD)" = "$mission_fixture_topic"
cd "$rollback_tmp/retained"
git checkout --quiet --detach "$mission_fixture_topic"
# The Mission proof binds this topic's runner bytes. Retain and hash the reviewed
# SDG-012 runner above, but do not overlay it into proof-bearing topologies.
install_reviewed_proof_fixture_bytes
assert_node_pass candidate candidate-authority "$node_authority"
assert_node_pass candidate candidate-cli "$node_cli"
restore_fixture_tree

active_commit="$(printf '%s\n' 'SDG-012 rollback exact active fixture' | GIT_AUTHOR_NAME=sdg012-rollback GIT_AUTHOR_EMAIL=sdg012-rollback@example.invalid GIT_COMMITTER_NAME=sdg012-rollback GIT_COMMITTER_EMAIL=sdg012-rollback@example.invalid git commit-tree "$mission_fixture_topic^{tree}" -p "$protocol_base" -p "$mission_fixture_topic")"
git checkout --quiet --detach "$active_commit"
install_reviewed_proof_fixture_bytes
assert_node_pass active active-authority "$node_authority"
assert_node_pass active active-cli "$node_cli"
restore_fixture_tree

git show "$mission_fixture_topic:$mission_proof_path" > "$rollback_tmp/mission-proof.json"

# A delivery-shaped commit whose tree contains no proof is not authority.  The
# direct validator rejects the externally claimed proof while dispatcher API
# and CLI remain exact canonical INACTIVE with zero authorized tasks.
no_proof_commit="$(printf '%s\n' 'SDG-012 rollback no-proof delivery-shaped fixture' | GIT_AUTHOR_NAME=sdg012-rollback GIT_AUTHOR_EMAIL=sdg012-rollback@example.invalid GIT_COMMITTER_NAME=sdg012-rollback GIT_COMMITTER_EMAIL=sdg012-rollback@example.invalid git commit-tree "$protocol_base^{tree}" -p "$protocol_base" -p "$mission_fixture_topic")"
git checkout --quiet --detach "$no_proof_commit"
test "$(git rev-list --parents -n 1 "$no_proof_commit")" = "$no_proof_commit $protocol_base $mission_fixture_topic"
test "$(git rev-parse "$no_proof_commit^{tree}")" = "$(git rev-parse "$protocol_base^{tree}")"
if git cat-file -e "$no_proof_commit:$mission_proof_path" >/dev/null 2>&1; then
  exit 1
fi
install_reviewed_proof_fixture_bytes
PROTOCOL_BASE="$protocol_base" MISSION_RAW="$rollback_tmp/mission-proof.json" python - <<'PY'
import os
from pathlib import Path
from scripts import run_subject_development_mission_v5 as mission
try:
    mission.validate_mission_activation_delivery(Path.cwd(), protocol_base=os.environ["PROTOCOL_BASE"], mission_raw=Path(os.environ["MISSION_RAW"]).read_bytes())
except mission.Denied:
    pass
else:
    raise AssertionError("no-proof delivery-shaped fixture accepted external proof")
PY
assert_no_proof_dispatcher_inactive
restore_fixture_tree

# The proof-bearing malformed fixture reverses the required parent order.  Its
# tree, proof mode, and proof bytes are exact, so every DENY below is topology
# enforcement rather than fallback to the no-proof INACTIVE state.
malformed_commit="$(printf '%s\n' 'SDG-012 rollback proof-bearing reversed-parent fixture' | GIT_AUTHOR_NAME=sdg012-rollback GIT_AUTHOR_EMAIL=sdg012-rollback@example.invalid GIT_COMMITTER_NAME=sdg012-rollback GIT_COMMITTER_EMAIL=sdg012-rollback@example.invalid git commit-tree "$mission_fixture_topic^{tree}" -p "$mission_fixture_topic" -p "$protocol_base")"
git checkout --quiet --detach "$malformed_commit"
test "$(git rev-list --parents -n 1 "$malformed_commit")" = "$malformed_commit $mission_fixture_topic $protocol_base"
test "$(git rev-parse "$malformed_commit^{tree}")" = "$(git rev-parse "$mission_fixture_topic^{tree}")"
test "$(git ls-tree "$malformed_commit" -- "$mission_proof_path" | cut -d ' ' -f 1)" = 100644
test "$(git cat-file -t "$malformed_commit:$mission_proof_path")" = blob
git show "$malformed_commit:$mission_proof_path" | cmp - "$rollback_tmp/mission-proof.json"
dispatcher_cli_path="scripts/validate_subject_task_authorization_dispatch_v5.py"
test "$(git ls-tree "$malformed_commit" -- "$dispatcher_cli_path" | cut -d ' ' -f 1)" = 100755
test "$(git cat-file -t "$malformed_commit:$dispatcher_cli_path")" = blob
test "$(git hash-object "$dispatcher_cli_path")" = "$(git rev-parse "$malformed_commit:$dispatcher_cli_path")"
install_reviewed_proof_fixture_bytes
PROTOCOL_BASE="$protocol_base" MISSION_RAW="$rollback_tmp/mission-proof.json" python - <<'PY'
import os
from pathlib import Path
from scripts import run_subject_development_mission_v5 as mission
try:
    mission.validate_mission_activation_delivery(Path.cwd(), protocol_base=os.environ["PROTOCOL_BASE"], mission_raw=Path(os.environ["MISSION_RAW"]).read_bytes())
except mission.Denied:
    pass
else:
    raise AssertionError("proof-bearing reversed-parent fixture was not denied")
PY
assert_malformed_dispatcher_api_denied
assert_malformed_dispatcher_cli_denied

# Only now mutate canonical main. The post-revert proof is explicitly limited
# to base-compatible INACTIVE behavior with the retained reviewed test bytes.
cd - >/dev/null
assert_canonical_delivery
git revert --no-edit -m 1 "$delivery_merge_commit"
test "$(git rev-parse HEAD^{tree})" = "$(git rev-parse "$delivery_merge_commit^1^{tree}")"
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
on the no-proof baseline. A delivery-shaped base tree is explicitly proven to
remain canonical `INACTIVE` with zero authorized tasks; a separate exact
proof-bearing reversed-parent topology retains direct Mission denial and
requires exact dispatcher API and CLI denial mapping. The new
tree must equal the delivery merge's first-parent tree; retained reviewed bytes
then establish exact `INACTIVE`, sequence 6, T-004 `PENDING`, and absent
pending/proof files. Every positive dispatcher node invocation writes a unique
JUnit file and requires exactly one real pass with zero skips, xfails, failures,
or errors.

Never rewrite history. Use only before any proposal/proof is bound to the
SDG-012 release. Set `SDG012_ROLLBACK_LEASE` to a new absolute path whose
existing parent is outside both the repository and the system temp tree; a
collision denies execution. Set `SDG012_ROLLBACK_NO_PROPOSAL` to
`confirmed-no-issued-proposal` only after recording the required owner-channel
confirmation. After proposal/proof binding, regenerate authority through the
governed protocol instead of blind revert.
