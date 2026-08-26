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
env PYTHONPATH=. "$VAULT_TEST_PYTHON" -m pytest -q \
  tests/test_memory_foundation_compare.py::test_strict_guard_fails_closed_for_unknown_scope_and_sensitivity
```

The real HTTP node is
`tests/test_gateway.py::test_gateway_memory_api_facade_is_candidate_first_and_metadata_only`.
It requires local loopback and belongs to the later Green proof, not this RED
reproduction. The attached RED evidence is from candidate
`7a64938bdc1e5aa483db013e4de4c8e78952fa20`; the separate Green proof uses
`1a346913563f5437b7815f655393f0eee5a0da52` after the compatibility fix.

## Environment and preconditions

- candidate head: `7a64938bdc1e5aa483db013e4de4c8e78952fa20`
- Vault locked test interpreter with pytest `9.1.1`
- merged governance runtime `0.2.0-experimental.9`
- no Hermes, production database, trust, signing, push, or merge mutation
