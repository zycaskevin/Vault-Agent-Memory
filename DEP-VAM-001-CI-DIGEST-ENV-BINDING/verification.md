# Verification

## Green command and result

Pending until the final non-audit implementation/DEP commit exists. Calculate
its digest only under the pinned CI contract environment, update the gate in a
separate audit-only commit, and rerun Local Green plus hosted CI.

The divergence reproduction passed against exact head `b2c8378`: default
`e155240b...` versus CI-contract `1ba66ab1...`. The final gate remains pending
until all non-audit remediation and proof records are committed.

Complete Local Green passed the current remediation tree: all 446
identity-isolated Subject nodes and 2,928 repository tests with 10 skips. The
final CI-contract digest is intentionally calculated only after the non-audit
commit exists.

## Before/after evidence

Before: the declared default-environment digest differed from hosted
verification. After: the gate will declare the CI-contract digest for the same
exact base and implementation head.

## Remaining limitations

This repository DEP does not modify the external governance CLI's digest
implementation. Future gate generation must retain the pinned CI environment
until upstream canonicalizes Git diff object IDs independently of config.
