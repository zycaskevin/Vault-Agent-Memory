# Decision Record: External Contributor Onboarding

Date: 2026-07-03

## Context

Vault-for-LLM is moving from a solo-maintained project toward a public
Agent-assisted builder audience. The repository already had development setup
instructions, but it did not give an external contributor enough confidence
about:

- what kinds of contribution are welcome;
- how issues should be reported safely;
- whether a small PR will be reviewed;
- which tasks are suitable for first-time contributors;
- how to avoid leaking private memory data in public reports.

For a memory-governance project, this matters more than usual. Contributors may
be tempted to paste real vault contents, private chats, API keys, or customer
records when reporting a bug. The repository needs a safer path before broader
promotion.

## Decision

Add a lightweight open-source contribution foundation:

- rewrite `CONTRIBUTING.md` for external Agent-assisted builders;
- add issue templates for bug reports and feature requests;
- add a pull request template with validation and safety prompts;
- add a code of conduct focused on respectful and privacy-preserving
  collaboration;
- add a good-first-issue idea list that points newcomers toward bounded docs,
  tests, examples, and CLI consistency work.

This is intentionally not a full community program. The project should not
pretend to have a large contributor base yet. The goal is to make the first
outside report or PR easier to write and easier to review.

## Public Boundary

Use honest language:

- Vault is maintained primarily by one maintainer with heavy Agent assistance.
- Reviews are not instant, but small issues and PRs should receive a response
  target.
- Large schema, security, Gateway, sync, or automation-policy changes should
  start as an issue before implementation.
- External contributors should never include real secrets, private chats,
  customer records, medical data, or production vault exports.

## Consequences

- The next public article or demo can link to a real contribution path instead
  of saying "PRs welcome" without structure.
- Good first issues should be created from real bounded tasks, not vague
  wishlist items.
- Future contribution docs should stay practical and short; detailed maintainer
  release process belongs in release docs, not the first contributor path.
