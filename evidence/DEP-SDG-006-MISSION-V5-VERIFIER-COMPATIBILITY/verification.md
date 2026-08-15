# Verification

## Green command and result

- Mission V5 plus v1 authorization lifecycle focused suite: 244 passed.
- Mission compatibility controls: unrelated sibling PASS; private file
  replacement DENY; external directory replacement DENY; hidden release
  history DENY.
- Ruff, Python 3.10 grammar, `git diff --check`, doctor, and CI Cost Guard: PASS.
- Local Green in the required unsandboxed identity-root environment: 301
  isolated identity nodes PASS; disjoint remainder 2,994 passed, 12 skipped,
  one pre-existing warning; overall PASS.

## Before/after evidence

RED is recorded in
`shareable/artifacts/terminal--mission-v5-private-lifecycle-red.txt`; GREEN is
recorded in
`shareable/artifacts/terminal--mission-v5-private-lifecycle-green.txt`.

Two sandboxed Local Green invocations were rejected before executing identity
nodes because the configured harness root under `.codex/sddgov-test-temp` is
outside the workspace-write sandbox. A diagnostic reproduced the exact
`PermissionError`. The governed unsandboxed run then completed all 301 identity
nodes and the full disjoint remainder without retry.

## Remaining limitations

The compatibility wrapper is intentionally Mission V5-only. It does not make
the expired proposal valid and does not activate the mission. A fresh proposal
and owner confirmation are required after the hotfix merge readback.

Independent protected review, hosted CI, and exact two-parent merge readback
remain required before a new Mission proposal may be generated.
