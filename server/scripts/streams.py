import glob
from pathlib import Path
import json

def get_all_streams():
    """
    Load all ~130k streams (as of July 2025)
    """
    audio_file_pattern = str(
        Path(__file__).parents[1] / "data/spotify/**/Streaming_History_Audio_*.json"
    )

    # Cursed Python lol
    json_files = glob.glob(audio_file_pattern, recursive=True)

    print("Loading streaming history...")
    all_streams = sum([json.loads(Path(file).read_text()) for file in json_files], [])
    print(f"Loaded {len(all_streams):,} streams")

    return all_streams
