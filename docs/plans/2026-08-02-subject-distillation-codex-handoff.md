# Subject Distillation B-000 — Codex Development Handoff

> **For Codex:** Execute this handoff only after the trusted owner prompt explicitly contains all four B-000 binding values below. This document, its PR, Issue #422, hashes, and review PASS are not authorization by themselves.

**Repository:** `zycaskevin/Vault-Agent-Memory`

**Parent epic:** #410

**Implementation issue:** #422

**Blocked successor:** #421 / T-001

**Goal:** Implement the smallest fail-closed authorization bootstrap needed to verify future T-task receipts without implementing T-001 or product runtime behavior.

**Requirements:** `specs/subject-distillation/requirements.md`, especially R-SD-015 and §13

**Design:** `specs/subject-distillation/design.md`, especially §21

**Tasks:** `specs/subject-distillation/tasks.md`, especially §1 and B-000

**Approval/examples:** The canonical package preserves all 43 approved SBE IDs. B-000 is governance-only and adds no product SBE.

**Tech stack:** Python 3.10+, JSON Schema 2020-12, pytest, Ruff, Linux/POSIX descriptor APIs

---

## 1. Exact reviewed binding

| Field | Required value |
|---|---|
| Lane | `B-000` |
| Baseline ID | `0f688cf2e2472beb` |
| Baseline full digest | `0f688cf2e2472beb22082fb16c9c344de921e06e71a5efc939c8a4c70f5ed773` |
| B-000 scope SHA-256 | `1cb9eaf4e13a4049d93cabd82edb3707c6251f8bf0f7c4d4dceb931a115d9739` |
| Canonical manifest SHA-256 | `ca55599acc49f3c0f7d263f081b3b884c202e2093ebfdec94925465b6e7a1483` |
| Fresh review | `PASS`, P0=`0`, P1=`0`, P2=`0` |

A valid owner prompt must explicitly contain this exact public tuple:

```text
lane=B-000
baseline_id=0f688cf2e2472beb
baseline_full_digest=0f688cf2e2472beb22082fb16c9c344de921e06e71a5efc939c8a4c70f5ed773
scope_sha256=1cb9eaf4e13a4049d93cabd82edb3707c6251f8bf0f7c4d4dceb931a115d9739
```

If any value is absent, different, inherited from chat summary, or bound to changed canonical bytes: **stop without editing**.

## 2. Base and branch policy

Preferred start:

1. Wait until the baseline/handoff PR containing this document is accepted into `main`.
2. Fetch `origin/main`.
3. Create a fresh branch such as `feat/subject-distillation-b000-bootstrap`.
4. Use a fresh worktree.
5. Verify the worktree is clean before the first B-000 write.

A stacked branch from the baseline/handoff PR head is allowed only when the owner explicitly chooses that reviewed base. Do not silently retarget or mix unrelated work.

Record before editing:

```bash
git status --short --branch --untracked-files=all
git rev-parse HEAD
git branch --show-current
git remote -v
```

Preflight must show no modified, staged, or untracked path. If it does, stop and report the exact path set; do not reset, stash, clean, or overwrite unrelated state.

## 3. Environment setup

Run from repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
command -v python
python --version
```

Any nonzero exit blocks B-000. Do not substitute another environment silently.

Then validate the exact baseline:

```bash
python scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json \
  --repo-root . \
  --json
