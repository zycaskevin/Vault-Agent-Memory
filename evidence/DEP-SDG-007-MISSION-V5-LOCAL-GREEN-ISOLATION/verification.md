# Verification

## Green command and result

`pytest --collect-only` reports 75 unique Mission V5 nodes. The targeted
release/routing/original-failure slice passes 3/3. The complete isolation
harness reports:

```text
identity-isolated subject tests passed: 376 nodes
```

## Before/after evidence

RED: the SDG-005 pre-sign Local Green passed 301 identity nodes, then the shared
remainder reported 2993 passed, 12 skipped, and one Mission V5 failure.

GREEN: all prior 301 nodes plus all 75 Mission V5 nodes pass in fresh processes;
the remainder excludes only files already executed by the harness.

Builder Local Green PASS without retry: the isolation harness completed 376
nodes; the disjoint remainder completed 2920 passed and 12 skipped with one
pre-existing warning. Doctor, CI Cost Guard, README smoke, and release parity
also passed in the same governed run.

## Remaining limitations

Independent review, hosted CI, and merge readback remain required. After merge,
the old Mission proposal/proof is invalid and a fresh owner-confirmed proposal
is required.
