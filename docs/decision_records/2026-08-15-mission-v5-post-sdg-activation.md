# Mission V5 post-SDG activation compatibility

## Status

Accepted as an L1 implementation and CI compatibility repair. This record does
not activate Mission V5, publish a mission proof, or authorize T-004.

## Context

Mission V5 was intentionally inactive after its post-start CI recovery. Its
release preflight compared every path changed since the V4 activation with the
closed V5 bridge path set. The later reviewed consumer-policy bootstrap and
Agentic SDD Governance integration were valid governance-only descendants, but
their additional paths made the stateless proposal command deny on the exact
clean current main.

The old check could not distinguish those exact reviewed descendants from an
unauthorized intervening commit. Broadly accepting any descendant would weaken
the Subject authority boundary and is not allowed.

## Decision

Keep the original inactive V5 release check and add one later closed delivery
layer:

1. Pin the exact inactive V5 release and the exact reviewed policy-bootstrap
   and SDG merge commits, including their ordered parents, merge trees, signed
   SDG receipt, and Merge Gate bytes.
2. Treat the exact SDG merge as the sole implementation base for this
   compatibility Work Package.
3. Accept a proposal base only when current clean `HEAD` and `origin/main` are
   the same exact two-parent merge: first parent is the pinned SDG merge, second
   parent is a non-empty linear topic chain, and the merge tree byte-equals the
   topic tree.
4. Every topic commit may add or modify only the closed compatibility path set.
   Deletion, rename, path reversion, side merge, wrong mode, missing final path,
   extra path, different parent order, or a later descendant denies.
5. After this hotfix is merged and read back, regenerate a fresh Mission V5
   proposal on that exact main. All earlier proposal IDs, receipts, proofs, and
   T-004 progress attempts remain invalid.

## Preserved boundaries

- The canonical five, v1-v4, all T-001 through T-003 authority artifacts, and
  the sequence-6 progress ledger remain byte-identical.
- No wildcard or generic descendant gains authority.
- The repair changes no product semantics or task descriptor.
- Mission activation still requires the later exact owner confirmation and
  proof publication defined by V5.
- T-032, T-033, private/live data, credentials, production, deployment,
  release, Billing, provider consoles, destructive operations, and L2/L3
  decisions remain outside this Work Package.

## Verification

Genuine RED/GREEN tests cover the exact merge and reject unauthorized later
history. Focused Mission V5 tests, CI pins, strict public DEP, full Local Green,
independent protected review, hosted CI, and exact merge readback are required
before generating the new proposal.
