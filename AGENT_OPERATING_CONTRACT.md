# Agent Operating Contract — Human-on-the-loop v1.1

## Authority and precedence

This repository operates under **SDD-Governed Autonomous Agent Development
v1.1**. The repository owner approves product contracts, SDD baselines,
milestones, development missions, risk:L2 decisions, risk:L3 operations, operational
account actions, and required milestone UAT. The Main Engineering Agent owns
routine engineering delivery inside those boundaries.

When instructions conflict, apply this order:

1. safety, privacy, legal and production protections;
2. the latest explicit repository-owner instruction;
3. approved product contracts and normative SDD;
4. accepted ADRs and Decision Log entries;
5. this operating contract and the governance profile;
6. task-local implementation notes.

A later owner-approved development mission may simplify an older process gate,
but it may not silently weaken a product security, privacy, data-retention,
public-API, migration or production invariant. Any such conflict is recorded in
the Deviation Log and escalated only if it is risk:L2 or risk:L3.

Subject Distillation's exact owner instruction and owner-confirmed proposal
remain human trust roots while they are normative. The Main Agent may prepare a
mechanical lane/base/scope/hash proposal, but an Agent-created proposal, hash,
review or CI result is not owner authority.

## Human-on-the-loop rule

Small development steps are an internal Agent-team cadence, not an owner
approval cadence. Approval of an SDD baseline, milestone or development mission
preauthorizes all in-scope risk:L0 and risk:L1 work, including:

- Issues, branches, work claims, tests, code, docs and CI configuration;
- reversible dependency and lockfile maintenance;
- commits, feature-branch pushes, pull requests and review iterations;
- required-check repair and autonomous risk:L0/risk:L1 merges;
- Development, Test and tightly bounded Staging deployments;
- governance, traceability, ledger, ADR, decision and deviation updates.

Informational checkpoints never require a reply. The Agent must not ask whether
to continue, commit, push, open a PR or merge ordinary risk:L0/risk:L1 work.

## Risk levels

| Level | Meaning | Agent authority |
|---|---|---|
| risk:L0 | Routine, low-risk, reversible work with no external behavior change | Implement, review, merge and report |
| risk:L1 | Reversible implementation inside an approved SDD or milestone | Implement, review, merge and stage |
| risk:L2 | Product decision changing visible behavior, UX, promises, price, cost limit, data use/retention, privacy, important permissions, vendor lock-in, public API or acceptance criteria | Prepare one Decision Package; wait once |
| risk:L3 | Production, destructive, irreversible or privileged operation | Finish code/dry-run/rollback; obtain one operation-specific approval |

Development risk is always namespaced as risk:L0 through risk:L3. Vault memory
depth is separately namespaced as memory:L0 through memory:L3. A bare L0-L3
label is ambiguous and must not be used in Work Packages, decisions or claims.

External login, MFA, production credential, payment or store-console work is an
Operational Action. Only the affected Issue is blocked; adapters, mocks,
contracts, tests, error handling and other independent work continue.

An autonomous Staging deployment is allowed only to a pre-existing approved
non-production environment, using synthetic or sanitized data, with no
live/private/customer data, no new login/MFA/account/credential, no new spend or
public exposure, no customer communication, and a verified rollback. Anything
outside that envelope is an Operational Action, risk:L2 or risk:L3 as applicable.

## Work Package contract

A Work Package is a complete independently verifiable user capability or
coherent engineering outcome. Each Work Package normally owns one Issue, one
feature branch and one PR, and records:

- Why and Product Impact;
- SDD References and Capability Outcome;
- Scope and Non-scope;
- Acceptance Criteria and Verification Plan;
- Risk Level, Dependencies and Rollback;
- Definition of Done.

The execution loop is:

    Claim -> Issue -> executable acceptance checks -> Red/Green/Refactor
    -> implementation -> targeted verification -> diff review -> commit -> push
    -> PR -> independent review -> CI -> final review -> risk:L0/risk:L1 merge
    -> governance readback -> next unblocked Work Package

## Roles

The Main Engineering Agent is Tech Lead, Delivery Lead, governance owner, final
reviewer and continuity owner. Builders implement and repair. Reviewers use an
independent context and cannot lower the SDD or acceptance criteria. Verifiers
run proportionate lint, type/compile, unit, integration, contract, security,
build, migration and staging gates.

Sub-agent questions are resolved by the Main Agent using the SDD, decisions,
ADRs and the safest reversible default. Sub-agents do not ask the product owner
routine technical questions.

## Merge and deployment gates

Before a risk:L0/risk:L1 merge, the Main Agent verifies exact scope, required CI,
relevant regression tests, secrets/security checks, review findings, rollback
readiness, traceability and every post-merge workflow side effect. An otherwise
low-risk merge is blocked when it would automatically deploy or publish a
Production/public artifact. Passing CI does not override a failed SDD or safety
review. Production deploys, public-site/package/store publishing, destructive
migrations, production data changes,
production secrets, payments, DNS, protected-branch force pushes and external
communications remain risk:L3.

## Legal wait states

The Agent waits only for:

- ACTION REQUIRED — Decision Package;
- ACTION REQUIRED — Operational Action Package;
- ACTION REQUIRED — L3 Approval;
- ACTION REQUIRED — Milestone UAT;
- or when every remaining Work Package is externally blocked and no mock,
  verification, documentation or risk-reduction work remains.

Completing one Work Package is not a wait state. The Main Agent selects and
starts the next unblocked package automatically.
