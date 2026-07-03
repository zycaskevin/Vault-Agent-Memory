# Landing Page Trilingual Flow Demo

Date: 2026-07-03

## Context

The landing/demo page is meant for people who may not know CLI, MCP, RAG, or
agent memory terminology. The first page must explain the product through the
memory lifecycle, not through a feature list.

The earlier static landing page was English-only and visually clear, but it did
not yet match the multilingual README direction. It also showed memory cards
without enough directional guidance.

## Decision

The landing page now supports English, Traditional Chinese, and Simplified
Chinese through a small in-page dictionary. English remains the no-JavaScript
default.

The page also uses SVG/CSS connector lines and subtle dashed motion to show the
flow:

1. agent discovers reusable knowledge;
2. Vault turns it into a candidate;
3. review gates decide what can be trusted;
4. promoted memory becomes reusable;
5. stale memory can roll back;
6. audit keeps the system accountable.

The animation is explanatory, not decorative, and is disabled for users who
prefer reduced motion.

## Consequences

- Future copy changes must update all three language bundles together.
- The page remains dependency-free and offline-safe.
- Directional visuals should stay tied to memory governance. Avoid decorative
  effects that do not explain the product.
- README translations and the landing page should use the same consumer-first
  vocabulary: daily memory report, governed-auto setup, candidate review, and
  rollback/audit.
