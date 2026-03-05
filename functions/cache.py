import json
import os
from typing import Any

import redis
from google.cloud import bigquery
from fastapi.encoders import jsonable_encoder



def _redis_client() -> redis.Redis:
    host = os.getenv("REDISHOST", "localhost")
    port = int(os.getenv("REDISPORT", "port"))
    return redis.Redis(host=host, port=port, decode_responses=True)


def set_one(item_id: str, payload: dict[str, Any], ttl_seconds: int | None = None) -> bool:
    client = _redis_client()
    return bool(client.set(item_id, json.dumps(jsonable_encoder(payload)), ex=ttl_seconds))


def set_many(
    items: list[dict[str, Any]],
    id_field: str = "id",
    ttl_seconds: int | None = None,
    key_prefix: str | None = None,
) -> int:
    client = _redis_client()
    mapping: dict[str, str] = {}
    for item in items:
        item_id = str(item[id_field])
        cache_key = f"{key_prefix}:{item_id}" if key_prefix else item_id
        mapping[cache_key] = json.dumps(jsonable_encoder(item))
    if not mapping:
        return 0
    if ttl_seconds is None:
        result = client.mset(mapping)
        return len(mapping) if result else 0

    pipe = client.pipeline()
    for key, value in mapping.items():
        pipe.set(key, value, ex=ttl_seconds)
    results = pipe.execute()
    return sum(1 for result in results if result)


def set_many_bigquery_data(
    table_path: str,
    id_field: str = "id",
    where_clause: str | None = None,
    ttl_seconds: int | None = None,
    key_prefix: str | None = None,
) -> int:
    bq_client = bigquery.Client()
    query = f"SELECT * FROM `{table_path}`"
    if where_clause:
        query += f" WHERE {where_clause}"
    rows = list(bq_client.query(query).result())
    items = [dict(row.items()) for row in rows]

    return set_many(
        items,
        id_field=id_field,
        ttl_seconds=ttl_seconds,
        key_prefix=key_prefix,
    )


def get_one(item_id: str) -> dict[str, Any] | None:
    client = _redis_client()
    raw = client.get(item_id)
    if raw is None:
        return None
    return json.loads(raw)


def get_many(item_ids: list[str]) -> dict[str, dict[str, Any] | None]:
    client = _redis_client()
    if not item_ids:
        return {}
    values = client.mget(item_ids)
    output: dict[str, dict[str, Any] | None] = {}
    for item_id, raw in zip(item_ids, values):
        output[item_id] = json.loads(raw) if raw is not None else None
    return output


def delete_one(item_id: str) -> bool:
    client = _redis_client()
    return bool(client.delete(item_id))


def delete_by_prefix(cache_prefix: str) -> int:
    client = _redis_client()
    pattern = f"{cache_prefix}:*"
    keys_to_delete: list[str] = []
    for key in client.scan_iter(match=pattern):
        keys_to_delete.append(key)
    if not keys_to_delete:
        return 0
    return int(client.delete(*keys_to_delete))


def get_cached_ids(cache_prefix: str) -> list[str]:
    client = _redis_client()
    pattern = f"{cache_prefix}:*"
    ids: list[str] = []
    for key in client.scan_iter(match=pattern):
        ids.append(key)
    return sorted(ids)


def clear_all() -> int:
    client = _redis_client()
    cleared = int(client.dbsize())
    client.flushdb()
    return cleared


def get_used_memory_size() -> int:
    client = _redis_client()
    info = client.info("memory")
    return int(info.get("used_memory", 0))


def get_id_count() -> int:
    client = _redis_client()
    return int(client.dbsize())
