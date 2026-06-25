# Decision Record: Split Automation Report Helpers

Date: 2026-06-25

## Context

`vault/automation.py` had grown into the largest module in the package. It
contained the automation policy flow, lifecycle actions, learning feedback,
human-review surfaces, report file IO, and Markdown rendering in one file.

The module-size gate added in v0.6.110 prevents new oversized modules, but
existing large modules still need incremental cleanup. The first safe split
should avoid changing the automation state machine.

## Decision

Move automation report, handoff, and Markdown artifact helpers into
`vault.automation_reports`.

Keep the public automation API in `vault.automation` unchanged. CLI commands and
MCP tools still import and call the same public functions:

- `automation_run`
- `automation_cycle`
- `automation_report`
- `automation_activity`
- `automation_brief`
- `automation_review_summary`
- `automation_review_feedback`
- `automation_learning_health`
- `automation_fleet_health`
- `automation_inbox`
- `automation_handoff`

## Consequences

- `vault/automation.py` drops from 4747 lines to 3946 lines.
- `vault/automation_reports.py` is 834 lines and stays below the default
  1200-line new-module threshold.
- Report path validation, JSON writing, Markdown rendering, and report summary
  helpers are easier to review as one bounded surface.
- The automation lifecycle logic remains in `vault.automation`, reducing the
  chance of behavioral drift during this split.

## Follow-Ups

- Continue splitting `vault/automation.py` by lower-risk boundaries, such as
  learning-health helpers, inbox/review-card helpers, or action-ledger helpers.
- Keep lowering baselines after each split so large modules cannot quietly
  regrow.
- Preserve public CLI/MCP payload compatibility during every split.
