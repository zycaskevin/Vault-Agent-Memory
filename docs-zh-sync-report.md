# Chinese README Sync Report (中文 README 同步差異報告)

> Generated from comparing `README.md` (EN) with `README.zh-CN.md` and `README.zh-Hant.md`.
> Baseline version: EN = 0.7.29, ZH was = 0.7.28 (已更新為 0.7.29)

## Summary (摘要)

| Item | Status | Notes |
|------|--------|-------|
| Version number | ✅ Fixed | Was 0.7.28 → bumped to 0.7.29 |
| Launch entry parity | ✅ Fixed | Role table, Mermaid architecture, Why Vault table, one-click install, and core concept link now exist in both Chinese READMEs |
| Section count | ✅ Close | EN: 21 vs ZH: 20 |
| Section structure | ✅ Audience-specific | Chinese versions keep a general-user/product entry shape while covering the launch-critical technical depth |
| MCP tool list | ✅ Present | Core 6 tools all present |
| Maturity table | ✅ Expanded | ZH now includes Search QA and Memory Migration status rows |
| Quickstart commands | ✅ Present | Install, quickstart, MCP, demo, automation, remote, import, and Search QA paths are covered |
| Doc link coverage | ✅ Launch-ready | ZH now links the key demo, automation, integration, remote, migration, governance, and Search QA docs |

## Applied Fixes (已套用修正)

The following small fixes were applied directly to both `README.zh-CN.md` and `README.zh-Hant.md`:

- ✅ **Version bump**: `0.7.28` → `0.7.29` in all pip install commands
- ✅ **Role-oriented entry**: added the 5-role starting-point table
- ✅ **Architecture visual**: added the Mermaid memory-governance flow
- ✅ **Why Vault comparison**: added the no-Vault / with-Vault comparison table
- ✅ **One-click install**: added macOS/Linux and PowerShell install commands with main/release wording
- ✅ **Core concepts link**: added `docs/core-concepts.md` to the Chinese advanced feature index
- ✅ **Killer demo depth**: added the `vault demo agent-governance --json` path and demo pack links
- ✅ **Memory model depth**: expanded temporal windows, expiry, and supersession metadata
- ✅ **Automation section**: added daily report and governed automation commands
- ✅ **Integrations table**: added Codex/Claude/Hermes/OpenClaw/n8n/Coze/Obsidian/Headroom paths
- ✅ **Remote sharing**: expanded Supabase plus Gateway / Remote Server setup paths
- ✅ **Memory migration**: added candidate-first import examples
- ✅ **Retrieval quality**: added Search QA command and interpretation guidance
- ✅ **Development path**: added uv workflow commands

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
2. **你是哪种用户？先从这里开始**
3. **最推荐：让 Agent 帮你安装**
4. **每天怎么用**
5. **适合谁**
6. **它不是什么**
7. **三个常见场景**
8. **一键安装**
9. **开发者快速开始**
10. **记忆分层**
11. **自动化与每日报告**
12. **集成方式**
13. **Obsidian**
14. **Supabase 与远端共享**
15. **记忆迁移**
16. **搜索质量**
17. **进阶功能索引**
18. **成熟度**
19. **开发与测试**
20. **授权**

## Major Structural Gaps (主要結構差異)

The Chinese READMEs still intentionally differ from the English structure, but
the high-impact launch and technical depth gaps have now been closed. Remaining
differences are product-positioning choices or lower-priority community docs:

| Section | Priority | Why It Matters |
|---------|----------|----------------|
| 3-Minute Demo placeholder | 🟡 Medium | EN still keeps a GIF placeholder; ZH prefers the existing visual demo plus common-scenario framing until the real media exists. |
| Documentation Map | 🟢 Low | ZH uses `进阶功能索引 / 進階功能索引` instead of mirroring the full EN documentation map. |
| Contributing | 🟢 Low | Contributing remains absent from ZH README to keep the Chinese page product-first; developers can use EN docs. |

## Sections Unique to Chinese (中文版本獨有章節)

The Chinese versions have some sections that don't have direct EN equivalents:

- **适合谁 / 適合誰** — Audience/fit section, not present as a dedicated section in EN
- **三个常见场景 / 三個常見情境** — Three common use cases section, now followed by the demo command and demo pack links
- **进阶功能索引 / 進階功能索引** — Advanced features index, different format from EN's 'Documentation Map'

## Translation Priority Recommendations (翻譯優先級建議)

Most launch-critical translation work is now complete. Remaining work should be
treated as polish, not a blocker:

### Phase 1 — Polish (中優先級)

1. **3-Minute Demo media** — Replace the placeholder with the real walkthrough once available.
2. **Documentation Map tuning** — Decide whether ZH should keep the compact feature index or mirror EN's full documentation map.

### Phase 2 — Lower Impact (低優先級)

3. **Contributing section** — Add only if the Chinese README is expected to serve community contributors directly.

## Related Launch Content (啟動前文件內容)

The following English README sections/features are now covered in both Chinese
READMEs, with wording adapted for the Chinese product-entry audience:

- **P0-1: Who Are You? Start Here** — Role-oriented entry table (5 rows)
- **P0-2: Mermaid architecture diagram** — Localized diagram plus Why Vault comparison table
- **P2-1: One-Click Install section** — Install script references and commands
- **P1-1: Core Concepts doc link** — `docs/core-concepts.md` link in the Chinese advanced feature index
- **Depth pass** — Demo path, memory model, automation, integrations, remote sharing, migration, Search QA, and uv development commands

Still not mirrored by design:

- **P2-2: 3-Minute Demo placeholder** — English keeps a placeholder; Chinese READMEs currently prefer the existing visual demo and common-scenario framing.

---

*Report generated as part of the pre-launch documentation improvement pass.*
