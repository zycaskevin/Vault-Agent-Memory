# Root Cause Hypothesis

## Hypothesis

The exact-head proof was added directly to the shareable evidence set without
passing its checkout field through the workstation-path redaction rule.

## Supporting evidence

- The Red test found `/home/` on the artifact's `checkout=` line.
- The manifest bound the unredacted artifact hash.
- The redaction report had no entry for the new artifact.

## Contradicting evidence

Older stable-root artifacts already use placeholders and have matching
source/output provenance. The exposure is limited to the newly added artifact.

## Falsification test

Replace the checkout value with `$BUILDER_WORKTREE`, bind the output hash in the
manifest, record the original and redacted hashes in the report, and rerun the
strict evidence verifier and regression test.

## Conclusion

Confirmed. Applying the existing evidence-redaction pattern makes both the
regression test and strict DEP verification pass.
