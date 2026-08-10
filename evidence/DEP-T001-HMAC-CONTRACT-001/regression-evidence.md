# Regression Evidence

## Regression test added or strengthened

The repaired T-001 contract assigns RED-first synthetic coverage to
`tests/test_subject_progress.py`: config shape/boundaries/canonicalization,
key selection, exact HMAC message, constant-time comparison, child-PASS with
invalid MAC, exact output caps, one-byte-over, timeout and process-group cleanup.
Those code tests intentionally remain unmodified until fresh T-001 authority.

## Related tests executed

The first docs-only Green pass executed:

```text
tests/test_subject_baseline.py
tests/test_subject_public_safety.py
tests/test_subject_authorization_bootstrap.py
tests/test_subject_authorization_runner.py
```

The first pass returned `320 passed, 2 skipped`. Independent review then found
two documentation-level traceability/RED-ownership conflicts. After adding
T-001 to R-SD-016, narrowing its test scope wording, assigning the actual
attester matrix to T-031, and making no-LF/concurrent-drain semantics explicit,
the same suite again returned `320 passed, 2 skipped`. The content-addressed
baseline validator returned PASS for final candidate baseline
`5dd83dd8b3d3696a` and full digest
`5dd83dd8b3d3696ae4f33ac863af87f4baf569ac1ca5ea11014ad5919ae740e0`.

The repository Local Green Gate then passed all five configured commands. Its
full pytest layer reported `2974 passed, 12 skipped`; compileall, README command
smoke, release parity and OpenClaw adapter verification all returned zero.

## Unaffected paths sampled

The existing receipt grammar, fixed HMAC domain, T-032 status pairing, T-033
child argv/error code allowlist and T-001 exact write allowlist are sampled for
byte/semantic drift during focused review. Independent re-review reported
P0=0/P1=0 and approved the docs-only repair.
