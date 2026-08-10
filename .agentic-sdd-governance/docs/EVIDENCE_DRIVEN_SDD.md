# Evidence-Driven SDD

## Design

SDD defines the intended behavior. Evidence records what the system actually did. The governance layer connects the two without turning every engineering step into a human approval request.

```text
Spec -> executable expectation -> observed failure -> evidence -> bounded fix -> proof
```

The debugging loop is:

```text
Red -> Evidence -> Fix -> Green -> Proof
```

- **Red**: reproduce the mismatch against an SDD reference or explicit expected behavior.
- **Evidence**: collect environment, console, network, runtime, test, and Git facts. Redact locally before sharing.
- **Fix**: state a falsifiable root-cause hypothesis and the smallest sufficient change. Preserve non-scope.
- **Green**: rerun the failing check and the relevant regression set.
- **Proof**: bind redacted artifacts, hashes, rollback, and limitations to the engineering record.

## Debug Evidence Package

A DEP is a local directory with two security zones:

```text
DEP-.../
├── summary.yaml                 # JSON-compatible YAML, schema-backed state
├── manifest.json                # provenance and hashes
├── reproduction.md
├── root-cause-hypothesis.md
├── fix-scope.md
├── regression-evidence.md
├── verification.md
├── rollback.md
├── redaction-report.json
├── private/raw/                 # never attach or export
└── shareable/artifacts/         # only after local redaction/review
```

`schemas/debug-evidence-package.schema.json` defines the machine contract. `evidence verify --strict` is the release gate. A DEP is not proof merely because the directory exists.

## Risk behavior

| Level | Evidence and debugging behavior | Human interaction |
|---|---|---|
| L0 | Reproduce, targeted evidence, bounded fix, targeted proof. A concise record is allowed by `solo-fast`. | None for approved scope. |
| L1 | Full DEP for cross-module, regression, data-flow, auth, or non-obvious failures; regression evidence is mandatory. | None for approved scope. |
| L2 | Collect evidence and test safe prototypes, then attach a Decision Package if the fix would change product behavior, acceptance criteria, privacy, cost, or public contract. | One bounded product decision. |
| L3 | Finish code, dry run, full redacted DEP, rollback drill, and exact operation plan. Do not access or publish raw production secrets/data. | One explicit approval for the concrete operation. |

Evidence changes what the Agent knows; it does not expand what the Agent is authorized to do.

## Loading rule

Development tasks load the Policy Kernel and project profile. Debugging tasks additionally load only:

1. the DEP contract;
2. the selected collector playbook;
3. the risk/evidence matrix;
4. the redaction gateway when artifacts may leave the machine.

Research, comparisons, roadmap, and every other collector playbook stay out of routine context.
