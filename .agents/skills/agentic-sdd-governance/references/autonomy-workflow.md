# Autonomous Development and Escalation

Default to `CONTINUE`. Before stopping, evaluate in order: Repository/SDD, Decision/ADR, Tests/CI/Tools, safe reversible L0/L1 decision, then whether only one Work Package is blocked. Only unresolved L2, concrete L3, Operational Action, or Necessary UAT may produce `ACTION REQUIRED`.

Never ask for approval to create an Issue, Branch, Commit, feature-branch Push, PR, Review, test, retry, integrity check, or L0/L1 Merge after required gates pass. Never ask a human to copy, paste, calculate, compare, or approve SHA-256.

Use:

```bash
sddgov autonomy evaluate request.json --path .
sddgov checkpoint --summary "..." --next-work-package WP-002
sddgov artifact lock dist/package.whl --release release-X --output release.lock
sddgov artifact verify dist/package.whl --lock release.lock
sddgov decision import-operation-approval signed-approval.json --path .
sddgov merge verify . --base-ref <exact-base>
```

Every known action request must include an explicit `effects` object. Use `{}` only after classification confirms that no Production, destructive, irreversible, Secret, permission-boundary, real-payment, or high-privilege effect applies.

Record an approved L2 decision once in `.sddgov/decisions.json` and reuse it while assumptions remain unchanged. L3 requires a trusted-owner Ed25519 receipt that is fresh, exact, unexpired, and atomically consumed on the first `CONTINUE`; a previous product decision or caller string never authorizes a new L3 operation.

Unknown categories and dangerous L0/L1 downgrades fail closed for machine reclassification. Before Merge, execute the Merge verifier; do not treat `policies/merge-policy.yaml` as self-enforcing documentation.

For Production, L0 is invalid. A routine reversible L1 deploy is autonomous only with recorded Baseline authorization and every guard in `policies/autonomy-policy.json`. Missing evidence blocks and triggers investigation; it does not become an approval request by itself.

Sub-agents report uncertainty to the Main Agent. The Main Agent performs lookup, evidence gathering, classification, and L0/L1 resolution before any owner escalation.
