# Module Size Baseline Review

Date: 2026-07-07
Scope: `vault/agent_setup.py` and `scripts/module_size_baseline.json`.

## Review Decision

`vault/agent_setup.py` is accepted into the module-size baseline at 1231 lines.

This is a baseline acknowledgement for existing code, not approval for further
growth. The module-size gate should fail again if this file grows beyond the
recorded baseline without another explicit review.

## Reason

The release readiness module-size gate uses a 1200-line default limit. The
multi-agent setup work already made `vault/agent_setup.py` larger than that
default. The current documentation PR does not change this module, but CI runs
the gate for every PR and therefore needs a reviewed baseline entry.

## Follow-Up

Future implementation work should split `vault/agent_setup.py` by responsibility
instead of increasing the baseline again. Likely extraction candidates are:

- agent detection and roster discovery;
- generated adapter templates;
- schedule and sync template generation;
- startup contract / doctor output assembly.
