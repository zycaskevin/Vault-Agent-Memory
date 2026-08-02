# Subject Distillation B-000 — Codex Development Handoff

> Execute B-000 only after the repository owner names `lane=B-000` and the
> exact clean implementation base commit. This document, a hash, review result,
> issue or PR is not implementation authority.

**Repository:** `zycaskevin/Vault-Agent-Memory`
**Parent epic:** #410
**B-000 issue:** #422
**Blocked successor:** #421 / T-001
**Goal:** Create the smallest fail-closed authorization bootstrap needed to
verify future T-task receipts, without implementing T-001 or product runtime.

Authoritative contract order:

1. `specs/subject-distillation/requirements.md`
2. `specs/subject-distillation/design.md`
3. `specs/subject-distillation/tasks.md`
4. Issue #422
5. This handoff

## 1. Owner instruction

The complete B-000 instruction is:

```text
lane=B-000
implementation_base_commit=<exact lowercase 40-or-64-hex commit>
```

The selected commit must contain the mechanically validated canonical baseline.
Preflight derives the baseline ID, full digest and exact three-path allowlist;
the owner does not repeat those derived values. An agent must not create, rewrite
or infer this instruction.

If the commit is missing, dirty, unresolved, does not contain the validated
canonical bytes or differs from `git rev-parse HEAD`, stop without editing.

## 2. Environment and base preflight

Use a clean worktree based on the exact selected commit. Record the branch,
HEAD and complete status path set before the first repository write. Do not
reset, clean, stash or overwrite unrelated user work.

From repository root, create or reuse the project-local environment:

```bash
test -x .venv/bin/python || python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
command -v python
python --version
```

Normal package-index/network dependency installation is allowed. Do not use an
unauthorized private index, credential or private source. Do not change package
metadata or dependencies in B-000. `.venv/` must remain ignored/untracked.

Then validate the manifest:

```bash
python scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json \
  --repo-root . \
  --json
```

The command must return PASS. Record its derived baseline ID/full digest in the
return packet. A mismatch blocks B-000; do not rewrite the manifest inside the
implementation lane.

## 3. Exact write allowlist

B-000 may create or modify exactly:

1. `tests/test_subject_authorization_bootstrap.py`
2. `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`
3. `scripts/verify_subject_implementation_authorization.py`

Read-only repository inspection and local ignored test/environment files are
allowed. No other repository path may change.

## 4. Safety boundary

B-000 must not:

- implement T-001/T-002+, Subject runtime, DDL, migration, CLI/MCP/Gateway,
  evidence/progress ledgers or product behavior;
- create/rewrite an owner instruction, T-task receipt or operator-private scope;
- read, copy, log or commit private/live/GB10 data, credentials, private receipt
  or scope contents/paths;
- perform production migration, deploy, release, merge or destructive action;
- change canonical specs, package metadata, dependencies or lock files.

Commit/push/PR delivery is not automatically forbidden by the implementation
lane, but it requires separate explicit owner authorization. Without that
authority, stop after the reviewed local return packet.

## 5. Atomic execution plan

### B-001 — Preflight

**Owner:** parent verifier
**Input:** two-value owner instruction + clean selected commit
**Output:** derived baseline/full digest, environment identity and exact status
**Success:** manifest PASS, HEAD match, three owned paths absent or unmodified,
supported Python active and no unexpected dirty/untracked path.

### B-002 — Genuine RED

**Owner:** implementer
**Input:** authoritative B-000 contract
**Output:** `tests/test_subject_authorization_bootstrap.py`
**Success:** focused pytest fails because the required schema/verifier behavior
is absent, not because of syntax, import, install or broken fixture setup.

### B-003 — Schema, verifier and adversarial matrix

**Owner:** implementer
**Inputs:** genuine RED + design §21 + tasks §1 scanner contract
**Outputs:** all three allowlisted files
**Success:** implement the fixed JSON Schema subset and standard-library verifier;
the focused tests cover canonical receipt/scope binding, duplicate keys/types,
timestamps, exact hashes, path normalization, descriptor no-follow/race handling,
resource caps, scanner boundaries and no-echo behavior.

