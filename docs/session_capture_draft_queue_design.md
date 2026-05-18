# B5 — Session Capture Draft Queue Design

> **For Hermes:** This is the B5 design contract for internal Guardrails dogfood. It connects B1 writeback governance and B6 privacy scanning into a review-gated draft queue. Do not implement silent auto-capture. Drafts must stay outside normal search until explicitly promoted.

**Last updated:** 2026-05-18 09:51 CST

**Phase:** Phase B / B5 — session capture draft queue

**Status:** Design complete, implementation pending

**Depends on:**

- `docs/session_writeback_governance.md` — B1 classification, review, dedupe, promote rules
- `docs/privacy_scanner_design.md` — B6 scanner outcomes and redaction/audit contract

**Next after this:** B2 Document Map coverage pass or B5 implementation, depending on priority

---

## 0. Goal

Borrow the useful part of agentmemory-style session capture without turning Guardrails into an uncontrolled recorder.

Session capture should become:

```text
session / transcript / manual note
  → dry-run candidate extraction
  → B1 classification
  → B6 privacy scan
  → dedupe / merge check
  → draft queue
  → human or explicit agent review
  → promote / merge / discard / block
```

Not:

```text
session happened → raw/ entry → compile → normal search
```

B5 defines the queue and lifecycle that keeps captured memory review-gated.

---

## 1. Non-goals

B5 does **not** implement:

- full scanner rules — see B6,
- candidate extraction LLM prompts — later B1-T2 work,
- search ranking / CJK retrieval improvements,
- automatic promotion,
- automatic Supabase sync of drafts,
- public Vault-for-LLM capture feature packaging,
- a hosted personal data collector.

B5 is a design contract for future implementation.

---

## 2. Core invariants

1. **Dry-run by default.**
   - Importing a session produces a redacted candidate report unless the caller explicitly asks to write drafts.

2. **Drafts are not knowledge.**
   - Drafts do not live in `raw/`.
   - Drafts do not create `knowledge` rows.
   - Drafts do not create `knowledge_vec` rows.
   - Drafts do not appear in `guardrails search`.

3. **Drafts cannot bypass B1/B6.**
   - Every draft must have a B1 classification.
   - Every draft must have a B6 privacy outcome.

4. **Private drafts remain local/private.**
   - `private_draft` and `private_only` materials never sync to Supabase as raw text.
   - Only transformed general rules may become shared knowledge.

5. **Blocked content stores audit only.**
   - Raw secrets, raw customer data, and raw private life material are not preserved in draft body or event notes.

6. **Promotion uses the normal pipeline.**
   - Curated promoted content enters `raw/`, runs compile/map/verify/search/sync like manual entries.

---

## 3. Source ingestion model

| Source | Allowed input | Stored source metadata | Raw transcript retention |
|---|---|---|---|
| Hermes session | session id, assistant/user messages, tool summaries | session id, source agent, channel, safe timestamps | no full raw transcript by default |
| Feishu transcript | selected thread/message refs, reply-only `寫入` proposal | chat/thread/message refs if safe | no whole conversation storage |
| Manual pasted notes | curated text pasted by Arthur or agent | actor, timestamp, manual source label | only redacted candidate text |
| Cron/session scan | daily candidate report | run id, scan window, counts | no raw transcript in draft queue |
| Subagent report | final summary and evidence handles | subagent id/model/session, returned file/id | no unverified raw tool logs |

Rules:

- Source refs must not include tokenized URLs, private credential paths, or raw secret-bearing transcript paths.
- If a transcript is needed for review, store an access handle outside shared search and mark it private; do not copy raw text into shared draft fields.
- Candidate reports sent to Feishu must show redacted previews only.

---

## 4. Capture modes

### 4.1 Dry-run mode — default

```bash
guardrails capture import --file session.jsonl --dry-run
```

Dry-run may:

- parse source,
- extract candidates,
- classify via B1,
- run B6 privacy scan,
- run dedupe checks,
- print or write a redacted report.

Dry-run must not:

- write `capture_drafts`,
- write `raw/`,
- call `guardrails add`,
- compile,
- sync,
- send unredacted content to Feishu.

### 4.2 Write-drafts mode

```bash
guardrails capture import --file session.jsonl --write-drafts
```

Write-drafts may create draft queue rows/files only for candidates that pass minimum storage rules:

- `shared_knowledge + clear` → pending review draft.
- `shared_knowledge + redact_required` → needs redaction; store only redacted draft.
- `private_draft + clear/redact_required/private_only` → private local draft only.
- `no_write` or `blocked` → audit-only event, no content body.

