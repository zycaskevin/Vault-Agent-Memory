# Reproduction

## Expected

The candidate-first HTTP facade test should prove that create/update/delete
requests do not add or mutate active knowledge rows. A fail-closed read of a
row with unknown stored scope and sensitivity should report the two exact
classification reasons without a redundant generic reason.

## Actual

The authorized exact-head Local Green completed all 446 identity-isolated
Subject nodes, then the repository suite returned 2 failed, 2965 passed, 10
skipped, and 1 warning. The HTTP test expected a fixed count of two even though
its setup now contained three active rows. The strict read-guard test received
`unknown_scope`, `unknown_sensitivity`, and the additional `unauthorized`.

## Deterministic steps

The focused read-guard node reproduces the exact extra reason code:

```text
python -m pytest -q tests/test_memory_foundation_compare.py::test_strict_guard_fails_closed_for_unknown_scope_and_sensitivity
```

The real HTTP node requires local loopback and was reproduced by the complete
repository-controlled Local Green captured in the attached RED evidence.

## Environment and preconditions

- candidate head: `7a64938bdc1e5aa483db013e4de4c8e78952fa20`
- Vault locked test interpreter with pytest `9.1.1`
- merged governance runtime `0.2.0-experimental.9`
- no Hermes, production database, trust, signing, push, or merge mutation
