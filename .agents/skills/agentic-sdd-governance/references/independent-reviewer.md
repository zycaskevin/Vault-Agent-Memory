# Independent Reviewer Workflow

Load this module only when the current Agent is explicitly assigned an independent protected-file Review. The Reviewer must use a fresh, clean checkout on a host or identity separate from the Builder. Unknown untracked files are a reason to use a fresh clone, never a reason to delete or ignore them.

## Trust bootstrap

For the first Review, the Reviewer creates and controls its own Ed25519 identity outside the repository:

```bash
sddgov reviewer bootstrap \
  --path /path/to/repo \
  --reviewer-id gb10-hermes-reviewer \
  --private-key /owner-controlled/sddgov/gb10-hermes-reviewer.pem \
  --trust-file /owner-controlled/sddgov/trusted-reviewers.json
```

The command creates both files without overwriting existing state, stores them with owner-only permissions, and never prints private-key bytes. The trust file contains public keys only. Register that public JSON directly as the GitHub repository variable `SDDGOV_TRUSTED_REVIEWERS_JSON`:

```bash
TRUST_JSON="$(sddgov reviewer export-trust \
  --path /path/to/repo \
  --trust-file /owner-controlled/sddgov/trusted-reviewers.json)"
gh variable set SDDGOV_TRUSTED_REVIEWERS_JSON \
  --repo OWNER/REPOSITORY \
  --body "$TRUST_JSON"
```

This is a bounded Operational bootstrap. Do not ask the product owner to generate, copy, paste, or inspect a key. Never place the private key in Repo, Chat, CI, DEP, logs, or shell history.

An empty trusted-approvers store is not a Merge blocker. It intentionally blocks future L3 operations until an owner-controlled L3 signer is provisioned for a concrete need.

## Review and sign

Independently obtain the Pull Request's exact Base and Head from GitHub. Review the diff and required Evidence, then run the repository's Local Green, full tests, `sddgov validate`, `sddgov ci verify`, and strict DEP verification. Do not sign when any finding remains open.

After a PASS verdict, sign the exact Merge gate:

```bash
sddgov reviewer sign \
  --path /path/to/repo \
  --reviewer-id gb10-hermes-reviewer \
  --private-key /owner-controlled/sddgov/gb10-hermes-reviewer.pem \
  --trust-file /owner-controlled/sddgov/trusted-reviewers.json \
  --review-id REV-WORK-PACKAGE-001 \
  --base-ref EXACT_PR_BASE_SHA \
  --output /path/to/repo/.sddgov/reviews/REV-WORK-PACKAGE-001.json \
  --approve-exact-change
```

The signing command fails closed on a dirty worktree, Repo-local or broadly readable private key, Builder/Reviewer identity collision, public/private-key mismatch, wrong Base, changed digest, non-audit post-review commit, wrong output path, or expired validity. Commit and Push only the public Review receipt. The Builder then reruns `sddgov merge verify`; no human checksum step is involved.
