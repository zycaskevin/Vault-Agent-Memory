# Guardrails Dream Curator — Cron Manifest

Last updated: 2026-05-24 CST

## Purpose

Daily local-only Dream review report generation for Arthur/reviewer. This manifest is the source-controlled spec; live Hermes `~/.hermes/cron/jobs.json` is runtime state only and must not be treated as the source of truth.

## Job: Guardrails Dream Curator — Daily Review

- **Name:** `🧠 Guardrails Dream Curator — Daily Review`
- **Schedule:** `10 8 * * *`
- **Owning project:** `/home/zycas/Guardrails-knowledge`
- **Repo entrypoint:** `scripts/dream_daily_review.py`
- **Recommended Hermes mode:** `no_agent=True`
- **Delivery:** Feishu report group or origin, per Arthur preference
- **Runtime artifacts:** `${GUARDRAILS_RUNTIME_DIR:-$HERMES_HOME/runtime/guardrails}/dream-review/`
- **Latest pointer:** `dream-review/latest.json`

## Direct Smoke Command

```bash
cd /home/zycas/Guardrails-knowledge
PYTHONPATH=/home/zycas/Guardrails-knowledge \
python scripts/dream_daily_review.py \
  --project-dir /home/zycas/Guardrails-knowledge \
  --runtime-dir "${GUARDRAILS_RUNTIME_DIR:-$HOME/.hermes/runtime/guardrails}" \
  --date "$(date +%F)" \
  --limit 50
```

Expected behavior:

- If candidates exist: stdout is a short Feishu-ready message plus `MEDIA:<markdown_path>`.
- If zero candidates: stdout is empty, so `no_agent=True` cron stays silent.
- JSON/Markdown artifacts, prompt-only triage packet, count-only dashboard aggregate, append-only/idempotent trend history JSONL, and `latest.json` are written locally.

## Hermes Cron Create Template

Use only after direct smoke passes:

```python
cronjob(
    action="create",
    name="🧠 Guardrails Dream Curator — Daily Review",
    schedule="10 8 * * *",
    no_agent=True,
    script="guardrails_dream_daily_review.py",
    deliver="origin",
)
```

Recommended thin wrapper at `~/.hermes/scripts/guardrails_dream_daily_review.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT = Path("/home/zycas/Guardrails-knowledge")
RUNTIME = Path(os.environ.get("GUARDRAILS_RUNTIME_DIR", Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "runtime" / "guardrails"))
cmd = [
    sys.executable,
    str(PROJECT / "scripts" / "dream_daily_review.py"),
    "--project-dir",
    str(PROJECT),
    "--runtime-dir",
    str(RUNTIME),
    "--date",
    datetime.now().date().isoformat(),
    "--limit",
    "50",
]
env = os.environ.copy()
env["PYTHONPATH"] = str(PROJECT) + os.pathsep + env.get("PYTHONPATH", "")
raise SystemExit(subprocess.run(cmd, cwd=PROJECT, env=env).returncode)
```

## Safety Invariants

The job must remain report-only/local-only:

```text
report_only=true
auto_promote=false
formal_knowledge_written=false
raw_written=false
sync_invoked=false
```

Hard constraints:

- Do not call `dream promote`.
- Do not call local model APIs by default; DL-6 only writes prompt-only triage packets for optional manual/model consumption.
- Do not call Supabase sync or remote write APIs.
- Do not write artifacts under project `raw/` or `compiled/`.
- Keep trend history under runtime `dream-review/history/`; it is an artifact store, not a source-of-truth knowledge store.
- Do not include candidate `summary` or `content_draft` in stdout.
- Copyable commands in Markdown must shell-quote candidate IDs.
- Empty queue should be silent, not a recurring healthy-status notification.

## Verification Checklist

After changes to the script or report format:

```bash
cd /home/zycas/Guardrails-knowledge
python -m pytest tests/test_dream_daily_review_script.py -q
python -m pytest tests/test_dream_report.py -q
python -m pytest tests/test_dream_*.py -q
python -m compileall -q scripts/dream_daily_review.py guardrails_lite/dream_report.py tests/test_dream_daily_review_script.py
git diff --check -- scripts/dream_daily_review.py tests/test_dream_daily_review_script.py docs/guardrails_dream_cron_manifest.md
```

If a live Hermes cron is created later, immediately run:

1. direct wrapper smoke: `python ~/.hermes/scripts/guardrails_dream_daily_review.py`
2. `cronjob(action="run", job_id="...")`
3. confirm `last_status=ok`, `last_delivery_error` empty, and delivery target correct

## Restore Notes

On a new host:

1. Clone/restore `/home/zycas/Guardrails-knowledge`.
2. Ensure `guardrails.db` exists and Dream schema migrations have run.
3. Copy the thin wrapper into `~/.hermes/scripts/guardrails_dream_daily_review.py` and `chmod +x` it.
4. Direct-smoke the wrapper before creating/resuming the cron job.
5. Create the Hermes job from the template above.
