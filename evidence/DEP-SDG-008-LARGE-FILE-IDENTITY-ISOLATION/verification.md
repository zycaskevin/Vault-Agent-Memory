# Verification

## Green command and result

`pytest --collect-only` reports 53 unique baseline-control nodes. The complete
file passes 53/53. The SDG-008 release/routing slice passes, and the closed
isolation harness reports:

```text
identity-isolated subject tests passed: 430 nodes
```

## Before/after evidence

RED: SDG-005 v2 pre-sign Local Green passed 376 identity nodes, then the shared
remainder reported 2919 passed, 12 skipped, and one large-file boundary failure.

GREEN: all prior 377 nodes plus all 53 baseline-control nodes pass in fresh
processes; the remainder excludes only files already executed by the harness.
The T-001 validator hash remains `86707e63e5ab6aebb91440eec5b22a13dd98618237a799c1b82409067d1efcd7`
and its baseline test hash remains
`77e11389e9ffdc205a26d7d835577476e9c2b6ba609b0af8bbc10508ae1e94b4`.

## Remaining limitations

Full Local Green, independent review, hosted CI, and merge readback remain
required. After merge, the old Mission proposal/proof is invalid and a fresh
owner-confirmed proposal is required.
