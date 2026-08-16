# Reproduction

## Expected

The immutable T-001 baseline-control suite completes inside Local Green while
retaining all file-identity and 16 MiB resource-boundary assertions.

## Actual

The SDG-005 v2 protected-review Local Green passed 376 identity-isolated nodes,
then the shared remainder failed
`test_stage_header_and_file_resource_boundaries`. The exact 16,777,216-byte
stage read failed closed in `_read_large_file`; result: 2919 passed, 12 skipped,
1 failed. No review receipt was issued.

## Deterministic steps

1. Run phase-correct SDG-005 Local Green on the reviewed synthetic merge.
2. Observe the 376-node identity harness PASS.
3. Observe the shared remainder fail the baseline-control 16 MiB boundary.
4. Confirm both affected T-001 files still match their terminal ledger hashes.
5. Execute the complete 53-node baseline-control file in a clean process.
6. Add that immutable file to the closed isolation set, exclude only the
   already-executed file from the remainder, and rerun.

## Environment and preconditions

macOS; CPython 3; SDG `0.2.0-experimental.6`; base
`6d499e41ac41b8cd0f560146b0f18939b55a5f3f`; branch
`agent/sdg008-large-file-identity-isolation`. No authorization runner, private
packet, live data, or production operation.
