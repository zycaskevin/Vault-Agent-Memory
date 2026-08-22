# Regression Evidence

## Regression test added or strengthened

The HTTP facade test now compares the final active-row count with the count
captured after fixture setup instead of a stale literal. The existing strict
read-guard test remains the exact reason-code regression.

## Related tests executed

RED is captured for the strict read-guard node and both failures are bound to
the exact-head full Local Green artifact. Targeted Green passed: the real HTTP
loopback node passed 1/1, and the governance/provider selection passed 30/30.
A complete exact-head Local Green remains pending after this fix is committed.

## Unaffected paths sampled

Adjacent tests for private rows, restricted sensitivity, invalid caller caps,
supersession, provider reads, and agent-policy filtering passed in the 30-test
selection. Ruff and `git diff --check` also passed.
