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
non-audit implementation commit is
`4b4bef132eca531165ca6a5dad88d104e37e40d2`. Under the pinned CI contract it
produced digest `120dbb4c0d2963266785459d44eac8ebbb9f0b19357799b30b68278d4866dd82`,
which matches the audit-only gate commit
`d57edaec8e6e6339be3df4f4163a4c2531028c04`. The resulting gate metadata digest
is `bbf9bf429d9a0a5245951a0b87e055eee0c88cb431e7f85737db84dbc7c97efa`.

A fresh clean clone at audit head
`d57edaec8e6e6339be3df4f4163a4c2531028c04` ran exact CI-pinned merge
verification. Its only error was this DEP's intentionally pending Fix phase; no
cleanliness or digest mismatch remained. This closes the environment-binding
defect without claiming the later Reviewer-receipt gate.

## Before/after evidence

Before: the declared default-environment digest differed from hosted
verification. After: the gate will declare the CI-contract digest for the same
exact base and implementation head.

## Remaining limitations

This repository DEP does not modify the external governance CLI's digest
implementation. Future gate generation must retain the pinned CI environment
until upstream canonicalizes Git diff object IDs independently of config.
