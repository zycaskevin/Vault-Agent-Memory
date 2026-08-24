# Fix Scope and 14-Item Disposition

## Product and contract changes

- Map PATCH/DELETE Memory API error payloads through the existing HTTP status
  mapper and document HTTP 400 in OpenAPI.
- Default scope/sensitivity only when a field is absent. A present empty or null
  stored label stays invalid and is denied by canonical policy, SQL selection,
  metadata, revision, bounded evidence, and the strict governance read guard.
- Add direct, provider, OpenAPI, and real HTTP regressions.

## Evidence and rollback corrections

1. **Valid, fixed:** PATCH/DELETE error status and OpenAPI 400.
2. **Valid, clarified:** focused tests are a subset of repository pytest, not
   additive counts.
3. **Outdated, dispositioned:** historical `f0a8273` proof records its then-next
   gate rebind; it must not overwrite the final successor gate.
4. **Valid, fail-closed disposition:** the impossible follow-up artifact
   chronology is preserved byte-for-byte but excluded as authoritative time
   evidence; later exact-head proofs supersede it.
5. **Valid, fixed:** replacement rollback runs successor tests before removing
   them and uses remaining baseline tests afterward.
6. **Valid, fixed:** compatibility rollback names exact commit `1a346913...`
   and an executable historical preparation, while successor rollback delegates
   to the authoritative PR procedure.
7. **Valid, fixed:** compatibility reproduction uses the pinned Python variable
   and exact selector.
8. **Valid, clarified:** the three Builder-path artifacts are ordered as
   interpreter RED, PATH-only Green/product RED, and overall proof.
9. **Outdated, verified:** current-head rollback already separates expected RED
   from rollback-safe Green; regression coverage preserves that separation.
10. **Valid, fixed:** absent versus present-empty/null governance semantics.
11. **Valid, fixed:** authoritative rollback resolves remote main with
    `ls-remote`, fetches the exact remote-tracking ref, and checks both.
12. **Valid, fixed:** independent-review reproduction provides one exact pinned
    command and identifies it as focused, not full-suite.
13. **Valid, clarified:** valid runtime/storage behavior was unchanged by the
    final docs repair, while missing identity intentionally maps to HTTP 400.
14. **Valid, fixed:** Builder PATH evidence defines one reusable exact value and
    contains no ellipsis placeholder.

## Explicit non-scope

No personality, identity, relationship, life-phase, or human-modeling logic.
No storage schema migration, live Hermes access, production-data mutation,
push, signing, trust change, merge, deployment, release, or shared install.
