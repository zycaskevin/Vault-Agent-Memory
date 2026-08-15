# Reproduction

## Expected

On the exact clean post-SDG main commit, the inactive Mission V5 runner emits a
fresh canonical proposal. It must continue to reject arbitrary intervening
history and must not publish a proof or start T-004.

## Actual

The runner exits 2 with the fixed public-safe
`SUBJECT_DEVELOPMENT_MISSION_V5_DENY` marker. Its release check requires the
cumulative V4-activation-to-base diff to equal only the V5 bridge paths, so the
reviewed policy-bootstrap and SDG merges are rejected together with genuinely
unauthorized history.

## Deterministic steps

1. Start from clean `origin/main` at
   `4c4c29a16decfeedda59b685886801f65b9fd878`.
2. Confirm `MISSION-V5-T004-T033.json` is absent.
3. Run:

   ```text
   PYTHONDONTWRITEBYTECODE=1 python3 scripts/run_subject_development_mission_v5.py propose-mission --implementation-base-commit 4c4c29a16decfeedda59b685886801f65b9fd878 --json
   ```

4. Observe exit 2 and the fixed DENY marker. The public-safe captured result is
   `shareable/artifacts/terminal--post-sdg-proposal-red.txt`.

## Environment and preconditions

- Repository: `zycaskevin/Vault-Agent-Memory`.
- Branch: `agent/mission-v5-activation-post-sdg`.
- Runtime: CPython 3.14.3 on macOS arm64.
- The exact main tree is clean, `HEAD == origin/main`, and the V5 proof is
  absent before reproduction.
