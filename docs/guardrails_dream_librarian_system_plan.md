# Guardrails Dream & Librarian System Implementation Plan

> **For Hermes:** Use `subagent-driven-development` to implement this plan task-by-task. Keep every first production slice report-only until Arthur explicitly approves promotion/merge automation.

**Date:** 2026-05-23
**Owner:** Nancy / Guardrails maintainers
**Goal:** Build a review-gated knowledge governance system that (1) collects candidate knowledge into a dream queue before formal write, and (2) periodically audits the existing encyclopedia for duplicates, stale entries, contradictions, low convergence, and provenance gaps.

**Architecture:** Split the system into two cooperating roles: **Dream Curator** controls the write入口 (`session/agent/cron → candidate → review → promote`), and **Knowledge Librarian** controls the existing庫存 (`formal knowledge → duplicate/freshness/convergence/conflict/provenance review`). Local SQLite plus curated `raw/` remain the source of truth; Supabase/Dashboard are sync or observability targets only.

**Tech Stack:** Guardrails Lite SQLite (`guardrails.db`), Markdown `raw/` and `compiled/`, Python CLI modules under `guardrails_lite/`, Hermes cron, Feishu review delivery, existing B1/B5/B6/B7 documents, MCP read/search tools, optional Dashboard count-only aggregate.

---

## 0. 白話結論

Guardrails 不能再靠「每次覺得值得記就直接寫」來長期運作。資料量已經大到需要治理：

- **Dream Curator**：每天整理「白天哪些東西值得寫入」，避免垃圾進百科。
- **Knowledge Librarian**：每週/月整理「已經寫進去的東西是否重複、過時、矛盾、不完整」，避免百科老化。

第一版只做 **report-only**：列出建議，不自動刪、不自動合併、不自動 promote、不自動覆蓋遠端。

---

## 1. 現況與問題

### 1.1 已有基礎

已存在的設計與工具：

- `docs/session_writeback_governance.md` — B1：session → candidate → classification → privacy → dedupe → draft → review → promote。
- `docs/session_capture_draft_queue_design.md` — B5：draft queue 概念。
- `docs/privacy_scanner_design.md` — B6：privacy scanner。
- `docs/multi_agent_convergence_workflow.md` — B7：多 agent 寫入與收斂。
- `guardrails b7 report --output <json>` — 已有 report-only duplicate / freshness / convergence / provenance signal 雛形。
- `~/.hermes/scripts/conversation_backwrite_scan.py` — 目前能掃 session 並輸出候選摘要，但不是正式 candidate queue。
- `guardrails_convergence_check.py`、`guardrails_freshness_check.py`、`guardrails_maintenance_daily.py` — 已有部分庫存健康檢查。

### 1.2 目前缺口

1. **入口缺口**：agent 發現知識後，仍容易直接寫正式百科，沒有一個穩定的 Dream Inbox。
2. **候選缺口**：候選資料缺少統一 schema、狀態機、來源引用、review evidence、privacy/dedupe 結果。
3. **整理缺口**：每日候選整理與每週正式百科整理還是分散 scripts，不是一個明確產品面。
4. **決策缺口**：Arthur 需要看到「哪些建議寫、哪些建議合併、哪些應丟棄、哪些要裁決」。
5. **安全缺口**：任何自動 merge / delete / promote 都有污染百科或洩密風險，所以第一版必須 report-only。

---

## 2. 核心原則

### 2.1 不變鐵律

1. **Candidate is not knowledge.** 候選不是正式百科。
2. **Draft is not knowledge.** 草稿不進 normal search / MCP search / Supabase sync。
3. **Local first.** Local SQLite + curated `raw/` 是 source of truth。
4. **Supabase is target, not authority.** Supabase 只做同步與 observability。
5. **Report-only first.** 第一版只報告，不自動改資料。
6. **Privacy before crossing boundaries.** 任何 promotion/sync/public export 之前都要 B6 scan。
7. **No destructive merge.** 合併必須是 review decision，不由 cron 自動執行。
8. **Provenance required.** 每條候選與整理建議都要能追到 session / agent / script / knowledge ids。
9. **Arthur-facing first.** 報告先說人話，再給技術附錄。

### 2.2 明確禁止

第一階段禁止：

- cron/subagent/MCP 自動 promote formal knowledge；
- 自動刪除重複知識；
- 自動覆蓋 remote / Supabase；
- 自動把 private draft 推到 public Vault-for-LLM；
- 只根據 semantic similarity 就 destructive merge；
- 把任務流水帳、commit hash、PR 編號、一次性報告寫進正式百科。

