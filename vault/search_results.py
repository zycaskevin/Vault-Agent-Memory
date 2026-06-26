"""Search result shaping, Document Map enrichment, and reranking helpers."""

from __future__ import annotations

from .search_rerank import (
    LightweightReranker,
    calc_freshness,
    calc_graph_depth,
    calc_usage_boost,
)
from .search_utils import _normalize_text


class SearchResultMixin:
        def _enrich_with_document_map(self, results: list[dict], query: str = "") -> None:
            """Attach best Document Map span metadata to search results when available.

            This is intentionally best-effort: older/local databases without populated
            map rows keep the previous result shape unchanged.
            """
            if self.db.conn is None:
                return

            query_terms = [term.lower() for term in self._tokenize(query or "")]
            for result in results:
                knowledge_id = result.get("id")
                if not knowledge_id:
                    continue
                try:
                    span = self._find_document_map_span(
                        int(knowledge_id),
                        result.get("best_claim", ""),
                        query_terms,
                    )
                except Exception:
                    # Search must not fail because optional map metadata is missing.
                    continue
                if not span:
                    continue

                line_start = span.get("line_start") or span.get("node_line_start")
                line_end = span.get("line_end") or span.get("node_line_end") or line_start
                if not line_start or not line_end:
                    continue

                title = result.get("title", "")
                node = {
                    "node_uid": span.get("node_uid", ""),
                    "heading": span.get("heading", ""),
                    "path": span.get("path", ""),
                    "line_start": span.get("node_line_start") or line_start,
                    "line_end": span.get("node_line_end") or line_end,
                }

                # Backward-compatible top-level fields plus structured fields.
                result["node_uid"] = node["node_uid"]
                result["path"] = node["path"]
                result["heading"] = node["heading"]
                result["line_start"] = int(line_start)
                result["line_end"] = int(line_end)
                result["best_span"] = f"L{line_start}-L{line_end}"
                result["best_node"] = node
                result["citation"] = f"#{knowledge_id} {title} L{line_start}-L{line_end}"
                result["recommended_next_tool"] = "vault_read_range"
                result["next_action"] = {
                    "tool": "vault_map_show",
                    "arguments": {"knowledge_id": int(knowledge_id)},
                }
                result["next_actions"] = [
                    {
                        "tool": "vault_map_show",
                        "arguments": {"knowledge_id": int(knowledge_id)},
                    },
                    {
                        "tool": "vault_read_range",
                        "arguments": {
                            "knowledge_id": int(knowledge_id),
                            "node_uid": node["node_uid"],
                            "line_start": int(line_start),
                            "line_end": int(line_end),
                        },
                    },
                ]

        @staticmethod
        def _compact_result(result: dict) -> dict:
            """Return an opt-in compact search payload without raw content blobs."""
            fields = (
                "id",
                "title",
                "category",
                "layer",
                "trust",
                "tags",
                "best_claim",
                "best_span",
                "node_uid",
                "path",
                "heading",
                "line_start",
                "line_end",
                "citation",
                "recommended_next_tool",
                "next_action",
                "next_actions",
                "temporal_state",
                "valid_from",
                "valid_until",
                "supersedes_id",
            )
            compact = {key: result[key] for key in fields if key in result}
            if "_rerank_score" in result:
                compact["rerank_score"] = result["_rerank_score"]
            return compact

        def _find_document_map_span(
            self,
            knowledge_id: int,
            best_claim: str = "",
            query_terms: list[str] | None = None,
        ) -> dict | None:
            """Return the best claim/node span for one knowledge entry, if populated."""
            query_terms = query_terms or []
            best_claim_norm = _normalize_text(best_claim)

            claim_rows = [
                dict(row)
                for row in self.db.conn.execute(
                    """SELECT c.node_uid, c.claim, c.line_start, c.line_end,
                              n.heading, n.path,
                              n.line_start AS node_line_start,
                              n.line_end AS node_line_end
                       FROM knowledge_claims c
                       LEFT JOIN knowledge_nodes n
                         ON n.knowledge_id = c.knowledge_id
                        AND n.node_uid = c.node_uid
                       WHERE c.knowledge_id=?
                       ORDER BY c.line_start, c.id""",
                    (knowledge_id,),
                ).fetchall()
            ]

            if claim_rows:
                scored_rows: list[tuple[int, dict]] = []
                for row in claim_rows:
                    claim_norm = _normalize_text(row.get("claim", ""))
                    haystack = " ".join(
                        str(row.get(key) or "").lower()
                        for key in ("claim", "path", "heading")
                    )
                    score = 0
                    if best_claim_norm and claim_norm == best_claim_norm:
                        score += 100
                    elif best_claim_norm and (
                        best_claim_norm in claim_norm or claim_norm in best_claim_norm
                    ):
                        score += 75
                    score += sum(10 for term in query_terms if term and term in haystack)
                    scored_rows.append((score, row))

                scored_rows.sort(
                    key=lambda item: (
                        item[0],
                        -(item[1].get("line_start") or 0),
                    ),
                    reverse=True,
                )
                return scored_rows[0][1]

            node = self.db.conn.execute(
                """SELECT node_uid, heading, path,
                          line_start, line_end,
                          line_start AS node_line_start,
                          line_end AS node_line_end
                   FROM knowledge_nodes
                   WHERE knowledge_id=?
                   ORDER BY line_start, level DESC, id
                   LIMIT 1""",
                (knowledge_id,),
            ).fetchone()
            return dict(node) if node else None

        @staticmethod
        def _rerank(results: list[dict], query: str = "") -> list[dict]:
            """
            搜尋結果重排序（靜態版本，向後兼容）。

            有查詢詞時使用輕量級 rerank，
            無查詢詞時使用基礎版 rerank（新鮮度、信任度、圖譜深度）。

            注意：實例級別的搜尋會使用 `_rerank_with_strategy` 方法，
            該方法支援 cross-encoder 等進階策略。

            Args:
                results: 搜尋結果列表
                query: 查詢詞，用於輕量級 rerank 的相關性計算（可選）
            """
            if query:
                # 使用輕量級增強 reranker
                reranker = LightweightReranker()
                return reranker.rerank(query, results)

            # 基礎版 rerank（向後兼容，無 query 時使用）
            for r in results:
                # 基礎語意分數（歸一到 0-1）
                base_sim = r.get("_score", 0.5)
                if isinstance(base_sim, float) and base_sim > 1.0:
                    # RRF 分數可能 > 1，歸一化
                    base_sim = min(base_sim / 0.05, 1.0)  # RRF 典型最大 ~0.05

                trust = r.get("trust", 0.5)
                freshness = r.get("freshness", None)
                if freshness is None:
                    freshness = calc_freshness(r.get("updated_at", ""))
                freshness = max(0.0, min(1.0, freshness))

                graph_bonus = calc_graph_depth(r)
                usage_boost = calc_usage_boost(r)

                rerank_score = (
                    base_sim * 0.5
                    + graph_bonus
                    + trust * 0.15
                    + freshness * 0.15
                    + usage_boost
                )

                r["_original_score"] = r.get("_score", 0.0)  # 保存 rerank 前的原始分數
                r["_rerank_score"] = round(rerank_score, 4)
                r["_score"] = rerank_score  # 更新最終分數，與其他 reranker 行為一致

            results.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
            return results

        def _rerank_with_strategy(self, results: list[dict], query: str = "") -> list[dict]:
            """
            使用實例配置的策略進行重排序。

            有查詢詞時使用配置的 reranker（cross-encoder 優先，否則 fallback 到輕量級），
            無查詢詞時使用基礎版 rerank。

            Args:
                results: 搜尋結果列表
                query: 查詢詞，用於 rerank 的相關性計算（可選）
            """
            if not self._enable_rerank:
                return results

            if query:
                # 使用策略指定的 reranker（cross-encoder 優先，否則 lightweight）
                reranker = self._get_reranker()
                if reranker is not None and reranker.available:
                    return reranker.rerank(query, results)
                # fallback 到輕量級 reranker（總是可用）
                return self._rerank(results, query)

            # 無 query 時使用基礎版 rerank
            return self._rerank(results)

        @staticmethod
        def _extract_best_claim(content_aaak: str) -> str:
            """
            從 AAAK 壓縮內容提取最相關的原子主張。
            如果有 CLAIMS 段，取第一條；否則取 content_raw 前 100 字。
            """
            if not content_aaak:
                return ""

            # 嘗試提取 CLAIMS 段
            if "CLAIMS:" in content_aaak:
                lines = content_aaak.split("\n")
                claims = []
                in_claims = False
                for line in lines:
                    if line.strip() == "CLAIMS:":
                        in_claims = True
                        continue
                    if in_claims and line.strip().startswith("- ["):
                        claims.append(line.strip())
                    elif in_claims and not line.strip().startswith("-"):
                        break

                if claims:
                    # 取第一條作為 best_claim
                    first = claims[0]
                    # 格式: "- [C1] 描述 (L12)"
                    import re
                    match = re.match(r"- \[\w+\]\s*(.+?)(?:\s*\(L\d+\))?$", first)
                    if match:
                        return match.group(1).strip()
                    return first.lstrip("- []C0123456789 ").strip()

            # 沒有 CLAIMS 段， fallback
            return ""

        @staticmethod
        def _generate_snippet(
            text: str,
            query: str,
            max_length: int = 150,
            highlight: bool = False,
            highlight_tag: str = "em",
            escape_html: bool = True,
        ) -> str:
            """
            根據查詢詞生成文本片段，優先顯示包含查詢詞的上下文。

            Args:
                text: 原始文本
                query: 查詢詞（支持多詞）
                max_length: 片段最大長度
                highlight: 是否高亮匹配的關鍵詞
                highlight_tag: 高亮使用的 HTML 標籤名（僅限字母數字）
                escape_html: 是否對文本內容進行 HTML 實體轉義（預設 True，防止 XSS）

            Returns:
                包含查詢詞上下文的片段，未找到則返回文本開頭
            """
            import html
            import re

            if not text or not query:
                if text and escape_html:
                    return html.escape(text[:max_length]).strip()
                return text[:max_length].strip() if text else ""

            # 安全驗證：highlight_tag 白名單機制，防止標籤注入
            # 只允許安全的內聯文本標籤
            ALLOWED_TAGS = {"em", "strong", "mark", "span", "b", "i", "u", "s", "code", "kbd", "var"}
            if not isinstance(highlight_tag, str) or highlight_tag.lower() not in ALLOWED_TAGS:
                highlight_tag = "em"
            else:
                highlight_tag = highlight_tag.lower()

            # 提取查詢詞（取前 5 個最長的詞進行匹配）
            query_terms = [t.strip().lower() for t in re.split(r'\s+', query) if t.strip()]
            if not query_terms:
                if escape_html:
                    return html.escape(text[:max_length]).strip()
                return text[:max_length].strip()

            # 按詞長度排序，優先匹配長詞
            query_terms_sorted = sorted(query_terms, key=len, reverse=True)[:5]

            text_lower = text.lower()
            best_pos = -1
            best_score = 0

            # 找到最佳匹配位置（匹配詞越多、詞越長，分數越高）
            for term in query_terms_sorted:
                if not term or len(term) < 2:
                    continue
                pos = 0
                while True:
                    idx = text_lower.find(term, pos)
                    if idx == -1:
                        break
                    # 計算該位置的分數：匹配詞長度 + 附近其他匹配詞數量
                    score = len(term)
                    # 檢查附近是否有其他匹配詞（窗口 100 字符）
                    window_start = max(0, idx - 50)
                    window_end = min(len(text_lower), idx + len(term) + 50)
                    window = text_lower[window_start:window_end]
                    for other_term in query_terms_sorted:
                        if other_term != term and len(other_term) >= 2 and other_term in window:
                            score += len(other_term) * 0.5

                    if score > best_score:
                        best_score = score
                        best_pos = idx

                    pos = idx + 1

            if best_pos == -1:
                # 沒有找到匹配，返回開頭
                snippet = text[:max_length].strip()
            else:
                # 以最佳位置為中心，提取上下文
                half_len = max_length // 2
                start = max(0, best_pos - half_len)
                end = min(len(text), start + max_length)
                # 調整 start 確保長度足夠
                if end - start < max_length:
                    start = max(0, end - max_length)

                snippet = text[start:end]

                # 添加省略號標記
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."

            # HTML 實體轉義（防止 XSS）
            if escape_html:
                snippet = html.escape(snippet)
                # 查詢詞也需要轉義，因為轉義後的文本中查詢詞可能被改變（如 < 變成 &lt;）
                # 我們需要用轉義後的查詢詞來匹配
                escaped_terms = [html.escape(t) for t in query_terms_sorted]
            else:
                escaped_terms = query_terms_sorted

            # 關鍵詞高亮：合併為單次正則替換，避免多次遍歷（ReDoS 優化）
            if highlight and best_pos >= 0:
                # 過濾有效詞並構建合併正則
                valid_terms = [t for t in escaped_terms if len(t) >= 2]
                if valid_terms:
                    # 按詞長降序排列，確保長詞優先匹配（避免短詞吞併長詞的部分）
                    valid_terms.sort(key=len, reverse=True)
                    combined_pattern = '|'.join(re.escape(t) for t in valid_terms)
                    pattern = re.compile(combined_pattern, re.IGNORECASE)
                    snippet = pattern.sub(f'<{highlight_tag}>\\g<0></{highlight_tag}>', snippet)

            return snippet.strip()
