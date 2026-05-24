# Guardrails Internal Knowledge Capability — Progress

Last updated: 2026-05-24 CST

## Current Phase: Phase B — 內部百科真正能力建設 — B1/B6/B5/B2/B3/B4 COMPLETE / B7 REPORT-ONLY + DREAM/LIBRARIAN DL-9 COMPLETE

### Goal
Let Nancy / Hermes / Guardrails dogfood the internal knowledge base every day so real retrieval, citation, capture, privacy, CJK search, and multi-agent convergence problems surface before public Vault-for-LLM productization.

### Current Planning Artifacts
- `docs/phase_b_internal_knowledge_capability_plan.md` — Phase B internal roadmap and execution order.
- `docs/session_writeback_governance.md` — B1 governance contract for session → candidate → draft → review → promote.
- `docs/privacy_scanner_design.md` — B6 shared scanner design for add/capture/compile/sync/MCP privacy gates.
- `docs/session_capture_draft_queue_design.md` — B5 review-gated draft queue design for session capture.
- `docs/document_map_coverage_plan.md` — B2 coverage plan for high-value Document Map/read_range/citation gaps.
- `docs/search_qa_metrics_plan.md` — B3 internal Search QA metrics plan, internal dogfood QA set, baseline, self-compare, and daily reporting boundary.
- `docs/multi_agent_convergence_workflow.md` — B7 local-first multi-agent writing, dedupe/conflict, convergence/freshness queue, safe sync, and public-safe export design contract.
- `docs/guardrails_dream_librarian_system_plan.md` — Guardrails Dream & Librarian System：每日候選整理、每週百科去重/過時/收斂治理、每月深度健康檢查的完整實施計畫。

### Phase B Priority Order
1. B1 對話回寫治理 — COMPLETE (design)
2. B6 privacy scanner — COMPLETE (design)
3. B5 session capture draft queue — COMPLETE (design)
4. B2 Document Map coverage strengthening — COMPLETE (design)
5. B3 internal Search QA metrics — COMPLETE (design/artifact baseline)
6. B4 CJK retrieval improvements — COMPLETE
7. B7 multi-agent writing and convergence workflow — COMPLETE (design)

### Immediate Next Task
Pick the next Dream/Librarian slice from `docs/guardrails_dream_librarian_system_plan.md` after DL-9 historical trend store: either create/verify the live Hermes cron after Arthur confirms delivery target, or add a safe trend-summary consumer for monthly/dashboard comparisons. Keep auto-promote off; review/triage/dashboard/monthly/history reports remain report-only/local-only, and `dream promote` remains explicit manual local-only with required `--no-sync`.

### Active Implementation Slice — 2026-05-24 — Dream/Librarian DL-9 COMPLETE
- ✅ Added runtime-only historical trend store: `guardrails_lite/report_history.py` writes count-only JSONL snapshots under runtime `dream-review/history/dashboard_history.jsonl` for dashboard/monthly comparison baselines.
- ✅ Integrated DL-9 into `scripts/dream_daily_review.py`: daily runs now append/replace a `guardrails.report_history.snapshot.v1` record and include `history_path` in `latest.json` and Feishu/no-agent stdout when candidates exist.
- ✅ Idempotency: repeated daily runs for the same `snapshot_date` replace the existing JSONL record instead of duplicating it, keeping history append-like by date while avoiding repeated cron noise.
- ✅ Path safety: history paths are validated and rejected if they live under project `raw/` or `compiled/`; history remains a runtime artifact store, not a source-of-truth knowledge store.
- ✅ Privacy/count-only hardening after three independent-review blocker rounds: forbidden keys (`candidate_id`, `title`, `knowledge_id`, `summary`, `content_draft`, raw/private payload fields) are rejected; unknown snapshot/aggregate fields are rejected; metric values must be non-bool integers; metadata fields must be valid date/ISO timestamp values; `source_schema` is validated before JSONL persistence.
- ✅ Added TDD coverage in `tests/test_report_history.py` and expanded `tests/test_dream_daily_review_script.py`: count-only summaries, latest/previous/delta behavior, forbidden key rejection, forbidden value rejection, metadata validation, raw/compiled path rejection, and daily-script history idempotency.
- ✅ Verification: report-history + daily-script tests passed (`10 passed`); related DL6-DL8/report tests passed (`28 passed`); Dream/B7 regression suite passed (`107 passed`); scoped `compileall`, `git diff --check`, malicious-candidate script smoke, runtime static scans, and final independent security/code-quality review all passed.
- ⚠️ No commit and no live Hermes cron creation performed. Worktree still contains uncommitted DL-2.5/DL-3/DL-4/DL-5/DL-6/DL-7/DL-8/DL-9 changes and repo remote divergence remains a known constraint; do not force push.

### Previous Implementation Slice — 2026-05-24 — Dream/Librarian DL-6/DL-7/DL-8 COMPLETE
- ✅ DL-6 local-model-assisted triage packet: added `guardrails_lite/dream_triage.py`, producing `schema=guardrails.dream.local_model_triage.v1` prompt-only packets from Dream reviewer UX action items. Packets are local-model-ready but do not call Ollama/vLLM/network by default, do not write formal knowledge/raw, do not sync, and exclude candidate `summary` / `content_draft`.
- ✅ DL-7 count-only dashboard aggregate: added `guardrails_lite/dashboard_aggregate.py`, aggregating safe Dream/B7 report counts into `schema=guardrails.dashboard.aggregate.v1` with `count_only=true` and no titles, candidate IDs, knowledge IDs, raw content, or private payload.
- ✅ DL-8 monthly deep cleanup report-only: added `guardrails_lite/librarian_monthly.py` plus `guardrails librarian monthly --output <json> --markdown <md>`. The report summarizes B7 duplicate/freshness/convergence/provenance queues, baseline trend metrics, and top cleanup priorities without merge/delete/promote/sync/remote overwrite side effects.
- ✅ Extended `scripts/dream_daily_review.py`: each daily run now writes JSON/Markdown review artifacts, DL-6 triage packet, DL-7 dashboard aggregate, and `latest.json` paths under runtime `dream-review/<date>/`; stdout remains bounded/no-agent-friendly and empty when there are zero candidates.
- ✅ Updated `docs/guardrails_dream_cron_manifest.md` to document the additional prompt-only triage and count-only dashboard artifacts, including the invariant that local model APIs are not called by default.
- ✅ Added TDD coverage: `tests/test_dream_local_triage.py`, `tests/test_guardrails_dashboard_aggregate.py`, `tests/test_librarian_monthly.py`, and expanded `tests/test_dream_daily_review_script.py` for new artifacts/latest pointer invariants.
- ✅ Verification: DL-6~DL-8 focused tests passed (`12 passed`); Dream/B7 regression suite passed (`107 passed`); scoped `compileall`, malicious-candidate daily script smoke, runtime static scans, `git diff --check`, and independent security/code-quality review all passed.
- ⚠️ No commit and no live Hermes cron creation performed. Worktree still contains uncommitted DL-2.5/DL-3/DL-4/DL-5/DL-6/DL-7/DL-8 changes and repo remote divergence remains a known constraint; do not force push.

