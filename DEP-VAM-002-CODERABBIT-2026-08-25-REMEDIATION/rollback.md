# Rollback

## Trigger

Rollback this documentation-only remediation if its new binding test creates a
false constraint or a corrected rollback command is shown inaccurate.

## Reversible steps

At exact successor commit `4456c1ceabdce4bcfd24c33fa958990984172ff9`, prepare
an uncommitted local revert of only that remediation commit. This procedure
requires a clean worktree, so it never absorbs pre-existing local changes. If
any post-revert check fails, `git revert --abort` removes only the temporary
revert state.

```bash
set -euo pipefail
rollback_commit=4456c1ceabdce4bcfd24c33fa958990984172ff9
test "$(git rev-parse HEAD)" = "$rollback_commit"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
test -x "$VAULT_TEST_PYTHON"
test -x "$RUFF"
git revert --no-commit "$rollback_commit"
if ! git diff --cached --name-only -z | python -c 'import sys; actual=set(filter(None,sys.stdin.buffer.read().decode().split("\0"))); expected=set("""DEP-VAM-002-BUILDER-LOCAL-GREEN-PATH/regression-evidence.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/fix-scope.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/manifest.json
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/redaction-report.json
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/regression-evidence.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/reproduction.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/rollback.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/root-cause-hypothesis.md
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--artifact-1.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--artifact-2.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--artifact-3.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--boundary-freeze-green.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--current-head-binding-green.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/shareable/artifacts/terminal--vam002-regression-green.txt
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/summary.yaml
DEP-VAM-002-CODERABBIT-2026-08-26-REMEDIATION/verification.md
DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/finding-dispositions.md
DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/fix-scope.md
DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/rollback.md
DEP-VAM-002-CODERABBIT-FINAL14-REMEDIATION/summary.yaml
DEP-VAM-002-CODERABBIT-REPLACEMENT-REVIEW-REMEDIATION/reproduction.md
DEP-VAM-002-FULL-SUITE-COMPATIBILITY/reproduction.md
DEP-VAM-002-FULL-SUITE-COMPATIBILITY/rollback.md
DEP-VAM-002-SEQUENTIAL-MAIN-INTEGRATION/rollback.md
tests/test_vault_boundary_freeze.py""".splitlines()); raise SystemExit(0 if actual == expected else 1)'; then
  git revert --abort
  exit 1
fi
if ! "$VAULT_TEST_PYTHON" -m pytest -q tests/test_vault_boundary_freeze.py; then
  git revert --abort
  exit 1
fi
if ! "$RUFF" check tests/test_vault_boundary_freeze.py; then
  git revert --abort
  exit 1
fi
git diff --cached --check
```

## Data compatibility

No database, stored memory, API route, or user data changes.

## Post-rollback verification

Run the pinned focused binding node, the pinned Ruff check, and `git diff
--cached --check` against the uncommitted rollback candidate.
