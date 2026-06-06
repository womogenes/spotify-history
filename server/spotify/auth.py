"""Small CLI for Spotify user auth and recently played tracks."""

from argparse import ArgumentParser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse
import json
import secrets
import time
import webbrowser

import requests
from dotenv import dotenv_values


AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
RECENT_TRACKS_URL = "https://api.spotify.com/v1/me/player/recently-played"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8787/callback"
DEFAULT_SCOPE = "user-read-playback-state user-read-recently-played"
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


class ConfigError(RuntimeError):
    """Raised when required env config is missing."""


@dataclass
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    refresh_token: str | None


def load_config() -> SpotifyConfig:
    env = dotenv_values(ENV_PATH)
    client_id = env.get("SPOTIFY_CLIENT_ID")
    client_secret = env.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ConfigError(
            "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in server/.env."
        )

    return SpotifyConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=env.get("SPOTIFY_REDIRECT_URI") or DEFAULT_REDIRECT_URI,
        refresh_token=env.get("SPOTIFY_REFRESH_TOKEN"),
    )


def build_authorize_url(config: SpotifyConfig, state: str, scope: str) -> str:
    query = urlencode(
        {
            "client_id": config.client_id,
            "response_type": "code",
            "redirect_uri": config.redirect_uri,
            "scope": scope,
            "state": state,
            "show_dialog": "true",
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def exchange_code_for_tokens(config: SpotifyConfig, code: str) -> dict[str, Any]:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.redirect_uri,
        },
        auth=(config.client_id, config.client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(config: SpotifyConfig, refresh_token: str) -> dict[str, Any]:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(config.client_id, config.client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def write_env_value(env_path: Path, key: str, value: str) -> None:
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()

    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n")


def wait_for_auth_code(redirect_uri: str, expected_state: str, timeout: int) -> str:
    parsed = urlparse(redirect_uri)
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ConfigError(
            "Local callback flow requires SPOTIFY_REDIRECT_URI to use localhost or "
            "127.0.0.1."
        )

    callback_path = parsed.path or "/"

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            request = urlparse(self.path)
            if request.path != callback_path:
                self.send_response(404)
                self.end_headers()
                return

            params = parse_qs(request.query)
            self.server.spotify_params = params  # type: ignore[attr-defined]

            if "error" in params:
                body = f"Spotify authorization failed: {params['error'][0]}\n"
                self.send_response(400)
            elif params.get("state", [None])[0] != expected_state:
                body = "Spotify authorization failed: state mismatch.\n"
                self.send_response(400)
            else:
                body = "Spotify authorization complete. You can close this tab.\n"
                self.send_response(200)

            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = HTTPServer((parsed.hostname, parsed.port or 80), CallbackHandler)
    deadline = time.time() + timeout

    while time.time() < deadline:
        if hasattr(server, "spotify_params"):
            break
        server.timeout = max(0.1, deadline - time.time())
        server.handle_request()

    params = getattr(server, "spotify_params", None)
    server.server_close()

    if params is None:
        raise TimeoutError(f"Timed out waiting for Spotify callback after {timeout}s.")
    if "error" in params:
        raise RuntimeError(f"Spotify returned an error: {params['error'][0]}")
    if params.get("state", [None])[0] != expected_state:
        raise RuntimeError("Spotify returned a mismatched state value.")

    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError("Spotify callback did not include an authorization code.")
    return code


def parse_manual_auth_input(value: str, expected_state: str) -> str:
    value = value.strip()
    if not value:
        raise RuntimeError("No authorization code or callback URL was provided.")

    if "://" not in value:
        return value

    parsed = urlparse(value)
    params = parse_qs(parsed.query)

    if "error" in params:
        raise RuntimeError(f"Spotify returned an error: {params['error'][0]}")
    if params.get("state", [None])[0] != expected_state:
        raise RuntimeError("Spotify returned a mismatched state value.")

    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError("Callback URL did not include an authorization code.")
    return code


def prompt_for_auth_code(expected_state: str) -> str:
    print()
    print(
        "After approving, paste the full redirected callback URL here. "
        "If your browser only shows the code, paste just the code."
    )
    return parse_manual_auth_input(input("Callback URL or code: "), expected_state)


def fetch_recent_tracks(access_token: str, limit: int) -> dict[str, Any]:
    response = requests.get(
        RECENT_TRACKS_URL,
        params={"limit": limit},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def print_recent_tracks(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    for item in payload.get("items", []):
        track = item["track"]
        artists = ", ".join(artist["name"] for artist in track["artists"])
        print(f"{item['played_at']} | {artists} - {track['name']}")


def handle_authorize(args: Any) -> int:
    config = load_config()
    state = secrets.token_urlsafe(24)
    url = build_authorize_url(config, state=state, scope=args.scope)

    print(f"Redirect URI: {config.redirect_uri}")
    print("Open this URL to authorize the app:")
    print(url)

    if args.print_only:
        return 0

    if not args.no_browser:
        webbrowser.open(url)

    if args.code:
        code = parse_manual_auth_input(args.code, expected_state=state)
    elif args.manual or args.no_browser:
        code = prompt_for_auth_code(expected_state=state)
    else:
        code = wait_for_auth_code(config.redirect_uri, expected_state=state, timeout=args.timeout)

    tokens = exchange_code_for_tokens(config, code)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Spotify did not return a refresh token.")

    if args.write_env:
        write_env_value(ENV_PATH, "SPOTIFY_REDIRECT_URI", config.redirect_uri)
        write_env_value(ENV_PATH, "SPOTIFY_REFRESH_TOKEN", refresh_token)
        print(f"Wrote SPOTIFY_REFRESH_TOKEN to {ENV_PATH}")
    else:
        print("Add this to server/.env:")
        print(f"SPOTIFY_REDIRECT_URI={config.redirect_uri}")
        print(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")

    print()
    print("Access token expires in:", tokens.get("expires_in"))
    return 0


def handle_recent(args: Any) -> int:
    config = load_config()
    refresh_token = args.refresh_token or config.refresh_token
    if not refresh_token:
        raise ConfigError(
            "Missing SPOTIFY_REFRESH_TOKEN. Run `python spotify/auth.py authorize "
            "--write-env` first."
        )

    token_payload = refresh_access_token(config, refresh_token)
    access_token = token_payload.get("access_token")
    if not access_token:
        raise RuntimeError("Spotify refresh response did not include an access token.")

    recent_tracks = fetch_recent_tracks(access_token, limit=args.limit)
    print_recent_tracks(recent_tracks, as_json=args.json)
    return 0


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    authorize = subparsers.add_parser(
        "authorize",
        help="Run the one-time user OAuth flow and obtain a refresh token.",
    )
    authorize.add_argument("--scope", default=DEFAULT_SCOPE)
    authorize.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for the local Spotify callback.",
    )
    authorize.add_argument(
        "--code",
        help="Manual authorization code or full redirected callback URL.",
    )
    authorize.add_argument(
        "--manual",
        action="store_true",
        help="Headless flow: print the URL and prompt for the callback URL or code.",
    )
    authorize.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the URL without trying to open a browser, then prompt manually.",
    )
    authorize.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the authorization URL and exit.",
    )
    authorize.add_argument(
        "--write-env",
        action="store_true",
        help="Persist SPOTIFY_REFRESH_TOKEN to server/.env.",
    )
    authorize.set_defaults(func=handle_authorize)

    recent = subparsers.add_parser(
        "recent",
        help="Fetch the current user's recently played tracks.",
    )
    recent.add_argument("--limit", type=int, default=20)
    recent.add_argument("--json", action="store_true")
    recent.add_argument("--refresh-token")
    recent.set_defaults(func=handle_recent)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
