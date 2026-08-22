# Verification

## Green command and result

Targeted merged-tree proof passed at integration commit
`8358bb95e6f26f3ec2f7ff36009d67570092c6b4`: 10 provider/change-envelope
tests, 4 direct Gateway/OpenAPI contract tests, and 73 boundary/setup tests.
Changed-module Ruff, module size, `git diff --check`, Frozen Subject diff, both
historical VAM-002 strict DEPs, and CI contract verification also passed.

The complete repository-controlled Local Green has not yet been executed at a
committed integration-evidence head. This DEP intentionally remains in Green
until one exact private-checkout Builder run passes and its result is bound to
the committed head.

## Before/after evidence

Before integration, current main was not an ancestor of PR #500 and the branch
could not produce a sequential VAM-002 delivery. After integration, exact main
is the merge commit's second parent and merge base. The product regression
oracle passes without source conflict, while the stale inherited VAM-003 gate
remains visibly invalid and will be replaced only after exact-head proof.

## Remaining limitations

- The HTTP loopback Gateway smoke and the repository-wide suite are deferred to
  the authorized private-checkout Local Green because sandbox loopback is
  intentionally unavailable.
- Independent focused architecture review and `REV-VAM-002` remain required.
- VAM-002 continues to expose current snapshots only, not historical content
  reconstruction.
