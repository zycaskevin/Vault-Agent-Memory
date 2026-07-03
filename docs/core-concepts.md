# Core Concepts in Plain Language

Understand Vault in 5 minutes — no jargon required.

---

## Candidate (候選記憶)
Think of it as a "suggestion box." Agents can propose things to remember, but candidates don't affect search results until they're reviewed. This is the safety net — bad memory never reaches the active vault.

**Analogy:** Like a Wikipedia draft before it's published.

## Promote (提升)
When a candidate memory passes review (human or automated low-risk check), it gets promoted to active memory. Now it shows up in searches and influences agent behavior.

**Analogy:** Promoting a draft to published status.

## L0-L3 Memory Layers (記憶分層)
Vault organizes memory like a closet, not a junk drawer:

- **L0 — Identity:** Who you are, project framing. Always loaded first. Like your driver's license — always on you.
- **L1 — Rules & Preferences:** Stable facts, how you like things done. Like the top drawer — you reach for it every day.
- **L2 — Recent Context & Summaries:** Reviewed recent context, current project status. Like your desk surface — what you're working on right now.
- **L3 — Deep Knowledge:** Detailed knowledge, SOPs, bug fixes, decisions, source notes. Like the storage room — vast, searchable, but not in your face.

## Governance Metadata (治理元數據)
Every memory has an "ID card" that describes:
- **Scope:** Is this private, project-only, shared, or public?
- **Sensitivity:** How confidential is this? (low / medium / high / restricted)
- **Owner:** Which agent wrote it?
- **Allowed agents:** Who can read it?
- **Expiry:** When should this be moved out of normal recall?
- **Valid period:** When was this fact true?

**Why it matters:** Without governance metadata, memory is just a pile of text with no guardrails.

## Bounded Read (邊界讀取)
Agents can't dump the entire vault. They search, get results, and read specific sections with source attribution. This prevents:
- Accidental data leaks between projects
- Context window bloat
- Unattributed claims

**Analogy:** Like a library — you find books via the catalog, then read specific chapters, not the whole building.

## Daily Report (每日報告)
The main human interface. You don't dig through the database — Vault summarizes what needs your attention:
- New memory candidates worth reviewing
- Stale memories that might be outdated
- Conflicting information
- Low-risk items that were auto-promoted

**Goal:** 2 minutes a day, not 20 minutes.

## Task Ledger (任務賬本)
Not memory — it's the live workbench: blockers, next actions, evidence links, due dates, handoff notes. Durable lessons get promoted to memory layers after review.

**Analogy:** Your whiteboard vs. your filing cabinet.

---

## The Workflow in One Sentence

Agents propose → Vault checks quality/privacy/duplicates → low-risk auto-promotes, high-risk waits for human review → searched and read with boundaries → can be deprecated or rolled back.

## Want More?

- [Memory governance deep dive](memory_governance.md)
- [MCP memory workflow](mcp_memory_workflow.md)
- [Architecture & design decisions](decision_records/)
