# Fix Scope

## Smallest sufficient change

Define exact canonical JSON v1 config bytes, a 32-byte lowercase-hex HMAC key,
1..64 sorted unique key entries, a 65,536-byte cap, external mode/link/no-follow
requirements, independent constant-time HMAC verification, and bounded child
output/timeout/process-group cleanup. Recompute the Subject baseline manifest.

## Files or components in scope

- `specs/subject-distillation/requirements.md`
- `specs/subject-distillation/design.md`
- `specs/subject-distillation/tasks.md`
- `specs/subject-distillation/baseline-manifest.json`
- this public-safe DEP

## Explicit non-scope

- No T-001 candidate source or test mutation before fresh exact authorization.
- No real private key/config/receipt/gate creation or access.
- No production runtime, migration, deployment, release, push, PR, or hosted CI.
- No change to HMAC algorithm, domain separator, receipt schema, thresholds, or
  experimental/stable label semantics.

## Blast radius

Canonical baseline bytes and baseline ID change. Every prior T-001 proposal and
authorization becomes stale by design. The preserved candidate must be rebased
only after a new exact proposal is confirmed and verified.