### Previous Implementation Slice — 2026-05-24 — Dream/Librarian DL-5 COMPLETE
- ✅ Added repo-owned cron-ready daily Dream review entrypoint: `scripts/dream_daily_review.py`. It builds local JSON/Markdown review artifacts for a date, updates a local `dream-review/latest.json` pointer atomically, and prints a short no-agent-friendly Feishu message only when candidates exist.
- ✅ Added source-controlled cron specification: `docs/guardrails_dream_cron_manifest.md`, including schedule (`10 8 * * *`), no-agent recommendation, direct smoke command, thin Hermes wrapper template, safety invariants, restore notes, and verification checklist. No live Hermes cron job was created in this slice.
- ✅ Preserved report-only/local-only boundaries: script writes only runtime report artifacts, rejects runtime dirs under project `raw/` or `compiled/`, does not change candidate status, does not write formal knowledge, does not write curated raw knowledge, does not sync, and does not call network APIs.
- ✅ Cron/no-agent behavior: non-empty queue emits bounded summary-only stdout with `MEDIA:<markdown_path>`; empty queue emits empty stdout so `no_agent=True` cron stays silent.
- ✅ Added TDD coverage in `tests/test_dream_daily_review_script.py`: artifact/latest pointer creation, no-agent stdout contract, DB/raw side-effect invariants, empty queue silence, and raw/compiled runtime-dir rejection.
- ✅ Verification: daily review script tests passed (`3 passed`); report tests passed (`19 passed`); all Dream tests passed (`101 passed`); scoped `compileall`, `git diff --check`, malicious candidate-id script smoke, static security scans, and final independent review passed.
- ⚠️ No commit and no live cron creation performed. Worktree still contains uncommitted DL-2.5/DL-3/DL-4/DL-5 changes and repo remote divergence remains a known constraint; do not force push.

### Previous Implementation Slice — 2026-05-24 — Dream/Librarian DL-4 COMPLETE
- ✅ Added reviewer-friendly Dream review UX in `guardrails_lite/dream_report.py`: `reviewer_ux.conclusion`, numbered `action_items`, Feishu `quick_replies`, and Markdown sections `## 結論`, `## Feishu 快速回覆`, and `## 編號審核清單`.
- ✅ Preserved hard safety invariants: review-report remains report-only/local-only with `auto_promote=false`, `formal_knowledge_written=false`, `raw_written=false`, and `sync_invoked=false`; no candidate status, raw, formal knowledge, sync, or network side effects are introduced.
- ✅ Hardened copyable reviewer commands: both new `reviewer_ux.action_items[*].decide_command` and legacy per-candidate Markdown `Feishu CTA:` now shell-quote candidate IDs via `shlex.quote(...)`, with regression coverage for malicious candidate IDs such as `dream_ux_bad; touch /tmp/pwned`.
- ✅ Kept report privacy boundaries: reviewer UX uses safe metadata only, excludes candidate `summary` and `content_draft`, keeps private/blocked metadata redacted, and avoids a top-level `summary` key to preserve existing leak-detection tests.
- ✅ Added TDD coverage in `tests/test_dream_report.py`: reviewer UX conclusion/action-items/quick-replies, report-only invariants, private payload redaction, CLI smoke-visible Markdown sections, and command quoting for both new and legacy CTA command paths.
- ✅ Verification: targeted report tests passed (`19 passed`); all Dream tests passed (`98 passed`); scoped `compileall`, `git diff --check`, CLI smoke with malicious candidate ID, static security scans, and final independent review passed.
- ⚠️ No commit performed. Worktree still contains uncommitted DL-2.5/DL-3/DL-4 changes and repo remote divergence remains a known constraint; do not force push.

### Previous Implementation Slice — 2026-05-24 — Dream/Librarian DL-3 COMPLETE
- ✅ Added explicit safe promotion API in `guardrails_lite/dream_promote.py`: approved Dream candidates can be promoted into local formal knowledge only after hard gates pass before side effects.
- ✅ Added `guardrails dream promote <candidate_id> --reviewer <name> --no-sync` CLI with optional `--skip-compile` / `--skip-map` test/smoke flags. The first implementation is local-only; sync requests fail closed.
- ✅ Promotion hard gates: reviewer required, `no_sync=True`, candidate `status=approved`, `privacy_status=clear`, `classification=shared_knowledge`, dedupe not `duplicate` / `near_duplicate` / `conflict`, final recursive privacy scan must return `clear`, and existing formal title/source collisions are blocked before raw/formal/status side effects.
- ✅ Success path writes a safe unique `raw/*.md` file with JSON frontmatter (`title`, `layer`, `category`, `tags`, `trust`, `summary`, `source`, `source_candidate_id`, `source_agent`, `source_type`, `created`), creates one formal `knowledge` row, updates candidate status to `promoted`, appends audit metadata, and verifies readback.
- ✅ Safety flags are explicit in result/audit: `formal_knowledge_written=true`, `raw_written=true`, `sync_invoked=false`, `auto_promote=false`, `no_sync=true`, plus compile/map/readback flags.
- ✅ Added TDD coverage in `tests/test_dream_promote.py`: success/readback/audit, CLI JSON smoke, default single-file compile/map with trailing-newline normalization, no unintended Git stage/commit during compile verification, raw-title collision isolation, SQL `LIKE` wildcard source-hijack regression, formal-title duplicate blocking, formal-source collision blocking before side effects, and failure invariants proving unsafe cases leave formal knowledge count, raw directory, and candidate status unchanged.
- ✅ Verification: RED evidence captured as missing module before implementation, then as default compile/readback failure, raw-title collision failure, SQL `LIKE` wildcard source-hijack failure, and exact source-collision failure; targeted DL-3 tests passed (`17 passed`); all Dream tests passed (`96 passed`); compile regression smoke `tests/test_lite.py` passed (`4 passed`); CLI smoke created one local knowledge row/raw file with `sync_invoked=false`; default compile/map smoke produced `compile_invoked=true`, `map_invoked=true`, one Document Map node, unchanged Git HEAD, unrelated tracked edits left unstaged, and promoted source preserved despite unrelated same-title raw; scoped `compileall`, `git diff --check`, static security scans, and final independent review passed.
- ⚠️ No commit performed. Worktree still contains uncommitted DL-2.5/DL-3 changes and repo remote divergence remains a known constraint; do not force push.

