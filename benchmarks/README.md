# 基準測試 (Benchmarks)

此目錄包含 Vault Agent Memory 搜尋效能與品質的基準測試工具。

## 可用的基準測試

### `memory_foundation_compare.py` - 外部記憶引擎 + Vault 配對測試

把 mem0、Letta/MemGPT、AgentMemory 或其他引擎輸出的 frozen candidate
pool 視為 `A`，再用 Vault read guard 產生 `A+B`，分開量測 Valid Recall、
forbidden exposure、latency 與 cost delta。另有 fixed-clock
`VaultGovBench` 動態治理 suite；完整契約與命令見
[`docs/memory_foundation_benchmarks.md`](../docs/memory_foundation_benchmarks.md)。

```bash
python3 benchmarks/memory_foundation_compare.py governance-run \
  --fixture benchmarks/vault_gov_bench/v0.1.json \
  --output /tmp/vault-gov-bench-v0.1.json
```

公開 synthetic fixture 只驗證 contract/scorer，不代表任何 live provider
的產品成績。

Live provider 必須先取得不含 scorer gold 的 input。Vault 本身也走同一條
blind path：

```bash
python3 benchmarks/external_memory_compare.py export-provider-input \
  --fixture benchmarks/vault_gov_bench/retrieval_v0.1.json \
  --output /tmp/vaultgov-provider-input.json

python3 benchmarks/vault_fixture_run.py \
  --fixture /tmp/vaultgov-provider-input.json \
  --candidate-pool-k 4 \
  --mode keyword \
  --output /tmp/vault-provider-run.json
```

舊的 `external_memory_compare.py vault-run` / `vault-mode-compare` 會在同一
process 解析 raw benchmark 與 gold，只能當 non-blind diagnostic，不能通過
目前的 publication gate。

### `agentmemory_compare.py` - rohitg00/agentmemory v0.9.27 adapter

以官方 `remember` / `smart-search` REST surface 產生 neutral run artifact。
因 v0.9.27 的 `project` 不會過濾一般 memory results，每次執行都必須搭配
全新的隔離 server store；任何無法映射回本次 fixture source 的 `obsId`
都會 fail closed。

```bash
python3 benchmarks/agentmemory_compare.py \
  --fixture /tmp/vaultgov-provider-input.json \
  --fresh-store-id agentmemory-run-001 \
  --provider-version 0.9.27 \
  --limit 4 \
  --output /tmp/agentmemory-run-001.json
```

這個 adapter 只支援 global fixture。Server 啟停、iii-engine 與 store
隔離由 provider sandbox 負責；adapter 會分開記錄 index 和 query latency，
且用 `memory.id -> fixture source` mapping 修正官方 compact result 固定回傳
`sessionId: "memory"` 的 provenance 問題。

所有 live provider（Vault、mem0、Letta、AgentMemory）都只能讀
`export-provider-input` 產生的 blind input；完整 gold fixture 只交給後續
`augment-run`、`score-pair` 與 scorer。可公開的 provider row 還必須具備：
同一個 clean committed source/lock/adapter/scorer chain、至少五次獨立
clean-state repeats、raw/pair/provider-input digest binding，以及每次執行的
empty-store/teardown evidence binding。缺少任何一項就是 `not measured` 或
developer diagnostic，不能用零值補齊。

公開 fixture 能讓任何人重現與 code review，但也能被事先研究；blind
input 只防止 provider process 意外讀到 gold，不等於 hidden test。正式推廣
的比較性主張還需要由獨立 scorer 保管、定期輪替的 hidden holdout。

### `search_benchmark.py` - 搜尋品質與效能基準測試

比較不同搜尋策略的效果與效能：

- 關鍵詞搜尋 vs 混合搜尋 vs 語義搜尋
- 有無 rerank 的差異
- 輕量 rerank vs cross-encoder rerank
- 有無查詢擴展的差異

**指標：**
- 精確率 (Precision@k)
- 召回率 (Recall@k)
- 歸一化折價累積增益 (NDCG@k)
- 查詢延遲 (平均、P95)

**使用方式：**

