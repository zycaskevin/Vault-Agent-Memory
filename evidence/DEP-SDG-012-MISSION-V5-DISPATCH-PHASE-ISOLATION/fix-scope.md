# Fix Scope

## Smallest sufficient change

Give the dispatcher tests a phase-neutral, test-only snapshot fixture equivalent
to the Mission V5 fixture. Add their exact two nodes to the identity harness,
raise the total from 444 to 446, and add one exact remainder ignore in each
local/hosted command. Advance the closed protocol release over the exact
reviewed SDG-012 merge.

## In scope

- Test-only candidate/active replay fixture.
- Identity FILES count 2 and total 446.
- Local/hosted disjoint remainder exclusions and exact CI pins.
- Closed SDG-012 compatibility paths and governance proof.

## Explicit non-scope

No production dispatcher, validator, updater, activation, proof, authority,
progress, ledger, product, private/live, deployment, release, L2, or L3 change.

## Blast radius

Limited to which Git snapshot the two dispatcher assertions inspect and which
test partition owns them. Test coverage is preserved and made phase-exact.
