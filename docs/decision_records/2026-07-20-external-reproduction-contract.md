# External reproduction contract

Date: 2026-07-20

## Decision

Vault accepts third-party benchmark evidence through a versioned, fail-closed
submission contract rather than screenshots, copied headline numbers, or an
informal statement that a benchmark was rerun.

The v1 kit supports the pinned `mem0 2.0.12` VaultGovBench retrieval track. It
provides a single runner, blinded provider input, five fresh-store repeats,
environment capture, exhaustive checksums, an operator attestation, a public
issue form, and CI validation. Other providers require their own pinned runtime
and publication gate before entering this contract.

## Evidence states

1. `Environment blocked`: setup or partial execution reached a disclosed stage,
   but an external network, runtime, storage, memory, or platform prerequisite
   prevented five repeats and a valid bundle. Diagnostic evidence only.
2. `Submitted`: an operator has supplied a public bundle; no technical claim.
3. `Contract validated`: checksums, schema, protocol, and release gates pass.
4. `Maintainer reviewed`: maintainers inspected attribution, conflicts,
   environment evidence, and deviations.
5. `Published external reproduction`: the reviewed record is linked publicly
   with its operator and immutable source.
6. `Rejected`: the bundle is invalid, unsafe, incomplete, or overclaims.

Contract validation is not identity verification, endorsement, statistical
independence, or proof of external validity. The website must continue to say
that no third-party reproduction has been accepted until a reviewed record
exists.

## Safety and provenance

Submissions must contain no credentials, private memory, customer data, or
unrelated environment secrets. The provider process receives only blinded
input. A clean 40-character source revision, fixed provider version, exact
repeat count, public operator handle, conflicts disclosure, and artifact
checksums are mandatory. Maintainers may reject a technically valid bundle if
its provenance or disclosure is insufficient.

The documented virtual environment and output directory must remain outside
the checkout. Ignoring an in-repository environment would hide source-tree
noise instead of preserving the clean-source invariant. The pinned FastEmbed
prewarm requires access to Hugging Face; an allowlist denial is classified as
`Environment blocked`, not provider failure and not a reproduction result.

Before execution, the stdlib-only machine-readable preflight must fail closed
on dirty source, an in-repository virtual environment or output path, dependency
drift, Python outside `>=3.10,<3.14`, insufficient disk or memory, and an unavailable model host without a
complete pinned cache. A preflight pass proves environment readiness only. An
owner-operated portability smoke must set `independent_operator` to false and
use a distinct artifact type, so it cannot enter the external evidence ladder.
