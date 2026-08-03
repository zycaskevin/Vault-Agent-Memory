# Architecture Decision Records

The established `docs/decision_records/` directory remains the canonical archive
for existing product and engineering decisions. This `docs/adr/` directory is
the structured ADR namespace introduced by Governance v1.1; it does not migrate,
rewrite or silently supersede those records. When both namespaces address the
same subject, the newer accepted record must explicitly link and supersede the
older record. `docs/governance/DECISION_LOG.md` records risk:L2 owner decisions;
an ADR records the approved decision's technical realization.

Use an ADR when an implementation makes a durable, non-obvious technical choice
inside an approved product/SDD boundary. Product-level risk:L2 decisions belong in
the Decision Log first; the ADR records their technical realization.

Copy 0000-template.md, assign the next four-digit identifier, and record status,
context, decision, consequences, verification, rollback and reopen conditions.
Accepted ADRs are immutable except for links and typo fixes; a new ADR
supersedes an old decision.

## Index

No ADR has been accepted under Governance v1.1 yet. `0000-template.md` is a
template and has no decision authority.
