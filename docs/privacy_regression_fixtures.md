# Taiwan Privacy Regression Fixtures

This document explains the test-only privacy regression fixtures in
`tests/fixtures/taiwan_privacy_fixtures.json` and the corresponding tests in
`tests/test_taiwan_privacy_regression.py`. The fixtures prove that fake
Taiwan-looking personal data is detected by `vault.privacy.scan_privacy` and
cannot silently auto-promote through `vault.automation.automation_run`.

## Scope and Disclaimer

These fixtures are **test-only**. They:

- Use obviously synthetic values that do not correspond to any real person,
  patient, or customer.
- Are **not** medical, HIPAA, or PHI compliance.
- Lock a specific safety property: candidates whose content contains
  Taiwan-looking PII stay in `candidate` status (privacy gate `warn`) and are
  not eligible for `auto_promote_low_risk_candidates`.

Broader clinic privacy profiles require a separate design discussion (issue
#394). Adding new detection patterns or changing security defaults is out of
scope for these fixtures.

## What Is Detected

The built-in `_WARN_PATTERNS` in `vault/privacy.py` detect:

| Pattern | Example fake value | Finding type |
| --- | --- | --- |
| Taiwan mobile (domestic) | `0987-654-321` | `taiwan_mobile` |
| Taiwan mobile (international prefix) | `+886-0987-654-321` | `taiwan_mobile` |
| Taiwan ID-like (one letter + `1` or `2` + 8 digits) | `C234567890` | `taiwan_id` |
| Phone-like clinic record numbers | `02-2345-6789` | `phone` |

When any of these match, `scan_privacy` returns `status = "warn"`. The
candidate creation flow (`vault.memory.create_candidate`) keeps the row as a
`candidate` (does not reject), and the auto-promote decision
(`vault.automation_lifecycle._auto_promote_candidate_decision`) marks the
candidate as not eligible with reason `privacy_gate_not_pass:warn`.

## What Is NOT Detected (False-Negative Risk)

The built-in patterns do **not** detect:

- Non-phone-like clinic record numbers (for example, `CLINIC-REC-0001`).
- Project-specific patient, customer, or member identifiers.
- Region-specific identifiers not listed above.
- Real-world international Taiwan mobile format that drops the leading `0`
  after `+886` (for example, `+886-987-654-321`). The `taiwan_mobile` regex
  requires the `09` prefix even when `+886-` is present, so the genuine
  international form is only caught by the generic `phone` pattern, not by
  `taiwan_mobile`.

The fixture case `clinic_record_non_phone_like_limitation` locks the first gap
as a regression: if a future change accidentally starts matching such values,
the test will fail and force a discussion. The fixture case
`taiwan_mobile_international_prefix` locks the current behavior of the
`taiwan_mobile` regex (which requires `09` after `+886-`); its `note` field
documents the international-format limitation. Broader clinic privacy profiles
require a separate design discussion per issue #394.

## How to Extend Detection for Project-Specific Clinic Terms

Projects that need broader detection should configure their own terms rather
than changing the public template. Two supported mechanisms:

1. **`VAULT_PRIVACY_TERMS` environment variable** — newline-delimited custom
   terms loaded by `scripts/history_privacy_scan.py:_load_runtime_terms`.
2. **Project-local `entity_rules.yaml`** — extend
   `templates/entity_rules.yaml` with project-specific entries. The public
   template intentionally does not ship a maintainer's private customer,
   clinic, product, or operational vocabulary.

Both are project-local. Broader clinic privacy profiles require a separate
design discussion per issue #394.

## False-Positive Risk

- The `taiwan_id` pattern matches any `[A-Z][12]\d{8}` string (case
  insensitive). This includes synthetic IDs, fake test fixtures, and
  non-identifier strings that happen to fit the shape.
- The `taiwan_mobile` pattern matches `09XX-XXX-XXX` even in non-phone
  contexts.
- The `phone` pattern matches any 8+ digit run with separators.

These are warn-level (not fail) so reviewers can still see and reject the
candidate. A `warn` does not delete data; it only blocks auto-promotion.
