# Root Cause Hypothesis

Status: confirmed.

The HTTP handlers reused a payload-level error mapper for GET/POST paths but
PATCH and DELETE sent every non-route payload with the default HTTP 200. The
OpenAPI response table mirrored that omission.

The read policy and SQLite visibility query used truthiness/`NULLIF` defaults.
That erased the semantic distinction between an absent legacy field and a
field that was present but empty or null. The intended boundary is default on
absence only; present invalid labels must remain invalid and fail closed.

The evidence findings came from accumulated historical packages whose
individual phase statements were read as current instructions. Exact commands,
stage names, rollback references, count arithmetic, and remote-main freshness
were not always stated together, leaving correct historical bytes open to
misinterpretation.
