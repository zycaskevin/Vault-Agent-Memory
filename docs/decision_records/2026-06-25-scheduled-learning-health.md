# Scheduled Learning Health

Date: 2026-06-25
Status: accepted

## Context

Vault automation now has a small feedback loop: review summaries collect human
decisions, review feedback records accept/reject/defer outcomes, automation eval
turns repeated outcomes into bounded ranking hints, and learning-health reports
whether the loop is cold, healthy, watching, or needs review.

The missing product step was installation. A user should not need to remember a
separate command just to know whether scheduled automation is learning well.

## Decision

`setup-agent` generated memory automation schedules now run:

1. the selected automation command (`cycle` by default, or `run`),
2. `vault automation inbox --write-handoff`, and
3. `vault automation learning-health --write-health`.

This writes `reports/automation/learning-health-latest.json` and `.md` after
each scheduled pass.

## Safety

- The learning-health step is read-only.
- It does not promote, delete, archive, or rewrite memory.
- It does not include raw feedback reasons or raw candidate content.
- It is a dashboard/startup artifact, not an authorization signal.
- No new core MCP tool is added; agents read the generated report or use the
  existing CLI/MCP startup surfaces.

## Consequences

Every installed automation schedule now leaves a short common health panel for
humans, dashboards, and the next agent session. This keeps the 5% human review
surface small while preserving auditability for the full reports.
