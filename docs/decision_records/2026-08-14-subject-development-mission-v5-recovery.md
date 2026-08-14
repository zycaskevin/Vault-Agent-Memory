# Decision Record: Mission V5 post-start CI recovery

Date: 2026-08-14
Decision ID: `SD-MISSION-V5-POST-START-CI-RECOVERY`
Status: Approved for inactive bridge implementation; authority remains inactive
until exact post-merge owner confirmation

## Context

Mission V4 was validly activated at commit
`03dcdabc873658cd7de24dfeeef8b85090cf2321`. Its first authorized T-004
preliminary branch proved a deterministic execution-routing defect: the
required Python CI jobs executed V4 control tests against the live sequence-7
ledger even though those tests were written for the immutable sequence-6
activation checkpoint. All three Python versions therefore failed before they
could accept any valid T-004 implementation. T-004 itself remained unmerged;
`origin/main` and the durable ledger stayed at sequence 6.

V4 declares its workflow, runner, updater, validator and dispatcher immutable
trust roots. It also makes trust-root drift a reopen condition. Neither an
Agent nor an ordinary T-task may edit those bytes and silently keep using the
old V4 proof. The owner therefore approved this successor-protocol bridge.

## Supersession boundary

V5 supersedes V4 only as the active task-authority and CI-routing layer for
T-004 through T-033. It preserves byte-for-byte:

- the canonical five Subject Distillation documents and baseline;
- the T-001 through T-003 proofs, reviews, ledger events, and deliveries;
- the complete inactive/active V4 bridge and activation history; and
- every product, privacy, evidence, scope, independent-review, hosted-CI,
  operational, L2, and L3 rule not explicitly replaced here.

The failed sequence-7 T-004 branch is evidence, not authority. V5 activation
starts from the exact sequence-6 ledger on merged main. No V4 task proof,
review, progress event, or output from that branch may be copied into V5.

## Phase-neutral CI

Required CI separates immutable history from current state:

1. V1 through V3 replays remain unchanged.
2. The complete V4 control suite and dispatcher run in a detached worktree at
   exact activation commit `03dcdabc873658cd7de24dfeeef8b85090cf2321`, with
   pinned V4 script, test, contract, proof, and ledger hashes.
3. The live checkout runs the old progress core plus the current V5 dispatcher.
4. V5 unit tests use synthetic or retained activation inputs; they never assume
   that the live ledger remains at sequence 6 after a task starts.

No test is skipped logically: historical assertions execute on their exact
historical state, while current validation executes against current bytes.
Unknown phases, altered checkpoints, hash drift, or an unvalidated current
ledger deny the required job.

## Authority and delivery

The inactive V5 bridge creates no task authority. After the bridge is merged
and read back from `origin/main`, the stateless V5 runner emits one canonical
proposal. Only a later owner confirmation of that exact proposal and receipt
may publish `MISSION-V5-T004-T033.json`. Its activation commit must be the
single-parent direct child of the reviewed V5 protocol release and add only
that proof.

GitHub may deliver that exact proof commit through an exact two-parent merge
whose first parent is the protocol release and whose second parent is the
single-parent proof commit. In that closed topology, the merge tree must differ
from the protocol release by only the byte-identical mode-0644 proof, and the
merge commit becomes the T-004 implementation base because it is the exact
current `origin/main`. A different parent order, intervening commit, extra path,
mode drift, or proof-byte drift is denied. If this delivery rule itself changes,
the old proof is removed as invalidated authority, CI returns to the sequence-6
inactive state, and a fresh post-merge owner-confirmed proposal is mandatory.

Once active, V5 retains the V4 serial task protocol: exact descriptor-bound
start proof, IN_PROGRESS preliminary commit, independent P0/P1=0 source review,
hosted required-CI readback, atomic completion, final two-path delivery, and
green final CI before fast-forward merge. T-032 remains operational-blocked
without separate L3 authority. T-033 remains experimental-only and attester
owned. Private data, credentials, production migration, deployment, release,
Billing, provider consoles, destructive operations, and product-policy changes
are not authorized.

V5 uses a new proof, contract, registry, revocation, runner, updater, validator,
and dispatcher namespace. It never overwrites or interprets the V4 mission
proof as V5 authority. Hashes prove byte binding; owner-channel authenticity
remains the human trust root.
