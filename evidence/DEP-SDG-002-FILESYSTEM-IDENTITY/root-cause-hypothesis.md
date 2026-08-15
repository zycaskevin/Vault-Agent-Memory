# Root Cause Hypothesis

## Confirmed cause

The frozen Subject verifier intentionally fails closed when any stored chain
identity changes, but its legacy identity tuple includes directory `st_size`
and `st_mtime_ns`. Those are membership metadata, not directory-object
identity. Codex runtime and shared OS temporary roots may create or delete
unrelated siblings while protected review is running, so an unchanged retained
file can be classified as drift.

The deterministic RED proves the mechanism: target bytes and inode remained
unchanged, only an unrelated sibling was created, and the legacy audit denied.
The stable-checkout control then completed the same full Local Green Gate with
zero failures.

This is an availability and test-environment isolation defect, not evidence of
a successful pathname-replacement bypass. The verifier remained fail-closed in
every observed failure.

## Hypothesis

TODO

## Supporting evidence

TODO

## Contradicting evidence

TODO

## Falsification test

TODO

## Conclusion

TODO