### Previous Implementation Slice — 2026-05-23 — Dream/Librarian DL-2.5 COMPLETE
- ✅ Added review decision workflow hardening via `guardrails dream decide`: decisions update only `knowledge_candidates`, append audit metadata, and always return `formal_knowledge_written=false`, `raw_written=false`, and `sync_invoked=false`.
- ✅ Added approval safety gates: `approved` now requires `privacy_status=clear`, `classification=shared_knowledge`, non-blocking dedupe status, and a non-reopened terminal status. Unsafe/private/duplicate/conflict candidates must be blocked, discarded, merged only when safe, or escalated to Arthur.
- ✅ Added merge safety gates: `merge_suggested` rejects blocked/private/no_write candidates and refuses to reopen terminal `blocked`/`discarded`/`promoted` rows.
- ✅ Hardened review reports for Feishu/JSON: non-clear privacy statuses (`unknown`, `redact_required`, `private_only`, `blocked`) redact user metadata fields, tags, and dedupe candidate titles; clear candidates remain readable.
- ✅ Hardened privacy flag summaries so arbitrary `kind` / `rule_id` strings are bucketed to safe labels instead of leaking user/private payloads into report JSON/Markdown.
- ✅ Added CLI guardrails: `dream review-report --output/--markdown` rejects paths under project `raw/` or `compiled/`, and `--limit` must be non-negative.
- ✅ Local-model route check: Ollama is reachable at localhost with `qwen3.6:35b` and `gpt-oss:120b`; local models are a backup direction for Dream/Librarian triage rather than the primary route, with cloud/mainline reasoning kept as default unless privacy, cost, or availability requires fallback.
- ✅ Verification: targeted report-hardening tests passed (`10 passed`); DL decision/report/queue/CLI tests passed (`66 passed`); all `tests/test_dream_*.py` passed (`79 passed`); scoped `compileall`, `git diff --check`, and scoped diff check passed.

### Previous Implementation Slice — 2026-05-23 — Dream/Librarian DL-2 COMPLETE
- ✅ Added deterministic recursive candidate privacy preflight with safe findings/audit summaries, redacted output, key-path hashing, secret-in-key detection, placeholder false-positive guards, normal-candidate clear path, and private/blocked action mapping.
- ✅ Added safe candidate dedupe checks for exact title, normalized title, content hash, and title-keyword near matches; persisted dedupe results are metadata-only and do not override stronger privacy recommendations (`block` / `ask_arthur`).
- ✅ Added `guardrails dream review-report` JSON/Markdown output via read-only DB access. Reports include `schema=guardrails.dream.review.v1`, `report_only=true`, `auto_promote=false`, `formal_knowledge_written=false`, `raw_written=false`, and `sync_invoked=false`; they exclude summary/content_draft and redact blocked/private metadata.
- ✅ Added DL-2 tests: `tests/test_dream_privacy.py`, `tests/test_dream_dedupe.py`, and `tests/test_dream_report.py`.
- ✅ Verification: DL-2 targeted tests passed (`16 passed`); DL-1+DL-2 targeted tests passed (`32 passed`); scoped `git diff --check` passed; scoped ruff on Dream/Librarian files/tests passed.
- ⚠️ Full `python -m pytest -q` is still blocked before complete collection by unrelated/pre-existing environment issues: missing `onnxruntime` and `supabase.create_client` import failure.
- ⚠️ Broad ruff over the whole legacy `guardrails_lite/guardrails_cli.py` still reports pre-existing F401/F541/F841 issues outside the DL-2 touched section; scoped Dream/Librarian ruff passes.

### Previous Implementation Slice — 2026-05-23 — Dream/Librarian DL-1 COMPLETE
- ✅ Added local SQLite schema foundation for `knowledge_candidates` and `knowledge_review_items` inside `guardrails_lite/guardrails_db.py`; schema creation is idempotent and candidate indexes cover status, created_at, source_session_id, and proposed_title.
- ✅ Added `guardrails_lite/dream_queue.py` with candidate create/list/status-update/audit helpers, enum validation, JSON field round-trip handling, generated `dream_YYYYMMDD_<short uuid>` IDs, and safe defaults.
- ✅ Added `guardrails dream submit` CLI. The command requires title, summary, content-file, category, tags, source-agent, and source-type; it writes only to `knowledge_candidates` and returns `formal_knowledge_written=false`.
- ✅ Added DL-1 tests: `tests/test_dream_librarian_schema.py`, `tests/test_dream_queue.py`, and `tests/test_dream_cli.py`.
- ✅ Verification: targeted DL-1 tests passed (`16 passed`), scoped `git diff --check` passed, scoped `ruff check` passed, temp-dir CLI smoke passed, spec review PASS, code-quality review APPROVED after fixing executable-bit drift.
- ⚠️ Full `python -m pytest -q` is blocked by environment/pre-existing dependency issues before DL-1 tests collect: missing `onnxruntime` and `supabase.create_client` import failure.
- ⚠️ Post-edit Graphify rebuild is blocked by local environment/tooling: default Python cannot import `graphify`, while the documented `/home/zycas/miniconda3/bin/python` Graphify rebuild command timed out in this session.

### Previous Implementation Slice — 2026-05-18 20:20 CST
- ✅ Added report-only CLI/export: `guardrails b7 report --output <json>`.
- ✅ Scope is read-only/report-only over local SQLite knowledge rows; the command opens DB read-only and does not promote, merge, sync, or export public material.
- ✅ Implemented signals: normalized title duplicates, content-hash duplicates, low convergence, stale freshness, and DB-only/provenance gaps for missing raw/compiled/map handles.
- ✅ Safety flags in report: `report_only=true`, `auto_promote=false`, `destructive_merge=false`, `private_public_sync=false`, `remote_overwrite=false`.
- ✅ Report emits safe metadata only: IDs, titles, issue types, safe reasons, review-only recommended actions, counts, and handles; tests assert raw content is not emitted.
- ✅ Verification: targeted B7 tests passed, full pytest passed, CLI smoke JSON parsed, reviewer PASS.

---

## Current Sprint: Sprint 4H — B7 Multi-agent Writing and Convergence Workflow — DESIGN COMPLETE

### Goal
Define how many agents can contribute Guardrails knowledge without overwriting, duplicating, leaking, or polluting the shared brain: local SQLite/raw stays source of truth, Supabase stays sync target, and public Vault-for-LLM output stays allowlisted/redacted.

### Scope Delivered
1. Added `docs/multi_agent_convergence_workflow.md` as the B7 design contract.
2. Defined core invariants: local-first source of truth, drafts are not knowledge, no auto-promote, B6 privacy gates before boundary crossings, append-only audit, contradiction review, and public allowlisting.
3. Defined actor permissions for Arthur, Nancy coordinator, subagents, MCP add, cron, Feishu review, and sync scripts.
4. Defined canonical candidate/draft/review/promote/sync/public-export state model.
5. Defined metadata/audit requirements for source_agent, source_session, trust, content fingerprint, nearest existing IDs, reviewer, decision reason, and evidence handles.
6. Defined duplicate classes and merge/update policy: exact_same, same_lesson, same_topic_new_edge_case, near_duplicate_uncertain, and not_duplicate.
7. Defined contradiction, convergence, and freshness queue behavior without automatic content rewrite.
8. Defined safe Supabase sync boundaries and remote drift classes.
9. Defined public-safe Vault-for-LLM export criteria and manifest fields.
10. Added implementation backlog B7-T1 through B7-T8, with the first slice intentionally report-only.

