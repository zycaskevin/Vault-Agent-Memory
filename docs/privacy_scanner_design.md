# B6 — Privacy Scanner Design

> **For Hermes:** This is the B6 design contract for internal Guardrails dogfood. It turns the B1 writeback governance privacy preflight into a shared scanner boundary for manual add, MCP add, session capture, compile, and Supabase sync. It is a design/spec artifact; implementation is still pending.

**Last updated:** 2026-05-18 01:51 CST

**Phase:** Phase B / B6 — privacy scanner

**Status:** Design complete, implementation pending

**Depends on:** `docs/session_writeback_governance.md`

**Next after this:** B5 session capture draft queue design

---

## 0. Goal

Guardrails needs one shared privacy scanner so every write path answers the same question before data becomes durable:

```text
candidate / raw entry / draft / compile output / sync payload
  → scan
  → clear | redact_required | private_only | blocked
  → audit
  → continue only through the allowed path
```

B6 is not about legal/compliance guarantees. It is a best-effort engineering guardrail that prevents obvious secrets, PII, CRM data, raw personal life material, and internal credentials from entering normal searchable knowledge.

---

## 1. Core invariants

1. **Raw secrets are never stored.**
   - Tokens, private keys, cookies, `.env` values, `.pypirc` values, and bearer credentials are always `blocked` or redacted before any draft storage.

2. **Client/customer data never enters shared knowledge.**
   - Medical aesthetics CRM context, names tied to phone/email/treatment/payment, and reply-audit content must remain private or be transformed into general rules.

3. **Arthur private life raw material is not shared memory.**
   - Only general collaboration rules or safety boundaries may be promoted after review.

4. **All write entry points use the same scanner.**
   - CLI add, MCP add, capture import, compile, sync, and future cron/session capture must call the shared scanner module or a wrapper around it.

5. **Override cannot store secrets.**
   - Arthur can approve exact scope for private/local handling, but raw secrets still cannot be stored or synced.

6. **Audit stores decisions, not sensitive raw content.**
   - Audit logs may record pattern names, counts, outcome, actor, and reason; they must not preserve secret values or raw private stories.

---

## 2. Module boundary

Recommended module:

```text
guardrails_lite/privacy_scanner.py
```

The module should be pure Python, deterministic, and usable without network access.

### 2.1 Public API sketch

```python
@dataclass
class PrivacyFinding:
    kind: str                    # secret|pii|crm|life_profile|internal_credential|internal_path|unknown
    severity: str                # low|medium|high|critical
    action: str                  # allow|redact|private_only|block
    start: int
    end: int
    preview: str                 # redacted snippet only
    rule_id: str
    message: str

@dataclass
class PrivacyScanResult:
    outcome: str                 # clear|redact_required|private_only|blocked
    findings: list[PrivacyFinding]
    redacted_text: str
    audit_summary: dict
    can_store_draft: bool
    can_promote_shared: bool
    can_sync_remote: bool


def scan_text(text: str, *, context: dict | None = None) -> PrivacyScanResult:
    ...


def scan_entry(entry: dict, *, context: dict | None = None) -> PrivacyScanResult:
    ...
```

### 2.2 Context fields

Callers should pass context so the scanner can apply stricter rules for risky paths:

```yaml
entry_point: "cli_add|mcp_add|capture_import|compile|sync|cron|manual_review"
source_channel: "feishu|cli|mcp|cron|telegram|local|unknown"
intended_visibility: "shared|private_draft|remote_sync|unknown"
contains_customer_context: true|false|unknown
contains_life_profile: true|false|unknown
actor: "nancy|subagent|cron|arthur|unknown"
override_requested: true|false
```

Rule: if `intended_visibility=shared` or `remote_sync`, apply the strictest policy.

### 2.3 `scan_entry` field coverage

`scan_entry()` must not scan only the body. Leak paths include titles, source refs, and audit notes.

Minimum fields to scan recursively:

| Field group | Examples | Why it matters |
|---|---|---|
| identity fields | `title`, `proposed_title`, `slug` | customer names or private descriptors can leak through titles |
| summaries | `summary`, `frontmatter.summary` | summaries are commonly indexed and synced |
| tags/categories | `tags`, `category`, `layer` | tags can include client names or internal project aliases |
| body/content | `content`, `content_draft`, `body`, `markdown` | primary sensitive text surface |
| source metadata | `source`, `source_refs`, `source_session_id`, URLs | tokenized URLs, private paths, message links |
| review/audit notes | `decision_reason`, `audit_log.note`, `reviewer_note` | reviewers may paste raw findings by accident |
| sync payload fields | any outgoing JSON/row field | remote boundary must scan the final payload shape |

Rules:

1. Nested dict/list/string fields are scanned recursively.
2. Non-string values are converted only for metadata classification, not for leaking raw binary/blob content.
3. `redacted_text` must preserve the same field structure where possible.
4. If a field cannot be safely redacted while preserving meaning, escalate to `private_only` or `blocked`.
5. After applying redactions, re-scan the redacted structure before storage or sync.

### 2.4 Finding aggregation and precedence

Multiple findings must resolve deterministically.

Outcome precedence:

```text
blocked > private_only > redact_required > clear
```

Severity precedence:

```text
critical > high > medium > low
```

Aggregation rules:

1. Any unredacted critical secret finding makes the result `blocked`.
2. Any CRM/customer or Arthur life-profile raw finding makes the result at least `private_only` unless safely transformed into a general rule.
3. Mixed findings choose the strictest outcome; for example `secret + CRM` is `blocked` until the secret is removed, then still `private_only` unless CRM raw content is transformed.
4. Redaction is successful only if a second scan finds no high/critical shared-visibility findings.
5. Allowlist matches can downgrade only the specific documented placeholder; they cannot downgrade a real value elsewhere in the same file.

---

## 3. Outcome model

| Outcome | Meaning | Draft storage | Shared promote | Supabase sync |
|---|---|---:|---:|---:|
| `clear` | no sensitive findings | yes | yes after B1 review | yes after local verification |
| `redact_required` | useful content but sensitive values must be removed | only redacted | only redacted + review | only redacted |
| `private_only` | useful but should not be shared | yes, private draft only | no, unless transformed | no raw sync |
| `blocked` | too risky or not valuable enough | no raw content; audit only | no | no |

Promotion gate:

```text
can_promote_shared = outcome in {clear, redact_required}
                     AND redacted_text has no high/critical findings
                     AND B1 classification is shared_knowledge
                     AND review decision is promote/merge
```

---

## 4. Finding categories and default actions

### 4.1 Secrets and credentials

Default: `blocked` for raw values; `redact_required` only if the surrounding content is independently useful.

Patterns / examples:

- GitHub tokens: `ghp_...`, `github_pat_...`, `gho_...`, `ghu_...`, `ghs_...`, `ghr_...`
- PyPI tokens: `pypi-...`
- OpenAI-style keys: `sk-...`, `sk-proj-...`
- Bearer authorization headers with non-placeholder values
- Private keys: `-----BEGIN ... PRIVATE KEY-----`
- `.env`, `.pypirc`, cookie/session header values
- long base64/hex strings near key/token/password labels

Action rules:

| Case | Action |
|---|---|
| raw credential value present | `blocked` or `redact_required` |
| docs mention placeholder only, e.g. `<TOKEN>` | allow if clearly placeholder |
| scanner docs list forbidden patterns | allow as documentation self-match after exact-line classification |
| real private key block | `blocked` |

Important: documentation examples are common false positives. The scanner must distinguish placeholder/pattern documentation from usable secret values.

### 4.2 Personal identifiable information (PII)

Default: `redact_required` or `private_only` depending on context.

Patterns / examples:

- emails
- phone numbers
- addresses
- government IDs/passports
- payment identifiers
- full names tied to contact details

Action rules:

| Case | Action |
|---|---|
| isolated example email like `user@example.com` | allow or low severity |
| real-looking email/phone in session capture | `redact_required` |
| name + phone/email/address | `private_only` or `blocked` |
| customer context with treatment/payment details | `private_only` or `blocked` |

### 4.3 Medical aesthetics / CRM data

