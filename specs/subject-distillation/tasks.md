# Subject Distillation — Implementation Tasks

**Status:** Canonical product contract; frozen bytes record integrity only
**Source reference commit:** `09a0f4c08f2f7479a01c9b6c083dd3cd0e564c27`（inventory reference only；not the normative baseline ID、delivery base、reviewed tree或implementation base）
**Integrity binding:** `baseline-manifest.json` binds the exact five canonical files, their order, byte sizes, SHA-256 values, full digest, and baseline ID. Integrity does not imply review approval, implementation authorization, migration registration, or release authorization.
**Implementation status:** Not implemented and not authorized by this artifact.
**Target:** Generic Subject Core + Person v1；Organization contract-only

## 0. 使用規則

這份文件是hash-bound implementation plan，不是coding授權，也不自行宣告plan verdict。B-000與T-001各自只能在其明列條件全部成立後開始；review PASS或hash本身從不授權implementation。

1. `baseline-manifest.json`通過mechanical integrity validation，證明top-level five-file hash/full-digest/baseline-ID/frozen-state binding成立；
2. docs-only process change完成mechanical validation與focused review；auth/security/migration/privacy/public-surface change完成一位independent reviewer的risk-based review，且P0=0、P1=0；
3. B-000已完成並通過exact-tree review；owner-approved Subject/Person development mission成立後，Main Engineering Agent可在不要求owner重貼`lane=B-001`或exact commit的情況下完成B-001 identity-safe runner與獨立security review，之後owner才可要求exact T-001/base proposal；stateless runner只回傳canonical public-safe proposal且不落地private bytes，owner另行確認完整proposal與exact receipt SHA-256後，單一`verify-confirmed`程序才可重建、驗證actual bytes綁定exact `baseline_id`、full digest、task及scope並完成安全cleanup；
4. B-001開始前由Main Engineering Agent機械選定current clean HEAD；它不得是任意local commit，必須byte-equal於current remote `main`或approved mission chain中已獨立review的Subject protocol-amendment PR head。Owner-visible Issue／PR metadata或task return packet在repo tree外記錄provenance proof、exact implementation base、validated baseline ID/full digest、owner mission/decision reference與exact兩-path allowlist；preflight不得建立或修改第三個B-001 repo path，且沒有未解的外部變更。這項base紀錄不是T-task授權。

執行紀律：

- SBE → SDD → TDD；每個behavior先有紅燈測試。
- 一次只做一個task；不得把`BLOCKED`標成完成。
- 每個behavior-bearing implementation slice的執行順序固定為：unit/contract → synthetic fixture behavior → surface contract → legacy regression → private live/shadow。T-002只建立public synthetic taxonomy並跑fixture privacy/schema unit gate，不執行Subject behavior或live資料，因此可在T-004前作preflight；不得把這個例外外推到behavior tests。
- Implementation agent負責coding；reviewed runner可在owner要求後產生不含private locator的canonical public-safe proposal，但只有owner對完整proposal與exact receipt digest的第二次確認才能允許同一`verify-confirmed`程序materialize/verify/cleanup並授權implementation；需要時由independent reviewer進行risk-based review；designated release authority獨立決定implementation authorization。
- 本檔所有checkbox是immutable contract bullets，永遠不表示execution status；baseline freeze後不得因task開始、阻塞或完成而改動checkbox。
- 每個task的唯一current status只存在`specs/subject-distillation/implementation-progress.json`；完成必須先追加合法ledger transition、附public-safe evidence refs，並由`python scripts/validate_subject_progress.py`實跑`PASS`。所有`BLOCKED`狀態也只記入該ledger，不得改本檔。
- `CHANGELOG.md`按coherent product／security／docs review unit更新，不按task status逐筆更新；不得以CHANGELOG取代progress ledger。
- 不把真實person/org資料、private pilot內容、secret、home path或remote credential放入repo。
- Auth、security、migration、privacy、production或public-surface變更需要一位independent reviewer；docs-only與低風險內部變更使用mechanical validation加focused review。

所有task共用stop/checkpoint：RED測試若因normative contract缺失、互相矛盾或需新增business/security決策而無法寫出，立即停止；T-001 strict control plane尚未建立前，只能在repo外owner-visible task packet／Issue記錄bounded public-safe `BLOCKED`，不得fabricate ledger。T-001 seed成功後，所有`BLOCKED`只可由atomic writer寫入progress ledger。不得用implementation選擇補規格。每個task至少在「RED原因符合spec」「GREEN只改approved scope」「verify命令實跑」「risk-based review適用時PASS」四個checkpoint留證據，未過checkpoint不得進下一task或phase。

在任何B-000或T-001命令前，從repo root建立或重用project-local環境：

```bash
test -x .venv/bin/python || python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
command -v python
python --version
```

`.venv/`必須已gitignored；supported Python依package contract為`>=3.10`。既有有效`.venv`可直接重用；一般package index/network dependency install可用，不得使用未授權private index、credential或private source。Dependency/package metadata變更仍是獨立review scope。Setup或`command -v python`失敗即阻塞該lane，不得silent interpreter/dependency substitution。

`.venv/`、Python cache與pytest cache是gitignored local setup/runtime artifacts，
不屬於T-task delivery tree或reviewed source allowlist；它們不得被stage、引用為
evidence或包含private input。T-001唯一允許的same-directory transient write是其
proposal明列的`specs/subject-distillation/.implementation-progress.pending`。

## 1. Closure artifacts

Implementation完成時至少交付：

1. `specs/subject-distillation/requirements.md`（normative requirements；不在檔內自宣告verdict）
2. `specs/subject-distillation/design.md`（normative design；review record依risk-based policy保存）
3. `specs/subject-distillation/tasks.md`（immutable execution contract；不是status evidence）
4. `specs/subject-distillation/schema.v15.sql`（normative physical schema contract）
5. `specs/subject-distillation/traceability.md`（design-approved 43-example mapping）
6. `specs/subject-distillation/sbe-traceability.json`（implementation closure的43個SBE→collected pytest node）
7. `specs/subject-distillation/baseline-manifest.json`（mechanical byte-identity/integrity evidence only）
8. `specs/subject-distillation/evidence/<baseline-id>/environment.json`
9. 同目錄`unit.txt`、`fixture.txt`、`surface.txt`、`legacy.txt`（完整命令、UTC、exit code與stdout/stderr artifact ref）
10. 同目錄`migration.json`、`backup-restore.json`（manifest/hash/rollback evidence）
11. 同目錄`fresh-review.json`（review ids、tree/hash、P0/P1/P2與verdict）
12. 同目錄`attestation.json`（artifact SHA-256與release label）
13. private shadow若尚未PASS，release label明確為`experimental`
14. `specs/subject-distillation/implementation-progress.schema.json`（progress ledger的strict schema）
15. `specs/subject-distillation/implementation-progress.json`（唯一mutable task-status control plane）
16. `scripts/validate_subject_progress.py`（duplicate-key-safe progress validator）

`<baseline-id>`唯一來源是hash-verified `baseline-manifest.json.baseline_id`（16位小寫hex）；authorization preflight後的acceptance命令先執行`BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"`與`EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"`，不得保留字面`<baseline-id>`或由Git object format／commit SHA另算同名ID。Baseline ID reading只證明identity；需要execution authorization的operation必須另行呼叫fail-closed authorization runner驗證release-authority receipt，不能由identity reader、manifest或review PASS推論。T-001把preflight `git rev-parse HEAD`原值加exact `git:` prefix後記入`environment.json.source_commit`，並要求suffix byte-equal且object-format length一致；它不是baseline ID。Artifact producer固定為：T-001→`environment.json`；T-027→`migration.json`與`backup-restore.json`；T-029→`unit.txt`、`fixture.txt`、`surface.txt`、`legacy.txt`與`sbe-traceability.json`；T-031→三份`reviews/*.json`及`fresh-review.json`；T-033→`attestation.json`並核對manifest/artifact hashes。

所有JSON必須分別通過固定schema：`environment.schema.json`、`migration.schema.json`、`backup-restore.schema.json`、`review-result.schema.json`、`fresh-review.schema.json`、`attestation.schema.json`（均位於`specs/subject-distillation/evidence-schemas/`，JSON Schema 2020-12）與`python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR"`。Design §22的common envelope、六份exact closed dictionaries、limits與cross-field rules是唯一normative schema source；每個object layer均`additionalProperties:false`。`reviewed_tree_sha256`由`hash_subject_review_tree.py`對task headers宣告的全部authorized source paths、五份normative files及evidence schemas建立按POSIX path byte-order排序的canonical JSON `[{"path":...,"sha256":...}]`後取SHA-256；腳本必須納入Git tracked與authorized untracked files、拒絕scope外dirty/untracked source，並排除generated evidence與private pilot資料。三份review input、aggregate與T-033重算值必須byte-equal，禁止只用commit SHA替代。四個stage TXT的首行固定為design §22.1的single-line canonical closed JSON header（同共通keys，另含`stage/requires/argv/started_at_utc/completed_at_utc/exit_code/result/stdout_size_bytes/stderr_size_bytes/stdout_sha256/stderr_sha256`），其`argv`只可byte-equal T-029相同stage固定`--`後command；其後按header byte sizes依序保留完整stdout與stderr。Raw streams先停留repo外，只有通過shared embedded-marker scanner、absolute-locator tokenization、Unicode control、current HOME與repo-root DENY後才可完整、未截斷地發布；unsafe output不得留下repo bytes。Evidence只能含public-safe／synthetic資料，不得提交private pilot內容。

Progress contract固定為JSON Schema 2020-12，所有object層級均`additionalProperties:false`。Top-level required keys為`schema_version`（固定non-Boolean JSON integer `1`）、`baseline_id`、`baseline_full_digest`、`tasks_sha256`、`updated_at_utc`、`tasks`與`events`；`baseline_id`及`baseline_full_digest`必須byte-equal於hash-verified `baseline-manifest.json.baseline_id`及`baseline-manifest.json.closure.full_digest`，`tasks_sha256`必須等於當前reviewed `tasks.md` bytes的SHA-256。`tasks`是exact key set `T-001`..`T-033`，每個value只可為`PENDING|IN_PROGRESS|BLOCKED|COMPLETED`。`events`從implicit all-`PENDING` state開始，必須nonempty；`sequence`只接受non-Boolean JSON integer且恰為`1..len(events)`，每筆required keys為`sequence/task_id/from/to/at_utc/evidence_refs/blocker`，只允許`PENDING→IN_PROGRESS|BLOCKED`、`IN_PROGRESS→BLOCKED|COMPLETED`、`BLOCKED→IN_PROGRESS`，重播後必須與`tasks`完全一致，每個中間狀態最多一個`IN_PROGRESS`，且`COMPLETED`為terminal。除T-032明確`BLOCKED`後可啟動T-033的`experimental` closure例外外，較後task不得在較前task仍為`PENDING|IN_PROGRESS|BLOCKED`時進入`IN_PROGRESS|COMPLETED`；T-033只可在T-001..T-031全為`COMPLETED`且T-032為`COMPLETED|BLOCKED`時進入`IN_PROGRESS`。`BLOCKED` event的`blocker`必須是`^[A-Z][A-Z0-9_]{0,63}$`的public-safe code，其餘event的`blocker`固定為`null`；`COMPLETED` event至少一個evidence ref。`evidence_refs`每event為`0..16`個canonical-JSON-unique discriminated objects，只允許兩形：`{"kind":"repo_file","path":<normalized POSIX repo-relative path>,"sha256":<64 lowercase hex>}`或`{"kind":"opaque","id":<1..128 chars matching ^[A-Za-z0-9][A-Za-z0-9._:-]*$>}`；repo path最多256 chars、不得為absolute、不得含empty／`.`／`..`component或backslash，且validator必須重算present repo file SHA-256；同一event不得重複ref。`opaque.id`是public-safe identifier，不是credential／secret carrier。

以下是progress與authorization共同且唯一normative public-safety JSON scanner contract；不得另加match類別或separator變體。JSON必須先由duplicate-key-rejecting parser解析，再遞迴走訪每個object key與每個string value（包含array內string）；每個object key本身以無owning key的string執行下列全部regex規則。每個string value同時帶其直接owning object key，array element則沿用該array的owning key，無owning key時不得套digest-field例外。Key normalization固定為lowercase後把每個maximal `[._-]+` run折成一個`_`。Normalized key若exact屬於`password|passwd|secret|token|api_key|access_key|private_key|client_secret|refresh_token|aws_secret_access_key|credential|capability_secret|raw|raw_evidence|content_raw|private_path|absolute_path`即DENY。

對每個string value依序執行下列Python regex規則；所示`fullmatch`／`search`語義是contract的一部分：

1. `re.search(r'(?i)(?:^|[^A-Za-z0-9])(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|sk-|sk_live_|sk_test_|rk_live_|rk_test_|pk_live_|whsec_|xoxb-|xoxp-|xoxa-|xoxr-|AKIA|ASIA|AIza|ya29\.)', value)`為DENY。
2. `re.search(r'(?i)(?:^|[^A-Za-z0-9])bearer(?:[._:-]|$)', value)`為DENY。
3. `re.search(r'(?<![A-Za-z0-9_./-])[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?![A-Za-z0-9_./-])', value)`為DENY；四段或更多dot-separated public identifier及URL/path component不得被截成JWT。
4. `re.search(r'(?i)(?:^|[^A-Za-z0-9])(?:token|secret|password|passwd|api[._-]?key|access[._-]?key|private[._-]?key|credential|client[._-]?secret|refresh[._-]?token|aws[._-]?secret[._-]?access[._-]?key)[.:=_-].+', value)`為DENY；分隔符恰為一個`.`、`:`、`=`、`_`或`-`，value至少一個character。
5. `re.search(r'(?i)-----BEGIN [A-Z0-9 ]*PRIVATE[A-Z0-9 ]*KEY-----', value)`為DENY。
6. 在generic digest rule前，只有direct owning key byte-exact為`domain_separator_utf8_hex`時，value才必須byte-exact為`7375626a6563742d64697374696c6c6174696f6e2d626173656c696e652d76310a`；exact pair成功即ALLOW該value並停止其後generic digest rule，key或value不符立即DENY。這是單一fixed manifest-domain literal exception，不使用normalized owning key，也不允許其他66位hex。Key的case、`.`、`-`、重複`_`或任何其他拼法，以及value的uppercase、prefix、suffix、length或content mutation全部DENY。
7. 若`re.fullmatch(r'private-shadow-pass:[0-9a-f]{64}', value)`成功，ALLOW該value並停止其後generic digest rule；prefix、suffix或uppercase mutation不匹配。
8. 在generic digest rule前，若normalized owning key exact屬於fixed set `artifact_sha256|authorization_id|authorization_pass_packet_sha256|authorization_schema_sha256|authorization_verifier_sha256|baseline_full_digest|delivery_diff_sha256|delivery_packet_sha256|environment_sha256|full_digest|input_hash|output_hash|private_shadow_receipt_sha256|proposal_id|receipt_sha256|reviewed_tree_sha256|scope_sha256|sha256|source_review_sha256|stderr_sha256|stdout_sha256|tasks_sha256`，則必須`re.fullmatch(r'[0-9a-f]{64}', value)`；成功即ALLOW該value並停止其後generic digest rule，失敗立即DENY。這是field/type exception而非generic string exception；uppercase、wrong length或其他malformed digest一律DENY。`null`不作string scan，只可在owning schema允許時存在。
9. `re.fullmatch(r'(?i)[0-9a-f]{32,128}', value)`為DENY。

