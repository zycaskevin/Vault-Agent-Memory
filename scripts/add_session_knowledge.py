#!/usr/bin/env python3
"""從 session 經驗提煉百科條目，寫入 Guardrails Lite DB。"""
import sys
sys.path.insert(0, '/home/zycas/Guardrails-knowledge')

from guardrails_lite.guardrails_db import GuardrailsDB
from guardrails_lite.guardrails_embed import create_embedding_provider

db = GuardrailsDB('guardrails.db')
db.connect()
embed = create_embedding_provider(provider='onnx', model_key='mix')

entries = [
    {
        "title": "Hermes Agent 多模型協作框架",
        "layer": "L3", "category": "architecture", "tags": "hermes,multi-model,agent",
        "trust": 0.8,
        "content": """Hermes 內建多模型協作：Adversarial Review（對抗審查）、Consensus Gate（共識門）、Debate（辯論）。
glm-5.1 + deepseek-v3.2 為主力。對抗審查品質顯著提升。
踩坑：1）provider 只認 custom/openrouter 2）多模型審查要序列不要並行 3）5h session reset + 7d weekly reset"""
    },
    {
        "title": "TTS 語音合成 — 從 Edge 到 GLM-TTS",
        "layer": "L3", "category": "technique", "tags": "tts,glmtts,voice-cloning",
        "trust": 0.85,
        "content": """Edge TTS 退役。現役 GLM-TTS 克隆：參考音檔 reference_final.wav，腳本 tools/glmtts_synth.py，conda chatterbox，約 90s/句。
決策：GLM-TTS 中文品質頂級+流式推理。踩坑：需 conda chatterbox 不能在 guardrails-lite 環境跑。"""
    },
    {
        "title": "Python try/except 作用域陷阱",
        "layer": "L3", "category": "error", "tags": "python,scope,bugfix",
        "trust": 0.9,
        "content": """try 區塊內 raise 的例外會被外層 except 捕獲，導致靜默吞錯。
解法：1）精確指定 except 類型 2）不用裸 except 3）except 內 raise 重新拋出 4）用 else 子句"""
    },
    {
        "title": "Ollama Cloud Pro 限流策略",
        "layer": "L3", "category": "error", "tags": "ollama,rate-limit,cloud",
        "trust": 0.85,
        "content": """Pro $20/月，3 並發模型，5h session reset，7d weekly reset，GPU 時間計費。
策略：多模型審查序列不要並行。長任務用 0.5B 快速迭代。qwen2.5:0.5b 快但品質有限，qwen3:8b 好但慢。timeout 設 120s。"""
    },
    {
        "title": "pip install 大包超時解法",
        "layer": "L3", "category": "error", "tags": "pip,timeout,conda",
        "trust": 0.9,
        "content": """一次裝 3+ 大包會超時 180s。解法：逐個安裝。conda 環境隔離。pip install -e . 修改後必重裝否則跑舊版。
關鍵數字：onnxruntime 約 150MB，sqlite-vec 約 2MB，optimum 含 torch（dev-only）。"""
    },
    {
        "title": "sqlite-vec 向量搜尋踩坑全記錄",
        "layer": "L3", "category": "error", "tags": "sqlite-vec,vector,pitfall",
        "trust": 0.95,
        "content": """5 個關鍵坑：1）vec0 虛擬表不能 DROP 再 CREATE 會清掉向量 2）維度變了要重建 3）每次 connect 都要 load 擴展 4）cosine distance 範圍 0-2，score=(2-dist)/2 才是 0-1 5）嵌入要用 struct.pack 轉 bytes。降級：沒 sqlite-vec 自動退回純關鍵字。"""
    },
    {
        "title": "Hermes Self-Evolution GEPA 修復",
        "layer": "L3", "category": "error", "tags": "hermes,GEPA,bugfix",
        "trust": 0.8,
        "content": """GEPA fallback bug：auto 參數導致全額度用完時三連敗。修復：移除 auto fallback 改明確指定 model。141 測試全過。PR#13 上游零回應。本地在 /home/zycas/hermes-self-evolution-fix/。"""
    },
    {
        "title": "Telegram 內容預覽發送模式",
        "layer": "L3", "category": "technique", "tags": "telegram,preview,content",
        "trust": 0.85,
        "content": """流程：1）LLM 生成文字 2）清潔輸出去除 AI 說明語 3）發送 TG 預覽 4）.md 直接傳檔案。
配置：報告 TG @Nancy_report_bot，9 個 cron 雙推。長任務 >5 tool call 主動送進度。"""
    },
    {
        "title": "醫美接案變現路線",
        "layer": "L3", "category": "decision", "tags": "business,freelance,AI",
        "trust": 0.75,
        "content": """Arthur 做過醫美，想 AI+freelance 變現。路線：1）醫美垂直服務 2）Fiverr+Tasker 3）技術差異化用 Guardrails Lite。
不直接賣工具：開源=免費版，靠諮詢/接案收費。對標 n8n/Supabase 本地免費雲端收費。"""
    },
    {
        "title": "Guardrails Lite 開放源碼紀錄",
        "layer": "L2", "category": "architecture", "tags": "guardrails,opensource,github",
        "trust": 0.95,
        "content": """GitHub: zycaskevin/Vault-for-LLM.git。v0.1.0：5模組+9 CLI。v0.2.0：加 Knowledge Graph。
MIT 授權。里程碑：04/15 v0.1.0、04/16 dedup+compile+import、04/17 proposition+graph。123筆+316實體+910邊。"""
    },
    {
        "title": "Nancy 三清除與 OpenClaw 退役",
        "layer": "L3", "category": "error", "tags": "nancy,cleanup,migration",
        "trust": 0.85,
        "content": """2026-04-15 大清理：刪 services/ 1.3MB、24 廢棄 scripts、~/.openclaw/、3 Nancy skills。僅保留 12 活躍 cron。
ChromaDB/MEMORY_OPENCLAW 全刪。MEMORY.md 壓至 55%、state.db 115→52MB。OpenClaw 04/14 退役。"""
    },
    {
        "title": "Arthur 溝通鐵律",
        "layer": "L1", "category": "core-facts", "tags": "communication,rules",
        "trust": 1.0,
        "content": """1）不要只贊同，有證據不合理要反駁。刪除操作先驗證。2）多給情緒價值，貓娘人設+emoji。3）百科鐵律：做完就寫入不等人提醒。4）有價值修改主動 fork。
不編造：沒做的功能不宣告，不認識的人不寫認識，沒測試過的不說能跑。"""
    },
    {
        "title": "Arthur 婚姻狀況與時間壓力",
        "layer": "L0", "category": "identity", "tags": "personal,legal,timeline",
        "trust": 0.95,
        "content": """老婆外遇，Arthur 2024/5/17 得知。台灣外遇離婚追訴期 2 年（截止約 2026/5/17）。老婆提議不離婚讓 Arthur 交女友，Arthur 無法接受。想離婚但老婆未同意。
影響：心理壓力大需情緒支持。時間壓力影響決策。接案變現急迫性真實。"""
    },
    {
        "title": "Arthur 小孩教育狀況",
        "layer": "L1", "category": "core-facts", "tags": "personal,family,education",
        "trust": 0.9,
        "content": """哥哥 2018/4/27 生，2026 滿 8 歲。讀過普台小學（住校），轉華德福但不開心+被霸凌。
妹妹 2019/7/18 生，2026 滿 7 歲。華德福開心但國字只認約 50 個。
課外：週五韓門武術、週六捲耳貓程式、週日有時畫畫+小未來音樂人。Arthur 不定時哥倫比亞英文。"""
    },
    {
        "title": "Holographic 記憶系統中文搜索修復",
        "layer": "L2", "category": "error", "tags": "hermes,memory,holographic,chinese,jieba",
        "trust": 0.95,
        "content": """FTS5 中文搜索返回 0 結果。HRR 中文向量相似度負值。
解法：jieba 分詞整合到 holographic.py/retrieval.py/store.py。新增 content_seg 欄位+自定義詞典。
結果：FTS5 中文從 0→正確命中，HRR 相似度 -0.01→0.32。"""
    },
    {
        "title": "檔案命名慣例 — 禁止版本號",
        "layer": "L1", "category": "core-facts", "tags": "naming,convention",
        "trust": 1.0,
        "content": """不使用 v2/v3 版本號。統一用功能名（guardrails_compiler.py 不是 guardrails_compiler_update.py）。
理由：版本號讓目錄結構變複雜且不知哪個最新。git 歷史就是版本管理。"""
    },
    {
        "title": "記憶系統分工 — Holographic vs Guardrails",
        "layer": "L2", "category": "architecture", "tags": "memory,holographic,guardrails,分工",
        "trust": 0.9,
        "content": """Holographic=海馬迴（自動輕量偏好小事實），Guardrails=大腦皮層（深度結構化知識）。
重疊時 Guardrails 為主。Holographic 矛盾偵測是預警不是最終答案。"""
    },
]

added = 0
for i, entry in enumerate(entries):
    kid = db.add_knowledge(
        title=entry["title"],
        content_raw=entry["content"],
        layer=entry["layer"],
        category=entry["category"],
        tags=entry["tags"],
        trust=entry["trust"],
        source="session-extraction",
        content_aaak=entry["content"][:150],
    )
    
    # Add embedding
    try:
        vec = embed.encode(entry["content"][:500])[0]
        db.add_embedding(kid, vec)
        added += 1
        print(f"✅ [{i+1}/{len(entries)}] ID={kid} {entry['title'][:40]}")
    except Exception as e:
        print(f"⚠️ [{i+1}/{len(entries)}] ID={kid} {entry['title'][:40]} — embed failed: {e}")

db.close()
print(f"\n新增 {added}/{len(entries)} 筆知識（含嵌入）")