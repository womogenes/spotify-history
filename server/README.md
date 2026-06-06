# Fiddle server

Syncs Spotify listening history into PocketBase.

There are two ingestion paths:

- `fiddle.spotify.main`: Polls Spotify's current playback endpoint (`/v1/me/player`) and writes inferred stream rows when a track ends, changes, or playback disappears.
- `fiddle.scripts.backfill_db`: Imports the local Spotify Extended Streaming History export and upserts those records into PocketBase.

Live rows are marked with `source = "spotify-api"`. They do not include export-only fields such as `conn_country`, `ip_addr`, or exact Spotify `reason_start` / `reason_end` values. Those values only come from the Extended Streaming History export.

## Spotify auth

Create or refresh the Spotify token:

```bash
uv run python spotify/auth.py authorize --write-env
```

On a headless machine:

```bash
uv run python spotify/auth.py authorize --no-browser --write-env
```

Open the printed URL in a local browser, approve it, then paste the redirected callback URL back into the terminal.

## Live sync

Run the live poller:

```bash
uv run python -m fiddle.spotify.main
```

The poller keeps the currently playing track in memory. It only writes a row after it observes that track end, change, or disappear. `ms_played`, `skipped`, and `reason_end` are inferred from the maximum observed playback progress.

## Backfill

Put Spotify Extended Streaming History files under `data/spotify/`, then run:

```bash
uv run python -m fiddle.scripts.backfill_db
```

## Structure

- `fiddle/spotify/`: Live Spotify playback polling
- `fiddle/db/`: PocketBase helpers
- `fiddle/scripts/`: Backfill and data loading scripts
- `prod/`: Deployment scripts (e.g. systemd service file)
- `data/`: Data (gitignored)
  - `spotify/`: Spotify streaming history
    - `Spotify Extended Streaming History/`: Full history as of July 2025
