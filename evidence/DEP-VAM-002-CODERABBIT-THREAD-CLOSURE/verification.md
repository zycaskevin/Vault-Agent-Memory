# Verification

## Green command and result

The focused rollback selection passed 2 tests at exact implementation commit
`8847f94a58acc81a5e1b18357a6cbf50d00a35a7`. The direct Markdown line scan,
Ruff 0.16.4, and `git diff --check` all passed. Exact committed-head Local Green
remains pending.

## Before/after evidence

RED is captured in
`shareable/artifacts/terminal--coderabbit-thread-red.txt`; Green evidence will
is captured in `shareable/artifacts/terminal--coderabbit-thread-green.txt`.

## Remaining limitations

No current-head CodeRabbit substantive review exists because its integration
is paused. Exact committed-head Local Green, strict proof, gate rebind,
independent Reviewer receipt, merge, and deployment remain separate gates.
