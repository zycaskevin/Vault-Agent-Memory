# Mission V5 activation and the SDG exact-head gate

## Status

Accepted as an L1 compatibility repair under the already approved Mission V5
and team-standard governance decisions. This record does not activate a mission
or authorize T-004.

## Context

Mission V5 originally required its activation delivery to add only the mission
proof. After Agentic SDD Governance became mandatory, every ready Pull Request
also requires an exact-head merge gate and a distinct signed review receipt.
The proof-only commit passes Mission V5 but fails the stale SDG gate. Adding the
current gate records passes SDG but violates Mission V5's proof-only replay.

## Decision

1. Preserve the proof as the sole task-authority artifact.
2. Permit only a closed SDG-005 engineering-record set beside that proof:
   the Work Package, strict DEP, current gate, claim/event records, and one
   signed review receipt.
3. Require every activation topic commit to be linear from the exact protocol
   base, with exact add/modify actions and mode 0644. Deletion, rename, side
   merge, hidden add/delete, missing record, or extra path denies.
4. Require the final GitHub merge to use the exact protocol base as first parent
   and the reviewed topic as second parent, with byte-identical topic/merge
   trees. Later task descendants may replay that one immutable delivery anchor.
5. Bind the hotfix itself to a separate closed SDG-004 merge from exact base
   `3374ac372930ee6200d38c1f02289a0c8fa1eb84`.
6. After this repair is independently reviewed, merged, and read back, discard
   every earlier Mission V5 proposal/proof and generate a fresh owner-confirmed
   proposal from the new trust root.

## Preserved boundaries

- SDG records are review/evidence metadata, never task authority.
- The canonical five, old authorization protocols, terminal T-001 through T-003
  history, and sequence-6 ledger remain byte-identical.
- T-004 remains PENDING until the later fresh proof delivery is merged and
  current-main validation returns ACTIVE.
- T-032/T-033, private/live data, production, deployment, release, Billing,
  credentials, provider consoles, and L2/L3 operations remain unchanged.

## Verification

Temp-Git tests must prove the exact SDG-004 hotfix merge and the exact SDG-005
activation review chain, including proof-only, extra-path, deletion, rename,
mode, and merge-topology negative controls. Full Local Green, independent
protected review, hosted CI, and merge readback remain mandatory.
