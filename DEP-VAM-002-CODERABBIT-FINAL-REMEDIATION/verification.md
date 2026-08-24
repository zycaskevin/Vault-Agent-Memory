# Verification

## Green command and result

The bounded static contract probe returned four PASS results and exit `0`.
The repo-relative VAM-002 focused selection returned `24 passed`; Ruff over
`tests/test_memory_change_envelope.py` and
`tests/test_vault_boundary_freeze.py`, `git diff --check`, governance Doctor,
and CI contract verification all returned zero. Exact commands and bounded
results are in `shareable/artifacts/terminal--final-review-green.txt`.

## Before/after evidence

RED at `36ff168a8c8ffffcc93d12107add2d5ecac0fbd1`: four independent
semantic checks failed. Green in the bounded remediation worktree: rollback
RED/Green expectations are distinct, evidence matches implementation, defect
categories are truthful, and normalized Markdown assertions are line-reflow
safe.

## Exact committed-head Local Green attempt

The one authorized non-sandbox gate at exact implementation commit
`c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a` passed private-boundary,
tracked-mode, Doctor, CI-contract, README-smoke, and release-parity checks. It
then failed in the identity-isolated phase at
`test_contract_is_closed_and_current_mission_phase_is_exact`: the Builder clone
had a local filesystem `origin`, while the Mission V5 repository-identity guard
accepts only the formal GitHub SSH or HTTPS remote. Repository-wide pytest did
not start. The checkout remained exact and clean; no retry was made.

## Additional authorized Local Green attempt

The owner explicitly authorized correcting that same private clone's `origin`
to the formal GitHub HTTPS URL and running one additional non-sandbox gate at
the same exact implementation commit. The origin correction, private boundary,
tracked physical mode, Doctor, CI-contract, README-smoke, and release-parity
checks all passed. Identity-isolated nodes then stopped at
`test_sdg012_current_main_transition_accepts_only_exact_delivery`: the existing
clone did not contain `refs/remotes/origin/main`, so `git rev-parse origin/main`
exited `128`. Repository-wide pytest again did not start. Post-run HEAD, clean
status, origin, and diff checks passed. Per authorization, no retry was made.

## Checkout preparation after the failed run

Without running another test gate, Builder fetched only the formal GitHub
`main` branch into `refs/remotes/origin/main`. It resolves to exact PR base
`c284e1c7bedf288a10009b98e5f2da525c3ee4bc`, and the merge-base with exact
candidate `c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a` is the same commit. All three
private boundaries remain `0700`; the worktree is detached and clean; all 1,455
tracked physical modes match the Git index. This preparation resolves the known
checkout precondition but is not Local Green proof.

## Final exact-head Local Green proof

With all checkout preconditions fixed and independently rechecked before
process start, the owner-authorized non-sandbox Local Green ran once at exact
implementation commit `c004c04cd1c1ed471ba39d6d4ad0f5e565dfea5a` and exited
`0`. Doctor, CI contract, README smoke, and release parity passed; all 446
identity-isolated Subject nodes passed; repository-wide pytest reported `2970
passed, 10 skipped, 1 warning`. The warning is the existing invalid-escape
deprecation at `tests/test_semantic_chunk_coverage.py:101`. Post-run exact HEAD,
formal origin, exact `origin/main`, clean status, diff checks, Frozen Subject
diff, and all 1,455 tracked physical modes remained Green.

## Remaining limitations

Valid identity-bearing runtime behavior and stored data did not change in this
final documentation/test remediation. The earlier intentional contract fix for
malformed requests remains: missing or empty `agent_id` returns
`agent_id_required` with HTTP 400 rather than HTTP 200. Exact committed-head
Builder Local Green is complete. Merge-gate rebind, public push, CodeRabbit
re-review, independent Reviewer receipt, merge, and deployment remain separate
gates; this proof authorizes none of them.
