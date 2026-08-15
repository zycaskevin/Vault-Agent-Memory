# Regression Evidence

## Regression test added or strengthened

`test_protocol_release_accepts_only_exact_post_sdg_compatibility_merge` is a
genuine RED/GREEN control for the exact two-parent delivery. The RED failed
because no post-SDG compatibility boundary existed. The repaired test passes
and then proves a later single-parent unauthorized descendant is denied.

`test_protocol_release_denies_hidden_topic_scope_and_mode_drift` proves that an
unauthorized intermediate path remains denied even when a later commit removes
it from the net diff, and that mode-0644 drift on the required executable is
denied. `test_reviewed_post_sdg_anchor_binds_signed_gate_and_receipt` replays
the exact frozen historical anchor.

## Related tests executed

- Mission V5 focused suite plus dispatcher: 67 passed.
- Ruff on the changed script/test: PASS.
- Python compile and `git diff --check`: PASS.
- First full Local Green in the active Codex runtime tree: fail-closed with two
  known frozen filesystem-identity cases; no retry was performed. This is not
  accepted as Green and is preserved in
  `terminal--unstable-root-local-gate-deny.txt`.

## Unaffected paths sampled

- Canonical five: unchanged.
- v1-v4 and T-001 through T-003 authority/progress bytes: unchanged.
- Mission proof: absent; T-004 remains PENDING at sequence 6.
- Repository/product/runtime modules outside the closed hotfix paths: unchanged.
