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

## Institutional presentation standard

The site must explain the category before asking visitors to inspect implementation details: memory engines retrieve; Vault supplies the trust decision between retrieval and action. The primary audience order is technical evaluator, platform buyer or partner, then investor. Visual polish may improve comprehension, but it must never make a claim stronger than its evidence.

Each language has stable product, architecture, evidence, and methodology routes. Quantitative charts show denominators and test scope near the metric. Case-level outcomes remain inspectable. Diagnostic and unmeasured integrations stay visible because hiding them would create a stronger but misleading story.

The bilingual integration route applies the same rule to provider-specific discovery. It may explain how mem0, AgentMemory, Letta / MemGPT, and custom RAG fit the augmentation contract, but every provider carries its current evidence state. Adapter existence alone is never presented as benchmark validation.

The site can support fundraising and distribution, but it cannot claim traction, market demand, third-party validation, or investment interest until those facts have their own verifiable sources. Those are business-evidence tracks, not design copy.

## Independent artifact verification

The repository provides `scripts/verify_publication_bundle.py` so a skeptical
reader can validate the frozen bundle locally with one command. The verifier
checks exhaustive checksum coverage, content digests, path safety, the index
contract, summary identity, repeat counts, and fail-closed publication state.

This creates a self-service integrity proof, not third-party reproduction.
Only a separately operated provider run with its own environment evidence can
satisfy the independent-reproduction roadmap item. The site and fundraising
materials must preserve that distinction.
