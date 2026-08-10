# Risk and Evidence Matrix

| Level | Default behavior | DEP expectation | Human gate |
|---|---|---|---|
| L0 | Reproduce, targeted check, bounded fix, targeted proof. | Concise proof; DEP when cause is not obvious or regression exists. | None in approved scope. |
| L1 | Evidence before change; full regression proof. | Full DEP for cross-module, data-flow, auth, reliability, or regression work. | None in approved scope. |
| L2 | Evidence and safe prototype may proceed; do not silently change product behavior. | Full DEP plus Decision Package and recommendation. | One bounded decision. |
| L3 | Prepare code, dry run, rollback, and redacted proof; do not perform the live action. | Full DEP, rollback drill, exact action and audit receipt. | Explicit approval for the concrete action. |

Escalate the authority level when the fix changes privacy, retention, pricing, quota, permission, public API, user-visible promise, production data, or irreversible operations. More evidence never lowers an authority level.
