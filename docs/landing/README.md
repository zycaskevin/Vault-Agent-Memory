# Vault-for-LLM Landing Demo

This directory contains the first static landing/demo page for Vault-for-LLM.

Open locally:

```bash
open docs/landing/index.html
```

The page is intentionally dependency-free:

- no React/Vite build step;
- no external network assets;
- no hosted analytics;
- safe to view offline or publish through GitHub Pages.
- English, Traditional Chinese, and Simplified Chinese switch in-place with a
  small static dictionary.
- Directional connector lines use SVG/CSS only and respect
  `prefers-reduced-motion`.

## Purpose

The landing page is not a replacement for the README.

Its job is to make the product story understandable in 30 seconds:

> Agents need memory governance, not just RAG.

It shows the shortest user path:

1. copy the install prompt to an Agent;
2. let the Agent set up Vault;
3. review a small daily memory report;
4. let reviewed memory become reusable by other Agents.

## Maintenance Rules

- Keep the first screen focused on memory governance, not a feature list.
- Keep the install prompt aligned with `vault guide --intent install`.
- Keep all three languages aligned when the core story changes.
- Keep flow animations subtle and directional; they should explain the memory
  lifecycle, not decorate the page.
- Keep the Obsidian conflict choices explicit: accept Obsidian, accept Vault,
  or keep both.
- Keep remote sharing language honest: Supabase and Gateway are adapters, not
  magic offline multi-master sync.
- Do not add a frontend build system unless the landing page needs real
  interactivity beyond this static demo.
