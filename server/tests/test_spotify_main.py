import unittest
from unittest.mock import patch

from fiddle.spotify.main import start_active_stream


class StartActiveStreamTest(unittest.TestCase):
    def test_generates_pocketbase_valid_record_id(self) -> None:
        playback = {
            "currently_playing_type": "track",
            "progress_ms": 1234,
            "shuffle_state": False,
            "item": {
                "duration_ms": 180000,
                "uri": "spotify:track:abc123",
            },
        }

        with patch("fiddle.spotify.main.time.time", return_value=1717657200.123):
            active_stream = start_active_stream(playback, reason_start=None)

        self.assertIsNotNone(active_stream)
        self.assertEqual(len(active_stream.id), 32)


if __name__ == "__main__":
    unittest.main()
