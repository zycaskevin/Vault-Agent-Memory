# Verification

## Green command and result

Primary command:

```text
umask 022 && PATH=$PYTHON_SHIM:$USER_BIN:/usr/local/bin:/usr/bin:/bin sddgov ci local-gate .
```

Result: PASS. Governance doctor and CI contract verification passed; README
command smoke and release parity passed; 446 identity-isolated frozen Subject
nodes passed; the remaining suite reported 2928 passed and 10 skipped.

Original focused provider/Gateway/change-envelope suite: 40 passed. The
CodeRabbit remediation exact head subsequently passed 42 focused tests, 446
identity-isolated nodes, and 2,930 repository tests with 10 skips.

## Before/after evidence

Before: the new test could not import `vault.memory_change_envelope`, and the
Gateway test could not import `gateway_memory_changes`.

After: the provider returns stable policy-filtered pages, stale revisions return
no content, the new GET route and OpenAPI contract are available, localhost HTTP
smoke passes, and the entire repository Local Green gate passes.

## Remaining limitations

- The first version represents current snapshots, not complete historical event
  replay or historical full-content reconstruction.
- Audit references are empty for legacy/current rows that have no matching
  audit-log event.
- An independent focused architecture review is still required before merge.
- The installed governance CLI reports version `0.2.0-experimental.3` while the
  repository package is `0.2.0-experimental.6`; doctor reports this as a warning,
  not an error.
