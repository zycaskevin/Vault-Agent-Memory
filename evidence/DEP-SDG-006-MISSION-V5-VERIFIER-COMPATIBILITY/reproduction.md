# Reproduction

## Expected

The exact owner-confirmed Mission V5 proposal should pass its shared private
verifier and remain valid while unrelated processes create or remove siblings
in a shared macOS temporary ancestor. Exact receipt and scope files must remain
bound to their retained descriptors, bytes, modes, and single-link identities.

## Actual

The shared private verifier returned PASS and cleanup returned PASS, but the
third lifecycle audit denied after the release-closure replay. The target
receipt/scope descriptors and bytes were unchanged. Only external ancestor
membership metadata had changed.

## Deterministic steps

1. Derive the exact Mission V5 receipt and scope from a clean sequence-6 main.
2. Create the private lifecycle under an external directory.
3. Create and remove one unrelated sibling beside the owned lifecycle slot.
4. Run the Mission V5 post-verifier lifecycle audit.
5. Before the fix, the required Mission V5 compatibility helper is absent and
   the production path falls back to the legacy full-directory metadata audit.
6. Confirm the shared verifier and cleanup independently PASS.

## Environment and preconditions

- Base: `d2b62eea0f130df7e02aa230f3592e28fd118617`.
- Branch: `agent/sdg006-mission-v5-verifier-compatibility`.
- No private user data, credentials, live data, or production operation.
- The expired owner proposal is used only as public byte-binding evidence and
  is not reused for authorization.
