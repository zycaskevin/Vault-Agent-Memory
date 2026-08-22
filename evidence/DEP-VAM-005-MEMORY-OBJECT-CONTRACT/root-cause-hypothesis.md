# Root Cause Hypothesis

## Hypothesis

Boundary documentation and change-feed semantics were split correctly, but no
bounded Work Package extracted the unique base Memory Object adapter and
machine-readable kind/capability contract from the broad VLT-001 draft.

## Supporting evidence

- The provider operation list lacks Memory Object create/search/get adapters.
- Memory API create ignores `memory_kind` and `confidence` aliases.
- Provider/OpenAPI contract payloads have no Memory Layer contract.
- VAM-002 currently emits the raw legacy `memory_type` as public `kind`.

## Contradicting evidence

Vault already stores compatible fields and VAM-002 already provides stable
cursor/revision/evidence semantics. Therefore the missing behavior can be
additive and migration-free.

## Falsification test

Add only the adapter, aliases, shared contract payload, and canonical-kind
mapping. If tests require schema changes, authority changes, or application
domain behavior, reopen the decision.

## Conclusion

Confirmed. This is a public contract gap with a small additive compatibility
implementation.
