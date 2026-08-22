# Regression Evidence

## Regression test added or strengthened

No product test was weakened or rewritten for the base integration. The
existing VAM-002 contract tests are the regression oracle: stable revision
digests, policy-bound cursors, readable-only pagination, bounded evidence,
opaque provider-owned ids, single-snapshot reads, Gateway routing, and OpenAPI
metadata must pass unchanged on the new main base.

## Related tests executed

- `tests/test_memory_change_envelope.py` plus `tests/test_memory_provider.py`:
  10 passed.
- Four direct Gateway/OpenAPI VAM-002 nodes: 4 passed.
- `tests/test_vault_boundary_freeze.py`,
  `tests/test_subject_extraction_boundary_docs.py`, and
  `tests/test_agent_setup.py`: 73 passed.
- Ruff on the VAM-002 implementation and test modules: PASS.
- Module size gate: PASS, 159 modules scanned.
- Both historical VAM-002 DEPs: strict PASS.
- CI Cost Guard contract verification: PASS.
- Exact committed Builder Local Green at `bee2543d02e3ad2c3436e6246703f31c743bdf72`:
  PASS once; 446 isolated Subject nodes and 2958 repository tests passed, with
  10 expected skips and one existing warning.

## Unaffected paths sampled

- `git diff --check origin/main...HEAD`: PASS before evidence changes.
- Frozen `specs/subject-distillation`, `vault/subject_contracts.py`, and
  `tests/test_subject_contracts.py` diff against current main: empty.
- No VAM-001/VAM-003 receipt, evidence, or runtime file was edited by the
  VAM-002 branch integration.
- Post-Local-Green checkout remained detached at the exact tested head, clean,
  with all physical tracked modes matching the Git index.
