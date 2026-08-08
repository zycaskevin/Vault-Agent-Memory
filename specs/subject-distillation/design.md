# Subject Distillation — Technical Design

**Status:** Canonical product contract; frozen bytes record integrity only
**Source reference commit:** `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27`
**Integrity binding:** `baseline-manifest.json` binds the exact five canonical files, their order, byte sizes, SHA-256 values, full digest, and baseline ID. Integrity does not imply review approval, implementation authorization, migration registration, or release authorization.
**Implementation status:** Not implemented and not authorized by this artifact.
**Product:** Vault Agent Memory
**Requirements binding:** subject to the five-file hash-bound manifest contract below；this file declares no requirements verdict
**Target slice:** Generic Subject Core + Person v1；Organization 僅契約與機械相容性
**Repository source reference:** public commit `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27` used for the original inventory；it is not the normative baseline ID、delivery base、reviewed tree或implementation base。

## 1. 設計結論

Subject Distillation 採用「**受治理的Subject領域層**」，而不是把人物資料塞進既有 `knowledge` 列或把 `owner_agent` 擴張成萬用身分欄位。

核心設計如下：

1. **Additive schema**：SQLite schema 升至 v15，以新表保存 subject、principal、證據、assertion、model、relationship、decision episode、policy、grant 與 evaluation；舊 L0-L3、candidate、search、Task Ledger 行為不改。
2. **Immutable provenance boundary**：`explicit` 只能由已綁定且通過surface authentication的subject principal建立；controller、observer、connector或LLM永遠不能靠設定把自己改標成subject。
3. **Candidate-first bridge**：agent/connector產生的Subject候選沿用既有 `memory_candidates` 的privacy/dedupe/quality/review gates，另以typed sidecar保存結構化payload；既有generic promotion不得把Subject candidate直接寫成一般active knowledge。
4. **Versioned projection**：Person v1的描述模型、理想方向、決策政策、授權政策是同一個sealed Subject Model的四類entry；Context Pack是第五個、由model＋grant＋purpose即時生成的最小投影。
5. **Append-only decisions**：decision episode只附加事件，不覆寫原建議、預測、實際選擇、理由或結果；projector計算current view。
6. **Relationship-first third-party governance**：關係是獨立、具方向與時間的edge；counterparty可先是opaque subject reference，perspective assertion不能冒充counterparty canonical self-model。
7. **Local deterministic core**：schema、validator、policy、projection、Context Pack、fragment validator與evaluation gate不需雲端模型；模型只可產生candidate。
8. **Prospective evaluation loop**：pilot manifest與門檻先freeze，close後不可回寫；學習只形成下一gate/model/policy version的候選，永不放寬安全invariant。
9. **Event-time authority, transition-time state**：authority一律以event `occurred_at`對grant半開窗判定；稍後撤銷grant不否定合法歷史event，row source-state、exact kind、single-use replay與timestamp binding則在transition time獨立檢查。Subject lifecycle使用same-Subject grant；global principal status只接受`subject_id IS NULL`的same-principal self-event與event-time-valid auth binding，不發明global admin。
10. **Dependent-first relationship closure**：alias、`relationship_experience`／`perspective` assertion、counterparty control先關閉，再關relationship；只有在endpoint前由有效request切入fail-closed `purge_pending`的deletion cleanup可於relationship結束後完成，endpoint後不得新開request。
11. **Dual-time top-level sealing**：model policy在model generation有效；pack不論entry數量都要在generated/sealed兩時點重驗exact model/model-policy＋grant/access-policy chain。
12. **Complete canonical evaluation header**：scorecard digest以固定欄序/型別綁定explicit eligibility/exclusion/hard-failure/scoring rule versions＋hashes、`created_at`、`frozen_at`、其餘frozen gate semantics及case/event rows；rationale metric沒有reviewable reason/source不得PASS。
13. **Long-term persona alignment without a second SSOT**：Evidence／Memory／Persona-Policy／Runtime是責任與projection邊界，不是四套可互相寫入的資料庫。Behavioral Diff只能成為typed candidate；approved behavior／decision boundary只能由既有Subject policy/model authority封存；persona/session snapshot是無authority的derived projection。Human、agent、model與third-party authorship必須分離，AI-produced material不得因approval/publish直接冒充human-explicit evidence。Dual retrieval、Persona IR、training export與LoRA維持future roadmap，不能擴張B-000或T-001。

## 2. Scope與非Scope

### 2.1 v1必須完成

- Generic Subject Core的資料契約與SQLite持久化。
- Person root subject安全初始化。
- 8種assertion class與不可跨越的provenance規則。
- pointer-only／private-copy／ephemeral證據治理。
- supporting／counter evidence。
- Person v1五個邏輯輸出。
- purpose-limited Context Pack與grant revocation。
- append-only decision episodes。
- directional／temporal relationships與perspective model。
- deterministic Subject Fragment contract validator；不持久化、不傳輸。
- Organization synthetic contract fixtures。
- frozen private-shadow evaluation gate與prospective loop。
- CLI、MCP、Gateway的最小安全surface；actual subject event只接受auth-bound principal。
- v14→v15 migration、legacy smoke、backup/rollback。

### 2.2 v1明確不做

- Organization完整runtime或UI。
- 被動掃描歷史Vault、裝置、聊天或transcript。
- 雲端模型硬依賴。
- remote Subject Fragment import、sync、federation、簽章或trust establishment。
- 自動執行高風險決策。
- 把private shadow資料、真實姓名、私有路徑或dogfood fixtures提交到公開repo。
- 用tool profile代替真正的authorization。

## 3. 現有架構整合點

| 現有元件 | 設計整合 | 不允許的捷徑 |
|---|---|---|
| `vault/db.py` | 僅呼叫新的Subject schema/store helper並維持薄facade；將inspect／legacy-current／migrate模式分開 | 不把全部Subject SQL繼續堆進此檔，也不在status/read時偷偷升級 |
| `vault/db_schema.py` | `SCHEMA_VERSION=15`，新增migration名稱 | 不改既有column語義 |
| `vault/db_migrations.py` | required table set與status加入v15表；v15採離散transactional migration | 不在upgrade時建立subject row、掃描knowledge或先stamp後建表 |
| `vault/db_backup.py` | 增加versioned schema manifest，允許驗證／restore受支援的v14 rollback backup | package target升v15後不能把合法v14備份誤判損壞 |
| `memory_candidates` | 承接Subject proposal的治理狀態 | generic `promote_candidate`不得直升Subject payload |
| `memory_audit_log` | 記錄metadata-only Subject操作與deny reason | 不寫raw evidence、token或完整private payload |
| `vault/access_policy.py`／`governance_read_guard.py` | 沿用scope/sensitivity fail-closed基元，再疊Subject grant/purpose gate | `include_private=true`不是Subject授權 |
| `vault/cli.py` | 掛載`subject` command tree | 不讓CLI body中的`principal_id`自行證明身分 |
| `vault/mcp_tools.py` | profile加入最小Subject tools，handler置於獨立module | tool profile不是authorization boundary |
| `vault/gateway.py`／`gateway_openapi.py` | 新增保守Subject endpoints與contract metadata | bearer body的`agent_id`不能覆寫token binding |
| `vault/cli_quickstart.py` | interactive flow要求root Subject步驟 | upgrade或non-interactive流程不得猜人 |

## 4. 邏輯架構

```text
Authorized source / Subject / Controller / Agent
                  │
                  ▼
        Principal Authentication Adapter
        (CLI capability / Gateway token binding /
         trusted MCP process binding)
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
Subject proposal         Explicit event / review
(candidate-only)         (authority checked)
       │                     │
       ▼                     ▼
existing memory_candidates + subject_candidate_payloads
       │ privacy / dedupe / quality / review
       └──────────┬──────────┘
                  ▼
          SubjectDomainService
  ┌───────────────┼────────────────┐
  ▼               ▼                ▼
Evidence       Assertions       Decision events
  │               │                │
  └──── support/counter ────────────┘
                  │
                  ▼
       Deterministic Model Assembler
                  │
       sealed/versioned Subject Model
                  │
        Subject policy + access grant
                  │
                  ▼
       Purpose-limited Context Pack
                  │
        metadata-only audit record
```

所有mutation由`SubjectDomainService` transaction boundary執行；CLI／MCP／Gateway不得直接寫Subject tables。

## 5. Core contracts

### 5.1 Stable identifiers

- 所有新領域ID使用lowercase UUID字串；API不可接受SQLite rowid當跨surface識別。格式正規化由`SubjectDomainService`的single supported writer在transaction前驗證；SQLite DDL負責FK、unique、state、authority與bounded-code防線，不把完整RFC3339／UUID parser假裝成SQL `CHECK`。直接SQL寫Subject tables不屬於supported surface，測試與runtime writer均不得繞過service。
- `subject_type`為可擴充、可namespace的字串，格式 `^[a-z][a-z0-9_.-]{0,63}$`；built-ins：`person`、`organization`、`team`、`project`、`role`。
- `identity_mode`：`canonical`或`opaque_reference`。Opaque counterparty沒有canonical self-model authority。
- 時間一律為UTC RFC3339；有效區間採`[valid_from, valid_until)`。對event `t=occurred_at`，grant authority的唯一共用predicate是`effective_from <= t AND (expires_at IS NULL OR expires_at > t) AND (revoked_at IS NULL OR revoked_at > t)`，另加exact Subject/principal/role（`event.actor_role = grant.role`）。不得用transition執行時的`revoked_at IS NULL`取代它；grant在event之後撤銷仍可證明合法歷史event。Transition-time只檢查governed row仍可轉移、event未重播、bound timestamp等於event time及row-specific lower bound。
- Subject lifecycle mapping固定為`inactive→subject.inactivated`、`revoked→subject.revoked`、`deleted→subject.deleted`。Event必須same Subject，actor是event-time-valid `subject` grant且`actor_role='subject'`；`controller`不是Subject lifecycle authority。`occurred_at = effective_until >= max(effective_from, created_at)`且`recorded_at >= occurred_at`；一個event id只能綁一筆Subject lifecycle transition。
- Principal status mapping固定為`suspended→principal.suspended`、`revoked→principal.revoked`。這是global self-event：`subject_id IS NULL`、`actor_principal_id`等於被轉移principal、`actor_role='subject'`作為固定self-event分類，authority只來自same-principal在event time有效的physical auth binding。`occurred_at = NEW.updated_at > OLD.updated_at`、`occurred_at >= created_at`且`recorded_at >= occurred_at`；event id單次使用。不得新增或假設`global_admin` role，也不得拿任一Subject grant替代self binding。
- JSON進private store前先schema validate與canonicalize；公開spec/synthetic artifact使用SHA-256，private subject content使用domain-separated HMAC；禁止非有限浮點、隱式datetime與unordered set。

### 5.2 `ValueState`

未知不得被空字串或模型猜值取代。公開payload中的可未知欄位使用：

```json
{"state":"known","value":"option-b"}
{"state":"unknown","reason":"not_reported"}
{"state":"withheld","reason":"policy"}
{"state":"unavailable","reason":"source_revoked"}
```

`prediction_confidence`只附著在predicted choice事件；不得代表rationale或subject reason的信心。

### 5.3 Assertion invariants

`assertion_class`固定為：

- `explicit`
- `controller_attested`
- `third_party_reported`
- `observed`
- `inferred`
- `aspirational`
- `strategic`
- `recommendation`

不可變規則：

