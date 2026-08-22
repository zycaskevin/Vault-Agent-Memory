# Verification

## Green command and result

Targeted merged-tree proof passed at integration commit
`8358bb95e6f26f3ec2f7ff36009d67570092c6b4`: 10 provider/change-envelope
tests, 4 direct Gateway/OpenAPI contract tests, and 73 boundary/setup tests.
Changed-module Ruff, module size, `git diff --check`, Frozen Subject diff, both
historical VAM-002 strict DEPs, and CI contract verification also passed.

The owner-authorized repository-controlled Local Green passed once in a fresh
0700 private checkout pinned to committed integration-evidence head
`bee2543d02e3ad2c3436e6246703f31c743bdf72`. Governance doctor, CI contract,
README smoke, and release parity passed; 446 identity-isolated Subject nodes
passed; and the repository suite completed with 2958 passed, 10 skipped, and
one existing invalid-escape warning. Post-run HEAD, clean status, physical
tracked modes, Frozen Subject diff, and index integrity remained exact. The
redacted proof is `shareable/artifacts/terminal--builder-local-green.txt`.

## Before/after evidence

Before integration, current main was not an ancestor of PR #500 and the branch
could not produce a sequential VAM-002 delivery. After integration, exact main
is the merge commit's second parent and merge base. The product regression
oracle passes without source conflict, while the stale inherited VAM-003 gate
remains visibly invalid and will be replaced only after exact-head proof.

## Remaining limitations

- Independent focused architecture review and `REV-VAM-002` remain required
  before merge.
- VAM-002 continues to expose current snapshots only, not historical content
  reconstruction.
