# Reproduction

## Expected

Local Green executes every collected test exactly once in a process boundary
that prevents authorization-module state from leaking across unrelated test
files.

## Actual

The existing 301 identity nodes passed, but the shared remainder process failed
one Mission V5 test after earlier files mutated the pinned sibling validator's
module-global state. Result: 2993 passed, 12 skipped, 1 failed; no receipt was
issued.

## Deterministic steps

1. Build the exact SDG-005 activation synthetic two-parent merge.
2. Run the configured `sddgov ci local-gate .`.
3. Observe the identity harness report 301 PASS.
4. In the disjoint remainder, observe
   `test_task_derivation_loads_the_pinned_sibling_validator` fail closed in
   `_repo_inputs`.
5. Run that exact node in a clean process and observe PASS.
6. Add the entire 75-node Mission V5 file to the closed isolation set, exclude
   only that already-executed file from the remainder, and rerun.

## Environment and preconditions

macOS; CPython 3; SDG `0.2.0-experimental.6`; base
`b1b0be02087f42b222d1de1731ff9dffa4676bf3`; branch
`agent/sdg007-mission-v5-local-green-isolation`. No authorization runner,
private packet, live data, or production operation.
