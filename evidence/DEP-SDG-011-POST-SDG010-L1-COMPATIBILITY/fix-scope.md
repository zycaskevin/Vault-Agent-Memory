# Fix Scope

## Smallest sufficient change

Add one reusable closed two-parent compatibility validator. Use it to validate
the exact SDG-010 delivery, including fixed parents, topic, tree, full linear
history, final path actions, modes, and trusted gate/receipt hashes. Then use it
to require one future SDG-011 merge from exact `efa43a4`, closed to the
enumerated SDG-011 source, tests, WP, DEP, CI, gate, claim/event, corrected
SDG-010 rollback, and independent-review receipt paths.

Correct the merged SDG-010 rollback record to query exact PR #484, actual v4
head branch, exact merge commit, exact parent order, and topic-tree equality.

## In scope

- `scripts/run_subject_development_mission_v5.py` compatibility chain.
- Genuine merge-topology/path/action/mode/gate/receipt regression tests.
- Static CI pins and rollback-query proof.
- Exact correction of the current SDG-010 rollback record.
- SDG-011 WP, strict DEP, governance claim/event/gate, independent receipt,
  hosted CI, and merge readback records.

## Explicit non-scope

No change to Mission activation delivery, proposal/proof schema, exact owner
confirmation, task authority, task progress, updater, dispatcher, identity
collection, canonical history, user-visible product behavior, private/live
data, production, deployment, release, billing, credentials, L2, or L3.

## Blast radius

Limited to whether a fresh Mission V5 proposal recognizes a reviewed protocol
release and whether the documented SDG-010 rollback can resolve its exact
merge. All downstream authority predicates remain unchanged and fail closed.
