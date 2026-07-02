# Obsidian Watch Mode

Date: 2026-07-02

## Decision

Vault supports a conservative Obsidian watch mode:

```bash
vault import obsidian --vault /path/to/ObsidianVault --watch --watch-interval 5
```

The watch loop repeatedly runs the existing incremental Obsidian import. It
uses the same manifest, folder rules, privacy gate, conflict detection, and
optional compile path as the normal one-shot import.

For agent-run automation, JSON watch mode must be bounded:

```bash
vault import obsidian --vault /path/to/ObsidianVault --watch --watch-iterations 2 --json
```

This prevents agents, CI, n8n, or other non-interactive runners from hanging on
an infinite JSON stream.

## Why

Obsidian should be usable as the human-facing Vault interface. A user should be
able to edit a note and have Vault pick up the change without remembering a
manual import command every time.

The first version deliberately uses polling instead of file-system watchers.
Polling is simpler, cross-platform, dependency-free, and consistent with
Vault's local-first architecture.

## Scope

Watch mode is still one-way from Obsidian notes into Vault raw notes. It does
not yet implement full two-way live mirroring, visual conflict resolution, or
automatic export of new active Vault knowledge back into user-authored folders.

Follow-up work:

- Optional generated LaunchAgent / systemd / n8n templates that run watch mode.
- Conflict review notes written back into `00-Vault-Knowledge/_Inbox/`.
- Full two-way mirror workflow with explicit conflict UI.
