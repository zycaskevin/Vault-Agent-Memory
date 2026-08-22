# Verification

## Green command and result

The historical focused-Green artifact records a 16-node PASS summary but did
not retain the exact pytest node list, so that count is supporting evidence and
not independently reproducible proof. The exact committed private-checkout
Local Green below is the authoritative proof for those changes. The historical
artifact also used “Changed core modules Ruff” too broadly: its actual scoped
Ruff PASS covered `vault/access_policy.py`, `vault/memory_provider.py`,
`vault/gateway_openapi.py`, and `tests/test_memory_change_envelope.py`; the
later public-reexport cleanup and exact all-changed-Python Ruff command are
captured in `DEP-VAM-002-PUBLIC-READ-SENSITIVITY`.

## Before/after evidence

Before: `max_sensitivity="typo"` returned an OK page containing a high row and
the Gateway encoded provider client errors as HTTP 200. After: all four
VAM-002 provider operations fail closed, list/read errors expose no data, and
the exact public client-error set is HTTP 400 with matching OpenAPI.

## Exact-head Builder proof

The single owner-authorized non-sandbox Builder Local Green passed at exact
committed head `f0a82733bc4854927f1877e31cac34fd1d415068`: governance doctor,
CI contract, README smoke, and release parity returned zero; 446 isolated
Subject nodes passed; and the remaining repository suite reported 2,962
passed, 10 skipped, and one already dispositioned warning. Post-run checks
confirmed the exact detached head, a clean worktree, 1,393 tracked physical
modes matching the Git index, and an empty Frozen Subject diff. Redacted proof:
`shareable/artifacts/terminal--exact-head-builder-local-green.txt`.

## Remaining limitations

The merge gate must now be rebound in an audit-only commit to the proof head.
Independent Reviewer re-review, `REV-VAM-002`, and hosted exact-head merge
verification remain separate protected-file gates.
