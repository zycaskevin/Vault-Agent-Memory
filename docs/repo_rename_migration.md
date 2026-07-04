# Repository Rename Migration Checklist

Target repository slug: `Vault-Agent-Memory`

Current repository slug: `Vault-Agent-Memory`

Previous repository slug: `Vault-for-LLM`

Status: repository rename executed on 2026-07-04.

Product display name: **Vault Agent Memory**

Package and runtime identifiers that must stay stable:

- `vault-for-llm` for PyPI and dependency pins
- `vault` for the CLI
- `vault-mcp` for the MCP stdio server
- existing local vault databases and generated project directories

## Before Rename

- Confirm the display-name PR is merged and CI is green.
- Confirm no release or publish workflow is running.
- Confirm GitHub owner permissions for `zycaskevin/Vault-Agent-Memory`.
- Confirm PyPI Trusted Publisher settings can be updated to the new repo slug.
- Confirm GitHub Pages behavior for the renamed repository.
- Leave current raw installer URLs unchanged until after the GitHub repo rename.

## Rename Command

Completed command:

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
uv run --extra dev python scripts/install_smoke_matrix.py --mode source
uv run --extra dev python scripts/readme_command_smoke.py
uv run --extra dev python scripts/check_release_parity.py
uv run --extra dev pytest -q
```

Windows PowerShell installer smoke runs in GitHub Actions because local
developer machines may not have `pwsh`.

## Post-Rename Verification On 2026-07-04

- `gh repo view zycaskevin/Vault-Agent-Memory` returned the renamed public
  repository with default branch `main`.
- `https://github.com/zycaskevin/Vault-for-LLM` redirected to
  `https://github.com/zycaskevin/Vault-Agent-Memory`.
- New canonical raw installer URLs for `scripts/install.sh` and
  `scripts/install.ps1` returned HTTP 200.
- The old raw `scripts/install.sh` URL still returned HTTP 200.
- `gh release view v0.7.29 -R zycaskevin/Vault-Agent-Memory` succeeded.
- GitHub Pages API reported
  `https://zycaskevin.github.io/Vault-Agent-Memory/`.
- Local checks passed:
  `git diff --check`, `scripts/check_release_parity.py`,
  `scripts/readme_command_smoke.py`, and
  `scripts/install_smoke_matrix.py --mode source`.
- Local PowerShell smoke was not run because `pwsh` was unavailable.

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
