# Memory Foundation Architecture Review

Date: 2026-07-09
Scope: Vault v0.9.0 memory foundation positioning, deployment modes, self-host
central host, Supabase adapter, Remote Semantic Search disclosure, and snapshot
migration safety.

## Result

Architecture score: **93/100** after the memory foundation plan.

Vault is correctly positioned as a local-first, backend-agnostic memory
governance layer. The core product semantics are the Vault Governance Contract:
approved reads, candidate submissions, review, promotion, audit, and daily
reports. Local SQLite, Self-host Central Memory Host, Supabase, and future
Vault Cloud are backend/deployment options around that contract.

## Release Blockers

No release blockers were found under the strict blocker definition.

The current reviewed surface does not show evidence of:

- installation failure;
- data destruction in the core local path;
- remote agents directly writing active memory;
- service-role keys being required in hosted agents;
- Remote Semantic Search being enabled by default;
- Supabase or self-host being documented as an active multi-master memory
  database.

## Known Limitations

- Remote Semantic Search is disabled by default, but when enabled the default
  query embedding provider is OpenAI unless the operator configures a local or
  trusted provider. Query text is provider-visible.
- Snapshot bundle import is candidate-first only. It can bootstrap review on a
  new backend, but it is not a full active-memory restore protocol.
- The self-host central host requires operator discipline: VPN/private network,
  token management, backups, daily-loop reports, and security doctor checks.
- Supabase is an optional cloud adapter and reviewed read copy plus candidate
  inbox. It is not a local source-of-truth replacement or active multi-master
  memory database.
- LoCoMo / LongMemEval language must remain retrieval-only evidence recall
  unless comparable final-answer QA runs are completed.

## Future Improvements

- Full audit-history import and active-restore disaster recovery tests.
- Operator dashboard for self-host health, candidate queue, backup age, and
  sync freshness.
- Packaged local embedding provider presets for privacy-sensitive teams.
- Stronger token rotation and per-agent key management for self-hosted fleets.
- Managed Vault Cloud backend for teams that do not want to operate memory
  infrastructure.

## Score Rationale

- `-3`: Remote Semantic Search still requires explicit operator understanding
  of provider-visible query text, even with improved documentation and health
  warnings.
- `-2`: Snapshot migration is safe and candidate-first, but full active restore
  and audit-history import remain future work.
- `-1`: Self-host deployment is operationally strong but still depends on
  external network hygiene such as VPN, HTTPS, and token rotation.
- `-1`: Vault Cloud is intentionally future-positioned, so hosted-backend
  operational guarantees are not yet implemented.

The remaining risks are known limitations and roadmap items, not release
blockers for the v0.9.0 Public Beta / Developer Preview positioning.
