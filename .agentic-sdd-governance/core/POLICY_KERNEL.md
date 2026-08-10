# Policy Kernel

Read this file at the start of governed development. Load detailed modules only when the current task needs them.

1. An approved SDD or Milestone pre-authorizes in-scope L0/L1 engineering work.
2. Issues, Commits, PRs, Reviews, CI, and local evidence are engineering records, not new human approval points.
3. A Main Agent absorbs routine sub-agent questions; sub-agents do not escalate ordinary technical choices to the product owner.
4. Interrupt a human only for unresolved L2 product decisions, a concrete L3 operation, an external owner action, or required Milestone UAT.
5. An external blocker blocks only the dependent Work Package; continue other safe work.
6. A Builder may not silently weaken acceptance criteria, tests, redaction, or final verification.
7. Required Evidence must be locally redacted and verified before Merge; raw evidence remains private.
8. Checkpoints are informational unless explicitly titled `ACTION REQUIRED` with one bounded decision or operation.
9. Respect the Approval Budget and do not ask the same decided question again unless its recorded reopen condition occurs.
10. Continue to the next unblocked Work Package until a documented legal stopping condition is reached.

Runtime load set:

```text
Policy Kernel + Project Profile + Current Work Package + Relevant Playbook
```

Do not load the entire repository as routine context.