所有不命中DENY且不需digest exception的string才ALLOW。Required legal-ALLOW fixtures必須逐一覆蓋receipt的`baseline_full_digest`、`scope_sha256`、`authorization_verifier_sha256`、`authorization_schema_sha256`、`authorization_id`，scope的`baseline_full_digest`，progress的`baseline_full_digest`、`tasks_sha256`與repo ref `sha256`，manifest的每個file `sha256`、closure `full_digest`及exact `domain_separator_utf8_hex` key/value pair，evidence/delivery的`artifact_sha256`、`authorization_pass_packet_sha256`、`delivery_diff_sha256`、`delivery_packet_sha256`、`environment_sha256`、`input_hash`、`output_hash`、`private_shadow_receipt_sha256`、`proposal_id`、`receipt_sha256`、`reviewed_tree_sha256`、`source_review_sha256`、`stderr_sha256`與`stdout_sha256`，以及exact private-shadow namespace與四段public dotted identifier。Required DENY fixtures必須證明32、64、128位bare hex置於其他key仍DENY，digest-field uppercase/wrong-length DENY，並覆蓋上述每個regex family在string起點與embedded位置、normalized forbidden-key separator variants、private-shadow namespace prefix/suffix/uppercase mutations，以及manifest-domain key的case／separator／duplicate-underscore mutations和value的uppercase／prefix／suffix／length／content mutations。通過fixed manifest-domain、private-shadow或digest-field exception的value不得再當generic bare string掃描。

`repo_file.path`在lexical normalization後、讀取／hash前，validator必須從repo root開始對每個path component執行`lstat`並拒絕任何symlink（包含symlink parent／alias），要求resolved target仍位於resolved repo root內、是regular file，且resolved target相對repo root的POSIX path byte-equal於lexically normalized repo-relative path；任何missing component、alias、escape、non-regular target或physical／lexical mismatch都fail closed，只有全部檢查成功才hash該regular file bytes。Future schema／validator必須具有上述scanner fixtures、symlink-parent／target／escape DENY，以及ordinary public-safe opaque和in-repo non-symlink regular-file legal ALLOW controls，但本docs-only amendment不建立schema、validator或tests。所有timestamp必須通過semantic calendar/clock解析的UTC RFC3339 `Z`；events的`at_utc`不得倒退，top-level `updated_at_utc`必須byte-equal末筆event `at_utc`。Validator必須用duplicate-key-rejecting JSON parser讀取manifest、schema與ledger；任何ledger write/update都必須在同一operation後執行validator並取得`PASS`，否則update不構成有效status transition。當重播結果為`T-033=COMPLETED`時，validator必須自動執行完整fixed evidence、review-tree與implementation-authorization attestation gate，不接受caller跳過；final event必須含resolved fixed `attestation.json` repo path及其當前SHA-256的exact `repo_file` ref。

`implementation-progress.json`是唯一mutable control-plane file，明確排除於T-031／T-033的`reviewed_tree_sha256`及`attestation.json.artifact_sha256`集合之外。`implementation-progress.schema.json`、`scripts/validate_subject_progress.py`、`scripts/update_subject_progress.py`與T-031先建立的`scripts/attest_subject_closure.py`則是authorized source paths，必須納入reviewed tree；其完整性由`reviewed_tree_sha256`覆蓋，不重複加入只用於固定closure evidence的`attestation.json.artifact_sha256`集合。Generated evidence及private pilot資料維持既有排除；`CHANGELOG.md`是T-030 reviewed source path，T-030完成後即freeze，T-031／T-033的status transition只能透過atomic writer進progress ledger，因此不得造成post-review source drift。

## 2. Phase A — Contract、fixtures與baseline

### B-000 — Bootstrap implementation-authorization gate

B-000 is not a T-task，never appears in `implementation-progress.json`，and cannot authorize itself。其sole purpose是建立並獨立review以下exact三個paths：

- `scripts/verify_subject_implementation_authorization.py`
- `specs/subject-distillation/evidence-schemas/implementation-authorization.schema.json`
- `tests/test_subject_authorization_bootstrap.py`

B-000只能在current five-file baseline integrity validates、repository owner透過trusted operator channel簽發包含`lane=B-000`與exact `implementation_base_commit`的instruction、`git rev-parse HEAD`等於該clean commit且其tree包含validated canonical bytes、以及clean branch/worktree preflight成立後開始。Baseline ID、full digest與exact三-path allowlist由preflight從該commit機械導出，不要求owner在chat重複。Trusted operator channel message本身是repository-owner instruction與唯一explicit human bootstrap trust root；repo無法自行cryptographically prove private conversation/channel。B-000與所有implementation agents must not self-authorize、不得從hash或review PASS推論授權，也不得create/rewrite owner instruction。

B-000 local-only且只能觸碰上述三paths；禁止product/runtime/data、production migration、deployment、release、private-live-data或destructive操作。Git commit/push/PR不由B-000本身授權，只能在owner另行授權Git delivery後執行。先在`tests/test_subject_authorization_bootstrap.py`建立genuine RED，再實作schema/verifier。Schema/verifier必須完整實現design §21的exact fields、canonical authorization ID、post-instruction receipt byte binding、duplicate-key/type/time/path/public-safety/no-echo contract與全部negative/legal-positive controls。

Schema validation不得新增dependency或修改package metadata：canonical schema只可使用design §21固定的JSON Schema 2020-12 keyword subset，verifier以Python standard library實作該exact closed subset；任何unknown keyword／remote `$ref` DENY，且schema-shape與receipt matrix證明fixed checker和canonical schema contract一致。不得silent import environment偶然存在的`jsonschema`。

Resource hostile matrix另須覆蓋每檔1,048,576-byte cap、JSON depth 32／aggregate node 32,768／single-container member 4,096 exact-boundary ALLOW與one-over DENY，且limit failure不得成為RecursionError或unbounded secondary copy。Local supported-OS run可作為開發與task completion evidence；descriptor/no-follow/race suite另須在supported Python 3.10+ Linux CI於merge前通過，return packet逐次記錄OS/Python。

Verifier deny contract固定為exit `2`、empty stdout、stderr exact `SUBJECT_IMPLEMENTATION_AUTHORIZATION_DENY\n`；unexpected internal/harness failure固定為exit `3`、empty stdout、stderr exact `SUBJECT_IMPLEMENTATION_AUTHORIZATION_ERROR\n`。Success contract固定為exit `0`、empty stderr及exact compact LF-terminated JSON object，且不得echo path、hostile key/value、token-shaped value或receipt content。

**B-000 acceptance（setup後，固定順序）：**

```bash
python -m pytest -q tests/test_subject_authorization_bootstrap.py
python -m ruff check scripts/verify_subject_implementation_authorization.py tests/test_subject_authorization_bootstrap.py
```

完成還要求parent readback、exact diff inventory及同一exact B-000 tree的一位independent security reviewer PASS。這不暗示或產生任何T-001 owner authorization；T-001仍須actual receipt verification。

### B-001 — Bootstrap identity-safe authorization runner

B-001 is a governance-only post-B-000 pre-task，not a T-task and never appears
in `implementation-progress.json`. It may create exactly:

- `scripts/run_subject_implementation_authorization.py`
- `tests/test_subject_authorization_runner.py`

B-001 starts when an owner-approved Subject/Person development mission is
active. The owner does not need to restate `lane=B-001` or an exact commit. The
Main Engineering Agent must not select an arbitrary local commit. It selects
clean HEAD that byte-equals current remote `main` or an independently reviewed
Subject protocol-amendment PR head in the approved mission chain, validates
that exact tree contains this canonical baseline, and records the provenance
proof、base commit、baseline ID/full digest、exact two-path allowlist and owner
mission/decision reference in owner-visible Issue/PR metadata or a task return
packet outside the repository tree before the first B-001 write. The preflight
record must not create or modify a third B-001 repository path. HEAD、baseline
or scope drift requires a new clean-base preflight record under the same
approved mission, not another owner prompt. That mechanical selection cannot
authorize T-001 or expand B-001 scope. Its runner implements the
two-stage proposal/confirmation protocol and invokes the unchanged B-000
verifier only after exact owner confirmation.

`propose` is stateless and read-only: it derives exact receipt/scope bytes in
memory and emits only the LF-terminated canonical public-safe proposal defined
in design §21. It creates no private file、registry、daemon、IPC endpoint、
background process or locator. `proposal_id` is the SHA-256 of canonical
proposal JSON with only `proposal_id` omitted. The proposal includes every
closed field, including task/base、baseline and scope data、timestamps、scope and
receipt digests、fixed `authorizing_principal`、derived `authorization_id` plus
canonical schema/verifier digests.

After the owner confirms that exact immediately preceding proposal and receipt
digest, one `verify-confirmed` process re-derives all fields against current
HEAD、validated baseline、fixed T-001 scope and schema/verifier bytes. It rejects
unknown、partial、noncanonical、stale、expired、future-issued、cross-task、replayed-
after-start or drifted input before private creation. Only then may it use
descriptor-relative no-follow creation、retained parent/directory/file
descriptors and exact device/inode identities；directory mode `0700`、file mode
`0600` and exact two-member set；xtrace disabled before private expansion；
byte/identity/mode recheck immediately before verifier；and one identity-safe
lifecycle for PASS、DENY、ERROR、timeout、exception、HUP、INT and TERM. Cleanup may
unlink only retained-identity owned entries and remove only the retained-
identity directory through its parent descriptor. Replacement or identity drift
must never trigger pathname deletion；return only bounded public-safe
`private_cleanup_required` and stop. An identity-safe repo-external advisory
lock is acquired nonblocking for the same repo/task/base, so exactly one of any
concurrent calls may proceed and every concurrent loser is DENY；an unexpired pre-start replay may only
reverify without an implementation side effect, and any existing T-001
`IN_PROGRESS|BLOCKED|COMPLETED` state is DENY. No proposal state persists across
processes. The runner repeats this progress check after verifier success but
before PASS；a ledger that appears、becomes invalid or changes T-001 away from
`PENDING` during verification requires cleanup and DENY. T-001 remains blocked
until verifier PASS is followed by proven cleanup and absence.

`tests/test_subject_authorization_runner.py` owns genuine RED-first coverage for
legal proposal/confirmation plus restart、unknown/stale/cross-task/partial or
noncanonical proposal、`proposal_id` mismatch、expired/future-issued input、
pre-start replay、post-start replay DENY and concurrent verification；proof that
`propose` creates no private file/registry/daemon/IPC；HEAD or baseline drift；
mid-verification progress creation/state flip followed by cleanup and DENY；
scope expansion/omission；xtrace inheritance；mode/member/digest drift；file/
directory replacement before verify and cleanup；short write；verifier PASS/
DENY/ERROR；timeout/exception/signals；cleanup failure/retry；no private marker in
stdout/stderr/repo logs；and proof that no implementation command runs before
verified cleanup. B-001 acceptance is focused pytest、Ruff、
exact two-path diff、parent readback and one independent security review with
P0=0/P1=0. Under an approved Development Mission, routine B-001 commit、push、
PR、CI repair and risk:L1 merge are autonomous engineering delivery；after
delivery B-001 stops before any T-001 proposal request or implementation.

### T-001 — Freeze implementation baseline

**Requirements:** R-SD-015–016
**Files:** no production changes；B-000 already owns the authorization schema/verifier/bootstrap test。Create `scripts/read_subject_baseline_id.py`、reuse existing `scripts/validate_subject_baseline.py`、Create `scripts/validate_subject_evidence.py`、per-artifact JSON schemas under `specs/subject-distillation/evidence-schemas/`、`tests/test_subject_baseline_control.py`、`specs/subject-distillation/implementation-progress.schema.json`、`specs/subject-distillation/implementation-progress.json`、`scripts/validate_subject_progress.py`、`scripts/update_subject_progress.py`、and existing planned `tests/test_subject_progress.py` solely for progress-ledger and stable-gate trust controls，then create `specs/subject-distillation/evidence/<baseline-id>/environment.json`。

The B-001 runner's fixed T-001 template is normative and contains exactly the
following Unicode-code-point sorted `allowed_repo_relative_paths`; `${baseline_id}`
is replaced only by the hash-verified 16-hex manifest value:

```text
scripts/read_subject_baseline_id.py
scripts/update_subject_progress.py
scripts/validate_subject_evidence.py
scripts/validate_subject_progress.py
specs/subject-distillation/.implementation-progress.pending
specs/subject-distillation/evidence-schemas/attestation.schema.json
specs/subject-distillation/evidence-schemas/backup-restore.schema.json
specs/subject-distillation/evidence-schemas/environment.schema.json
specs/subject-distillation/evidence-schemas/fresh-review.schema.json
specs/subject-distillation/evidence-schemas/migration.schema.json
specs/subject-distillation/evidence-schemas/review-result.schema.json
specs/subject-distillation/evidence/${baseline_id}/environment.json
specs/subject-distillation/implementation-progress.json
specs/subject-distillation/implementation-progress.schema.json
tests/test_subject_baseline_control.py
tests/test_subject_progress.py
```

Its exact sorted `non_goals` are `no.live.private.data`,
`no.t002.plus.artifact`, `no_product_runtime`, and `no_production_migration`.
Its exact sorted `prohibited_operations` are `deploy`, `live_private_data`,
`migration`, `non_github_remote_network`, `product_runtime`, `release`, and
`unreviewed_git_delivery`. After every acceptance command and independent
auth/security review reports P0=P1=0, the exact reviewed allowlist may use GitHub
stage/commit/push/PR/CI/merge under the approved Human-on-the-loop mission.
No other network、wildcard、directory grant or inferred path is allowed.
`scripts/validate_subject_baseline.py` and the B-000 files are read-only inputs,
not T-001 write grants.

- [ ] Record `git status --short --branch`, `git rev-parse HEAD`, Python/SQLite versions and current schema status.
- [ ] Verify every SHA-256 in `baseline-manifest.json` against bytes on disk; any mismatch blocks T-001 and requires a new fresh review, never an in-place manifest rewrite under old approval.
- [ ] Run existing pre-change migration, backup, CLI JSON and gateway tests.
- [ ] Create a temporary legacy v14 fixture through supported APIs, not by copying a private DB.
- [ ] Verify no private path/secret enters captured evidence.

Trust-artifact RED ownership is exact：`tests/test_subject_baseline_control.py` owns genuine RED-first coverage for baseline ID reader、baseline validator、evidence schemas/validator、`environment.json` controls and deterministic authorization-pass packet reconstruction/digest mismatch；`tests/test_subject_progress.py` owns only progress-ledger RED controls, including the closed source-review packet、descriptor-safe `--source-review-packet` handoff、derived `review_id` and arbitrary opaque-id rejection。For every T-001-created trust artifact, its owner test must demonstrably fail before implementation and the corresponding focused/direct command below must pass afterward。T-001不得create或rewrite B-000的schema、verifier或bootstrap test。

