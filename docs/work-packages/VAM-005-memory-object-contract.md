# Work Package: VAM-005 canonical Memory Object contract

## References

- Issue: `docs/issues/VAM-005-memory-object-contract.md`
- SDD: `docs/specs/vam-005-memory-object-contract.md`
- Decision: `docs/decision_records/2026-08-21-memory-object-contract.md`
- Risk: L2

## Objective Contract

- Outcome: give Vault and external integrations one stable, domain-neutral
  Memory Object contract without changing storage or policy authority.
- Success metric: exact-kind/capability tests, legacy mapping tests,
  candidate-first provider tests, Gateway alias tests, OpenAPI parity, VAM-002
  canonical-kind integration, and full Local Green pass.
- Guardrails: no application-domain runtime; no migration; no direct active
  writes; no default adapter switch; no broad docs rewrite; no merge, release,
  or deployment.
- Keep condition: old clients remain green, invalid explicit kinds fail before
  write, unknown legacy types are preserved without interpretation, strict DEP
  passes, and independent focused architecture review is obtained before merge.
- Rollback condition: compatibility break, policy bypass, noncanonical public
  kind, stored-data reinterpretation, or existing API regression.

## Scope

- In scope: `MemoryObject`; machine-readable Memory Layer contract; three
  provider operations; additive create aliases; OpenAPI/provider metadata;
  VAM-002 canonical-kind integration; focused tests; L2 records; DEP; stacked
  Draft PR.
- Non-scope: L0/docs cleanup from VAM-003; Subject extraction from VAM-001;
  cursor/evidence behavior already delivered by VAM-002; application database
  or runtime; package release/version bump; merge/deploy.
- Dependencies: VAM-002 Draft PR #500 / branch
  `codex/vam-002-memory-change-envelope`.
- Evidence requirement: RED, focused Green, compatibility regression, full
  Local Green, strict DEP, and independent focused architecture review before
  merge.
- Verification plan: focused Memory Object/provider/Gateway/OpenAPI tests;
  VAM-002 tests; changed-Python Ruff; full Agentic SDD Local Green.

## Claim

- Agent: codex
- Claimed at: 2026-08-21T10:25:00Z
- Expires at: 2026-08-21T18:25:00Z
