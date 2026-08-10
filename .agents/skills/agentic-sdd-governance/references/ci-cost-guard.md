# CI Cost Guard Route

Read `docs/CI_COST_GUARD.md` under the Governance Root when work creates, modifies, reruns, or diagnoses CI.

Before Push:

1. Read `.sddgov/ci-cost-guard.json`.
2. Run `sddgov ci verify .`.
3. Run `sddgov ci local-gate .`.
4. Batch the bounded Work Package into one reviewable revision.
5. Do not rerun the same revision unless Evidence proves a transient failure.

Use the DEP debugging route for a non-transient CI failure. CI optimization is L1 only while acceptance criteria and required proof remain unchanged. Billing, paid runners, and self-hosted runner installation remain L3 external actions.
