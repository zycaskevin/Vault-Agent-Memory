# Quickstart Wizard

Date: 2026-07-03

## Decision

Add `vault quickstart` as the small first-run command for agent-assisted users.

`vault quickstart` should wrap the existing consumer setup path and ask only the
questions a new user needs before seeing a working daily memory loop:

1. setup language;
2. independent or shared memory vault;
3. optional Obsidian/Supabase connection;
4. daily report time.

`vault setup-agent` remains the advanced command for operators, maintainers, and
agents that need explicit feature flags, templates, permissions, remote readers,
validation packs, automation policies, or developer dependencies.

## Rationale

`setup-agent` has grown into a powerful installer and template generator. That
is useful for advanced agent fleets, but exposing the full flag surface during a
new user's first minute makes onboarding feel heavier than the product promise:

> answer a few setup questions, then read a short daily memory report.

A separate quickstart command lets the project keep the advanced installer
without making every new user understand it first.

## Behavior

- Interactive `vault quickstart` asks the small consumer questionnaire.
- `vault quickstart --non-interactive` uses conservative defaults:
  private vault, `core,mcp`, governed-auto memory, cron daily report, and no
  optional connectors unless requested.
- Obsidian and Supabase are still available, but behind one `--connections`
  choice instead of many setup-agent flags.
- The generated artifacts still come from the same setup engine, so registry,
  daily report, smoke test, safety guide, and automation schedule behavior stay
  consistent.

## Non-Goals

- This does not remove or deprecate `setup-agent`.
- This does not hide advanced setup-agent flags from operators.
- This does not make Supabase, semantic search, Headroom, or developer
  dependencies default.
- This does not turn Vault into a zero-setup hosted product.
