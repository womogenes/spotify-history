"""
Backfill the pocketbase with existing streaming history
"""

from pathlib import Path
from tqdm import tqdm

from dotenv import load_dotenv

from fiddle.db.utils import batch_upsert_records
from fiddle.db.utils import pocketbase_client
from fiddle.scripts.streams import get_all_streams

load_dotenv(str(Path(__file__).parents[1] / ".env"))

BATCH_SIZE = 500
COLLECTION_NAME = "audio_streams"


if __name__ == "__main__":
    # Get all streams
    all_streams = get_all_streams()

    # Initialize pocketbase
    pb = pocketbase_client()

    uploaded = 0

    for start in tqdm(range(0, len(all_streams), BATCH_SIZE), ncols=80):
        chunk = all_streams[start : start + BATCH_SIZE]
        uploaded += batch_upsert_records(pb, COLLECTION_NAME, chunk)

    print(f"Upserted {uploaded:,} streams")
