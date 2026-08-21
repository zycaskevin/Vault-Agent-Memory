# Extract Subject Distillation from Vault Agent Memory

Status: accepted

Date: 2026-08-21

Decision: `DEC-VAM-001`

## Context

Vault Agent Memory is governed memory infrastructure for AI agents. It owns
domain-neutral storage, retrieval, provenance, confidence, lifecycle, and
governance for Memory Objects.

The frozen Subject Distillation package grew beyond that responsibility. Its
requirements cover person models, identity claims, belief and relationship
evolution, reflection, review, temporal identity, and purpose-scoped Context
Packs. Those are application-domain semantics built on memory; they are not
generic memory infrastructure.

PR #494 completed the pure Generic Subject contracts at T-004 and merged them
into `main`. The historical ledger still has T-005 through T-033 pending, and
Issues #495, #496, and #497 would continue the old Vault-owned runtime path.

## Decision

Subject Distillation runtime ownership moves to a separate product and clean
repository: Digital Life Identity Runtime. Vault will not implement the
remaining Subject runtime tasks.

Vault preserves the existing Subject research and T-001 through T-004 outputs
as origin provenance. Preservation does not make those artifacts an active
Vault runtime roadmap, and it does not transfer Vault's Mission V4/V5/V6
authority machinery to Digital Life Identity.

The new repository will use selected-source extraction with verifiable origin
metadata and Apache-2.0 attribution. It will not be a Vault fork and will not
carry Vault's full history or product surface.

## Why Subject crossed the Memory boundary

Memory infrastructure answers questions such as what was stored, where it came
from, how confidently it is held, who may retrieve it, and when it expires.

Identity modeling answers different questions: what evidence may support a
claim about a person, how contradictory observations are handled, how beliefs
or preferences change over time, who reviews an inference, and which claims
may enter a purpose-scoped Context Pack. These decisions require their own
privacy, review, temporal, and product policy. Keeping them in Vault would make
the memory provider responsible for one consumer application's semantics.

## What Vault retains

- Generic Memory Objects and the memory storage/retrieval contract.
- Provenance, confidence, lifecycle, governance, audit, and bounded reads.
- The merged Generic Subject contracts as preserved origin material.
- The frozen Subject Distillation specification, evidence, and T-001 through
  T-004 history without reinterpretation or mutation.
- A future generic Memory Change Envelope developed independently as VAM-002.

Vault does not retain ownership of Person Model, Identity Claim, personality,
belief evolution, relationship evolution, reflection, or Identity Context
Pack runtime behavior.

## What Digital Life Identity owns

Digital Life Identity owns Subject Core application semantics, Evidence
References, Life Signals and Life Events, Reflection Runs, Identity Candidates,
Candidate Evidence Graphs, Review Decisions, Identity Claims, supersession,
versions, timelines, snapshots, and purpose-scoped Context Packs.

It owns a separate `identity.db` and its own repository interfaces. It does not
become the source of truth for raw conversations, general documents, or Vault
memory.

## Preserved T-001 through T-004 origin

T-001, T-002, T-003, and T-004 remain `COMPLETED` in the historical progress
ledger. Their canonical specification, authorization, review, evidence, and
merged Generic Subject contract outputs remain unchanged.

The active code candidates for future provenance-based extraction are
`vault/subject_contracts.py` and `tests/test_subject_contracts.py`, originating
from PR #494. Any extraction must record source and destination hashes plus a
modification notice in the new repository.

## Why T-005 through T-033 are not continued

T-005 through T-033 remain `PENDING` in the historical ledger. They are not
marked completed, cancelled, or blocked, because no such historical transition
occurred. Instead, this decision records that Vault will not start or continue
them.

Continuing those tasks would build Subject database tables, identity runtime,
and Mission control-plane machinery inside the wrong product. Useful general
principles—such as fail-closed migrations and WAL-aware backup—may inform new
DLI designs, but Vault-specific implementations and authority are not ported.

## Issue disposition

| Issue | Disposition | Reason |
|---|---|---|
| #410 | Keep open until DLI Sprint 1 has a stable repository location; then link the new origin and close as moved/completed. | Preserves the public historical chain without claiming a destination that does not exist yet. |
| #495 | Close as superseded, not completed. | Its VaultDB/v15 task will not run; general migration-safety ideas may be redesigned for DLI's separate IdentityDB. |
| #496 | Close as not planned. | Repairing Mission V5 solely to authorize T-005 has no remaining product value. |
| #497 | Close as superseded by this architecture decision. | Mission V6 and continued T-005 through T-033 authority are no longer required. |

VAM-001 initially prepared comment drafts only. A later concrete owner
instruction executed the bounded disposition: comments were posted and Issues
#495, #496, and #497 were closed; #410 remains open. The action and its
non-reusable authorization basis are recorded as
`VAM-001-ISSUE-DISPOSITION`. This record grants no authority for another
external mutation.

## Origin

- Source repository: `zycaskevin/Vault-Agent-Memory`
- Source commit: `291d5595c9cb2208a6b74206acbba35a883eb918`
- Source delivery: PR #494, “feat: add generic Subject contracts (T-004)”
- License: Apache-2.0

The new repository must include an `ORIGIN_MANIFEST.json` with source path,
destination path, source hash, destination hash, extraction mode, license, and
modification notice.

## Compatibility

This decision changes no Vault runtime, database schema, CLI, MCP, Gateway, or
Memory API. Existing Subject contract imports continue to work in Vault. The
frozen specification and ledger remain readable as historical origin.

No existing data is migrated or reclassified. VAM-002 and any DLI adapter are
separate behavior slices with separate review.

## Rollback

If this record misstates the owner decision, revert the VAM-001 documentation,
test, and local governance records. No data rollback is required.

Once a new product has relied on this decision, a future architecture change
must supersede this ADR rather than erase the provenance trail.

## Future integration contract

The dependency direction is one-way:

```text
Digital Life Identity Runtime
        -> generic Vault Memory API / Memory Provider protocol
        -> Vault governance and bounded evidence reads
```

The Vault adapter lives in the Digital Life Identity repository. Vault treats
DLI payload semantics as opaque application data.

The following are forbidden boundaries:

- Vault imports `digital_life_identity`.
- Digital Life Identity reads `vault.db` or imports VaultDB internals.
- Either repository creates cross-database foreign keys.
- Vault adds identity-, personality-, or subject-model-specific endpoints.

Real personal data, private shadow evaluation, production migration, release,
deployment, and external runtime injection remain separate L3 actions requiring
explicit authorization.
