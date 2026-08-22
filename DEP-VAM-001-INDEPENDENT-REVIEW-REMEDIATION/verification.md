# Verification

## Green proof

The strengthened section-level boundary tests, exact Subject baseline node,
and Subject contract tests passed: 56 tests. The production progress validator
returned `baseline_id=0dc10cfc4a429662`, `sequence=8`, and `status=PASS`.
Ruff and `git diff --check` also passed. Full Local Green passed after the
remediation: all 446 identity-isolated Subject nodes passed, followed by
2,926 passed and 10 skipped in the repository suite. Hosted CI remains required
after the remediation and exact gate metadata are committed.

## Independent review

The previous Reviewer verdict remains FAIL and no receipt exists. A fresh
independent review is required against the remediated exact head.

## Limitations

The rollback command is a guarded candidate-producing operation; it must not be
executed without its future exact L3 approval and strict rollback DEP.

## Green command and result

The repository-defined `sddgov ci local-gate .` ran with the pinned governance
CLI and isolated PATH. It returned success after governance doctor, CI contract,
README command smoke, release parity, all 446 identity-isolated Subject nodes,
and the 2,926-pass repository suite completed.

## Before/after evidence

Before: the independent review found cross-section assertions and contradictory
rollback instructions, so the verdict was FAIL and no receipt was issued.

After: issue assertions are scoped to their own sections, the ADR boundary is
checked by section, and the rollback procedure has one compatibility-only target
with exact preconditions and verification. Focused and full Local Green both
pass; a new independent review of the exact remediated head is still required.

The Full Green summary was collected twice because the first collector label
omitted `.txt`. Both immutable raw entries retain the same SHA-256; the first
was renamed with a text extension and both were processed by the redaction gate.

## Remaining limitations

This DEP does not authorize rollback or merge. Rollback still requires a fresh
strict DEP and consumed L3 approval. Merge still requires the exact gate digest,
a fresh independent Reviewer receipt, and hosted CI success.