1. `explicit`需要`confirmation_event_id`，event actor必須具有當時有效的`subject`角色及同principal Subject auth binding；binding以`created_at <= confirmation.occurred_at`、未到期且`revoked_at IS NULL OR revoked_at > confirmation.occurred_at`判定。只有role grant而無physical auth binding必須拒絕。
2. `controller_attested`、`third_party_reported`不得透過review或config改標`explicit`。
3. `observed`與`inferred`至少一個supporting evidence；`inferred`必須可保存counter-evidence集合，即使集合目前為空。
4. `strategic`需要當時有效的authority source/grant；`recommendation`需要producer policy identity。
5. 每次correct都建立新assertion並`supersedes_assertion_id`；舊列不改寫。
6. `inferred`即使active也保留`assertion_class='inferred'`，renderer以`output_kind='hypothesis'`呈現；其physical namespace仍只能是`canonical`、`relationship_experience`或`perspective`，不會因重複次數升格成explicit。
7. source不可讀或被刪除時改變coverage／confidence state，不複製或捏造來源。

### 5.4 Perspective invariants

`assertion_namespace`：`canonical`、`relationship_experience`、`perspective`。

- `canonical`：`model_owner_subject_id == about_subject_id`。
- `relationship_experience`：`model_owner_subject_id == about_subject_id`且必須有一條該owner參與的exact relationship；它是owner的第一人稱經驗，不是counterparty self-model。
- `perspective`：兩者不同，且必須有`relationship_id`；輸出固定標註「由model owner的證據形成，非counterparty self-model」。
- Primary subject的consent只適用於自己的relationship experience；不能填入counterparty consent或發布authority。

## 6. SQLite schema v15

Subject tables預設位於同一個operator-owned `vault.db`，但raw `private_copy` bytes不放在一般table。所有foreign key、index與trigger由`vault/db_subject_schema.py`集中建立。

### 6.1 Identity、authority與policy

| Table | 關鍵欄位 | 主要invariant |
|---|---|---|
| `subject_installation` | singleton id, `available_uninitialized/initialized_empty/active/archived`, nullable root subject, schema contract version, initialized_at | INSERT只能是`available_uninitialized`；table存在不等於initialized；只允許單向三段轉移，active前必須已有sealed current model |
| `subject_principals` | `principal_id`, `principal_type`, `status`, status event, timestamps | principal是可驗證actor，不等同subject；status transition只接受§5.1 exact global self-event、same-principal event-time-valid auth binding、single-use event與exact timestamp；不建立global admin |
| `subject_auth_bindings` | `binding_id`, `principal_id`, adapter, scrypt salt/digest/parameters, high-entropy fingerprint, issued/revocation events, expiry, revoked_at | INSERT只能是event-bound active；只存不可逆credential material；只能active→expired/revoked且不可恢復、改綁或DELETE；revoke event Subject必須等於original issue event Subject，actor必須是exact `issued_by_principal_id`且其role grant在revoke event time有效，禁止cross-Subject revoke |
| `subjects` | `subject_id`, `subject_type`, `identity_mode`, `is_root`, lifecycle, effective window | v15 migration不自動insert；每Vault至多一個active root；terminal transition依§5.1 exact kind、same-Subject event-time authority、single-use event及`occurred_at=effective_until` |
| `subject_role_grants` | principal, subject, role, domain/scope, authority, quorum, expiry, authority/revocation events | role分離；issue event與revoke event都必須屬於同一subject；既有grant只能單向revoked，不能改role/scope/issuer/event或DELETE；所有event authority使用§5.1 event-time predicate，允許authorizing grant在event後才撤銷 |
| `subject_policies` | kind, subject, version, rules payload ref, status, approved event, effective window, supersedes | INSERT只能是draft；draft→sealed必須綁同subject approval event與active rules payload，approval authority依event time而非transition current-state；sealed metadata immutable；敏感rules可governed purge；新version supersede舊version |
| `subject_delegation_rules` | policy, domain, stakes, reversibility, cost ceiling, approval mode, expiry/revocation event | sealed parent下唯一允許的row mutation是event-bound、單向revoke；recommendation或Context Pack不能隱式產生delegation authority |
| `subject_access_grants` | consumer principal/agent, purpose/task opaque refs or allowlisted codes, domain, output kinds, sensitivity ceiling, expiry, revocation event, policy version | 同Vault連線不等於grant；issue時`policy_id`必須是exact same-Subject、sealed、且分別在authority event time與grant `effective_from`落入policy半開窗的`access` policy，任一時點不符都拒絕；低熵自由文字不寫plain digest；event-bound revocation阻止未來pack |
| `subject_counterparty_controls` | relationship/counterparty, processing basis, authority event, allow-store/model/export bits, export mode, retention, sealed legal policy id/version, legal-hold authority/policy id/version, deletion state | relationship必須精確連接primary→counterparty；consent event必須由當時有效的counterparty subject role發出；consent/legal basis必須綁定同primary、在其event time有效的exact sealed policy，而非要求transition time仍current；`retention_until >= created_at`；legal-hold event必須位於exact sealed counterparty policy window，active hold阻擋deletion completion；primary-only只能`none/primary_perspective_only` export；禁止建立counterparty canonical model |

`principal_type`與surface身份分離。Gateway token、MCP process binding或CLI capability先解析成`principal_id`，再由role/grant決定可做什麼。

`policy_kind`的v1 allowlist明確包含`privacy/review/delegation/retention/counterparty/evaluation/model/access`；model seal只接受`model` policy，Context Pack的access grant只接受`access` policy。任何trigger要求的kind都必須同時存在於table CHECK，合法draft→sealed正例是schema closure必測項。

### 6.2 Events、evidence與assertions

| Table | 關鍵欄位 | 主要invariant |
|---|---|---|
| `subject_events` | kind, nullable subject, actor principal/role, authority ref, source ref, occurred/recorded time, opaque audit id | append-only；confirm/correct/revoke/review/setup均可稽核；Subject lifecycle exact kind/authority/time與global principal `subject_id IS NULL` self-event由dedicated trigger綁定；不含可逆推出private value的plain digest |
| `subject_payload_objects` | subject, payload kind, private adapter, opaque object ref, byte_count, integrity MAC, retention, lifecycle | `(payload_id, subject_id)`是所有child引用的ownership key；evidence/assertion/candidate/alias/decision/purge另驗payload kind；所有可刪敏感value都在DB外private lane |
| `subject_purge_jobs` | payload object, requested authority/event, state, attempts, object-deleted/parent-fsynced/metadata-cleared proof timestamps | job只走`pending→running→succeeded/failed`；metadata清除前必須有同一running job的delete＋fsync proof，job success還必須看到metadata cleared，之後payload才可`purged` |
| `subject_evidence` | controller principal, about subject, retention mode, opaque source identity/locator ref, integrity MAC, availability, sensitivity, effective/retention window, optional payload object, optional supersedes ref | `private_copy`必須引用同about subject的active `private_evidence` payload；全列append-only；availability/retention變化以successor row表示 |
| `subject_assertions` | model owner, about subject, namespace, relationship, class, semantic kind, domain, optional value payload ref, confidence/value state, lifecycle, actor/authority/confirmation/termination refs, sensitivity, policy version, supersedes | known value必須引用同model owner的active `assertion_value` payload；authority/explicit confirmation是exact-kind、role grant event-time有效，且explicit另需confirmation-time active auth binding；`perspective` relationship精確連接owner→about；terminal transition需event且`effective_until >= max(effective_from, recorded_at)`；relationship-bound termination event須在relationship半開窗內（deletion cleanup exception不適用assertion） |
| `subject_assertion_evidence` | assertion, evidence, polarity `support/counter`, weight/notes integrity MAC | 同一evidence可support或contradict不同assertions |
| `subject_candidate_payloads` | existing `memory_candidates.id`, candidate kind, subject, payload contract version, payload object ref, integrity MAC | payload必須是同subject active `candidate_value`；base candidate只存非敏感descriptor；typed sensitive payload不複製進`memory_candidates.content` |
| `subject_candidate_reviews` | candidate id, reviewer principal/role, decision, reason code/optional integrity MAC, reviewed_at | append-only typed review history；base status與sidecar review必須一致 |

`private_copy`預設store adapter是operator-local filesystem private lane，directory mode `0700`、object mode `0600`；系統不宣稱預設加密。其他加密store可由adapter提供，但不得成為core必需依賴。欄位名稱固定為`byte_count`，DB不得有名為`bytes`或可存raw body的BLOB/TEXT欄位。

Standard SQLite backup只備份metadata DB，**不包含**private lane object。Private-lane backup在v1為獨立、明確opt-in操作；未提供受測adapter前不得宣稱可恢復raw object。DB restore遇到missing/expired object ref時，該payload立即標為`unavailable`並讓assertion/pack降級為unknown，不得回填、猜測或從audit digest重建。

Governed deletion分兩個closure transaction。第一個transaction寫delete-request event、建立purge job並把payload切到`purge_pending`；assertion此時尚未宣稱`deleted`，但所有read已fail closed。Worker只可刪除private root內、無symlink escape且MAC/opaque ref相符的object；刪除及fsync parent後，先在同一running job依序寫入`object_deleted_at`、`parent_fsynced_at` proof，再於`purge_pending`原子清空object ref／integrity MAC／byte count。DB trigger要求metadata清除時同一running job已具兩個proof，且job切`succeeded`時locator已清空並寫`metadata_cleared_at`。第二個transaction驗證同一job成功後把payload切`purged`並設定`purged_at`，再以termination event把assertion切`deleted`。Crash只重試同一job；不得在實體刪除、parent fsync與locator清空前宣稱job成功，也不得在job未成功時宣稱purged/deleted。Assertion provenance與event rows不改寫；敏感payload不留在SQLite page/WAL或standard DB backup。

四個proof timestamp是物理序列，不只是non-null旗標：`object_deleted_at <= parent_fsynced_at <= metadata_cleared_at <= completed_at`，且job `updated_at`不可倒退。每一步只允許由前一個state獨立UPDATE到下一個state；時間倒置即使分多個transaction寫入也由table CHECK拒絕。

Public artifact／fixture可用plain SHA-256。涉及subject value、reason、purpose、task、rendered entry或私有來源的完整性識別使用`HMAC-SHA256(vault_audit_key, domain_separator || canonical_bytes)`；低熵值不單獨留下plain digest。Audit key在DB外以`0600`保存並由operator secret backup另管；key缺失時狀態為`unverifiable`，不得改用plain hash補算。

Private-shadow release receipt把這個物理契約固定如下，producer與attester不得各自選格式。Duplicate-key-safe parse後先驗exact key set/type：non-Boolean integer `schema_version=1`、`artifact_kind="private-shadow-release"`、`verdict="PASS"`、bounded opaque `gate_version`、lowercase 64-hex `scorecard_sha256`／`manifest_sha256`、distinct bounded opaque `subject_controller_signoff_id`／`fresh_reviewer_signoff_id`、semantic UTC RFC3339 `created_at_utc`、bounded non-secret `key_id`（`^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`）及lowercase 64-hex `receipt_hmac_sha256`；不接受其他key。`key_id`只從operator-private evaluation-verifier config選定exact HMAC key，receipt、repo及log不得含key。Domain separator是UTF-8/ASCII literal `vault-subject-private-shadow-release-v1`後接單一NUL byte `0x00`，即exact bytes `b"vault-subject-private-shadow-release-v1\x00"`。HMAC message唯一為`domain_separator_bytes || canonical_receipt_without_hmac_bytes`：從已exact-validated object只移除`receipt_hmac_sha256`，再用現有RFC8785-like project canonical JSON contract遞迴排序object keys、UTF-8編碼、移除insignificant whitespace並拒絕non-finite numbers；不加delimiter、length prefix或newline，也不含HMAC欄本身。Result為lowercase 64-hex HMAC-SHA256；verifier重建完全相同bytes並constant-time compare。完整public receipt SHA-256則取包含`receipt_hmac_sha256`之validated canonical receipt bytes。Key/config unavailable、unknown `key_id`、type/key/canonicalization錯誤或MAC mismatch一律fail closed；不得fallback plain SHA-256，亦未新增任何hash algorithm。

