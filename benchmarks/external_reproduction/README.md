# External Reproduction Kit

This kit lets an independent operator rerun the pinned `mem0 2.0.12` versus
`mem0 + Vault guard` experiment without receiving evaluation gold labels in the
provider process. It is the first supported external-reproduction track; other
providers remain outside the v1 submission contract.

## 1. Fork and create an isolated environment

Use a clean checkout of a tagged or committed Vault revision. Create a new
Python virtual environment, install this repository and the pinned provider
requirements, and keep the worktree clean:

```bash
python -m venv .repro-venv
.repro-venv/bin/python -m pip install -e .
.repro-venv/bin/python -m pip install \
  -r benchmarks/provider_requirements/mem0-2.0.12.txt
```

The model prewarm downloads the pinned FastEmbed assets. No provider API key is
required. Expect the complete five-repeat run to take time and several GB of
model/cache space. Put the output outside the repository so generated files do
not make the source worktree dirty.

## 2. Run the frozen protocol

```bash
.repro-venv/bin/python scripts/run_external_reproduction.py \
  --output-dir /tmp/vault-external-reproduction \
  --github-handle YOUR_GITHUB_HANDLE \
  --affiliation independent \
  --accept-public-attestation
```

The runner exports blinded provider input, prewarms the fixed embedding assets,
creates five distinct stores, runs native mem0 retrieval, applies the Vault
guard to the same candidates, scores both arms, checks publication gates,
records the environment, and writes exhaustive SHA-256 checksums.

## 3. Validate before submitting

```bash
.repro-venv/bin/python scripts/validate_external_reproduction.py \
  /tmp/vault-external-reproduction --json
```

A passing contract validates artifact integrity, isolation declarations,
source identity, the frozen protocol, and a publishable repeat summary. It does
not mean maintainers endorse the operator or that this synthetic retrieval
fixture proves production-scale or end-to-end answer quality.

## 4. Submit for public review

Open an **External reproduction submission** issue first. Link a public fork or
release containing the complete bundle; do not paste large artifacts into the
issue. Maintainers verify checksums and CI, inspect conflicts and environment
evidence, then classify the result as `Submitted`, `Contract validated`,
`Maintainer reviewed`, or `Rejected`. Only reviewed evidence may appear on the
public website, and the original artifact remains attributable to its operator.

Never include tokens, API keys, private memory, customer data, local absolute
paths, or unrelated environment secrets.
