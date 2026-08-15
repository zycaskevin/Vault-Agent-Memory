# Root Cause Hypothesis

## Hypothesis

Mission V5 calls the frozen v1 `_audit_lifecycle` after a comparatively long
Git release replay. That audit delegates the external ancestor chain to the
verifier's full identity tuple, which includes directory size and modification
time. Those fields describe directory membership, not directory-object
identity, so unrelated sibling churn creates a false DENY.

## Supporting evidence

- The shared private verifier returned PASS on the exact mechanically derived
  receipt and scope.
- The post-verifier lifecycle audit alone returned DENY.
- Cleanup returned PASS and left no pending or mission proof artifact.
- The existing directory-identity helper already binds device, inode, type,
  and mode while intentionally ignoring owned-member metadata churn.

## Contradicting evidence

The fail-closed denial is safe: no hostile replacement was accepted. A real
receipt or directory replacement must therefore remain a required negative
control after the availability fix.

## Falsification test

Use a Mission V5-only wrapper that applies stable directory-object identity to
the ancestor chain but preserves full identity and exact bytes for the owned
private directory, receipt, and scope. It must pass unrelated sibling churn and
deny private-file and external-directory replacement.

## Conclusion

Confirmed. The failure occurs after the verifier PASS and before proof
publication, exactly at the legacy post-verifier lifecycle audit. The bounded
compatibility wrapper is sufficient and does not require frozen v1 edits.