T-033的`stable` completed branch不得只把receipt交給attester。Attester必須強制接收operator-private `SUBJECT_PRIVATE_EVAL_VERIFIER`、`PRIVATE_SHADOW_GATE_INPUT`、`PRIVATE_SHADOW_VERIFIER_CONFIG`、`PRIVATE_SHADOW_RELEASE_RECEIPT`四個輸入，以shell xtrace disabled執行唯一固定介面 `reopen-and-verify-release-receipt --gate-input <gate> --verifier-config <config> --release-receipt <receipt> --public-handoff-output -`。Operator-private verifier必須從closed gate重新計算canonical scorecard、所有threshold與兩個distinct signoff，重驗上述HMAC／完整receipt digest，且成功stdout只能是exactly one LF-terminated line `private-shadow-pass:<64 lowercase hex>`；任何失敗必須nonzero、stdout empty，stderr最多一個LF-terminated ASCII line、總長最多96 bytes，且只能是`private-shadow-error:<code>`，其中`code` exact allowlist為`missing-input|verifier-unavailable|unknown-key|invalid-private-input|recompute-mismatch|signoff-drift|threshold-drift|hmac-mismatch|receipt-digest-mismatch|internal-failure`。Attester還要把該digest與完整validated canonical receipt及ledger opaque ref比對後才可產生`stable`。任何missing input、unknown/unavailable verifier、unknown key、recompute mismatch、signoff/threshold drift或digest mismatch都DENY；repo與log不得記錄或echo private path、key、gate、full receipt或private result。Verifier executable由operator-private environment提供，本設計不宣稱repo內存在該executable。

Supported write contract的inline TEXT白名單只允許：stable/opaque ID、enum、UTC timestamp、bounded allowlisted code、non-sensitive public manifest SHA-256。`SubjectDomainService`對每個inline TEXT執行typed validator；DDL另外對所有安全敏感code／opaque locator施作長度、字元、enum、FK與state `CHECK`／trigger。Coverage/exclusion只用具名numeric counts；evaluation rule bodies只存SHA-256。`authority_scope`、`reason_code`、`source_ref`、assertion semantic/domain、relationship role/state、alias purpose與payload object ref均不得接受raw quote、自由文字reason、姓名、聯絡資料、絕對路徑或subject value；需要自由文字時必須走`subject_payload_objects`。T-028同時驗service boundary與DDL已聲明的physical invariants，不宣稱SQLite本身是完整UUID/RFC3339 parser。

Subject proposal固定以`review_required`模式進入base candidate queue。既有`propose_memory(mode="promote_if_safe")`與generic `promote_candidate`不得接受`subject_*` typed payload；這是hard policy，不是呼叫端慣例。

`lifecycle_event_id`與`status_event_id`除FK外還要有dedicated exact-event trigger及single-use partial uniqueness；只驗「same Subject event exists」或只驗欄位變更形狀不算authority。Global principal self-event驗證只查same-principal auth binding的`[created_at, expires_at)`及`revoked_at`event-time窗，不查不存在的global role grant。Subject lifecycle則只查該Subject的`subject` grant；`controller`不具此權限，兩條路徑不得混用。

### 6.3 Models與Context Packs

| Table | 關鍵欄位 | 主要invariant |
|---|---|---|
| `subject_models` | subject, monotonically increasing version, status, generated_at, data window, policy version, producer, numeric coverage counts, confidence/value state, integrity MAC, supersedes | INSERT只能是draft且`generated_at <= created_at`；draft→sealed時entry count、integrity、exact same-Subject sealed `model` policy在`generated_at`有效，以及全部source time/lifecycle必須重驗；child entries只能在draft parent插入；sealed model immutable；current model唯一 |
| `subject_model_entries` | model, output kind, source type/id, domain, ordering, rendered integrity MAC | assertion/policy source必須在model data window相交且於generated_at前已有效；assertion另須同model subject、同domain、active且有required support；policy須同subject sealed且output/policy kind相容；四類stored outputs不複製raw evidence |
| `subject_context_pack_runs` | pack id/version/state, model/grant/consumer, purpose/task opaque refs, model policy, generated/sealed time, action domain/stakes/reversibility/cost scope, numeric include/coverage/exclusion counts, content integrity MAC | pack generated_at不得早於model且`sealed_at >= generated_at`；seal時先在top level重驗exact same-Subject sealed model＋its exact `model` policy及grant＋its exact sealed `access` policy，兩個policy及grant均在generated/sealed兩時點有效，consumer/purpose/task完全一致；此chain與entry count無關，zero-entry pack也必須通過；之後逐entry重驗exact model/source lifecycle/effective window、domain/output/sensitivity及delegation scope；sealed後不能補child或改summary；不保存raw conversation |
| `subject_context_pack_entries` | pack run, assertion/policy/model-entry ref, rendered integrity MAC | 每個ref必須解析到該pack exact model的一個entry，且entry domain/output/sensitivity符合active grant；可重建「包含了什麼」，不寫raw evidence |

`output_kind`：`descriptive`、`aspirational`、`decision_policy`、`delegation_policy`。第五個`context_pack`由前四類與grant即時投影，並以pack run記錄。

### 6.4 Decisions與relationships

| Table | 關鍵欄位 | 主要invariant |
|---|---|---|
| `decision_episodes` | episode id, subject, domain, lifecycle/review state, created event, projection integrity MAC/through-sequence | INSERT只能是`open/unreviewed`且exact created event由同subject有效角色發出；parent每次只投影一個已存在latest child；child semantic delta必須同步review/lifecycle後才可append下一筆 |
| `decision_episode_events` | episode, sequence, kind, actor/authority/source, optional payload object ref, occurred/recorded time | sequence連續且parent已投影前一筆；authority event須為`decision.<event_kind>`且角色有效；terminal event未投影前不能有後續；payload若有必為同episode subject active `decision_event`；metadata immutable |
| `subject_relationships` | from/to subject refs, formal type, source/counterparty roles, lived state, effective window, sensitivity, provenance, lifecycle, termination event | INSERT provenance必須是from-subject的authorized `relationship.recorded`；event actor role必須等於grant role且依event-time predicate；終止使用與target lifecycle相符且時間等於effective_until的exact event，並滿足`effective_until >= max(effective_from, created_at)`；transition前所有alias、`relationship_experience`／`perspective` assertion及counterparty-control window必須已關閉至該時間，或control已由endpoint前有效request進入§8.3 fail-closed cleanup；role/provenance不可改 |
| `subject_aliases` | controller subject, referenced subject, relationship, alias payload ref, purpose code/sensitivity, authority/revocation event, effective window | exact active controller→referenced edge、alias/event/created time位於relationship interval、同controller active `alias_value`與event-bound create/revoke；revoke event本身必須落在relationship半開窗內並使用event-time authority；alias不是identity |

Decision event kinds至少涵蓋：`created`、`context_set`、`options_set`、`constraints_set`、`recommendation_added`、`prediction_added`、`actual_choice_confirmed`、`subject_reason_added`、`outcome_added`、`feedback_added`、`reviewed`、`corrected`。

只有auth-bound subject event或具明確authority的bounded connector source能建立`actual_choice_confirmed`／`outcome_added`；agent推斷只能提交candidate。

Relationship closure的assertion anti-join必須使用`namespace IN ('relationship_experience','perspective')`。依半開窗，只阻擋`effective_from < t AND (effective_until IS NULL OR effective_until > t)`；`effective_until = t`是合法closed positive。Control的`purge_pending` legal positive還必須解析到同control的exact `counterparty.deletion_requested`、event-time-valid primary `subject/controller`或counterparty `subject` authority，且request `occurred_at`位於原relationship interval並`< t`；state label本身不算closure proof。

### 6.5 Evaluation loop

| Table | 關鍵欄位 | 主要invariant |
|---|---|---|
| `subject_evaluation_gates` | subject, per-subject gate version, manifest SHA-256, `eligibility_rules_version`＋`eligibility_rules_sha256`, `exclusion_rules_version`＋`exclusion_rules_sha256`, `hard_failure_rules_version`＋`hard_failure_rules_sha256`, `scoring_definitions_version`＋`scoring_definitions_sha256`, denominator/minimum N/rounding, every overall/domain/abstention/high-confidence threshold, reviewer authority code, state, created/frozen/closed time, scorecard/fingerprint, verdict | INSERT只能draft；每個rule version/hash在draft preregister、freeze時non-null且freeze後不可變；`frozen_at >= created_at`；PASS close由DB機械檢查complete canonical digest、frozen-to-close window、domain/case分布、abstention/correction聯集、overall/domain threshold與hard failure；close後全列不可變 |
| `subject_evaluation_prediction_assessments` | gate/case, `not_emitted` or `reviewed`, privacy-safe predicted/actual choice SHA-256, confidence, mechanically derived correctness, subject principal, bounded source ref, assessed/reviewed time, unique audit id | 每個completed eligible case在close前exactly one；只可在frozen gate由assessment-time與review-time皆有效的same-subject `subject` grant寫入；`not_emitted`的prediction/actual/correctness全NULL，`reviewed`須有lowercase 64-hex hashes、`[0,1]` confidence且correctness等於hash equality；append-only |
| `subject_evaluation_cases` | gate, opaque case id/private integrity MAC, primary domain, abstention/correction/counter-evidence/contextual-constraint flags, eligibility, preregistered exclusion, completion state/disposition time | cases只可在draft INSERT且必須從`preregistered`開始；gate FK不可改掛；frozen期間只可一次性轉`completed/excluded/incomplete`，其餘定義不可變；closed後全列不可變 |
| `subject_evaluation_events` | composite gate/case owner, event type, nullable metric value, passed bit/reason, actor, source, time, opaque audit id | append-only；只有`utility|reason_alignment|abstention|domain_score`是metric-bearing：`metric_value`必須non-null且只允許0/1，`passed=CAST(metric_value)`；`hard_failure`是non-metric assessment，固定`metric_value=NULL`、`passed IN (0,1)`且`reason_code` non-null；每個completed eligible case必有utility/reason/hard-failure，abstention case另有abstention；PASS-eligible `reason_alignment`必須有non-null bounded `reason_code`及reviewable `source_ref`，metric row本身不是rationale；同case/event type至多一筆；actor須有event-time有效同subject評估角色 |
| `subject_evaluation_signoffs` | gate, authority role, principal, decision, time, 64-hex scorecard SHA-256 | signer在INSERT及close皆須為current active，並持有同subject於signed_at半開窗有效的exact mapped role；fresh reviewer另須匹配authority scope；同一principal不能冒充雙角色；subject/controller與fresh reviewer需簽同一scorecard |

