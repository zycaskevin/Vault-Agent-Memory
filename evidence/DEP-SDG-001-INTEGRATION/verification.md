# Verification

## Hosted revision-1 result

- Ordinary project checks: passed or continued normally.
- Agentic SDD Governance merge gate: failed closed before review verification because the job-created repository-local virtual environment made the checkout dirty.
- Classification: reproducible CI configuration defect, not a transient provider failure.
- Action: create a new reviewed revision with the governance virtual environment outside the repository; do not rerun the failed revision.

## Revision-2 Local Green attempt 1

- Result: 3,282 passed, 12 skipped, 1 failed, 1 warning.
- Failure: the existing T-003 real-Git pending-written recovery case denied on retained repository-input identity.
- Isolated rerun: PASS, 1 passed.
- Classification: transient fail-closed filesystem identity race; this satisfies the Cost Guard evidence prerequisite for one full rerun of the same revision.

## Independent clean-checkout portability finding

- RED: an external-venv invocation of `sddgov ci local-gate` failed before commands ran because `.sddgov/ci-cost-guard.json` referenced missing repository-local executables.
- Root cause: the workflow runtime location and the executable names embedded in the project contract were inconsistent.
- FIX: use PATH-resolved `sddgov`/`python` contract commands and publish only `$RUNNER_TEMP/sddgov-venv/bin` to subsequent workflow steps.
- Required GREEN: external-venv clean-checkout Local Green must execute successfully while `git status --porcelain` remains empty.
- GREEN: the independent reviewer ran `PATH=<external-sddgov-venv>/bin:$PATH sddgov ci local-gate <clean-detached-checkout>`; `git status --porcelain` was empty before installation, after installation, and after two complete Local Green executions. Both runs reported `3283 passed, 12 skipped, 1 warning`. See `shareable/artifacts/terminal--external-clean-checkout-green.txt`.

## Green command and result

`.venv-sddgov/bin/sddgov ci local-gate .` returned `ok: true`. Its final pytest
command reported `3283 passed, 12 skipped, 1 warning` in 162.80 seconds after
the consumer policy bootstrap and executable hosted merge-gate job were added.

## Before/after evidence

Before: `ci verify` exited 2 because the contract did not exist. After: static
verification returns `ok: true`, lists both governed automatic workflows and
all 15 hosted jobs, and reports no errors. The original integration revision's
artifact records a T-002 filesystem-identity flake; its isolated case and
permitted rerun passed (`shareable/artifacts/terminal--local-green.txt`). A
later revision separately saw the named T-003 pending-written real-Git case
deny on the same fail-closed identity class; that exact case passed in isolation
and the revision's permitted full rerun passed. These are two distinct events,
not conflicting identifiers for one failure.

## Remaining limitations

Repository-wide Ruff remains pre-existing lint debt (1,557 findings) and was
not promoted into a new acceptance criterion by this scoped integration.
Hosted CI and independent review remain separate gates until the final revision
is committed and reviewed.
