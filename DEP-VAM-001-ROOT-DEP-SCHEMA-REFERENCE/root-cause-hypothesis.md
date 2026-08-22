# Root Cause Hypothesis

## Hypothesis

`sddgov evidence init` emitted a template path intended for a DEP nested under
another directory, while these DEPs live at repository root. The Builder did
not normalize the relative path, and strict DEP verification validates the
document shape but not `$schema` path resolution.

## Supporting evidence

- Seven existing root-level VAM-001 DEPs use the correct
  `../.agentic-sdd-governance/schemas/...` form.
- Only the two DEPs created in the private-checkout remediation use the
  incorrect `../../schemas/...` form.
- Path resolution deterministically points outside the repository.
- Nine strict DEP checks passed despite the invalid references.

## Contradicting evidence

No contrary evidence. The schema content itself is present and unchanged; only
the two relative selectors are incorrect.

## Falsification test

Change both selectors to the canonical root-level form and rerun the exhaustive
root DEP reference test. The hypothesis is falsified if any selector still
resolves elsewhere or the canonical schema does not exist.

## Conclusion

Confirmed relative-path and verifier-coverage defect. Fix the two selectors and
retain the exhaustive repository test as the regression gate.