SQLite從immutable case/event/prediction-assessment rows機械判定是否達門檻。`subject_evaluation_scorecard_v1`以固定欄序、排序、UTF-8、record separator U+001E、field separator U+001F與`%!.17g` numeric encoding形成canonical bytes。Top-level header依序且帶明確type encoding綁定：scorecard contract version；gate/Subject/gate version；manifest SHA；eligibility rule version＋SHA；exclusion rule version＋SHA；hard-failure rule version＋SHA；scoring-definition version＋SHA；denominator rule；minimum N；rounding rule；utility、reason-alignment、abstention、domain-utility、high-confidence thresholds；reviewer-authority code；`created_at`；`frozen_at`。Version欄位是gate row的explicit frozen data，不得由view硬編字串。其後依序綁定以case id排序的case rows、以case/type/event id排序的event rows、以及以case/assessment id排序的prediction-assessment rows；每列使用明確`C`/`E`/`P` tag、固定欄序、numeric encoding與NULL marker。任一rule version/hash、timestamp、threshold或assessment-only差異必須改變digest。Host連線必須在任何Subject寫入前註冊deterministic `subject_sha256(text)` UDF；`SubjectDomainService`在同一close transaction讀view重算digest；DDL transition再讀同一view比對`NEW.scorecard_sha256`，兩份signoff亦須相同。缺UDF、缺任一version/hash、`frozen_at < created_at`、pre-freeze/future-to-close timestamp、missing rationale representation、completed eligible case缺exactly-one prediction assessment或任意caller digest都fail closed。PASS另要求不存在`reviewed` assessment同時滿足`prediction_confidence > high_confidence_threshold`且choice hash不相等；等於threshold不觸發。`not_emitted`只報告、不進此hard-failure判定；prediction choice正確但rationale被拒絕本身也不是此prediction hard failure（rationale仍由其獨立門檻判定）。這不是宣稱SQLite內建SHA-256，而是versioned host function contract。下一版調整使用既有candidate queue＋typed payload；closed pilot不因adjustment改分數、分母或verdict。

Evaluation event、prediction assessment與signoff在INSERT及frozen→closed皆重驗authorization。Event actor須為current active且在`occurred_at`至少持有一個同Subject `subject|controller|reviewer` grant；assessment subject principal須為current active且同一`subject` grant同時覆蓋`assessed_at`與`reviewed_at`；signer須為current active，並由`fresh_reviewer -> reviewer`、其他authority role原樣映射exact role，fresh reviewer authority scope亦須匹配gate。所有grant窗皆為半開：`effective_from <= t`、`expires_at IS NULL OR expires_at > t`、`revoked_at IS NULL OR revoked_at > t`。因此晚於dependent row時間的撤銷不抹除合法歷史，等於或早於該時間則close fail closed。Principal status只有current state而無temporal interval，故採保守reviewed規則：INSERT與close當下都必須為`active`；這可能拒絕曾暫停後恢復的歷史（且v15目前沒有恢復transition），但不會把無法證明的歷史active狀態當成合法。這些是close-time mechanical anti-join，不加入scorecard fingerprint。

### 6.6 DB-level guards

除service validation外，v15必須建立trigger／constraint：

- append-only audit/domain metadata禁止UPDATE/DELETE；可刪內容只存在`subject_payload_objects`指向的private lane，並僅允許normative purge state transition。
- sealed model/policy的child禁止INSERT；Context Pack只允許draft→sealed一次關閉；frozen gate禁止新增case，closed gate禁止新增event/signoff。
- active root subject唯一partial index。
- current model per subject唯一partial index。
- relationship interval與model/assertion temporal query有index。
- context pack／evidence／assertion按subject、status、sensitivity索引。
- foreign keys在測試與runtime均`PRAGMA foreign_keys=ON`。
- read-write connection在執行任何Subject DDL/write前註冊deterministic `subject_sha256`；缺失時evaluation scorecard query/close必須失敗，不得降級為只驗64-hex。
- 所有exact-authority trigger共用§5.1 event-time grant predicate；focused lint禁止在該predicate殘留無時間限定的`g.revoked_at IS NULL`。Transition row的current state另行檢查，兩者不得混寫。
- Subject lifecycle與global principal status使用各自§5.1 exact mapping、authority、single-use及timestamp trigger；禁止用generic same-row event FK代替，也禁止讓global principal event借用Subject grant。
- relationship closure trigger必須在parent transition檢查alias、兩種relationship-bound assertion namespace與control；只有endpoint前有效request已切`purge_pending`可視為closed。Pack/model top-level seal、evaluation header digest及zero-entry legal positives不得依賴child-loop副作用。
- evaluation freeze與digest必須讀gate row上四組explicit rule version/hash及`created_at`/`frozen_at`；hard-coded version literal、只hash不version或漏timestamp都fail closed。

完整column type、nullability、default、CHECK、FK action、partial index與trigger定義以同目錄`schema.v15.sql`為normative physical contract；本節表格僅是語義索引。SQL contract必須能在empty SQLite DB transaction中直接parse，且不得建立root subject或讀legacy content。

v15不在本docs-only變更中偷偷提高現有runtime floor，因此`schema.v15.sql`暫不使用SQLite 3.37才提供的`STRICT` table。安全與canonical型別必須由顯式`CHECK`／trigger加上`subject_contracts.py` typed validator雙重保護；SQLite affinity本身不算驗證。若fresh review判定必須改用`STRICT`，必須先另案更新受支援SQLite版本、upgrade preflight與相容性測試，不能只在DDL加一個關鍵字。

## 7. Services與module boundaries

每個production module目標不超過約600行；超出前先拆分。

| Module | Responsibility |
|---|---|
| `vault/subject_contracts.py` | enums、dataclasses、ValueState、canonical JSON、pure validators |
| `vault/db_subject_schema.py` | v15 DDL、indexes、triggers、required table names |
| `vault/db_subject_store.py` | typed CRUD與transaction-local queries，不做policy判斷 |
| `vault/subject_auth.py` | surface identity→principal binding；credential hash／revocation |
| `vault/subject_policy.py` | role、authority、assertion transition、grant、purpose/sensitivity decision |
| `vault/subject_candidates.py` | existing candidate bridge與typed promotion dispatch |
| `vault/subject_evidence.py` | evidence metadata、retention modes與source availability；private adapter只作thin call |
| `vault/subject_private_evidence.py` | 唯一operator-local private object/purge adapter |
| `vault/subject_privacy.py` | 唯一Subject redaction與inline scalar validator facade |
| `vault/subject_assertions.py` | assertion lifecycle、support/counter evidence、correction/deletion |
| `vault/subject_models.py` | deterministic assembly、version seal、coverage/confidence recalculation |
| `vault/subject_context.py` | Context Pack minimization、render、audit metadata |
| `vault/subject_decisions.py` | append-only event validation與projection |
| `vault/subject_relationships.py` | directional roles、alias、perspective boundary |
| `vault/subject_fragments.py` | pure in-memory contract/lifecycle validator；禁止DB/network I/O |
| `vault/subject_evaluation.py` | preregistration、freeze、score、close、signoff、next-version candidate |
| `vault/subject_service.py` | public domain facade與transaction orchestration |
| `vault/cli_subject.py` | CLI handlers only |
| `vault/mcp_subject.py` | MCP tool schemas/handlers only |
| `vault/gateway_subject.py` | Gateway request adapters only |

`VaultDB`只公開小型delegating methods或`subject_store`property，不讓surface依賴raw connection。

## 8. Authorization與disclosure decision

### 8.1 Principal authentication

`principal_id`是authorization input，不是proof。Surface必須提供不可偽造的binding：

- **Gateway**：server-side token fingerprint→principal/agent mapping；body中的ID只能與binding一致，不能覆蓋。
- **MCP**：server啟動時綁定trusted process principal/capability；tool argument不可自行提升principal。未綁定時只能proposal或pure validation。
- **CLI**：root setup bootstrap後，subject/controller mutation需從stdin/OS secret source提供capability；DB只存scrypt/hash與fingerprint，不回顯secret。一般讀取仍需role/grant。

Authentication與authorization分開判定：`explicit` confirmation除了event-time-valid Subject role grant，還要有same-principal auth binding在confirmation `occurred_at`有效。歷史判定使用binding的created/expiry/revoked時間窗，不要求該binding在較晚transition時仍是current active；但沒有binding、binding在confirmation前已撤銷/到期、或綁到另一principal都fail closed。

Global principal status transition沿用同一physical-binding時間窗但不綁任一Subject：event `subject_id`必須為NULL、actor必須是被轉移principal自己、kind與target status exact match，且`actor_role='subject'`是固定self-event分類。若same-principal binding在event time前不存在、已到期或已撤銷，transition fail closed；任一Subject上的controller／subject grant都不能補足，也沒有`system`或`global_admin` fallback。

Tool profile只控制暴露面與schema token量，**不是**安全邊界。

Root bootstrap採明示的local TOFU（trust on first use）邊界：只允許本機interactive TTY、project owner OS account、`subject_installation=available_uninitialized`，且subjects/principals/bindings/role grants皆為零。Setup在一個transaction建立一個human principal、root subject、分離的`subject`與`controller`role grants，再於最後一步切換installation state。角色可由同一human principal持有，但authority仍以兩條grant稽核；Gateway、MCP、non-interactive setup與request-body identity都不能進入bootstrap。

| Authority transition | 唯一允許者／proof | Fail-closed rule |
|---|---|---|
| 初始root subject＋subject/controller binding | 上述empty-state local TOFU setup capability | 非empty、非TTY、非project owner或任何remote surface一律拒絕 |
| Subject inactive/revoke/delete | exact target-kind lifecycle event；event-time有效same-Subject `subject` grant（controller無此權限） | Subject/kind/actor-role、`occurred_at=effective_until`、lower bound或single-use任一不符即拒絕；transition-time current state與event-time grant分開檢查 |
| Global principal suspend/revoke | exact `principal.suspended`／`principal.revoked` self-event＋same-principal event-time-valid auth binding | event必須`subject_id IS NULL`、actor=self、single-use及`occurred_at=updated_at`；不接受另一principal、任一Subject grant或虛構global admin |
| 新增／旋轉subject auth binding | 目前有效的subject principal capability | controller/reviewer/consumer不能代簽；新binding成功後才atomic revoke舊binding；revoke必須回指original issue event的同一Subject，由exact `issued_by_principal_id`以event-time有效同Subject role執行，另一Subject上的authority不可重用 |
| 新增／撤銷controller | subject principal；可受已sealed quorum policy加嚴 | controller不能自我提升為subject或解除subject revocation |
| 發放bounded consumer/access grant | controller在same-Subject sealed/effective `access` policy明定scope內 | `policy_id` kind/Subject/version/window任一不符即拒絕；不得產生subject role、counterparty consent或high-risk authority |
| Reviewer決定candidate／pilot signoff | 明定review role且綁定同一artifact digest | reviewer不能發grant、綁subject或修改payload |
| Subject credential recovery | setup時一次性產生、owner離線保存的recovery capability＋local interactive flow | DB不存recoverable secret；controller/reviewer無recovery權；只可輪替同一subject binding，不可更換subject identity |
| Recovery capability遺失 | 無自動fallback | v1停止並要求governed manual migration；禁止以「同機器／同帳號」自動重建subject authority |

所有binding issue/rotate/revoke/recover與role/access/delegation grant transition都需append-only exact event，authority一律依§5.1的event-time predicate；grant在事件後撤銷不使歷史事件失效。Transition執行時另驗row仍是可轉移current source state及lower bound，並以stable deny reason區分event-authority失敗與transition-state失敗。Credential material使用scrypt/Argon2-compatible KDF contract；若實際依賴未提供Argon2，v1必須使用stdlib-supported scrypt，不可降級為plain SHA-256。

### 8.2 Context Pack fail-closed algorithm

`generate_context_pack(subject, consumer, purpose, task, requested_domains)`：

