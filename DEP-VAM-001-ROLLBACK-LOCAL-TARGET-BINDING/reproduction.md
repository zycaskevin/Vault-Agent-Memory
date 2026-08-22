# Reproduction

## Expected

After resolving PR #498's merge commit, the rollback must refuse unless the
local checkout is branch `main` at that exact commit.

## Actual

At reviewed head `92bd0d28f36b9da401c57d08cd7ebd57d972c36e`, the command could reach
`git revert --no-commit ec107d1` from the PR branch or another descendant.

## Deterministic steps

Read the `command:` field in `DEP-VAM-001-DELIVERY-GATE/rollback.md`; observe
that remote state, merge shape, and ancestry are checked, but no local branch or
HEAD equality appears before the approval-consuming autonomy command.

## Environment and preconditions

Exact PR base `291d5595c9cb2208a6b74206acbba35a883eb918`, reviewed remote head
`92bd0d28f36b9da401c57d08cd7ebd57d972c36e`, clean independent clone.
