# Regression Evidence

## Regression test added or strengthened

The HTTP facade test now compares the final active-row count with the count
captured after fixture setup instead of a stale literal. The existing strict
read-guard test remains the exact reason-code regression.

## Related tests executed

RED is captured for the strict read-guard node and both failures are bound to
the compatibility implementation. Targeted Green passed: the real HTTP
loopback node passed 1/1, and the governance/provider selection passed 30/30.
The subsequently authorized Builder Local Green at exact implementation head
`1a346913563f5437b7815f655393f0eee5a0da52` completed with 446 isolated
Subject nodes passing and repository pytest reporting 2967 passed, 10 skipped,
and one previously dispositioned warning.

## Unaffected paths sampled

Adjacent tests for private rows, restricted sensitivity, invalid caller caps,
supersession, provider reads, and agent-policy filtering passed in the 30-test
selection. Ruff and `git diff --check` also passed.
