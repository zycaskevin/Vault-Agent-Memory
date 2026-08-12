# Decision Record: Version-dispatched Subject authorization for T-003

Date: 2026-08-12
Decision ID: `SD-TASK-AUTH-V2-T003`
Status: Approved for implementation by the owner

## Context

T-001 and T-002 are terminal, content-addressed trust chains. The immutable v2
bridge deliberately supports only T-002, and its full validator cannot be
reused after a later task changes the Git delta or progress ledger. Editing any
v1 or v2 trust byte would invalidate already accepted evidence.

## Decision

Add protocol version 3 as the T-003 implementation of the approved v2
version-dispatch policy. Preserve every v1, v2, T-001 and T-002 trust byte.
Version 3 authorizes only T-003 and does not delegate task authority to an
Agent. T-003 still requires an exact owner-confirmed proposal and receipt
digest after this bridge is merged.

The dispatcher always runs the v3 validator for the T-003 release. The v3
validator reconstructs and byte-binds the exact sequence-4 T-002 terminal
prefix before validating the T-003 proof, review, outputs and atomic ledger
transitions. It does not re-run the frozen v2 full Git-delta validator after
the additive bridge commit because that validator correctly rejects paths that
were not part of the completed T-002 delivery. Instead, the v3 contract binds
the frozen v2 runner, validator, updater, contract, schema, descriptor, proof,
review, outputs and terminal event bytes. Any T-004 or later transition
remains denied.

## T-003 resolved scope

The exact descriptor allows only:

- `scripts/export_subject_sbe_traceability.py`;
- `specs/subject-distillation/sbe-traceability.json`;
- `tests/test_subject_sbe_traceability.py`;
- T-003 proof and completion-review artifacts;
- the progress ledger and two fixed transient pending paths.

The exporter is mode `0755`; other persistent artifacts are mode `0644`.
The completion review binds both canonical verification commands. Runtime,
database, migration, live/private data, deployment, release, deletion and
T-004+ artifacts are outside the grant.

## Activation and replay

The v3 contract binds main commit
`c52ef13c1ef986dbf5a66c16107026daa09fc620`, the exact sequence-4 progress
digest, T-001/T-002 event digests, and every immutable v2 proof/review/output
and bridge trust artifact. Proposal generation requires this exact prestart
state. A changed activation prefix, descriptor, baseline, task header, trust
root, base, proof or repository identity denies.

The proof lifecycle retains the v1 private no-follow verifier and cleanup
boundary. The public proof, proof-aware start, closed completion-review packet,
atomic completion, rollback and idempotent recovery use the versioned v3
scripts. Private receipt and scope bytes remain repository-external and are
never persisted in Git.

## Reopen conditions

Reopen on baseline, descriptor, owner policy, product/risk boundary, trust-root
or repository identity change. Before T-004, add another reviewed version
dispatch release; do not broaden v3 in place.
