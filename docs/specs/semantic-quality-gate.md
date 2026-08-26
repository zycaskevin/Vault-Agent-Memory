# Semantic Quality Gate

Vault evaluates a proposed Memory Object as memory content. It does not infer
personality, identity, relationships, life phases, or a human model.

`quality_gate()` keeps the legacy `status` and `findings` keys and adds:

- `disposition`
- `policy`
- `semantic_completeness`
- `authorship_state`
- `decision_state`
- `context_dependency`
- `future_utility`
- `title_quality`

The policy emits typed findings for question-only content, meta instructions,
dangling punctuation, deictic text without an anchor, and opaque hash-like
titles. Provenance `reason` text is not a semantic quality signal. The word
`問題` in a question is not a positive quality signal.

A short rule may pass when it is a complete, tagged statement with an explicit
rule signal such as `must`, `不得`, `最多`, or `上限`. Length alone does not
make a candidate useful or useless.

The additive semantic fields are persisted inside the existing candidate gate payload,
so existing candidate rows and callers remain readable without a schema rewrite.
Promotion Contract v2 and authenticated reviewed overrides are separate work;
this slice does not treat a caller-supplied identity as review authority.
