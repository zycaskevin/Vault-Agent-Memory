# Decision Record: One owner-confirmed Development Mission for T-004–T-033

Date: 2026-08-13
Decision ID: `SD-TASK-AUTH-V4-MISSION`
Status: Approved for bridge implementation; mission inactive pending exact post-merge owner confirmation

## Context

The frozen Subject canonical baseline and versioned v1–v3 authorization roots
require a separate owner confirmation for each T-task. T-001 through T-003 are
terminal, content-addressed histories and cannot be rewritten or rebaselined
without invalidating their evidence. The owner selected option B: build a
larger but safer generic mission protocol that reduces future approval prompts.

## Later-owner-decision overlay

This direct owner decision is a versioned governance overlay. It supersedes
only the per-task human-confirmation step for the exact tasks T-004 through
T-033 on the exact canonical file hashes recorded in
`development-mission-v4.contract.json`. It does not claim that the older SDD
self-authorizes the change. All product/SBE semantics, exact scope, testing,
independent review, CI, operational and risk gates remain in force. T-001
through T-003 retain their original authority rules and immutable evidence.

The bridge itself creates no mission authority. After the bridge is merged and
read back from `origin/main`, the stateless runner emits one exact canonical
mission proposal. Only the owner’s later confirmation of that complete
proposal and receipt digest may publish the mission proof. Hashes prove byte
binding, not chat identity.

## Authority boundary

An active mission delegates routine L0/L1 engineering authority for exact
T-004–T-033 descriptors in local, development, test and staging environments.
It authorizes exact task proof derivation, implementation, tests, independent
review, commit, push, PR, required CI and eligible L0/L1 merge. It does not
authorize L2 product decisions, L3 or destructive operations, production
migration/deploy/release, private/live data, credentials, billing, provider
consoles, legal commitments or customer communication.

T-032 is `operational-blocked-only` until a separate Operational/L3 package is
approved. Without that package, T-033 may produce only the canonical
experimental closure. Stable closure remains outside the mission. Generic
task tooling must never complete T-033; the reviewed attester owns finalization.

## Scope, sequence and evidence

The scope registry contains all thirty immutable descriptors. Each descriptor
binds the canonical task header, exact read/write paths, actions, modes,
outputs, verification steps, risk and terminal policy. No wildcard or later
registration creates authority. Development remains serial because the frozen
progress contract permits at most one `IN_PROGRESS` task.

Each start binds the active mission, exact clean current-main descendant,
descriptor, ledger prefix, and exact mode/SHA snapshot of every declared read
input. The mission activation commit is the single-parent direct child of the
reviewed protocol release and adds only the exact owner-confirmed mission proof;
it is the only legal T-004 base. Every later task base is the preceding task's
exact final delivery commit. The T-032 BLOCKED path is one direct-child commit
that modifies only the ledger and becomes the T-033 base. No intervening,
merge-wrapper, add-then-revert, or otherwise out-of-scope commit may enter this
linear authority chain.

The builder then creates one single-parent preliminary commit directly on the
authorized task base; its complete delta is the proof, IN_PROGRESS ledger and
exact outputs. An independent source-review packet and a
separate hosted-CI readback packet must bind that exact commit, tree, workflow,
pull request identity, all fifteen immutable required check names and complete
base-to-head delta. Only then may the updater build
the durable review and atomically publish COMPLETED. The final delivery changes
only the review and ledger and must pass required CI again before merge. A red
preliminary check therefore never creates an irreversible terminal event.
Proof, review, revocation and ledger crash recovery must be byte-idempotent and
fail closed.

