# Root Cause Hypothesis

## Hypothesis

The fixed denials are the repository's previously documented ancestor-directory
metadata race. The frozen verifier intentionally audits full path identities,
including directory size and modification time. `/tmp` is a shared filesystem
root, so unrelated membership activity can change ancestor metadata while the
protected bytes and inode remain unchanged. VAM-003 does not modify the frozen
runner, verifier, manifest, schema, or the failing tests.

## Supporting evidence

- The exact failed node passed immediately when executed alone.
- The exact node also passed with a newly created isolated `HOME`, `TMPDIR`,
  and pytest base temp matching the isolation runner's environment.
- The same 446-node suite passed on the preceding VAM-003 head.
- The only new source edit is removal of a blank line in
  `vault/agent_setup.py`.
- A controlled complete recheck failed at a different parameterized node with
  the same fail-closed proposal denial, falsifying a node-specific regression.
- Existing DEP-SDG-002 and DEP-SDG-008 evidence documents this exact
  ancestor-directory metadata race and prescribes a stable dedicated root.

## Contradicting evidence

The fixed-deny output intentionally hides the internal audit branch. The
classification therefore relies on the unchanged frozen bytes, different-node
reproduction, exact-node Green controls, and the repository's existing
deterministic evidence for this race.

## Falsification test

Move the candidate to a stable dedicated filesystem root outside shared OS
temporary directories and run the complete 446-node candidate isolation suite.
Failure there with unchanged target bytes would falsify the location-based
classification.

## Conclusion

Confirmed as the known availability race: the controlled `/tmp` recheck failed
on a different node, while both exact-node controls passed. Verification must
move to a stable dedicated root; no Subject source change is authorized.