`tests/test_subject_progress.py` must remain byte-identical between the
IN_PROGRESS preliminary CI and COMPLETED final CI. Its repository-ledger check
accepts exactly the design §22.3 sequence-1 or sequence-2 delivery shape and
asserts the validator-reported sequence equals the validated event count；it
must not hard-code the repository ledger as permanently sequence 1. Every
seed-specific state/time mutation uses a temporary writer-created seed or an
exact one-event seed projection with the task map and `updated_at_utc`
reconstructed from event 1. Add RED controls proving both legal phases pass and
an inconsistent hybrid or third sequence DENYs；no skip、xfail or phase-selected
test file is allowed.

Progress-ledger obligations：

- Create the strict schema and duplicate-key-safe validator before seeding the ledger；the schema/validator are reviewed source, while the ledger is the excluded mutable control plane defined in §1.
- Create the design §22.3 `init`／`transition` atomic writer `scripts/update_subject_progress.py`; every T-001..T-033 status change must pass expected-current-state、sequence、dependency and evidence-ref validation in memory, create only the fixed mode-0600 pending file, write and validate exact retained bytes, `fchmod`／fsync／audit it to final mode 0644, atomically publish, then fsync the parent. Every published ledger is 0644. Before replace any fault leaves old bytes；after replace/crash only byte-identical old or fully validator-valid new is legal, and exact retry is idempotent without duplicate transition. Manual direct ledger editing is invalid execution evidence.
- Seed exactly `T-001` as`IN_PROGRESS` and `T-002`..`T-033` as`PENDING`, binding the integrity-verified manifest `baseline_id`／`closure.full_digest` and the separately reviewed `tasks.md` SHA-256；immediately run the progress validator.
- Create the exact design §22.2 public-safe `environment.implementation_authorization` only from the owner-confirmed proposal plus runner PASS；T-033 byte-equivalently revalidates/copies it into `attestation.json.implementation_authorization`. Manifest integrity、task completion or review PASS cannot populate or imply it.
- Append the `T-001: IN_PROGRESS→COMPLETED` event only after every mandatory local command exits `0`、the exact design §22.3 source/auth review packet validates with P0=P1=0、and required GitHub CI is green for the packet-bound preliminary PR head containing the IN_PROGRESS ledger；invoke `transition` with exactly one descriptor-safe `--source-review-packet` input and immediately rerun the progress validator. Any nonzero exit blocks T-001 and prevents its COMPLETED ledger event。Failure evidence is recorded public-safely，but recording is not a waiver。Only a separately owner-authorized normative amendment plus a new baseline and fresh review may change this rule。Do not mark any T-001 checkbox。
- The completion event contains design §22.3's exact 14 current `repo_file` refs plus matching `t001-authorization:<authorization_id>` and `t001-review:<review_id>` opaque refs, where `review_id` is mechanically derived from the exact source-review packet bytes rather than accepted as caller text. It excludes the mutable ledger and transient pending path；the writer must require the pending path absent after success. After completion, create the closed final delivery-readback packet, push only the ledger finalization commit, rerun required CI and merge only its exact green head. Any post-completion failure that needs a source or ledger byte correction invalidates this execution and requires a fresh repaired baseline and authorization；the terminal ledger is never reversed.

`tests/test_subject_progress.py` is the one and only `Create` owner for the progress adversarial matrix. It must cover opaque token-prefix（including `sk_test_`、`rk_test_` and `whsec_` parity with the shared scanner）、Bearer、three-segment JWT、credential assignment、PEM/private-key marker、bare-digest and recursively scanned dotted/dashed/underscored forbidden-key variants plus the expanded `client_secret|refresh_token|aws_secret_access_key|capability_secret|raw|raw_evidence|content_raw|private_path|absolute_path` DENY controls；the sole receipt exception exact `private-shadow-pass:<64 lowercase hex>` legal ALLOW；`repo_file` DENY controls for `..` components、absolute paths、symlink final targets、symlink ancestors、alias/physical-lexical mismatch、non-regular targets、and resolved targets outside the repo, plus the legal ALLOW for a regular non-symlink file whose canonical relative path remains inside the repo；以及atomic writer的stale expected state、invalid dependency、invalid temp bytes、short write、file-fsync、validator、replace、directory-fsync fault injection與crash/retry controls。Pre-publication failure必須證明old ledger byte-identical；post-publication／directory-fsync failure只允許old或完整validator-valid new，exact retry不得duplicate transition。T-029 must execute this concrete file in its unit stage, and T-031 must include its unchanged bytes together with both progress scripts in the authorized reviewed tree before hashing.

The same sole-owner progress test must RED-first prove the stable private gate,
without any real private data. Synthetic controls cover the exact canonical
private-config v1 object and 65,536-byte limit；1 and 64 sorted unique keys
ALLOW；zero/65、duplicate/unsorted/unknown key、wrong key case/length、extra
field、duplicate JSON key、trailing LF and non-canonical bytes DENY. It must prove
that the progress validator itself uses the selected 32-byte key and
`hmac.compare_digest` over the fixed domain plus canonical
receipt-without-HMAC；wrong domain、wrong MAC、MAC self-field inclusion、plain
SHA-256 fallback and child-PASS-with-invalid-MAC all DENY. The private child
channel matrix must prove exact 85-byte success and 96-byte failure boundaries,
one-byte-over denial while concurrently draining both pipes, one monotonic
300-second deadline via an injected short test clock, cross-pipe stall
resistance, process-group termination, 5-second terminate-to-kill escalation,
descendant-held pipe cleanup, no echo, and no repository side effect.

**Trusted-channel handoff（normative, before Commands）：** B-001 must be accepted
before proposal creation. The owner first asks the reviewed runner for a
candidate proposal naming `lane=T-001` and an exact clean implementation base
commit. This authorizes stateless proposal derivation only. `propose` creates no
private object and returns the complete LF-terminated canonical public-safe
proposal JSON required by design §21, including `proposal_id` and receipt
SHA-256. The owner must then separately confirm that exact immediately preceding
JSON and receipt SHA-256. Only after that confirmation may the unchanged JSON
enter one runner `verify-confirmed` process:

```bash
export SUBJECT_IMPLEMENTATION_PROPOSAL_JSON='<exact confirmed canonical public-safe proposal JSON>'
export SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256='<trusted 64-lowercase-hex receipt digest>'
export SUBJECT_IMPLEMENTATION_BASE_COMMIT='<confirmed exact clean commit>'
```

These are explanatory placeholders, never literal values. The runner owns every
private path、descriptor、mode、identity、signal and cleanup operation required
by B-001；the T-001 shell receives only public-safe confirmed values. Any
proposal/base/digest drift requires a new proposal and confirmation. Runner
absence、unaccepted B-001 bytes、private cleanup handoff or non-PASS runner result
blocks T-001 before implementation. Materialization、verification、a hash or
review PASS alone is not authority.

**Authorization preflight（clean exact base, before every T-001 write）：**

```bash
set +x
set -euo pipefail
: "${SUBJECT_IMPLEMENTATION_PROPOSAL_JSON:?confirmed canonical proposal JSON is required}"
: "${SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256:?trusted parent receipt digest is required}"
: "${SUBJECT_IMPLEMENTATION_BASE_COMMIT:?confirmed implementation base is required}"
case "$SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256" in (*[!0-9a-f]*|'') exit 2 ;; esac
[ "${#SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256}" -eq 64 ] || exit 2
case "$SUBJECT_IMPLEMENTATION_BASE_COMMIT" in (*[!0-9a-f]*|'') exit 2 ;; esac
case "${#SUBJECT_IMPLEMENTATION_BASE_COMMIT}" in 40|64) ;; *) exit 2 ;; esac
python scripts/validate_subject_baseline.py --manifest specs/subject-distillation/baseline-manifest.json --json
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_subject_authorization_bootstrap.py tests/test_subject_authorization_runner.py
.venv/bin/python scripts/run_subject_implementation_authorization.py verify-confirmed \
  --proposal-json "$SUBJECT_IMPLEMENTATION_PROPOSAL_JSON" \
  --implementation-base-commit "$SUBJECT_IMPLEMENTATION_BASE_COMMIT" \
  --expected-receipt-sha256 "$SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256" \
  --expected-task T-001 \
  --require-cleanup \
  --json
unset SUBJECT_IMPLEMENTATION_PROPOSAL_JSON SUBJECT_IMPLEMENTATION_AUTHORIZATION_SHA256 SUBJECT_IMPLEMENTATION_BASE_COMMIT
```

Runner PASS and verified cleanup start T-001. Preserve only its public-safe
output/proposal binding for design §22.2；never persist private receipt/scope.

**Post-authorization acceptance（no runner replay）：**

```bash
set -euo pipefail
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
python -m pytest -q tests/test_subject_baseline_control.py
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require environment
python -m pytest -q tests/test_subject_progress.py
python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json
python -m pytest -q tests/test_db_migrations.py tests/test_db_backup.py tests/test_cli_json_contract.py tests/test_gateway.py
python scripts/readme_command_smoke.py
python scripts/check_release_parity.py
python -m ruff check scripts/verify_subject_implementation_authorization.py scripts/validate_subject_baseline.py scripts/read_subject_baseline_id.py scripts/validate_subject_evidence.py scripts/validate_subject_progress.py scripts/update_subject_progress.py tests/test_subject_authorization_bootstrap.py tests/test_subject_baseline_control.py tests/test_subject_progress.py
git diff --check
```

**Done when:** the pre-write runner verifies the actual T-001 receipt and cleanup；all trust artifacts show genuine RED-first ownership；the post-authorization commands pass in order with exit `0`；the progress schema/validator/seed ledger pass T-001 spec and quality review；the closed source-review packet validates、its exact preliminary PR head passes required CI、the packet-consuming writer creates the completion event with design §22.3's exact environment/auth/test/legacy/review evidence set、the closed final delivery packet binds the ledger-only finalization head、required CI passes again；and final `T-001=COMPLETED` replay passes the direct validator。No future T-002+ artifact is required by T-001 validation。

### T-002 — Add public synthetic fixture taxonomy

**Requirements/SBE:** R-SD-002；E-P-001..018、E-O-001..005、E-F-001..020
**Files:**

- Create `tests/fixtures/subject_distillation/manifest.json`
- Create `tests/fixtures/subject_distillation/person/*.json`
- Create `tests/fixtures/subject_distillation/organization/authority-boundary-cases.json` as the sole Create owner of the exact `E-O-001..005` fixture and record its SHA-256 in the manifest
- Create any other required `tests/fixtures/subject_distillation/organization/*.json` without duplicating those five owners
- Create `tests/fixtures/subject_distillation/fragments/*.json`
- Create `tests/fixtures/subject_distillation/migration/*.json`
- Create `tests/test_subject_fixture_privacy.py`

- [ ] Write failing tests requiring all 43 unique SBE IDs and exactly one fixture owner per SBE.
- [ ] Add synthetic cases only; all names, IDs, paths, source locators and content are fabricated.
- [ ] Add scans for secrets, local absolute paths, known private identifiers and accidental raw evidence.
- [ ] Add primary-domain and abstention/correction/counter-evidence flags required by evaluation fixtures.
- [ ] Verify `authority-boundary-cases.json` contains exactly the five unique `E-O-001..005` IDs, is their only fixture owner, and byte-matches the manifest SHA-256.

**Verify:**

```bash
python -m pytest -q tests/test_subject_fixture_privacy.py
```

### T-003 — Add machine-readable SBE traceability contract

**Requirements:** R-SD-016、R-SD-020
**Files:**

- Read normative `specs/subject-distillation/traceability.md`
- Create the planned mapping seed `specs/subject-distillation/sbe-traceability.json`; T-029 is the sole final producer that binds collected nodes
- Create `scripts/export_subject_sbe_traceability.py`
- Create `tests/test_subject_sbe_traceability.py`

- [ ] Write red tests for 26 requirement IDs, 43 SBE IDs, no duplicates, no missing planned pytest path.
- [ ] Serialize the already approved 43-row mapping from `traceability.md`; do not invent or remap ownership during implementation.
- [ ] Map each SBE to an expected fixture and the normative planned pytest path; do not claim collected nodes before tests exist.
- [ ] Exporter must fail closed on mapping drift; T-029 later runs collect-only and atomically writes the final collected-node artifact.
- [ ] Prevent `manual`, `TBD` or private-path placeholders in final state.

**Verify:**

```bash
python -m pytest -q tests/test_subject_sbe_traceability.py
python scripts/export_subject_sbe_traceability.py --mode planned --check specs/subject-distillation/traceability.md
```

## 3. Phase B — Pure contracts與schema

### T-004 — Implement generic Subject contracts

**Requirements:** R-SD-001、003、006、007、009、010、020
**Files:**

- Create `vault/subject_contracts.py`
- Create `tests/test_subject_contracts.py`

- [ ] Red-test namespaced extensible `subject_type` and built-ins.
- [ ] Red-test UUID／UTC RFC3339／half-open effective interval validation.
- [ ] Red-test `ValueState` known/unknown/withheld/unavailable.
- [ ] Red-test the eight assertion classes, namespaces and output kinds.
- [ ] Red-test canonical JSON plus public SHA/private HMAC stability, including rejection of non-finite floats.
- [ ] Implement pure dataclasses/enums/validators without DB or network imports.

**Verify:**

```bash
python -m pytest -q tests/test_subject_contracts.py
ruff check vault/subject_contracts.py tests/test_subject_contracts.py
```

### T-005 — Implement fail-closed DB lifecycle preflight

**Requirements/SBE:** R-SD-015、025；E-F migration/status preflight cases
**Files:**

- Modify `vault/db.py` for constructor/connect/inspect/require-schema routing
- Modify `vault/db_schema.py` only for versioned manifest registration interface（不註冊v15 DDL）
- Modify `vault/db_migrations.py` only for explicit migrate orchestration that fail-closes when a target manifest/helper is absent
- Modify `vault/db_backup.py`
- Modify `vault/db_runtime.py` for shared/exclusive schema-lock lifecycle
- Modify `vault/cli_flow.py` for a non-mutating status/preflight path
- Create `tests/test_subject_migration.py`

- [ ] Red-test canonical `VaultDB.inspect(path)`的missing／empty／v14／unsupported／contradictory state matrix；它是readonly class/service path，constructor與inspect不得建立父目錄、DB、sidecar、journal mode、DDL或version stamp，且不得依賴先建立可寫instance。
- [ ] Red-test `SCHEMA_MANIFESTS`是status、migration與backup共用的唯一versioned shape authority；移除`max(...)` version reconciliation。
- [ ] Red-test a v14 DB can continue legacy memory operations while Subject calls return `schema_upgrade_required`；在T-006註冊v15 target前，canonical explicit `VaultDB.migrate(path, backup_path, target=15)`只可回`schema_contract_unavailable`且source/backup pre/post inventory與source hash相同。任何pre-existing backup target（file/symlink/directory）固定回`backup_exists`且byte/inode/inventory不變。
- [ ] Red-test every supported read-write `VaultDB` holds a shared schema lock and migration orchestration obtains an exclusive lock before backup/DDL callback/post-verify。
- [ ] Red-test同一source connection的`data_version`在backup前後、`BEGIN IMMEDIATE`後發現raw external writer race時，必須rollback、只依opened-descriptor identity刪除本attempt新建且pathname identity未變的backup，並重跑完整snapshot/preflight，最多三次attempt；第三次race固定回`migration_source_raced`、無migrator-authored DDL/version/migration-row、外部writer資料仍保留、該attempt backup absent，而不是宣稱source byte-identical、migration或無限retry。Pre-existing/replaced/identity-drifted backup target不得刪除；cleanup不能安全證明ownership時固定回`backup_cleanup_unsafe`。
- [ ] Implement lifecycle/inspection/lock scaffolding without importing or executing v15 Subject DDL；T-005完成時不會建立任何Subject table。

