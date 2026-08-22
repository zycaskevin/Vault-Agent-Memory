# Canonical Memory Object contract

Date: 2026-08-21
Decision ID: VAM-005-memory-object-contract
Risk: L2
Status: approved for implementation; focused architecture review required before merge

## Context

The owner froze Vault as governed memory infrastructure and named five object
kinds plus six infrastructure capabilities. The completed boundary ADR,
bootstrap cleanup, and change envelope do not by themselves provide one stable
machine-readable base object contract.

An older uncommitted VLT-001 worktree contains a broad draft of this direction,
but it overlaps multiple isolated Work Packages and includes large unrelated
documentation rewrites. Committing that dirty draft as one change would make
review, rollback, and provenance unclear.

## Decision

Extract only the unique Memory Object behavior into VAM-005, stacked on
VAM-002. Define exactly five canonical kinds and six core capabilities. Adapt
legacy rows without migration, preserve unknown legacy types as opaque
application metadata, add candidate-first provider operations, accept additive
HTTP create aliases, and publish the contract through OpenAPI/provider health.

Do not commit, clean, reset, or rewrite the original dirty VLT-001 worktree.
Do not duplicate VAM-003's L0/docs cleanup or expand into an application-domain
runtime.

## Consequences

- New integrations have one base Memory Object envelope and canonical kind set.
- Existing storage and clients remain compatible.
- VAM-002 change envelopes use the same canonical kind mapping.
- The PR is stacked on #500 and must be rebased/retargeted after its dependency
  lands.
- Independent focused architecture review remains a merge prerequisite.

## Reopen conditions

Reopen if a sixth generic kind is proposed, the compatibility schema cannot
represent a required envelope field, or consumers require a transport behavior
beyond the existing candidate-first/read-policy boundary.