### 4.3 Review/promote mode

Promotion is an explicit review action, not part of import.

```bash
guardrails draft review <draft_id> --decision promote
```

Promotion must run the B6 scanner again on the exact content that will enter `raw/`.

---

## 5. Canonical storage design

Recommended canonical queue: SQLite tables in the local Guardrails database.

### 5.1 `capture_import_runs`

Tracks one import/dry-run batch.

```sql
CREATE TABLE IF NOT EXISTS capture_import_runs (
    run_id              TEXT PRIMARY KEY,
    schema_version      INTEGER NOT NULL DEFAULT 1,
    source_channel      TEXT NOT NULL,
    source_session_id   TEXT NOT NULL DEFAULT '',
    mode                TEXT NOT NULL, -- dry_run | write_drafts
    actor               TEXT NOT NULL DEFAULT '',
    started_at          TEXT NOT NULL,
    completed_at        TEXT NOT NULL DEFAULT '',
    stats_json          TEXT NOT NULL DEFAULT '{}',
    report_redacted     TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL
);
```

### 5.2 `capture_drafts`

Tracks one candidate/draft.

```sql
CREATE TABLE IF NOT EXISTS capture_drafts (
    draft_id                         TEXT PRIMARY KEY,
    schema_version                   INTEGER NOT NULL DEFAULT 1,

    status                           TEXT NOT NULL,
    classification                   TEXT NOT NULL,
    privacy_outcome                  TEXT NOT NULL,
    visibility                       TEXT NOT NULL,

    source_channel                   TEXT NOT NULL,
    source_agent                     TEXT NOT NULL DEFAULT '',
    source_session_id                TEXT NOT NULL DEFAULT '',
    source_refs_json                 TEXT NOT NULL DEFAULT '[]',
    source_metadata_json             TEXT NOT NULL DEFAULT '{}',
    import_run_id                    TEXT NOT NULL DEFAULT '',

    extracted_at                     TEXT NOT NULL,
    created_at                       TEXT NOT NULL,
    updated_at                       TEXT NOT NULL,

    proposed_title                   TEXT NOT NULL,
    summary                          TEXT NOT NULL,
    content_draft_redacted           TEXT NOT NULL DEFAULT '',
    category                         TEXT NOT NULL DEFAULT 'general',
    tags_json                        TEXT NOT NULL DEFAULT '[]',

    trust_initial                    REAL NOT NULL DEFAULT 0.4,
    freshness_initial                REAL NOT NULL DEFAULT 1.0,
    convergence_status_initial       TEXT NOT NULL DEFAULT 'unknown',

    privacy_flags_json               TEXT NOT NULL DEFAULT '[]',
    privacy_findings_summary_json    TEXT NOT NULL DEFAULT '{}',
    scanner_version                  TEXT NOT NULL DEFAULT '',
    redaction_applied                INTEGER NOT NULL DEFAULT 0,

    content_fingerprint              TEXT NOT NULL DEFAULT '',
    dedupe_candidates_json           TEXT NOT NULL DEFAULT '[]',
    duplicate_of_knowledge_id        INTEGER DEFAULT NULL,
    merge_target_knowledge_id        INTEGER DEFAULT NULL,

    review_decision                  TEXT NOT NULL DEFAULT 'pending',
    decision_reason                  TEXT NOT NULL DEFAULT '',
    reviewer                         TEXT NOT NULL DEFAULT '',
    reviewed_at                      TEXT NOT NULL DEFAULT '',

    promoted_knowledge_id            INTEGER DEFAULT NULL,
    promoted_raw_path                TEXT NOT NULL DEFAULT '',
    compile_run_id                   TEXT NOT NULL DEFAULT '',
    search_verification_json         TEXT NOT NULL DEFAULT '{}',

    FOREIGN KEY (import_run_id) REFERENCES capture_import_runs(run_id)
);
```

### 5.3 `capture_draft_events`

Append-only audit trail.

```sql
CREATE TABLE IF NOT EXISTS capture_draft_events (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id              TEXT NOT NULL,
    timestamp             TEXT NOT NULL,
    actor                 TEXT NOT NULL,
    action                TEXT NOT NULL,
    from_status           TEXT NOT NULL DEFAULT '',
    to_status             TEXT NOT NULL DEFAULT '',
    note_redacted         TEXT NOT NULL DEFAULT '',
    audit_summary_json    TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (draft_id) REFERENCES capture_drafts(draft_id)
);
```

