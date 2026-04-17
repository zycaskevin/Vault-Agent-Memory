---
title: Guardrails Lite 長文件分塊匯入 — 4 種策略對標 2025 SOTA
category: architecture
layer: L2
tags: guardrails,RAG,分塊,語意分塊,摘要引導,chapter-detection,向量搜尋
trust: 0.95
source: 實測驗證
---

# Guardrails Lite 長文件分塊匯入 — 4 種策略對標 2025 SOTA

## 問題
丟一部 10 萬字小說到 Guardrails，原本只會變成 1 筆知識 → 1 個模糊向量 → 搜「主角跟誰吵架」只能找到整本書。

## 解法：4 種分塊策略

### 1. Chapter Detection（預設）
- 正則偵測中文章節（第X章/節）、英文章節（Chapter X/Part X）、Markdown 標題（# / ##）
- 短章直接當一塊，長章內部再用語意分塊
- 零 LLM 成本，純規則

### 2. Semantic Chunking
- 計算相鄰句子嵌入向量的餘弦相似度
- 相似度驟降處 (< threshold) 切斷
- 保證每塊語意連貫，不會把兩個不相關話題黏在一起
- 需要嵌入模型（ONNX 本地跑）

### 3. Summary-Guided Segmentation（ACL 2025 論文）
- 用文本前 2000 字當「摘要代理」
- 計算每句跟摘要的相似度
- 相似度局部極小值 = 主題轉換點 = 切斷位置
- 不需要 LLM，純嵌入即可
- 比純語意分塊精確 5-15%（論文實測）

### 4. Sliding Window（降級方案）
- 固定大小 + 重疊
- 嘗試在句子邊界截斷
- 不需要嵌入模型

## 實測結果
測試文本：三體小說 5000 字摘要，7 個章節

搜尋「葉文潔向太陽發射信號」：
| 排名 | 分塊 | 分數 |
|------|------|------|
| 🥇 | 第一節 太陽放大器 | **0.636** |
| 🥈 | 第二章 三體世界 | 0.478 |
| 🥉 | 第三章 黑暗森林 | 0.471 |

搜尋「面壁者」：
| 排名 | 分塊 | 分數 |
|------|------|------|
| 🥇 | 第二節 執劍人 | 0.468 |
| 🥈 | 第一節 面壁者 | 0.465 |

精確命中相關段落，而不是整本書。

## CLI 用法
```bash
guardrails import novel.md --strategy chapter --title "三體"
guardrails import report.txt --strategy summary-guided
guardrails import paper.pdf --strategy semantic --no-embed
guardrails import doc.md --strategy sliding --chunk-size 500
```

## 論文基礎
- Semantic Chunking: 2023 基礎，計算相鄰嵌入相似度切斷
- Summary-Guided: ACL 2025 "Document Segmentation Matters for RAG"，用全文摘要引導分塊邊界
- Adaptive Chunking: arXiv 2603.25333，自動選最適合分塊策略
- Late Chunking: Jina AI 2024，先嵌入整篇再分塊（需長上下文模型）
- RAPTOR: Stanford 2024，遞迴摘要樹（需 LLM）
- Proposition-Based: Dense X Retrieval 2023，最小意義單元檢索