# Root Cause Hypothesis

## Hypothesis

PRs #498, #499, #500, and #501 were opened from the same original main
revision so that their product work could proceed independently. Sequential
delivery changes the effective base after each merge. Git can integrate the
new base without source conflicts, but the protected merge gate and review
receipt are intentionally Work-Package-specific and cannot be inherited from
the newly merged main branch.

## Supporting evidence

- PR #500 remote head had the original pre-#498 merge base.
- Merging current main was conflict-free and made current main an exact
  ancestor of the integration commit.
- The inherited merge gate still names VAM-003's reviewed head, receipt, and
  rollback rather than the current VAM-002 integration.
- Existing VAM-002 product commits and their two historical DEPs remain
  present and unchanged.

## Contradicting evidence

- No application source conflict occurred during the merge.
- The previously hosted VAM-002 functional matrix passed on the old base.
- Those facts reduce product-conflict risk but do not make an old-base gate or
  a different Work Package's signature reusable.

## Falsification test

On the merged candidate, run the focused Memory Change Envelope, provider, and
Gateway tests; compare Frozen Subject paths against current main; verify both
historical VAM-002 DEPs and this integration DEP strictly; then create a new
gate whose base is current main, reviewed head is the committed VAM-002
candidate, receipt is `REV-VAM-002`, and rollback is this DEP's guarded
VAM-002-only rollback. Any failure falsifies a conflict-free governance-only
integration.

## Conclusion

Confirmed. The defect is stale delivery metadata caused by sequential base
advancement, not a product-source merge conflict. The fix must refresh evidence,
rollback, digest, gate, and independent review without changing the approved
Memory Change Envelope contract or reusing VAM-003 authority.
