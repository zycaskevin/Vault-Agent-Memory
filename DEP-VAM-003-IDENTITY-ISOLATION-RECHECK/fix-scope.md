# Fix Scope

## Smallest sufficient change

No product-code change. Move the existing candidate worktree to a stable,
dedicated filesystem root outside `/tmp`, then complete Local Green there.

## Files or components in scope

- Stable-root candidate Subject identity isolation verification
- This DEP

## Explicit non-scope

No changes to frozen Subject files, security auditing, fixed-deny behavior,
test expectations, CI acceptance criteria, or timeout values.

## Blast radius

Verification only. No runtime or public behavior changes.
