# Reproduction

## Expected

All 446 frozen Subject identity nodes pass in isolated homes and temporary
directories during the candidate-phase Local Green gate.

## Actual

One node failed before its intended assertion because the helper proposal was
denied with exit 2. The same node and complete isolation suite had passed on
the previous VAM-003 exact head.

## Deterministic steps

1. Use the VAM-003 worktree after the one-line module-size correction.
2. Run `sddgov ci local-gate .` with the repository Python wrapper.
3. Observe the candidate isolation runner stop at the recorded node.
4. Re-run only the exact node under a fresh isolated home/temp root to test
   whether the failure is deterministic before changing frozen Subject code.

## Environment and preconditions

Local Linux worktree `/tmp/Vault-VAM-003`; candidate phase; the isolation
runner creates a fresh `HOME`, `TMPDIR`, and pytest base temp for every node.
