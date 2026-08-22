# Reproduction

## Expected

The exact PR #498 Local Green must pass from a fresh, clean Reviewer checkout
when the tracked repository bytes and pinned Subject baseline inputs are
unchanged. Unrelated creation or deletion of a sibling entry in a shared
ancestor directory must not be classified as repository-input replacement.

## Actual

The one owner-authorized Reviewer run exited 2. The first Mission V5 identity
node failed during fixture setup at
`validate_mission_proof_value -> _repo_inputs` with the intentionally collapsed
`subject_authorization_v1_pinned.Denied`. The checkout remained clean and all
pinned verifier/manifest content hashes matched.

## Deterministic steps

1. At exact head `d355d32e442e388598b1ee502527839050d63559`, call the
   pinned `_repo_inputs` against the unchanged clean checkout. It passes with
   baseline `0dc10cfc4a429662`.
2. Wrap the final pinned verifier `_audit` only for diagnosis so it creates and
   removes one unrelated sibling directory directly under shared `/tmp` before
   executing the original audit.
3. Call the same `_repo_inputs` against the same unchanged checkout.
4. Observe `shared_tmp_sibling_change=DENIED`.

Exact command and output are captured in
`private/raw/terminal--ancestor-race-diagnostic` and its redacted derivative.

## Environment and preconditions

- Pull request: #498
- Base: `291d5595c9cb2208a6b74206acbba35a883eb918`
- Head: `d355d32e442e388598b1ee502527839050d63559`
- Reviewer checkout: fresh detached checkout directly below shared `/tmp`
- Runtime: pinned Local Green Python and `sddgov` environments
- Repository state after failure: tracked, staged, unstaged, and untracked clean
