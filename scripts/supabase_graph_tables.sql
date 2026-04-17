-- Guardrails Lite 圖譜表 — 在 Supabase SQL Editor 執行

-- 知識圖譜：實體表
CREATE TABLE IF NOT EXISTS gr_entities (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'tag',
    knowledge_ids JSONB DEFAULT '[]',
    mention_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, entity_type)
);

-- 知識圖譜：邊表
CREATE TABLE IF NOT EXISTS gr_edges (
    id BIGSERIAL PRIMARY KEY,
    source_id UUID REFERENCES guardrails_knowledge(id) ON DELETE CASCADE,
    target_id UUID REFERENCES guardrails_knowledge(id) ON DELETE CASCADE,
    relation TEXT NOT NULL DEFAULT 'related_to',
    weight REAL DEFAULT 1.0,
    auto_inferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, target_id, relation)
);

-- 實體 ↔ 知識條目 關聯表
CREATE TABLE IF NOT EXISTS gr_entity_knowledge (
    id BIGSERIAL PRIMARY KEY,
    entity_id BIGINT REFERENCES gr_entities(id) ON DELETE CASCADE,
    knowledge_id UUID REFERENCES guardrails_knowledge(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, knowledge_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_edges_source ON gr_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON gr_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation ON gr_edges(relation);
CREATE INDEX IF NOT EXISTS idx_edges_auto ON gr_edges(auto_inferred);
CREATE INDEX IF NOT EXISTS idx_entities_type ON gr_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON gr_entities(name);
CREATE INDEX IF NOT EXISTS idx_ek_entity ON gr_entity_knowledge(entity_id);
CREATE INDEX IF NOT EXISTS idx_ek_knowledge ON gr_entity_knowledge(knowledge_id);

-- 啟用 RLS
ALTER TABLE gr_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE gr_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE gr_entity_knowledge ENABLE ROW LEVEL SECURITY;

-- 允許 anon 讀取
CREATE POLICY "Allow read access" ON gr_entities FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON gr_edges FOR SELECT USING (true);
CREATE POLICY "Allow read access" ON gr_entity_knowledge FOR SELECT USING (true);

-- 允許 anon 寫入
CREATE POLICY "Allow write access" ON gr_entities FOR ALL USING (true);
CREATE POLICY "Allow write access" ON gr_edges FOR ALL USING (true);
CREATE POLICY "Allow write access" ON gr_entity_knowledge FOR ALL USING (true);