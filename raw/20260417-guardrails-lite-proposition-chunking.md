---
title: Guardrails Lite Proposition-level Chunking v3
layer: L3
tags: [guardrails-lite, proposition, chunking, ollama, vector-search]
trust: 0.8
---

# 問題

百科知識是整篇存入 DB，一個向量代表 5-15 個事實。搜「Ollama timeout 改多少」只能找到整篇，不是那一句。

# 解法：Proposition-level Chunking（Dense X Retrieval 2023）

把每個段落拆成原子命題（atomic claim），每條獨立嵌入。搜尋精準命中具體事實。

## 實作

```python
proposition_chunk(
    text, doc_title="", ollama_model="qwen3:8b",
    max_propositions_per_chunk=8, paragraph_max_chars=2000,
)
```

### 流程

1. 跳過 YAML frontmatter
2. 按 Markdown 標題（# / ## / ###）分段落
3. 短段落（<100字）直接當命題，跳過 LLM
4. 程式碼塊段落直接保留
5. 長段落用 Ollama 拆成原子命題（每段最多 8 條）
6. Ollama 不可用時降級為句子級分塊

### LLM Prompt 設計

```
你是一個知識管理助手。請把{context}拆解成獨立的原子命題。
規則：
1. 每個命題是一個簡潔、自足的事實陳述
2. 一句話只包含一個事實
3. 保留原來的專有名詞和數字
4. 最多 N 個命題
5. 每行一個命題，不要編號，不要其他說明
```

### 過濾規則

LLM 輸出需要嚴格過濾，尤其是小模型：

1. 移除編號前綴（1. 2. - 等）
2. 移除 Markdown 格式（**加粗**、```代碼塊```）
3. 移除 LLM 冗餘回應（「好的」「以下是」「根據您的要求」）
4. 太短（<10字）或太長（>200字）的行跳過
5. 移除 prompt 洩漏（包含「命題」「拆解」「規則」等指令性文字）

## CLI 用法

```bash
guardrails import doc.md --strategy proposition --ollama-model qwen2.5:0.5b
guarrails import doc.md --strategy proposition --ollama-model qwen3:8b  # 品質更好但慢
```

# 踩坑

## 1. 0.5B 模型品質有限

qwen2.5:0.5b 會產生重複廢話（「情況性陳述」）、meta 回應（「好的，根據您的要求」）、編號前綴。需要嚴格的 reject pattern 過濾。

qwen3:8b 品質好很多但 CPU 推理每段落 ~40s，16 個段落需 ~5 分鐘。

**建議：** 正式匯入用 8B，快速測試用 0.5B。

## 2. 短段落不用拆

<100 字的段落只有 1-2 句話，LLM 拆不出新東西，反而產生垃圾。直接當命題。

## 3. 程式碼塊保留不拆

程式碼被逐行拆成命題完全沒意義。整塊保留。

## 4. YAML frontmatter 要跳過

不跳過的話 LLM 會把 `title:` `tags:` 當命題拆。

# 測試結果

1 篇百科（Contextual Retrieval 文檔）：

| 項目 | 數量 |
|------|------|
| 輸入段落 | 16 |
| 輸出命題 | 44 |
| 短段落直接保留 | ~6 |
| LLM 拆解 | ~10 段落 |
| 過濾掉的垃圾 | ~4 條 |

搜尋品質：

| 查詢 | 命中 | Score |
|------|------|-------|
| Ollama timeout 改多少 | §19 timeout | 0.501 |
| 分塊後失去什麼 | §1 問題描述 | 0.453 |

# 路線圖

- v1：chapter + semantic chunking
- v1.5：summary-guided
- v2：Contextual Retrieval（Ollama 上下文增強）
- v3：Proposition-level chunking ✅（本次）
- v3.5：改善 Ollama 輸出品質（更大模型或 better prompt）
- v4：RAPTOR（遞迴摘要樹）
- v5：GraphRAG