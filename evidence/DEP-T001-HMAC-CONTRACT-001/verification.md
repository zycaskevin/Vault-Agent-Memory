# Verification

## Green command and result

```bash
python3 scripts/validate_subject_baseline.py \
  --manifest specs/subject-distillation/baseline-manifest.json --json
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider \
  tests/test_subject_baseline.py \
  tests/test_subject_public_safety.py \
  tests/test_subject_authorization_bootstrap.py \
  tests/test_subject_authorization_runner.py
git diff --check
```

Results after the independent-review remediation: final candidate baseline
`5dd83dd8b3d3696a` validator PASS; `320 passed, 2 skipped`; diff-check PASS.
Fresh bounded independent re-review returned P0=0/P1=0 and APPROVE. Agentic SDD
Governance `ci verify` returned `ok: true`. The complete Local Green Gate
returned `ok: true`: full pytest `2974 passed, 12 skipped`, compileall PASS,
README command smoke PASS, release parity PASS and OpenClaw adapter smoke PASS.

## Before/after evidence

Before: stable HMAC config and child resource behavior were implementation
defined. After: three canonical documents define one closed grammar,
attester-owned HMAC verification, RED ownership, and bounded child lifecycle;
the baseline manifest binds those exact bytes. The requirement/task matrix now
mechanically includes T-001 under R-SD-016, while T-031 owns the distinct actual
attester lifecycle matrix.

## Remaining limitations

This docs-only repair does not implement the validator. It deliberately
invalidates the old exact proposal; T-001 implementation resumes only after a
new clean-base proposal is separately confirmed and verified. Two non-blocking
review notes remain for implementation review: explicitly exercise hard-link
and non-regular config fixtures in the already-required complete T-031 boundary,
and retain final DEP timing metadata. No hosted CI, push, PR, deployment,
release, production data or operator-private input was used.