Historical replay reads every task's required inputs from its exact
implementation-base commit and its reviewed outputs from its exact preliminary
commit. It also binds each review's progress-before digest to the actual ledger
prefix immediately before that task's completion. It never compares an older
task's bytes with a later task's current
worktree. The unique final delivery is located in Git history by its exact
review and terminal-ledger blobs and by an exact two-path delta from the
preliminary head. It is the preliminary commit's single-parent direct child and
must be fast-forwarded without merge wrappers. Squash/rebase rewriting is
fail-closed and requires a
fresh delivery protocol rather than silently discarding the evidence chain.
The atomic progress writer may recover only its exact pending pathname, mode,
identity and candidate bytes; any mismatched pending or additional Git dirt is
denied without deleting anything. Before the first cleanup unlink, the updater
must prove the complete Git status, pending candidate and unreferenced artifact
identity; it re-audits the reduced exact status after each fsynced unlink.
Expiry or revocation aborts an exact unpublished start/completion by
validating and fsync-unlinking its pending candidate and unreferenced proof or
review before writing the authority BLOCKED event; these bytes are never
promoted after authority closes. An exact T-032 or authority BLOCKED ledger
that was already atomically replaced is a read-only `RECOVERED_COMMITTED`
result on retry and can never append a duplicate event. Optional revocation
bytes must equal the already validated owner packet before cleanup begins, then
remain retained and identity-audited across every cleanup step. An authority
BLOCKED worktree is accepted only on the task's exact direct-child
implementation head; its committed delivery is that head's single-parent child
and changes only progress, plus the exact revocation record for revocation.
Required CI validates the activation delivery
as soon as the mission proof exists and validates the T-032 progress-only
delivery as soon as the BLOCKED event exists, rather than deferring either
failure to the next task.

The T-031 reviewed source tree includes the immutable V4 workflow, decision,
runner, updater, validator, dispatcher, contract, proof schema, mission README,
active mission proof and scope registry. Generated progress, revocation,
review/evidence outputs and private material remain outside that source-tree
digest. T-033 independently replays the frozen T-001–T-003 prefix, the active
mission root and every ledger-referenced T-004+ proof/review chain before final
attestation; it does not infer authority from a caller-provided summary. The
attester calls `validate_t033_action` under the same stable progress lease.
That API first performs retained historical replay, then freshly requires an
unexpired and unrevoked mission immediately before and after the replay.
It is additive and never replaces the frozen canonical attestation/private
gate: the attester validates that gate on the same temporary candidate before
calling the V4 action API and before publishing either artifact or ledger.
Current required-CI replay remains historical and therefore does not turn a
valid expired or revoked history red.

## Expiry and revocation

The mission lasts exactly 7,776,000 seconds (90 days) from activation. Expiry
or an append-only owner-delivered revocation prevents new starts, rebases,
review publication and completion. An active task may only transition to the
fixed public-safe blocker. V4 supports one terminal epoch only: expiry or
revocation is irreversible. Resume requires a separately reviewed,
owner-approved successor protocol (V5 or later); an Agent cannot un-revoke or
recreate ACTIVE authority inside V4.

The revocation record is closed canonical JSON binding the exact mission ID,
epoch 1, owner principal and owner-channel confirmation reference, semantic
UTC effective time, fixed reason code and a content-derived `revocation_id`.
It also binds the exact previous ledger sequence and SHA-256, so the owner
revokes one byte-exact execution prefix rather than an ambiguous moving state.
Its hashes prove byte binding only; owner-channel authenticity remains the
human trust root.

Historical validation and action eligibility are separate. A structurally
valid expired or revoked history remains CI-green with mission state `EXPIRED`
or `REVOKED`, while every new start/review/completion action is denied. If a
task was active, revocation publication and the exact `MISSION_REVOKED` block
form one recoverable protocol operation; until the block is present the tree
fails closed.

## Delivery phases

1. Merge the inactive v4 bridge after P0=P1=0 independent review and green CI.
2. Generate the mission proposal from the exact merged `origin/main` commit.
3. Obtain one exact owner confirmation and atomically publish the mission proof.
4. Fast-forward the exact single-parent activation-proof commit after readback
   and CI; only then start T-004.

Every v1–v3 historical replay remains required. V4 CI and T-033 replay the
mission root plus all T-004+ proof/review chains. Any baseline, canonical task
header, registry, trust-root, risk boundary, expiry or revocation change reopens
the mission.
