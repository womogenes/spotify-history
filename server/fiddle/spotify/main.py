"""
Sync Spotify playback history into PocketBase.
"""

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
import logging
import signal
import time

import pocketbase
import requests
from dotenv import load_dotenv

from fiddle.db.utils import batch_upsert_records
from fiddle.db.utils import pocketbase_client
from fiddle.db.utils import resolve_pocketbase_url
from fiddle.utils import hash_dict

from spotify.auth import load_config
from spotify.auth import refresh_access_token


SERVER_DIR = Path(__file__).resolve().parents[2]
COLLECTION_NAME = "audio_streams"
POLL_INTERVAL_SECONDS = 2.5
CURRENT_PLAYBACK_URL = "https://api.spotify.com/v1/me/player"
TRACK_DONE_THRESHOLD_MS = 5_000
TRACK_DONE_THRESHOLD_RATIO = 0.9


@dataclass
class ActiveStream:
    id: str
    track: dict[str, Any]
    max_progress_ms: int
    duration_ms: int
    shuffle: bool
    reason_start: str | None


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def track_to_stream(
    record_id: str,
    track: dict[str, Any],
    ts: str,
    ms_played: int,
    shuffle: bool,
    skipped: bool,
    reason_start: str | None,
    reason_end: str | None,
) -> dict[str, Any]:
    """
    Turn a currently playing track into a stream row in the DB
    """
    album = track.get("album") or {}
    track_artists = track.get("artists") or []
    album_artists = album.get("artists") or []

    artist = track_artists[0]["name"] if track_artists else None
    album_artist = album_artists[0]["name"] if album_artists else artist

    return {
        "id": record_id,
        "ts": ts,
        "source": "spotify-api",
        "platform": "spotify_api",
        "ms_played": ms_played,
        "conn_country": None,
        "ip_addr": None,
        "master_metadata_track_name": track.get("name"),
        "master_metadata_album_artist_name": album_artist,
        "master_metadata_album_album_name": album.get("name"),
        "spotify_track_uri": track.get("uri"),
        "episode_name": None,
        "episode_show_name": None,
        "spotify_episode_uri": None,
        "audiobook_title": None,
        "audiobook_uri": None,
        "audiobook_chapter_uri": None,
        "audiobook_chapter_title": None,
        "reason_start": reason_start,
        "reason_end": reason_end,
        "shuffle": shuffle,
        "skipped": skipped,
        "offline": False,
        "offline_timestamp": None,
        "incognito_mode": False,
    }