```bash
# 基礎測試（僅關鍵詞搜尋）
python3 benchmarks/search_benchmark.py

# 指定嵌入提供者進行完整測試
python3 benchmarks/search_benchmark.py --embed-provider auto

# 保存結果到指定文件
python3 benchmarks/search_benchmark.py --output results.json

# 同時跑 Search QA fixture，輸出 top-k / MRR / latency 摘要
python3 benchmarks/search_benchmark.py \
  --embed-provider None \
  --qa-file benchmarks/search_qa/basic.en.json \
  --qa-modes keyword
```

未指定 `--output` 時，結果會寫到 `/tmp/vault_search_benchmark_results.json`，避免把本機 benchmark 產物提交到 repo。

**輸出範例：**

```
+----------------------------+-------+-------+-------+-------+-------+-------+--------+--------+----------+-----------+
|             配置             |  P@1  |  P@3  |  P@5  |  R@1  |  R@3  |  R@5  | NDCG@3 | NDCG@5 | 平均延遲(ms) | P95延遲(ms) |
+----------------------------+-------+-------+-------+-------+-------+-------+--------+--------+----------+-----------+
|          keyword_no_rerank | 0.867 | 0.378 | 0.227 | 0.713 | 0.860 | 0.860 |  0.875 |  0.865 |      0.4 |       3.0 |
| keyword_lightweight_rerank | 0.933 | 0.378 | 0.227 | 0.780 | 0.860 | 0.860 |  0.900 |  0.890 |      0.3 |       2.1 |
+----------------------------+-------+-------+-------+-------+-------+-------+--------+--------+----------+-----------+
```

### `search_qa/` - 搜尋 QA 測試集

包含用於搜尋品質評估的問答測試數據集。

- `basic.en.json` - 基礎英文測試集
- `basic.zh-Hant.json` - 基礎繁體中文測試集
- `memory_workflow.zh-Hant.json` - 記憶工作流程測試集
- `semantic_hybrid.en.json` - 語義/混合搜尋測試集

### `semantic_index_benchmark.py` - Semantic index backend 基準測試

專門量測 stored semantic index 的 backend 差異：Python full scan/cap 與 sqlite-vec shadow index。輸出會列出延遲、掃描/候選列數、截斷狀態，以及最後一筆 needle 是否能被找到。這可作為改動前後的 before/after 對照基準。

```bash
# 快速 smoke
python3 benchmarks/semantic_index_benchmark.py --sizes 1000 --repeats 3

# 中大型 synthetic benchmark
python3 benchmarks/semantic_index_benchmark.py --sizes 1000 10000 50000 --repeats 5 --output /tmp/semantic-index-benchmark.json
```

重要欄位：

- `p50_latency_ms` / `p95_latency_ms`：同機器上的查詢延遲。
- `backends`：每個 backend 的獨立結果，目前包含 `scan`，若 sqlite-vec 可用則包含 `sqlite_vec`。
- `mean_scanned_rows`：`scan` 代表實際掃描 semantic vectors 數；`sqlite_vec` 代表 KNN 候選數。
- `truncated_runs`：有多少次碰到 scan cap。
- `hit_rate`：needle 插在最後一筆時，有沒有被 top-k 找到。
- `index_rebuild_ms` / `indexed_vectors`：sqlite-vec shadow index 的重建成本與列數。

這些數字只適合同一台機器、同一設定下比較 before/after；不要拿不同硬體或 CI runner 的絕對延遲直接比較。

## 擴展基準測試

### 添加自定義測試數據

編輯 `search_benchmark.py` 中的 `SAMPLE_DOCUMENTS` 和 `QUERY_TEST_SET` 變量：

```python
SAMPLE_DOCUMENTS = [
    {
        "title": "文件標題",
        "content": "文件內容...",
        "category": "類別",
        "tags": ["標籤1", "標籤2"],
    },
    # ...
]

QUERY_TEST_SET = [
    {
        "query": "測試查詢",
        "relevant_docs": [1, 3],  # 相關文件的索引（1-based）
        "relevant_score": [1.0, 0.5],  # 相關性分數
    },
    # ...
]
```

### 添加新的搜尋配置

在 `main()` 函數中添加新的 `run_benchmark()` 調用：

```python
# 自定義配置
print("執行: 自定義配置...")
metrics = run_benchmark(
    db, search, QUERY_TEST_SET,
    mode="hybrid",
    use_rerank=True,
    use_query_expansion=True,
    use_llm_rewrite=True,
    name="custom_config",
)
all_metrics.append(metrics)
```
