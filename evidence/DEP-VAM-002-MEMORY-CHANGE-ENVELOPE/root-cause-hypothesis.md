# Root Cause Hypothesis

## Hypothesis

Vault exposes search, bounded reads, timeline metadata, and audit metadata, but
its Memory Provider Interface has no provider-independent change envelope,
cursor listing, or revision-bound evidence operation.

## Supporting evidence

- The provider operation list contains create/search/get/update/delete,
  promotion, timeline, audit, and sync only.
- The Gateway exposes no `/memory/changes` route.
- The focused test cannot import the specified envelope module.
- Existing knowledge rows already contain the state and time fields required to
  derive a current snapshot without a migration.

## Contradicting evidence

Existing revision and audit tables provide related metadata, and the current
bounded-read path already enforces access policy. These are reusable building
blocks, but they do not expose the required incremental contract.

## Falsification test

Implement only an additive envelope/helper, provider operations, and read-only
Gateway route. If focused tests cannot pass without changing tables or bypassing
the existing access gate, the hypothesis is false and the design must reopen.

## Conclusion

Confirmed. The missing behavior is an interface/API gap, not a storage-schema
gap. The smallest sufficient fix is additive and migration-free.
