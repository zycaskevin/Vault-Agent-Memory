# Root Cause Hypothesis

## Hypothesis

The documentation test models the file as an unordered bag of phrases instead
of a structured Issue record, and the later machine-readable rollback header
was added without reconciling the older compatibility-only prose.

## Supporting evidence

- The test has four heading assertions followed by four global state checks.
- No helper extracts a bounded Markdown section.
- The rollback header targets PR #498's merge commit, but the prose names only
  the compatibility commit and explicitly preserves the ADR.

## Contradicting evidence

The current document happens to place every phrase correctly, and the focused
tests are Green. This shows correct current content, not a sufficient contract.

## Falsification test

Extract each Issue section and assert its own disposition plus the #410
do-not-post condition. Make the rollback target compatibility-only, gate it on
a fresh L3 approval and strict DEP, and run the complete post-rollback checks.

## Conclusion

Confirmed. The smallest fix is section-aware assertions plus a single coherent
provenance-preserving rollback contract.
