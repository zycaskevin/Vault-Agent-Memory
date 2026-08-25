# Canonical 14-Item Disposition List

This is the single disposition list for the Final14 remediation.  It is the
source referenced by the DEP summary, regression evidence, and binding test.

1. HTTP PATCH/DELETE error status: fixed by the VAM-002 HTTP mapper change.
2. Focused test counts: clarified as separate, non-additive command results.
3. Historical gate successor reference: dispositioned with the full commit id.
4. Follow-up artifact chronology: historical artifact retained; a fresh
   current-head evidence package is required for chronological claims.
5. Replacement rollback: fixed with successor tests before removal.
6. Compatibility rollback: fixed with full historical commit and executable
   regression node ids.
7. Compatibility reproduction: fixed with pinned interpreter setup and a
   separate RED/Green sequence.
8. Builder-path evidence: fixed by direct executable resolution and one gate.
9. Current-head rollback: fixed by separating expected RED from Green checks.
10. Present empty/null labels: fixed as fail-closed behavior.
11. Sequential rollback: fixed with ignored-file and staged-diff checks.
12. Independent review reproduction: fixed with an explicit focused command.
13. Missing identity HTTP status: fixed as documented HTTP 400 behavior.
14. Current-head evidence provenance: fixed by the successor L1 package
    `DEP-VAM-002-CODERABBIT-2026-08-25-REMEDIATION`.
