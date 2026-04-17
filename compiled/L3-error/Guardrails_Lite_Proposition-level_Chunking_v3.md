---
category: error
hash: 28d33f83f312ed93
id: 14
layer: L3
tags: guardrails-lite,proposition,chunking,ollama,vector-search
title: Guardrails Lite Proposition-level Chunking v3
trust: 0.8
updated_at: '2026-04-17T02:57:23.679331+00:00'
---

TITLE:Guardrails Lite Proposition-level Chunking v3
- 百科知識是整篇存入 DB，一個向量代表 5-15 個事實。
- 把每個段落拆成原子命題（atomic claim），每條獨立嵌入。
- proposition_chunk(。
- text, doc_title="", ollama_model="qwen3:8b",。
- max_propositions_per_chunk=8, paragraph_max_chars=2000,。
- 跳過 YAML frontmatter
- 按 Markdown 標題（# / ## / ###）分段落
- 短段落（<100字）直接當命題，跳過 LLM
... (36 more)