### Verification Plan
```bash
git diff --check
# Expected: PASS, no whitespace errors.

/usr/bin/python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# Expected: run after docs change if graphify is available; classify missing module as tooling gap, not product regression.
```

### Remaining Follow-up
- Implement B7-T2/T3 report-only queue slice first.
- Add queue/audit schema or JSON contract only after reviewing current DB migration constraints.
- Keep `scripts/deduplicate_semantic.py --merge` as a report source, not the B7 merge engine.
- Harden Search QA with `expected_hit: false`, segment metrics, misses/regressions arrays, and snapshot metadata as part of B7-T8.

---

## Previous Sprint: Sprint 4G — CJK / Alias Keyword Retrieval — COMPLETED

### Goal
Fix keyword retrieval misses surfaced by the B3 internal QA baseline without weakening citation policy: score mixed-language candidates before final limiting, add conservative CJK Traditional/Simplified and domain-alias query expansion, and keep regression coverage explicit.

### Root Cause Findings
1. `search_keyword` currently orders SQL candidates by `trust DESC LIMIT ?` before Python relevance scoring, so high-trust weak matches can crowd out the actual best match.
2. `_tokenize` is brittle for mixed technical terms: hyphen/underscore/domain tokens are split into noisy fragments (`Vault-for-LLM`, `sqlite-vec`, `read_range`, `id-token`).
3. CJK tokenization uses non-overlapping 2–4 char chunks and lacks Traditional/Simplified normalization, so Simplified queries can pass only accidentally.
4. No domain alias layer exists for Phase B language pairs such as `對話回寫` ↔ `session writeback`, `草稿隊列` ↔ `draft queue`, and `隱私掃描` ↔ `privacy scanner`.
5. QA hygiene gap found: a redacted placeholder-like core QA case ID needed normalization; display-layer ellipsization was verified not to mutate the actual JSON IDs.

### Implementation Rules
- Add failing tests before changing search code.
- Keep expansion in query-time memory only; do not mutate stored knowledge rows.
- Keep alias dictionary narrow and Phase-B/domain specific.
- Do not change final citation policy; search citations remain navigation hints.

### Scope Delivered
1. Changed keyword search to gather the full SQL candidate pool before final Python relevance scoring, avoiding `trust DESC LIMIT` truncation of lower-trust exact matches.
2. Added deterministic mixed-language tokenization for hyphen/underscore technical identifiers (`Vault-for-LLM`, `sqlite-vec`, `read_range`, `id-token`) plus component tokens.
3. Added narrow Phase-B alias expansion for `對話回寫`/`session writeback`, `草稿隊列`/`draft queue`, `隱私掃描`/`privacy scanner`, and `內部百科`/`internal knowledge base`.
4. Added conservative Simplified→Traditional query normalization for the B4 CJK cases without mutating stored knowledge rows.
5. Hardened QA hygiene checks for stable unique core QA case IDs and fixed the script-style `tests/test_new_features.py` smoke test to use the active Python interpreter instead of assuming `conda` is on PATH.

### Final Metrics
```text
Search QA run complete
- total_cases: 14
- cases_with_results: 14
- top1_hits: 11
- topk_hits: 13
- mean_reciprocal_rank: 0.8452380952380951
- map_guidance_rate: 0.07142857142857142
- read_range_guidance_rate: 0.07142857142857142
- citation_policy_violations: 0

Before/after from B3 baseline:
- top1_hits: 4 -> 11 (+7)
- topk_hits: 5 -> 13 (+8)
- mean_reciprocal_rank: 0.32142857142857145 -> 0.8452380952380951 (+0.52380952381)
- citation_policy_violations: 0 -> 0 (0)
```

### Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python tests/test_new_features.py
# PASS: RESULTS: 26/26 PASSED, 0 FAILED

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# PASS: 80 passed, 2 warnings in 27.97s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python \
  -m guardrails_lite.guardrails_cli search-qa run \
  --qa-file qa/internal_guardrails_search_qa/core.json \
  --mode keyword \
  --limit 10 \
  --output /tmp/guardrails_b4_search_qa_final.json
# PASS: top1_hits=11; topk_hits=13; citation_policy_violations=0.

/home/zycas/miniconda3/envs/guardrails-lite/bin/python \
  -m guardrails_lite.guardrails_cli search-qa compare \
  --before /tmp/guardrails_b3_search_qa_baseline.json \
  --after /tmp/guardrails_b4_search_qa_final.json \
  --output /tmp/guardrails_b4_search_qa_final_compare.json
# PASS: top1 +7, topk +8, MRR +0.52380952381, citation policy unchanged.

/usr/bin/python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# PASS: graphify rebuilt graph.json and GRAPH_REPORT.md; graph.html skipped because graph exceeds viz node limit.
```

### Remaining Follow-up
- `negative-private-raw-transcript` remains a non-gating negative control; B7 or a later Search QA hardening sprint should implement first-class `expected_hit: false` evaluator semantics.
- The lower `map_guidance_rate` / `read_range_guidance_rate` reflects better direct retrieval of expected entries; B7 should continue improving Document Map coverage and convergence evidence rather than weakening citation policy.

---

## Current Sprint: Sprint 4F — Internal Search QA Dogfood Baseline — COMPLETED

### Goal
Create the internal dogfood Search QA artifact that turns Phase B retrieval/citation concerns into repeatable metrics before changing CJK tokenization, synonyms, ranking, or daily reporting.

### Scope Delivered
1. Added `docs/search_qa_metrics_plan.md` with:
   - internal QA schema,
   - baseline command and metrics,
   - before/after comparison protocol,
   - read-only daily reporting boundary,
   - B4 handoff cases,
   - implementation backlog.
2. Added `qa/internal_guardrails_search_qa/core.json` with 14 internal cases across B2 gaps, Phase B anchors, citation policy, privacy/release hygiene, CJK aliases, and one non-gating negative control.
3. Marked `negative-private-raw-transcript` as observational/non-gating until `expected_hit: false` evaluator semantics are implemented.
4. Kept citation policy strict: search citations remain navigation hints; final evidence still requires `read_range`.

### Baseline Metrics
```text
Search QA run complete
- total_cases: 14
- cases_with_results: 14
- top1_hits: 4
- topk_hits: 5
- mean_reciprocal_rank: 0.32142857142857145
- map_guidance_rate: 0.42857142857142855
- read_range_guidance_rate: 0.42857142857142855
- citation_policy_violations: 0
```

### Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python \
  -m guardrails_lite.guardrails_cli search-qa run \
  --qa-file qa/internal_guardrails_search_qa/core.json \
  --mode keyword \
  --limit 10 \
  --output /tmp/guardrails_b3_search_qa_baseline.json
# PASS: command exited 0; total_cases=14; citation_policy_violations=0.

/home/zycas/miniconda3/envs/guardrails-lite/bin/python \
  -m guardrails_lite.guardrails_cli search-qa compare \
  --before /tmp/guardrails_b3_search_qa_baseline.json \
  --after /tmp/guardrails_b3_search_qa_baseline.json
# PASS: all metric deltas are zero.

git diff --check
# PASS: no whitespace errors.
```

