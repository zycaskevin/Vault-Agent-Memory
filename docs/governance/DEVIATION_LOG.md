# Deviation Log

## GOV-DEV-001 — Legacy per-step authorization language

- **Detected:** 2026-08-03
- **State:** Controlled
- **Conflict:** Older Subject planning combines exact Subject authorization with
  routine Git delivery and merge stop points. The owner has replaced routine
  risk:L0/risk:L1 delivery approvals with Human-on-the-loop mission authority,
  but the canonical Subject SDD still defines exact owner instructions and
  owner-confirmed proposals as sole human trust roots.
- **Resolution:** Routine code, Git, CI and risk:L0/risk:L1 merge transitions do
  not prompt the owner. The Main Agent may mechanically prepare exact base,
  lane, scope and hash proposals, but cannot treat them, a review or CI PASS as
  authority. B-001's exact owner lane/base and T-task exact owner
  proposal/digest confirmation remain required while normative. Byte binding,
  private-material cleanup, fail-closed behavior and task-scope isolation remain
  mandatory product security controls.
- **Risk:** Stale-base work or accidental scope expansion.
- **Controls:** Clean-base preflight, explicit owned paths, exact PR diff,
  independent security review, required CI and rollback-ready commits.
- **Reopen condition:** An explicit owner decision updates the normative Subject
  trust-root protocol, or a proposed change alters Subject security/privacy/data
  invariants, public API, acceptance criteria or enters risk:L3.

## GOV-DEV-002 — GitHub CLI authentication drift

- **Detected:** 2026-08-03
- **State:** Mitigated
- **Observation:** Local GitHub CLI authentication reports an invalid token while
  the GitHub Connector and HTTPS Git credential path remain usable.
- **Resolution:** Use the Connector for Issue/PR/review state and Git credentials
  for feature-branch push. Escalate one Operational Action only if an authorized
  delivery cannot proceed.
- **Security:** Never print, request, store or commit credentials.
