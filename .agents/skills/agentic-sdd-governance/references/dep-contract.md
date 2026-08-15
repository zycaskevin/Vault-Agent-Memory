# DEP Contract

The canonical machine document is `summary.yaml`, encoded as JSON-compatible YAML so the stdlib CLI can parse it without an optional YAML dependency. It conforms to `schemas/debug-evidence-package.schema.json` under the resolved Governance Root.

Security zones:

- `private/raw`: original collector output; local only; never attach.
- `shareable/artifacts`: locally redacted text or manually reviewed derivative.

Required proof documents:

- `reproduction.md`
- `root-cause-hypothesis.md`
- `fix-scope.md`
- `regression-evidence.md`
- `verification.md`
- `rollback.md`
- `redaction-report.json`
- `manifest.json`

Run:

```bash
evidence init --issue ISSUE-123 --risk L1 --sdd CAP-03
evidence collect <DEP> --collector terminal --input failure.log
evidence redact <DEP>
evidence verify <DEP> --strict
evidence attach <DEP> --target pr
```

Blocked binary artifacts require a human-reviewed safe derivative. Do not mark them shareable by editing the report.

Attachment eligibility is destination-specific and fail closed:

- L0/L1 requires a strict-verified DEP in an approved package state.
- L2 additionally requires the approved Decision Package for the behavior or authority change.
- L3 additionally requires explicit approval for the concrete operation and destination.
- Sensitive L2/L3 evidence stays local unless the engineering record names an authorized destination and the minimum disclosure required there.

Verification changes evidence confidence; it never grants a destination or operation by itself.
