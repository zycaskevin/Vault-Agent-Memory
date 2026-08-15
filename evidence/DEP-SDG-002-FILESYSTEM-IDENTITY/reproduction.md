# Reproduction

## Expected

The SDG Local Green Gate and protected review are deterministic. Retained
regular files remain bound to exact bytes and full descriptor/path identity,
while an unrelated sibling create/delete in an ancestor directory does not
masquerade as replacement of the retained target.

## Actual

The final independent review for PR #473 observed two distinct failures in
unchanged Subject authorization integration tests. Both denied safely, but
neither represented target-byte or target-inode drift. A deterministic probe
then opened one unchanged regular file through the frozen legacy verifier,
created only an unrelated sibling, and observed `Denied` from the full
directory metadata audit.

## Deterministic reproduction

1. Open a synthetic regular file with the frozen verifier's descriptor-relative
   no-follow chain.
2. Read and retain its bytes and inode.
3. Create one unrelated sibling in the containing directory.
4. Confirm the target bytes and inode are unchanged.
5. Call the frozen `_audit` and observe `DENY`.

The redacted terminal artifact records only Boolean outcomes and no local path.

## Preconditions

- Base commit: `5587cc099d544e2f83f4db87dad3b0d882f52a10`.
- No private receipt, scope, credential, or production data is used.
- Frozen T-001 through T-003 bytes are read-only controls.

## Expected

TODO

## Actual

TODO

## Deterministic steps

TODO

## Environment and preconditions

TODO