### 5.4 Status values

| Status | Meaning | Next states |
|---|---|---|
| `candidate` | extracted, not fully checked | `pending_review`, `needs_redaction`, `blocked`, `discarded` |
| `pending_review` | classified, scanned, dedupe checked | `promote_ready`, `duplicate_review`, `contradiction_review`, `discarded`, `blocked` |
| `needs_redaction` | useful but redaction incomplete | `pending_review`, `blocked`, `discarded` |
| `private_pending` | private/local review only | `transformed`, `discarded`, `blocked` |
| `duplicate_review` | likely duplicate | `merged`, `discarded`, `pending_review` |
| `contradiction_review` | conflicts with existing guidance | `merged`, `promoted`, `discarded` after review |
| `promote_ready` | reviewer approved promote | `promoted`, `blocked` if final scan fails |
| `promoted` | formal knowledge created | terminal |
| `merged` | integrated into existing entry | terminal |
| `discarded` | not valuable enough | terminal |
| `blocked` | privacy/no-write failure | terminal |
| `transformed` | private raw material converted to safe shared candidate | new linked draft |

### 5.5 Visibility values

| Visibility | Meaning |
|---|---|
| `draft_only` | safe draft, not searchable |
| `private_local_only` | local/private review only; no remote sync |
| `audit_only` | no body retained |
| `promoted` | formal knowledge created; normal search allowed through knowledge DB |

---

## 6. Optional Markdown draft export

SQLite is canonical. Markdown export is only for human review.

Suggested path:

```text
drafts/YYYYMMDD/draft_YYYYMMDD_HHMMSS_slug.md
```

Hard rules:

- `drafts/` is not `raw/`.
- Compiler must not scan `drafts/`.
- Normal search must not query `drafts/`.
- Supabase sync must not upload `drafts/`.
- Export body contains redacted preview only.
- Export must include `visibility: draft_only` or `private_local_only`.

Example:

```yaml
---
draft_id: "draft_20260518_095100_capture_queue"
status: "pending_review"
classification: "shared_knowledge"
privacy_outcome: "clear"
visibility: "draft_only"
source_channel: "feishu"
source_agent: "nancy"
source_session_id: "safe-session-id"
source_refs: []
proposed_title: "Session capture drafts must stay outside normal search"
summary: "Session capture should create redacted drafts first; only reviewed promotion enters raw and search."
category: "workflow"
tags: ["guardrails", "capture", "draft-queue", "privacy"]
trust_initial: 0.4
freshness_initial: 1.0
convergence_status_initial: "unknown"
dedupe_candidates: []
review_decision: "pending"
reviewer: ""
reviewed_at: ""
---
```

---

## 7. B1/B6 routing matrix

| B1 classification | B6 outcome | Draft queue action | Promotion eligibility |
|---|---|---|---|
| `shared_knowledge` | `clear` | `pending_review` | yes after dedupe + review |
| `shared_knowledge` | `redact_required` | `needs_redaction` | only after redaction + re-scan |
| `shared_knowledge` | `private_only` | `private_pending` or transform-required | no raw promote |
| `shared_knowledge` | `blocked` | `blocked`, audit only | no |
| `private_draft` | `clear` | `private_pending` | no raw promote; transform only |
| `private_draft` | `redact_required` | redacted `private_pending` | no raw promote; transform only |
| `private_draft` | `private_only` | `private_pending` local only | no raw promote |
| `private_draft` | `blocked` | `blocked`, audit only | no |
| `no_write` | any | `discarded` or `blocked`, audit only | no |

Rule: any future implementation must compute this routing deterministically and store the chosen route in audit.

---

## 8. Dedupe, merge, and contradiction workflow

Before a draft can be promoted, run:

1. Exact proposed title search.
2. Tag + keyword search.
3. Semantic/hybrid search.
4. Graph neighbor lookup if relevant.
5. Known IDs referenced in the source session.
6. Content fingerprint check for idempotent repeated imports.

Decision table:

| Finding | Draft state | Action |
|---|---|---|
| same title + same lesson | `duplicate_review` | merge/update existing entry |
| same topic + new pitfall | `pending_review` | append update note or linked entry |
| contradictory guidance | `contradiction_review` | reviewer decides, no overwrite |
| repeated import same fingerprint | terminal duplicate event | do not create new draft |
| no match | `pending_review` | eligible for new promotion |

Merge output format should preserve history:

```md
## Update YYYY-MM-DD
- New observation
- What changed or what remains valid
- Source session / evidence handle
```

---

## 9. Review lifecycle

### 9.1 Reviewer actions

| Action | Required fields | Result |
|---|---|---|
| `promote` | reviewer, reason, final title/content/tags | create curated raw entry |
| `merge` | reviewer, reason, target knowledge ID | update existing knowledge |
| `discard` | reviewer, reason | terminal no content promotion |
| `block` | scanner/audit reason | terminal audit-only |
| `transform` | reviewer, safe transformed rule | create new linked shared candidate |

### 9.2 Promotion checklist

Promote only when all are true:

- draft classification is `shared_knowledge`,
- privacy outcome is `clear` or safely redacted,
- final content is curated and no longer raw transcript,
- dedupe completed,
- reviewer and decision reason recorded,
- trust/freshness/convergence defaults assigned,
- final scanner pass succeeds,
- source metadata is safe.

### 9.3 Promotion pipeline

```text
draft promote
  → final B6 scan of curated content
  → write raw/ markdown with frontmatter
  → guardrails compile
  → exact title / ID verification
  → Document Map build or verify if long entry
  → read_range verification if map exists
  → search smoke
  → if search misses, add Search QA backlog item
  → optional Supabase sync after local verification + sync scan
```

Promotion success is based on exact local verification, not semantic search ranking alone.

---

## 10. Search invisibility proof

Draft isolation is not just policy; it must be testable.

Current architecture supports isolation if drafts stay outside `raw/` and `knowledge`:

- compiler reads curated knowledge from `raw/`, not `drafts/`,
- normal search reads SQLite `knowledge` / `knowledge_vec`,
- MCP search reads the same knowledge layer,
- Supabase sync starts from local knowledge DB, not draft queue.

### Required smoke test

Use a unique nonce:

```text
NONCE = draft_visibility_nonce_YYYYMMDD_HHMMSS
```

Test steps:

1. Create draft containing `NONCE` in `content_draft_redacted`.
2. Run `guardrails search NONCE`.
3. Query SQLite `knowledge` and `knowledge_vec` for `NONCE`.
4. Verify no normal search hit and no knowledge row.
5. Promote curated entry containing `NONCE`.
6. Compile.
7. Verify exact title/ID exists.
8. Search may now find the entry; if not, record Search QA backlog.

Acceptance:

- Before promotion: zero normal search visibility.
- After promotion: formal knowledge exists only through curated path.

---

## 11. CLI design sketch

### 11.1 Import commands

```bash
guardrails capture import --file session.jsonl --dry-run
guardrails capture import --file session.jsonl --write-drafts
guardrails capture import --from-session <session_id> --dry-run
guardrails capture import --from-feishu-thread <thread_id> --dry-run
```

Defaults:

- `--dry-run` if no mode is specified.
- `--write-drafts` requires explicit flag.
- No import command promotes.

### 11.2 Draft review commands

```bash
guardrails draft list --status pending_review
guardrails draft show <draft_id>
guardrails draft review <draft_id> --decision promote --reason "..."
guardrails draft review <draft_id> --decision merge --target <knowledge_id> --reason "..."
guardrails draft discard <draft_id> --reason "..."
guardrails draft block <draft_id> --reason "..."
```

### 11.3 Reporting commands

```bash
guardrails draft stats
guardrails draft audit <draft_id>
guardrails draft export <draft_id> --format markdown
```

Reporting must redact sensitive previews.

---

## 12. MCP / Feishu / cron boundaries

### 12.1 MCP

Future MCP draft tools may exist:

```text
vault_capture_draft_create
vault_capture_draft_list
vault_capture_draft_review
```

Rules:

- Formal `guardrails_add` / `vault_add` is not for raw session capture.
- Draft-create requires source metadata and intended visibility.
- Draft-review requires explicit review decision.
- Agent cannot silently promote inside the same capture loop without review policy.

### 12.2 Feishu

Feishu review UX should show:

- proposed title,
- summary,
- classification,
- privacy outcome,
- dedupe candidates,
- redacted preview,
- action buttons/commands: promote, merge, discard, block.

Feishu must not show raw tokens, raw CRM details, or raw private life stories.

### 12.3 Cron

Cron may:

- scan sessions,
- generate candidate reports,
- create redacted drafts if explicitly configured,
- report pending review counts.

Cron must not:

- promote,
- override privacy scanner,
- sync private drafts,
- recursively schedule writeback jobs.

---

## 13. Audit requirements