**Verify:**

```bash
python -m pytest -q tests/test_subject_migration.py tests/test_db_migrations.py
```

### T-006 — Add v15 Subject DDL and complete explicit migration

**Requirements/SBE:** R-SD-001、003-013、015-016、018-023、025-026；E-F migration/upgrade cases
**Depends on:** T-005 PASS；不得反向依賴。
**Files:**

- Read normative `specs/subject-distillation/schema.v15.sql`
- Create `vault/db_subject_schema.py`
- Modify `vault/db_schema.py` to register the exact v15 manifest/helper
- Modify `vault/db_migrations.py` to bind the v14→v15 callback into the T-005 orchestration
- Modify `vault/db.py` only to call the helper through the T-005 routing
- Create `tests/test_subject_db_schema.py`
- Create `tests/test_subject_migration_deferred_fk.py`
- Extend `tests/test_subject_migration.py`

- [ ] Parse `schema.v15.sql` in an empty SQLite transaction and red-test every normative column type/nullability/default/CHECK/FK action/index/trigger without inventing DDL.
- [ ] Red-test every policy kind referenced by a seal trigger is admitted by the table enum;合法`model`及`access` draft→sealed正例必須通過，direct sealed INSERT必須拒絕。
- [ ] Red-test singleton installation/version contracts, one active root, one current model, append-only histories, no-resurrection, sealed/frozen parent closure, governed purge/deletion, counterparty authority and evaluation gate closure.
- [ ] Red-test exact authority tuple (`event_kind/subject/principal/actor_role=grant_role/event-time`) for issue、approval、confirmation、termination、revocation、legal-hold與deletion；`revoked_at`不可早於effective/created time。
- [ ] Red-test every exact-authority trigger with half-open event-time grant validity: a grant revoked/expired at or before the event is denied, while an immutable event created when the grant was valid remains a legal positive after that grant is later revoked.
- [ ] Register deterministic `subject_sha256(text)` on every test/runtime read-write connection before Subject writes; verify missing UDF makes scorecard view/close fail closed and verify canonical v1 view digest stability.
- [ ] Direct-SQL red-test purge proof timestamp inversion、counterparty completion-before-request、relationship-time inversion、per-subject gate-version uniqueness及same-subject duplicate denial。
- [ ] Red-test schema target v15 and required table reporting, then enable the only v15 upgrade entry `VaultDB.migrate(path, backup_path, target=15)`；backup path不可省略、猜測或由source旁路推導。
- [ ] Red-test default `VaultDB(path)` for absent/v15/v14/pre-v14/contradictory states remains non-mutating until explicit connect/migrate.
- [ ] Red-test explicit migration holds the T-005 exclusive lock through backup, DDL, version stamp and post-verify；WAL snapshot/backup uses the shared manifest authority.
- [ ] Red-test legacy DB becomes `available_uninitialized` with zero subject rows, no legacy knowledge inference/backfill, idempotent retry and fault injection safety.
- [ ] Red-test v15 package code verifies a supported v14 rollback backup using the backup's own schema manifest.
- [ ] Add the complete composite physical-contract direct-SQL deny matrix and matching legal positives in `tests/test_subject_db_schema.py`: cross-subject auth-binding revoke; relationship/assertion termination before creation/recording; pack seal before generation or after action-rule expiry; deletion completion under active legal hold; retention before control creation; PASS without rationale; explicit confirmation without active auth binding; access issuance without same-subject sealed/effective access policy; model generation after row creation; legal-hold event outside its policy window; and evaluation freeze before gate creation. Preserve every expected-ALLOW control while fixing the deny cases.
- [ ] Add the complete lifecycle/access/relationship/evaluation invariant direct-SQL differential matrix in this sole-owner file, with one targeted DENY and one legal ALLOW control per boundary: (1) `subjects` lifecycle transitions bind same-subject exact target-state events `subject.inactivated`／`subject.revoked`／`subject.deleted`, while global `subject_principals` status transitions bind exact `principal.suspended`／`principal.revoked` events with `event.subject_id IS NULL` and `event.actor_principal_id = principal_id`; reject a wrong kind、wrong subject/global scope or other principal without letting an unrelated guard fire first；(2) an exact same-subject sealed `access` policy is effective at both issuance `occurred_at` and grant `effective_from`; reject a policy valid at only one instant；(3) relationship closure rejects any alias、`perspective` assertion、`relationship_experience` assertion or counterparty-control window that remains open past the endpoint；(4) a control already in `purge_pending` before the endpoint counts as closed for parent termination only when every store/model/export/disclosure use is denied immediately；(5) deletion request at/after the relationship endpoint is denied, while completion at/after the endpoint remains legal only for a request strictly before it and never restores use；(6) canonical evaluation one-field twins diverge for manifest SHA, every eligibility/exclusion/hard-failure/scoring-definition version and SHA, and gate `created_at`／`frozen_at`; identical twins remain stable and scorecard view/close fail closed when `subject_sha256` is absent.
- [ ] Add the event-authority/half-open endpoint direct-SQL DENY＋legal-ALLOW pairs in this same sole-owner file without creating another test owner: (1) an otherwise exact Subject lifecycle event backed only by a same-Subject `controller` grant or carrying `actor_role='controller'` is denied, while the same target-kind event carrying `actor_role='subject'` and backed by the exact same-Subject event-time-valid `subject` grant is allowed；(2) a global principal status event with `actor_role <> 'subject'` is denied, while the exact NULL-Subject、same-principal self-event with `actor_role='subject'` and an event-time-valid physical auth binding is allowed；(3) for both Subject lifecycle and principal status, `recorded_at < occurred_at` is denied and equality/later recording is allowed, while principal `updated_at` equality/regression is denied and a strictly later value equal to `occurred_at` is allowed；(4) for each relationship-bound `perspective` and `relationship_experience` assertion, `effective_until = parent effective_until` is the legal half-open boundary, while `effective_until > parent endpoint` or NULL is denied；(5) replaying one `counterparty.deletion_requested` event across two controls is denied, while two separately authorized, control-bound request events are allowed. Each pair must reach the named guard directly and preserve unrelated valid prerequisites.
- [ ] Implement transaction-compatible DDL helper and keep `db.py` a thin facade.

**Verify:**

```bash
python -m pytest -q tests/test_subject_db_schema.py tests/test_subject_migration.py tests/test_subject_migration_deferred_fk.py tests/test_db_migrations.py
```

### T-007 — Add typed Subject store

**Requirements:** R-SD-001、004、006、009、012、019、021-023
**Files:**

- Create `vault/db_subject_store.py`
- Modify `vault/db.py` with small delegating property/methods
- Create `tests/test_subject_store.py`
- Create `tests/test_subject_store_failure.py`

- [ ] Red-test transaction rollback across multi-table mutation.
- [ ] Red-test current/effective-time queries exclude superseded/revoked/tombstoned records by default.
- [ ] Red-test historical query requires explicit flag.
- [ ] Red-test methods return typed rows and never raw SQLite rowids as public IDs.
- [ ] Implement CRUD only; no policy decision inside store.
- [ ] Red-test injected store/transaction failures in `tests/test_subject_store_failure.py`; legal successful mutations remain atomic and readable through the typed store.

**Verify:**

```bash
python -m pytest -q tests/test_subject_store.py tests/test_subject_store_failure.py
```

## 4. Phase C — Authentication、roles與candidate governance

### T-008 — Implement principal authentication bindings

**Requirements:** R-SD-003、007-008、011-012、018、025
**Files:**

- Create `vault/subject_auth.py`
- Create `tests/test_subject_auth.py`

- [ ] Red-test request body `principal_id` cannot establish identity.
- [ ] Red-test valid CLI/Gateway/MCP binding resolution and ID mismatch rejection.
- [ ] Red-test local TOFU bootstrap only succeeds for interactive project owner in a completely empty `available_uninitialized` state; Gateway/MCP/non-interactive paths cannot bootstrap.
- [ ] Red-test subject/controller are separate role grants even when one human principal holds both.
- [ ] Red-test only current subject capability may add/rotate subject binding or add/revoke controller; controller/reviewer/consumer cannot mint subject authority.
- [ ] Red-test one-time offline recovery rotates the same subject binding only; lost recovery has no automatic fallback.
- [ ] Red-test credential KDF contract uses scrypt with salt/parameters, expiry and revocation; plain SHA-256 is rejected.
- [ ] Red-test existing binding can only transition `active→expired/revoked`; revoked/expired bindings cannot reactivate, change principal/adapter/verifier or be deleted.
- [ ] Red-test auth-binding revoke rejects an event whose subject scope differs from the original issuance event or whose issuer lacks exact event-time authority; the same-subject, exact-authority revoke remains the legal positive, including when an earlier immutable event is evaluated after a later grant revocation.
- [ ] Red-test global principal status transitions separately from Subject-scoped role/binding revocation: `principal.suspended` and `principal.revoked` require `event.subject_id IS NULL` and self-bind `event.actor_principal_id` to the transitioned principal; wrong kind、non-NULL Subject scope or another principal is denied, while each exact monotonic transition is a legal positive.
- [ ] Red-test the principal event-authority/time-order boundary pairs in this existing owner: `actor_role <> 'subject'` DENY versus an exact `actor_role='subject'` self-event ALLOW；`recorded_at < occurred_at` DENY versus equality/later recording ALLOW；and `NEW.updated_at <= OLD.updated_at` DENY versus a strictly later `NEW.updated_at = event.occurred_at` ALLOW. Keep NULL Subject scope、same-principal actor、exact kind and event-time-valid physical auth binding valid so each negative reaches only its intended guard.
- [ ] Red-test secrets never appear in output, exception or audit payload.
- [ ] Implement adapter interface; use stdlib/local primitives only.

**Verify:**

```bash
python -m pytest -q tests/test_subject_auth.py
```

### T-009 — Implement role、authority與assertion policy engine

**Requirements/SBE:** R-SD-003、005、007、011-013、018、023；E-P/E-O provenance and authority cases
**Files:**

- Create `vault/subject_policy.py`
- Create `tests/test_subject_policy.py`

- [ ] Red-test subject/controller/observer/consumer/authority-source role separation.
- [ ] Red-test controller or agent cannot emit `explicit` even with config override.
- [ ] Red-test explicit requires a subject confirmation event plus an active auth binding for that subject principal at confirmation time; a correctly bound principal with the exact event-time subject role remains the legal positive.
- [ ] Red-test strategic policy authority, bounded delegation and high-risk denial.
- [ ] Red-test perspective assertions never become counterparty canonical model.
- [ ] Implement pure authorization decisions with stable allow/deny codes.

**Verify:**

```bash
python -m pytest -q tests/test_subject_policy.py
```

### T-010 — Bridge existing candidate gates

**Requirements:** R-SD-003-005、017、021、026
**Files:**

- Create `vault/subject_candidates.py`
- Modify `vault/memory.py` as the current canonical generic candidate promotion dispatcher
- Create `tests/test_subject_candidates.py`

- [ ] Red-test Subject proposal creates base `memory_candidates` row plus typed sidecar atomically.
- [ ] Red-test privacy/dedupe/quality/review statuses remain base-candidate authority.
- [ ] Red-test every Subject proposal forces `review_required`; `promote_if_safe` is rejected.
- [ ] Red-test generic promotion of `subject_*` memory types fails closed with `subject_review_required`.
- [ ] Red-test typed reviewer authority and append-only review history stay consistent with base candidate state.
- [ ] Red-test agent/connector source can only propose, not write active assertion/event.
- [ ] Implement typed promotion protocol/registry boundary and keep all Subject handlers unregistered/fail-closed; no active assertion transaction exists in this task.

**Verify:**

```bash
python -m pytest -q tests/test_subject_candidates.py tests/test_memory_curator.py
```

## 5. Phase D — Evidence與assertions

### T-011 — Implement evidence metadata and retention modes

**Requirements/SBE:** R-SD-004、018、021；E-P source loss and retention cases
**Files:**

- Create `vault/subject_evidence.py`
- Create `tests/test_subject_evidence.py`

- [ ] Red-test `pointer_only`, `private_copy`, `ephemeral` behaviors.
- [ ] Red-test every accepted evidence has opaque source identity, bounded locator reference and domain-separated integrity MAC.
- [ ] Red-test ephemeral processing retains no durable raw bytes.
- [ ] Red-test source unavailable/revoked transitions and dependent lookup.
- [ ] Implement metadata service without model dependency.

**Verify:**

```bash
python -m pytest -q tests/test_subject_evidence.py
```

### T-012 — Implement operator-local private evidence lane

**Requirements:** R-SD-004、008、018、021
**Files:**

- Create `vault/subject_private_evidence.py`（固定private adapter／purge worker路徑；`vault/subject_evidence.py`只可作thin caller，不得另選module）
- Create `tests/test_subject_private_evidence.py`
- Create `tests/test_subject_purge.py`

- [ ] Red-test private-copy is explicit opt-in and default-off.
- [ ] Red-test directory `0700`, object `0600`, opaque refs, `byte_count` and HMAC verification; no DB raw/BLOB/body column exists.
- [ ] Red-test path traversal/symlink escape rejection.
- [ ] Red-test standard SQLite backup excludes private objects and restore with missing/expired ref yields `unavailable/unknown` without reconstruction.
- [ ] Red-test `active→purge_pending→purged` journal is crash-retryable, read-denied from pending, fsyncs parent, clears ref/MAC, and orphan cleanup is private-root bounded.
- [ ] Red-test purge removes raw object but leaves non-reconstructive metadata-only audit.
- [ ] Red-test audit/error output excludes bytes and absolute private path.
- [ ] Red-test assertion content/provenance UPDATE is always denied; only `active→superseded/revoked/expired/deleted` is allowed, and `superseded` requires an already-inserted successor row.
- [ ] Red-test delete request creates event+job and enters `purge_pending`; worker必須先刪除外部物件並在running job寫`object_deleted_at`，再fsync parent並寫`parent_fsynced_at`，DB才允許清除ref/MAC/byte_count；job只有看到locator已清空並寫`metadata_cleared_at`後可`succeeded`，payload在job未成功時不可`purged`，assertion最後才可`deleted`；job authority/proof/state不可重寫或刪除。
- [ ] Red-test crash/retry and proof-order failures in `tests/test_subject_purge.py`; the legal positive completes exactly once only after object deletion、parent fsync、metadata clearing and terminal assertion transition.
- [ ] Implement adapter; do not claim encryption unless a tested encrypted adapter exists.

**Verify:**