Default: `private_only`; `blocked` if raw customer identifiers are present.

High-risk markers:

- customer name + treatment
- phone/email + appointment/treatment/payment
- material cost, commission, net profit tied to a customer
- reply audit involving identifiable customer context
- before/after cases with identifiable traits

Allowed transformed knowledge:

```text
CRM reply audits should store only generalized workflow rules and anonymized validation patterns; do not store customer raw messages or treatment records in shared Guardrails knowledge.
```

### 4.4 Arthur life-profile raw material

Default: `private_only` or `blocked`; only transformed collaboration rules can become shared.

High-risk markers:

- marriage/family/children raw narrative
- intimate emotional messages
- legal/personal conflict raw details
- medical/body/private plans not needed for system behavior

Allowed transformed knowledge examples:

- `When helping Arthur with life-profile work, prioritize long-term happiness, dignity, freedom, and safety over short-term appeasement.`
- `Do not store raw personal narrative in shared knowledge; extract only stable collaboration boundaries.`

### 4.5 Internal environment and local credentials

Default: `redact_required` for secrets; `private_only` for sensitive internal topology.

Examples:

- private dashboard URLs with admin paths
- local file paths containing secrets
- production tokens, app IDs, channel IDs when tied to credentials
- service account JSON paths
- database passwords

Nuance:

- Some internal paths are stable operational knowledge and already injected as private memory; they can remain local/private.
- Public/shared entries should avoid credentials and reduce path detail unless required for a reusable SOP.

---

## 5. Redaction preview rules

The scanner should produce a safe preview, not silently mutate content without evidence.

Redaction format:

| Finding | Replacement |
|---|---|
| token/key | `[REDACTED_SECRET:rule_id]` |
| private key block | `[REDACTED_PRIVATE_KEY]` |
| email | `[REDACTED_EMAIL]` |
| phone | `[REDACTED_PHONE]` |
| customer name | `[REDACTED_CUSTOMER]` |
| address | `[REDACTED_ADDRESS]` |
| raw personal story block | `[REDACTED_PRIVATE_CONTEXT]` |

Preview requirements:

1. Preserve enough surrounding context to review whether the entry is still useful.
2. Never include full matched secret values in logs or audit.
3. Include finding counts and rule IDs.
4. If redaction destroys the meaning, outcome should be `private_only` or `blocked`, not `clear`.

---

## 6. Entry-point integration

### 6.1 CLI `guardrails add`

Manual add is curated, but still must scan.

Flow:

```text
guardrails add
  → scan_text / scan_entry
  → if clear: continue
  → if redact_required: show preview; require confirm or `--apply-redactions`
  → if private_only: require explicit `--private-draft` or abort
  → if blocked: abort; write audit only
```

Recommended flags:

- `--privacy-scan` default on
- `--apply-redactions`
- `--private-draft`
- `--override-with-audit "reason"`
- `--no-privacy-scan` should be unavailable or developer-only for tests, not normal use

### 6.2 MCP add

MCP write tools are high-risk because agents can call them during conversation loops.

Rules:

1. Public MCP schema should require routing-critical context: `source_channel`, `intended_visibility`, `source_session_id` when session-derived.
2. Formal `guardrails_add` may only accept curated shared knowledge.
3. Session-derived material should go to future draft tool, not formal add.
4. If scanner returns `redact_required`, MCP tool returns a preview and asks for review; it must not auto-promote.
5. Final assistant answer cannot claim “已寫入” unless same-turn write evidence includes ID/path + scanner outcome.

### 6.3 Capture import / future B5 draft queue

Default mode is dry-run candidate extraction.

Flow:

```text
session transcript
  → extract candidates
  → scan each candidate
  → blocked candidates: audit summary only
  → private_only: private draft metadata + redacted content only
  → clear/redact_required: pending shared draft after dedupe
```

Rules:

- Full transcripts should not be stored as normal knowledge.
- Source refs can point to session IDs or safe handoff paths, not raw secret-bearing URLs.
- Captured drafts never enter normal search until promoted.

### 6.4 Compile

Compile is a second safety net, not the first gate.

Rules:

- Scan raw entry body and frontmatter before generating compiled/AAAK output.
- If high/critical finding appears in raw, fail compile for that entry.
- If docs self-match scanner examples, allow only when classified as scanner documentation.
- Compile errors should show rule IDs and redacted previews, not matched secret values.

### 6.5 Sync to Supabase

Sync is the remote boundary and should be stricter than local draft storage.

Rules:

- Scan payload before upsert.
- `private_only` and `blocked` content must not sync.
- `redact_required` may sync only after redactions are applied and verified.
- Sync report must include privacy scan counts.
- If local DB contains legacy risky entries, sync should fail those entries and produce a remediation list instead of silently uploading.

### 6.6 Cron jobs

Cron can scan and report; it must not override.

Rules:

- session scan cron can produce candidate reports,
- privacy scanner cron can produce remediation queues,
- cron cannot auto-promote or auto-override,
- empty/no-finding reports may stay silent,
- non-empty high/critical findings should be delivered to the configured review channel.

---

## 7. Override and audit policy

Overrides are only for non-secret private/internal material. They cannot store raw credentials.

Required fields:

```yaml
override_id: "override_YYYYMMDD_HHMMSS_slug"
actor: "arthur|nancy|manual_reviewer"
entry_point: "cli_add|mcp_add|capture_import|compile|sync"
original_outcome: "redact_required|private_only|blocked"
final_decision: "allow_redacted|private_local_only|discard|block"
reason: "Specific reason"
scope: "Exact file/draft/entry title"
expires_at: "optional"
created_at: "timestamp"
```

Policy:

| Original outcome | Override allowed? | Maximum allowed result |
|---|---:|---|
| `redact_required` | yes | redacted shared or private |
| `private_only` | yes | private/local only, or transformed shared rule |
| `blocked` due secret | no | block |
| `blocked` due no long-term value | yes | discard reason only |

Audit logs must store redacted previews and rule IDs only.

Cron-specific rule: cron jobs cannot approve overrides. If a cron run detects a case that appears override-worthy, it may create an audit-only review request with redacted preview, but the final override actor must be `arthur`, `nancy`, or another explicit manual reviewer.

---

## 8. Configuration

Project-level config can tune rules but not weaken core blocks.

Recommended file:

```text
privacy_scanner_rules.yaml
```

Recommended shape:

```yaml
version: 1
strict_remote_sync: true
allow_documentation_self_matches: true
blocked_patterns:
  - id: github_token
    severity: critical
    action: block
redaction_patterns:
  - id: email
    severity: medium
    action: redact
private_only_patterns:
  - id: arthur_life_profile
    severity: high
    action: private_only
allowlist:
  - id: docs_placeholder_email
    pattern: "user@example.com"
    scope: "documentation_only"
```

Hard rule: config may add allowlists for documented placeholders and test fixtures, but may not allow raw secrets to sync remotely.

---

## 9. Review UX

Scanner output should be human-reviewable.

CLI/MCP review summary:

```text
Privacy scan: redact_required
Findings:
- critical secret.github_token x1 → redacted
- medium pii.email x2 → redacted
Allowed paths:
- store redacted draft: yes
- promote shared: requires review
- sync remote: yes after redaction
```

For Feishu review reports, show:

1. candidate title,
2. outcome,
3. finding categories/counts,
4. redacted preview,
5. recommended action,
6. exact next command or button/action if implemented later.

Never send raw matched secrets to Feishu/Telegram.

---

## 10. Smoke cases

### Case 1 — reusable SOP with no sensitive data

Input: technical debugging session summary with commands and no credentials.

Expected:

- outcome: `clear`
- can_store_draft: true
- can_promote_shared: true after B1 review
- can_sync_remote: true after local verification

### Case 2 — GitHub token in session transcript

Input: `github_pat_...` or `ghp_...` appears in a pasted log.

Expected:

- finding: `secret.github_token`
- severity: `critical`
- outcome: `blocked` or `redact_required` depending on whether useful non-secret content remains
- raw token never appears in redacted preview/audit
- remote sync: false until redacted

### Case 3 — documentation self-match

