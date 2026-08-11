# Decision Record: Additive Subject Task Authorization v2 Bridge

Date: 2026-08-12
Decision ID: `SD-TASK-AUTH-V2-BRIDGE`
Status: Approved for implementation by the owner

## Context

The completed T-001 control plane is content-addressed. Its original runner,
verifier, schema, evidence validator, progress validator, atomic writer, tests,
environment proof, and completion references are historical trust artifacts.
Changing those bytes would invalidate the T-001 proof chain.

The original runner deliberately supports only T-001. The shared verifier is
task-generic, but the runner scope, proposal parser, and prestart rule are not.
The original progress writer can also start a later task without a task-specific
authorization proof. Therefore T-002 cannot safely begin by modifying or
reusing the v1 runner as though it were already generic.

## Decision

Add a separately versioned v2 bridge. Preserve all v1 and T-001 immutable
bytes. The bridge does not delegate owner authority to an Agent: every task
still requires an exact owner-confirmed proposal and receipt digest.

This immutable v2 release authorizes only T-002. Before T-003, an additive
version-dispatch release must be introduced; historical v2 files remain
unchanged and continue validating the T-002 proof. The bridge consists of:

- a closed protocol contract anchored to the completed T-001 ledger;
- one immutable, exact-path scope descriptor per task;
- a v2 proposal/confirmation runner that reuses the pinned v1 private
  receipt/scope lifecycle and verifier;
- an atomic public proof published only after verified private cleanup;
- a proof-aware start wrapper that records the proof in the task's
  `PENDING -> IN_PROGRESS` event; and
- a closed completion-review packet and atomic completion path; and
- a required CI overlay that rejects T-002 starts or completion events lacking
  the exact proof, review, output, prior-ledger, and task bindings.

The owner approval for this bridge is a product/governance decision, not a
substitute for a later task confirmation. `owner_confirmation_ref` is an audit
reference only and is not represented as cryptographic proof of chat identity.

## T-002 Scope Resolution

The wildcard prose in the frozen T-002 task header is resolved to a reviewed,
closed descriptor before proposal generation. The descriptor authorizes only:

- four synthetic fixture files covering Person, Organization, Fragment/failure,
  and Migration/failure cases;
- the fixture manifest;
- the privacy/schema test;
- the per-task public proof; and
- the byte-identical public-safe completion-review proof; and
- the atomic progress/proof transient paths.

No recursive glob, caller-selected directory, deletion, product runtime,
production migration, live/private data, deploy, or release action is granted.
The protocol contract contains a stable closed descriptor policy rather than a
mutable digest manifest. Each proposal and durable proof binds its own exact
descriptor path, digest, resolved path set, and frozen task-header digest, so a
later descriptor can be added without invalidating earlier task proofs.

## Proof And Replay Rules

The durable proof binds the task, exact base, baseline, predecessor ledger
digest, descriptor, resolved paths, proposal, receipt, scope, v1 trust roots,
v2 bridge bytes, timestamps, and owner confirmation audit reference.

The proof is published with no-follow, no-overwrite, fsync, mode `0644`, and
byte-identical recovery. A different existing proof, descriptor drift, ledger
drift, cross-task replay, or any task state other than `PENDING` is denied.
Private receipt and scope bytes remain repository-external and are cleaned by
the pinned v1 lifecycle before public proof publication.

Completion does not accept a caller-chosen review ID. A distinct reviewer
produces a closed, canonical, repository-external public packet that binds the
exact six output paths, modes, hashes, verification argv and zero exit, exact
authorization proof, distinct builder/reviewer principals, P0=0/P1=0, and the
exact pre-completion progress sequence and digest. The six outputs plus proof
are the seven immutable reviewed changes; the mutable progress ledger remains
inside the exact Git path closure but is validated as a semantic transition.
The wrapper retains that packet and the reviewed source/trust bytes by
descriptor, publishes a byte-identical `T-002.review.json`, derives the review
ID from its SHA-256, and atomically writes the exact ten completion refs under
the same progress lock. A post-publication validation failure rolls the ledger
back; the identical review proof is recoverable for a safe retry.

The review packet is content-addressed audit evidence, not cryptographic proof
of reviewer identity and not an authority credential. Owner authority remains
in the exact per-task authorization proof. Before publishing the review, the
wrapper mechanically derives the current Git delta from the proof base, checks
HEAD/base and the exact eight pre-review paths, binds the seven immutable
paths/actions/modes/hashes plus their canonical change-set digest, and binds
the eighth path to the exact pre-completion progress sequence and digest. It
rejects every extra tracked or untracked path and requires an already-valid
`IN_PROGRESS` ledger whose latest start or resume is no later than the review.
After review publication the exact delta is nine paths; required CI reconstructs
the pre-completion prefix from the completed ledger, validates the final ledger
semantically, and rejects drift. The verification command is executed by
the engineering/review workflow and again by required CI; the packet's claimed
exit result alone is never sufficient for Git delivery or merge.

## Enforcement Boundary

The old writer remains byte-immutable. It is therefore not the sole v2
authority boundary. The supported start path is the v2 wrapper, and the GitHub
required CI suite runs the v2 ledger validator. A direct v1 transition without
the exact v2 proof refs fails that gate.

The hand-written JSON Schema is a documentation mirror. The duplicate-safe,
canonical, fail-closed Python validator is the executable authority for the
cross-file proposal, proof, review, descriptor, output, and progress
correlations; tests require the mirror's proof keys to remain in parity.

T-031/T-033 must use the matching versioned validator when building the
reviewed closure and attestation. T-002 must have exactly one v2 proof; missing,
extra, duplicate, wrong-task, wrong-ledger, or byte-drifted proofs deny closure.

## Reopen Conditions

Reopen this decision when the baseline, v1 trust root, descriptor, product/risk
boundary, or owner authorization policy changes. A changed descriptor requires
a new base, proposal, owner confirmation, and proof; an already-started task's
descriptor and proof are immutable.