```bash
python -m pytest -q tests/test_subject_private_evidence.py tests/test_subject_purge.py
```

### T-013 — Implement immutable assertions and provenance

**Requirements/SBE:** R-SD-003-006、012、017-019、021、023；Person provenance cases
**Files:**

- Create `vault/subject_assertions.py`
- Create `vault/subject_service.py` with the minimal assertion transaction boundary used by T-013; later tasks may extend but not replace it
- Extend `vault/subject_candidates.py`
- Modify `vault/memory.py` to register the approved typed Subject assertion handler only through `SubjectDomainService`
- Create `tests/test_subject_assertions.py`
- Extend `tests/test_subject_candidates.py`

- [ ] Red-test all eight assertion classes and required actor/authority/source refs.
- [ ] Red-test support/counter evidence links.
- [ ] Red-test inference remains visible hypothesis under repetition/review.
- [ ] Red-test correction creates superseding row; revocation stops current disclosure.
- [ ] Red-test assertion/event metadata is immutable while every sensitive value lives only in a purgeable external payload object.
- [ ] Red-test governed deletion never leaves subject value in SQLite table/WAL/standard backup and retains only safe non-reconstructive audit metadata.
- [ ] Red-test assertion cannot become`deleted` until payload is`purged` by the same succeeded job and a termination event is recorded; failed/retryable jobs never yield deleted state.
- [ ] Red-test assertion termination before either its governed effective start or `recorded_at`; a termination at/after both lower bounds and within the governing relationship/authority window remains the legal positive.
- [ ] Red-test source loss recalculates availability/coverage without fabricating a source.
- [ ] Red-test approved typed promotion becomes an active assertion only inside the T-013 service transaction; unregistered/failed handlers leave base candidate and sidecar consistent and create no partial assertion/event.
- [ ] Implement lifecycle via `SubjectDomainService` transaction.

**Verify:**

```bash
python -m pytest -q tests/test_subject_assertions.py
```

## 6. Phase E — Models、grants與Context Packs

### T-014 — Implement deterministic Subject Model assembler

**Requirements/SBE:** R-SD-005-006、010、012-014、019-021；E-P five-output and temporal cases
**Files:**

- Create `vault/subject_models.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_models.py`

- [ ] Red-test active/effective assertions only and explicit historical opt-in.
- [ ] Red-test four stored output kinds plus fifth Context Pack capability declaration.
- [ ] Red-test unknown and inferred hypothesis labels.
- [ ] Red-test deterministic output/integrity MAC for same inputs and domain separation across artifact kinds.
- [ ] Red-test source loss/correction creates next version rather than mutating sealed model.
- [ ] Red-test assertion/policy source intersects the model data window and exists by generated_at；entry-valid→source-revoked→model-seal must fail.
- [ ] Red-test `generated_at > created_at` and a governing model policy not yet effective at `generated_at`; equality/earlier generation with the exact same-subject sealed policy already effective at generation remains the legal positive, including a zero-entry model where allowed.
- [ ] Implement local deterministic assembly; model-generated text may only enter candidate path.

**Verify:**

```bash
python -m pytest -q tests/test_subject_models.py
```

### T-015 — Implement access grants and revocation

**Requirements:** R-SD-007-008、011-012、018-019
**Files:**

- Extend `vault/subject_policy.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_grants.py`

- [ ] Red-test same agent in same Vault has no implicit Subject grant.
- [ ] Red-test purpose, task scope, domain, output kind, sensitivity ceiling and expiry.
- [ ] Red-test grant revocation blocks future packs immediately.
- [ ] Red-test access-grant issuance rejects a missing、cross-subject、draft or wrong-kind access policy, plus each one-sided window twin where the exact sealed policy is valid at issuance `occurred_at` but not grant `effective_from`, or at grant start but not issuance; a same-subject sealed `access` policy effective at both instants remains the legal positive.
- [ ] Red-test role/access grants cannot rewrite role/scope/issuer/authority event or reactivate after revocation; replacement requires a new row.
- [ ] Red-test binding、role/access grant及sealed delegation rule revocation all require an append-only revocation event bound to the correct subject/authority scope; a sealed delegation rule remains revocable but otherwise immutable.
- [ ] Red-test grant cannot confer subject role or high-risk action authority.
- [ ] Red-test delegation rule requires explicit domain, stakes, reversibility, cost ceiling, approval mode, expiry and revocation state.
- [ ] Red-test recommendation or Context Pack content cannot synthesize a delegation rule.
- [ ] Red-test delegation/model child rows can be inserted only while their parent is draft and cannot be inserted/updated/deleted after parent sealing.
- [ ] Implement versioned grant decisions and stable denial reasons.

**Verify:**

```bash
python -m pytest -q tests/test_subject_grants.py
```

### T-016 — Implement Context Pack generator

**Requirements/SBE:** R-SD-008、010-012、018-019、023；E-P/E-O role-scoped pack cases
**Files:**

- Create `vault/subject_context.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_context.py`

- [ ] Red-test auth→grant→purpose→domain→sensitivity→minimization order.
- [ ] Red-test raw evidence/private object refs never leave the pack.
- [ ] Red-test third-party and perspective filtering.
- [ ] Red-test current-only default and historical explicit grant.
- [ ] Red-test model/policy/producer version, coverage, class, namespace and ValueState metadata.
- [ ] Red-test pack run stores only refs/domain-separated integrity MACs/exclusion counts.
- [ ] Red-test pack entries insert only under draft run; sealing verifies actual entry count and freezes all entries/counts/MAC, with no post-seal INSERT.
- [ ] Red-test sealing rejects cross-subject model/policy/grant, wrong consumer/purpose/task, inactive generated-time grant and policy/model mismatch.
- [ ] Red-test pack generated_at cannot precede model generated_at, `sealed_at` cannot precede `generated_at`, and seal revalidates the top-level exact subject/model/access-policy/model-policy/grant chain at both generated and sealed time independently of entry count；entry-valid→source-revoked→seal and grant/policy/action-rule expiry before seal must fail.
- [ ] Add zero-entry legal positives for a monotonic generated→sealed pack whose exact grant、access/model policies and action rule remain effective at both times; pair each top-level negative with a non-empty legal positive and preserve per-entry revalidation.
- [ ] Red-test `action_authority:false` unless independent delegation policy allows it; true requires pack action domain/stakes/reversibility/cost/currency to match grant and sealed rule exactly/within ceiling.
- [ ] Implement deterministic budget truncation without sensitivity escalation.

**Verify:**

```bash
python -m pytest -q tests/test_subject_context.py
```

## 7. Phase F — Decisions、relationships與fragments

### T-017 — Implement append-only decision event validation

**Requirements/SBE:** R-SD-006、009、012、017、026；E-P decision cases
**Files:**

- Create `vault/subject_decisions.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_decisions.py`

- [ ] Red-test event vocabulary and monotonic sequence.
- [ ] Red-test DB rejects UPDATE/DELETE.
- [ ] Red-test parent projection advances exactly one sequence, consumes each semantic delta, and a new child cannot append until the prior child—including terminal event—is projected.
- [ ] Red-test recommendation, predicted choice, actual choice, subject reason, outcome and feedback are distinct.
- [ ] Red-test confidence belongs only to predicted choice.
- [ ] Red-test unsourced actual choice/outcome hard-fails.
- [ ] Red-test agent inference remains candidate.
- [ ] Implement append service and deterministic projector.

**Verify:**

```bash
python -m pytest -q tests/test_subject_decisions.py
```

### T-018 — Implement directional and temporal relationships

**Requirements/SBE:** R-SD-006、018、022-023；relationship Person cases
**Files:**

- Create `vault/subject_relationships.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_relationships.py`
- Create `tests/test_subject_counterparty.py`
- Create `tests/test_subject_relationship_expiry.py`

- [ ] Red-test separate spouse/co-parent/manager edges and independent effective windows.
- [ ] Red-test stable opaque counterparty ID across aliases.
- [ ] Red-test alias revocation does not change subject reference.
- [ ] Red-test primary subject consent only governs own experience.
- [ ] Red-test perspective assertion keeps model owner/about subject/relationship/provenance.
- [ ] Red-test relationship provenance event belongs to one endpoint; `perspective` connects owner→about, `relationship_experience` keeps owner=about, and counterparty control connects primary→counterparty.
- [ ] Red-test alias/perspective/counterparty authority、effective與created time all lie in the exact relationship interval; future/ended relationship must deny.
- [ ] Red-test relationship termination before either its effective start or `created_at`, and reject termination while alias、`perspective` assertion、`relationship_experience` assertion or counterparty-control windows extend past the proposed half-open endpoint; legal positives cover no-dependent termination and every dependent closed atomically by the endpoint.
- [ ] Red-test the relationship assertion half-open endpoint twins in this existing owner for both relationship-bound namespaces: `effective_until = relationship.effective_until` is a legal half-open close, while `effective_until > relationship.effective_until` and NULL each deny parent termination for both `perspective` and `relationship_experience`.
- [ ] Red-test a counterparty control entering `purge_pending` strictly before the proposed endpoint is accepted as relationship-closure-safe only after store/model/export/disclosure authorization all fail closed; an active or still-usable control remains a DENY, and the legal positive does not require post-endpoint purge completion.
- [ ] Red-test alias／`perspective`／`relationship_experience` termination or revoke events at/after the relationship endpoint and late generic lifecycle events after termination; legal positives occur strictly inside the relationship interval. Keep only the separately proven post-relationship deletion-completion exception.
- [ ] Red-test no counterparty control permits only deidentified first-person perspective and denies raw quote/contact/self-model/export.
- [ ] Red-test `counterparty_consent`/`legal_obligation` require independent authority, purpose, operations, retention and sealed same-primary legal-policy id/version; consent actor must hold counterparty subject role at event time.
- [ ] Red-test every counterparty control has authority event; primary-only basis cannot export counterparty/bilateral data; legal hold requires its own authority event and policy version.
- [ ] Red-test `retention_until < control.created_at` and legal-hold authority events outside the sealed policy effective window; equality/greater retention and an event inside the exact policy window remain legal positives.
- [ ] Red-test primary-subject export, authenticated counterparty export, independent purge/deidentification and expiring legal hold boundaries.
- [ ] Red-test counterparty deletion request must occur strictly before the relationship endpoint; a request at equality or later is denied. Completion must be strictly after that request, may occur at/after the endpoint only for the pre-endpoint request, and is denied by an active legal hold; after hold expiry/revocation the legal completion only finishes purge/deidentification bookkeeping and never restores store/model/export/disclosure authority.
- [ ] Red-test deletion-request event single use: binding the same `counterparty.deletion_requested` event to a second counterparty control is denied even when both controls share otherwise valid scope and authority; two distinct, separately authorized events each bound to its own control are the legal positive.
- [ ] Implement relationship and alias lifecycle.

**Verify:**

```bash
python -m pytest -q tests/test_subject_relationships.py tests/test_subject_counterparty.py tests/test_subject_relationship_expiry.py
```

### T-019 — Implement pure Subject Fragment validator

**Requirements/SBE:** R-SD-014、018、023-024；E-F-007、E-F-010..012
**Files:**

- Create `vault/subject_fragments.py`
- Create `tests/test_subject_fragments.py`

- [ ] Red-test required issuer/authority/origin/binding/version/fingerprint/audience/purpose/sensitivity/effective/expiry/sharing/revocation/coverage fields.
- [ ] Red-test unauthorized issuer, binding mismatch, unverifiable revocation and raw evidence denial.
- [ ] Red-test lifecycle `valid/superseded/revoked/expired/conflicted`.
- [ ] Red-test remote, local perspective and bilateral artifacts remain visible and unmerged.
- [ ] Red-test function performs no DB/file/network I/O.
- [ ] Implement pure validator only; no transport/import/persistence.

**Verify:**

```bash
python -m pytest -q tests/test_subject_fragments.py
```

### T-020 — Verify Organization contract compatibility

**Requirements/SBE:** R-SD-001、003、006-008、010、012-014、019-020；E-O-001..005
**Files:**

- Create `tests/test_subject_organization_contract.py`
- Read/reuse the T-002-owned `tests/fixtures/subject_distillation/organization/authority-boundary-cases.json`; do not create, rewrite or rename it
- Read/reuse the T-002-owned `tests/fixtures/subject_distillation/manifest.json`; do not rewrite its five owners or fixture SHA-256
- Read no other organization fixtures unless needed to prove they do not duplicate the exact five owners

- [ ] Red-test official strategy authority vs team habit vs employee preference.
- [ ] Red-test strategy v2 supersedes v1 while history remains.
- [ ] Red-test role-scoped Context Pack.
- [ ] Red-test the test loads exactly `authority-boundary-cases.json`, resolves exactly five unique `E-O-*` IDs, and verifies its manifest SHA-256; a missing/renamed/unreferenced fixture fails.
- [ ] Verify the reused fixture IDs are exactly `E-O-001..005`, the manifest hash matches its bytes, and T-002 remains the sole Create owner.
- [ ] Red-test no core table has person-only required columns.
- [ ] Satisfy tests with generic core; do not add Organization runtime surface.

**Verify:**

```bash
python -m pytest -q tests/test_subject_organization_contract.py
```

## 8. Phase G — Product journey與public surfaces

### T-021 — Implement default-on Subject capability state

**Requirements/SBE:** R-SD-007、014、025；new-install/upgrade cases
**Files:**

- Modify `vault/subject_service.py`
- Modify `vault/cli_quickstart.py`
- Modify `vault/agent_setup.py` at the existing canonical interactive setup extension point
- Create `tests/test_subject_setup.py`

- [ ] Red-test new interactive quickstart cannot silently skip root Subject setup.
- [ ] Red-test setup creates root subject, principals/bindings, role grants, exact same-subject sealed `privacy` default-private policy、exact sealed `model` policy及empty sealed model only；成功transaction經`initialized_empty`後終止於`active`，任何中途fault整體rollback且不得留下可觀察partial state。
- [ ] Red-test no personality inference or source scan occurs.
- [ ] Red-test legacy/direct init/non-interactive without explicit args returns `available_uninitialized` plus next action.
- [ ] Red-test repeated setup does not create second active root.
- [ ] Red-test Subject-row lifecycle event binding with exact target-state kinds: wrong-kind／cross-subject events cannot drive `active→inactive/revoked/deleted` or `inactive→revoked/deleted`, while the same-subject `subject.inactivated`、`subject.revoked` and `subject.deleted` event controls drive only their matching monotonic transitions.
- [ ] Red-test the Subject lifecycle event-authority/time-order pairs in this existing owner: an otherwise exact event backed only by a same-Subject controller grant or carrying `actor_role='controller'` is denied versus an exact event-time-valid same-Subject `subject` role event allowed；`recorded_at < occurred_at` is denied versus equality/later recording allowed. Keep target kind、Subject、source state、single-use event and `occurred_at = effective_until` valid so each negative reaches its intended authority or chronology guard.
- [ ] Implement lifecycle states and setup transaction.

**Verify:**

```bash
python -m pytest -q tests/test_subject_setup.py tests/test_agent_setup.py
```

### T-022 — Add CLI Subject command tree

**Requirements:** R-SD-003、007-012、014、017、019、022、024-026
**Files:**