---

## 3. 系統角色

## 3.1 Dream Curator — 入口治理

**回答的問題：**「白天發生的這些事，哪些值得變成長期知識？」

輸入：

- current session proposals；
- Feishu reply-only `寫入`；
- session capture；
- subagent proposed knowledge；
- cron/self-maintenance findings；
- 手動候選提交。

輸出：

- `knowledge_candidates` records；
- 每日 `Dream Review Report`；
- 建議：`promote` / `merge` / `discard` / `blocked` / `ask_arthur`。

## 3.2 Knowledge Librarian — 庫存治理

**回答的問題：**「已經進百科的東西，現在是否乾淨、有效、可查、可引用？」

輸入：

- `knowledge` rows；
- `raw/`、`compiled/`、AAAK、Document Map；
- convergence/freshness metrics；
- B7 duplicate/provenance report；
- search QA misses；
- sync drift report。

輸出：

- 每週 `Librarian Weekly Review`；
- 每月 `Deep Cleanup Report`；
- 建議：`review_duplicate` / `review_freshness` / `review_convergence` / `repair_provenance` / `mark_deprecated` / `archive_candidate` / `ask_arthur`。

---

## 4. 資料模型

## 4.1 `knowledge_candidates` table

Purpose：所有 agent/cron/session 提出的候選知識先進這裡。

```sql
CREATE TABLE IF NOT EXISTS knowledge_candidates (
  candidate_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_type TEXT NOT NULL,              -- session|feishu|cron|subagent|manual|mcp
  source_agent TEXT NOT NULL,             -- nancy|cron|subagent-name|manual
  source_session_id TEXT,
  source_channel TEXT,
  source_refs_json TEXT NOT NULL DEFAULT '[]',

  proposed_title TEXT NOT NULL,
  summary TEXT NOT NULL,
  content_draft TEXT NOT NULL,
  category TEXT NOT NULL,                 -- error|technique|decision|workflow|observation|general
  tags_json TEXT NOT NULL DEFAULT '[]',

  classification TEXT NOT NULL,           -- shared_knowledge|private_draft|no_write
  privacy_status TEXT NOT NULL,           -- unknown|clear|redact_required|private_only|blocked
  privacy_flags_json TEXT NOT NULL DEFAULT '[]',
  dedupe_status TEXT NOT NULL,            -- unknown|unique|duplicate|near_duplicate|conflict
  dedupe_candidates_json TEXT NOT NULL DEFAULT '[]',

  status TEXT NOT NULL,                   -- pending|ready_for_review|approved|promoted|merge_suggested|discarded|blocked
  recommended_action TEXT NOT NULL,       -- review|promote|merge|discard|block|ask_arthur
  decision_reason TEXT NOT NULL DEFAULT '',
  reviewer TEXT NOT NULL DEFAULT '',
  reviewed_at TEXT,

  trust_initial REAL NOT NULL DEFAULT 0.4,
  freshness_initial REAL NOT NULL DEFAULT 1.0,
  convergence_status_initial TEXT NOT NULL DEFAULT 'unknown',
  audit_log_json TEXT NOT NULL DEFAULT '[]'
);
```

### Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_candidates_status ON knowledge_candidates(status);
CREATE INDEX IF NOT EXISTS idx_candidates_created_at ON knowledge_candidates(created_at);
CREATE INDEX IF NOT EXISTS idx_candidates_source_session ON knowledge_candidates(source_session_id);
CREATE INDEX IF NOT EXISTS idx_candidates_title ON knowledge_candidates(proposed_title);
```

## 4.2 `knowledge_review_items` table

Purpose：Knowledge Librarian 對正式百科產生的整理建議。

```sql
CREATE TABLE IF NOT EXISTS knowledge_review_items (
  review_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  source_report TEXT NOT NULL,             -- b7|freshness|convergence|search_qa|sync_drift|manual
  issue_type TEXT NOT NULL,                -- duplicate_title|duplicate_content_hash|near_duplicate|stale_freshness|low_convergence|provenance_gap|contradiction|search_miss|sync_drift|archive_candidate
  knowledge_ids_json TEXT NOT NULL DEFAULT '[]',
  titles_json TEXT NOT NULL DEFAULT '[]',
  safe_reason TEXT NOT NULL,
  evidence_refs_json TEXT NOT NULL DEFAULT '[]',
  severity TEXT NOT NULL,                  -- low|medium|high|critical
  recommended_action TEXT NOT NULL,        -- review_duplicate|review_freshness|review_convergence|repair_provenance|mark_deprecated|archive_candidate|ask_arthur
  status TEXT NOT NULL,                    -- open|acknowledged|resolved|discarded|blocked
  reviewer TEXT NOT NULL DEFAULT '',
  reviewed_at TEXT,
  decision_reason TEXT NOT NULL DEFAULT '',
  audit_log_json TEXT NOT NULL DEFAULT '[]'
);
```

## 4.3 Report files

All reports should be reproducible local artifacts:

```text
~/Guardrails-knowledge/reports/dream/YYYY-MM-DD-dream-review.json
~/Guardrails-knowledge/reports/dream/YYYY-MM-DD-dream-review.md
~/Guardrails-knowledge/reports/librarian/YYYY-MM-DD-weekly.json
~/Guardrails-knowledge/reports/librarian/YYYY-MM-DD-weekly.md
~/Guardrails-knowledge/reports/librarian/YYYY-MM-monthly.json
~/Guardrails-knowledge/reports/librarian/YYYY-MM-monthly.md
```

Reports are artifacts, not source of truth. DB state + raw/compiled remain canonical.

---

## 5. 狀態機

## 5.1 Candidate lifecycle

```text
pending
  → ready_for_review
  → approved
  → promoted
```

Alternative paths:

```text
pending → blocked
pending → discarded
ready_for_review → merge_suggested
ready_for_review → ask_arthur
approved → promoted
approved → blocked
```

Rules:

- `blocked` means privacy/security prevents storing content beyond minimal audit.
- `discarded` means not valuable enough for long-term knowledge.
- `merge_suggested` means do not create a new knowledge row; update/append existing entry after review.
- `promoted` requires exact created/updated knowledge id and verification evidence.

## 5.2 Review item lifecycle

```text
open
  → acknowledged
  → resolved
```

Alternative paths:

```text
open → discarded
open → blocked
```

Rules:

- `resolved` requires evidence: changed knowledge id, map rebuilt, search/readback verified, or explicit no-op reason.
- `discarded` requires reason: false positive, historical note, intentionally duplicated, etc.

---

## 6. Daily Dream Curator Workflow

## 6.1 Collection

Sources:

1. current assistant proposal accepted by Arthur;
2. session scanner for previous day;
3. subagent final summaries with `knowledge_candidates` block;
4. cron script findings;
5. manual CLI/API submit.

Command target:

```bash
cd ~/Guardrails-knowledge
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli dream collect --since yesterday --output /tmp/guardrails_dream_collect.json
```

Expected invariants:

```json
{
  "schema": "guardrails.dream.collect.v1",
  "writes_formal_knowledge": false,
  "auto_promote": false,
  "candidates_created": 0
}
```

## 6.2 Classification

Each candidate gets:

```text
shared_knowledge | private_draft | no_write
```

Rules:

- reusable technical/workflow/decision knowledge → `shared_knowledge`;
- personal/client/internal sensitive raw context → `private_draft`;
- secrets/customer PII/one-off logs/unverified guesses → `no_write`.

## 6.3 Privacy preflight

Outcomes:

```text
clear | redact_required | private_only | blocked
```

Minimum scans:

- token/API key/private key patterns;
- `.env` / connection string patterns;
- customer PII / CRM treatment/payment details;
- raw personal life-profile content;
- external platform private data;
- session transcript body that should not cross into shared knowledge.

## 6.4 Dedupe & merge check

Signals:

- exact title;
- normalized title;
- content hash;
- keyword search;
- hybrid/semantic search;
- graph neighbor;
- same lesson vs same topic with new edge case;
- contradiction.

## 6.5 Dream Review Report

Markdown report format:

```markdown
# Guardrails Dream Review — YYYY-MM-DD

## 結論
今天有 X 條候選；建議寫入 A 條、合併 B 條、丟棄 C 條、需 Arthur 裁決 D 條。

## 建議寫入
1. [category] title
   - 為什麼值得記：...
   - 來源：session/cron/subagent
   - 風險：clear
   - 建議動作：promote after approval

## 建議合併
...

## 建議丟棄
...

## 需要 Arthur 裁決
...

