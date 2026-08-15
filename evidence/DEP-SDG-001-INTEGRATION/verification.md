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

## Green command and result

`.venv-sddgov/bin/sddgov ci local-gate .` returned `ok: true`. Its final pytest
command reported `3283 passed, 12 skipped, 1 warning` in 162.80 seconds after
the consumer policy bootstrap and executable hosted merge-gate job were added.

## Before/after evidence

Before: `ci verify` exited 2 because the contract did not exist. After: static
verification returns `ok: true`, lists both governed automatic workflows and
all 15 hosted jobs, and reports no errors. The first Local Green run saw one
fail-closed macOS temporary-directory identity flake in unchanged T-002 code;
the isolated case passed, and the single policy-permitted full rerun passed.

## Remaining limitations

Repository-wide Ruff remains pre-existing lint debt (1,557 findings) and was
not promoted into a new acceptance criterion by this scoped integration.
Hosted CI and independent review remain separate gates until the final revision
is committed and reviewed.
