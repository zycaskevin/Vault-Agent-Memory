# External Reproduction Kit

This kit lets an independent operator rerun the pinned `mem0 2.0.12` versus
`mem0 + Vault guard` experiment without receiving evaluation gold labels in the
provider process. It is the first supported external-reproduction track; other
providers remain outside the v1 submission contract.

## 1. Fork and create an isolated environment

Use a clean checkout of a tagged or committed Vault revision. Create the
virtual environment **outside the repository**, install this repository and
the pinned provider requirements, and keep the worktree clean. The runner
intentionally rejects tracked and untracked source changes:

```bash
python3.13 -m venv ../vault-repro-venv
../vault-repro-venv/bin/python -m pip install -e .
../vault-repro-venv/bin/python -m pip install \
  -r benchmarks/provider_requirements/mem0-2.0.12.txt
```

Use Python `>=3.10,<3.14`. The pinned spaCy environment does not install on
Python 3.14. Confirm the selected interpreter before creating the environment.

Do not substitute `.repro-venv` inside the checkout: an untracked environment
correctly makes the source identity dirty. The model prewarm needs outbound
HTTPS access to `huggingface.co` and downloads the pinned FastEmbed assets
(`qdrant/gte-large-onnx` and the Qdrant BM25 sparse model). No provider API key
is required. Expect the complete five-repeat run to take time and several GB of
model/cache space. Put the output outside the repository too, so generated
files do not change the source identity.

## 2. Run the machine-readable preflight

Check source identity, environment isolation, pinned dependencies, disk, memory,
model cache, and Hugging Face access before spending time on five repeats:

```bash
../vault-repro-venv/bin/python scripts/run_external_reproduction.py \
  --output-dir /tmp/vault-external-reproduction \
  --model-cache-dir ../vault-repro-model-cache \
  --preflight-only --json
```

Exit `0` with status `pass` means the environment is ready. Exit `2` with
status `environment_blocked` names every blocking check. A cold model cache is
only a warning when Hugging Face is reachable; an unreachable model host blocks
the run unless both pinned cache entries already exist. A preflight pass is
environment readiness only—not a benchmark result, external reproduction, or
provider security audit.

## 3. Run the frozen protocol

```bash
../vault-repro-venv/bin/python scripts/run_external_reproduction.py \
  --output-dir /tmp/vault-external-reproduction \
  --model-cache-dir ../vault-repro-model-cache \
  --github-handle YOUR_GITHUB_HANDLE \
  --affiliation independent \
  --accept-public-attestation
```

The runner exports blinded provider input, prewarms the fixed embedding assets,
creates five distinct stores, runs native mem0 retrieval, applies the Vault
guard to the same candidates, scores both arms, checks publication gates,
records the environment, and writes exhaustive SHA-256 checksums.

The model layer is frozen independently of the Python lock: the runner fetches
the exact `qdrant/gte-large-onnx` and `Qdrant/bm25` Hub commit SHAs, verifies
their complete snapshot tree SHA-256 values, then sets `HF_HUB_OFFLINE=1` for
all five repeats. A moved `main` branch, partial cache, altered file, or wrong
snapshot therefore fails before any publishable result is produced. The exact
revisions and observed tree digests are included in `submission.json`.

## 4. Validate before submitting

```bash
../vault-repro-venv/bin/python scripts/validate_external_reproduction.py \
  /tmp/vault-external-reproduction --json
```

A passing contract validates artifact integrity, isolation declarations,
source identity, the frozen protocol, and a publishable repeat summary. It does
not mean maintainers endorse the operator or that this synthetic retrieval
fixture proves production-scale or end-to-end answer quality.

If package installation or blinded-input export succeeds but model download,
provider startup, storage, memory, or another environment prerequisite prevents
all five repeats from completing, report the attempt as `Environment blocked`.
That status is useful diagnostic evidence, but it is not `Submitted`,
`Contract validated`, or an accepted external reproduction. Include the exact
stage, redacted error, OS/Python details, source revision, and network/runtime
constraint in the blocked-attempt issue form.

## 5. Submit for public review

Open an **External reproduction submission** issue first. Link a public fork or
release containing the complete bundle; do not paste large artifacts into the
issue. Maintainers verify checksums and CI, inspect conflicts and environment
evidence, then classify the result as `Submitted`, `Contract validated`,
`Maintainer reviewed`, or `Rejected`. Only reviewed evidence may appear on the
public website, and the original artifact remains attributable to its operator.

Never include tokens, API keys, private memory, customer data, local absolute
paths, or unrelated environment secrets.
