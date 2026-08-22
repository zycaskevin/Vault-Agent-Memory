# Work Package: VAM-003 L0 Bootstrap Boundary

## References

- Issue: `docs/issues/VAM-003-l0-bootstrap-boundary.md`
- SDD: `docs/specs/vam-003-l0-bootstrap-boundary.md`
- Owner decision: Digital Life Identity Runtime v0.1 SDD, 2026-08-21
- Risk: L1 compatibility implementation under approved boundary direction

## Objective Contract

- Outcome: make new Vault bootstrap and setup surfaces memory-neutral while
  retaining read compatibility for historical L0 identity-labelled paths.
- Success metric: focused boundary tests and the complete local governance gate
  pass without schema, stored-data, permission, or frozen Subject changes.
- Guardrails: no legacy data rename/delete, breaking identifier removal,
  identity runtime, DLI dependency, VAM-002 change, merge, release, or deploy.
- Keep condition: RED is preserved, focused and full regressions pass, active
  public guidance is consistent, and the strict DEP verifies.
- Rollback condition: legacy L0 content becomes unreadable, new output still
  teaches Vault-owned human modeling, or unrelated behavior changes.

## Scope

- In scope: canonical project directories; layer source inference; generated
  memory-maintenance guide; active setup/access wording; active README,
  concepts, governance, install, integration, CLI, and manifest wording; tests.
- Non-scope: historical records, Subject artifacts, schema/data migration,
  access semantics, VAM-002, DLI repo work, merge, release, and deployment.
- Dependencies: owner architecture directive and origin/main at
  `291d5595c9cb2208a6b74206acbba35a883eb918`.
- Evidence requirement: full L1 DEP with redacted RED and GREEN artifacts.
- Verification plan: focused tests, relevant initialization/compiler/setup
  regressions, README/parity smoke, full local Green Gate, and strict DEP.

## Claim

- Agent: codex
- Claimed at: 2026-08-21T09:42:43Z
- Expires at: 2026-08-21T17:42:43Z