1. 驗證auth-bound consumer principal。
2. 讀exact access grant及它的policy；grant issuance本身必須已綁same-Subject sealed `access` policy，並分別證明policy在issuance event `occurred_at`與grant `effective_from`落入`[policy.effective_from, policy.effective_until)`，不得只驗其中一個時點。再檢查subject、consumer、purpose、task、domain、output kind、sensitivity ceiling，並以grant的`[effective_from, expires_at)`加`revoked_at IS NULL OR revoked_at > t`分別驗`generated_at`與`sealed_at`。
3. 鎖定同subject的一個sealed current model及其exact sealed `model` policy；pack的`model_id/policy_id`必須是這一組，model/access兩個policy都須在generated/sealed兩時點有效，且`sealed_at >= generated_at`。
4. 只取effective-current entries；歷史資料需明確historical request及另行grant。
5. 對每個assertion執行既有governed-read基元＋Subject policy。
6. 排除raw evidence、private-copy object refs、無權third-party data與未授權perspective assertions。
7. 依purpose/domain/task做deterministic minimization；超budget時先移除低相關項目，不能靠提高敏感度補足。
8. 產生typed pack，保留class、namespace、confidence/unknown、effective window、coverage summary、model/policy/producer version。
9. 寫metadata-only pack run、entry refs、deny/exclusion counts與audit event；seal trigger先做與entry count無關的top-level exact-chain核對，再逐entry revalidate。Zero-entry pack不能繞過model/access policy、grant dual-time或timestamp gate。

Pack payload預設`action_authority: false`，此時action domain/stakes/reversibility/cost欄位必須全部為NULL。只有在draft→sealed同一交易中顯式設定`delegation_rule_id`及完整action scope，且該rule屬同一Subject的sealed delegation policy、`approval_mode=bounded_autonomy`，rule與policy均在`generated_at`及`sealed_at`有效（包括`revoked_at IS NULL OR revoked_at > t`），並逐欄匹配grant domain與rule的stakes/reversibility/cost ceiling/currency，才可設true；rule/policy才是authority source，Pack只帶可稽核引用。即使為true，高風險或不可逆action仍由執行系統的獨立guard處理。

### 8.3 Counterparty processing、export與deletion

R-SD-018採deny-by-default processing state。沒有active `subject_counterparty_controls`時，只能保存primary subject自己的第一人稱perspective assertion，counterparty使用opaque reference，且不得存counterparty raw quote、聯絡資料、self-model或可匯出profile。

允許的`processing_basis`只有：`subject_perspective_only`、`counterparty_consent`、`legal_obligation`。每列必須引用精確連接primary→counterparty的active relationship，且`retention_until >= created_at`。`subject_perspective_only`只能由primary的有效subject/controller以`counterparty.perspective_authorized`建立；`counterparty_consent`只能由counterparty有效subject以`counterparty.consent_granted`建立；`legal_obligation`與legal hold只能由primary上event-time有效`authority_source`分別以`counterparty.legal_obligation_recorded`、`counterparty.legal_hold_created`建立。後兩者另綁purpose、allowed operation、retention window與同primary的exact sealed legal-policy id/version；legal-hold event必須位於該policy的`[effective_from,effective_until)`。Primary-subject event永遠不能manufacture counterparty consent。Control row的basis、authority、export mode、legal hold與purpose建立後不可原地改寫或DELETE；revocation、deletion request/completion分別只接受allowlisted lifecycle event與event-time有效角色，並走單向transition。要改scope必須先revoke current row，再插入帶`supersedes_counterparty_control_id`的新row；同一primary/counterparty/purpose最多一個未撤銷current row。

Relationship close採兩步驟：先把所有alias、`relationship_experience`／`perspective` assertion及counterparty control的有效窗關到proposed `effective_until=t`，再transition relationship；任一dependent仍符合`effective_from < t AND (effective_until IS NULL OR effective_until > t)`就拒絕parent close，等於`t`則依半開窗視為已關閉。Control也可由exact、event-time-authorized `counterparty.deletion_requested`先切入不再允許store/model/export/pack/disclosure的`purge_pending`；request必須綁同control、位於原relationship半開窗且`occurred_at < t`，因此invalid/replayed/at-endpoint/post-endpoint event或單改state都不能讓parent close。Alias revoke與兩種relationship-bound assertion termination event必須在relationship半開窗內。唯一例外是上述已於有效期內開始的deletion cleanup：保留同一pre-endpoint request後，`counterparty.deletion_completed`可在relationship結束後發生，但必須晚於request、使用completion event time有效的primary `controller/authority_source` grant、在completion time沒有`legal_hold_until > occurred_at`，且只完成purge/deidentify bookkeeping，不能恢復或延長任何processing/export/model/disclosure權。Relationship一旦到endpoint，任何新的deletion request一律拒絕。

- **Ingestion：** 缺basis、過期、revoked或超出purpose時拒絕；connector只能提candidate，不能建立counterparty canonical assertion。
- **Primary-subject export：** 可輸出自己的perspective與去識別relationship metadata；預設排除counterparty raw payload、self-fragment與獨立識別資料。
- **Counterparty export：** 只接受auth-bound counterparty principal，且只輸出其self-fragment或雙方共同授權的bilateral artifact。
- **Deletion：** counterparty payload、consent與self-fragment有獨立purge scope；primary subject的合法第一人稱notes不因此被改寫，但必須解除／去識別counterparty link。Request建立時立即deny所有use，且只有relationship endpoint前的valid bound request可在endpoint後completion。Completion必須保留同一request binding且晚於request；`legal_hold_until > completion.occurred_at`時必須拒絕。Legal hold需位於exact sealed policy window、最小保留與expiry，不可用永久boolean規避刪除。
- **Audit：** export/delete/deny只記opaque IDs、authority/policy version與counts，不留被拒內容或低熵plain digest。

## 9. State machines

### 9.1 Subject capability

```text
available_uninitialized
        │ explicit setup-root
        ▼
initialized_empty ── first sealed model ──▶ active
        │                                  │
        └──────── governed archive ────────▶ archived
```

v15 legacy migration的installation INSERT只能落在`available_uninitialized`；policy、model及evaluation gate INSERT只能落在各自的draft起點，decision episode只能從`open/unreviewed`建立。終態不得由INSERT直接宣告。該狀態由`subject_installation`singleton決定，不由「表是否存在」或root row猜測；只有完整setup transaction最後一步可切為initialized。New interactive quickstart必須完成setup-root；non-interactive或直接`vault init`不猜測subject，回傳明確next action。

`subjects`與`subject_principals`的row state machine亦不得只靠UPDATE shape：前者每次terminal transition綁§5.1 exact same-Subject lifecycle event，後者每次status transition綁§5.1 exact global self-event。兩者都要求single-use event與exact timestamp，且保留event-time authority／transition-time current-state分離。

### 9.2 Assertion

```text
candidate (existing queue)
  ├─ reject/blocked
  └─ approved typed promotion
        ▼
reviewed/active ── superseded ──▶ historical
        ├─ revoked (future disclosure denied)
        └─ governed deletion ──▶ tombstoned metadata
```

### 9.3 Model／policy

```text
candidate_version ── validate+approve ──▶ sealed/current
       ▲                                  │
       └──── next candidate ◀── supersede─┘
```

### 9.4 Evaluation

```text
draft ── preregister+freeze ──▶ frozen/running ── close ──▶ closed PASS|FAIL
                                                              │
                                         next-version candidate only
```

Freeze transition必須滿足`frozen_at >= created_at`；case disposition、metric event及signoff仍全部限制在`[frozen_at, closed_at]`。

## 10. Public surfaces

### 10.1 CLI

命令群：

```text
vault subject status
vault subject setup-root
vault subject principal bind|revoke
vault subject propose
vault subject review
vault subject confirm|correct|revoke|delete-request
vault subject model build|show
vault subject context-pack
vault subject decision create|append|show
vault subject relationship add|end|alias
vault subject grant create|revoke
vault subject fragment validate
vault subject evaluation init|freeze|record|close|signoff|propose-next
```

- 所有machine-facing命令支援`--json/--pretty`與stable error code。
- `vault subject status`、`vault_subject_status`與`GET /subject/status`是同一個read-only contract：只能呼叫`VaultDB.inspect(path)`，不得經`VaultDB.connect()`／compatible open；missing、empty、v14、v15、unsupported、contradictory輸入都只回狀態，且不得create DB、journal/WAL/SHM/lock/sidecar、改bytes/hash或stamp schema。
- secret只從stdin、環境secret reference或OS adapter取得，不出現在argv、stdout、audit。
- `review`對Subject typed candidate走專用promotion；generic `vault memory promote`遇Subject candidate須fail closed並指向正確命令。

### 10.2 MCP

`core` profile可加入：

- `vault_subject_status`
- `vault_subject_propose`
- `vault_subject_context_pack`
- `vault_subject_fragment_validate`

`review/maintenance/full`再加入review、model build、decision append、grant/evaluation工具。任何actual/explicit mutation仍需server-side principal binding；未綁定時回`principal_auth_required`。

### 10.3 Gateway

新增：

- `GET /subject/status`
- `POST /subject/proposals`
- `POST /subject/events`
- `POST /subject/context-packs`
- `POST /subject/fragments/validate`

Gateway不新增「下載完整Subject Model或raw evidence」的預設endpoint。Controller/reviewer inspect可先留在local CLI；若未來加HTTP read，需另經contract review。

OpenAPI `x-vault-subject-safety`必須揭露：candidate-first、principal binding required、private by default、raw evidence excluded、action authority independent、remote fragment persistence false。

## 11. Main flows

### 11.1 New interactive root setup

1. `quickstart`完成既有agent setup。
2. 顯示用途與privacy boundary，不掃描任何既有來源。
3. 使用者明確提供subject type、controller principal與subject principal關係。
4. 建立principal、auth binding、root subject、subject/controller role grants、一份sealed `privacy` default-private policy及一份sealed `model` policy；兩者皆是empty-safe、同Subject、具獨立version與approval event。
5. 先把installation切到`initialized_empty`，再以exact sealed `model` policy建立empty sealed model v1（coverage為empty/unknown；不產生人格內容），最後在同一setup transaction切到`active`；任何中途失敗整體rollback，因此成功setup不對外停留在`initialized_empty`。
6. 回傳minimal proposal與Context Pack surface；無access grant時pack只有安全metadata或deny。

### 11.2 Agent observation proposal

1. Agent提交bounded source及typed candidate。
2. 寫`memory_candidates`與`subject_candidate_payloads`，狀態candidate。
3. 執行privacy/dedupe/quality/provenance gates。
4. Reviewer核准後由typed dispatcher建立evidence/assertion或decision candidate event。
5. 若聲稱`explicit`但缺subject auth confirmation，降為candidate／`third_party_reported`或拒絕，絕不靜默升格。

### 11.3 Subject correction

1. Auth-bound subject提交correction event。
2. 建立新的`explicit`或`aspirational` assertion；引用confirmation event。
3. 舊assertion被新列supersede，保持歷史可查。
4. 下一model version重算；current Context Pack不再回舊assertion。

### 11.4 Decision feedback

1. 建立episode與context/options/constraints events。
2. Agent recommendation／prediction各為獨立events；prediction confidence只綁choice。
3. Actual choice／subject reason／outcome分別追加，有未知就輸出ValueState unknown。
4. Projector產生current view但不改過往event。
5. Model calibration讀事件與counter-evidence產生candidate，不自動promotion。

### 11.5 Evidence source loss

1. Connector或operator追加`evidence_unavailable` event。
2. Evidence metadata保留，private object如政策要求則purge。
3. 找出dependent assertions與models，重算coverage／confidence。
4. 新model version標示unavailable；不回傳hidden copy或虛構來源。

## 12. Subject Fragment validator

Pure function：

```python
validate_subject_fragment(
    fragment_payload,
    lifecycle_payload,
    expected_binding,
    authority_context,
    local_perspective_assertions=(),
    bilateral_artifacts=(),
) -> FragmentValidationResult
```