- Create `vault/cli_subject.py`
- Modify `vault/cli.py` parser/dispatch only
- Create `tests/test_subject_cli.py`
- Extend `tests/test_cli_json_contract.py`

- [ ] Red-test command names, required auth, JSON/pretty schema and stable error codes.
- [ ] Red-test secret accepted only through safe input path and never echoed.
- [ ] Red-test exact design §10.1 command vocabulary：`status`、`setup-root`、`principal bind|revoke`、`propose`、`review`、`confirm|correct|revoke|delete-request`、`model build|show`、`context-pack`、`decision create|append|show`、`relationship add|end|alias`、`grant create|revoke`、`fragment validate`；evaluation group由T-025/T-026在各自domain unit/fixture PASS後依同一canonical vocabulary加入，不得使用別名替代canonical command。
- [ ] Red-test `vault subject status` uses only canonical `VaultDB.inspect(path)` and missing/empty/legacy/current/unsupported/contradictory inputs create no DB or sidecar and preserve source bytes/hash.
- [ ] Red-test generic promotion rejects Subject candidate.
- [ ] Implement thin handlers calling `SubjectDomainService`.

**Verify:**

```bash
python -m pytest -q tests/test_subject_cli.py tests/test_cli_json_contract.py
```

### T-023 — Add minimal MCP Subject tools

**Requirements:** R-SD-007-008、011、014、017、019、024-025
**Files:**

- Create `vault/mcp_subject.py`
- Modify `vault/mcp_tools.py` registration/profile lists only
- Create `tests/test_subject_mcp.py`

- [ ] Red-test core profile includes status/propose/context-pack/fragment-validate only.
- [ ] Red-test `vault_subject_status` uses only canonical `VaultDB.inspect(path)` and is byte/sidecar/no-create identical to CLI status across the full inspect state matrix.
- [ ] Red-test review/maintenance tools require process principal binding.
- [ ] Red-test caller-supplied principal cannot elevate.
- [ ] Red-test tool profile is disclosed as surface control, not authorization.
- [ ] Implement schemas/handlers and preserve existing tool profiles.

**Verify:**

```bash
python -m pytest -q tests/test_subject_mcp.py tests/test_mcp_memory.py
```

### T-024 — Add Gateway Subject adapters

**Requirements:** R-SD-003、007-008、011、014、017-019、024-025
**Files:**

- Create `vault/gateway_subject.py`
- Modify `vault/gateway.py`
- Modify `vault/gateway_openapi.py`
- Extend `tests/test_gateway.py`

- [ ] Red-test five approved endpoints and auth/rate/body-size/error contracts.
- [ ] Red-test `GET /subject/status` uses only canonical `VaultDB.inspect(path)` and is byte/sidecar/no-create identical to CLI/MCP status across the full inspect state matrix.
- [ ] Red-test token→principal binding wins over body identity.
- [ ] Red-test remote proposals are candidate-first.
- [ ] Red-test Context Pack excludes raw evidence and ungranted third-party data.
- [ ] Red-test fragment endpoint validates only and has no persistence side effect.
- [ ] Red-test no full-model/raw-evidence download endpoint is introduced.
- [ ] Add `x-vault-subject-safety` and endpoint contract.

**Verify:**

```bash
python -m pytest -q tests/test_gateway.py -k subject
python -m pytest -q tests/test_gateway.py
```

## 9. Phase H — Evaluation loop

### T-025 — Implement frozen evaluation gate

**Requirements/SBE:** R-SD-016、026；E-P-017、E-P-018、E-F-017..020
**Files:**

- Create `vault/subject_evaluation.py`
- Extend `vault/subject_service.py`
- Create `tests/test_subject_evaluation.py`
- Modify `vault/cli_subject.py` to add only the evaluation subgroup after domain tests pass
- Modify `vault/cli.py` parser/dispatch registration only
- Extend `tests/test_subject_cli.py` with evaluation surface cases

- [ ] Red-test preregistered eligibility/exclusion, one primary domain and no outcome-based subset.
- [ ] Red-test v1 abstention minimum is exactly`0.80`; cases separately represent subject correction, counter-evidence and contextual constraint, and at least three qualify by their union.
- [ ] Red-test case INSERT is draft-only, event/signoff INSERT is frozen-only, and closed PASS cannot accept new case/event/signoff.
- [ ] Red-test case disposition/event/signoff timestamps are not before frozen_at and not after closed_at; caller future timestamps cannot escape the close window.
- [ ] Red-test `N` is all completed eligible preregistered cases and `N>=20`.
- [ ] Red-test `ceil(0.80*N)` utility and independent reason denominator; 25→20.
- [ ] Red-test missing/non-reviewable rationale is unaligned and can never produce DB `PASS`; a completed eligible case with a policy-safe reviewable rationale remains the legal positive and participates in the canonical denominator.
- [ ] Red-test abstention denominator and per-domain denominator.
- [ ] Red-test DB PASS close itself rejects one-domain/all-failed/NULL-metric/invalid-scorecard/same-principal-double-signoff and signers without current same-subject role grants.
- [ ] Red-test gate version is unique per Subject (two Subjects may each own v1); close recomputes `subject_evaluation_scorecard_v1` and rejects arbitrary 64-hex even when both signoffs repeat it.
- [ ] Red-test `frozen_at < gate.created_at`; equality/later freeze with all preregistered rows valid remains the legal positive, and otherwise-identical one-field `created_at` and `frozen_at` twins each produce distinct canonical digests.
- [ ] Red-test canonical scorecard bytes bind, in fixed order/type, manifest SHA、denominator、minimum N、rounding、every overall/domain/abstention/reason/high-confidence threshold、reviewer authority and each preregistered eligibility/exclusion/hard-failure/scoring-definition version and SHA. Build explicit one-field differential twins for every listed version/hash (not one representative pair) and every threshold; each pair must diverge, while byte-identical frozen inputs remain stable. Without deterministic `subject_sha256`, both scorecard-view read and close fail closed before accepting or comparing any caller digest; registering it restores the legal stable/differential controls.
- [ ] Red-test high-confidence hard rule uses incorrect predicted choice only.
- [ ] Red-test correct choice/rejected reason separation and independent material-misrepresentation hard fail.
- [ ] Red-test all deterministic safety invariants are hard, non-adjustable failures.
- [ ] Implement draft→frozen→closed and scorecard fingerprint.
- [ ] 依固定順序執行本task：evaluation pure/domain unit → synthetic fixture/DB contract → CLI surface；surface handler只能呼叫`SubjectDomainService`。
- [ ] Red-test canonical CLI evaluation `init|freeze|record|close` commands及read-only evaluation status view，stable JSON/error schema and authorization；不得使用`create`替代`init`，不得在unit/fixture尚紅時先提交surface。

Evaluation-event shape is fixed to the existing physical contract and must be asserted in `tests/test_subject_evaluation.py`: only `utility|reason_alignment|abstention|domain_score` carry non-null binary `metric_value` with `passed=CAST(metric_value)`; `hard_failure` is non-metric with `metric_value=NULL`, `passed IN (0,1)`, and non-null bounded `reason_code`. NULL rejection for `metric_value` applies to the four metric-bearing types, not to `hard_failure`.

**Verify:**

```bash
python -m pytest -q tests/test_subject_evaluation.py
python -m pytest -q tests/test_subject_cli.py -k evaluation
```

### T-026 — Implement sign-off and prospective adjustment

**Requirements:** R-SD-016、026
**Files:**

- Extend `vault/subject_evaluation.py`
- Modify `vault/subject_service.py` only for the typed sign-off/next-version candidate orchestration methods defined here; no unrelated service refactor
- Modify `vault/cli_subject.py` only to add canonical evaluation `signoff|propose-next` handlers after domain tests pass
- Modify `vault/cli.py` parser/dispatch registration only
- Extend `tests/test_subject_evaluation.py`
- Extend `tests/test_subject_cli.py` with signoff/propose-next surface cases

- [ ] Red-test subject/controller and fresh reviewer sign the same closed scorecard fingerprint.
- [ ] Red-test both signoffs use the canonical view digest and signed_at lies inside the frozen-to-close interval.
- [ ] Red-test missing or mismatched signoff blocks formal release.
- [ ] Red-test closed gate cannot change verdict/threshold/denominator/case result.
- [ ] Red-test analysis creates a candidate for next gate/model/policy version only.
- [ ] Red-test candidate cannot weaken deterministic privacy/authority/provenance/temporal invariants.
- [ ] Red-test canonical CLI evaluation `signoff|propose-next` commands, stable JSON/error schema and exact server-side principal authority；surface handler只呼叫typed service method，caller-supplied principal不得elevate。
- [ ] Implement report-only next-version proposal path through existing candidate gates.

**Verify:**

```bash
python -m pytest -q tests/test_subject_evaluation.py -k 'signoff or prospective or closed'
python -m pytest -q tests/test_subject_cli.py -k 'evaluation and (signoff or propose_next)'
```

## 10. Phase I — Migration recovery、privacy與regression

### T-027 — Prove backup and rollback recovery

**Requirements/SBE:** R-SD-015；migration failure/rollback cases
**Files:**

- Extend `tests/test_subject_migration.py`
- Extend `tests/test_db_backup.py`
- Create `scripts/capture_subject_recovery_evidence.py`
- Update operational docs in T-030, not before behavior passes

- [ ] Create v14 DB through supported legacy API and backup it.
- [ ] Migrate to v15, add synthetic Subject-only data, then restore backup to a different path.
- [ ] Verify old runtime-compatible compile/search/read/propose/promote smoke against restored DB.
- [ ] Verify knowledge/governance metadata parity.
- [ ] Verify rollback does not silently copy Subject-only data into legacy DB.
- [ ] Verify interrupted migration can retry.
- [ ] Verify package target v15 does not reject a structurally valid v14 backup solely because versions differ.
- [ ] Verify standard DB rollback makes private refs unavailable rather than claiming raw private-lane recovery; separately test explicit private backup adapter only if one is implemented.

**Verify:**

```bash
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
python -m pytest -q tests/test_subject_migration.py tests/test_db_backup.py
python scripts/capture_subject_recovery_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --migration-out "$EVIDENCE_DIR/migration.json" --backup-out "$EVIDENCE_DIR/backup-restore.json" -- python -m pytest -q tests/test_subject_migration.py tests/test_db_backup.py
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require migration,backup-restore
```

### T-028 — Run privacy and log-redaction gate

**Requirements:** R-SD-002、004、008、014、018、021、024
**Files:**

- Create `tests/test_subject_privacy_gate.py`
- Create `vault/subject_privacy.py` as the only Subject redaction/inline validator helper；若測試證明無production helper必要，仍保留此檔為明確no-op/typed facade，不得改未列名module
- Modify `vault/subject_service.py` only to invoke that typed privacy facade at the existing Subject writer/pack boundaries；不得新增第二套redaction policy或改其他runtime module

- [ ] Scan fixtures, exceptions, audit payloads, CLI/MCP/Gateway responses and pack runs.
- [ ] Assert no secret, capability, raw private evidence, absolute operator path or ungranted counterparty detail.
- [ ] Assert audit preserves actor/action/decision/reason code/opaque ID needed for accountability without plain low-entropy fingerprints.
- [ ] Assert public artifacts use SHA-256 while private values use domain-separated HMAC or opaque IDs; missing audit key yields `unverifiable`, never plain-hash fallback.
- [ ] Fuzz every inline TEXT field through the supported `SubjectDomainService`/CLI/MCP/Gateway writer boundaries to reject free text, names, contact data, raw quotes and paths outside its ID/enum/time/code/aggregate schema；另以direct-SQL negative fixtures驗證DDL列出的authority、lifecycle、FK與高風險opaque-code CHECK。敏感text只能進external payload objects；不得把未支援的raw SQLite writer宣稱為產品surface。

**Verify:**

```bash
python -m pytest -q tests/test_subject_fixture_privacy.py tests/test_subject_privacy_gate.py
```

### T-029 — Full synthetic and legacy regression gate

**Requirements:** all
**Files:** create `scripts/capture_subject_closure.py`、`scripts/run_subject_sbe_fixture_gate.py`、`scripts/run_subject_legacy_gate.py`; reuse the exporter created by T-003 without overwriting it; finalize `specs/subject-distillation/sbe-traceability.json`; write only the five declared evidence artifacts under the resolved `EVIDENCE_DIR`; no product behavior changes

- [ ] Unit stage executes every behavior-bearing non-surface Subject file from T-004..T-028, including `test_subject_assertions/auth/candidates/context/contracts/counterparty/db_schema/decisions/evaluation/evidence/fragments/grants/migration_deferred_fk/models/policy/privacy_gate/private_evidence/purge/relationship_expiry/relationships/setup/store/store_failure.py` plus existing integration owners `test_memory_curator.py` and `test_agent_setup.py`.
- [ ] Export exactly 43 unique SBE IDs to collected pytest node IDs; fail on missing/duplicate/uncollected node.
- [ ] Fixture stage executes those 43 collected nodes plus fixture privacy, SBE mapping, exact Organization fixture, and migration behavior; mapping validation without node execution is a failure.
- [ ] Surface stage runs CLI/MCP/Gateway/JSON contracts only after fixture PASS.
- [ ] Legacy runner executes full existing suite, Ruff, README smoke, release parity, and `git diff --check`; any subcommand failure returns nonzero and is preserved in `legacy.txt`.

T-029's concrete unit inventory additionally includes the T-001-owned `tests/test_subject_progress.py`; T-029 only executes/reuses that file and never becomes a second `Create` owner.

T-029 release-parity classification is exact and typed. `scripts/run_subject_legacy_gate.py` may convert the release-only checker's observed exit `1` to the single non-PASS disposition `{"status":"NOT_APPLICABLE_UNRELEASED","reason":"TOP_CHANGELOG_HEADING_IS_UNRELEASED","observed_exit":1}` only when all of these are mechanically true in the same run: (1) the first level-2 CHANGELOG heading is byte-exact `## [Unreleased]`; (2) `python scripts/check_release_parity.py` actually exited exactly `1` and its sole reported cause is that exact top heading, with no additional parse/version/tag/I/O error；and (3) local version hygiene still holds—`pyproject.toml [project].version` and literal `vault.__version__` are byte-equal, each matches the checker's `PEP440_RELEASE_RE`, and any `a|b|rc` prerelease suffix is identical. For the immutable checkbox above, only this exact successful classification is non-applicable rather than a subcommand failure；the raw checker exit remains recorded. The runner must emit and capture the exact public-safe marker `release-parity:NOT_APPLICABLE_UNRELEASED:TOP_CHANGELOG_HEADING_IS_UNRELEASED:exit=1` in `legacy.txt`; it must never rename this disposition `PASS`. Any other exit `1`, multiple/unknown reason, heading variation, version drift, malformed output, signal, or execution error is `DENY`, makes the legacy stage nonzero, and remains preserved verbatim as bounded public-safe evidence.

**Commands（must run in this exact order; capture script records canonical header、full command、UTC、exit code、stdout/stderr）：**