def fetch_current_playback(
    access_token: str,
) -> dict[str, Any]:
    """
    Hit Spotify API to get the current playback state
    """
    response = requests.get(
        CURRENT_PLAYBACK_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code == 204:
        return {}
    response.raise_for_status()
    return response.json()


class SpotifyAccessToken:
    """
    Utility for providing always-up-to-date Spotify access token
    """

    def __init__(self) -> None:
        self.config = load_config()
        self.access_token: str | None = None
        self.expires_at = 0.0

    def get(self) -> str:
        if self.access_token and time.time() < self.expires_at - 60:
            return self.access_token

        if not self.config.refresh_token:
            raise RuntimeError(
                "Missing SPOTIFY_REFRESH_TOKEN. Run "
                "`python spotify/auth.py authorize --write-env` first."
            )

        token_payload = refresh_access_token(self.config, self.config.refresh_token)
        access_token = token_payload.get("access_token")
        if not access_token:
            raise RuntimeError("Spotify refresh response did not include an access token.")

        self.access_token = access_token
        self.expires_at = time.time() + int(token_payload.get("expires_in", 3600))
        return access_token


def is_track_done(progress_ms: int, duration_ms: int) -> bool:
    if duration_ms <= 0:
        return False

    return (
        duration_ms - progress_ms <= TRACK_DONE_THRESHOLD_MS
        or progress_ms / duration_ms >= TRACK_DONE_THRESHOLD_RATIO
    )


def start_active_stream(
    playback: dict[str, Any],
    reason_start: str | None,
) -> ActiveStream | None:
    track = playback.get("item")
    if not track or playback.get("currently_playing_type") != "track":
        return None

    started_at_ms = int(time.time() * 1000)

    return ActiveStream(
        id=hash_dict(
            {
                "source": "spotify-api",
                "started_at_ms": started_at_ms,
                "track_uri": track.get("uri"),
            }
        ),
        track=track,
        max_progress_ms=playback.get("progress_ms") or 0,
        duration_ms=track.get("duration_ms") or 0,
        shuffle=bool(playback.get("shuffle_state")),
        reason_start=reason_start,
    )


def finalize_active_stream(
    active_stream: ActiveStream,
    reason_end: str | None,
) -> dict[str, Any]:
    skipped = not is_track_done(
        active_stream.max_progress_ms,
        active_stream.duration_ms,
    )
    return track_to_stream(
        record_id=active_stream.id,
        track=active_stream.track,
        ts=utc_now(),
        ms_played=active_stream.max_progress_ms,
        shuffle=active_stream.shuffle,
        skipped=skipped,
        reason_start=active_stream.reason_start,
        reason_end=reason_end,
    )


def upload_active_stream(
    pb_client: pocketbase.Client,
    active_stream: ActiveStream,
    reason_end: str,
) -> int:
    stream = finalize_active_stream(active_stream, reason_end=reason_end)
    return batch_upsert_records(pb_client, COLLECTION_NAME, [stream])


def poll_once(
    pb_client: pocketbase.Client,
    token_provider: SpotifyAccessToken,
    active_stream: ActiveStream | None,
) -> tuple[int, ActiveStream | None]:
    """
    Do a single poll, upload to database
    """
    playback = fetch_current_playback(token_provider.get())
    current_track = playback.get("item")
    current_track_uri = current_track.get("uri") if current_track else None
    active_track_uri = active_stream.track.get("uri") if active_stream else None

    if not current_track_uri or playback.get("currently_playing_type") != "track":
        if active_stream is None:
            return 0, None

        stream = finalize_active_stream(active_stream, reason_end="endplay")
        return batch_upsert_records(pb_client, COLLECTION_NAME, [stream]), None

    if active_stream is None:
        if not playback.get("is_playing"):
            return 0, None
        return 0, start_active_stream(playback, reason_start=None)

    if current_track_uri == active_track_uri:
        active_stream.max_progress_ms = max(
            active_stream.max_progress_ms,
            playback.get("progress_ms") or 0,
        )
        active_stream.shuffle = bool(playback.get("shuffle_state"))
        return 0, active_stream

    previous_done = is_track_done(
        active_stream.max_progress_ms,
        active_stream.duration_ms,
    )
    reason_end = "trackdone" if previous_done else "fwdbtn"
    reason_start = "trackdone" if previous_done else "fwdbtn"
    stream = finalize_active_stream(active_stream, reason_end=reason_end)
    next_active_stream = start_active_stream(playback, reason_start=reason_start)

    return batch_upsert_records(pb_client, COLLECTION_NAME, [stream]), next_active_stream


def poll_forever() -> None:
    """
    Run in a tight loop
    """
    load_dotenv(str(SERVER_DIR / ".env"))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    pb_url = resolve_pocketbase_url()
    logging.info("Connecting to PocketBase at %s", pb_url)

    pb_client = pocketbase_client(pb_url)
    token_provider = SpotifyAccessToken()
    active_stream = None
    should_stop = False

    def request_stop(signum: int, frame: Any) -> None:
        nonlocal should_stop
        should_stop = True
        logging.info("Received signal %s; flushing active stream before exit", signum)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        while not should_stop:
            try:
                upserted, active_stream = poll_once(
                    pb_client=pb_client,
                    token_provider=token_provider,
                    active_stream=active_stream,
                )
                logging.info("Upserted %s stream(s)", upserted)

            except Exception:
                logging.exception("Polling iteration failed")

            time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        if active_stream is not None:
            upserted = upload_active_stream(
                pb_client,
                active_stream,
                reason_end="endplay",
            )
            logging.info("Flushed %s active stream(s)", upserted)


if __name__ == "__main__":
    poll_forever()
