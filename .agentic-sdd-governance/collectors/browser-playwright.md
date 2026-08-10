# Browser and Playwright Collectors

Use for visible UI symptoms, Console errors, Network behavior, DOM state, and E2E timing.

## Browser Console (`browser-console`)

Capture only the reproduction window. Preserve timestamp, level, message, source, browser version, URL with query secrets removed, and the action that produced the entry.

Likely secrets: authorization data printed by the app, email, user IDs, request URLs, session identifiers.

## HAR (`browser-har`)

Prefer a filtered HAR for the affected host and time window. Remove cookies, Authorization, request/response bodies containing user data, signed URLs, and query tokens. A HAR is text but may contain encoded binary or deeply nested secrets; inspect the redaction report and manually review it.

## Playwright (`playwright-trace`)

For reproducible tests, keep the failing test, console/network summary, and trace. Native trace ZIPs and screenshots are binary and therefore fail closed in the MVP gateway. Export a manually reviewed text summary or redacted screenshot derivative before attachment.

Example:

```bash
npx playwright test path/to/spec --trace on
evidence collect <DEP> --collector playwright-trace --input test-results/trace.zip
```

Do not share the raw trace when it includes typed credentials, DOM content, cookies, storage, or private user data.