Input: scanner documentation lists `github_pat_...` as a forbidden pattern with placeholder ellipsis.

Expected:

- classify as documentation placeholder, not a real credential
- outcome: `clear` or low-severity allowlisted finding
- no false blocking of `docs/privacy_scanner_design.md`

### Case 4 — Nana CRM customer data

Input: customer name + phone + treatment + payment/commission details.

Expected:

- findings: `crm.customer_context`, `pii.phone`, optionally `crm.financial`
- outcome: `private_only` or `blocked`
- shared promote: false
- allowed transformed rule: anonymized workflow/policy only

### Case 5 — Arthur private life raw story with reusable support rule

Input: raw personal narrative plus a durable collaboration boundary.

Expected:

- raw narrative: `private_only` or `blocked`
- transformed rule can become shared candidate after review
- no raw private text in shared knowledge

### Case 6 — `.env` / `.pypirc` content before compile

Input: raw entry accidentally includes `password=...`, `token=...`, or PyPI token.

Expected:

- compile fails for that entry
- error reports rule IDs and redacted preview only
- compiled/ and AAAK output not generated for unsafe entry

### Case 7 — Supabase sync payload with legacy risky entry

Input: sync sees an old local entry containing customer phone/email.

Expected:

- sync skips or fails that entry
- remediation list includes entry title/id and finding categories
- no remote upload of raw risky content

### Case 8 — MCP write without required context

Input: MCP add tries to write session-derived content without `source_session_id` / `intended_visibility`.

Expected:

- tool returns context-required validation error
- no formal add
- assistant final answer cannot claim persistence

### Case 9 — cron report with high-risk findings

Input: daily session scan cron finds a reusable technical lesson and a pasted token in the same candidate.

Expected:

- cron produces redacted review report only
- no auto-promote
- no override from cron
- finding categories/counts are included; raw token is absent

### Case 10 — one-off/no-long-term-value content

Input: many tool calls produced only temporary task status, file counts, or a one-time progress update.

Expected:

- scanner may return `clear`, but B1 value gate still returns discard/no candidate
- audit can record `discarded_no_long_term_value`
- no shared knowledge entry and no draft content required

### Case 11 — MCP raw session bypass attempt

Input: an agent tries to send uncurated session transcript directly to formal MCP add.

Expected:

- formal add rejects or routes to future draft-only path
- scanner runs before any persistence
- if private/client/raw personal material appears, outcome is `private_only` or `blocked`
- assistant final answer may say “已建立待審候選” only if a draft ID/path exists; it cannot say “已寫入百科”

---

## 11. Acceptance criteria

B6 design is complete when future implementation can satisfy:

1. One shared scanner module can be called by CLI, MCP, capture, compile, sync, and cron.
2. Outcomes exactly match B1: `clear`, `redact_required`, `private_only`, `blocked`.
3. Secret/token/private-key raw values never enter draft, compiled output, audit logs, Feishu reports, or Supabase payloads.
4. CRM/customer and Arthur life-profile raw data default to private/block, with only transformed generalized rules eligible for shared knowledge.
5. Redaction preview preserves reviewability without leaking values.
6. Override requires explicit reason and audit trail, and cannot store raw secrets.
7. Documentation self-matches are handled as false positives when they are placeholders/pattern examples.
8. Sync boundary is stricter than local/private draft boundary.
9. Smoke cases above can be turned into deterministic tests.

---

## 12. Implementation plan for later

Recommended next implementation tasks after design approval:

1. Create `guardrails_lite/privacy_scanner.py` with deterministic regex/rule engine and dataclasses.
2. Add unit tests for the eleven smoke cases.
3. Integrate scanner into `guardrails add` path with redaction preview.
4. Integrate scanner into MCP add or wrapper path, requiring context for session-derived writes.
5. Add compile-time safety gate for raw entries.
6. Add sync-time remote boundary scan and remediation report.
7. Add private/draft-safe audit format for B5 capture queue.
8. Add Feishu-friendly review report format that never includes raw findings.

Do not start B5 capture automation until B6 scanner implementation has at least CLI/MCP/capture dry-run coverage.
