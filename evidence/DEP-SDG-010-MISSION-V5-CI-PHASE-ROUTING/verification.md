# Verification

## Builder Green

The candidate-routing revision ran under the externally coordinated exclusive
test lease; repeated process audits found no unrelated same-repository pytest,
identity harness, Local Green, or merge-verify process. The focused suite
passed 92 tests in 46.37 seconds.

The one Builder Local Green completed successfully:

```text
identity-isolated subject tests passed: 431 nodes
2869 passed, 12 skipped, 1 warning in 94.73s
```

Doctor, CI contract verification, README smoke, and release parity also
returned zero. The warning is the existing invalid-escape SyntaxWarning in
`tests/test_semantic_chunk_coverage.py`; it is outside this Work Package.

## Candidate-routing result

The candidate route accepts either an exact active delivery anchor with a
lawful descendant or a closed linear topic replayed inactive. A purported
invalid delivery remains DENY and does not fall back to the topic route. The
strict DEP verification records this result for independent review.

## Rollback record correction

The rollback record now resolves exactly one merged source-branch PR and
requires an exact two-parent merge before reverting. Its machine verification
uses the retained canonical dispatcher/progress invariants, so it remains
available after the routed identity harness itself is reverted. A post-
activation rollback instead requires mission revocation and fresh authority.
