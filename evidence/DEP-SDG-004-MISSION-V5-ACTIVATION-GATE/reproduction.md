# Reproduction

## Expected

An exact owner-confirmed Mission V5 proof can be delivered without weakening
either the Mission replay or the mandatory SDG signed exact-head merge gate.

## Actual

The proof-only activation commit passes Mission V5, while `sddgov merge verify`
rejects the stale SDG-003 gate. Adding refreshed gate/receipt paths would make
the old Mission V5 proof-only delivery check reject the same Pull Request.

## Deterministic steps

1. Start from clean merged main `3374ac372930ee6200d38c1f02289a0c8fa1eb84`.
2. Generate and verify the exact owner-confirmed Mission V5 proof.
3. Commit only `MISSION-V5-T004-T033.json`.
4. Run `python3 scripts/validate_subject_development_mission_v5.py --json`.
5. Run `sddgov merge verify . --base-ref 3374ac372930ee6200d38c1f02289a0c8fa1eb84`.
6. Observe Mission V5 PASS and deterministic SDG base/head mismatch DENY.

## Environment and preconditions

macOS; Python 3; SDG `0.2.0-experimental.6`; branch
`agent/mission-v5-activation-after-sdg003`; proof commit `0a865b2b...`.
