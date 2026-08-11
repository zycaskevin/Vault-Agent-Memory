# Reproduction

## Expected

The `stable` T-033 path independently selects the receipt key from a closed,
bounded, operator-private config, recomputes the specified HMAC in the
repository validator, and rejects any child PASS whose receipt MAC is invalid.
The child channel must remain memory-bounded during execution.

## Actual

The prior baseline specified only a `key_id` to key/config relationship. It did
not define config bytes, exact keys, key encoding, count, size, canonical form,
or an attester-owned comparison algorithm. Independent review demonstrated that
the candidate contained no HMAC comparison and its positive test could use an
arbitrary 64-hex MAC with a mocked child PASS. Child stdout/stderr used an
unbounded capture API.

## Deterministic steps

1. Read R-SD-016, design private-shadow receipt rules, T-001 progress-gate
   ownership, and T-033 stable closure rules at commit
   `d7e8803d659170ed8120594401c7e07114d22e60`.
2. Search the T-001 candidate progress validator for an attester-owned HMAC
   operation or constant-time comparison.
3. Exercise the synthetic stable positive with a child PASS and arbitrary
   lowercase 64-hex `receipt_hmac_sha256`.
4. Observe that the baseline provides no deterministic config parser with
   which an independent implementation could reject that control.

## Environment and preconditions

The observation is public-safe and uses only synthetic identifiers and keys.
No operator-private config, receipt, gate input, path, or secret was read. The
candidate remained isolated in its original dirty worktree; this repair occurs
in a clean docs-only worktree.
