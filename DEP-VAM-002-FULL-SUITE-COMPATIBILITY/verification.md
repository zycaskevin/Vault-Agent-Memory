# Verification

## Green command and result

Targeted Green passed after the minimal fix:

- real HTTP loopback node: 1 passed;
- governance/provider adjacent selection: 30 passed;
- Ruff for the two changed Python files: PASS;
- `git diff --check`: PASS.

The single authorized complete Local Green then passed at exact committed head
`1a346913563f5437b7815f655393f0eee5a0da52`: 446 identity nodes passed and
repository pytest returned 2967 passed, 10 skipped, and one existing warning.
Post-run HEAD, clean worktree, 1429 physical modes, and frozen Subject diff all
matched the declared candidate.

## Before/after evidence

Before: 446 identity nodes passed, then repository pytest returned 2 failed,
2965 passed, 10 skipped, and 1 warning. The attached RED artifact identifies
both nodes and exact candidate head.

## Remaining limitations

The HTTP node and complete gate used separately approved non-sandbox loopback
execution after the sandbox denied socket creation. No production or Hermes
data was accessed. Any later candidate mutation requires new proof.
