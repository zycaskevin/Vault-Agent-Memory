# Repository Rename Migration Checklist

Target repository slug: `Vault-Agent-Memory`

Current repository slug: `Vault-for-LLM`

Product display name: **Vault Agent Memory**

Package and runtime identifiers that must stay stable:

- `vault-for-llm` for PyPI and dependency pins
- `vault` for the CLI
- `vault-mcp` for the MCP stdio server
- existing local vault databases and generated project directories

## Before Rename

- Confirm the display-name PR is merged and CI is green.
- Confirm no release or publish workflow is running.
- Confirm GitHub owner permissions for `zycaskevin/Vault-for-LLM`.
- Confirm PyPI Trusted Publisher settings can be updated from old repo slug to
  new repo slug.
- Confirm GitHub Pages behavior for the renamed repository.
- Leave current raw installer URLs unchanged until after the GitHub repo rename.

## Rename Command

Use the GitHub UI or:

```bash
gh repo rename Vault-Agent-Memory --repo zycaskevin/Vault-for-LLM
```

Expected new repository:

```text
https://github.com/zycaskevin/Vault-Agent-Memory
```

## Update Immediately After Rename

Update current installation and repository references:

- `README.md`
- `README.zh-Hant.md`
- `README.zh-CN.md`
- `.github/ISSUE_TEMPLATE/config.yml`
- `scripts/install.sh`
- `scripts/install.ps1`
- `docs/upgrade/OPEN_SOURCE_BASELINE.md`
- `docs/release_hygiene_trusted_publishing_design.md`
- active integration docs under `docs/` and `integrations/`
- GitHub Pages and landing-page references, if any

Do not mechanically rewrite archived release notes only for the rename.

## Verify Redirects And Canonical URLs

```bash
gh repo view zycaskevin/Vault-Agent-Memory --json nameWithOwner,url,defaultBranchRef
curl -I https://github.com/zycaskevin/Vault-for-LLM
curl -I https://github.com/zycaskevin/Vault-Agent-Memory
curl -I https://raw.githubusercontent.com/zycaskevin/Vault-for-LLM/main/scripts/install.sh
curl -I https://raw.githubusercontent.com/zycaskevin/Vault-Agent-Memory/main/scripts/install.sh
curl -I https://raw.githubusercontent.com/zycaskevin/Vault-Agent-Memory/main/scripts/install.ps1
```

The old GitHub repository URL may redirect, but current docs should point to the
new canonical repository after the rename.

## Verify Installers

Run installer smoke checks against the new canonical raw URLs:

```bash
python scripts/install_smoke_matrix.py --script scripts/install.sh
python scripts/install_smoke_matrix.py --script scripts/install.ps1
python scripts/readme_command_smoke.py
python scripts/check_release_parity.py
python -m pytest -q
```

If local `python` is unavailable, use `python3` or the repository's `uv run`
workflow.

## Verify Release Infrastructure

- Update PyPI Trusted Publisher repository from `Vault-for-LLM` to
  `Vault-Agent-Memory`.
- Confirm `.github/workflows/publish.yml` still maps to the configured PyPI
  publisher.
- Confirm release links resolve from both old and new repository URLs.
- Confirm badges and GitHub Pages URLs display correctly.
- Confirm `gh release view v0.7.29` works from the renamed checkout.

## Rollback Notes

If the rename breaks release or installer paths, rename the repository back to
`Vault-for-LLM`, restore old raw URLs in current docs, and rerun installer smoke
before retrying the migration.