```bash
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
python scripts/capture_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --stage unit --output "$EVIDENCE_DIR/unit.txt" -- python -m pytest -q tests/test_subject_assertions.py tests/test_subject_auth.py tests/test_subject_candidates.py tests/test_subject_context.py tests/test_subject_contracts.py tests/test_subject_counterparty.py tests/test_subject_db_schema.py tests/test_subject_decisions.py tests/test_subject_evaluation.py tests/test_subject_evidence.py tests/test_subject_fragments.py tests/test_subject_grants.py tests/test_subject_migration_deferred_fk.py tests/test_subject_models.py tests/test_subject_policy.py tests/test_subject_privacy_gate.py tests/test_subject_private_evidence.py tests/test_subject_progress.py tests/test_subject_purge.py tests/test_subject_relationship_expiry.py tests/test_subject_relationships.py tests/test_subject_setup.py tests/test_subject_store.py tests/test_subject_store_failure.py tests/test_memory_curator.py tests/test_agent_setup.py
python scripts/export_subject_sbe_traceability.py --mode collected --requirements specs/subject-distillation/requirements.md --traceability specs/subject-distillation/traceability.md --collect-command "python -m pytest --collect-only -q tests/test_subject_*.py" --require-count 43 --output specs/subject-distillation/sbe-traceability.json
python scripts/capture_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --stage fixture --requires unit --output "$EVIDENCE_DIR/fixture.txt" -- python scripts/run_subject_sbe_fixture_gate.py --mapping specs/subject-distillation/sbe-traceability.json --require-count 43 --extra tests/test_subject_fixture_privacy.py tests/test_subject_sbe_traceability.py tests/test_subject_organization_contract.py tests/test_subject_migration.py tests/test_db_migrations.py tests/test_db_backup.py
python scripts/capture_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --stage surface --requires fixture --output "$EVIDENCE_DIR/surface.txt" -- python -m pytest -q tests/test_subject_cli.py tests/test_subject_mcp.py tests/test_gateway.py tests/test_cli_json_contract.py tests/test_mcp_memory.py
python scripts/capture_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --stage legacy --requires surface --output "$EVIDENCE_DIR/legacy.txt" -- python scripts/run_subject_legacy_gate.py --pytest "python -m pytest -q" --ruff "ruff check vault tests scripts" --readme-smoke "python scripts/readme_command_smoke.py" --release-parity "python scripts/check_release_parity.py" --diff-check "git diff --check"
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require unit,fixture,surface,legacy
```

**Done when:** unit、fixture、surface and every non-release-only legacy subcommand have real PASS output；release parity has either a real exit-0 PASS or the exact typed `NOT_APPLICABLE_UNRELEASED` record and marker above. The typed disposition is evidence of non-applicability, never PASS；no critical invariant is skipped, and every DENY is repaired and rerun rather than summarized away. A real release gate remains a separate post-T-030 obligation.

## 11. Phase J — Documentation、release label與fresh closure

### T-030 — Update canonical docs and changelog

**Requirements:** R-SD-014-016、019-020、024-026
**Files:**

- Modify `README.md`
- Modify `README.zh-Hant.md`
- Modify `README.zh-CN.md`
- Modify `docs/memory_governance.md`
- Modify `SCHEMA.md`
- Modify `CHANGELOG.md`
- Create `docs/subject_operations.md` as the single focused operations doc

- [ ] Document setup state, privacy default, evidence modes, roles, Context Pack, fragment limitation, migration/rollback and evaluation label.
- [ ] Clearly state Organization runtime and remote fragment sync are deferred.
- [ ] Clearly state model/pack never grants high-risk action by itself.
- [ ] Document private shadow handling without exposing private evidence.
- [ ] Run docs command smoke and link/path checks available in repo.

**Freeze rule:** finalize `CHANGELOG.md` for all coherent implementation／security／docs units before T-031, then freeze it with every other authorized source path；T-031 and T-033 task-status changes go only to `implementation-progress.json`.

**Verify:**

```bash
python scripts/readme_command_smoke.py
```

T-029's `NOT_APPLICABLE_UNRELEASED` never satisfies release readiness. After T-030, and only once the operator finalizes an actual top release heading, execute the release-only gate separately immediately before the real release/tag and require exit 0；an `[Unreleased]` heading, typed N/A, missing tag, or any mismatch is not releasable:

```bash
RELEASE_VERSION="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
python scripts/check_release_parity.py --tag "v${RELEASE_VERSION}"
```

### T-031 — Fresh code/security/migration review

**Requirements:** all
**Files:** reviewers do not edit reviewed artifacts; create `scripts/hash_subject_review_tree.py`、`scripts/record_subject_fresh_review.py`、`scripts/attest_subject_closure.py` and `tests/test_subject_attestation.py` before computing the review tree；T-031 is the sole `Create` owner of `tests/test_subject_attestation.py`；record the three fixed reviewer result files at `$EVIDENCE_DIR/reviews/requirements-architecture.json`、`security-privacy.json`、`execution-traceability.json`; write aggregate `$EVIDENCE_DIR/fresh-review.json`

- [ ] Fresh reviewer A: provenance/auth/policy/third-party/privacy.
- [ ] Fresh reviewer B: schema/migration/rollback/legacy compatibility.
- [ ] Fresh reviewer C: SBE traceability/evaluation/no-post-hoc semantics.
- [ ] Record exact P0/P1/P2 counts and artifact commit/tree hash.
- [ ] After T-030 docs and all T-031-owned closure tooling/tests reach their final candidate bytes, rerun the complete T-029 unit→fixture→surface→legacy sequence on that exact final source tree and replace the four stage artifacts with those fresh results before hashing；an earlier T-029 run cannot prove the later tree。
- [ ] Before review, fail on scope-external dirty/untracked source and compute the deterministic authorized final-tree manifest digest; all three reviewers must record that exact `reviewed_tree_sha256` and the aggregator must reject any mismatch or post-review tree drift.
- [ ] Fix every P0/P1, rerun affected tests, then rerun fresh review.

Before the authorized tree hash, the T-031-owned `tests/test_subject_attestation.py` must exercise both legal controls (`T-032=BLOCKED`→`experimental` with no private inputs and `T-032=COMPLETED`→independently revalidated `stable`), plus completed-branch missing verifier executable、missing gate input、missing verifier config、missing release receipt、unknown/unavailable verifier、unknown selected key、wrong HMAC domain、MAC mismatch、canonicalization mismatch、self-field inclusion、canonical scorecard recomputation mismatch、distinct-signoff drift、threshold drift、complete-receipt digest／stdout handoff mismatch、invalid receipt/status pairing、manual `T-033=COMPLETED` ledger rewrite、attestation-write/ledger-replace crash-resume、and final replay validation. It must also run the producer and completed attester blocks from a parent shell with inherited `set -x`, seed unique harmless markers for every private argv/path/result value, and prove the blocks' first-command `set +x` prevents every marker from reaching parent/child stdout, stderr, or any repo log/artifact. Every DENY must assert nonzero exit、no attestation/final-ledger mutation、bounded public-safe stderr and no private echo；the valid completed control must assert the exact one-line `private-shadow-pass:<64 lowercase hex>` handoff and `stable` ALLOW. Run this complete matrix and its task-local focused command together with the T-001-owned progress test before computing `reviewed_tree_sha256`; both test files and the completed attester must then enter the authorized reviewed tree unchanged.

The same T-031-owned test file must explicitly cover the T-033 child-channel grammar as a byte matrix. Valid control: exit `0`, stderr empty, and exactly one LF-terminated stdout line matching `private-shadow-pass:[0-9a-f]{64}`. Success-path DENY cases: multiline stdout、missing final LF、extra stdout bytes、wrong stdout format, or any nonempty stderr. Failure-path DENY cases: nonempty stdout；unknown stderr code；multiline、non-ASCII, or more-than-96-byte stderr；and a child that attempts to print private argv、path, or result markers. Every malformed case must prove nonzero attester exit, fixed no-echo public-safe attester error, byte-identical preexisting `attestation.json` and progress ledger (or continued absence when absent), and no private marker in stdout、stderr or any repo log/artifact. The exact valid control must alone permit the independently verified `stable` path.

The actual T-031 attester test matrix must also exercise the complete design §5
private-config and child lifecycle boundary, not only a mocked progress
validator helper. Config fixtures cover 1 and 64 sorted unique keys as ALLOW and
0/65、duplicate、unsorted、unknown、non-canonical、wrong mode、symlink/final or
ancestor replacement as DENY. Child fixtures cover exact stdout 85/stderr 96
caps and both one-byte-over cases while both pipes are concurrently drained；a
single monotonic 300-second deadline through injected short test timing；one
pipe blocked while the other is active；whole-process-group terminate、at most
5 seconds grace、force-kill and reap；and a descendant retaining a pipe. Every
failure proves no private echo、no attestation mutation、no final-ledger
mutation and no orphan child. These tests reuse the same implementation path
that `scripts/attest_subject_closure.py` invokes；a test-only alternate reader or
config parser is not acceptance evidence.

Review-tree rule：T-031 must include `implementation-progress.schema.json`、`scripts/validate_subject_progress.py`、`scripts/update_subject_progress.py`、the completed `scripts/attest_subject_closure.py`、`tests/test_subject_progress.py` and `tests/test_subject_attestation.py` as authorized source paths before hashing, and include the T-030-frozen `CHANGELOG.md`; it must exclude `implementation-progress.json`, generated evidence and private pilot data. All three reviewers must review the attester's progress/authorization/tree/evidence bindings before PASS. After `reviewed_tree_sha256` is computed, no authorized source byte may change. Fixed-path review evidence may be produced outside that tree, and the only mutable control-plane file is the excluded progress ledger. After all three reviews and aggregate validation pass, record `T-031=COMPLETED` only through the atomic writer and rerun the progress validator；any P0/P1 source fix requires a new tree hash and fresh review.

**Pass condition:** all blocking reviews are `PASS`, P0=0, P1=0. P2 has explicit disposition.

**Evidence command:**

```bash
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
python -m pytest -q tests/test_subject_attestation.py
python -m pytest -q tests/test_subject_progress.py
python scripts/record_subject_fresh_review.py --manifest specs/subject-distillation/baseline-manifest.json --require-hash-match --require-reviewed-tree-hash-match --require-p0 0 --require-p1 0 --output "$EVIDENCE_DIR/fresh-review.json" "$EVIDENCE_DIR/reviews/requirements-architecture.json" "$EVIDENCE_DIR/reviews/security-privacy.json" "$EVIDENCE_DIR/reviews/execution-traceability.json"
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require fresh-review
```

### T-032 — Private shadow pilot（operator-private, post-synthetic only）

**Requirements:** R-SD-016、026
**Repo files:** none containing private cases/results

- [ ] Create private preregistered manifest and freeze gate version.
- [ ] Verify N/domain/abstention/correction requirements before running.
- [ ] Run all eligible cases; no preferred subset or outcome-based exclusion.
- [ ] Close immutable scorecard; obtain matching subject/controller and fresh reviewer signoffs.
- [ ] If PASS, retain evidence in private governed store and only record public-safe release attestation.
- [ ] If FAIL or not run, label feature `experimental`; propose next-version candidate only.

**Operator-private producer invocation contract（not a repo command）：** the executable name is deliberately supplied by the operator-private environment; no repository executable is asserted to exist. With shell xtrace disabled, invoke the fixed subcommand and argument contract exactly as follows:

```bash
set +x
: "${SUBJECT_PRIVATE_EVAL_VERIFIER:?operator-private verifier executable is required}"
: "${PRIVATE_SHADOW_GATE_INPUT:?operator-private closed-gate input is required}"
: "${PRIVATE_SHADOW_VERIFIER_CONFIG:?operator-private key/config input is required}"
: "${PRIVATE_SHADOW_RELEASE_RECEIPT:?operator-private receipt output is required}"
"$SUBJECT_PRIVATE_EVAL_VERIFIER" produce-release-receipt \
  --gate-input "$PRIVATE_SHADOW_GATE_INPUT" \
  --verifier-config "$PRIVATE_SHADOW_VERIFIER_CONFIG" \
  --receipt-output "$PRIVATE_SHADOW_RELEASE_RECEIPT" \
  --public-handoff-output -
```

`--gate-input` is the operator-private closed gate/case store consumed through the canonical evaluation verifier；`--verifier-config` is the operator-private `key_id`→key configuration；`--receipt-output` is the complete duplicate-key-safe receipt retained outside the repo；and `--public-handoff-output -` must emit exactly one stdout line, `private-shadow-pass:<64 lowercase hex public receipt SHA-256>`, only after all thresholds、distinct signoffs、canonicalization and HMAC checks pass. Exit is nonzero otherwise, and stderr may contain only a bounded public-safe error code. The invoker may pass the one-line opaque ref to the T-032 progress event and later pass the private receipt path to T-033 through `PRIVATE_SHADOW_RELEASE_RECEIPT`; it must never write or echo a raw case、private gate/path、key/config、full receipt、or private result into the repo or logs.

**Hard rule:** privacy, authority, provenance, temporal correctness and high-risk action invariants may never be tuned down.

**Closure relationship:** `T-032=COMPLETED` is legal exclusively after the operator-private evaluation verifier reopens the closed gate, recomputes the canonical scorecard, verifies every R-SD-016 threshold and both distinct signoffs, verifies the release receipt HMAC, and produces that receipt's SHA-256. The duplicate-key-safe receipt stays in the private governed store and, after exact type validation, has exactly these keys: `schema_version`=non-Boolean JSON integer `1`、`artifact_kind`=`private-shadow-release`、`verdict`=`PASS`、bounded opaque `gate_version`、lowercase 64-hex `scorecard_sha256`、lowercase 64-hex `manifest_sha256`、distinct bounded opaque `subject_controller_signoff_id` and `fresh_reviewer_signoff_id`、semantic UTC RFC3339 `created_at_utc`、bounded non-secret `key_id` matching `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$`、and lowercase 64-hex `receipt_hmac_sha256`; it contains no raw case、name、private path、key or other secret. `key_id` selects exactly one key from operator-private evaluation-verifier config；the receipt/repo/log never contains the key. The HMAC domain separator bytes are exactly the UTF-8/ASCII bytes for `vault-subject-private-shadow-release-v1` followed by one NUL byte `0x00`（equivalently `b"vault-subject-private-shadow-release-v1\x00"`）. Producer must duplicate-key-safely parse and exact-key/type validate the receipt object, remove only `receipt_hmac_sha256`, encode the remaining object with the existing RFC8785-like project canonical JSON contract（recursive sorted object keys、UTF-8、no insignificant whitespace、non-finite numbers rejected；no new hash algorithm）, then compute exactly `HMAC-SHA256(selected_key, domain_separator_bytes || canonical_receipt_without_hmac_bytes)` with no delimiter、length prefix、newline or self-field；store its lowercase 64-hex result as `receipt_hmac_sha256`. The public receipt SHA-256 is over the complete validated canonical receipt bytes including `receipt_hmac_sha256`. Verification must repeat those exact bytes and use constant-time MAC comparison；missing verifier key/config、unknown `key_id`、malformed canonical input or mismatch fails closed with no plain-SHA fallback. The completion event must contain exactly one matching opaque ref `private-shadow-pass:<64 lowercase hex receipt SHA-256>`. FAIL or not-run must be represented as`T-032=BLOCKED` with a bounded public-safe blocker code and no PASS-receipt ref. At T-033, `release_label=stable` iff T-032 is`COMPLETED` and the attester independently revalidates the matching receipt；`release_label=experimental` iff T-032 is`BLOCKED`. No other status／label pairing is valid, and neither branch authorizes an understanding or high-risk autonomy claim.