## 技術附錄
- report path
- candidate ids
- dedupe ids
- scanner summary
```

Feishu CTA:

```text
回覆：「寫入全部」「只寫 1,3」「合併 2」「先不用」「封鎖 4」
```

---

## 7. Weekly Knowledge Librarian Workflow

## 7.1 Signals

Weekly report gathers:

1. B7 duplicate/provenance report;
2. convergence partial/unknown/low score;
3. freshness critical/stale;
4. contradiction/conflict candidates;
5. search QA misses/regressions;
6. Document Map coverage gaps;
7. Supabase sync drift;
8. archive candidates such as daily radar/report entries that do not belong in long-term shared knowledge.

Command target:

```bash
cd ~/Guardrails-knowledge
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli librarian weekly --output /tmp/guardrails_librarian_weekly.json
```

Expected invariants:

```json
{
  "schema": "guardrails.librarian.weekly.v1",
  "report_only": true,
  "auto_promote": false,
  "destructive_merge": false,
  "remote_overwrite": false
}
```

## 7.2 Weekly report format

```markdown
# Guardrails Librarian Weekly Review — YYYY-MM-DD

## 結論
本週百科健康度：...

## 1. 建議合併 / 去重
- group: #id + #id
- reason: same lesson / duplicate title / duplicate content hash
- recommended action: review_duplicate

## 2. 建議標記過時 / 更新
- #id title
- freshness: critical
- reason: provider/API/CLI behavior likely changed
- recommended action: review_freshness

## 3. 建議補強
- #id title
- convergence: partial/unknown
- missing: symptoms/root cause/fix/verification

## 4. Provenance / Document Map gap
- #id title
- missing: raw/compiled/map

## 5. 建議封存
- #id title
- reason: daily report / one-off status / time-limited artifact

