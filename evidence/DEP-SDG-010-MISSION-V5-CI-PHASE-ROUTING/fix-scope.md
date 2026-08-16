# Fix Scope

## Smallest sufficient change

Add a strict linear-topic predicate alongside the unchanged active delivery
predicate. Route the isolated Mission V5 test file with an explicit required
CLI phase: preliminary for pull requests and active for main. The preliminary
fixture validates the proof at its recorded activation time, protocol ancestry,
and closed topic, then replays the protocol-base inactive state.

## In scope

- Mission V5 runner and fixture; identity harness phase parser and count.
- CI and Local Green phase routing; CI byte pins and static routing tests.
- SDG-010 Work Package, DEP, claim/event, and later merge/review records.

## Explicit non-scope

No change to active delivery semantics, exact merge topology, task updater,
dispatcher/action authorization, progress, proof publication, customer data,
production, release, credentials, billing, or L2/L3 behavior.
