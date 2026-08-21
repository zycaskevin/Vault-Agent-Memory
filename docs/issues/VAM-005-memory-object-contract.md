# VAM-005: Freeze the canonical Memory Object contract

Status: in progress

## Problem

The boundary ADR, neutral bootstrap layer, and change-envelope API establish
where Vault stops, but Vault still lacks one machine-readable definition of the
generic object it stores. Without it, integrations can disagree about memory
kinds, confidence, provenance, lifecycle, and governance fields.

## Outcome

Add a stable `MemoryObject` adapter and publish the Vault Memory Layer contract:

- canonical kinds: `event`, `experience`, `decision`, `knowledge`,
  `interaction`;
- capabilities: storage, retrieval, provenance, confidence, lifecycle,
  governance;
- application-domain semantics remain opaque and outside Vault;
- existing rows, `memory_type`, `trust`, CLI, MCP, Gateway, and storage schema
  remain compatible.

## Acceptance criteria

- The five kinds and six capabilities have one machine-readable source.
- Unknown legacy memory types remain preserved as application metadata and map
  to generic `knowledge`; Vault does not reinterpret them.
- The provider can create candidate-first Memory Objects and return governed
  Memory Object views.
- `POST /memory/create` accepts additive `memory_kind` and `confidence` aliases.
- OpenAPI and provider status publish the same contract.
- The VAM-002 change envelope emits canonical kinds.
- No database migration or default authority switch occurs.

## Non-scope

- Application identity/personality/relationship/life-phase/human-model runtime.
- L0 directory or broad documentation cleanup already owned by VAM-003.
- Historical change replay already bounded by VAM-002.
- Package release/version bump, deployment, merge, or new repository creation.