## 6. 需要 Arthur 裁決
...
```

---

## 8. Monthly Deep Cleanup Workflow

Monthly cleanup does not necessarily inspect every line. It produces a board-level health review.

Checks:

- total knowledge count trend;
- embeddings coverage;
- Document Map coverage;
- convergence distribution;
- freshness distribution;
- unresolved review items by age;
- top duplicate clusters;
- raw/compiled/DB consistency;
- Supabase sync drift;
- public-safe export risks;
- skills vs Guardrails overlap.

Command target:

```bash
cd ~/Guardrails-knowledge
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli librarian monthly --output /tmp/guardrails_librarian_monthly.json
```

Output:

```text
百科健康度月報
- 本月新增多少正式知識
- 有多少候選被丟棄，避免污染
- 還有多少 duplicates/stale/partial/provenance gaps
- 下月最該修的 3 件事
```

---

## 9. Cron 設計

## 9.1 Daily Dream Curator

Name:

```text
🧠 Guardrails Dream Curator — Daily Review
```

Schedule:

```text
10 8 * * *
```

Model:

```json
{"provider":"openai-codex","model":"gpt-5.5"}
```

Reason: needs judgment, synthesis, dedupe explanation, Arthur-facing report.

Delivery:

```text
origin or Feishu report group, depending on Arthur preference
```

Toolsets:

```json
["terminal", "file", "web"]
```

Prompt invariant:

```text
You are Guardrails Dream Curator. Use only candidate/report artifacts and safe metadata. Do not promote, merge, delete, sync, or write formal knowledge. Produce an Arthur-facing review report. If there are no candidates, output [SILENT].
```

## 9.2 Weekly Knowledge Librarian

Name:

```text
📚 Guardrails Knowledge Librarian — Weekly Hygiene
```

Schedule:

```text
30 8 * * 1
```

Model:

```json
{"provider":"openai-codex","model":"gpt-5.5"}
```

Prompt invariant:

```text
You are Guardrails Knowledge Librarian. Review existing formal knowledge using report-only signals. Do not delete, merge, deprecate, sync, or overwrite. Produce a prioritized hygiene report with recommended actions only.
```

## 9.3 Monthly Deep Cleanup

Name:

```text
🧹 Guardrails Deep Cleanup — Monthly Health Review
```

Schedule:

```text
0 9 1 * *
```

Model:

```json
{"provider":"openai-codex","model":"gpt-5.5"}
```

Prompt invariant:

```text
Produce a monthly health review. Report-only. No destructive changes. Summarize trends and top 3 cleanup priorities.
```

---

## 10. Dashboard / Workbench Integration

Dashboard should consume only count-only safe aggregates.

Allowed Dashboard fields:

```json
{
  "dream_candidates_pending": 0,
  "dream_candidates_ready_for_review": 0,
  "dream_candidates_blocked": 0,
  "librarian_open_duplicates": 0,
  "librarian_open_stale": 0,
  "librarian_open_low_convergence": 0,
  "librarian_open_provenance_gaps": 0,
  "last_dream_review_at": "...",
  "last_librarian_review_at": "..."
}
```

Forbidden Dashboard fields:

- raw candidate content;
- session transcript body;
- `content_draft`;
- private source refs;
- secret scanner findings text containing possible secret fragments;
- exact customer/client details.

Fail closed if:

- report says `report_only=false`;
- `auto_promote=true`;
- `destructive_merge=true`;
- unknown issue types;
- unknown recommended actions;
- report contains raw/private payload fields.

---

## 11. Implementation Tasks

### Task 1: Add schema migration for candidate/review tables

**Objective:** Create local SQLite tables for dream candidates and librarian review items.

**Files:**

- Create: `supabase/migrations/local/20260523_dream_librarian_tables.sql` or project-appropriate local migration path.
- Modify: `guardrails_lite/guardrails_db.py` if project uses Python-managed schema migrations.
- Test: `tests/test_dream_librarian_schema.py`

**Steps:**

1. Inspect current schema migration conventions.
2. Add `knowledge_candidates` and `knowledge_review_items` tables.
3. Add indexes.
4. Write tests that create a temp DB and assert tables/columns/indexes exist.
5. Run targeted test.
6. Commit scoped schema/test change.

**Verification:**

```bash
cd ~/Guardrails-knowledge
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest tests/test_dream_librarian_schema.py -q
```

Expected: PASS.

---

### Task 2: Add candidate model helpers

**Objective:** Provide typed helper functions to insert/list/update candidate rows safely.

**Files:**

- Create: `guardrails_lite/dream_queue.py`
- Test: `tests/test_dream_queue.py`

**Required functions:**

```python
def create_candidate(conn, candidate: dict) -> str: ...
def list_candidates(conn, status: str | None = None, limit: int = 50) -> list[dict]: ...
def update_candidate_status(conn, candidate_id: str, status: str, reason: str, reviewer: str = "") -> None: ...
def append_candidate_audit(conn, candidate_id: str, event: dict) -> None: ...
```

**Rules:**

- Validate enum values.
- JSON fields must round-trip as lists/dicts.
- Do not write to formal `knowledge` table.
- Do not invoke sync.

**Verification:**

```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest tests/test_dream_queue.py -q
```

Expected: PASS.

---

### Task 3: Implement `guardrails dream submit`

**Objective:** Allow manual/agent-safe submission of candidate knowledge without formal write.

**Files:**

- Modify: `guardrails_lite/guardrails_cli.py`
- Modify/Create: `guardrails_lite/dream_queue.py`
- Test: `tests/test_dream_cli.py`

**CLI target:**

```bash
guardrails dream submit \
  --title "..." \
  --summary "..." \
  --content-file /tmp/candidate.md \
  --category technique \
  --tags "guardrails,dream" \
  --source-agent nancy \
  --source-type manual