輸出含`accepted`、`normalized_lifecycle_state`、stable error codes、content fingerprint、conflicts。它必須：

- 驗subject、issuer、issuer-to-subject authority/consent scope、origin Vault、counterparty binding、version、fingerprint、audience、purpose、sensitivity、effective/expiry、onward-sharing、revocation ref及coverage summary。
- 預設拒絕raw evidence。
- 拒絕unauthorized issuer、binding mismatch、unverifiable revocation。
- 保持remote fragment、local perspective、bilateral artifact三條來源，不互相覆寫。
- 不開DB、不寫檔、不call network、不建立trust、不持久化。

## 13. Organization compatibility

Organization fixture使用同一`subjects`、`subject_assertions`、`subject_role_grants`、`subject_policies`與Context Pack contract：

- official strategy為`strategic` assertion並有authority event/grant。
- team habit為`observed`且scope為team-local。
- employee preference不會成為organization policy。
- strategy v2以supersession取代v1 current view，v1保留歷史。
- role-scoped pack使用相同grant/purpose/minimization。

禁止在generic core新增`person_*`必填column；Person專用內容放在typed payload與domain service。

## 14. Migration、backup與rollback

### 14.1 v14→v15

目前`VaultDB.connect()`會立即執行`_init_tables()`，而`vault db status`也會先開啟會變更schema的connection。v15新增以下concrete API；既有約120個`VaultDB(path)`call site不需逐一改參數：

```python
VaultDB(path, schema_mode="compatible")        # default
VaultDB.inspect(path)                           # readonly URI, no DDL/write lock
VaultDB.migrate(path, backup_path, target=15)   # only explicit migration entry
db.require_schema(15, capability="subject")
```

`compatible`是唯一default：不存在／空DB時建立current v15；一致v15正常開啟；一致v14只開legacy tables且不DDL、不stamp，legacy memory操作維持可用；Subject call回`schema_upgrade_required`；版本低於14或metadata矛盾則fail closed。只有`cmd_db_status`、backup preflight改用`inspect`，只有`cmd_db_migrate`可呼叫`migrate`，所有Subject service入口先呼叫`require_schema`。因此call-site plan是central constructor semantic change＋三類明確adapter，不是盲改120處。

`inspect`以SQLite immutable/readonly URI或等價的無寫入方式開啟：missing path回`missing`且不得建立檔案；empty path回`empty`；一致v14/v15回版本與capability；unsupported或三個version signals／manifest不一致回明確error。任何`inspect`／`vault db status`路徑都不得建立sidecar、切換journal mode、執行DDL、commit、寫migration row或改變DB bytes；pre/post SHA-256與missing-file測試必須證明此點。WAL-mode DB的inspect與backup必須用SQLite connection snapshot語義，不能只複製主`.db`檔。

`backup_path`是caller選定的new-file target：migration開始前若任何filesystem
object已存在即回`backup_exists`且不得開啟、覆寫、截斷、替換或刪除。每個
attempt建立backup後保留其opened descriptor identity；cleanup只可unlink該
attempt新建且pathname仍解析為同一regular-file identity的backup。Identity
不符、pathname被替換或任何pre-existing target一律停止並保留現況，回
`backup_cleanup_unsafe`；不得以清理失敗為理由操作不屬於本attempt的path。

Schema version authority集中於`vault/db_schema.py::SCHEMA_MANIFESTS`。每個受支援version明列table、column、index、trigger與migration IDs；`db_migrations.py`、`db_backup.py`與status共同import。`config.schema_version`、`PRAGMA user_version`與applied migration rows必須全部一致；禁止現行`max(...)`容錯。任何缺值、超前、分歧、manifest shape不符回`schema_metadata_inconsistent`，不得自動修正。

所有`VaultDB` read-write connection生命週期持有`vault.db.schema.lock`的shared OS advisory lock；explicit migrate取得exclusive lock並等待既有connection結束。鎖內流程：

1. 在同一條source connection上做readonly manifest preflight確認一致v14，記`PRAGMA data_version=d0`；
2. 在exclusive advisory lock仍持有時，以WAL-aware SQLite online backup建立v14 snapshot並依v14 manifest驗證；不得以raw file copy取代；
3. 在同一條source connection取得`BEGIN IMMEDIATE`，再讀`data_version=d1`；若`d1 != d0`，代表有不遵守advisory lock的外部writer，立即rollback、依上述identity rule只刪除本attempt新建backup並重試整個snapshot/preflight cycle，絕不migration；每次explicit migrate最多三次attempt（initial + two retries），第三次race後回stable `migration_source_raced`，不得有任何migrator-authoredDDL/version/migration-row變更且不得保留本attempt backup；外部writer已提交的合法資料變化原樣保留，不宣稱source全檔byte-identical；不得無限重試或在race後繼續DDL；
4. 同一transaction建立additive tables、indexes、triggers與`subject_installation=available_uninitialized`；最後才寫migration/config/`PRAGMA user_version`；
5. commit後仍持有exclusive lock，跑v15 manifest/integrity verification；失敗即停止並保留verified v14 backup，不切runtime；
6. 釋放lock後，`subject status`回`available_uninitialized`。不修改舊knowledge/candidate/task、不建立root subject、不掃描檔案。

直接使用raw sqlite而繞過VaultDB lock不屬於supported writer；`data_version`二次檢查仍封住backup完成至write reservation之間的race。重跑migration只得到相同schema；中斷不得留下v15 marker或initialized state。

### 14.2 Fault injection

每個DDL group需可注入fault。失敗時transaction rollback；若SQLite環境造成已存在的前段DDL，重跑仍需idempotent且capability不得誤報initialized。

### 14.3 Rollback

`verify_backup`需按備份自身schema version選擇manifest；package target為v15時仍能驗證受支援的v14 backup。它不得用「一定要等於目前package SCHEMA_VERSION」拒絕rollback來源。

不提供破壞式down migration。正式rollback為：

- 停止新runtime；
- 在temporary path驗證pre-migration backup；
- restore成獨立DB；
- 使用舊版runtime跑compile/search/read/propose/promote smoke；
- 比對knowledge與governance metadata；
- 只有驗證通過才切換project path。

這避免刪新表時誤傷private Subject data。文件必須明示rollback會捨棄migration後Subject-only變更，需另行受治理export／archive，而非偷偷混回legacy DB。

## 15. Evaluation與release label

### 15.1 Deterministic invariants（100%）

- permission leakage = 0
- false explicit self-attribution = 0
- unsourced actual choice/outcome = 0
- temporal/supersession錯誤 = 0
- unauthorized high-stakes action = 0
- legacy migration/rollback failure = 0

任何一項失敗立即FAIL，loop不能放寬。

### 15.2 Mechanical SBE

Repo保存synthetic manifest，將43個SBE ID映射到pytest node id。Manifest check要求：

- 18個E-P、5個E-O、20個E-F各有至少一個機械test。
- test node存在且可collect。
- fixture不含真實person/org資料、home path、secret或remote dependency。

### 15.3 Private shadow gate

Evaluator使用所有完成且符合預先登記資格的案例`N`，`N>=20`；至少三domain、每domain至少5、至少5 abstention probes、至少3 correction/counter-evidence/context cases。

- utility pass：`ceil(0.80*N)`
- reason alignment pass：`ceil(0.80*N)`；每個PASS-eligible reason event都要有non-null bounded `reason_code`與可review的`source_ref`，只有metric/`passed`即失敗
- abstention：所有preregistered abstention probes中至少80%
- 每domain usefulness：所有該primary domain eligible cases至少60%
- `>0.80` hard rule只看錯誤subject-choice prediction
- correct choice＋rejected rationale只算reason failure；若另構成material misrepresentation則hard fail
- scorecard fingerprint必須是64位小寫hex SHA-256；canonical header按§6.5固定順序/型別綁定manifest、四組explicit eligibility/exclusion/hard-failure/scoring version＋hash、denominator、minimum N、rounding、所有threshold、reviewer authority、`created_at`及`frozen_at`；任一version/hash/timestamp/threshold-only paired DB必須不同digest；所有metric event必須有bounded numeric value與明確`passed` bit，不得用NULL規避
- PASS close由DB gate trigger機械核對上述domain/case分布、overall/domain門檻及hard-failure；subject/controller與fresh reviewer必須是不同principal，且各自在signoff時持有同subject有效role並對同一scorecard簽核

Synthetic pass但shadow未pass時只能標`experimental`；不宣稱「理解」subject，也不授權高風險action。

## 16. Test strategy與順序

固定順序：

1. **Unit**：pure validators、state machine、policy、projection、rounding。
2. **Fixture**：43個SBE、Person／Organization／Fragment／migration synthetic fixtures。
3. **Surface contract**：CLI JSON、MCP schemas/handlers、OpenAPI/Gateway auth binding。
4. **Legacy regression**：existing compile/search/read/propose/promote、backup/restore、full pytest。
5. **Private live/shadow**：僅operator private Vault；不進repo，不在synthetic gate前執行。

Current contract alignment要求bounded direct-SQL DENY＋legal ALLOW pairs涵蓋既有authority／temporal矩陣，並補：Subject lifecycle exact target-kind/authority/replay/timestamp；global principal NULL-Subject self-event、same-principal event-time binding及no-global-admin negative；access policy同時在issuance與grant `effective_from`有效；closure同時阻擋`relationship_experience`與`perspective`跨endpoint窗；只有endpoint前valid request的`purge_pending`可使parent close且立即deny use；endpoint後new request DENY但pre-endpoint request later completion ALLOW；四組explicit evaluation rule version/hash freeze及digest對version、`created_at`、`frozen_at`的paired divergence。Manifest只供mechanical byte identity；review結論必須綁定exact baseline或changed-path diff並依§20.1風險規則記錄，本設計不自行宣告其結果。每個negative fixture必須對準目標guard，不能先被無關FK/time check擋下。

最低命令：

```bash
python -m pytest -q tests/test_subject_contracts.py
python -m pytest -q tests/test_subject_db_schema.py tests/test_subject_store.py tests/test_subject_migration.py
python -m pytest -q tests/test_subject_assertions.py tests/test_subject_context.py
python -m pytest -q tests/test_subject_decisions.py tests/test_subject_relationships.py
python -m pytest -q tests/test_subject_fragments.py tests/test_subject_evaluation.py
python -m pytest -q tests/test_subject_cli.py tests/test_subject_mcp.py tests/test_gateway.py
python -m pytest -q tests/test_db_migrations.py tests/test_db_backup.py tests/test_cli_json_contract.py
python -m pytest -q
ruff check vault tests
python scripts/readme_command_smoke.py
python scripts/check_release_parity.py
```

## 17. Requirements traceability

`traceability.md`是本design package的normative 43-example mapping；下表保留requirement-level摘要。Implementation不得把T-003當成重新決定example ownership的授權。

