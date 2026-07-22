import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def builder():
    spec = importlib.util.spec_from_file_location("site_data", ROOT / "scripts/build_benchmark_site_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_data_is_checksummed_and_fail_closed():
    module = builder()
    data = module.build(module.BUNDLE)
    assert data["headline"]["baseline_recall"] == 0.666667
    assert data["headline"]["augmented_recall"] == 1.0
    assert data["headline"]["augmented_forbidden_exposure"] == 0.0
    assert [x["status"] for x in data["tracks"]] == ["published", "published", "diagnostic", "unmeasured"]
    assert data["tracks"][2]["evidence"] is None

def test_claim_and_accessibility_contract():
    pages = list((ROOT / "site").glob("**/*.html"))
    assert len(pages) >= 4
    text = "\n".join(p.read_text(encoding="utf-8") for p in pages)
    assert "retrieval-only" in text and "LoCoMo" in text and "LongMemEval" in text
    assert "Unmeasured" in text and "不做品質主張" in text
    assert "prefers-reduced-motion" in (ROOT / "site/assets/site.css").read_text()
    assert all('name="viewport"' in p.read_text() for p in pages)

def test_generated_catalog_is_deterministic():
    module = builder()
    expected = json.dumps(module.build(module.BUNDLE), indent=2, sort_keys=True) + "\n"
    assert (ROOT / "site/data/benchmark-catalog.v1.json").read_text() == expected

def test_english_site_is_complete_and_has_stable_routes():
    english_root = ROOT / "site/en"
    routes = [
        english_root / "index.html",
        english_root / "architecture/index.html",
        english_root / "benchmarks/index.html",
        english_root / "benchmarks/methodology/index.html",
    ]
    assert all(path.exists() for path in routes)
    text = "\n".join(path.read_text(encoding="utf-8") for path in routes)
    assert all('<html lang="en">' in path.read_text() for path in routes)
    assert "Memory engines retrieve. Vault decides" in text
    assert "Trust claims should be inspectable" in text
    assert "Fix the question. Blind the provider" in text
    assert "架構" not in text and "測試結果" not in text and "測試方法" not in text

def test_institutional_site_contract():
    css = (ROOT / "site/assets/site.css").read_text()
    english = (ROOT / "site/en/benchmarks/index.html").read_text()
    chinese = (ROOT / "site/benchmarks/index.html").read_text()
    assert english.count('class="bar') >= 4
    assert 'class="heatmap"' in english and 'class="heatmap"' in chinese
    assert "Stale temporal fact" in english and "Superseded revision" in english
    assert "33.3%" in english and "+0.1482" in english and "ms" in english
    assert "overflow-x:auto" in css and ":focus-visible" in css
    assert all('class="skip"' in p.read_text() and 'id="main"' in p.read_text()
               for p in (ROOT / "site").glob("**/*.html"))
    assert (ROOT / "site/robots.txt").exists()
    assert (ROOT / "site/sitemap.xml").read_text().count("<url>") == 12

def test_bilingual_independent_bundle_verification_contract():
    english = (ROOT / "site/en/benchmarks/methodology/index.html").read_text()
    chinese = (ROOT / "site/benchmarks/methodology/index.html").read_text()
    command = "python scripts/verify_publication_bundle.py"
    assert command in english and command in chinese
    assert "all 36 evidence files" in english
    assert "全部 36 個證據檔案" in chinese
    assert "not an independent provider rerun" in english
    assert "不代表第三方已獨立重跑 provider" in chinese
    assert (ROOT / "scripts/verify_publication_bundle.py").exists()

def test_bilingual_external_reproduction_program_contract():
    english = (ROOT / "site/en/reproduce/index.html").read_text()
    chinese = (ROOT / "site/reproduce/index.html").read_text()
    assert "Don’t trust the chart. Run the contract." in english
    assert "不要相信圖表。親自重跑合約。" in chinese
    assert "No third-party reproduction has been accepted yet" in english
    assert "目前尚未接受任何第三方獨立重跑" in chinese
    assert "0 accepted" in english and "0 accepted" in chinese
    assert "run_external_reproduction.py" in english and "run_external_reproduction.py" in chinese
    assert "--preflight-only --json" in english and "--preflight-only --json" in chinese
    assert "Environment readiness" in english
    assert "只代表環境符合執行條件" in chinese
    assert "snapshot-tree digests" in english
    assert "snapshot tree digest" in chinese
    assert "Contract validated" in english and "Contract validated" in chinese
    assert "Maintainer reviewed" in english and "Maintainer reviewed" in chinese
    assert "Environment blocked" in english and "Environment blocked" in chinese
    assert "external_reproduction_blocked.yml" in english
    assert "external_reproduction_blocked.yml" in chinese

def test_bilingual_integration_and_search_contract():
    english = (ROOT / "site/en/integrations/index.html").read_text()
    chinese = (ROOT / "site/integrations/index.html").read_text()
    assert "Keep the engine. Add a trust layer." in english
    assert "保留原本的引擎，加上一層信任地基。" in chinese
    for label in ("Published", "Diagnostic", "Unmeasured"):
        assert label in english and label in chinese
    pages = list((ROOT / "site").glob("**/*.html"))
    assert len(pages) == 12
    assert all('rel="canonical"' in page.read_text() for page in pages)
    assert all('hreflang="en"' in page.read_text() for page in pages)
    assert all('hreflang="zh-Hant"' in page.read_text() for page in pages)
    assert 'application/ld+json' in (ROOT / "site/en/index.html").read_text()

def test_social_preview_dimensions():
    import struct
    payload = (ROOT / "site/assets/og.png").read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", payload[16:24]) == (1200, 630)

if __name__ == "__main__":
    test_data_is_checksummed_and_fail_closed()
    test_claim_and_accessibility_contract()
    test_generated_catalog_is_deterministic()
    test_english_site_is_complete_and_has_stable_routes()
    print("benchmark site contract: PASS")
