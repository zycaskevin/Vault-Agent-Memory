# Root Cause Hypothesis

## Hypothesis

The replacement-review remediation adopted the review comment's exact-parent
wording without reconciling it with the governance verifier's intentional
audit-only descendant model.

## Supporting evidence

`only_audit_changes_after_review` in the merged governance runtime first
requires ancestry, then restricts changed paths to the merge gate or review
receipts. The governance hard-gate contract also states that gate and receipt
commits remain audit-only descendants.

## Contradicting evidence

An unconstrained ancestor check is insufficient because it could accept
arbitrary code after review. The repair therefore cannot merely restore the
old ancestor command; it must pair ancestry with an exact path allowlist.

## Falsification test

The hypothesis is false if a guard using ancestry plus the exact gate/receipt
exclusions still accepts a non-audit descendant or if it rejects a legitimate
gate-only and receipt-only descendant.

## Conclusion

Confirmed. Exact equality is too strict, ancestor-only is too weak, and the
smallest correct guard is ancestry plus a mechanically empty non-audit diff.
