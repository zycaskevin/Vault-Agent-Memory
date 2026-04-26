---
title: "Agent Harness 架構：Model + Body + Harness 三層框架"
category: "concept"
tags: ["harness", "agent", "architecture", "LLM", "body", "model", "constraint", "verification", "sub-agent", "context-firewall"]
trust: 0.9
source: "2026-04-27 Agent Harness 架構分析（Anthropic + Viv Trivedy + HumanLayer 文獻）"
created: "2026-04-27"
summary: "Agent = Model + Body + Harness。Model 是大腦，Body 是手腳（tools），Harness 是校準層。同模型不同 Harness 跑出不同結果。軟規則模型不一定遵守，硬 Hook 才能真正收窄輸出分布。"
---

# Agent Harness 架構：Model + Body + Harness

## 核心框架

**Agent = Model + Body + Harness**

源自 Viv Trivedy（LangChain）《Anatomy of an Agent Harness》+ Anthropic engineering blog + HumanLayer《Skill Issue》+ 實測驗證。

| 層 | 角色 | 解決什麼問題 | 例子 |
|----|------|-------------|------|
| **Model** | 大腦 | 推理能力 | Opus 4.6, GLM-5.1, DeepSeek-V4 |
| **Body** | 手腳 | 能不能做事 | Bash, Filesystem, Browser, MCP, API calls |
| **Harness** | 校準 | 會不會做歪 | Hooks, Rules, Verification loops, Sub-agent firewalls |

## 關鍵論證

### 1. 同 Model 不同 Harness = 不同結果

OpenClaw 跟 Claude Code 都用 Opus 4.6，寫 code 體感差很多：
- Claude Code 的 Body 專為工程師設計（bash 直接執行、git 整合、typecheck hook）
- Claude Code 的 Harness 校準「寫好 code」（先 plan 再 implement、commit 進度、跑 verification）
- OpenClaw 的 Harness 校準「做好的 personal assistant」（記憶、跨 channel、人格穩定）

同顆模型，裝進不同的 Body + Harness，自然不同。

### 2. Harness 改一行就出包

Anthropic 2026/4/23 postmortem 承認：近期品質問題來自三個 **harness 層** 變更，不是模型退化：

1. **3/4** reasoning effort 從 high 改成 medium
2. **3/26** caching bug：thinking history 每輪都清（本應 1 小時 idle 才清）
3. **4/16** verbosity 限制：「tool calls 間 ≤25 words, final ≤100 words」→ 官方評估「caused an outsized effect on intelligence」

動的不是 Body（bash 還是 bash），動的不是 Model（模型沒換），動的是 Harness——校準層改一點點，整個 output 分布就跑掉。

### 3. Model 變強，Harness 不會消失

Harness 解的不是「model 弱」的問題，是「LLM 永遠 non-deterministic」的結構問題：

- **被 model 變強解掉的**：補 model 弱點的 harness（early scaffolding, Ralph Loop for early stop）
- **永遠在的**：校準 non-deterministic 系統的 harness（hooks, verification, sub-agent firewall, planner-evaluator）

Model 變強 → Body 長新器官（Computer Use, 多 agent 並行），但 Harness 永遠在。

## Harness 六個具體技術

### 1. System prompt 規則（CLAUDE.md / AGENTS.md）
把高頻偏離行為寫成規則。**缺點：模型不一定遵守。**

### 2. Hooks（硬約束）
寫「請不要 X」模型可能還是會做 X。Hook 是「做了 X 就 block 或 warn」。**HumanLayer 原則：success is silent, only failures produce verbose output。**

### 3. Planner / Generator / Evaluator 分離
Anthropic 驗證：絕對不能讓同一個 agent 自己寫自己評。對抗性 evaluator 才有信號。

### 4. Sub-agent context firewall
主 agent 只看 prompt + 最終結果，中間 grep、tool call、檔案讀取都不污染主 thread。每個 sub-agent 拿全新 context window。

Chroma 的 context rot research 證明：拉長 context window 不是解——needle 還是找不到。真正的解是結構性切割 context。

### 5. Verification loop / Back-pressure
不相信 agent 自己說「我做完了」。寫 typecheck、跑 test、build，有錯就把錯誤丟回去。

### 6. Mistake → Rule
每條規則必須追溯一次具體失敗。Addy Osmani：「Every line in a good AGENTS.md should be traceable back to a specific thing that went wrong.」

**注意**：不停堆 rule 也不一定有用。更好的做法是把 harness 結構化（hooks、rule-based 中介層），而不是不停往 prompt 塞文字。

## Body 標準件

| 器官 | 說明 |
|------|------|
| Filesystem + Git | 持久狀態、跨 session、版本控制 |
| Bash + 程式執行 | 自主寫 tool |
| Sandbox | 隔離執行環境 |
| Browser / Computer Use | GUI 互動 |
| MCP server | 擴充工具（注意：tool description 也是 prompt，塞太多撐爆 context） |
| Web Search + Read Image | 人類能做的幾乎都做得到 |

MCP 踩坑：如果 MCP 跟成熟 CLI 功能重疊，用 CLI（省 context window）。

## 實作範例：Hermes Hard Hooks

```
R001 — config.yaml/.env 不可被 agent 覆蓋（block）
R002 — Python 寫入後自動語法驗證（warning）
R006 — send_message 非 DM 目標注入警告（warning）
R011 — 本地模型端點攔截（warning）
R014 — 高風險 tool call 前自動搜尋知識庫（context injection）
```

全部遵循 HumanLayer 原則：成功靜默，失敗才出聲。
所有觸發記錄到 audit.log，供季度審查。

## Terminal-Bench 2.0 洞見

- 不換 model，只改 harness，就有不同的 accuracy
- 「該模型最佳的 harness 就是它被訓練的那個」不一定正確
- 同一問題讓不同 runtime/harness 試，反而有意外驚喜

## ChatGPT Images 2.0 — Harness 升級的體感

OpenAI 推出 gpt-image-2，官方定位「first image model with thinking capabilities」：
關鍵不只是 model 變強，而是加了 harness 層：「create image → search web for reference → double-check own output」。
驗證循環是 harness 的典型手法——不換 model，加約束邏輯，品質就提升。

## 結論

下次有人說「等更強的模型出來就好了」，問：這個問題本質是缺大腦（Model），是缺手腳（Body），還是缺約束（Harness）？

- Model 變強後，Body 長新器官，但 Harness 永遠在
- 軟規則靠模型遵守，硬 Hook 才能真正收窄分布
- 每條規則追溯一個具體失敗，不要空泛的「請小心」
- 審計日誌讓你知道每條規則在不在作用