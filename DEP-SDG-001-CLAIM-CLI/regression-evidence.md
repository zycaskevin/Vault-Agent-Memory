# Regression Evidence

## Regression test added or strengthened

No product-code regression test was needed. The original failing CLI command
and corrected command form a deterministic RED/GREEN control for the invocation
boundary.

## Related tests executed

`sddgov status .` and direct inspection of `.sddgov/work-claims.json` must show
exactly one active `SDG-001` claim for `codex`.

## Unaffected paths sampled

No package source, product code, test, CI workflow, or policy file changed as a
result of correcting the claim command.
