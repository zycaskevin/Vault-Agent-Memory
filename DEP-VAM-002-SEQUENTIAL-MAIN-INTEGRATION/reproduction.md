# Reproduction

## Expected

PR #500 must contain the already merged #498 and #499 history, while its
current merge gate and protected review refer only to the VAM-002 candidate
being proposed on top of that exact main commit.

## Actual

The remote PR head `68ddbe6c8300f7538774eb40cbf19c5f3e028016`
still had merge base `291d5595c9cb2208a6b74206acbba35a883eb918`.
After a conflict-free merge of current main, the resulting integration commit
`8358bb95e6f26f3ec2f7ff36009d67570092c6b4` correctly contains main
`c284e1c7bedf288a10009b98e5f2da525c3ee4bc`, but `.sddgov/merge-gate.json`
still binds VAM-003 reviewed head `fcac3c1f82d2b58a61fb55488175a32e599d5f5b`,
receipt `REV-VAM-003.json`, and the VAM-003 rollback.

## Deterministic steps

1. Checkout PR #500 exact remote head `68ddbe6c8300f7538774eb40cbf19c5f3e028016`.
2. Verify its merge base with current `origin/main` is the old
   `291d5595c9cb2208a6b74206acbba35a883eb918`.
3. Merge exact current main `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`.
4. Verify current main is now an ancestor of the integration commit.
5. Compare `.sddgov/merge-gate.json` `head_sha`, review receipt, and rollback
   to the integration head and VAM-002 work package. The gate does not bind the
   current head or VAM-002.

## Environment and preconditions

Fresh `/tmp` Builder clone, formal GitHub origin, `umask 022`, branch
`codex/vam-002-memory-change-envelope`. The current main and PR head were
fetched before the merge. The worktree contained no pre-existing local edits.
