# Regression Evidence

## Regression test added or strengthened

Added `test_vam001_root_dep_schema_references_resolve_exactly`. It enumerates
every VAM-001 root-level DEP summary, resolves `$schema` relative to its own
directory, requires exact equality with the Governance Root schema, and
requires that schema file to exist.

## Related tests executed

- Red: focused test failed on the first invalid selector.
- Green: focused test passed after correcting both Reviewer-found selectors and
  the new root-level DEP's own template selector.
- Strict verification remains required for all ten bound DEPs.

## Unaffected paths sampled

The schema content, artifact hashes, DEP semantic fields, workflow histories,
frozen Subject paths, Vault runtime, and public API were not changed.
