# Automation Learning Module Split

Date: 2026-06-25

## Decision

Move automation feedback-learning helpers from `vault.automation` into `vault.automation_learning`.

The moved helpers cover:

- feedback aggregates to bounded learning policy
- learning-health status, cards, and top rules
- learned priority matching for review inbox items
- loading and writing `reports/automation/learning_policy.json`

## Context

`vault.automation` owns the daily memory automation loop: plan, run, cycle, inbox, brief, review summary, handoff, activity, learning health, fleet health, forgetting, cold-store, auto-promote preview, and safety reporting.

The learning-policy section is conceptually separate from mutation policy. It turns human review outcomes into ranking and review hints, but it must not authorize writes, auto-promotion, deletion, or privacy/access-policy bypass.

Keeping this logic in a focused module makes that boundary easier to inspect.

## Consequences

- `vault.automation` remains the orchestration module.
- `vault.automation_learning` owns learned ranking and learning-health helpers.
- Existing CLI/MCP behavior remains unchanged.
- Future learning changes should keep the same safety boundary: learning may rank or explain review cards, but mutation decisions stay policy-gated elsewhere.

## Verification

The release gate should verify:

- `vault automation eval` still writes the same bounded learning policy shape.
- `vault automation learning-health` still returns read-only health cards.
- `vault automation inbox` still applies learning multipliers without changing candidate status.
- `scripts/module_size_gate.py` reflects the lower `vault/automation.py` size after the split.