```

Expected exact semantic result:

```json
{"baseline_id":"0f688cf2e2472beb","full_digest":"0f688cf2e2472beb22082fb16c9c344de921e06e71a5efc939c8a4c70f5ed773","status":"PASS"}
```

A mismatch means the handoff is stale. Stop; do not rewrite the manifest under the old owner instruction.

## 4. Exact write allowlist

B-000 may create or modify exactly:

1. `tests/test_subject_authorization_bootstrap.py`
2. `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`
3. `scripts/verify_subject_implementation_authorization.py`

Read-only inspection of repository files is allowed. No other repository write is allowed—not README, changelog, roadmap, progress ledger, evidence, fixture, helper, config, lock file, package metadata, snapshot, transcript, or generated report.

Local `.venv` and ephemeral test directories are not repository artifacts and must remain untracked.

## 5. Explicit non-goals

Do not:

- implement T-001 or any T-002+ task;
- create `read_subject_baseline_id.py`, evidence schemas beyond the one authorization schema, progress schema/ledger, environment evidence, Subject runtime, DDL, migration, CLI/MCP/Gateway behavior;
- create or rewrite an owner instruction, T-task receipt, or operator-private scope artifact;
- use private/live/GB10 data or credentials;
- persist operator-private receipt/scope paths or contents;
- stage, commit, push, open/update a PR, merge, release, deploy, migrate, or write to GitHub from the B-000 implementation lane;
- weaken canonical requirements to make tests pass;
- infer policy from old issues, old baselines, or summaries when canonical docs differ.

## 6. Contract hierarchy

If sources conflict, use this order:

1. Current validated canonical `requirements.md`
2. Current validated canonical `design.md`
3. Current validated canonical `tasks.md`
4. Issue #422
5. This handoff
6. Chat summaries or old issues

Do not modify the canonical files during B-000. A real contradiction is a blocker, not permission to choose a convenient interpretation.

## 7. Atomic execution plan

### B-001 — Create genuine RED bootstrap tests

**Objective:** Prove the absent schema/verifier fail for the intended reason before implementation.

**File:** Create `tests/test_subject_authorization_bootstrap.py`

**Required first test slices:**

- expected schema path does not exist;
- expected verifier path does not exist;
- focused CLI invocation cannot succeed because the verifier is absent;
- test imports and fixture construction themselves are valid.

Run:

```bash
python -m pytest -q tests/test_subject_authorization_bootstrap.py
```

Expected RED: nonzero because the canonical schema/verifier are missing. It must not fail because of syntax, import, package-install, fixture-path, or unrelated repository errors.

Capture the RED command, exit code, and concise failure class outside the repo for parent review.

Stop if the expected files already exist or another test owns conflicting behavior.

### B-002 — Implement the strict receipt schema

**Objective:** Encode the exact JSON Schema 2020-12 receipt shape without adding policy.

**File:** Create `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`

Implement exactly the required fields and closed shape from design §21:

- `schema_version`
- `artifact_kind`
- `baseline_id`
- `baseline_full_digest`
- `authorizing_principal`
- `authorized_task`
- `scope_sha256`
- `authorization_verifier_sha256`
- `authorization_schema_sha256`
- `issued_at_utc`
- `expires_at_utc`
- `authorization_id`

Use `additionalProperties: false`. Preserve exact regex/const/type restrictions. JSON Schema alone does not replace semantic duplicate-key, canonical-byte, timestamp, path, self-hash, or public-safety checks; those belong in the verifier.

Add schema positive and negative tests before relying on the verifier.

### B-003 — Implement the fail-closed verifier CLI

**Objective:** Verify exact trusted receipt bytes and all transitive bindings without echoing hostile/private input.

**File:** Create `scripts/verify_subject_implementation_authorization.py`

Required CLI:

```text
--receipt <absolute operator-private path>
--expected-receipt-sha256 <64 lowercase hex from trusted parent>
--scope <absolute operator-private path>
--manifest specs/subject-distillation/baseline-manifest.json
--schema specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json
--expected-authority github:zycaskevin
--expected-task T-001
--json
```

Required implementation boundaries:

1. Reject missing, unknown, or duplicate flags and absent `--json` as DENY.
2. Use duplicate-key-rejecting JSON parsing and exact builtin type checks.
3. Hash exact receipt bytes and compare to trusted `--expected-receipt-sha256`.
4. Validate receipt schema and canonical `authorization_id`.
5. Parse and canonicalize the T-task scope contract from design §21; cross-bind baseline, task, scope digest, receipt, authority, verifier self hash, and schema hash.
6. Validate OS UTC wall-clock timestamps; issue < expiry and `now >= expiry` is DENY. Production CLI has no caller clock override.
7. Implement the sole key-aware public-safety scanner from tasks §1. Do not copy an older scanner or invent extra token classes.
8. Open operator-private absolute paths from `/` dirfd and fixed repo-relative inputs from repo-root dirfd, component by component with no-follow semantics.
9. Require regular files, enforce 1,048,576-byte caps, retain descriptors, read from the same descriptor, and compare exact pre/post `fstat` tuple `(st_dev, st_ino, st_mode, st_size, st_mtime_ns)`.
10. Do not use `Path.resolve`, `realpath`, pathname reopen, mount rejection, or physical/lexical alias heuristics as authorization decisions.
11. Centralize descriptor cleanup in reverse acquisition order.
12. Never echo path, key, value, receipt/scope content, token-shaped input, or raw exception.

Exact output contract:

| Result | Exit | stdout | stderr |
|---|---:|---|---|
| PASS | `0` | one LF-terminated compact sorted JSON object with only `authorization_id`, `authorized_task`, `baseline_id`, `status` | empty |
| DENY | `2` | empty | exact `SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n` |
| ERROR | `3` | empty | exact `SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n` |

Caller/input faults are DENY. ERROR is reserved for safely classified unexpected internal/programmer/harness failure.

### B-004 — Complete the adversarial matrix

The single bootstrap test file must cover at least these named classes.

#### Legal ALLOW

- exact valid receipt, canonical scope, current baseline, correct authority/task;
- every required lowercase 64-hex digest-bearing authorization field;
- manifest file `sha256` and closure `full_digest` legal neighbors;
- exact `private-shadow-pass:<64 lowercase hex>` namespace;
- ordinary public-safe strings;
- normalized absolute operator-private regular receipt/scope files;
- fixed repo-relative regular manifest/schema/verifier files;
- issue time before expiry and current time before expiry;
- exact success serialization and empty stderr.

#### Required DENY

- missing/unknown/duplicate CLI flag; missing `--json`;
- receipt exact-byte digest mismatch;
- duplicate JSON keys at every parsed artifact class;
- Boolean where integer is required, wrong builtin types, unknown/missing fields;
- malformed/uppercase/wrong-length digest fields;
- bare 32/64/128 hex under non-digest keys;
- each exact token-prefix, Bearer, JWT, assignment, PEM/private-key, forbidden normalized-key, and private-shadow namespace mutation from tasks §1;
- authority/task/baseline/full-digest/scope/self-hash/schema-hash mismatch;
- invalid `authorization_id` or noncanonical receipt/scope bytes;
- invalid calendar, non-UTC/noncanonical timestamp, issue >= expiry, expiry equality, expired receipt;
- relative private input path, NUL/backslash, empty/`.`/`..` component;
- symlink ancestor, symlink final, missing/non-regular file;
- file over byte cap, short/extra read, descriptor identity or metadata mutation race;
- hostile path/content/exception no-echo assertions;
- exact fixed DENY serialization.

#### Required ERROR

Use a non-CLI test seam to inject an unexpected internal fault after safe classification and assert exact exit `3`/fixed stderr/no echo. Do not add a production CLI fault or clock override.

### B-005 — Run deterministic gates

After GREEN, run in this order:

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

All commands must exit `0`. The final status path set must be exactly the three B-000 files. If `.venv` appears, fix local ignore/exclude state without editing tracked repository files.

## 8. Parent readback gate

Codex must return control before any Git side effect. Parent must independently:

- read all three files in full;
- compare the exact diff against the three-path allowlist;
- verify canonical five-file baseline remains unchanged and still validates;
- rerun focused tests and Ruff;
- inspect hostile/no-echo/race tests, not only pass counts;
- compute candidate diff and artifact hashes;
- confirm no owner instruction, receipt, scope, private path, token, transcript, or generated evidence entered the repo.

Codex self-report is not acceptance evidence.

## 9. Ordered fresh reviews

Run only after parent deterministic gates pass, on the same exact tree.

### Review 1 — Fresh spec compliance

Require a fresh read-only reviewer to verify:

- exact canonical receipt/schema/verifier contract;
- all B-000 acceptance criteria in #422;
- only three allowed paths changed;
- genuine RED evidence exists;
- no T-001/product behavior or guessed policy;
- exact baseline/scope binding preserved.

Required verdict: `PASS`, P0=`0`, P1=`0`.

### Review 2 — Fresh quality/security

Only after Review 1 PASS. Require a different fresh read-only review of:

- fail-closed classification;
- descriptor/no-follow/race handling;
- duplicate-key/type/time/canonicalization correctness;
- scanner false-positive and false-negative boundaries;
- no-echo behavior;
- resource cleanup;
- maintainability and test adversarial quality.

Required verdict: `PASS`, P0=`0`, P1=`0`.

Any byte change after either review invalidates that review and requires rerunning the affected ordered gates.

## 10. Rollback and failure policy

For each atom, capture pre-atom state of its owned path. On failure:

- restore only the captured owned-path state;
- do not use `git reset --hard`, `git clean`, broad checkout, or stash on a mixed/unknown worktree;
- do not delete a pre-existing file;
- retain failure evidence outside repo without private/raw content;
- report `BLOCKED` with the exact failed command/class;
- do not reinterpret a failure as a waiver.

Default waiver policy is zero. Changing the canonical contract requires a separate docs-only amendment, new baseline manifest, new fresh review, and new owner instruction.

## 11. Required Codex return packet

Return a concise machine-checkable handoff to the parent containing:

```text
STATUS: PASS | BLOCKED
BASE_COMMIT: <sha>
BASELINE_ID: 0f688cf2e2472beb
BASELINE_FULL_DIGEST: 0f688cf2e2472beb22082fb16c9c344de921e06e71a5efc939c8a4c70f5ed773
SCOPE_SHA256: 1cb9eaf4e13a4049d93cabd82edb3707c6251f8bf0f7c4d4dceb931a115d9739
CHANGED_PATHS:
- <exact paths>
RED_COMMAND: <command>
RED_EXIT: <exit>
RED_REASON: <public-safe class>
GREEN_COMMANDS:
- <command>: <exit/result>
RUFF: <result>
BASELINE_VALIDATOR: <result>
DIFF_CHECK: <result>
UNRESOLVED:
- <none or exact blockers>
GIT_SIDE_EFFECTS: none
```

Do not include tokens, private paths, raw receipt/scope content, hidden chain-of-thought, or fabricated outputs.

## 12. Stop boundary after B-000

Even after B-000 tests and both reviews pass:

- do not mark #422 complete until parent verifies the exact tree;
- do not commit/push/open a B-000 PR without separate Git-side-effect authorization;
- do not begin T-001;
- do not create a T-001 receipt or scope;
- do not reuse the old #421 baseline/authorization.

The next valid transition is parent verification, then separately authorized B-000 Git delivery, then actual T-001 receipt verification and a new T-001 owner decision.
