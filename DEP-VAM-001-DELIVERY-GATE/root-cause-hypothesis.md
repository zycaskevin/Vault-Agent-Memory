# Root Cause Hypothesis

## Hypothesis

VAM-001 replaced the exact case-sensitive historical phrase required by the
baseline compatibility test. Separately, the PATH workaround exposed the
virtual environment's `vault` console script and the host-created worktree
directories retained mode 0775; both differ from the hosted clean-checkout
preconditions used by the existing tests.

## Supporting evidence

The baseline assertion requires the literal `Runtime is not implemented`.
The status page conveyed the same meaning with different casing. Agent-setup
tests pass when invoked with the virtual-environment Python by absolute path and
without that environment's `vault` entry on PATH. Source files are 0644 while
the worktree root and `tests/` directory are 0775.

## Contradicting evidence

Focused VAM-001 tests and the complete 446-node identity isolation suite pass,
so there is no evidence of frozen artifact drift or runtime behavior change.

## Falsification test

Restore the exact historical phrase, run the failing baseline node, expose
only a `python` shim on PATH, normalize source-directory modes to 0755, and
rerun the full CI Cost Guard. Any remaining repository failure falsifies the
hypothesis.

## Conclusion

Confirmed. One bounded documentation compatibility repair is required. The
other failures are local execution-precondition drift and require no product
or acceptance change.
