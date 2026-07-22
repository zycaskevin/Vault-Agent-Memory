# Founding 10 independent reproduction challenge

Date: 2026-07-22

## Decision

Vault will begin external validation with a small, outcome-neutral cohort rather
than a vendor leaderboard. The Founding 10 accepts at most ten independently
operated entries. Each accepted operator receives a 14-day window confirmed in
their public registration issue.

The three tracks are:

1. **Reproduce** the frozen mem0 contract without protocol changes.
2. **Break It** by identifying reproducibility, isolation, documentation,
   fairness, or claim-boundary failures.
3. **Bring Your Memory** by comparing the same engine as A and A + Vault while
   holding the model, corpus, queries, candidate pool, and environment constant
   where possible.

## Evidence policy

Positive, negative, environment-blocked, and protocol-issue outcomes are all
publishable. Missing results must remain missing rather than becoming zero.
Registration, contract validation, maintainer review, and endorsement remain
separate states. The first cohort promises public attribution and contributor
recognition only; it does not promise cash rewards.

The shared scorecard includes valid recall, forbidden exposure, expiry leakage,
citation correctness, repeat stability, latency, and resource cost. This keeps
the evaluation aligned with Vault's memory-foundation claim instead of reducing
it to retrieval recall alone.

## Public surfaces

- Challenge overview: `site/challenge/` and `site/en/challenge/`
- Registration: `.github/ISSUE_TEMPLATE/challenge_registration.yml`
- Completed bundle: `.github/ISSUE_TEMPLATE/external_reproduction.yml`
- Blocked attempt: `.github/ISSUE_TEMPLATE/external_reproduction_blocked.yml`

Maintainers confirm cohort acceptance and the 14-day start date in the public
registration issue. A registration form submission alone is not an acceptance.
