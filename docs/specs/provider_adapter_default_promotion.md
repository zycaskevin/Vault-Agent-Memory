# Provider Adapter Default Promotion Criteria

Status: required release-readiness checklist before any provider-backed Memory
API adapter becomes the default Gateway result authority.

The provider-backed `/memory/search` and `/memory/{id}` adapters are preview
paths. Operators can opt in with `result_adapter=provider`, and they can compare
preview behavior with legacy Gateway behavior through:

```bash
vault memory-api parity-report \
  --agent-id AGENT \
  --search-query "representative query" \
  --read-range MEMORY_ID:1-20 \
  --json
```

That report is a promotion gate. It is not a promotion switch.

## Current Authority

Until every criterion below is met, default requests keep using the legacy Gateway policy-filtered result authority:

- `POST /memory/search` without `result_adapter=provider` uses the legacy
  Gateway search result path.
- `GET /memory/{id}` without `result_adapter=provider` uses the legacy bounded
  read path.
- Provider-backed adapters stay opt-in preview paths.
- No backend adapter may bypass candidate-first writes, review, promotion,
  audit, or access-policy semantics.

## Required Evidence Before Default Promotion

A provider-backed adapter can become the default result authority only after all
of these checks pass on the candidate release branch:

1. Representative parity probes pass.
   - Include public, shared, private, high-sensitivity, and denied-read cases.
   - Include at least one search probe and one bounded-read probe.
   - Search parity compares result ids, not raw content.
   - Read parity compares access decisions and bounded content hashes.

2. Security invariants hold.
   - The parity report does not return raw query text.
   - The parity report does not return raw memory content.
   - Provider adapters do not expose provider raw rows.
   - Provider adapters do not create hidden-result count side channels.
   - Remote or untrusted writes still create candidates, not active memory.

3. Rollback remains trivial.
   - `result_adapter=legacy` or the default request path must keep working.
   - Operators must be able to disable provider-backed default authority without
     migrating memory rows or deleting candidate queues.
   - The release note must state the rollback path in plain language.

4. Full release validation is green.
   - Full pytest passes.
   - Release parity passes against the intended public tag boundary.
   - Module-size gate passes.
   - Public documentation tests pass.
   - GitHub Actions for the pull request and main branch pass.

5. Documentation is updated.
   - `CHANGELOG.md` names the authority switch.
   - `docs/specs/vault_memory_api.md` names the default adapter authority.
   - Release notes explain that the provider path has moved from preview to
     default, or explicitly say that it has not.
   - Known limitations still describe backend adapters as implementations of
     the Vault Governance Contract, not separate product meanings.

## Release-Blocker Boundary

Provider parity mismatches should be triaged carefully. A mismatch blocks a
release only when it causes one of the strict release-blocker classes:

- installation failure;
- data corruption or irreversible active-memory mutation;
- security-misleading behavior, such as returning private memory that legacy
  policy would deny;
- a core read, write, review, promotion, or audit flow becoming unusable.

Other gaps can ship as known limitations or roadmap work when the preview path
is still opt-in and the legacy Gateway authority remains the default.

## What Does Not Count As Promotion

The following are useful but insufficient by themselves:

- adding a provider implementation;
- passing provider unit tests only;
- exposing provider metadata in Gateway health;
- adding OpenAPI schema entries;
- running a parity report with no probes;
- matching only public-memory searches;
- matching search ids but skipping denied-read and bounded-read checks.

## Operator Checklist

Before asking reviewers to approve default promotion, attach a short evidence
block like this to the pull request or release issue:

```text
Provider default promotion evidence
- representative parity report: passed
- probes: public/shared/private/high-sensitivity/denied, search, bounded read
- raw query text returned: no
- raw memory content returned: no
- remote writes remain candidate-first: yes
- rollback path documented: yes
- full pytest: passed
- release parity: passed
- module-size gate: passed
- CI: passed
```

If any line cannot be filled honestly, keep the provider adapter in preview.
