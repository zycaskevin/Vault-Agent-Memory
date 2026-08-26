# Reproduction

## Expected

No line in
`DEP-VAM-002-INDEPENDENT-REVIEW-REMEDIATION/rollback.md` begins with `#500`,
and the normalized text contains the plain-prose phrase `PR #500 procedure`.

## Actual

At exact audit head `077fc5355703e4ba10fe61d7556c6c8368a8830c`,
line 13 began with `#500`, so Markdown interpreted the issue number as a
malformed heading and CodeRabbit kept thread `discussion_r3836142902` open.

## Deterministic steps

Read the rollback as UTF-8, enumerate lines for `line.startswith("#500")`, and
fail when the resulting list is non-empty. The RED probe returned
`bad_lines=[13]` and exit `1`.

## Environment and preconditions

- base: `c284e1c7bedf288a10009b98e5f2da525c3ee4bc`
- audit head: `077fc5355703e4ba10fe61d7556c6c8368a8830c`
- branch: `codex/vam-002-memory-change-envelope-ready`
- public repository text only; no live Vault, Hermes, or production data
