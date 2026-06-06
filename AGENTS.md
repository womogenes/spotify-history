## Style guide

- Do not use `from __future__ import annotations` for Python
- Always use sentence case for Markdown headers, diagram labels, titles, etc.
- Update this AGENTS.md as you work
- Write Python docstrings with triple quotes and with newlines after opening and before closing.
- Do not write unnecessary helpers. Prefer flat things.

## Project notes

- The SvelteKit frontend uses `@sveltejs/adapter-vercel` with an explicit Node runtime so Vercel does not dynamically install an adapter during builds.
- Live Spotify stream IDs must remain 32 characters because the PocketBase `audio_streams.id` field enforces a 32-character minimum.
