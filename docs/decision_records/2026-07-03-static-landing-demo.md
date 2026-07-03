# Static Landing Demo Page

Date: 2026-07-03

## Decision

Vault-for-LLM should have a static landing/demo page under `docs/landing/`.

The README pages now have clearer positioning, but a README is still a
developer-facing artifact. The landing page should be the first visual doorway
for non-expert Agent users and early adopters.

## Rationale

The product message is easier to understand as a short story than as a command
list:

1. an Agent finds a reusable lesson;
2. Vault receives it as a memory candidate;
3. gates check privacy, duplicates, quality, and evidence;
4. safe memory can enter the vault;
5. uncertain memory goes to the daily report;
6. another Agent reuses it with source;
7. outdated memory can be deprecated or rolled back.

This is the difference between Vault and a plain RAG database.

## Scope

The first version is deliberately small:

- `docs/landing/index.html`
- `docs/landing/README.md`
- no frontend build system;
- no external assets or analytics;
- smoke tests for core landing-page copy and links.

## Non-Goals

- This is not the final marketing website.
- This does not add cloud hosting.
- This does not replace the README or the docs.
- This does not claim remote sharing is conflict-free multi-master sync.

## Expected Outcome

A new visitor should understand within 30 seconds:

- Vault is about agent memory governance;
- ordinary users can start by copying one prompt to an Agent;
- daily reports keep memory automation reviewable;
- Obsidian, Supabase, Gateway, MCP, and CLI are adapters around the same
  governed memory lifecycle.