### Remaining Backlog
- Add segment-aware aggregate metrics to `search_qa.py`.
- Add real `expected_hit: false` support for negative controls.
- Expand `query_variants` into evaluated subcases.
- Add snapshot metadata: git SHA, DB path, QA hash, evaluator version.
- Add explicit misses/regressions arrays to JSON output.
- Add daily report renderer / cron only after Arthur approves schedule and destination.

---

## Previous Sprint: Sprint 4E — Search QA Set + Before/After Metrics — COMPLETED

### Goal
Create a deterministic Search QA Set and before/after metric runner so Guardrails search quality can be measured before changing ranking logic. This sprint is about observability and regression safety, not about making search ranking smarter yet.

### Baseline Findings
- Repository baseline: `/home/zycas/Guardrails-knowledge`, branch `main`, HEAD `72da9d9f0fabf514d30f66b2c05f500e57286be4`.
- Working tree before Sprint 4E implementation: `PROGRESS.md` modified by Sprint 4D documentation only; no search-quality code changes yet.
- Graphify baseline: 1081 nodes / 2320 edges / 72 communities.
- Existing search path:
  - `guardrails_lite/guardrails_search.py` owns keyword/vector/hybrid search, rerank, Document Map enrichment, and navigation hints.
  - `guardrails_lite/agent_policy.py` owns the behavior policy that keeps search citations as navigation-only and requires read-range citations for final answers.
  - `tests/test_search_map_integration.py`, `tests/test_agent_behavior_policy.py`, and `tests/test_guardrails_health_metrics.py` already cover the Document Map and citation-policy boundary.
- Current local DB health sample (`sample_limit=20`): total entries 424, entries with nodes 1, entries with claims 1, map coverage 0.24%, claim coverage 0.24%, citation coverage 0%, read_range over-limit violations 0. This local DB state differs from the latest synced Dashboard snapshot and confirms that QA metrics must read local SQLite as source of truth.
- Existing test baseline: `tests/test_search_map_integration.py tests/test_agent_behavior_policy.py tests/test_guardrails_health_metrics.py` passed (`16 passed in 3.27s`).

### Scope Delivered
1. Added `guardrails_lite/search_qa.py` as a pure Python local evaluator around `GuardrailsSearch`.
2. Added an extendable in-repo QA fixture at `tests/fixtures/search_qa_set.json`.
3. Added aggregate and per-case metrics:
   - `total_cases`
   - `cases_with_results`
   - `top1_hits`
   - `topk_hits`
   - `mean_reciprocal_rank`
   - `map_guidance_rate`
   - `read_range_guidance_rate`
   - `citation_policy_violations`
4. Added deterministic before/after snapshot comparison with JSON output and human-readable CLI formatting.
5. Added explicit CLI commands:
   - `guardrails search-qa run --qa-file --output --mode --limit --db-path`
   - `guardrails search-qa compare --before --after --output`
6. Added `tests/test_search_quality_metrics.py` with temporary SQLite fixtures and CLI smoke coverage; tests do not require network, Supabase, Ollama, or embedding providers.
7. Preserved citation policy boundaries: search result citations remain navigation hints only; the evaluator only measures guidance and flags suspicious final-citation labels.

### Review Findings Resolved
- Independent review found one blocking metric-correctness issue: `expected_title_substrings` originally used OR semantics, so `["citation", "policy"]` could falsely match `Citation Only` or `Policy Only`.
- Fixed by requiring all configured substrings to match the result title.
- Regression proof:
  - `Citation Policy Boundary` → `True`
  - `Citation Only` → `False`
  - `Policy Only` → `False`
- Re-review passed with no blocking or non-blocking findings.

### Non-Goals Preserved
- No search ranking tuning.
- No Supabase schema changes and no changes to `hermes_guardrails_health`.
- No citation policy weakening.
- No Dashboard frontend changes.
- No live DB `guardrails map build` as part of implementation; Document Map building only appears inside temporary test fixtures.

### Final Verification
```bash
# Targeted Search QA + policy + health regression
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_search_quality_metrics.py \
  tests/test_search_map_integration.py \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_health_metrics.py -q
# PASS: 22 passed in 4.02s

# Full Guardrails regression
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# PASS: 74 passed, 2 warnings in 48.70s

# CLI smoke on local DB and in-repo QA set
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli \
  search-qa run --qa-file tests/fixtures/search_qa_set.json \
  --output /tmp/guardrails-search-qa.json --mode keyword --limit 5
# PASS: total_cases=2, cases_with_results=2, top1_hits=1, topk_hits=2, citation_policy_violations=0

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli \
  search-qa compare --before /tmp/guardrails-search-qa.json \
  --after /tmp/guardrails-search-qa.json \
  --output /tmp/guardrails-search-qa-compare.json
# PASS: deterministic zero-delta comparison generated.

# Git hygiene
git diff --check
# PASS: no whitespace errors.

# Graphify after code changes
/usr/bin/python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# PASS: 1126 nodes, 2416 edges, 73 communities.
```

Independent worktree verification from detached HEAD `72da9d9` also passed after applying the targeted patch:

```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_search_quality_metrics.py \
  tests/test_search_map_integration.py \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_health_metrics.py -q
# PASS: 22 passed in 4.16s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# PASS: 74 passed, 2 warnings in 40.44s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli search-qa run ...
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m guardrails_lite.guardrails_cli search-qa compare ...
# PASS: CLI commands executed successfully in isolated worktree.

git diff --check
# PASS.
```

### Files Changed
- `guardrails_lite/search_qa.py`
- `guardrails_lite/guardrails_cli.py`
- `tests/test_search_quality_metrics.py`
- `tests/fixtures/search_qa_set.json`
- `PROGRESS.md`

## Previous Sprint: Sprint 4D — Dashboard Document Map Metrics Display — COMPLETED

### Goal
Render Guardrails Document Map health in the Hermes Dashboard frontend by reading Supabase `hermes_guardrails_health` snapshots and making coverage / citation / violation signals visible in the System Health tab.

### Scope Delivered
1. Kept local SQLite as the source of truth; Dashboard only reads synced Supabase snapshots.
2. Reused the deployed `hermes_guardrails_health` schema and removed the stale frontend `id` select assumption.
3. Renamed the Guardrails goal from generic `Guardrails 品質` to `Guardrails Document Map`.
4. Surfaced Document Map-specific metrics from existing schema slots:
   - `total_knowledge` → total Guardrails entries.
   - `convergence_rate` → Document Map coverage.
   - `avg_freshness` → citation navigation coverage.
   - `contradiction_count` → `read_range` over-limit violations.
   - `gap_count` → entries without nodes + entries without claims.
5. Added Guardrails-specific metric definitions in `GoalDetailSection.tsx`, explicitly stating that Dashboard metrics are observability only and final citations still require `read_range`.
6. Added a coverage sparkline and defensive percentage normalization so historical fraction rows (`0.94`) and percent rows (`94`) both render correctly.
7. Preserved citation policy boundaries: no search/final citation policy code was changed.

