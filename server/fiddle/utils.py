"""Shared Fiddle utilities."""

from typing import Any
import hashlib
import json


def hash_dict(data: dict[str, Any]) -> str:
    serialized = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.md5(serialized.encode()).hexdigest()
