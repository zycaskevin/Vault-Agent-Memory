# Subject Distillation

Subject Distillation is a proposed pipeline for turning evidence about a subject
into durable, reviewable memory. Its public outputs must not accidentally carry
credentials, machine-local paths, private evidence, or other material that is
unsafe to publish.

## Safety model

Public artifacts should pass through a deterministic, fail-closed scanner in the
planned pipeline before they can be emitted. This Phase 0 slice provides a
standalone validator; it is not yet wired into artifact emission. The scanner
checks JSON-like dictionaries and lists, rejects non-string dictionary keys, and
blocks forbidden field names and secret-, credential-, or local-path-shaped
strings. Failures use a fixed message that never includes the rejected value.
The scanner is a defense-in-depth boundary, not a replacement for evidence
governance or human review.

## Phased architecture

The planned flow is:

1. **Evidence:** collect bounded source material without treating it as memory.
2. **Normalized claims:** extract explicit, comparable statements from evidence.
3. **Temporal and provenance context:** attach when a claim applied and where it
   came from so conflicts and staleness remain visible.
4. **Governed promotion:** propose reviewed claims for promotion under the
   repository's candidate-first memory policy.

This first pull-request slice is only the Phase 0 public-safety foundation for
[Issue #410](https://github.com/zycaskevin/Vault-Agent-Memory/issues/410). It is
independently useful for validating future JSON-like intermediate values, but it
does not complete Subject Distillation.

## Non-goals

This phase does not process live or private data, deploy a service, promote any
claim automatically, or perform network writes.

## Validation

Run the focused contract tests with:

```bash
python -m pytest -q -p no:cacheprovider tests/test_subject_public_safety.py
```
