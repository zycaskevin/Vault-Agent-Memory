# Reproduction

## Expected

The rollback target must originate exclusively from PR #498's head parent, and
the proof/rollback records must identify exact checkout and commit order.

## Actual

At `b2c8378`, ancestry was checked only against the merge as a whole; evidence
and historical rollback selectors lacked the reviewed exact facts.

## Deterministic steps

Inspect CodeRabbit review `4994753914` and compare the delivery command,
local-target rollback, Green artifact, warning summary, and red risk wording.

## Environment and preconditions

Exact base `291d5595c9cb2208a6b74206acbba35a883eb918`, head
`b2c8378db44079080d1d9bbd418febf93e527ec9`, no Reviewer receipt.
