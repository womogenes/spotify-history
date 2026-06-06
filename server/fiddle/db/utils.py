"""PocketBase utilities."""

from typing import Any
import os

import pocketbase

from fiddle.utils import hash_dict


DEFAULT_POCKETBASE_URL = "https://fiddle-db.wfeng.dev"


def resolve_pocketbase_url(url: str | None = None) -> str:
    return url or os.environ.get("PB_URL") or DEFAULT_POCKETBASE_URL


def pocketbase_client(url: str | None = None) -> pocketbase.Client:
    client = pocketbase.Client(resolve_pocketbase_url(url))
    client.collection("_superusers").auth_with_password(
        username_or_email=os.environ["PB_EMAIL"],
        password=os.environ["PB_PASSWORD"],
    )
    return client


def batch_upsert_records(
    client: pocketbase.Client,
    collection_name: str,
    records: list[dict[str, Any]],
) -> int:
    if not records:
        return 0

    response = client.send(
        "/api/batch",
        {
            "method": "POST",
            "body": {
                "requests": [
                    {
                        "method": "PUT",
                        "url": f"/api/collections/{collection_name}/records",
                        "body": {
                            "id": hash_dict(record),
                            **record,
                        },
                    }
                    for record in records
                ],
            },
        },
    )
    return len(response)
