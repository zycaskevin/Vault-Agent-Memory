# Chinese README Sync Report (中文 README 同步差異報告)

> Generated from comparing `README.md` (EN) with `README.zh-CN.md` and `README.zh-Hant.md`.
> Baseline version: EN = 0.7.29, ZH was = 0.7.28 (已更新為 0.7.29)

## Summary (摘要)

| Item | Status | Notes |
|------|--------|-------|
| Version number | ✅ Fixed | Was 0.7.28 → bumped to 0.7.29 |
| Section count | ⚠️ Different | EN: 21 vs ZH: 14 |
| Section structure | ❌ Major gap | Chinese versions use different section organization |
| MCP tool list | ✅ Present | Core 6 tools all present |
| Maturity table | ⚠️ Different items | ZH table has fewer and different categories |
| Quickstart commands | ⚠️ Partial | 6/7 found |
| Doc link coverage | ⚠️ Partial | EN has more doc links |

## Applied Fixes (已套用修正)

The following small fixes were applied directly to both `README.zh-CN.md` and `README.zh-Hant.md`:

- ✅ **Version bump**: `0.7.28` → `0.7.29` in all pip install commands

## Section-by-Section Comparison (章節對比)

### English Sections

1. **30-Second Version**
2. **Who Are You? Start Here 👇**
3. **For Agent Builders: Ask Your Agent To Install It**
4. **Daily Use**
5. **What Vault Is Not**
6. **Killer Demo: Shared Governed Memory**
7. **3-Minute Demo (Coming Soon)**
8. **One-Click Install**
9. **Developer Quickstart**
10. **Memory Model**
11. **Automation And Daily Reports**
12. **Integrations**
13. **Obsidian**
14. **Remote Sharing**
15. **Memory Migration**
16. **Retrieval Quality**
17. **Maturity**
18. **Documentation Map**
19. **Development**
20. **Contributing**
21. **License**

### 中文 Sections

1. **30 秒版**
2. **最推荐：让 Agent 帮你安装**
3. **每天怎么用**
4. **适合谁**
5. **它不是什么**
6. **三个常见场景**
7. **开发者快速开始**
8. **记忆分层**
9. **Obsidian**
10. **Supabase 与远端共享**
11. **进阶功能索引**
12. **成熟度**
13. **开发与测试**
14. **授权**

## Major Structural Gaps (主要結構差異)

The Chinese READMEs have a significantly different structure from the English version.
Key sections present in EN but missing or differently organized in ZH:

| Section | Priority | Why It Matters |
|---------|----------|----------------|
| Killer Demo: Shared Governed Memory | 🔴 High | The killer demo section with `vault demo agent-governance --json` and demo pack links is absent. This is a critical onboarding section. |
| Memory Model | 🔴 High | The L0-L3 memory layers explanation + governance metadata + temporal windows. ZH has '记忆分层' but is less detailed (missing temporal facts, expiry vs valid_until distinction). |
| Automation And Daily Reports | 🔴 High | Automation commands (`vault daily-report`, `vault automation brief`, etc.) and the governed-auto explanation are not a dedicated section in ZH. |
| Integrations table | 🔴 Medium | The full integrations table (Codex/Claude/Hermes/n8n/Coze/Obsidian/etc.) is missing. ZH mentions integrations but not in a structured table. |
| Remote Sharing (full section) | 🔴 Medium | EN has a full Remote Sharing section with both Supabase and Gateway/Remote Server. ZH only covers Supabase briefly. |
| Memory Migration | 🔴 Medium | The `vault import memory` section with candidate-first migration approach is missing. |
| Retrieval Quality / Search QA | 🔴 Medium | Search QA benchmarking section and claims are missing from ZH. |
| What Vault Is Not (full section) | 🔴 Low | ZH has '它不是什么' but covers fewer points than EN's dedicated section. |
| Development (full section) | 🔴 Low | ZH has '开发与测试' but only the basic pip path, missing uv sync path. |
| Contributing | 🔴 Low | Contributing section is absent from ZH README. |

## Sections Unique to Chinese (中文版本獨有章節)

The Chinese versions have some sections that don't have direct EN equivalents:

- **适合谁 / 適合誰** — Audience/fit section, not present as a dedicated section in EN
- **三个常见场景 / 三個常見情境** — Three common use cases section, which overlaps with EN's 'Killer Demo' and 'Integrations' but is framed differently
- **进阶功能索引 / 進階功能索引** — Advanced features index, different format from EN's 'Documentation Map'

## Translation Priority Recommendations (翻譯優先級建議)

Given the significant structural differences, here is the recommended translation order:

### Phase 1 — High Impact (高優先級)

1. **Killer Demo section** — This is the primary conversion path for new users
2. **Memory Model section (expanded)** — Core product differentiator; current ZH '记忆分层' is too brief
3. **Automation And Daily Reports** — Key feature explanation with command examples
4. **Role-oriented entry table (P0-1)** — The new 'Who Are You?' table from this PR needs translation

### Phase 2 — Medium Impact (中優先級)

5. **Integrations table** — Helps users quickly understand compatibility
6. **Retrieval Quality / Search QA** — Evidence-backed quality claims
7. **Remote Sharing (expanded)** — Gateway/Remote Server documentation
8. **Maturity table alignment** — Make ZH maturity table match EN items and descriptions

### Phase 3 — Lower Impact (低優先級)

9. **Memory Migration section** — Niche use case
10. **Development section (uv path)** — Developer-only info
11. **Contributing section** — Community-facing, lower urgency
12. **Mermaid architecture diagram (P0-2)** — Visual diagram is language-independent but the Why Vault? table needs translation

## Related New Content from This PR (本次 PR 新增內容)

The following new sections/features were added to the English README in this PR and also need Chinese translation:

- **P0-1: Who Are You? Start Here** — Role-oriented entry table (5 rows)
- **P0-2: Mermaid architecture diagram** — Diagram itself is universal; 'Why Vault?' comparison table needs translation
- **P2-1: One-Click Install section** — Install script references and commands
- **P2-2: 3-Minute Demo placeholder** — 'Coming soon' section
- **P1-1: Core Concepts doc link** — `docs/core-concepts.md` link in Documentation Map

---

*Report generated as part of the pre-launch documentation improvement pass.*
