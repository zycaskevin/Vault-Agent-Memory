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
    module = builder(); data = module.build(module.BUNDLE)
    assert data["headline"]["baseline_recall"] == 0.666667
    assert data["headline"]["augmented_recall"] == 1.0
    assert data["headline"]["augmented_forbidden_exposure"] == 0.0
    assert [x["status"] for x in data["tracks"]] == ["published", "published", "diagnostic", "unmeasured"]
    assert data["tracks"][2]["evidence"] is None

def test_claim_and_accessibility_contract():
    pages = list((ROOT / "site").glob("**/*.html")); assert len(pages) >= 4
    text = "\n".join(p.read_text(encoding="utf-8") for p in pages)
    assert "retrieval-only" in text and "LoCoMo / LongMemEval" in text
    assert "N/A — 不當成零分" in text
    assert "prefers-reduced-motion" in (ROOT / "site/assets/site.css").read_text()
    assert all('name="viewport"' in p.read_text() for p in pages)

def test_generated_catalog_is_deterministic():
    module = builder(); expected = json.dumps(module.build(module.BUNDLE), indent=2, sort_keys=True) + "\n"
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
    assert "Keep the memory engine you like" in text
    assert "Compare A with A + Vault" in text
    assert "Fix the question first" in text
    assert "架構" not in text and "測試結果" not in text and "測試方法" not in text

if __name__ == "__main__":
    test_data_is_checksummed_and_fail_closed()
    test_claim_and_accessibility_contract()
    test_generated_catalog_is_deterministic()
    test_english_site_is_complete_and_has_stable_routes()
    print("benchmark site contract: PASS")
