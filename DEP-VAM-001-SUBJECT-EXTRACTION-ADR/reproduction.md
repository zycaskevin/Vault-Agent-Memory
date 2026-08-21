# Reproduction

## Expected

The repository contains the extraction ADR, marks Subject Distillation as a
preserved origin package, keeps the exact historical task states, and provides
bounded drafts for Issues #410, #495, #496, and #497.

## Actual

The ADR and drafts do not exist. The status page still presents Issue #410 as
the current owner without recording the owner-approved extraction decision.

## Deterministic steps

From exact `origin/main` commit
`291d5595c9cb2208a6b74206acbba35a883eb918`, run:

```bash
/home/zycas/文件/ChatGPT/Vault/.venv/bin/pytest -q tests/test_subject_extraction_boundary_docs.py
```

The three executable documentation assertions fail: two missing files and one
missing status transition.

## Environment and preconditions

Local isolated worktree on `codex/vam-001-subject-extraction-adr`; no network,
database, credentials, private fixtures, or runtime service is required.