| Requirement | Design sections | Primary verification |
|---|---|---|
| R-SD-001 | 5.1, 6.1, 13 | generic subject + org fixture |
| R-SD-002 | 2, 6.2, 15.2 | fixture privacy scan |
| R-SD-003 | 5.3, 6.2 | assertion transition unit tests |
| R-SD-004 | 5.3, 6.2, 11.5 | provenance/support/counter/source-loss tests |
| R-SD-005 | 5.3, 9.2 | hypothesis visibility/anti-promotion tests |
| R-SD-006 | 5.1, 6.2-6.4, 9 | temporal/supersession tests |
| R-SD-007 | 6.1, 8.1 | role separation/impersonation tests |
| R-SD-008 | 6.3, 8.2 | Context Pack leakage matrix |
| R-SD-009 | 5.2, 6.4, 11.4 | append-only episode/projector tests |
| R-SD-010 | 6.3, 8.2 | five-output acceptance fixture |
| R-SD-011 | 8.2 | action authority independence tests |
| R-SD-012 | 6.1-6.4, 9 | revoke/correct/delete tests |
| R-SD-013 | 13 | organization authority fixtures |
| R-SD-014 | 2, 7, 12 | no-network deterministic tests |
| R-SD-015 | 3, 9.1, 14 | legacy migration/rollback suite |
| R-SD-016 | 15 | invariant/SBE/shadow gate evaluator |
| R-SD-017 | 4, 11.2 | source adapter candidate-only tests |
| R-SD-018 | 5.4, 6.4, 8.2 | third-party minimization matrix |
| R-SD-019 | 6.3, 8.2 | model/pack metadata inspection tests |
| R-SD-020 | 13 | E-O plus generic-column check |
| R-SD-021 | 6.2, 11.5 | retention mode/source-loss tests |
| R-SD-022 | 6.4, 11.4 | multi-role/alias/temporal tests |
| R-SD-023 | 5.4, 6.4, 12 | perspective/canonical conflict tests |
| R-SD-024 | 12 | pure fragment validator tests |
| R-SD-025 | 9.1, 11.1, 14 | quickstart vs legacy state tests |
| R-SD-026 | 6.5, 9.4, 15.3 | frozen-gate/no-post-hoc tests |

Fresh design closure需同時hash-lock `requirements.md`、`design.md`、`tasks.md`、`schema.v15.sql`與`traceability.md`。

## 18. Risks與mitigations

| Risk | Mitigation |
|---|---|
| Subject schema過大、`db.py`再膨脹 | schema/store/service分檔；`VaultDB`只delegate |
| Body提供principal_id造成impersonation | server-side auth binding；ID mismatch fail closed |
| Raw private evidence洩漏到DB/log | private lane adapter；metadata-only audit；secret/payload scans |
| Generic candidate promotion繞過typed gates | Subject memory type在generic promote明確拒絕 |
| Context Pack因「有用」而過度揭露 | grant→purpose→domain→sensitivity→minimization固定順序 |
| Counterparty變成偽canonical model | namespace＋model owner/about subject＋relationship invariant |
| Model rebuild改寫歷史 | immutable assertions/events；sealed version refs |
| Pilot結果不好後改門檻 | DB freeze trigger＋scorecard fingerprint＋雙signoff |
| Migration成功但回報錯誤initialized | capability state由`subject_installation`singleton決定，不由table/root existence決定 |
| `db status`或一般open先於backup偷偷升級 | readonly inspect＋explicit migration；v14 legacy操作與Subject capability gate分離 |
| v15 runtime拒絕合法v14 rollback backup | versioned schema manifest，依backup版本驗證 |
| generic candidate自動promotion繞過Subject review | 強制`review_required`＋generic promotion hard block＋append-only typed review |
| Private pilot污染open-source fixtures | separate operator DB；repo privacy scanner |

## 19. Rejected alternatives

1. **把Subject欄位加進`knowledge`**：會混淆文章知識與subject assertion，也無法表達actor、counter-evidence、authority、perspective與append-only decision。
2. **把`owner_agent`當controller/subject**：違反角色分離，也讓agent identity冒充human authority。
3. **讓LLM直接產生active model**：無法保證typed provenance、candidate gate與可重現性。
4. **把Context Pack存成完整JSON blob**：增加撤銷後殘留與raw copy風險；v1只保存entry refs與domain-separated integrity MAC。
5. **直接down-migrate刪Subject tables**：容易不可逆遺失private data；採verified backup restore。
6. **v1做live fragment sync**：需要federated identity、簽章、revocation與trust establishment，超出已核准scope。
7. **只靠MCP tool profile保護資料**：profile只減少tool surface，不是authorization。

## 20. Design approval gate

本節不自行宣告technical-design verdict。`baseline-manifest.json`只機械驗證top-level五檔hash、canonical full digest、baseline ID與frozen state；review結論記錄於PR、task return packet或其他owner-visible work record，並綁定被審查的baseline或diff。Review PASS不等於implementation、merge、release或production授權。

Design completion conditions（normative；review深度依風險選擇）：

- 風險適當的review確認P0=0、P1=0；
- schema能機械表達Person v1與Organization fixture，無person-only core column；
- principal authentication與role authorization無自我聲明漏洞；
- migration、interrupt recovery、backup rollback具可測試路徑；
- 43個SBE均可映射到明確fixture/test layer；
- tasks.md只描述待授權implementation，不把文件PASS誤當coding批准。

Technical design verdict: `NOT_SELF_DECLARED`

### 20.1 Risk-based review record

The review record must identify the exact baseline or changed paths, reviewer,
verdict, P0/P1/P2 counts and unresolved findings. It may live in the PR, task
return packet or another owner-visible work record; a canonical repo-external
JSON body, locator and digest are not required.

Docs-only process changes require mechanical validation plus one focused review.
Changes to authentication, authorization, security controls, migration, privacy,
public interfaces or production behavior require one independent reviewer. Final
merge, release and production gates may require broader review under their own
contracts. No agent may use its own review record to create owner authority.

## 21. Pre-implementation bootstrap and receipt protocol

The first executable pre-task is B-000, before T-001. It is a local-only,
non-product bootstrap that may create exactly:

- `scripts/verify_subject_implementation_authorization.py`
- `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`
- `tests/test_subject_authorization_bootstrap.py`

B-000 is not a T-task, is absent from `implementation-progress.json`, and cannot
authorize itself. Its trusted operator channel and exact repository-owner
instruction form the sole explicit human bootstrap trust root; the repository
cannot cryptographically prove that private channel. Neither B-000 nor any
implementation agent may self-authorize, infer authority from integrity/review
PASS, or create/rewrite that instruction. B-000 permits no product/runtime/data,
production migration, deployment, release, private-live-data or destructive
operation. Git publishing is outside B-000 and requires separate explicit owner
authorization.

The receipt schema is JSON Schema 2020-12 with `additionalProperties:false` at
every object layer and exactly these required top-level fields: `schema_version`
(non-Boolean integer, const `1`), `artifact_kind` (string, const
`subject-distillation-implementation-authorization`), `baseline_id` (string,
`^[0-9a-f]{16}$`), `baseline_full_digest` (string, `^[0-9a-f]{64}$`),
`authorizing_principal` (string, const `github:zycaskevin`), `authorized_task`
(string, `^T-[0-9]{3}$`), `scope_sha256`, `authorization_verifier_sha256`, and
`authorization_schema_sha256` (each string, `^[0-9a-f]{64}$`),
`issued_at_utc` and `expires_at_utc` (semantic RFC3339 UTC `Z`; expiry strictly
later than issue and unexpired at verification), and `authorization_id`
(string, `^[0-9a-f]{64}$`). No other top-level field is allowed.

B-000 may not modify package metadata or add a runtime dependency. The canonical
schema therefore uses only this fixed JSON Schema 2020-12 subset: `$schema`,
`$id`, `type`, `properties`, `required`, `additionalProperties`, `const`, and
`pattern`. The verifier implements and tests that exact closed subset with the
Python standard library; it does not import `jsonschema`, resolve remote `$ref`,
or claim to be a general JSON Schema evaluator. Schema-shape tests reject every
keyword outside the subset and prove the fixed receipt checker accepts/rejects
the same required/property/type/const/pattern/additional-property matrix.
Semantic timestamps, canonical bytes, cross-field digests and freshness remain
explicit verifier checks outside JSON Schema.

`authorization_id` is SHA-256 of UTF-8 canonical JSON for the receipt with only
`authorization_id` omitted, using `sort_keys=True`, separators `(',', ':')`,
and `ensure_ascii=True`. It is an integrity identifier, not a signature. Human
authenticity is owner-confirmation-bound, not hash-generated: after B-001 is
accepted, the trusted operator channel requests a candidate proposal for an
exact task/base. The reviewed runner's stateless `propose` mode derives the
candidate canonical receipt/scope bytes in memory, creates no private object,
and returns their complete canonical public-safe proposal. The owner separately
confirms that exact proposal and full receipt-file SHA-256；only then does one
`verify-confirmed` process re-derive and temporarily materialize the exact bytes
and pass the confirmed digest through `--expected-receipt-sha256`. The verifier
recomputes and exactly matches
the receipt bytes, scope file, its own script, canonical schema, current
baseline ID and full digest, semantic timestamps, and authorization ID. It
proves byte binding and substitution resistance after owner confirmation；
it does not independently prove the human identity/channel and cannot turn an
agent-generated receipt, digest, manifest or review PASS into owner authority.

There are two separate scope boundaries. B-000 has no receipt or persisted
bootstrap-scope artifact. Its exact write allowlist is:

1. `scripts/verify_subject_implementation_authorization.py`
2. `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`
3. `tests/test_subject_authorization_bootstrap.py`

The preflight derives and verifies the baseline ID、full digest and this allowlist
from the selected commit. A valid trusted owner instruction contains exactly the
decision-bearing values `lane=B-000` and `implementation_base_commit=<lowercase
40-or-64-hex commit>`；the selected commit must be clean and contain the validated
canonical bytes. Derived manifest or scope hashes need not be repeated in chat.
The owner message itself is the instruction；a hash, review PASS or agent-created
replacement cannot authorize B-000.

For a T-task, authorization is two-stage and unavailable until B-001 is
accepted. First, the owner requests a proposal for `lane=T-NNN` at an exact
clean implementation base commit. This permits only a stateless public-safe
proposal, never private materialization or implementation. Preflight requires `git
rev-parse HEAD` to equal that commit and requires its tree to contain the
validated baseline. The parent returns the exact task/base、baseline ID/full
digest、complete sorted `allowed_repo_relative_paths`、`non_goals` and
`prohibited_operations` arrays、issue/expiry timestamps、scope SHA-256、full
receipt SHA-256、schema/verifier SHA-256 values and `proposal_id`. Second, the
owner confirms that exact immediately preceding canonical proposal and receipt
SHA-256. An ambiguous、stale、partial or cross-task
confirmation is DENY. The second message remains the sole human implementation
authorization trust root；the reviewed runner is only its bounded materializer
and executor. Any changed field or byte requires a new proposal and confirmation.

The LF-terminated canonical proposal JSON is a closed object with exactly:
`schema_version` (integer `1`), `artifact_kind`
(`subject-implementation-proposal`), `authorized_task`,
`implementation_base_commit`, `baseline_id`, `baseline_full_digest`,
`authorizing_principal`, complete
sorted `allowed_repo_relative_paths`、`non_goals` and
`prohibited_operations`, strict UTC `issued_at_utc` and `expires_at_utc`,
`scope_sha256`, `receipt_sha256`, `authorization_verifier_sha256`,
`authorization_schema_sha256`, `authorization_id`, and `proposal_id`. Its canonicalization is the
same `json.dumps(..., sort_keys=True, separators=(',', ':'),
ensure_ascii=True) + '\n'` rule. `proposal_id` is the SHA-256 of those canonical
bytes with only `proposal_id` omitted. The runner fixes the validity window at
15 minutes, rejects future-issued proposals and treats equality at expiry as
expired. Unknown fields、duplicate keys、noncanonical bytes or identifier/hash
mismatch are DENY.

