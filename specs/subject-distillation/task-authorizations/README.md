# Subject task authorization proofs

This directory contains public-safe, immutable per-task authorization proofs
created by the additive `SD-TASK-AUTH-V2-BRIDGE`. Private receipt and scope
bytes are never stored here.

Each `T-NNN.json` proof is valid only for its exact base, baseline, progress
prefix, reviewed scope descriptor, and owner-confirmed proposal. A later task
must not edit an earlier proof.

For T-002, `T-002.review.json` is the byte-identical public-safe copy of the
independent completion-review packet. Its own SHA-256 is the only valid review
ID. The packet binds the exact six completion outputs, authorization proof,
verification command and result, distinct builder/reviewer principals, a
P0=0/P1=0 verdict, and the exact pre-completion progress sequence and digest.
The six outputs plus proof are immutable reviewed changes. The progress ledger
is separately reconstructed and semantically validated across completion; one
digest is never reused for both its `IN_PROGRESS` and `COMPLETED` bytes. It is
content-addressed audit evidence, not an authority
credential or cryptographic proof of reviewer identity; the exact owner proof,
mechanically derived Git scope, required CI, and merge gates remain separate.
Raw reviewer notes and private inputs do not belong here.
