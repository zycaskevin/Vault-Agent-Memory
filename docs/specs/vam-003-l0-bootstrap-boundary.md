# VAM-003 L0 Bootstrap Boundary SDD Slice

Status: owner-approved boundary transition; L1 compatibility implementation.

## Problem

Vault is governed memory infrastructure. Its current L0 directory name and
setup guidance still imply that Vault owns user identity/profile modeling. That
public contract conflicts with the frozen product boundary and invites new
identity, personality, relationship, life-phase, and human-model features into
the memory provider.

## Required outcome

- New `vault init` and `vault setup-agent` projects create `L0-bootstrap`.
- Existing content whose source path contains `L0-identity` still resolves to
  layer `L0` without migration.
- `L0` is documented as stable bootstrap/project framing, not a person model.
- Generated memory-agent guidance is limited to candidate curation, lifecycle
  reporting, and reversible archive/expiry suggestions.
- Active installation and governance sources state that identity/profile/care
  modeling belongs to an application above Vault.

## Acceptance criteria

1. Both new-project creation paths create `L0-bootstrap` and do not create
   `L0-identity`.
2. Layer inference accepts both `L0-bootstrap/**` and legacy
   `L0-identity/**` as `L0`.
3. Existing `L0-identity` directories and data are never renamed or deleted.
4. Generated English, Traditional Chinese, and Simplified Chinese maintenance
   guides contain no instruction to construct a profile, personality, care
   summary, relationship, life phase, or human model.
5. README variants, core concepts, memory governance, install/CLI guidance, and
   the agent manifest describe the neutral boundary and compatibility rule.
6. Legacy public identifiers remain accepted, but are described as
   compatibility labels rather than Vault-owned modeling domains.

## Guardrails

- Do not change database schema, stored layer values, or read permissions.
- Do not rename, move, or delete user files.
- Do not add Digital Life Identity dependencies or endpoints.
- Do not rewrite historical ADRs, announcements, plans, frozen Subject files,
  fixtures, or completed evidence.
- Do not silently remove legacy CLI flags, feature IDs, agent roles, presets,
  aliases, or memory-type strings.

## Rollback

Revert the canonical directory and guidance changes. Existing projects remain
compatible because the legacy directory is never mutated and the database
layer value remains `L0`.