The T-task receipt scope-file contract alone is the inline
`subject-distillation-implementation-scope` contract here; B-000 must not add a
scope schema file. It is one object with exactly these required fields and no
others (`additionalProperties:false` semantically at every object layer):
`schema_version` (exact builtin integer `1`, not Boolean), `artifact_kind`
(const `subject-distillation-implementation-scope`), `baseline_id`
(`^[0-9a-f]{16}$`), `baseline_full_digest` (`^[0-9a-f]{64}$`),
`authorized_task` (`^T-[0-9]{3}$`), `allowed_repo_relative_paths`, `non_goals`,
and `prohibited_operations`. The baseline values byte-match the verified
manifest and the task byte-matches both receipt and `--expected-task`.
`allowed_repo_relative_paths` has 1..64 unique, strictly Unicode-code-point
sorted 1..256-character ASCII strings. Each is a normalized POSIX
repo-relative path: no leading slash, backslash, control, empty/`.`/`..`
component, duplicate separator, or trailing slash. T-001 lists only paths that
T-001 expressly owns and grants nothing to T-002+. `non_goals` has 1..16
unique, strictly sorted 1..128-character ASCII values matching
`^[a-z][a-z0-9]*(?:[._:-][a-z0-9]+)*$`. `prohibited_operations` has 1..16
unique, strictly sorted members of this closed vocabulary: `commit`, `deploy`,
`github`, `live_private_data`, `migration`, `pr`, `product_runtime`, `push`,
`release`, `remote_network`, `stage`. T-001 contains all except it may omit
`migration` or `product_runtime` solely for an operation
expressly required by T-001, which grants no broader operation.

The `remote_network` task prohibition governs product/service calls and access to
remote or private data during the authorized task. It does not prohibit the
public dependency installation described by tasks §0 before task execution；that
setup may not use a private index, credential or private source without separate
authority. Dependency or package-metadata changes remain outside B-000/T-001
unless expressly scoped.

The scope rejects duplicate keys, non-exact builtin types, non-finite numbers,
missing/unknown fields, and unsorted/duplicate/out-of-bound arrays. Its bytes
must equal UTF-8 encoding of `json.dumps(value, sort_keys=True,
separators=(',', ':'), ensure_ascii=True) + '\n'`; `scope_sha256` hashes those
exact bytes.

Operator-private `--receipt` and `--scope` accept only normalized absolute paths
outside the repository. After B-001 is accepted and the owner requests a
proposal, `propose` derives the exact candidate bytes in memory only and must
not persist or inject them. After owner confirmation of the complete canonical
public-safe proposal and exact receipt digest, `verify-confirmed` re-derives
those bytes from the proposal、current HEAD、validated manifest、fixed task
scope and current schema/verifier bytes before creating private files. The
current verifier enforces semantic UTC timestamps with
`issued_at < expires_at` and current time strictly before expiry；this contract
does not claim that it enforces a maximum lifetime、future-issue rejection、file
permission bits or post-verification deletion. Generated paths and contents
must never be copied into repo/evidence or echoed. Canonical `--manifest` and `--schema`
accept only the exact repo-relative strings
`specs/subject-distillation/baseline-manifest.json` and
`specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`.

B-001 authorization is mission-bound rather than message-bound. Once the
repository owner has approved a Subject/Person development mission under the
repository's Human-on-the-loop operating model, the Main Engineering Agent may
start B-001 without asking the owner to restate `lane=B-001` or an exact commit.
Before any B-001 write, the Main Agent must not select an arbitrary local
commit. It must mechanically select clean HEAD that byte-equals current remote
`main` or an independently reviewed Subject protocol-amendment PR head in the
approved mission chain, validate the canonical baseline from that exact tree,
and record the provenance proof、base commit、baseline ID/full digest、exact
two-path write allowlist and owner mission/decision reference in owner-visible
Issue/PR metadata or a task return packet outside the repository tree. The
preflight record must not create or modify a third B-001 repository path. HEAD、
baseline or scope drift requires a new clean-base preflight record under the
same approved mission, not another owner prompt. Base selection is auditable
execution metadata, not a human-authenticity claim；it cannot authorize T-001、
change the B-001 allowlist、
waive independent security review or infer authority from hash/review PASS.
The two-stage owner-confirmed proposal protocol below remains mandatory for
every T-task.

Post-B-000 governance bootstrap B-001 must create the reviewed
`scripts/run_subject_implementation_authorization.py` parent runner and
`tests/test_subject_authorization_runner.py`. The runner owns every control
outside verifier scope and is stateless across invocations. `propose` performs
read-only derivation and emits the canonical proposal only；it creates no
receipt/scope file、persistent proposal registry、daemon、IPC endpoint、background
process or private locator. Restart simply re-derives a newly requested
proposal. `verify-confirmed` accepts the exact canonical proposal JSON, checks
its `proposal_id` and owner-confirmed receipt digest, and re-derives every field
from current HEAD、the validated baseline、the fixed task scope and the fixed
schema/verifier bytes. It rejects unknown、partial、noncanonical、stale、expired、
future-issued、cross-task or drifted input before private creation.

Only after those checks, `verify-confirmed` disables inherited xtrace and
creates one fresh normalized repo-external directory with exact mode `0700`
and exactly `receipt.json`/`scope.json` regular non-symlink files with mode
`0600`. The same process retains parent-directory、candidate-directory and file
descriptors plus device/inode identity from creation through verification；
requires the directory member set to remain exact；rechecks identity、mode、
canonical bytes and the owner-confirmed digest immediately before invoking the
existing verifier；and never prints a path、private argv or content.

Cleanup is descriptor-relative and identity-checked. It unlinks only the two
owned entries when current no-follow identity equals the retained identity,
then removes only the identity-matching candidate directory through its retained
parent descriptor and proves the three names absent. Replacement or identity
drift is never pathname-deleted；the runner returns a bounded public-safe
`private_cleanup_required` result and stops. Signal handlers clean safely and
terminate nonzero rather than swallowing interruption. PASS、DENY、ERROR、
timeout、exception and every signal path must run the same lifecycle state
machine. An identity-safe repo-external advisory lock uses nonblocking
acquisition for concurrent `verify-confirmed` calls on the same repo/task/base,
so exactly one may proceed and every concurrent loser is DENY. A byte-identical,
unexpired replay before T-001 starts may reverify but has no implementation side
effect；once the progress ledger records T-001 as `IN_PROGRESS`、`BLOCKED` or
`COMPLETED`, replay is DENY. No proposal state persists between processes.
The runner checks that progress state both before private creation and again
after verifier success but before any PASS return. If the ledger appears、
becomes invalid or records any T-001 non-`PENDING` state during that interval,
the runner completes identity-safe cleanup and returns DENY；the advisory lock
does not substitute for this post-verifier state check.
T-001 may continue only after verifier PASS and verified cleanup；until B-001
implementation、restart/replay/concurrency and hostile replacement/mode/
extra-entry/signal tests plus independent review pass, private materialization
remains unavailable.
Production starts at repo root, discovered once by `git rev-parse
--show-toplevel`; its strict-decoded absolute physical result must byte-match
the no-symlink physical cwd. The verifier self-hashes its own regular bytes at
fixed repo path `scripts/verify_subject_implementation_authorization.py`; no
caller path can replace it.

Lexical validation precedes access. Operator-private receipt/scope arguments
must be absolute normalized POSIX paths and reject NUL, backslash, and any
empty, `.`, or `..` component. Start from an opened `/` directory fd. Repo
canonical input arguments must byte-equal their fixed repo-relative paths;
start from an opened repo-root directory fd and apply the same component
rejections. For both classes, open each component relative to the prior dirfd
with Linux/Python descriptor APIs (`os.open(..., dir_fd=prior_fd)`) and
`O_NOFOLLOW`; require each ancestor to be a directory and the final object to
be a regular file. The three fixed repo inputs are the manifest, schema, and
verifier paths stated above. Mount points and bind mounts are not independently
forbidden: security derives from descriptor lineage, no symlink following,
fixed lexical components for repo inputs, bounded reads from the same final fd,
and stable identity.

The explicit byte cap is 1,048,576 bytes separately for each receipt, scope,
manifest, schema, and verifier file. Reject a pre-read `st_size` over its cap,
then read at most cap+1 bytes from that same final fd and reject an extra byte or
a length inconsistent with the audited size. The exact pre/post `fstat` tuple
is `(st_dev, st_ino, st_mode, st_size, st_mtime_ns)` and any change is DENY;
repeat the comparison immediately before PASS while retaining all descriptors.
No `Path.resolve`, `realpath`, pathname reopen, undefined physical/lexical alias
comparison, or mount-device comparison is an authorization decision. Mutation,
replacement, short/extra data, non-regular input, or any race is DENY. One
central cleanup closes descriptors in reverse acquisition order.

After byte-bounded parsing, each JSON artifact also has deterministic structural
limits: maximum nesting depth 32, maximum 32,768 aggregate JSON values/object
members/array elements visited by the duplicate-key-safe parser and scanner, and
maximum 4,096 members in any one object or array. Exceeding a limit is DENY, not
an internal recursion error. Tests must include exact-boundary ALLOW and one-over
DENY controls without allocating attacker-proportional secondary copies.

Parsing is duplicate-key-safe and checks exact builtin JSON types. Recursively
scan receipt, scope, manifest and schema using the sole public-safety scanner
grammar normative in `tasks.md` §1. That section exclusively defines recursive
key/value traversal, normalized forbidden keys, exact regexes, digest-field
handling, the private-shadow namespace exception, and one fixed manifest-domain
exception. That manifest exception applies only when the direct owning key is
byte-exact `domain_separator_utf8_hex` and the value is byte-exact
`7375626a6563742d64697374696c6c6174696f6e2d626173656c696e652d76310a`；
it is not a generic 66-hex allowance. Any key spelling/separator/case mutation or
value prefix/suffix/case/content mutation is DENY. Named DENY and ALLOW fixtures
required there are reused by progress and authorization, alongside path/no-follow/
race and no-echo tests. No copied or second scanner grammar is permitted here.

Local development and focused tests may run on any supported host. The
descriptor/no-follow/race suite must also pass on Linux with supported Python
3.10+ in CI before merge or release. The return packet names OS and Python
versions for each gate run so local evidence is not confused with the Linux gate.

Missing, unknown or duplicate CLI arguments (including repeated flags), absent
mandatory `--json`, and all caller-controlled absent/unreadable/malformed/
mismatched/expired/unsafe/racing inputs are DENY. Only unexpected internal
programmer or harness faults after safe classification are ERROR. No raw
exception/path/key/value/content is echoed. `--json` is mandatory and the only
production verification output mode; help/version/discovery cannot emit PASS.
The trusted clock is local OS UTC wall time read as timezone-aware UTC. Both
timestamps are semantic canonical RFC3339 UTC `Z`, issue is strictly before
expiry, and `now >= expires_at_utc` is DENY. Production has no caller-controlled
clock override; a non-CLI test seam may inject one.

Success is exit `0`, empty stderr, and exactly one LF-terminated compact JSON
stdout object with exact keys `authorization_id`, `authorized_task`,
`baseline_id`, `status`, where `status` is `PASS` and values match the verified
receipt/current baseline. The object uses `json.dumps(..., sort_keys=True,
separators=(',', ':'),
ensure_ascii=True) + '\n'`, so its exact key order is `authorization_id`,
`authorized_task`, `baseline_id`, `status`. A deny is exit `2`, empty stdout,
and exactly
`SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n` on stderr. Unexpected internal or
harness failure is exit `3`, empty stdout, and exactly
`SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n` on stderr. No path, hostile
key/value, token-shaped value, or receipt content may be echoed.

After exact-tree B-000 testing and its independent security review, no T-001 authority is implied.
T-001 requires its actual verified receipt. Old baseline, review, and
authorization evidence does not transfer after canonical byte changes.
