# Fix Scope

## Smallest sufficient fix

Run independent protected review and its mandatory post-sign Merge Gate from a
fresh clean checkout under a stable, dedicated filesystem root that is outside
the active Codex runtime tree and outside shared OS temporary roots. Keep the
reviewer's private key and trust store outside the Repo as already required.

The same stable checkout must perform both the pre-sign Local Green Gate and
the post-sign `sddgov merge verify`; changing checkout or source bytes between
them invalidates the review.

## In scope

- Issue #474 and this public-safe L1 DEP.
- A fresh exact-source independent review checkout under a stable root.
- Recomputed SDG Merge Gate metadata and a new independent receipt.
- Full Local Green before signing and the mandatory Local Green embedded in
  post-sign Merge Gate verification.

## Explicit non-scope

- No edits to frozen T-001 through T-003 runner, verifier, tests, contracts,
  proofs, reviews, ledger events, or canonical Subject documents.
- No relaxation, skip, xfail, retry loop, or acceptance of a red Merge Gate.
- No product behavior, authorization scope, privacy, deployment, release,
  Billing, production data, or credentials.

## Blast radius

Only the local independent-review execution location and SDG evidence/gate
metadata change. Hosted CI already uses an isolated hosted workspace. Runtime
authorization behavior and its fail-closed security boundary remain unchanged.
