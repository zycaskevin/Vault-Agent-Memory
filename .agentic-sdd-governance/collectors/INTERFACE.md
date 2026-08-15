# Collector Interface

Every collector produces a file outside the DEP, then imports it through the same local contract:

```bash
evidence collect <DEP> --collector <id> --input <file> [--label <name>]
```

The CLI copies the artifact into `private/raw`, records collector ID, timestamp, relative path, and SHA-256, and marks it non-shareable. `evidence redact` creates a safe derivative when supported.

A Collector Playbook must state:

- purpose and supported questions;
- local command or tool;
- minimum time window and scope;
- sensitive fields likely to appear;
- expected file type;
- redaction/manual-review path;
- cleanup/retention notes.

Collectors do not upload, post, email, or attach evidence. They do not expand L0-L3 authority.
