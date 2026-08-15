# Fix Scope

## Smallest sufficient change

Keep the original V5 bridge verification as a separately callable frozen
check. Add one new release boundary that pins the exact reviewed post-SDG merge
commit, its ordered parents, and tree. A future activation base is accepted
only when it is an exact two-parent merge whose first parent is that anchor,
whose second-parent topic is a linear chain changing only the closed hotfix
paths, and whose merge tree equals the reviewed topic tree.

## Files or components in scope

- `scripts/run_subject_development_mission_v5.py`: release ancestry and closed
  compatibility path validation only.
- `tests/test_subject_development_mission_v5.py`: genuine RED/GREEN and hostile
  ancestry/path/topology controls.
- `.github/workflows/ci.yml`: exact trust-root pin refresh.
- SDG-003 Work Package, strict DEP, protected merge-gate metadata, and one
  independent review receipt.
- A public decision record explaining that this is pre-activation
  compatibility, not task authority.

## Explicit non-scope

- No Mission proof publication and no T-004 start.
- No canonical five, v1-v4, T-001 through T-003 artifacts, sequence-6 ledger,
  product behavior, scope registry, or task descriptor change.
- No private/live data, credentials, production, deployment, release, Billing,
  provider-console action, destructive operation, or L2/L3 decision.
- No wildcard or generic descendant acceptance.

## Blast radius

The hotfix changes one inactive V5 trust-root script and its focused test, so it
requires a fresh post-merge owner-confirmed proposal. Existing proposals remain
invalid and no authority artifact is reused. Runtime product behavior is
untouched; the only new accepted state is the exact reviewed hotfix merge over
the exact pinned SDG anchor.

The candidate script is not an authority by itself. Delivery remains gated by
the external trusted-reviewer signature over the exact protected diff, hosted
Merge Gate and CI readback, exact Git merge topology, and a fresh owner
confirmation of the post-merge proposal. Candidate-controlled hashes alone
cannot activate Mission V5.
