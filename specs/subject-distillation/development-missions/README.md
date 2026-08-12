# Subject Development Missions

This directory stores public-safe, owner-confirmed Development Mission roots
and append-only revocation records. Mission proposals and private receipt/scope
material are never stored here. Absence of the exact v4 proof means the v4
bridge is inactive and T-004 remains fail-closed.

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

V4 has one irreversible epoch. A valid revocation or expiry keeps historical
CI replay valid but permanently disables new V4 actions. Resumption requires a
separately reviewed and owner-approved successor protocol; V4 cannot un-revoke
itself.