The CLI and output contract remain exactly as specified in design §21:

- PASS: exit `0`, empty stderr, one compact LF-terminated JSON object;
- DENY: exit `2`, empty stdout, exact
  `SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n`;
- ERROR: exit `3`, empty stdout, exact
  `SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n`.

Caller/input failures are DENY. ERROR is only for safely classified unexpected
internal/programmer/harness faults. Never echo path, hostile key/value, token-
shaped input, receipt/scope content or raw exception.

### B-004 — Verify, review and stop

**Owner:** parent verifier + one independent security reviewer
**Inputs:** exact three-path candidate
**Output:** local return packet
**Success:** parent reads all files, confirms exact diff, reruns commands, checks
RED/GREEN evidence and receives an independent security verdict P0=0/P1=0.

Any source-byte fix after review requires rerunning the affected focused tests
and review. B-004 does not authorize T-001.

## 6. Required verification

Run after GREEN:

```bash
python scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json \
  --repo-root . \
  --json
python -m pytest -q tests/test_subject_authorization_bootstrap.py
python -m ruff check \
  scripts/verify_subject_implementation_authorization.py \
  tests/test_subject_authorization_bootstrap.py
git diff --check -- \
  scripts/verify_subject_implementation_authorization.py \
  specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json \
  tests/test_subject_authorization_bootstrap.py
git status --short --untracked-files=all
```

All must exit `0`, except the earlier genuine RED run which must be recorded as
expected nonzero. The final repository change set must be exactly the three paths.

Local development and task verification may run on any supported OS. The focused
descriptor/no-follow/race suite must also pass on supported Python 3.10+ Linux CI
before merge or release. Record OS/Python for every run and do not describe a
macOS pass as Linux evidence.

## 7. Review rule

One independent security reviewer examines the unchanged exact B-000 tree for:

- scope compliance and no T-001/product expansion;
- fixed schema/verifier parity and fail-closed classification;
- duplicate-key/type/time/canonicalization correctness;
- descriptor/no-follow/race and resource-limit behavior;
- public-safety scanner legal/DENY boundaries;
- no-echo, cleanup and adversarial-test quality.

Required verdict: PASS, P0=`0`, P1=`0`. Two ordered reviewers and a separate
repo-external review-evidence JSON body are not required.

## 8. Failure and rollback

Capture each owned path before its atom. On failure, restore only that owned
path; never use broad destructive cleanup on a mixed/unknown worktree. Report
the exact public-safe failed command/class. Do not reinterpret a failure as a
waiver or edit the canonical contract inside B-000.

Stop for owner direction if implementation requires a fourth repository path,
dependency/metadata change, product/security decision not present in the SDD,
private/live access, production/destructive action or broader Git authority.

## 9. Return packet

```text
STATUS: PASS | BLOCKED
IMPLEMENTATION_BASE_COMMIT: <sha>
BASELINE_ID: <derived value>
BASELINE_FULL_DIGEST: <derived value>
CHANGED_PATHS:
- <exact paths>
RED_COMMAND: <command>
RED_EXIT: <exit>
RED_REASON: <public-safe reason>
GREEN_COMMANDS:
- <command>: <exit/result>
RUFF: <result>
BASELINE_VALIDATOR: <result>
DIFF_CHECK: <result>
REVIEW: PASS|FAIL; P0=<n>; P1=<n>; P2=<n>
OS_PYTHON: <each run>
UNRESOLVED:
- <none or exact blockers>
GIT_SIDE_EFFECTS: none | <separately authorized exact effects>
```

Do not include tokens, private paths, receipt/scope contents or fabricated output.

## 10. Stop boundary

After B-000 tests, parent readback and independent security review pass, stop.
Do not begin T-001, create a T-001 receipt/scope, or claim product runtime. Git
delivery is a separate owner decision. After an accepted B-000 delivery, T-001
still needs an actual verified receipt and independent authorization.
