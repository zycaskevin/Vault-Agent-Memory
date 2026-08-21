# Regression Evidence

## Regression test added or strengthened

No product test changed. The original failing SDG-012 node is the executable
regression check, and checkout preparation now includes an exact
`refs/remotes/origin/main == PR base` assertion.

## Related tests executed

- Consumed Builder Local Green: FAIL at the missing-ref node; no retry.
- Targeted sandbox Green after exact fetch/assertion: `1 passed in 4.57s`.
- Previous private-lifecycle targeted Green remains PASS.

## Unaffected paths sampled

The tracked worktree remained clean before and after the remote-ref fix. No
frozen Subject/runtime path changed.
