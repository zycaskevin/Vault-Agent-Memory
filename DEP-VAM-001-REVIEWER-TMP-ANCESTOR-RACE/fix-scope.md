# Fix Scope

## Smallest sufficient change

Relocate the fresh independent-review checkout from shared `/tmp` to a unique,
owner-private stable directory below `~/.codex/sddgov-review-checkouts/`, bind
`origin` to the exact ASCII GitHub repository URL, then run the same exact
pinned Local Green once. Keep the checkout clean, detached at the exact GitHub
head, and verify ancestor identity stability before and after.

## Files or components in scope

- Reviewer execution location and pre/post checkout evidence
- Exact repository identity (`https://github.com/zycaskevin/Vault-Agent-Memory.git`)
- This DEP and the PR #498 merge-gate evidence binding
- The exact existing Local Green command; no command-content change

## Explicit non-scope

- No change to the pinned Subject verifier, baseline, contracts, mission code,
  frozen SDD, production Vault runtime, API, privacy boundary, or acceptance
  criteria
- No retry in shared `/tmp`
- No receipt or signature unless the relocated exact run and all review gates
  pass

## Blast radius

Local independent-review infrastructure only. The remedy changes where a fresh
checkout lives; it does not change repository behavior or shipped artifacts.
