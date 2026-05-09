# Guardrails 百科（內部主庫）

> Arthur Liao 的個人知識中樞 — 四層分層記憶系統，336+ 筆知識 + 254 筆技能，Supabase + SQLite 雙引擎。

⚠️ **給 AI agent：這是主庫。** `~/Vault-for-LLM/` 是從這個庫「閹割」出去的開源版（去敏感內容、換品牌名 `vault` CLI）。搜尋知識時優先讀這個庫，別搞錯。

---

## 與其他庫的關係

| 目錄 | 是什麼 | 別搞錯 |
|---|---|---|
| **`~/Guardrails-knowledge/`** ← 你在這裡 | **主庫**（336+ 知識 + 254 技能，schema v5） | 這是唯一真實來源 |
| `~/Vault-for-LLM/` | 開源版（從主庫閹割、去敏感內容、品牌改名 `vault`） | 不是主庫，知識不完整 |
| `~/.hermes/Guardrails/` | Graphify / L2 context 相關目錄 | 不是主知識庫；查知識仍以本 repo 為準 |

---

## 架構

```
L0 身份    → identity.md（每次對話注入）
L1 核心事實 → current-projects.md（每次對話注入）
L2 脈絡    → recent-sessions/（每天自動更新）
L3 深度知識 → SQLite guardrails.db（keyword + vector + graph 混合搜尋）+ Supabase 同步
```

---

## AI Agent 讀取指南

**每次對話：**
1. 讀 `L0-identity/identity.md`（用戶身份）
2. 讀 `L1-core-facts/current-projects.md`（當前專案）

**需要查知識時：**
```bash
# 優先 CLI
guardrails search "query"

# 或用 MCP
mcp_guardrails_guardrails_search query="query"

# 或用 rg 搜 raw/ compiled/
rg "關鍵字" raw/ compiled/
```

**做完有價值的工作後：**
1. 寫入 `raw/` 一條新知識（YAML frontmatter）
2. 執行 `guardrails compile`

---

## 近期核心系統入口（給 AI Agent）

### Hermes Dashboard — 多 Agent 可觀測性儀表板

- **外網入口**：https://dashboard.nancyai.dev
- **本機入口**：http://localhost:3460
- **服務**：`hermes-dashboard.service`
- **本地路徑**：`~/.hermes/dashboard/oa-cli/`
- **用途**：集中查看 Nancy / Nana / Harness / 其他 profile 的狀態、cron 執行、Harness Gate、Token 預算、Guardrails 品質。
- **相關百科條目**：
  - `#333 Hermes Dashboard — 多 Agent 共享可觀測性儀表板`
  - `#335 Hermes Dashboard 前端繁體中文化與六階段閉環設計`
  - `#336 Hermes Dashboard Supabase 寫入範例 — Agent 狀態同步`

常用驗證：

```bash
systemctl is-active hermes-dashboard
curl -s -o /dev/null -w "%{http_code}" https://dashboard.nancyai.dev/
cd ~/.hermes/dashboard/oa-cli/dashboard-src && npx tsc --noEmit
```

### Handoff Protocol — 跨 Profile 任務交接

- **腳本**：
  - `~/.hermes/scripts/kanban_handoff.py`
  - `~/.hermes/scripts/handoff_dispatcher.py`
- **資料庫**：`~/.hermes/kanban/kanban.db`
- **用途**：Nancy / Harness Verify / Harness Correct / Nana CRM 之間建立交接事件，並推送到 Dashboard Harness Gate。
- **相關百科條目**：`#334 Handoff Protocol — Hermes 跨 Profile 任務交接協議`

最小用法：

```python
import sys
sys.path.insert(0, "/home/zycas/.hermes/scripts")
import kanban_handoff as k

k.init()
k.create_handoff(
    from_agent="nancy",
    to_agent="harness-verify",
    summary="Nancy 完成任務，請驗證",
    verdict="pending"
)
```

---

## Dashboard / Handoff 相關 Supabase 表

其他 Agent 要同步狀態到 Dashboard，優先寫入以下五表：

| 表 | 用途 |
|---|---|
| `hermes_cron_runs` | cron 執行結果、成功/失敗/timeout |
| `hermes_agent_sessions` | agent session 狀態、tool calls、tokens、harness score |
| `hermes_harness_events` | Harness Gate、R 規則、handoff、verify/correct/evolve 事件 |
| `hermes_token_usage` | Token 預算與用量（`date` 唯一，重複會 409） |
| `hermes_guardrails_health` | Guardrails 收斂率、新鮮度、矛盾數（`check_date` 唯一） |

欄位與寫入範例見百科 `#336`。

---

## CLI 參考

| 命令 | 說明 |
|---|---|
| `guardrails search "query"` | 混合搜尋（keyword + vector + graph） |
| `guardrails add "Title" --content "..."` | 新增知識 |
| `guardrails compile` | 編譯 raw/ → db + compiled/ |
| `guardrails list` | 列出知識 |
| `guardrails stats` | 統計（含 skill_count） |
| `guardrails lint` | 品質檢查 |
| `guardrails doctor` | 環境診斷 |
| `guardrails graph build` | 建立知識圖譜 |
| `guardrails skill push --file SKILL.md` | 註冊技能到市場 |
| `guardrails skill search "query"` | 搜尋技能 |
| `guardrails skill pull "name"` | 下載技能 |

---

## 目錄結構

```
Guardrails-knowledge/
├── README.md               ← 你在這裡
├── L0-identity/            ← 身份
├── L1-core-facts/          ← 核心事實
├── L2-context/             ← 動態上下文
├── L3-knowledge/           ← 深度知識
├── raw/                    ← 原始知識輸入
├── compiled/               ← AAAK 壓縮備份
├── guardrails.db           ← SQLite 主資料庫（schema v5）
├── scripts/                ← 維護腳本
└── templates/              ← 空白模板
```

---

## 維護

```bash
# 編譯
guardrails compile

# 同步到 Supabase
python3 scripts/sync_to_supabase.py

# 收斂檢查
guardrails converge

# 新鮮度檢查
guardrails freshness
```

---

## YAML Frontmatter 格式

```yaml
---
title: "知識標題"
category: "concept|technique|workflow|lesson|error|comparison"
layer: 0-3
tags: ["tag1", "tag2"]
trust: 0.0-1.0
source: "來源"
created: "YYYY-MM-DD"
---
```

---

*最後更新：2026-04-30 — 修復品牌混淆（不再自稱 Vault-for-LLM）*