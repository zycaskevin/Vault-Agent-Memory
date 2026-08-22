# Root Cause Hypothesis

## Hypothesis

The contracts were reviewed as prose or shell fragments without independently
binding every parser, pipeline-status, path-scope, and provenance boundary.

## Supporting evidence

The H2 helper matched raw substrings; approval validation used a pipeline; the
rollback candidate lacked an exact changed-path assertion; two approved
integration prohibitions were not tested; remediation rollback lacked exact
anchors and full proof requirements.

## Contradicting evidence

Current content and normal success paths passed, showing the omissions were
fail-closed and regression-contract gaps rather than current product corruption.

## Falsification test

Exercise fenced/prose heading decoys, assert all forbidden boundaries, bind
approval capture and path allowlist order, and make rollback provenance and
verification requirements exact.

## Conclusion

Confirmed. The smallest sufficient fix is limited to VAM-001 documentation
contracts, rollback records, tests, this DEP, and audit metadata.
