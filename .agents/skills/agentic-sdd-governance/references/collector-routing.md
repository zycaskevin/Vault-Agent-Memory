# Collector Routing

Read only the matching playbook under the resolved Governance Root:

| Symptom or stack | Collector IDs | Playbook |
|---|---|---|
| Browser UI, Console, Network, DOM, E2E | `browser-console`, `browser-har`, `playwright-trace` | `collectors/browser-playwright.md` |
| Flutter or Android runtime | `flutter-log`, `android-logcat` | `collectors/flutter-android.md` |
| Supabase local stack or containerized service | `supabase-log`, `docker-log` | `collectors/supabase-docker.md` |
| Tests, CLI, build, diff, blame, bisect | `terminal`, `git` | `collectors/terminal-git.md` |

Prefer the narrowest time window and smallest relevant component. Record the exact collection command in reproduction or verification without embedding credentials.
