# Reproduction

## Expected

PR candidate CI must test dispatcher behavior at the inactive authority anchor;
active main must retain exact active dispatcher assertions. Both nodes execute
once inside the explicit phase-isolated identity harness and never again in the
remainder.

## Actual

PR #487 hosted run `31943149157`, governance job `95155106192`, checked out the
exact PR head and passed the candidate Mission V5 identity controls. Its Local
Green remainder then collected `tests/test_subject_task_authorization_dispatch_v5.py`
outside that harness and ran its two active-only assertions against a
preliminary candidate. Exact results were one `Denied` from delivery lookup and
one CLI return-code mismatch (`2` versus expected `0`): 2 failed, 2870 passed,
10 skipped, one pre-existing warning.

## Deterministic steps

1. Check out a proof-present exact activation topic before its merge.
2. Run candidate identity controls; observe the Mission V5 phase-aware suite
   passes.
3. Run the configured disjoint remainder; observe both dispatcher nodes execute
   without the phase-neutral snapshot and fail at the active-only assumption.
4. Confirm the identity harness omits the dispatcher file and each remainder
   also omits an ignore for it.
5. After the fix, require exact count 2, total 446, candidate/active focused
   passes, and one exact ignore in each remainder.

## Environment and preconditions

Issue #488; base `9ddc50883957875aeb29a1a2ac6501bfe5c7b8a0`; branch
`agent/sdg012-mission-v5-dispatch-phase-isolation-v2`; GitHub Actions Python 3.12;
Agentic SDD Governance 0.2.0-experimental.6. No private/live data is involved.
