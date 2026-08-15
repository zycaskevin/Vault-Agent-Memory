# Policy Kernel

Read this file at the start of governed development. Load detailed modules only when the current task needs them.

1. An approved SDD or Milestone pre-authorizes in-scope L0/L1 engineering work.
2. Issues, Commits, PRs, Reviews, CI, and local evidence are engineering records, not new human approval points.
3. A Main Agent absorbs routine sub-agent questions; sub-agents do not escalate ordinary technical choices to the product owner.
4. Interrupt a human only for an unresolved L2 product decision, a concrete L3 operation, an Operational Action (external owner action), or Necessary UAT (required Milestone UAT).
5. An external blocker blocks only the dependent Work Package; continue other safe work.
6. A Builder may not silently weaken acceptance criteria, tests, redaction, or final verification.
7. Required Evidence must be locally redacted and verified before Merge; raw evidence remains private.
8. Checkpoints are informational unless explicitly titled `ACTION REQUIRED` with one bounded decision or operation.
9. Respect the Approval Budget and do not ask the same decided question again unless its recorded reopen condition occurs.
10. Continue to the next unblocked Work Package until a documented legal stopping condition is reached.
11. `NO_HUMAN_ESCALATION_IF_MACHINE_VERIFIABLE`: within authorized L0/L1 scope, if Repo, SDD, Decision/ADR, Policy, CI, Tests, Tools, or deterministic verification can answer the question, verify it and continue. Evidence gathering never grants L2/L3 authority.
12. SHA-256 is machine-generated and machine-verified integrity infrastructure. Never ask a human to copy, paste, calculate, or approve a digest.
13. Before stopping, run the escalation classifier. Only unresolved L2, concrete L3, Operational Action, or Necessary UAT may emit the strict `ACTION REQUIRED` Decision Package.
14. A Main Agent absorbs sub-agent uncertainty. L0/L1 technical questions never pass directly from a sub-agent to the product owner.

Runtime load set:

```text
Policy Kernel + Project Profile + Current Work Package + Relevant Playbook
```

Do not load the entire repository as routine context.
