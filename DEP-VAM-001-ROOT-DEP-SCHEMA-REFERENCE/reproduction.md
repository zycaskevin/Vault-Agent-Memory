# Reproduction

## Expected

Every root-level `DEP-VAM-001-*/summary.yaml` must resolve its `$schema`
relative reference to the repository's governed schema at
`.agentic-sdd-governance/schemas/debug-evidence-package.schema.json`.

## Actual

Two newly added summaries used `../../schemas/debug-evidence-package.schema.json`,
which resolves outside the repository to a nonexistent sibling `schemas/`
directory. Existing `sddgov evidence verify --strict` still returned PASS,
leaving the reference-integrity gap undetected.

## Deterministic steps

1. Enumerate every root-level `DEP-VAM-001-*/summary.yaml`.
2. Parse the JSON-compatible YAML and resolve `$schema` relative to the summary.
3. Require exact equality with the Governance Root schema path and require the
   resolved file to exist.
4. Run the new focused test and observe failure on
   `DEP-VAM-001-PRIVATE-CHECKOUT-REMOTE-REF/summary.yaml` before the fix.

## Environment and preconditions

- PR #498 base: `291d5595c9cb2208a6b74206acbba35a883eb918`
- Red head: `20a520a0883994717d0492447a587a2b7e094164`
- Branch: `codex/vam-001-subject-extraction-adr`
- Runtime: pinned Python 3.11 pytest environment
