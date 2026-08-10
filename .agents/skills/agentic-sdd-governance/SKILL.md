---
name: agentic-sdd-governance
description: Govern software development, bug fixing, refactoring, testing, pull-request review, database changes, deployment preparation, and multi-agent engineering using approved SDD scope, L0-L3 authority, evidence gates, and bounded human escalation. Use for any repository development or debugging task that adopts Agentic SDD Governance; load evidence references only when a failure, regression, incident, or proof requirement is involved.
---

# Agentic SDD Governance

## Bootstrap

1. Resolve the Governance Root: use `.agentic-sdd-governance/` when its `manifest.json` exists; otherwise use the governed repository root.
2. Read `core/POLICY_KERNEL.md` under the Governance Root.
3. Read exactly one selected file from `profiles/` under the Governance Root.
4. Read the current Work Package, SDD references, and existing decisions.
5. Classify the work L0-L3 before mutation.
6. Continue autonomously for approved L0/L1 work. Escalate only within the Policy Kernel boundary.

Do not load every governance document. Use the smallest relevant set.

## Development loop

```text
SDD -> Work Package -> executable check -> implementation -> review -> CI -> proof -> next work
```

Treat Issue, Commit, PR, CI, and Evidence as engineering records, not approval prompts.

For CI creation, modification, reruns, or cost control, read `references/ci-cost-guard.md` and require the repository Local Green Gate before Push.

## Debugging route

When a task includes a failure, bug, regression, incident, flaky test, unexpected UI/API behavior, or a request for verification proof:

1. Read `references/evidence-workflow.md`.
2. Read `references/risk-evidence-matrix.md`.
3. Read `references/dep-contract.md` before creating or validating a DEP.
4. Read only the relevant collector file under the Governance Root named by `references/collector-routing.md`.
5. Read `redaction/LOCAL_REDACTION_GATEWAY.md` under the Governance Root before any artifact may leave local storage.
6. Run `evidence verify --strict` before generating an attachment.

Never fix from a screenshot alone when runtime evidence is available. A screenshot may establish a symptom, not a root cause.

## Records

Use `references/engineering-records.md` for Issue, Commit, PR, Changelog, Root Cause, Fix Scope, Regression Evidence, and Rollback fields.

## Safety

- Keep raw evidence in `private/raw`.
- Never request passwords, tokens, OTPs, private keys, production dumps, or unredacted patient/payment data in chat.
- Evidence changes confidence, not authorization.
- Stop before an unapproved L2 product change or concrete L3 action.
