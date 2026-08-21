# Root Cause Hypothesis

## Hypothesis

The original L0 filesystem label and setup templates encoded identity/profile
modeling as part of the memory layer. Multiple project-creation paths and active
documentation copied that assumption independently, so a documentation-only
rename cannot satisfy the boundary or retain compatibility.

## Supporting evidence

`vault.cli_core.cmd_init` and `vault.agent_setup.ensure_project` each contain a
literal `L0-identity` list. `vault.compiler.assign_layer` maps only that legacy
spelling. The generated three-language memory-agent guide contains explicit
Profile, user-profile, care-summary, and personality-profile instructions.

## Contradicting evidence

The stored layer is the neutral value `L0`, and the compiler already isolates
directory-name inference from database semantics. Therefore no schema or stored
data migration is required.

## Falsification test

Centralize the canonical/legacy directory contract, make both project creators
use the canonical list, retain the legacy inference alias, neutralize generated
guidance, and rerun focused plus full regression gates. A legacy-read failure or
new human-modeling instruction falsifies the hypothesis.

## Conclusion

Confirmed. The smallest compatible fix changes new-project output and active
guidance while preserving all legacy identifiers and data in place.

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
