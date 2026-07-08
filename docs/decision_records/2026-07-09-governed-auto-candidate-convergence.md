# Governed-auto candidate queue convergence

Date: 2026-07-09

## Context

`governed-auto` setup enabled scheduled automation with `--apply` and allowed
Dream to write candidate suggestions. The low-risk auto-promote policy was
intentionally narrow and promoted only sourced `session_capture/session_lesson`
candidates.

That left a gap: Dream metadata/dedup suggestions could be written into
`memory_candidates`, but no daily lifecycle step would close them. Renaming the
result to a candidate backlog is not acceptable. A governed automation loop
should process safe routine backlog and leave only real review work visible.

## Decision

Vault keeps Dream suggestions candidate-first and does not auto-promote them.
Instead, governed automation now has a separate convergence rule:

- `auto_close_low_risk_dream_noise`
- default enabled for `balanced` and `autonomous`, disabled for `conservative`
- handles only low-trust Dream metadata/dedup review notices
- rejects matching candidates and records review feedback
- never deletes candidate rows
- never writes or deletes active knowledge
- never closes private/high/restricted candidates

Dream candidate deduplication also treats previously reviewed rows as existing.
If a Dream suggestion with the same `source_ref` and `memory_type` was already
candidate, approved, rejected, blocked, or promoted, scheduled Dream runs do not
create another copy.

## Consequences

When only low-risk Dream metadata/dedup noise exists, a governed-auto apply run
can converge the pending candidate queue to zero without a user-facing review
alert. Freshness, convergence, orphan-repair, consolidation, sensitive, and
other real human-review candidates remain in the queue.

This is not a promotion path. Duplicate or low-trust Dream suggestions are
closed as rejected feedback, not silently added to active memory.