### T-033 — Final attestation and implementation closure

**Requirements:** R-SD-016
**Files:** reuse the T-031-created and reviewed `scripts/attest_subject_closure.py` and `tests/test_subject_attestation.py` without changing either file's bytes；write `$EVIDENCE_DIR/attestation.json`; no product behavior changes

- [ ] Verify working tree contains only authorized files.
- [ ] Verify all required artifacts and exact command outputs exist.
- [ ] Verify release label reflects private shadow truth.
- [ ] Verify implementation was explicitly authorized and fresh reviewers reviewed the actual final tree.
- [ ] Recompute the authorized final-tree manifest after every prerequisite, require equality with all three review inputs and `fresh-review.json`, and fail if any source byte or scope membership changed after review.
- [ ] Provide final four-part report: completed work, issues, fixes, test/reviewer evidence.

Attestation rules：

- Before attestation, the attester must accept the exact manifest、progress schema、tasks file and progress ledger paths and call the same duplicate-key-safe progress validation API used by the CLI. It must refuse output unless the ledger binds the hash-verified manifest `baseline_id`／`closure.full_digest` and reviewed `tasks.md` SHA-256, T-001..T-031 are`COMPLETED`, T-033 is`IN_PROGRESS`, and T-032 is exactly`COMPLETED|BLOCKED`. Caller-provided status summaries or a separately parsed status map are not evidence.
- The attester derives, never accepts, the release label. For T-032=`COMPLETED`, all four operator-private inputs are mandatory and empty/missing values DENY: `SUBJECT_PRIVATE_EVAL_VERIFIER`（operator-private executable, not a claimed repo command）、`PRIVATE_SHADOW_GATE_INPUT`（closed gate/case input）、`PRIVATE_SHADOW_VERIFIER_CONFIG`（`key_id`→key/config input）and `PRIVATE_SHADOW_RELEASE_RECEIPT`（complete receipt input）. With shell xtrace disabled, the attester must invoke exactly `"$SUBJECT_PRIVATE_EVAL_VERIFIER" reopen-and-verify-release-receipt --gate-input "$PRIVATE_SHADOW_GATE_INPUT" --verifier-config "$PRIVATE_SHADOW_VERIFIER_CONFIG" --release-receipt "$PRIVATE_SHADOW_RELEASE_RECEIPT" --public-handoff-output -`; no alternate subcommand, flag alias, receipt-only mode or caller-supplied verdict is legal. The private verifier must reopen the closed gate and independently recompute canonical scorecard bytes、every threshold、both distinct signoffs、receipt HMAC and complete validated canonical receipt SHA-256. Success is exit 0, empty stderr, and exactly one LF-terminated stdout line matching `private-shadow-pass:[0-9a-f]{64}`；failure is nonzero with stdout empty and at most one LF-terminated ASCII stderr line `private-shadow-error:<code>`（maximum 96 bytes total）, where `code` is exactly one of `missing-input|verifier-unavailable|unknown-key|invalid-private-input|recompute-mismatch|signoff-drift|threshold-drift|hmac-mismatch|receipt-digest-mismatch|internal-failure`. The attester must capture rather than forward child output, reject every other byte, and never echo or persist argv、private paths、keys/config、gate data、full receipt or private result in repo output or logs.
- Child-channel validation is byte-exact and fail-closed: exit-0 children with multiline/missing-LF/extra-byte/wrong-format stdout or nonempty stderr DENY；nonzero children with nonempty stdout、unknown/multiline/non-ASCII/>96-byte stderr, or attempted private argv/path/result output DENY. The attester emits only its fixed no-echo public-safe error, creates or changes neither attestation nor ledger, and leaves no private marker in repository logs/artifacts. Only the exact valid control (exit 0, empty stderr, one LF-terminated matching stdout line) may proceed.
- A successful private-verifier process is necessary but not sufficient. The attester must reject symlink/non-regular gate/config/receipt inputs, duplicate-key-safely parse the complete receipt, enforce the exact T-032 key/type contract, select the exact bounded `key_id` from operator-private config, rebuild domain bytes `b"vault-subject-private-shadow-release-v1\x00"` and the existing canonical JSON bytes with only `receipt_hmac_sha256` removed, verify `HMAC-SHA256(selected_key, domain_bytes || canonical_receipt_without_hmac_bytes)` by constant-time lowercase-hex comparison with no plain-SHA fallback, hash the complete validated canonical receipt including the HMAC, require equality among that digest、the verifier stdout digest and the ledger's exact `private-shadow-pass:<receipt SHA-256>` opaque ref, and only then write `release_label=stable` plus that SHA-256. Missing input、unknown/unavailable verifier or key、recomputation mismatch、signoff/threshold drift、HMAC/canonicalization mismatch or digest mismatch all DENY. For T-032=`BLOCKED`, all four private flags must be absent, and the attester writes `release_label=experimental` plus `private_shadow_receipt_sha256=null`; any private input or other pairing fails closed.
- `PRIVATE_SHADOW_VERIFIER_CONFIG` is not an implementation-defined mapping. It must satisfy design §5's exact canonical JSON v1 grammar、65,536-byte cap、1..64 strictly sorted unique entries、bounded `key_id` and exact lowercase 32-byte-key hex encoding. The attester retains and audits that external mode-0600 single-link regular file, selects the matching key itself, and independently performs the HMAC check with `hmac.compare_digest`; it must DENY even after exact child PASS when the config、key selection、domain、canonical receipt-without-HMAC or MAC is invalid. Neither a readable in-process capability object nor the child verdict is authority.
- Child output must use the design §5 bounded reader: concurrently drained stdout cap 85 bytes、stderr cap 96 bytes、one monotonic 300-second deadline、new process group, whole-group terminate, at-most-5-second grace, force-kill and reap. The implementation must never use unbounded `capture_output`; timeout、one-byte-over、cross-pipe stall、descendant-held pipe or incomplete cleanup DENY with no private echo or repository mutation.
- `attestation.json.artifact_sha256` and recomputed `reviewed_tree_sha256` must exclude `implementation-progress.json`. The authorized progress schema、progress validator、atomic progress writer and frozen attester source must be included in`reviewed_tree_sha256` but are not duplicated in the fixed closure-evidence`artifact_sha256` set. No authorized source or T-030-frozen CHANGELOG byte may change after T-031 hashing.
- `experimental`與`stable`都只是evidence label，不是merge/release/default-on rollout authority。任何distribution、new-install enablement、cohort/canary或release仍需designated release authority另行核對installed-artifact parity、rollback/kill procedure與operator-facing label；`experimental`不得被UI/docs隱藏或宣稱production-ready。
- The reviewed attester owns the finalization operation: validate pre-state；atomically write and fully validate the fixed attestation；append exactly `T-033: IN_PROGRESS→COMPLETED` with the fixed attestation repo path/current SHA-256 `repo_file` ref to a temporary ledger；run the progress validator in automatic final mode so it repeats the fixed evidence、review-tree、authorization and, for`stable`, private receipt gate；only then atomically replace the ledger. Any failure must leave T-033 non-completed and must not retain a newly invalid attestation；a crash after a valid attestation write but before ledger replacement remains safely`IN_PROGRESS` and may only resume by byte-validating the same fixed artifact. Manual final ledger rewrites are forbidden.

**Evidence command:**

Completed and blocked are two explicit invocation forms；the attester derives and validates T-032 from the ledger and rejects whichever form does not match that pre-state. The completed branch is:

```bash
set +x
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
: "${SUBJECT_PRIVATE_EVAL_VERIFIER:?operator-private verifier executable is required}"
: "${PRIVATE_SHADOW_GATE_INPUT:?operator-private closed-gate input is required}"
: "${PRIVATE_SHADOW_VERIFIER_CONFIG:?operator-private key/config input is required}"
: "${PRIVATE_SHADOW_RELEASE_RECEIPT:?operator-private release receipt is required}"
python -m pytest -q tests/test_subject_attestation.py
python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json
python scripts/attest_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --progress-schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json --private-shadow-verifier "$SUBJECT_PRIVATE_EVAL_VERIFIER" --private-shadow-gate-input "$PRIVATE_SHADOW_GATE_INPUT" --private-shadow-verifier-config "$PRIVATE_SHADOW_VERIFIER_CONFIG" --private-shadow-release-receipt "$PRIVATE_SHADOW_RELEASE_RECEIPT" --evidence-dir "$EVIDENCE_DIR" --require environment,unit,fixture,surface,legacy,migration,backup-restore,fresh-review --require-reviewed-tree-hash-match --require-implementation-authorization --output "$EVIDENCE_DIR/attestation.json"
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require environment,unit,fixture,surface,legacy,migration,backup-restore,fresh-review,attestation --require-reviewed-tree-hash-match
python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json --private-shadow-verifier "$SUBJECT_PRIVATE_EVAL_VERIFIER" --private-shadow-gate-input "$PRIVATE_SHADOW_GATE_INPUT" --private-shadow-verifier-config "$PRIVATE_SHADOW_VERIFIER_CONFIG" --private-shadow-release-receipt "$PRIVATE_SHADOW_RELEASE_RECEIPT"
```

The T-032=`BLOCKED` branch omits all four private flags and must DENY if the ledger is not exactly blocked:

```bash
set +x
BASELINE_ID="$(python scripts/read_subject_baseline_id.py --manifest specs/subject-distillation/baseline-manifest.json)"
EVIDENCE_DIR="specs/subject-distillation/evidence/${BASELINE_ID}"
python -m pytest -q tests/test_subject_attestation.py
python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json
python scripts/attest_subject_closure.py --manifest specs/subject-distillation/baseline-manifest.json --progress-schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json --evidence-dir "$EVIDENCE_DIR" --require environment,unit,fixture,surface,legacy,migration,backup-restore,fresh-review --require-reviewed-tree-hash-match --require-implementation-authorization --output "$EVIDENCE_DIR/attestation.json"
python scripts/validate_subject_evidence.py --manifest specs/subject-distillation/baseline-manifest.json --evidence-dir "$EVIDENCE_DIR" --require environment,unit,fixture,surface,legacy,migration,backup-restore,fresh-review,attestation --require-reviewed-tree-hash-match
python scripts/validate_subject_progress.py --manifest specs/subject-distillation/baseline-manifest.json --schema specs/subject-distillation/implementation-progress.schema.json --tasks specs/subject-distillation/tasks.md --progress specs/subject-distillation/implementation-progress.json
```

## 12. Requirement-to-task matrix

此表由每個T-header的`Requirements`欄機械反算；header是唯一normative source，closure必須重算並要求byte-equivalent mapping，禁止手動補表。

| Requirement | Tasks |
|---|---|
| R-SD-001 | T-004, T-006–T-007, T-020, T-029, T-031 |
| R-SD-002 | T-002, T-028–T-029, T-031 |
| R-SD-003 | T-004, T-006, T-008–T-010, T-013, T-020, T-022, T-024, T-029, T-031 |
| R-SD-004 | T-006–T-007, T-010–T-013, T-028–T-029, T-031 |
| R-SD-005 | T-006, T-009–T-010, T-013–T-014, T-029, T-031 |
| R-SD-006 | T-004, T-006–T-007, T-013–T-014, T-017–T-018, T-020, T-029, T-031 |
| R-SD-007 | T-004, T-006, T-008–T-009, T-015, T-020–T-024, T-029, T-031 |
| R-SD-008 | T-006, T-008, T-012, T-015–T-016, T-020, T-022–T-024, T-028–T-029, T-031 |
| R-SD-009 | T-004, T-006–T-007, T-017, T-022, T-029, T-031 |
| R-SD-010 | T-004, T-006, T-014, T-016, T-020, T-022, T-029, T-031 |
| R-SD-011 | T-006, T-008–T-009, T-015–T-016, T-022–T-024, T-029, T-031 |
| R-SD-012 | T-006–T-009, T-013–T-017, T-020, T-022, T-029, T-031 |
| R-SD-013 | T-006, T-009, T-014, T-020, T-029, T-031 |
| R-SD-014 | T-014, T-019–T-024, T-028–T-031 |
| R-SD-015 | T-001, T-005–T-006, T-027, T-029–T-031 |
| R-SD-016 | T-001, T-003, T-006, T-025–T-026, T-029–T-033 |
| R-SD-017 | T-010, T-013, T-017, T-022–T-024, T-029, T-031 |
| R-SD-018 | T-006, T-008–T-009, T-011–T-013, T-015–T-016, T-018–T-019, T-024, T-028–T-029, T-031 |
| R-SD-019 | T-006–T-007, T-013–T-016, T-020, T-022–T-024, T-029–T-031 |
| R-SD-020 | T-003–T-004, T-006, T-014, T-020, T-029–T-031 |
| R-SD-021 | T-006–T-007, T-010–T-014, T-028–T-029, T-031 |
| R-SD-022 | T-006–T-007, T-018, T-022, T-029, T-031 |
| R-SD-023 | T-006–T-007, T-009, T-013, T-016, T-018–T-019, T-029, T-031 |
| R-SD-024 | T-019, T-022–T-024, T-028–T-031 |
| R-SD-025 | T-005–T-006, T-008, T-021–T-024, T-029–T-031 |
| R-SD-026 | T-006, T-010, T-017, T-022, T-025–T-026, T-029–T-032 |

## 13. Current gate

- Normative current-truth contract: apply `baseline-manifest.json` mechanical identity only when its five recorded canonical hashes equal disk bytes, its canonical `closure.full_digest` and 16-hex `baseline_id` mechanically recompute from those hashes, and `baseline_state` is a manifest-validator-recognized frozen state. Otherwise the disk bytes are unreviewed remediation, no manifest verdict applies, and this section does not invent one.
- Implementation authorization code: `NOT_AUTHORIZED` — no coding or implementation may start from this artifact alone；B-001完成前不得產生proposal；其後`propose`仍不得建立private candidate，只有owner確認完整canonical proposal與exact receipt SHA-256且單一runner/verifier/cleanup PASS才授權T-task implementation。
- Renderer-proof authorization remains `NOT_AUTHORIZED` in the normative package；a separate designated release authority receipt is applicable only when it binds the same successfully verified manifest `baseline_id`、`closure.full_digest` and authorized scope, and may never be inferred from review PASS.
- Completed historical pre-task: **B-000, merged through PR #423**.
- Completed pre-task: **B-001, merged and independently reviewed；its runner remains hash-pinned and fail-closed**.
- First product implementation task: **T-001, BLOCKED until this repaired canonical baseline is independently reviewed and delivered, then a fresh exact-base proposal is generated, the owner separately confirms that complete canonical proposal/digest, and one `verify-confirmed` process re-derives、verifies and identity-safely cleans the private objects**. Any proposal bound to superseded canonical bytes is invalid.
- No current baseline ID is hard-coded in these canonical docs。After canonical byte changes，the parent rebinds the manifest and applies risk-based review；planning-only changes and ordinary implementation iterations within unchanged authorized scope do not require a repeated owner prompt。
