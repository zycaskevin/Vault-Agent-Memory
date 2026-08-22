# Regression Evidence

## Regression test added or strengthened

No new test was necessary. The existing hosted-equivalent
`scripts/module_size_gate.py` check is the exact regression contract and now
passes at the unchanged 1,231-line allowance.

## Related tests executed

- Module-size gate: PASS, 158 modules scanned.
- VAM-003 boundary and agent-setup tests: 58 passed.
- Stable-root Local Green: 446 identity nodes passed; remaining suite 2,935
  passed and 10 skipped.

## Unaffected paths sampled

The full Local Green sampled CLI, compiler, setup, gateway, provider, sync,
privacy, packaging, and frozen Subject contracts. No baseline or acceptance
check was changed.
