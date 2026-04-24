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

print(load_dotenv(str(Path(__file__).parents[1] / ".env")))


def hash_dict(d: dict) -> str:
    s = json.dumps(
        d,
        sort_keys=True,
        separators=(",", ":"),  # No whitespace
        ensure_ascii=False,  # Ensure all ascii
    )
    return hashlib.md5(s.encode()).hexdigest()


if __name__ == "__main__":
    audio_file_pattern = str(
        Path(__file__).parents[1] / "data/spotify/**/Streaming_History_Audio_*.json"
    )

    # Initialize pocketbase
    pb = pocketbase.Client("https://fiddle-db.wfeng.dev")
    auth_data = pb.collection("users").auth_with_password(
        username_or_email=os.environ["PB_EMAIL"],
        password=os.environ["PB_PASSWORD"],
    )

    # Cursed Python lol
    json_files = glob.glob(audio_file_pattern, recursive=True)[:1]

    print("Loading streaming history...")
    all_streams = sum([json.loads(Path(file).read_text()) for file in json_files], [])
    print(f"Loaded {len(all_streams):,} streams")

    for stream in tqdm(all_streams, ncols=80):
        md5 = hash_dict(stream)
