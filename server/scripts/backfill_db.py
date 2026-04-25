"""
Backfill the pocketbase with existing streaming history
"""

from pathlib import Path
import glob
import json
import hashlib
from tqdm import tqdm

import pocketbase

from dotenv import load_dotenv
import os

from streams import get_all_streams

load_dotenv(str(Path(__file__).parents[1] / ".env"))

BATCH_SIZE = 500


def hash_dict(d: dict) -> str:
    s = json.dumps(
        d,
        sort_keys=True,
        separators=(",", ":"),  # No whitespace
        ensure_ascii=False,  # Ensure all ascii
    )
    return hashlib.md5(s.encode()).hexdigest()


if __name__ == "__main__":
    # Get all streams
    all_streams = get_all_streams()

    # Initialize pocketbase
    pb = pocketbase.Client("https://fiddle-db.wfeng.dev")
    auth_data = pb.collection("_superusers").auth_with_password(
        username_or_email=os.environ["PB_EMAIL"],
        password=os.environ["PB_PASSWORD"],
    )

    uploaded = 0

    for start in tqdm(range(0, len(all_streams), BATCH_SIZE), ncols=80):
        chunk = all_streams[start : start + BATCH_SIZE]
        res = pb.send(
            "/api/batch",
            {
                "method": "POST",
                "body": {
                    "requests": [
                        {
                            "method": "PUT",
                            "url": "/api/collections/audio_streams/records",
                            "body": {
                                "id": hash_dict(stream),
                                **stream,
                            },
                        }
                        for stream in chunk
                    ],
                },
            },
        )
        uploaded += len(res)

    print(f"Upserted {uploaded:,} streams")
