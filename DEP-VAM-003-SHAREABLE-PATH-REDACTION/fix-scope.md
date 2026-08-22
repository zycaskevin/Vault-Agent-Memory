# Fix Scope

## Smallest sufficient change

Replace one workstation path with a stable placeholder, update its manifest and
redaction provenance, and add a regression that verifies content and hashes.

## Files or components in scope

- `DEP-VAM-003-IDENTITY-ISOLATION-RECHECK/shareable/artifacts/exact-head-builder-local-green.txt`
- its `manifest.json` and `redaction-report.json`
- the exact-head artifact, manifest, redaction report, verification, and
  regression record in `DEP-VAM-003-INDEPENDENT-REVIEW-REMEDIATION`
- `DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY/rollback.md`
- `tests/test_vault_boundary_freeze.py`
- this DEP

## Explicit non-scope

- No runtime, storage, retrieval, API, or public documentation behavior.
- No change to the recorded exact head, command, result, or test counts.
- No private raw evidence is added to Git.

## Blast radius

Evidence-only and low. The source hash remains recorded while the owner-home
path is removed from every tracked shareable byte. The rollback preservation
list gains the new DEP without changing its staged behavioral allowlist. The
independent-review remediation proof now records the already-completed exact
committed/gate-bound Builder Local Green instead of a pending statement.
