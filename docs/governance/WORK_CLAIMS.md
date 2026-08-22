# Work Claims

| Claim | Owner | Capability outcome | Risk | Base | Owned paths | State |
|---|---|---|---:|---|---|---|
| WP-GOV-001 / #427 | Main Engineering Agent | Repository can run auditable Human-on-the-loop delivery without per-step owner prompts | risk:L0 | cfee9429c64a1dfa86bc14b126666979a6ce2611 | `work-claims/WP-GOV-001.yaml` | CLAIMED |
| WP-SD-B001 / #429 | Builder Agent, queued | Owner-approved SDD can produce and verify a canonical T-001 authorization while leaving no private artifact | risk:L1 | exact owner-selected clean main after WP-GOV-001 | runner, runner tests, capability-state governance records | BLOCKED_INTERNAL |
| WP-CI-001 / #428 | Builder Agent, queued | New changes cannot add lint/dependency debt without blocking on historical debt | risk:L0 | latest clean main after WP-GOV-001 | CI, debt baseline/report, verification tests/docs | QUEUED |

## Claim rules

- One active owner per Work Package; duplicate work joins or supersedes the claim.
- A claim records capability scope, not permission to cross risk:L2/risk:L3 boundaries.
- Existing user changes are preserved and inventoried before reuse.
- Claims release on merge, supersession or a documented blocker; stalled work
  does not prevent independent packages from continuing.
- Active claim records under `work-claims/` enumerate exact owned paths so
  concurrent agents can detect overlap mechanically.
