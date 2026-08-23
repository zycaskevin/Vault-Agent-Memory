# Rollback

## Trigger

Rollback only if a verified review shows that the semantic record corrections
are false, the normalized contract test masks a real SDD mismatch, or the
authoritative rollback preservation/allowlist additions are incorrect.

## Reversible steps

Revert only the immutable implementation commit identified in the final
verification record, without committing. Restore this DEP from current HEAD so
the Red/Evidence/Fix/Green/Proof audit trail remains. Fail closed unless the
staged path set is limited to the five corrected existing files plus the
authoritative rollback and boundary regression changes recorded in Fix Scope.

## Data compatibility

No runtime, schema, migration, database, cursor, candidate, audit event, API
response, Hermes workspace, or production data is changed by this remediation
or its rollback.

## Post-rollback verification

Confirm the bounded path allowlist and no untracked files. Run the original
four-condition static probe and record the expected pre-fix failures, then run
the unaffected VAM-002 focused baseline, Ruff on staged Python files,
`git diff --check`, strict verification of the preserved DEP, and repository
Local Green. Only the documented RED probe may exit nonzero; every separate
Green command must exit zero.