### Baseline Findings
- Dashboard stack: Vite + React + TypeScript under `/home/zycas/.hermes/dashboard/oa-cli/dashboard-src`.
- `useHermesData.ts` already queried `hermes_guardrails_health`, but only showed generic convergence / total / contradiction metrics and no Document Map-specific trend or definitions.
- `GoalDetailSection.tsx` already supported goal-specific metric definitions and default sparkline charts; Sprint 4D reused that existing UI pattern.
- Live Supabase rows include older fractional snapshots (`convergence_rate` around `0.94`), so the frontend normalizes both fraction and percent formats.

### Final Verification
```bash
# Dashboard TypeScript + production build
npm run build
# PASS: tsc + Vite build passed; existing large chunk warning only.

# Supabase read-path smoke
node --input-type=module <supabase hermes_guardrails_health select smoke>
# PASS: 3 rows returned; latest 2026-05-08 total_knowledge=368, convergence_rate=0.940217, avg_freshness=0.861, gap_count=22.

# HTTP + browser smoke
curl -I http://localhost:3460/
# PASS: HTTP/1.1 200 OK
# Browser DOM confirmed Guardrails Document Map card and detail render 94% coverage, 86% citation coverage, 368 entries, 0 read_range over-limit, 22 Map/Claim gaps.
# Browser console: no JavaScript errors.

# Guardrails backend regression
conda run -n guardrails-lite python3 -m pytest -q
# PASS: 68 passed, 2 warnings in 48.35s.

# Git hygiene
git diff --check
# PASS for Dashboard targeted diff and Guardrails PROGRESS.md.

# Graphify
/usr/bin/python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# PASS: 1081 nodes, 2320 edges, 72 communities.
```

Independent worktree verification also passed:

```bash
# Dashboard source patch applied to detached worktree from HEAD 62ac4aac
npm ci
npm run build
# PASS: tsc + Vite build passed; npm audit reported existing dependency vulnerabilities, not introduced by this source patch.

# Guardrails PROGRESS.md patch applied to detached worktree from HEAD 72da9d9
conda run -n guardrails-lite python3 -m pytest -q
# PASS: 68 passed, 2 warnings in 41.95s.
```

### Files Changed
- `/home/zycas/.hermes/dashboard/oa-cli/dashboard-src/src/hooks/useHermesData.ts`
- `/home/zycas/.hermes/dashboard/oa-cli/dashboard-src/src/types.ts`
- `/home/zycas/.hermes/dashboard/oa-cli/dashboard-src/src/components/GoalDetailSection.tsx`
- `/home/zycas/.hermes/dashboard/oa-cli/src/oa/dashboard/index.html` and hashed built asset from `npm run build`
- `/home/zycas/Guardrails-knowledge/PROGRESS.md`

## Previous Sprint: Sprint 4C — Dashboard Health Integration — COMPLETED

### Goal
Expose Document Map health to the Hermes Dashboard by collecting local SQLite coverage metrics and upserting a daily snapshot into Supabase `hermes_guardrails_health`, without changing the Dashboard frontend or weakening the Sprint 3 citation policy harness.

### Scope Delivered
1. Added `guardrails_lite/guardrails_health.py` with a small, testable local SQLite collector for:
   - `map_coverage = entries_with_nodes / total_entries`
   - `claim_coverage = entries_with_claims / total_entries`
   - `citation_coverage = sampled_search_results_with_best_span / sampled_search_results`
   - `read_range_over_limit_violations` from local Document Map node bounds.
2. Added `scripts/sync_to_supabase.py --health` / `--guardrails-health` with `--health-sample-limit` to write one daily Dashboard snapshot.
3. Preserved SQLite as source of truth; Supabase remains a Dashboard/read target only.
4. Reused the existing deployed `hermes_guardrails_health` schema instead of adding unverified columns:
   - `total_knowledge = total_entries`
   - `convergence_rate = map_coverage * 100`
   - `avg_freshness = citation_coverage * 100`
   - `contradiction_count = read_range_over_limit_violations`
   - `gap_count = entries_without_nodes + entries_without_claims`
5. Added fake-client and local SQLite tests in `tests/test_guardrails_health_metrics.py`; no real network/Supabase access is required.
6. Preserved Sprint 3/4B behavior harness: search citations remain navigation hints only; final citations must come from local or remote `read_range`.

### Guardrails Observed
- Document-first: this progress file was updated before the implementation slice.
- Schema-drift control: the first review found that deployed `hermes_guardrails_health` has no `id` column; the writer now upserts by `check_date` instead of the generic `id`-based helper.
- Surgical scope: no Dashboard frontend changes and no citation policy relaxation.
- Push safety: verification included an independent worktree checkout with the same patch applied before commit.

### Final Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_guardrails_health_metrics.py \
  tests/test_sprint4a_document_map_sync.py \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_mcp_map.py \
  tests/test_search_map_integration.py -q
# 30 passed in 5.60s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# 68 passed, 2 warnings in 41.29s

git diff --check
# passed

/home/zycas/miniconda3/bin/python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# 1081 nodes, 2320 edges, 72 communities
```

Independent worktree verification also passed from detached HEAD `0076424` after applying the uncommitted patch:

```bash
git worktree add --detach /tmp/guardrails-s4c-worktree-verify HEAD
git apply --whitespace=error-all /tmp/guardrails-s4c.patch
git diff --check
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_guardrails_health_metrics.py \
  tests/test_sprint4a_document_map_sync.py \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_mcp_map.py \
  tests/test_search_map_integration.py -q
# 30 passed in 5.60s
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# 68 passed, 2 warnings in 41.29s
```

## Previous Sprint: Sprint 4B — Remote Document Map Read Path + Supabase DDL — COMPLETED

### Goal
Complete the remote Document Map loop by adding Supabase DDL/migration support for synced map tables, exposing a remote MCP read path backed by `guardrails_knowledge_nodes` / `guardrails_knowledge_claims`, and extending the Sprint 3 citation policy harness to cover remote trace events.

### Scope Delivered
1. Added `supabase/migrations/20260509_document_map_sprint4b.sql` for `guardrails_knowledge_nodes` and `guardrails_knowledge_claims`, including UUID primary keys, natural-key uniqueness, indexes, RLS, `agents_rw` policies, and source-of-truth comments.
2. Added remote MCP tools:
   - `guardrails_remote_map_show(knowledge_id, compact=false)` reads synced Supabase nodes and returns remote `read_range` next actions.
   - `guardrails_remote_read_range(knowledge_id, node_uid, line_start, line_end)` reads bounded remote ranges and returns fixed citations.
3. Preserved local SQLite as canonical source; Supabase remains a sync/read target only.
4. Extended deterministic policy tests so remote traces are accepted only when they follow `search → remote_map_show → remote_read_range → final answer with read_range citation`.
5. Kept Sprint 4A sync behavior backward-compatible: `scripts/sync_to_supabase.py --document-map` remains opt-in.
6. Added fake Supabase tests; no real network/Supabase access is required for test coverage.

### Guardrails Observed
- Surgical scope: no Dashboard metrics or repo hygiene in this sprint.
- Citation policy preserved: search citations remain navigation hints only; final citations must come from local or remote `read_range`.
- Review agent requested one fix: remote claim fallback must hash the returned claim content, not reuse node `content_hash`. Fixed with regression coverage.

### Final Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_mcp_map.py \
  tests/test_search_map_integration.py \
  tests/test_sprint4a_document_map_sync.py -q
# 24 passed in 3.67s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# 62 passed, 2 warnings in 38.88s

git diff --check
# passed
```

