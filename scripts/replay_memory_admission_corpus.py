"""Run a read-only semantic admission replay over a JSON corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from vault.memory import quality_gate


DEFAULT_CORPUS = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "memory_admission"
    / "hermes-semantic-corpus.json"
)


def replay(corpus_path: Path) -> dict:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    cases = corpus.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("corpus cases must be a non-empty list")
    results = []
    for case in cases:
        gate = quality_gate(case)
        finding_types = {finding["type"] for finding in gate["findings"]}
        expected_finding = case.get("expected_finding")
        passed = gate["status"] == case.get("expected_status") and (
            expected_finding is None or expected_finding in finding_types
        )
        results.append(
            {
                "id": case.get("id"),
                "passed": passed,
                "status": gate["status"],
                "findings": sorted(finding_types),
            }
        )
    return {
        "contract": corpus.get("contract", ""),
        "case_count": len(results),
        "passed_count": sum(1 for result in results if result["passed"]),
        "failed_count": sum(1 for result in results if not result["passed"]),
        "write_authority": False,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    args = parser.parse_args()
    report = replay(args.corpus)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