```

**Expected output:**

```json
{
  "success": true,
  "candidate_id": "dream_...",
  "formal_knowledge_written": false
}
```

**Verification:**

- Candidate row exists.
- `knowledge` count unchanged.
- `raw/` unchanged.

---

### Task 4: Implement privacy preflight for candidates

**Objective:** Run B6 privacy scanner before candidate becomes ready for review.

**Files:**

- Modify/Create: `guardrails_lite/privacy_scanner.py` if existing scanner module exists, otherwise add a dedicated interface.
- Modify: `guardrails_lite/dream_queue.py`
- Test: `tests/test_dream_privacy.py`

**Minimum cases:**

1. normal workflow content → `clear`;
2. fake API key/token pattern → `blocked` or `redact_required`;
3. private/customer details → `private_only`;
4. docs that mention scanner patterns as examples → avoid false positive if clearly placeholder.

**Verification:**

```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest tests/test_dream_privacy.py -q
```

---

### Task 5: Implement candidate dedupe check

**Objective:** Attach safe dedupe candidates to each dream candidate.

**Files:**

- Create/Modify: `guardrails_lite/dream_dedupe.py`
- Test: `tests/test_dream_dedupe.py`

**Signals:**

- exact title;
- normalized title;
- content hash;
- keyword search;
- optional semantic search if embeddings available;
- conflict markers.

**Output shape:**

```json
{
  "dedupe_status": "unique|duplicate|near_duplicate|conflict",
  "dedupe_candidates": [
    {"knowledge_id": 858, "title": "...", "reason": "normalized_title"}
  ]
}
```

**Safety:** no raw content in report.

---

### Task 6: Implement `guardrails dream review-report`

**Objective:** Generate daily Arthur-facing dream review report from pending candidates.

**Files:**

- Create: `guardrails_lite/dream_report.py`
- Modify: `guardrails_lite/guardrails_cli.py`
- Test: `tests/test_dream_report.py`

**CLI target:**

```bash
guardrails dream review-report --date 2026-05-23 --output reports/dream/2026-05-23-dream-review.json --markdown reports/dream/2026-05-23-dream-review.md
```

**Invariants:**

```json
{
  "schema": "guardrails.dream.review.v1",
  "report_only": true,
  "auto_promote": false,
  "formal_knowledge_written": false
}
```

**Verification:**

- JSON parses.
- Markdown generated.
- No raw private payload.
- Candidate counts correct.

---

### Task 7: Implement review decision CLI

**Objective:** Record Arthur/Nancy decisions without immediately doing unsafe writes.

**Files:**

- Modify: `guardrails_lite/guardrails_cli.py`
- Modify: `guardrails_lite/dream_queue.py`
- Test: `tests/test_dream_decisions.py`

**CLI target:**

```bash
guardrails dream decide dream_20260523_xxx --decision approved --reason "Arthur confirmed in Feishu"
```

Allowed decisions:

```text
approved | merge_suggested | discarded | blocked | ask_arthur
```

**Verification:** audit log contains reviewer/time/reason.

---

### Task 8: Implement safe promotion path

**Objective:** Promote exactly approved candidates to formal knowledge using existing local add/compile/map/sync discipline, but only when explicitly called.

**Files:**

- Create: `guardrails_lite/dream_promote.py`
- Modify: `guardrails_lite/guardrails_cli.py`
- Test: `tests/test_dream_promote.py`

**CLI target:**

```bash
guardrails dream promote dream_20260523_xxx --reviewer nancy --no-sync
```

**Hard gates:**

- candidate status must be `approved`;
- privacy status must be `clear` or approved `redact_required` result;
- dedupe must not be unresolved `duplicate` or `conflict`;
- content must pass final scanner;
- generated raw file must include summary/category/tags/created/source;
- compile/map/readback verification must run.

**First implementation option:** keep promotion manual and local-only; sync remains a separate explicit command.

---

### Task 9: Implement librarian review item helpers

**Objective:** Create helpers to store formal knowledge hygiene review items.

**Files:**

- Create: `guardrails_lite/librarian_queue.py`
- Test: `tests/test_librarian_queue.py`

**Required functions:**

```python
def create_review_item(conn, item: dict) -> str: ...
def list_review_items(conn, status: str = "open", limit: int = 50) -> list[dict]: ...
def resolve_review_item(conn, review_id: str, reason: str, reviewer: str) -> None: ...
```

---

### Task 10: Implement weekly librarian report

**Objective:** Aggregate B7/freshness/convergence/provenance signals into a single weekly report.

**Files:**

- Create: `guardrails_lite/librarian_report.py`
- Modify: `guardrails_lite/guardrails_cli.py`
- Test: `tests/test_librarian_report.py`

**CLI target:**

```bash
guardrails librarian weekly --output reports/librarian/2026-05-25-weekly.json --markdown reports/librarian/2026-05-25-weekly.md
```

**Invariants:**

```json
{
  "schema": "guardrails.librarian.weekly.v1",
  "report_only": true,
  "auto_promote": false,
  "destructive_merge": false,
  "remote_overwrite": false
}
```

**Sources:**

- existing `guardrails b7 report`;
- convergence check;
- freshness check;
- Document Map gap check;
- optional search QA misses.

---

### Task 11: Implement monthly deep cleanup report

**Objective:** Produce high-level health report and top cleanup priorities.

**Files:**

- Extend: `guardrails_lite/librarian_report.py`
- Test: `tests/test_librarian_monthly.py`

**CLI target:**

```bash
guardrails librarian monthly --output reports/librarian/2026-06-monthly.json --markdown reports/librarian/2026-06-monthly.md
```

**Output:**

- counts;
- trends;
- unresolved review items by age;
- top duplicate clusters;
- top stale categories;
- recommended next 3 cleanup tasks.

---

### Task 12: Add Hermes cron wrappers

**Objective:** Add thin scripts under `~/.hermes/scripts/` for scheduled runs.

**Files:**

- Create: `~/.hermes/scripts/guardrails_dream_curator.py`
- Create: `~/.hermes/scripts/guardrails_librarian_weekly.py`
- Create: `~/.hermes/scripts/guardrails_librarian_monthly.py`

**Wrapper rules:**

- use absolute Python path: `/home/zycas/miniconda3/envs/guardrails-lite/bin/python`;
- run from `/home/zycas/Guardrails-knowledge`;
- write reports to repo `reports/` or runtime dir by policy;
- stdout has hard budget;
- `[SILENT]` if no actionable items;
- no formal writes.

**Verification:** direct script smoke before cron creation.

---

### Task 13: Create cron jobs and verify

**Objective:** Schedule Dream Curator and Librarian reviews.

**Use Hermes `cronjob` tool:**

1. Create daily Dream Curator job.
2. Create weekly Librarian job.
3. Create monthly Deep Cleanup job.
4. Immediately run each job.
5. Check `last_status=ok` and delivery target.

**Important:** These are not `no_agent=True` unless scripts output final report fully. If LLM synthesis is required, pin `openai-codex/gpt-5.5`.

---

### Task 14: Add Dashboard count-only aggregate

**Objective:** Export safe counts for Dashboard without raw content.

**Files:**

- Create/Modify: `guardrails_lite/dashboard_aggregate.py`
- Test: `tests/test_dream_librarian_dashboard_aggregate.py`

**Output:** count-only JSON.

**Fail closed if:** unknown issue types, forbidden fields, unsafe flags.

---

### Task 15: Documentation and operating manual

**Objective:** Make future agents know the rules.

**Files:**

- Modify: `docs/session_writeback_governance.md`
- Modify: `docs/session_capture_draft_queue_design.md`
- Modify: `docs/multi_agent_convergence_workflow.md`
- Create: `docs/dream_librarian_operating_manual.md`
- Modify: `PROGRESS.md`
- Optional: update `SCHEMA.md`

**Must include:**

- candidate ≠ knowledge;
- draft ≠ knowledge;
- report-only first;
- review commands;
- promote gates;
- cron schedule;
- troubleshooting;
- Feishu reply format.

---

## 12. Testing Strategy

### 12.1 Targeted tests

```bash
cd ~/Guardrails-knowledge
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_dream_librarian_schema.py \
  tests/test_dream_queue.py \
  tests/test_dream_cli.py \
  tests/test_dream_privacy.py \
  tests/test_dream_dedupe.py \
  tests/test_dream_report.py \
  tests/test_librarian_queue.py \
  tests/test_librarian_report.py \
  tests/test_dream_librarian_dashboard_aggregate.py \
  -q
