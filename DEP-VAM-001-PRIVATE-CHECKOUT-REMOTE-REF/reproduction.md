# Reproduction

## Expected

A fresh private Builder or Reviewer checkout that is bound to the formal GitHub
repository must expose the exact PR base as `refs/remotes/origin/main` before
Local Green starts, so Mission V5 can validate current-main transitions.

## Actual

The Builder's one authorized exact Local Green reached the SDG-012 identity
node and exited 2 because `git rev-parse origin/main` returned 128. The checkout
had the correct origin URL but was cloned from a local source, so no
`refs/remotes/origin/main` ref existed. The worktree stayed clean.

## Deterministic steps

1. Create a clean local-source clone and replace its origin URL with the formal
   GitHub URL without fetching remote refs.
2. Confirm `git rev-parse origin/main` fails.
3. Run the named SDG-012 node and observe the missing-ref failure.
4. Fetch `main` into the explicit `refs/remotes/origin/main` selector and assert
   it equals PR base `291d5595c9cb2208a6b74206acbba35a883eb918`.
5. Rerun only the named node and observe `1 passed`.

## Environment and preconditions

- PR #498 audit head: `c52aee2e5dec50406209c1f4d3be69add5eb3c86`
- Private checkout mode: `0700`
- Origin URL: `https://github.com/zycaskevin/Vault-Agent-Memory.git`
- Runtime: pinned Local Green Python and `sddgov 0.2.0-experimental.6`
