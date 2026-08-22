# Reproduction

## Expected

Tests and rollback records must reject heading decoys, masked approval failures,
out-of-scope revert paths, omitted integration boundaries, and unbounded
remediation rollback.

## Actual

At exact remote head `b2c8378db44079080d1d9bbd418febf93e527ec9`, those conditions were not
all mechanically bound even though current happy-path content passed.

## Deterministic steps

Read CodeRabbit review `4994599002`; compare each finding with the exact test
helper and both rollback records. Inspect the delivery command around autonomy
evaluation, revert/restore, and its missing staged-path assertion.

## Environment and preconditions

PR #498 base `291d5595c9cb2208a6b74206acbba35a883eb918`, exact reviewed head
`b2c8378db44079080d1d9bbd418febf93e527ec9`, no Reviewer receipt.
