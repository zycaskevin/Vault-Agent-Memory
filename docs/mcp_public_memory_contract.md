# Public MCP Memory Contract

This document fixes the public contract slice used to find, read, propose, and
review memory. It describes MCP tool schemas and their current dispatch output;
it does not define or emit Subject Distillation artifacts.

MCP clients discover each advertised `inputSchema` through `tools/list` and
should validate inputs against it. The runtime also validates search modes, so
direct dispatcher and stdio callers receive `failure_mode:
"unsupported_search_mode"`, the stable `supported_modes` list, and a safe
retry action using `auto`.
`basic` remains a supported compatibility alias for `auto`; it does not select
a distinct retrieval implementation.

All successful tool calls except search return an MCP object whose `result`
field contains JSON text. Search success uses the same `result` JSON envelope;
the decoded value is an array. When `fields` is supplied, each search record
contains only allowed requested fields. No search item key is universally
guaranteed, and an empty field list may yield `{}` records. Tool-execution
failures use the stable outer fields `error`, `failure_mode`, and `next_action`.
Across stdio, failures are standard MCP tool results with `isError: true`.
Typed unsupported-search failures put the complete JSON envelope in
`content[0].text`; generic failures preserve the legacy error text there.

The JSON block below is machine-checked against the live schemas and profile
selection. Each hash covers the complete canonical `inputSchema`, including
descriptions and recursively nested values. Ordered `properties` arrays exactly
match live schema declaration order. Output `keys` describe the minimal stable
decoded envelope; individual records may include extra metadata.

<!-- contract-json-start -->
```json
{
  "vault_search": {
    "schema_sha256": "c4ecfc06eedd20e50fb2a26d4792dc450747d4c5decc3551c3d3371683268a67",
    "properties": ["query", "mode", "limit", "offset", "normalize_scores", "include_snippet", "fields", "compact", "agent_id", "include_private", "max_sensitivity", "include_expired_temporal", "include_future_temporal", "temporal_as_of"],
    "required": ["query"],
    "supported_modes": ["auto", "basic", "keyword", "vector", "semantic", "hybrid"],
    "profiles": ["core", "review", "remote", "maintenance", "full"],
    "output": {"envelope": "search_result_json", "projection_dependent": true, "keys": []}
  },
  "vault_read_range": {
    "schema_sha256": "279dc9bd7204923f50ee5a8973ad701003eff2eb7d2061abe7694782101d2824",
    "properties": ["knowledge_id", "node_uid", "line_start", "line_end", "agent_id", "include_private", "max_sensitivity"],
    "required": ["knowledge_id"],
    "profiles": ["core", "review", "remote", "maintenance", "full"],
    "output": {"envelope": "result_json", "keys": ["entry_id", "content", "citation"]}
  },
  "vault_memory_propose": {
    "schema_sha256": "48326f3fb64e532be0635517ff81184bcec825d5bc8b80581111bea4010da7f3",
    "properties": ["title", "content", "source", "source_ref", "layer", "category", "tags", "trust", "scope", "sensitivity", "owner_agent", "allowed_agents", "memory_type", "expires_at", "agent_id", "allow_shared", "allow_private", "allow_high_sensitivity", "allow_restricted", "reason", "mode"],
    "required": ["title", "content", "reason"],
    "profiles": ["core", "review", "remote", "maintenance", "full"],
    "output": {"envelope": "result_json", "keys": ["status", "candidate_id", "gates"]}
  },
  "vault_memory_candidates": {
    "schema_sha256": "c4bc14b088f08852427f81c70652c466d4869eb3ab5c7859fd3cb8beba2031bd",
    "properties": ["status", "all", "limit", "include_content", "include_gates", "agent_id", "include_private", "max_sensitivity"],
    "required": [],
    "profiles": ["review", "maintenance", "full"],
    "output": {"envelope": "result_json", "keys": ["count", "status", "candidates"]}
  },
  "vault_memory_promote": {
    "schema_sha256": "cf44650f4bd6b5779d14b8039482b271faacb5faf8c67c1125259860f2f68f24",
    "properties": ["candidate_id", "confirm", "compile", "build_map", "agent_id", "allow_shared", "allow_private", "allow_high_sensitivity", "allow_restricted"],
    "required": ["candidate_id", "confirm"],
    "profiles": ["review", "maintenance", "full"],
    "output": {"envelope": "result_json", "keys": ["status", "candidate_id"]}
  },
  "vault_memory_review": {
    "schema_sha256": "71840a34e1645c5a204043dde577030d387da38bcc7f46c70f698d405cea31d7",
    "properties": ["candidate_id", "outcome", "reason", "score"],
    "required": ["candidate_id", "outcome", "reason"],
    "profiles": ["review", "maintenance", "full"],
    "output": {"envelope": "result_json", "keys": ["status", "candidate_id", "score"]}
  }
}
```
<!-- contract-json-end -->

## Inputs and compatibility

- `vault_search.mode`: `auto` (default), `basic`, `keyword`, `vector`,
  `semantic`, or `hybrid`. `basic` is the backwards-compatible alias for
  `auto`. `limit` is 1–50 (default 10), `offset` is 0–1000 (default 0), and
  `query` is required with a maximum length of 1000 characters.
- `vault_read_range` requires `knowledge_id`. Its default sensitivity ceiling
  is `medium`.
- `vault_memory_propose` requires `title`, `content`, and `reason`. Its mode is
  `candidate` by default; `promote_if_safe` is the only other public value.
- `vault_memory_candidates` has no required input. Its limit is 1–100,
  defaulting to 50.
- `vault_memory_promote` requires `candidate_id` and explicit `confirm`.
- `vault_memory_review` requires `candidate_id`, `reason`, and an outcome of
  `rejected` or `blocked`.

## Synthetic examples

Search request:

```json
{"query": "release checklist", "mode": "basic", "limit": 5}
```

Candidate proposal:

```json
{
  "title": "Release verification rule",
  "content": "Run a clean-environment smoke test after packaging.",
  "reason": "Keeps the verification step available to future maintainers."
}
```

Candidate review:

```json
{
  "candidate_id": "candidate-example-001",
  "outcome": "rejected",
  "reason": "The proposed rule duplicates an existing reviewed entry."
}
```
