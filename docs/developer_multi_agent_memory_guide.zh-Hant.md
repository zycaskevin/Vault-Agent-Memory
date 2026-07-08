# 多 Agent 記憶地基開發者導覽

這份文件用白話說明 Vault Agent Memory 的核心架構：同一台電腦上的多個
agent 怎麼共享一份 Vault，不同主機或 hosted agent 又怎麼安全參與，而不
污染正式記憶。

最短版：

> 單主機可以共享同一份本地 Vault；多主機只能讀已審核記憶、送候選記憶。
> 正式記憶、Dream、封存、同步、中央向量索引，都由 trusted sync host 負責。

## 兩種模式

### 1. 單主機共享

這是最簡單也最強的模式。

```text
Codex / OpenClaw / Claude / Hermes / local scripts
  -> 同一台電腦
  -> 同一個 Vault project
  -> 同一份 vault.db
  -> CLI / MCP / local Gateway
```

重點是 `project_dir`。只要不同 agent 指到同一個 project directory，它們就
是在使用同一份 Vault。

常見入口：

- MCP：日常 agent 使用，像 `vault_search`、`vault_read_range`、
  `vault_propose_memory`。
- CLI：安裝、維護、驗證、修復、報告。
- local Gateway：給不會 MCP 的 local script 或工具一個小 HTTP 入口。

單主機共享仍然不是亂寫。共享記憶建議走 candidate-first：agent 先提出候
選，通過 review / policy gate 後才進正式記憶。

## 2. 多主機 governed sync

不同主機或 hosted agent 不應該拿到 service-role key，也不應該直接寫正式
記憶。

正確流程是：

```text
remote / hosted agent
  -> 用 anon key / scoped token / Gateway token
  -> 讀已審核且有權限的記憶
  -> 提交候選記憶
  -> candidate inbox
  -> trusted sync host 定時拉回
  -> local review queue
  -> review / promote / reject
  -> 正式本地 Vault
  -> Dream / archive / forgetting / report
  -> 推送 approved read copy 和中央向量索引
```

一句話：遠端 agent 可以「投稿」，不能「改百科正文」。

## 角色分工

| 角色 | 可以做什麼 | 不可以做什麼 |
|---|---|---|
| Local agent | 搜尋、bounded read、提交候選、依本地 policy 使用共享 Vault | 跳過 review 直接污染共享記憶 |
| Remote / hosted agent | 讀 approved memory、提交候選 | service-role、正式寫入、Dream、封存、rollback、寫中央向量 |
| Trusted sync host | 拉候選、review、promote、同步 read copy、寫中央向量、產報告 | 把未審核候選當正式記憶 |
| Human reviewer | 核准、拒絕、改 sensitivity、處理衝突 | 無 audit 的靜默刪除 |

## Gateway 在這裡做什麼

Gateway 是一扇小門，不是第二個資料庫。

它適合：

- 不支援 MCP 的 agent；
- local script；
- n8n / Coze 這類 HTTP connector；
- 自架 Remote Server。

Gateway 的安全原則：

- search 不回 raw content；
- read 要 bounded read；
- submit 只建立 candidate；
- 不寫 active memory；
- 需要 token；
- 有 audit log。

目前 Gateway 有這些主要 endpoint：

- `GET /health`
- `GET /openapi.json`
- `POST /search`
- `POST /read-range`
- `POST /submit-candidate`
- `POST /central-candidates/submit`
- `POST /central-candidates/pull`
- `POST /remote-semantic-search`
- `POST /remote-snapshot-read`

其中最後兩個是中央語義讀取鏈：

這兩個 endpoint 比一般 search 更敏感，所以預設是關閉的。要開給非 MCP
agent 使用時，Gateway host 必須同時設定：

- `VAULT_GATEWAY_REMOTE_SEMANTIC_ENABLED=1` 或啟動參數
  `--remote-semantic`；
- `VAULT_GATEWAY_TOKEN_AGENT_MAP` 或 `--token-agent-map`，把每個 token 綁到
  固定 `agent_id`，例如 `token-for-codex=codex,token-for-openclaw=openclaw`；
- request 必須帶目前 Vault 的 `project_id`，除非你明確設定
  `allow_global_public=true` 做 public-only 全域搜尋。

不要讓多個 agent 共用同一個 remote semantic token。Gateway 會以 token 綁定
的 agent 身分執行 policy check；如果 request 自稱另一個 `agent_id`，會被拒絕。
另外，`/remote-semantic-search` 需要把 query text 送到 Gateway 設定的
embedding provider 產生 query embedding。不要把 API key、密碼、客戶私密資料或
未審核原文塞進 query。

```text
/remote-semantic-search
  -> 中央向量索引只回 safe preview + read_handle
  -> 不回 embedding
  -> 不回 raw memory

/remote-snapshot-read
  -> 用 read_handle 讀 approved snapshot 的 bounded preview
  -> 仍然受 agent_id / project_id / sensitivity policy 限制
```

## Supabase 在這裡做什麼

Supabase 是可選的中央 read/candidate surface，不是 active memory 真相源。

它可以放：

- approved read copy；
- candidate inbox；
- safe summary embedding；
- pgvector 中央語義索引；
- policy-aware RPC。

它不應該讓 remote agent 寫：

- active memory；
- revision truth；
- lifecycle state；
- archive / forgetting decisions；
- central vector index rows。

中央向量索引只是「已審核記憶的語義目錄」。它像圖書館目錄，不是書本本
身，也不是館長。

## 一個新 agent 應該怎麼接

### 同一台電腦

1. 選同一個 `project_dir`。
2. MCP-capable agent 接 `vault-mcp`。
3. 不支援 MCP 的工具接 local Gateway。
4. 確認 search、bounded read、propose candidate 都正常。

### 不同主機或 hosted agent

1. 不給 service-role key。
2. 給 anon/scoped credential 或 Gateway token。
3. 只允許 approved read 和 candidate submit。
4. trusted sync host 定時 pull candidate。
5. review 後才 promote。
6. promote 後再 sync approved read copy / central vector index。

## 判斷有沒有做錯

如果出現下面狀況，就是架構跑偏了：

- hosted agent 可以直接寫 active memory；
- candidate 一提交就被其他 agent 搜到；
- remote agent 拿到 service-role key；
- 多個 remote agent 共用同一個 Gateway semantic token；
- remote semantic search 沒帶 project_id 就跨專案搜尋；
- 中央 vector table 變成 remote agent 可寫；
- search 結果直接回 raw private content；
- Dream / archive / forgetting 在非 trusted host 上跑。

正確狀態應該是：

- remote write 永遠先進 candidate；
- candidate 不進 shared semantic index；
- approved read copy 可搜尋；
- full content 仍走 bounded read；
- trusted sync host 才能 promote、sync、Dream、archive、report。

## 開發者心智模型

把 Vault 想成四層：

```text
本地正式 Vault
  真相源。review、promote、rollback、Dream、archive 都在這裡。

Candidate inbox
  投稿箱。local/remote agent 都可以提候選，但候選不是正式記憶。

Approved read copy
  已審核記憶的遠端副本。給 remote agent 安全讀取。

Central semantic read layer
  已審核 safe summary 的向量目錄。用來找相關記憶，再用 read_handle 做 bounded read。
```

這就是 Vault 跟一般記憶庫或純向量資料庫最大的不同：

> Vault 不是讓 agent 直接把所有東西丟進向量桶。Vault 先治理記憶，再讓
> agent 搜尋和讀取治理後的結果。
