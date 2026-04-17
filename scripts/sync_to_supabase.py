#!/usr/bin/env python3
"""
Sync Guardrails Lite → Supabase
把本地 DB 的知識（包含嵌入）同步到 Supabase。

策略：
1. 讀取本地 DB 全部知識 + 嵌入
2. 用 title 去重（本地有的才更新/新增）
3. 新增的插入，已有的更新
4. Supabase 多餘的不刪除（保留雲端獨有的）
"""
import os, sys, json, time
from dotenv import load_dotenv
from supabase import create_client

sys.path.insert(0, "/home/zycas/Guardrails-knowledge")
from guardrails_lite.guardrails_db import GuardrailsDB

load_dotenv('/home/zycas/.hermes/.env')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

db = GuardrailsDB("/home/zycas/Guardrails-knowledge/guardrails.db")
db.connect()

# 1. Get all local knowledge
local_rows = db.conn.execute("""
    SELECT k.id, k.title, k.content_raw, k.content_aaak, k.layer, k.category, 
           k.tags, k.trust, k.source, k.created_at,
           kv.embedding
    FROM knowledge k
    LEFT JOIN knowledge_vec kv ON k.id = kv.knowledge_id
""").fetchall()

print(f"📚 本地知識: {len(local_rows)} 筆")

# 2. Get all Supabase knowledge titles (for dedup)
sb_rows = sb.table('guardrails_knowledge').select('id,title').execute().data
sb_titles = {r['title']: r['id'] for r in sb_rows}
print(f"☁️ Supabase 知識: {len(sb_rows)} 筆")

# 3. Sync
inserted = 0
updated = 0
skipped = 0
failed = 0

for row in local_rows:
    title = row['title']
    # Convert embedding bytes to list
    try:
        emb_bytes = row['embedding'] if 'embedding' in row.keys() else None
    except (KeyError, IndexError):
        emb_bytes = None
    if emb_bytes:
        import struct
        dim = len(emb_bytes) // 4
        vec_list = list(struct.unpack(f'{dim}f', emb_bytes))
    else:
        vec_list = None
    
    # Convert tags from comma-separated string to list
    tags_str = row['tags'] or ''
    if isinstance(tags_str, str):
        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
    elif isinstance(tags_str, list):
        tags_list = tags_str
    else:
        tags_list = []
    
    # Content hash (required by Supabase)
    import hashlib
    content_hash = hashlib.sha256((row['content_raw'] or '').encode()).hexdigest()[:16]
    
    payload = {
        'title': title,
        'content_raw': row['content_raw'] or '',
        'content_aaak': row['content_aaak'] or '',
        'content_hash': content_hash,
        'layer': int(row['layer'].replace('L', '')) if row['layer'] else 3,
        'category': row['category'] or 'general',
        'tags': tags_list,
        'trust': float(row['trust'] or 0.5),
        'source': row['source'] or 'guardrails-lite',
        'embedding': vec_list,
    }
    
    if title in sb_titles:
        # Update existing
        try:
            sb.table('guardrails_knowledge').update(payload).eq('id', sb_titles[title]).execute()
            updated += 1
        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"  ❌ Update failed: {title[:40]}: {str(e)[:80]}")
    else:
        # Insert new
        try:
            sb.table('guardrails_knowledge').insert(payload).execute()
            inserted += 1
        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"  ❌ Insert failed: {title[:40]}: {str(e)[:80]}")
    
    if (inserted + updated) % 20 == 0 and (inserted + updated) > 0:
        print(f"  {inserted + updated}/{len(local_rows)} synced...")

# 4. Verify
sb_final = sb.table('guardrails_knowledge').select('id,title').execute().data
print(f"\n✅ Sync complete:")
print(f"   Inserted: {inserted}")
print(f"   Updated: {updated}")
print(f"   Skipped: {skipped}")
print(f"   Failed: {failed}")
print(f"   Supabase total: {len(sb_final)}")

db.close()