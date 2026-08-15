# Fix Scope

## Smallest sufficient change

Add one exact SDG-004 compatibility release layer and replace proof-only
activation acceptance with validation of the closed future SDG-005 record set
whose actions, modes, ancestry, and merge topology are mechanically replayed.
The SDG-005 records exercised here are non-authorizing test fixtures; a fresh
proposal and owner confirmation remain required after this hotfix is merged.

## Files or components in scope

- `scripts/run_subject_development_mission_v5.py`
- `tests/test_subject_development_mission_v5.py`
- the current V5 SHA pin in `.github/workflows/ci.yml`
- `.sddgov/ci-cost-guard.json` and the closed
  `scripts/run_subject_identity_test_isolation.py` harness for per-node process
  isolation without collection reduction
- SDG-004 Work Package, decision record, strict DEP, gate, and review receipt

## Explicit non-scope

Mission activation itself; any T-task implementation; canonical five; v1-v4;
T-001 through T-003 artifacts; ledger; task descriptors; private/live data;
production, deployment, release, Billing, credentials, provider consoles; L2/L3.

## Blast radius

The change affects only the pre-activation Git delivery/replay boundary. It adds
no runtime product code, persistence schema, or task output.