Every state transition writes an event:

```yaml
timestamp: "YYYY-MM-DDTHH:MM:SS+08:00"
actor: "nancy|subagent|cron|arthur|unknown"
action: "created|classified|privacy_checked|redacted|dedupe_checked|reviewed|promoted|merged|discarded|blocked|search_verified"
from_status: "pending_review"
to_status: "promoted"
note_redacted: "safe operational note"
audit_summary:
  privacy_outcome: "clear"
  privacy_rule_ids: []
  dedupe_candidate_count: 0
  reviewer: "arthur"
```

Audit must never include:

- matched secret values,
- full raw private story,
- customer PII,
- tokenized URLs,
- raw transcript chunks with sensitive content.

---

## 14. Edge cases

1. **No reusable lesson**
   - Session has many tool calls but no durable knowledge.
   - Expected: no draft or discarded candidate.

2. **Reply-only `寫入`**
   - Recover previous proposal; if unavailable, ask one clarification.
   - Expected: draft or promote path still goes through B1/B6/dedupe.

3. **Token in transcript**
   - Expected: token redacted/blocked; raw token never stored in draft/audit/report.

4. **Private life story mixed with reusable rule**
   - Expected: private raw material stays private/block; safe transformed rule may become separate candidate.

5. **CRM/customer context**
   - Expected: no shared raw data; only anonymized workflow rule can proceed.

6. **Documentation self-match**
   - Expected: placeholders/pattern examples may be allowed; real values blocked.

7. **Duplicate candidate**
   - Expected: merge flow, no duplicate knowledge entry.

8. **Contradiction**
   - Expected: contradiction review, no overwrite.

9. **Redaction destroys meaning**
   - Expected: private_only or blocked, not clear.

10. **MCP bypass attempt**
    - Expected: raw session capture cannot call formal add directly.

11. **Cron noise**
    - Expected: report/drafts only, rate-limited, no auto-promote.

12. **Concurrent agents**
    - Expected: content fingerprint prevents duplicate draft creation.

13. **Search miss after promote**
    - Expected: exact readback validates promote; search miss goes to Search QA backlog.

14. **Remote divergence / sync failure**
    - Expected: local source of truth remains canonical; no remote overwrite.

---

## 15. Acceptance criteria

B5 design is accepted when all are true:

- [ ] Capture import defaults to dry-run.
- [ ] Drafts are isolated from `raw/`, `knowledge`, `knowledge_vec`, normal search, MCP search, and Supabase sync.
- [ ] Every stored draft has B1 classification and B6 privacy outcome.
- [ ] Blocked/no-write candidates store audit only, not body content.
- [ ] Private drafts remain local/private and cannot be promoted raw.
- [ ] Dedupe runs before promotion.
- [ ] Promotion uses curated `raw/` + compile + map/read/search verification.
- [ ] Unique nonce smoke proves drafts do not enter normal search before promotion.
- [ ] CLI/MCP/Feishu/cron boundaries are explicit.
- [ ] Audit is useful but redacted.
- [ ] The document can feed either B5 implementation or B2/B3 follow-up work.

---

## 16. Implementation tasks after B5

### Task B5-T1 — Add capture draft schema migration

Create SQLite tables:

- `capture_import_runs`
- `capture_drafts`
- `capture_draft_events`

Add tests for schema creation and default values.

### Task B5-T2 — Add draft isolation tests

Create a draft with a unique nonce and prove normal search cannot find it until promotion.

### Task B5-T3 — Add dry-run import command

Implement `guardrails capture import --dry-run` that produces redacted candidate reports only.

### Task B5-T4 — Add write-drafts mode

Implement `--write-drafts` and route through B1/B6 outcomes.

### Task B5-T5 — Add review/promote commands

Implement draft list/show/review/promote/merge/discard/block.

### Task B5-T6 — Add Feishu review report format

Produce redacted review cards for Arthur, with promote/merge/discard/block actions.

### Task B5-T7 — Add Search QA backlog hook

When promoted entries are exact-readable but search misses, append a case to the internal Search QA backlog.

---

## 17. Current decision

After B5 design, the next planning track is **B2 Document Map coverage pass** unless Arthur asks to implement B1/B6/B5 first.

Rationale:

- B1/B6/B5 now define safe write boundaries.
- B2/B3 define whether promoted knowledge can be read, cited, and measured.
- Implementation should not begin until the remote divergence strategy for `/home/zycas/Guardrails-knowledge` is decided or work remains local-only.