Graphify was rebuilt after code changes:

```bash
/home/zycas/miniconda3/bin/python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# 1031 nodes, 2170 edges, 73 communities
```

## Previous Sprint: Sprint 4A — Supabase Document Map Sync + Compile Hook — COMPLETED

### Goal
Keep Document Map rows fresh on local compile and add an explicit Supabase sync path for `knowledge_nodes` / `knowledge_claims`, while preserving SQLite as source of truth and the Sprint 3 citation policy harness.

### Scope Delivered
1. Added compile hook in `guardrails_lite/guardrails_compile.py`: successful non-dry-run new/update entries now refresh Document Map rows via `build_document_map_for_entry()`.
2. Kept `dry_run` and unchanged/skipped entries side-effect free for Document Map rebuilds.
3. Extended duplicate cleanup to delete `knowledge_claims` and `knowledge_nodes` before removing duplicate `knowledge` rows, preventing orphan map rows.
4. Added `scripts/sync_to_supabase.py --document-map` to sync SQLite `knowledge_nodes` / `knowledge_claims` into Supabase tables `guardrails_knowledge_nodes` / `guardrails_knowledge_claims`.
5. Document Map sync uses natural-key select/update/insert upsert: nodes by `(knowledge_id, node_uid)`, claims by `(knowledge_id, claim_uid)`.
6. Added fake-client tests in `tests/test_sprint4a_document_map_sync.py`; no network is required for sync tests.

### Guardrails Observed
- Document-first: this progress note was updated before code changes.
- Minimal scope: only sync, compile hook, and targeted tests were changed.
- Backward compatibility: default Supabase knowledge sync behavior remains unchanged; `--document-map` is opt-in.
- Local-first: SQLite remains source of truth; Supabase is a sync target only.
- Citation policy: Sprint 3 behavior harness remains untouched and passing.

### Final Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_mcp_map.py \
  tests/test_search_map_integration.py \
  tests/test_sprint4a_document_map_sync.py -q
# 16 passed in 3.57s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# 54 passed, 2 warnings in 38.81s

git diff --check
# passed
```

Graphify was updated after verification. The `guardrails-lite` conda env cannot import `graphify`; use base conda Python for the AGENTS.md rebuild command:

```bash
/home/zycas/miniconda3/bin/python -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
# 987 nodes, 1945 edges, 71 communities
```

### Review Notes
- Review agent verdict: APPROVED.
- Follow-up for Sprint 4B / operations: create Supabase DDL for `guardrails_knowledge_nodes` and `guardrails_knowledge_claims`, including unique constraints on `(knowledge_id,node_uid)` and `(knowledge_id,claim_uid)`.

## Previous Sprint: Sprint 3 — Agent Behavior Loop + Citation Policy Harness — COMPLETED

### Goal
Ensure external agents do not merely have Document Map tools available, but are guided and tested to follow the intended reading loop:

```text
guardrails_search → guardrails_map_show → guardrails_read_range → final answer with read_range citation
```

### Scope Delivered
1. Added deterministic agent behavior policy harness in `guardrails_lite/agent_policy.py`.
2. Added `tests/test_agent_behavior_policy.py` to reject unsupported traces:
   - citation-free answers when citation is required;
   - invented citations;
   - search-only citation claims;
   - `read_range` without prior `map_show`;
   - mismatched `knowledge_id` loops.
3. Treated search-result citations as navigation hints only; final answer citations must come from `guardrails_read_range`.
4. Added additive `next_action` / `next_actions` metadata in search/map/read_range payloads.
5. Added opt-in `compact=true` support for search and map payloads without changing default output shapes.
6. Normalized MCP failure responses with `failure_mode` and actionable `next_action` metadata while preserving existing `error` values.
7. Updated `docs/document_map_upgrade_plan.md` with the Sprint 3 agent behavior contract.
8. Updated `/home/zycas/.hermes/skills/guardrails/SKILL.md` with Sprint 3 citation policy discipline.

### Guardrails Observed
- Document-first: this file was updated before feature implementation.
- TDD: behavior/payload tests were added for the Sprint 3 slice.
- Surgical changes only: no Supabase sync, compile hook, dashboard metrics, or unrelated refactors were included.
- Backward compatibility: default payload shapes were preserved; compact mode is opt-in.

### Final Verification
```bash
/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest \
  tests/test_agent_behavior_policy.py \
  tests/test_guardrails_mcp_map.py \
  tests/test_search_map_integration.py -q
# 12 passed in 2.04s

/home/zycas/miniconda3/envs/guardrails-lite/bin/python -m pytest -q
# 50 passed, 2 warnings in 36.71s

