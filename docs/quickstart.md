# 5-Minute Quickstart and FAQ

This page is the shortest safe path for a new user. It keeps the first run small
and leaves advanced setup under `vault setup-agent`.

## 5-Minute Quickstart

### 0:00 Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "vault-for-llm[mcp]"
```

### 1:00 Run The Small Wizard

```bash
vault quickstart
```

Answer only the first-run questions:

1. language;
2. independent or shared memory vault;
3. optional Obsidian/Supabase connection;
4. daily report time.

### 2:00 Run The Smoke Check

`quickstart` writes a local smoke script under `agent-install/`. Ask your agent
to run it, or run the script path shown in the setup output.

### 3:00 Read The Daily Report

```bash
vault daily-report
```

Use this report as the human review surface. Safe, low-risk memories may be kept
automatically; uncertain memories stay in the report.

### 5:00 Search One Phrase

```bash
vault search "installed smoke memory" --json
```

If the result is empty, run `vault compile --no-embed` and retry the search.

## FAQ

### 1. Do I need to learn every CLI command?

No. Start with `vault quickstart`, `vault daily-report`, and `vault search`.
Advanced commands remain available when you need them.

### 2. Does quickstart replace setup-agent?

No. `vault quickstart` is the beginner entrypoint. `vault setup-agent` remains
the advanced installer for explicit templates, permissions, remote readers,
validation packs, automation flags, and developer dependencies.

### 3. Can Vault work without cloud services?

Yes. Core memory uses local SQLite and Markdown. Supabase, Gateway, Obsidian,
and semantic providers are optional integrations.

### 4. Does Gateway write active knowledge?

No. Gateway writes create review candidates first. Active knowledge still goes
through review and promotion gates.

### 5. Where do uncertain memories go?

They stay in the daily report for review. Strategy, private, sensitive,
conflicting, or low-trust memories should not enter active memory automatically.

### 6. Should I connect Obsidian on day one?

Only if you already use Obsidian. You can start with the local daily report and
connect Obsidian later.

### 7. Is Supabase required?

No. Supabase is optional sharing infrastructure for hosted readers or remote
candidate workflows.

### 8. What should I do if Vault says `vault.db` is missing?

Run:

```bash
vault init --project-dir <project>
```

Or pass the correct project directory with `--project-dir <project>`.

### 9. How long can search queries be?

Keep search queries under 1000 characters. If you have a long source text, add
or remember it first, then search for a short phrase or concrete question.

### 10. How do I expose Gateway safely?

Keep token auth enabled, use TLS or a trusted reverse proxy for cross-host
access, restrict firewall or IP access, and review `reports/gateway/audit.jsonl`
during rollout.

## More

- `vault guide --intent install`
- `vault guide --intent faq`
- `docs/agent_install.md`
- `docs/agent_integrations.md`
