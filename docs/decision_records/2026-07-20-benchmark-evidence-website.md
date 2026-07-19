# Benchmark evidence website and claim boundary

Date: 2026-07-20

## Decision

Vault's website positions the product as a memory governance foundation that can work standalone or augment another retrieval engine. Comparisons use paired `A` versus `A + Vault` tracks, not a generic speed leaderboard.

The GitHub Pages site has routes for the product story, architecture, results, methodology, and raw versioned evidence. Headline values are generated from checksummed publication bundles by `scripts/build_benchmark_site_data.py`. A failed checksum or unpublished track fails the build instead of displaying a number.

## Evidence policy

- Label synthetic retrieval-only evidence as synthetic retrieval-only evidence.
- Do not present it as end-to-end QA or an official LoCoMo/LongMemEval score.
- Report latency only as a within-track paired delta.
- Render missing systems as `Diagnostic` or `Unmeasured`, never zero.
- Link every published track to its raw summary and methodology.

## Consequences

GitHub Pages publishes `site/` plus an allowlisted benchmark bundle. A new integration needs a reproducible adapter run, five clean-state repeats under the current protocol, publication gates, checksums, and a versioned artifact bundle before becoming `Published`.
