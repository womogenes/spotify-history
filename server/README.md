# Fiddle server

Listens to Spotify streaming events in realtime and updates the database accordingly.

Code here also performs backfills.

## Structure

- `prod/`: Deployment scripts (e.g. systemd service file)
- `data/`: Data (gitignored)
  - `spotify/`: Spotify streaming history
    - `Spotify Extended Streaming History/`: Full history as of July 2025
