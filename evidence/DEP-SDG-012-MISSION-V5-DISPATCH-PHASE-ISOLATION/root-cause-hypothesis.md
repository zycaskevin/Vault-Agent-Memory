# Root Cause Hypothesis

## Hypothesis

The dispatcher test file remained in the generic Local Green remainder after
Mission V5 introduced explicit candidate/active replay. Because it was absent
from the identity harness, its two assertions always inspected live checkout
topology and therefore required an active merge even on an exact preliminary PR
head.

## Supporting evidence

- Hosted candidate Mission V5 identity controls passed before the remainder.
- The remainder alone reported exactly the two dispatcher V5 failures.
- The identity harness lists eight files and omits dispatcher V5.
- Both local and hosted remainder commands omit only Mission V5, not dispatcher
  V5.
- Production dispatcher correctly denied the preliminary topic; its fail-closed
  behavior is evidence against changing production code.

## Builder focused repair finding

The first focused source revision passed seven of eight selected checks but the
new SDG-011 anchor assertion denied during historical SDG-004 replay. Static
diff inspection found the Builder had accidentally added
`tests/test_repo_hygiene_tools.py` to historical `SDG004_COMPATIBILITY_PATHS`
and `SDG007_COMPATIBILITY_MODIFIED_PATHS`. Those records describe immutable
merged deliveries, so expanding either set correctly caused fail-closed replay.
The bounded repair removes only those two contaminating entries while retaining
the hygiene path in the new SDG-012 closed set.

## Contradicting evidence

No evidence shows a production dispatcher, validator, updater, activation, or
authority defect. The ordinary test job's synthetic merge topology already
passes the unconditional production dispatch replay.

## Security re-review finding

Return code zero alone is insufficient per-node evidence because pytest can
encode skip or non-strict xfail as success. The first rollback also ran the
dispatcher file only after reverting it to historical bytes, so it could not
prove the reviewed SDG-012 phase fixture, and it did not freshly bind canonical
`origin/main` to the exact delivery merge. These are verification defects, not
production authority defects. The bounded repair adds strict JUnit outcome
parsing and broader AST bypass rejection, retains exact reviewed bytes in an
external temporary clone, completes canonical phase proof before mutation, and
limits post-revert evidence to the first-parent-compatible INACTIVE state.

Focused v2C then falsified overlaying the reviewed SDG-012 runner into the
older activation proof topology: the validator correctly rejected that runner
because the proof binds its own trust-root bytes. The v2D correction does not
weaken validation. It overlays only reviewed test/outcome-harness bytes during
proof-bearing phase checks, retains and hashes the reviewed runner separately,
and executes that runner only against the no-proof post-revert baseline.

## Post-sign dev6 parser finding

The v2D rollback body was executable and fail-closed, but its record used
`rollback_version: 1.1` and omitted top-level `command:` and `verify:` fields.
Pinned Agentic SDD Governance experimental.6 accepts only version `1.0` plus
non-placeholder `target`, `command`, and `verify` values. It therefore failed
before merge with `rollback record is missing or incomplete`. This is a record
schema defect, not evidence against the rollback safeguards or product
authority behavior. v2E exposes parser-safe one-line command/verification
fields while retaining the full canonical-origin, exact-main, pre-revert phase,
and post-revert baseline checks.

## Falsification

The hypothesis is false if the same two failures remain after the dispatcher
nodes run from phase-neutral snapshots exactly once, if candidate dispatch
authorizes, if active replay is not the exact two-parent delivery or no longer
returns ACTIVE, or if the exact 2-node, 446-total, and one-ignore-per-remainder
collection invariants drift.
It is also false if any isolated node reports skip/xfail under return code zero,
or if rollback phase proof depends on bytes already replaced by the revert.

## Hosted v2E platform finding

v2E correctly rejected dispatcher skip/xfail, but applied the same one-PASS
JUnit requirement to all 446 identity nodes. Linux therefore rejected the
unchanged test runner's one Darwin-only node after pytest legitimately returned
zero with exact one-skip JUnit. Exact PR #490 run `31953893529` reproduced this
on Python 3.10/3.11/3.12 and the governance Local Green gate. The smallest
correction is an exact one-entry platform-skip allowlist while retaining genuine
one-PASS evidence everywhere else; broad skip acceptance would falsify the fix.

## Conclusion

Move test ownership, not authority semantics: add the two nodes to the explicit
phase harness, exclude them from both remainders, keep production bytes
unchanged, and never mutate historical delivery path sets.

## Static reviewer v3 signal finding

The rollback used one cleanup function as the handler for EXIT, HUP, INT, and
TERM. A trapped signal runs that function but does not mechanically require the
shell to terminate; the script could therefore remove its exclusive lease and
continue toward mutation. The bounded correction leaves cleanup only on EXIT
and makes each signal handler exit nonzero (129/130/143), which invokes EXIT
cleanup exactly once. This is rollback control-flow evidence, not a production
authority defect.

## PR #491 review finding

The malformed topology was denied directly by the Mission delivery validator,
but rollback never checked the two public dispatcher surfaces on that same
commit. A dispatcher-specific exception mapping regression could therefore
escape while direct validation stayed fail-closed. The minimal correction
retains direct denial and adds exact API/CLI denial assertions before revert.

The proposed equality between the future SDG-012 delivery topic and PR #487's
Mission proof topic contradicts the protocol: one is the compatibility delivery
being rolled back; the other is an immutable proof-bearing fixture. The root
cause is ambiguous naming and insufficient independent metadata binding, not a
missing equality. v4 gives the objects distinct names and validates each PR's
exact role. Production dispatcher, validator, updater, authority, and ledger
bytes remain outside the fix.

## Focused v4b fixture classification finding

Focused v4b falsified the assumption that the malformed checkout was
proof-bearing. Its commit used `protocol_base^{tree}`, so the proof path was
absent. Direct validation denied only because the wrapper separately supplied
the Mission proof bytes; dispatcher validation correctly classified the actual
checkout as the exact no-proof `INACTIVE` baseline. v4c separates those
contracts: the base-tree delivery shape must remain INACTIVE with zero
authorized tasks, while an exact proof-bearing topic tree with reversed parent
order must deny direct Mission, dispatcher API, and CLI. This is a test-fixture
defect, not a production authority defect.
