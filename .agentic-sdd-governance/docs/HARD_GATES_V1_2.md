# SDG v1.2 Hard Gates

This module closes three trust gaps without adding human approval to routine L0/L1 engineering.

## Fail-closed action classification

`sddgov autonomy evaluate` accepts only canonical categories. Every known action request must include an explicit `effects` object, using `{}` when no sensitive effect applies; omission, `null`, unknown flags, and false-valued flags fail closed. Unknown categories return `BLOCKED` with `requires_response: false`; the Agent must classify the action instead of asking the owner to approve uncertainty.

Production data deletion, irreversible migration, Secret change, permission-boundary change, real payment, and high-privilege Production operations always require L3. Routine categories may also declare sensitive effects. Any Production, destructive, irreversible, Secret, permission-boundary, payment, or high-privilege effect prevents an L0/L1 downgrade.

## Trusted L3 approval receipts

Caller-provided strings are not authority. `decision authorize-operation` and the separate consume command are removed. An L3 operation uses this sequence:

1. An external owner-controlled signer produces an Ed25519 envelope matching `schemas/operation-approval-receipt.schema.json`.
2. `.sddgov/trusted-approvers.json` is an auditable mirror only. Runtime authority comes from the same file at the immutable `SDDGOV_TRUSTED_BASE_REF`, or from an owner-controlled file outside the repository at `SDDGOV_TRUSTED_APPROVERS_FILE`. The candidate worktree copy is never an authority source.
3. The Agent runs `sddgov decision import-operation-approval signed-approval.json --path .`.
4. `sddgov autonomy evaluate request.json --path .` re-verifies the stored signed envelope and its digest under the decision lock, then verifies exact operation ID, signer, expiry, nonce, and unused state. Editing `.sddgov/decisions.json` cannot create or expand L3 authority.
5. The first `CONTINUE` atomically consumes the receipt. Reuse returns `ACTION REQUIRED`; concurrent evaluation permits at most one consumer.

Private signing keys must never enter the repository, chat, DEP, Agent workspace, or CI. Provisioning the trusted Base/out-of-band public-key source or using an owner signing key is an Operational/L3 boundary and is intentionally outside this repository's autonomous workflow.

Both approval and review signatures use these canonical signing bytes: serialize only the inner `receipt` or `review` object with `json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))`, then UTF-8 encode it. Padded Base64 is required: Ed25519 public keys are 44 characters and signatures are 88 characters.

## Executable Merge policy

`sddgov merge verify . --base-ref <exact-base>` executes the Merge contract:

- clean exact-HEAD worktree;
- executable change digest, immutable `base_sha`, and exact reviewed `head_sha`;
- repository Local Green Gate;
- strict Proof-phase DEP for L1-L3;
- zero Redaction blockers and no tracked `private/raw` Evidence;
- structured rollback record with `rollback_version`, explicit `target`, executable `command`, and `verify` fields;
- trusted-reviewer Ed25519 receipt when a protected path changed.

The GitHub Governance workflow fetches full history and runs this command for non-Draft PRs and `main` pushes. Configure it as a required check in repository rulesets; a workflow file alone cannot prevent an administrator from bypassing GitHub controls.

The Merge gate follows `schemas/merge-gate.schema.json`. `change_digest` excludes only `.sddgov/merge-gate.json` and `.sddgov/reviews/`. DEP and Rollback content remains inside the digest, so it cannot change after review. The recorded `head_sha` is the exact reviewed commit; current HEAD may descend from it only through commits whose paths are limited to those two audit-receipt locations.

Calculate `base_sha`, reviewed `head_sha`, and the executable digest with `sddgov merge digest . --base-ref <exact-base>`. Place them in the Merge gate, then calculate the review metadata binding with `sddgov merge gate-digest .`. Place both digest values in the independent Review receipt. Commit only the gate and receipt afterward, then run `sddgov merge verify`.

The Review receipt follows `schemas/protected-review-receipt.schema.json` and must live under `.sddgov/reviews/`. Its signer must be active in the reviewer store from the trusted base revision, the reviewer must differ from the Builder, and the receipt must approve both the exact executable `change_digest` and `gate_metadata_digest` while unexpired. The metadata digest is SHA-256 over canonical JSON containing `schema_version`, `base_sha`, `head_sha`, `risk_level`, `builder_id`, `change_digest`, `deps`, and `rollback_path`; changing the base, reviewed Head, risk, or Evidence requirements after review therefore invalidates the receipt. A Builder-authored `reviewer_id` string is not review authority.

Protected-path policy and an active Reviewer store are read from the trusted base revision first. An external store cannot override active base authority. Only when the initial rollout has no usable base-committed reviewer may bootstrap provide an owner-only, regular, non-linked public-key store outside the repository through `SDDGOV_TRUSTED_REVIEWERS_FILE`; candidate-controlled policy or keys are never accepted as authority. The bundled GitHub workflow materializes that external file with mode `0600` from the repository variable `SDDGOV_TRUSTED_REVIEWERS_JSON` in runner temporary storage. Configure this public-key-only variable and the required-check ruleset as a one-time Operational action before converting the bootstrap PR from Draft.

The independent Reviewer performs this bootstrap without asking the product owner for a key. On its separate host and clean checkout it runs `sddgov reviewer bootstrap`, registers the output of `sddgov reviewer export-trust` directly as `SDDGOV_TRUSTED_REVIEWERS_JSON`, completes its independent checks, and runs `sddgov reviewer sign`. The private key remains owner-only and Repo-external; the signed public receipt is the only key-related artifact committed. See the on-demand `references/independent-reviewer.md` module.

An empty `.sddgov/trusted-approvers.json` is not a Merge failure. It is a safe default that prevents future L3 operations until a separate owner-controlled L3 identity is deliberately provisioned.

Raw Evidence is checked across every commit in `base_ref..HEAD`, not only the final tree. Adding and later deleting `private/raw/` data still fails the gate because the sensitive bytes remain in Git history.

## Remaining trust boundary

SDG can fail closed on malformed or missing inputs, but it cannot make an Agent's operating-system account less privileged than it already is. Production credentials, owner private keys, GitHub branch protection, and deployment permission remain external controls.
