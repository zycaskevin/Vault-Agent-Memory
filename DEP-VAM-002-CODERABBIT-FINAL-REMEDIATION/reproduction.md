# Reproduction

## Expected

The rollback record must explicitly separate a documented RED reproduction
from rollback-safe checks that must exit zero. Remediation records must name the
two implementation defects separately from the six test/evidence/documentation
defects, describe the full knowledge-row snapshot oracle that is actually
implemented, and normalize both specification and decision Markdown before
phrase assertions.

## Actual

At exact head `36ff168a8c8ffffcc93d12107add2d5ecac0fbd1`, the rollback
record says every command must exit zero even though it also requires the known
RED reproduction after reverting the fix. One RED node did not exist before the
implementation commit, so that command cannot exit zero at the rollback
candidate. The scope and regression records are stale, and the normative
contract test uses raw `spec` and `decision` text for some assertions.

## Deterministic steps

Run the bounded static contract probe recorded in
`shareable/artifacts/terminal--final-review-red.txt`. It checks four independent
conditions:

1. truthful defect categories in the current-head remediation fix scope;
2. explicit expected-RED versus required-Green rollback semantics;
3. full column-projected snapshot wording in compatibility evidence; and
4. normalized specification and decision assertions in the normative test.

The exact probe at the public head exited `1` with all four checks reporting
`FAIL`.

## Environment and preconditions

- base: `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`
- head: `36ff168a8c8ffffcc93d12107add2d5ecac0fbd1`
- branch: `codex/vam-002-memory-change-envelope-ready`
- inputs are public repository text and AST only; no live Vault or Hermes data
  is read or changed
