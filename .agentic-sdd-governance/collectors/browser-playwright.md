# Browser and Playwright Collectors

Use for visible UI symptoms, Console errors, Network behavior, DOM state, and E2E timing.

## Collection boundary

Deny by default: browser evidence is local-only until a bounded, manually reviewed derivative proves that sensitive URL and identity data has been removed. Never share query parameters, path segments, headers, referrers, full request URLs, signed URLs, session identifiers, emails, user IDs, OAuth callbacks, bot/admin secrets, connector credentials, provider/runtime secrets, or Supabase service-role values. A host, route shape, or fixed error class may be retained only when it is necessary for the reproduction and cannot identify a person, tenant, credential, or privileged endpoint.

## Browser Console (`browser-console`)

Capture only the reproduction window. Before export, sanitize both `message` and `source` deny-by-default: remove sensitive URLs and URL fragments, tokens, OAuth data, personal identifiers, response bodies, and full local paths. Preserve only timestamp, level, a reviewed fixed error class or sanitized message, browser version, a non-identifying source shape, and the action that produced the entry.

Likely secrets: Authorization or cookie headers, provider/runtime secrets, Supabase service-role values, connector/OAuth/bot/admin credentials, email, user IDs, request URLs, referrers, signed URLs, and session identifiers.

## HAR (`browser-har`)

Prefer a filtered HAR for the affected host and time window. Before any derivative leaves local storage, apply a deny-by-default safe metadata allowlist: retain only the minimum reviewed method, status class, timing, origin, and non-identifying route shape needed for the reproduction. Remove cookies, Authorization, Referer, Set-Cookie, Proxy-Authorization, API-key and custom identity headers, sensitive path segments, query/fragment data, signed URLs, unapproved metadata, and **all request and response bodies**, regardless of apparent content. A HAR is text but may contain encoded binary or deeply nested secrets; inspect the redaction report and manually review it.

## Playwright (`playwright-trace`)

For reproducible tests, keep the failing test, console/network summary, and trace. Native trace ZIPs and screenshots are binary and therefore fail closed in the MVP gateway. Export a manually reviewed text summary or redacted screenshot derivative before attachment.

Example:

```bash
npx playwright test path/to/spec --trace on
evidence collect <DEP> --collector playwright-trace --input test-results/trace.zip
```

Do not share the raw trace when it includes typed credentials, DOM content, cookies, storage, or private user data.
