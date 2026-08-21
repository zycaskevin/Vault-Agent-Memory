# Reproduction

## Expected

The provider, Gateway, OpenAPI, and VAM-002 change envelope publish one
canonical Memory Object contract and accept additive kind/confidence aliases.

## Actual

The VAM-002 dependency branch has no Memory Object provider operations, create
alias metadata, or published Memory Layer contract. The focused suite reports
three deterministic failures.

## Deterministic steps

Run:

```text
env PYTHONPATH=. /home/zycas/文件/ChatGPT/Vault/.venv/bin/pytest -q tests/test_memory_object_contract.py
```

The shareable RED artifact records missing provider operations and response
contract keys.

## Environment and preconditions

- Branch: `codex/vam-005-memory-object-contract`
- Dependency commit: `48cea2cb60c1d90dc6e4eeef92e2d1f604623cb7`
- Python: repository development virtual environment, Python 3.11
- Isolated stacked worktree; original dirty VLT-001 worktree remains untouched
