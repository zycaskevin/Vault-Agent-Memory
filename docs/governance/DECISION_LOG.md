# Decision Log

## GOV-DEC-001 — Human-on-the-loop development

- **Date:** 2026-08-03
- **Status:** Accepted by repository owner
- **Decision:** Adopt SDD-Governed Autonomous Agent Development v1.1. Owner
  approval of an SDD baseline, milestone or development mission preauthorizes
  in-scope risk:L0/risk:L1 engineering and delivery. Checkpoints are informational.
- **Reason:** Small engineering steps are Agent-team cadence, not owner approval
  points. Auditability comes from Issues, tests, commits, PRs, reviews, CI and
  ledgers.
- **Guardrails:** risk:L2 decisions, risk:L3 operations, operational accounts/credentials
  and required UAT remain human gates. Product security/privacy invariants are
  not weakened.
- **Reopen condition:** Evidence that autonomous risk:L0/risk:L1 delivery caused an
  uncontained production, privacy, security or acceptance-criteria breach.

## GOV-DEC-002 — First post-Bootstrap capability

- **Date:** 2026-08-03
- **Status:** Accepted as plan sequencing
- **Decision:** Recover and independently verify the existing B-001 runner
  candidate before creating new Subject runtime code.
- **Reason:** It is the first dependency in the approved Subject SDD and avoids
  duplicate work.
- **Guardrails:** Rebase against exact current main; update stale normative
  identifiers; preserve B-001/T-001 separation and fail-closed cleanup.
- **Reopen condition:** Bootstrap or independent review proves the candidate is
  incompatible with the approved SDD or unsafe to salvage.
