# Decision Record: Fleet Health As Startup Handoff Preface

Date: 2026-06-25

## Context

Vault automation already writes compact cycle and inbox handoffs for the next
agent. v0.6.104 added `vault automation fleet-health` so multi-agent installs
can see shared automation health across local agent registry entries,
learning-health, and update-distribution status.

If each agent only reads its own cycle or inbox handoff, the shared automation
state can still be missed at startup. If handoff switches to fleet health
instead, agents lose their task-specific next steps.

## Decision

`vault automation handoff` keeps the selected cycle/inbox handoff as the main
handoff content. When `reports/automation/fleet-health-latest.md` or `.json`
exists, handoff also attaches it as a startup health preface.

CLI output prints:

1. fleet health, if present;
2. the selected cycle/inbox handoff.

JSON and MCP output preserve the existing `content` contract for the selected
handoff and expose the shared health panel separately:

- `fleet_health_path`
- `fleet_health_content_type`
- `fleet_health_content`

If no cycle/inbox handoff exists, `source=auto` may fall back to
`fleet-health-latest.md` or `.json`.

## Safety Boundary

The preface only reads existing artifacts under `reports/automation`.
It does not generate reports, mutate memory, promote candidates, archive rows,
read transcript contents, read private memory, or expose raw candidate or raw
feedback reason content.

## Consequences

- Agents can start with shared multi-agent health before individual task
  instructions.
- Existing JSON/MCP consumers that read `content` as the selected handoff do not
  break.
- Dashboards and startup adapters can consume one handoff payload instead of
  discovering fleet health separately.
