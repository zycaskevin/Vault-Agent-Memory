#!/usr/bin/env python3
"""Build public site data from a checksummed benchmark bundle."""
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "benchmarks/results/vaultgovbench-retrieval-v0.1/89b9156"

def read(path): return json.loads(path.read_text(encoding="utf-8"))
def mean(data, group, name):
    item = data.get(group, {}).get(name, {})
    return item.get("mean") if item.get("available") is True else None

def build(bundle):
    for line in (bundle / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if hashlib.sha256((bundle / name.lstrip("*")).read_bytes()).hexdigest() != digest:
            raise ValueError(f"checksum mismatch: {name}")
    index = read(bundle / "artifact-index.json")
    tracks = {x["system"]: x for x in index["tracks"]}
    if not all(x.get("publishable") is True for x in tracks.values()):
        raise ValueError("headline data is not publishable")
    mem0, vault = read(bundle / tracks["mem0"]["summary"]), read(bundle / tracks["vault"]["summary"])
    return {"schema_version": 1, "generated_from": f"{index['benchmark']}/{bundle.name}",
      "evidence_revision": index["evidence_source_revision"], "claim_boundary": index["claim_boundary"],
      "protocol": {"cases": index["cases_per_repeat"], "top_k": index["top_k"], "candidate_pool_k": index["candidate_pool_k"], "repeats": 5, "repeat_policy": index["repeat_policy"]},
      "headline": {"system": "mem0", "system_version": tracks["mem0"]["system_version"],
        "baseline_recall": mean(mem0,"baseline","valid_recall"), "augmented_recall": mean(mem0,"augmented","valid_recall"),
        "baseline_forbidden_exposure": mean(mem0,"baseline","forbidden_exposure_case_rate"), "augmented_forbidden_exposure": mean(mem0,"augmented","forbidden_exposure_case_rate"),
        "paired_mean_overhead_ms": mean(mem0,"delta","latency_mean_ms"), "paired_p95_delta_ms": mean(mem0,"delta","latency_p95_ms")},
      "tracks": [{"name":"mem0 + Vault","status":"published","evidence":"mem0-guard-summary.json"},
        {"name":"Vault standalone","status":"published","evidence":"vault-guard-summary.json","baseline_recall":mean(vault,"baseline","valid_recall"),"augmented_recall":mean(vault,"augmented","valid_recall")},
        {"name":"AgentMemory + Vault","status":"diagnostic","evidence":None},
        {"name":"Letta / MemGPT + Vault","status":"unmeasured","evidence":None}]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--bundle",type=Path,default=BUNDLE); p.add_argument("--output",type=Path,default=ROOT/"site/data/benchmark-catalog.v1.json"); a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(build(a.bundle.resolve()),indent=2,sort_keys=True)+"\n",encoding="utf-8")
if __name__ == "__main__": main()