```

### 12.2 Full regression

```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
```

### 12.3 CLI smoke

```bash
guardrails dream submit --title "Test candidate" --summary "測試候選不寫正式百科" --content-file /tmp/test.md --category general --tags test --source-agent nancy --source-type manual

guardrails dream review-report --output /tmp/dream.json --markdown /tmp/dream.md

guardrails librarian weekly --output /tmp/librarian.json --markdown /tmp/librarian.md
```

Verify:

- candidate created;
- formal `knowledge` row count unchanged until explicit promote;
- reports parse;
- `report_only=true`;
- no raw private payload;
- no destructive flags.

### 12.4 Security scan smoke

```bash
python - <<'PY'
import json
for path in ['/tmp/dream.json', '/tmp/librarian.json']:
    text=open(path, encoding='utf-8').read()
    for forbidden in ['BEGIN PRIVATE KEY', 'Bearer ', 'content_raw', 'plain_secret', 'api_key=']:
        assert forbidden not in text, (path, forbidden)
print('safe report smoke ok')
PY
```

---

## 13. Acceptance Criteria

### Phase 1 acceptance — Dream Inbox

- [ ] Agents can submit candidates without writing formal knowledge.
- [ ] Candidate schema stores source/provenance/status/audit.
- [ ] Privacy and dedupe statuses are stored.
- [ ] `knowledge` count does not change during candidate submission.
- [ ] Tests cover clear/private/block/duplicate cases.

### Phase 2 acceptance — Dream Review

- [ ] Daily report groups candidates into write/merge/discard/blocked/ask Arthur.
- [ ] Report is Arthur-facing and safe.
- [ ] Feishu response can map back to candidate ids.
- [ ] No auto promote.

### Phase 3 acceptance — Safe Promote

- [ ] Only `approved` candidates can promote.
- [ ] Promotion writes local raw + DB through canonical path.
- [ ] Compile/map/readback verification runs.
- [ ] Search miss after write is reported as search backlog, not false failure.
- [ ] Sync remains explicit or separately approved.

### Phase 4 acceptance — Librarian Weekly

- [ ] Weekly report covers duplicate/freshness/convergence/provenance/search QA signals.
- [ ] Review items are stored and can be resolved/discarded.
- [ ] No destructive merge/delete/deprecate.

### Phase 5 acceptance — Monthly Deep Cleanup

- [ ] Monthly health report tracks trends.
- [ ] Top 3 cleanup priorities are clear.
- [ ] Dashboard can show count-only aggregate.

---

## 14. Risk Matrix

| Risk | Impact | Mitigation |
|---|---|---|
| Candidate queue becomes another垃圾堆 | High | Daily report groups discard/block reasons; weekly age review. |
| Privacy scanner false negative | Critical | Block suspicious content; keep raw session out of shared candidates; B6 scan before promote/sync. |
| False duplicate suggestions | Medium | Report-only first; human review; classify same lesson vs same topic edge case. |
| Agent over-trusts report | High | Every report includes `report_only=true`, `auto_promote=false`; prompt forbids formal writes. |
| Dashboard leaks titles/content | High | Count-only aggregate; fail closed for raw fields. |
| Cron token cost grows | Medium | Script pre-aggregation, stdout budget, `[SILENT]` on no action. |
| Dirty repo / divergent origin blocks commit | Medium | Scope changes; avoid `git add .`; do not force push; report divergence. |
| Formal promote bypasses compile/map | High | Safe promote CLI hard-gates verification. |
| Remote Supabase drift overwrites local | Critical | Local → remote only; remote drift report-only. |

---

## 15. Recommended Start Sequence

### Sprint DL-1 — Design-to-schema foundation

1. Add schema migration for `knowledge_candidates` and `knowledge_review_items`.
2. Add queue helper modules and tests.
3. Add `guardrails dream submit`.
4. Verify candidate submission does not change formal knowledge.

### Sprint DL-2 — Daily Dream Review

1. Add privacy preflight interface.
2. Add dedupe check.
3. Add `dream review-report` JSON/Markdown.
4. Add Feishu-friendly report format.
5. Run report on synthetic fixtures.

### Sprint DL-3 — Safe promote, still manual

1. Add decision CLI.
2. Add explicit safe promote CLI.
3. Hard-gate privacy/dedupe/compile/map/readback.
4. Keep sync separate.

### Sprint DL-4 — Weekly Librarian

1. Build `librarian weekly` on top of B7/freshness/convergence.
2. Store review items.
3. Add resolution/discard flow.
4. Output Arthur-facing report.

### Sprint DL-5 — Cron and Dashboard

1. Add wrappers.
2. Create cron jobs.
3. Verify manual run and delivery.
4. Add count-only Dashboard aggregate.

### Sprint DL-6 — Monthly Deep Cleanup

1. Add monthly report.
2. Add trend metrics.
3. Add top cleanup priorities.
4. Document operating manual.

---

## 16. Open Questions for Arthur

These are the only product decisions that need Arthur input before production cron creation:

1. **Dream Review 發哪裡？** 原 Feishu 對話、報告群、還是專門百科群？
2. **Daily Dream Curator 時間？** 建議 08:10，讓你早上看到。
3. **Weekly Librarian 時間？** 建議週一 08:30。
4. **Monthly Deep Cleanup 是否每月 1 號？** 建議每月 1 號 09:00。
5. **低風險 candidate 未來是否允許半自動 promote？** MVP 不允許；跑 1–2 週後再討論。

---

## 17. Completion Report Checklist

When this plan is implemented, final report must include:

- [ ] What files changed.
- [ ] What tables/commands were added.
- [ ] Which tests ran and passed.
- [ ] Direct CLI smoke outputs.
- [ ] Cron job ids and `last_status=ok`.
- [ ] Example Dream Review report path.
- [ ] Example Librarian Weekly report path.
- [ ] Proof that formal knowledge was not changed by candidate submission.
- [ ] Proof that Dashboard aggregate is count-only.
- [ ] Remaining manual decisions.

---

## 18. One-line product promise

> 白天所有 agent 先把「可能值得記」放進夢境池；每天整理夢，週週整理書架，月月做健康檢查。正式百科只收通過隱私、去重、收斂與人工確認的長期知識。
