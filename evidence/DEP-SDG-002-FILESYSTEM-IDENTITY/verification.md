# Verification

## Completed

- Deterministic full-directory-metadata RED: PASS as a reproduction (legacy
  audit denied the unchanged target after unrelated sibling churn).
- Fresh stable-root SDG Local Green Gate: PASS.
- Public artifact redaction: PASS, with no blocked artifact.

## Required before merge

1. Add this strict DEP to the exact SDG-001 Merge Gate.
2. Recompute the reviewed source and gate metadata digests.
3. Use a new distinct independent reviewer in a fresh stable-root checkout.
4. Before any gate, require `git remote get-url origin` to equal the canonical
   GitHub HTTPS URL; a bundle pathname is not accepted as repository identity.
5. Require pre-sign Local Green and post-sign `sddgov merge verify` on the same
   exact source; either red result rejects the receipt.
6. Run hosted CI once on the final revision and merge only when required checks
   are green.

## Limitations

This mitigation removes a local review-environment false-deny source. It does
not change the frozen runtime audit or claim that unrelated directory metadata
can never cause a fail-closed denial in every possible operator environment.
Any future need to change that runtime behavior requires a separately versioned
Subject authority protocol; it is not hidden inside this SDG integration.
