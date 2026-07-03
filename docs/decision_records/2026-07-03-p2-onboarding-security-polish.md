# P2 Onboarding And Gateway Safety Polish

Date: 2026-07-03

## Decision

Add a P2 polish pass for first-run documentation, beginner FAQ, Gateway safety
warnings, actionable error payloads, search query length limits, and HTTP
security headers.

## Rationale

After `vault quickstart`, new users should not need to discover operational
rules by reading the advanced installer. The product needs a short path for the
first five minutes, and Gateway needs explicit safety reminders before users
bind it beyond localhost.

## Behavior

- `docs/quickstart.md` provides a 5-minute quickstart and 10 beginner FAQs.
- `vault guide --intent install` includes the 5-minute flow and FAQ summary.
- `vault guide --intent faq` prints the beginner FAQ directly.
- Gateway startup output highlights token handling and remote deployment
  checklist items.
- Gateway error payloads include `try` and `next_action` for common failures.
- Search query inputs are capped at 1000 characters for CLI, MCP, and Gateway.
- Gateway JSON responses send `X-Content-Type-Options` and `Referrer-Policy`;
  TLS Gateway responses also send HSTS.

## Non-Goals

- This does not replace the advanced `setup-agent` documentation.
- This does not make Gateway safe for public internet exposure without an
  operator-controlled network, token storage, and TLS boundary.
- This does not change the 64KB HTTP request body cap; it adds a clearer search
  query cap inside that envelope.
