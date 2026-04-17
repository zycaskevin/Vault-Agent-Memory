---
title: Guardrails Lite Knowledge Graph v0.2.0 — 輕量知識圖譜層
layer: L2
category: architecture
tags: knowledge-graph,sqlite,BFS,mermaid,graphviz,entity-inference
trust: 0.95
source: 實測開發
---

# Guardrails Lite Knowledge Graph v0.2.0

## 問題
向量搜尋只能找語義相似的知識，無法發現**關聯性**。例如搜 "Ollama timeout" 能找到 timeout 那條，但不知道它跟 sqlite-vec 載入順序有關。

## 解法：輕量知識圖譜層
在向量搜尋之上加一層 edges + entities 表，用 BFS 擴展搜尋結果。

### 架構
- **entities 表**：自動從 tags/title/category 推斷實體（tool/model/concept/platform/tag）
- **edges 表**：共用實體的知識條目自動連邊（shared_XXX），支援手動建邊
- **entity_knowledge 表**：實體↔知識條目的多對多對應
- **BFS 擴展**：`search --graph-expand 1/2` 從搜尋結果沿邊擴展到鄰居

### 效能
- 123 筆知識 → 316 實體 → 910 邊（8.7 秒建構）
- 批次 INSERT 替代逐條 add_edge（速度提升 10x）
- 只連接 2-8 筆知識的實體（超連接實體如 error/git 無區分度，過濾掉）
- 116/123 節點連通

### CLI 新命令
```bash
guardrails graph build          # 自動推斷圖譜
guardrails graph show           # 顯示摘要
guardrails graph export -f mermaid -o graph.md  # Mermaid 可視化
guardrails graph export -f dot -o graph.dot     # Graphviz 可視化
guardrails graph link 1 11 -r related_to -w 0.9 # 手動建邊
guardrails graph expand 1 -d 1  # BFS 擴展
guardrails search "ollama" --graph-expand 1     # 搜尋+圖譜擴展
```

### 圖譜搜尋效果
- 純搜尋：找到語義最相似的 N 筆
- +graph-expand：額外找到**透過共用實體關聯**的知識
- 分數衰減：graph_expand 結果 score = base_score × 0.7^distance

## 踩坑
1. **邊爆炸**：超連接實體（error、git 連 30+ 筆知識）會產生 C(30,2)=435 條無意義邊。解法：只保留連接 2-8 筆知識的實體
2. **雙重建邊**：`infer_from_knowledge` 內部呼叫 `_infer_edges_from_shared_entities`，`infer_all` 又呼叫 `_infer_all_edges_batch`。解法：加 `build_edges=False` 參數
3. **批次 INSERT**：逐條 `add_edge` + commit 太慢。改用 `executemany` + `INSERT OR IGNORE`
4. **實體噪音**：tag 提取會把 "if"、"1." 等無意義詞建為實體。解法：停用詞過濾 + 長度限制 + 必須含字母
5. **Schema 遷移**：v1→v2 需加 edges/entities/entity_knowledge 表，`_init_tables` 用 `CREATE TABLE IF NOT EXISTS` 無痛升級
