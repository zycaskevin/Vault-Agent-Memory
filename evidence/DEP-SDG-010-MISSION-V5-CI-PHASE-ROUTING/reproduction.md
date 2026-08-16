# Reproduction

## Expected

An unmerged Mission V5 topic must prove its exact proof, linear topic closure,
and protected review without becoming ACTIVE. Only main after one exact
two-parent delivery merge may evaluate ACTIVE.

## Actual

PR #483's governance job checked out exact head
`bd9a3aca8b79a459ac7b8dda87492048093d3d3d`. That head is linear from
`46690372e532c50761f9232ff5b2e20e18779d28`; the full delivery validator
correctly found zero two-parent delivery commits and denied during Local Green.

## Deterministic steps

1. Check out an exact linear activation topic from its protocol base.
2. Run the full active delivery predicate: it must deny before merge.
3. Run the preliminary predicate: it must require exact base, exact proof,
   every closed activation path, and linear parent chain, then return INACTIVE.
4. Merge with `--no-ff` using the protocol base as first parent and the topic
   as second parent; run active validation and require ACTIVE.
5. Add an extra path, pending artifact, replacement, or wrong phase and
   require denial.

## Environment and preconditions

The RED observation is from GitHub Actions pull_request execution, not a new
local test run. No private/live data, credential, deployment, or production
operation is involved.
