# Subject Development Missions

This directory stores public-safe, owner-confirmed Development Mission roots
and append-only revocation records. Mission proposals and private receipt/scope
material are never stored here. V4 was activated at the immutable sequence-6
checkpoint, but its first post-start required-CI run exposed a phase-sensitive
test-routing defect. V5 therefore supersedes V4 only for T-004 through T-033
task authority and CI routing. Absence of the exact V5 proof means the V5
bridge is inactive and T-004 remains fail-closed; the V4 proof remains
historical evidence and is never interpreted as V5 authority.

The activated execution history is deliberately linear: the mission-proof
commit is the direct child of the reviewed protocol release, T-004 starts from
that commit, every preliminary and final delivery is a single-parent direct
child, and each next task starts from the preceding final commit. T-032's
BLOCKED-only delivery may modify only the progress ledger before T-033. This
prevents unregistered commits and add-then-revert history from acquiring mission
authority. Exact progress pending bytes may be recovered by the atomic writer;
they never grant scope and any mismatch denies. Once expiry or revocation
closes authority, an exact unpublished start/completion candidate is securely
discarded with its unreferenced proof/review before the ledger is blocked; it
cannot be completed later. Cleanup begins only after a complete exact Git-status
and retained-identity preflight; extra dirt denies with zero deletion. A retry
that reads back the exact already-published T-032 or authority BLOCKED event
returns `RECOVERED_COMMITTED` without appending another event. Revocation bytes
must byte-match the validated owner packet before they remain
descriptor-retained throughout cleanup. Authority BLOCKED delivery is
valid only as a progress-only direct child of the exact implementation head,
with the exact revocation record as the sole additional path when revoked.
Current CI validates activation and T-032 BLOCKED
delivery immediately in their own phases.

V4 and V5 each have one irreversible epoch. A valid revocation or expiry keeps
historical CI replay valid but permanently disables new actions for that
protocol. Resumption requires a separately reviewed and owner-approved
successor protocol; neither protocol can un-revoke itself. V5 independently
replays the exact V4 activation proof, immutable V4 roots and sequence-6 ledger
prefix before it can activate or authorize any task.
