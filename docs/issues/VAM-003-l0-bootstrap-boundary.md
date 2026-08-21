# VAM-003: Clarify L0 Bootstrap boundary

## Evidence ID

`DEP-VAM-003-L0-BOOTSTRAP-BOUNDARY`

## Expected

New Vault projects use a neutral `L0-bootstrap` directory and generated setup
guidance describes memory curation and lifecycle maintenance, not identity,
personality, relationship, life-phase, care, or human-model construction.
Existing `L0-identity` source paths remain readable as a compatibility alias.

## Actual

Both project initialization paths create `L0-identity`; the compiler knows only
that L0 directory spelling; active README/core documentation calls L0
"Identity"; and opt-in setup guidance tells Profile agents to create user
profiles and care summaries.

## Reproduction

Run:

```bash
python -m pytest -q tests/test_vault_boundary_freeze.py
```

The initial tests fail because `L0-bootstrap` is not created and generated
guidance still teaches Vault-owned profile modeling.

## SDD reference

`docs/specs/vam-003-l0-bootstrap-boundary.md`

## Risk

L1. The owner-approved architecture direction is fixed, but this slice changes
new-project filesystem output and generated setup guidance. Compatibility and
full regression evidence are therefore required.

## Non-scope

- Deleting or renaming an existing `L0-identity` directory
- Changing the `L0` database value or L0-L3 ordering
- Removing legacy `memory_agents`, `personal-agent`, profile, or care CLI/API
  identifiers
- Subject Distillation frozen artifacts or Digital Life Identity runtime work
- VAM-002 Memory Change Envelope

## Verification plan

- Add focused RED tests for canonical creation, legacy read compatibility, and
  neutral generated guidance.
- Run initialization, compiler, setup-agent, README smoke, and full local
  governance gates.
- Strictly verify the redacted DEP before Draft PR delivery.
