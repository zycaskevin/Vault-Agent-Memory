# Root Cause Hypothesis

## Hypothesis

`sddgov claim --path` selects the governed project root, not the Work Package
record. Passing a Markdown file therefore makes the CLI resolve its state as
`<markdown-file>/.sddgov`, which cannot be created.

## Supporting evidence

The traceback ends in the governance state writer while creating the parent of
the supplied path. CLI help documents `--path PATH` separately from the
positional `work_package` identifier.

## Contradicting evidence

None. No partial claim or nested directory was created.

## Falsification test

Run the same claim with positional Work Package `SDG-001` and `--path .`.
The hypothesis is false if it does not update the repository's
`.sddgov/work-claims.json` with one active claim.

## Conclusion

Confirmed CLI invocation error; no package or repository code defect.