git diff --check
# passed
```

Graphify was updated after verification:

```bash
/home/zycas/miniconda3/bin/graphify update .
# 947 nodes, 1736 edges, 71 communities
```

Final commit is performed after this verification block.

## Current Maintenance Pass: Full Test Environment + Repo Hygiene + Audit — COMPLETED

### Goal
Restore the project to a cleaner post-Sprint-2 working state before Sprint 3 by:
1. Auditing current repo/test/documentation state.
2. Reproducing and fixing full `pytest -q` collection blockers when they are environment/dependency related.
3. Classifying and resolving non-Sprint untracked files without mixing unrelated work into Sprint 2.

### Guardrails
- Do not start Sprint 3 feature work in this pass.
- Do not hide real product test failures behind dependency changes.
- Do not delete untracked files without evidence of what they contain.
- Keep Sprint 2 commit `970784a Add document map MCP tools` as the baseline.

### Results

#### Audit ✅
- Sprint 2 baseline remains `970784a Add document map MCP tools`.
- Graphify report was reviewed after Sprint 2; main hubs remain `GuardrailsDB`, `GuardrailsSearch`, `EmbeddingProvider`, `GuardrailsGraph`, and Document Map MCP helpers.
- Branch state observed during audit: local `main` is ahead of and behind `origin/main`; do not push/merge this maintenance commit until a sync/rebase strategy is chosen.

#### Full test environment ✅
- The earlier full-suite blockers were environment/dependency issues, not Sprint 2 product regressions.
- Correct interpreter for verification is:
  `/home/zycas/miniconda3/envs/guardrails-lite/bin/python`
- Full suite now passes with the direct interpreter:
  `45 passed`.
- Caveat: `conda run -n guardrails-lite python` can be polluted by the previously activated `/tmp/research-scrapling-tinyfish/venv-scrapling` environment in this shell. Use the direct interpreter path above for reliable verification until shell environment state is reset.

#### Untracked file classification ✅
- `_knowledge_base/` contains local research notes (`ai-website-cloner`, `scrapling-tinyfish`, `siami-reading-ghost-fields`) unrelated to Sprint 2 source changes. It is now ignored as local research/scratch material.
- `scripts/cross_validate_cloud_only.py` is a local cron-style wrapper around `scripts/cross_validate.py`. It compiles, but changes runtime behavior (`apply=True`, cloud-only, model/timeouts) and needs a separate operational review before becoming project source.
- `scripts/guardrails_gap_scanner.py` is a local daily gap-scanner draft. It compiles, but has hard-coded local paths and the docstring mentions Telegram delivery while the current implementation only prints. It needs a separate operational review before becoming project source.
- The two draft scripts are now ignored explicitly to keep Sprint maintenance commits clean.

#### Final verification ✅
- `git diff --check` passed.
- Targeted Document Map suite passed: `41 passed in 23.33s`.
- Script syntax check passed for `scripts/cross_validate.py`, `scripts/cross_validate_cloud_only.py`, and `scripts/guardrails_gap_scanner.py`.
- Full suite passed with direct interpreter: `45 passed in 33.44s`.
- Graphify was not rebuilt in this maintenance commit because no code files changed; only `.gitignore` and `PROGRESS.md` changed.

## Previous Sprint: Sprint 2 (B/E1) — COMPLETED

### Goal
Make Guardrails usable as an agent brain: search results point to Document Map spans, and MCP clients can inspect structure before reading bounded line ranges with fixed citations.

### Scope Delivered

#### B1 — Search result enrichment ✅
- Modified `guardrails_lite/guardrails_search.py`.
- Search results are enriched with Document Map metadata when available:
  - `node_uid`
  - `path`
  - `heading`
  - `line_start`
  - `line_end`
  - `best_span`
  - `best_node`
  - `citation`
  - `recommended_next_tool`
- Backward compatibility preserved: entries without populated map rows still return normally with map fields absent/empty.

#### B2 — MCP tools ✅
- Modified `guardrails_lite/guardrails_mcp.py`.
- Added MCP-callable tools:
  - `guardrails_map_show(knowledge_id)` — returns entry metadata and section structure from `knowledge_nodes`.
  - `guardrails_read_range(knowledge_id, node_uid, line_start, line_end)` — returns bounded line-numbered source content.
- Implementation remains local-first; no Supabase schema changes in Sprint 2.

#### B3 — Range limit and citation guard ✅
- `guardrails_read_range` defaults to maximum 80 lines.
- Over-limit requests return `range_too_large` and ask the caller to split ranges.
- Successful reads include a fixed citation string from the tool, e.g. `#405 Title L1-L8`.
- Agents should not invent citations; citations come from `guardrails_read_range` output.

#### E1 — Guardrails skill update ✅
- Updated `/home/zycas/.hermes/skills/guardrails/SKILL.md`.
- Added reading discipline:
  - For long knowledge entries: `search → guardrails_map_show → guardrails_read_range`.
  - Answers based on encyclopedia content should prefer `#id + line range` citations.
- Corrected CLI fallback syntax:
  - CLI: `guardrails map read <knowledge_id> --lines 12-36`
  - MCP: `guardrails_read_range` supports `node_uid` or `line_start` + `line_end`.

### Verification Results

#### Automated tests ✅
```bash
conda run -n guardrails-lite python -m pytest \
  tests/test_document_map.py \
  tests/test_document_map_cli.py \
  tests/test_search_map_integration.py \
  tests/test_guardrails_mcp_map.py -q
```

Result: `41 passed in 6.81s`

#### Manual CLI verification ✅
```bash
conda run -n guardrails-lite guardrails map show 405
conda run -n guardrails-lite guardrails map read 405 --lines 1-8
```

Verified output includes line-numbered source content and citation:
`#405 PageIndex 的可借鑑價值：Document Map + Tool-gated Reading L1-L8`

#### Manual MCP handler verification ✅
Direct `handle_tool_call()` checks passed for:
- `guardrails_map_show` with `knowledge_id=405`
- `guardrails_read_range` with `knowledge_id=405, line_start=1, line_end=8`
- `guardrails_read_range` with `knowledge_id=405, node_uid="摘要-1"`

Verified outputs include:
- tool registration names: `guardrails_map_show`, `guardrails_read_range`
- `nodes[]` from Document Map
- bounded `content`
- `content_hash`
- fixed `citation`
- node metadata when reading by `node_uid`

#### Manual search enrichment verification ✅
Keyword searches for mapped entry #405 were verified:
- Query: `PageIndex`
- Query: `先看全局地圖`

Returned enriched fields include:
- `node_uid='摘要-1'`
- `path='摘要'`
- `line_start=3`
- `line_end=3`
- `best_span='L3-L3'`
- `citation='#405 PageIndex 的可借鑑價值：Document Map + Tool-gated Reading L3-L3'`
- `recommended_next_tool='guardrails_read_range'`

Entries without map rows were also observed to remain backward-compatible with empty map fields.

#### Diff hygiene ✅
- `git diff --check` passed with no whitespace errors.

#### Full test suite note ⚠️
Full `pytest -q` was attempted but blocked during collection by existing environment dependencies unrelated to Sprint 2:
- `ModuleNotFoundError: No module named 'onnxruntime'` in `tests/test_e2e.py`
- `ModuleNotFoundError: No module named 'yaml'` in `tests/test_lite.py` and `tests/test_new_features.py`

Sprint 2 targeted tests pass.

#### Graphify update ✅
The AGENTS.md Python import command failed because the active Python environment cannot import `graphify` as a module. Correct current CLI path was found at `/home/zycas/miniconda3/bin/graphify`; code graph was updated with:

```bash
/home/zycas/miniconda3/bin/graphify update .
```

Result:
- `785 nodes`
- `1434 edges`
- `61 communities`
- Updated `graphify-out/graph.json` and `graphify-out/GRAPH_REPORT.md`

### Files Changed

#### Modified
- `guardrails_lite/guardrails_search.py`
- `guardrails_lite/guardrails_mcp.py`
- `/home/zycas/.hermes/skills/guardrails/SKILL.md`

#### Added
- `PROGRESS.md`
- `tests/test_search_map_integration.py`
- `tests/test_guardrails_mcp_map.py`

#### Preserved / Not Sprint 2
The following pre-existing untracked files were not touched:
- `_knowledge_base/`
- `scripts/cross_validate_cloud_only.py`
- `scripts/guardrails_gap_scanner.py`

### Next Sprint
Sprint 3 should focus on agent-loop behavior:
1. Ensure external agents actually follow `search → map_show → read_range`.
2. Add integration examples or harness checks that reject unsupported, citation-free answers.
3. Decide whether MCP result payloads should be more compact for high-volume agent use.

Sprint 4 remains the Supabase/schema synchronization phase and was intentionally not started in Sprint 2.
