from time import perf_counter

from fastapi import FastAPI, HTTPException, Query

from api.schema import (
    CachedIDsResponse,
    CacheMemoryUsageResponse,
    ClearCacheResponse,
    DeleteByPrefixResponse,
    GetManyResponse,
    GetOneResponse,
    DeleteOneResponse,
    LoadFromBigQueryRequest,
    LoadFromBigQueryResponse,
    SetManyRequest,
    SetManyResponse,
    SetOneRequest,
    SetOneResponse,
)
from functions.cache import (
    clear_all,
    delete_by_prefix,
    delete_one,
    get_cached_ids,
    get_id_count,
    get_many,
    get_one,
    get_used_memory_mb,
    get_used_memory_size,
    set_many,
    set_many_bigquery_data,
    set_one,
)


app = FastAPI(
    title="Cache Redis API",
    version="0.1.0",
    openapi_tags=[
        {"name": "Set", "description": "Write data into Redis cache."},
        {"name": "Get", "description": "Read data from Redis cache."},
    ],
)


@app.middleware("http")
async def add_runtime_header(request, call_next):
    start = perf_counter()
    response = await call_next(request)
    elapsed_ms = (perf_counter() - start) * 1000
    response.headers["x-runtime-respone"] = f"{elapsed_ms:.2f}ms"
    return response


@app.post("/cache/set-one", response_model=SetOneResponse, tags=["Set"])
def cache_set_one(payload: SetOneRequest) -> SetOneResponse:
    success = set_one(payload.id, payload.data, ttl_seconds=payload.ttl_seconds)
    return SetOneResponse(success=success)


@app.post("/cache/set-many", response_model=SetManyResponse, tags=["Set"])
def cache_set_many(payload: SetManyRequest) -> SetManyResponse:
    try:
        count = set_many(
            payload.items,
            id_field=payload.id_field,
            ttl_seconds=payload.ttl_seconds,
            key_prefix=payload.key_prefix,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Missing id field in item: {payload.id_field}") from exc
    return SetManyResponse(count=count)


@app.post("/cache/set-many-bigquery", response_model=LoadFromBigQueryResponse, tags=["Set"])
def cache_set_many_bigquery(payload: LoadFromBigQueryRequest) -> LoadFromBigQueryResponse:
    count = set_many_bigquery_data(
        table_path=payload.table_path,
        id_field=payload.id_field,
        where_clause=payload.where_clause,
        ttl_seconds=payload.ttl_seconds,
        key_prefix=payload.key_prefix,
    )
    return LoadFromBigQueryResponse(count=count)

@app.get("/cache/get-one/{item_id}", response_model=GetOneResponse, tags=["Get"])
def cache_get_one(item_id: str) -> GetOneResponse:
    data = get_one(item_id)
    return GetOneResponse(id=item_id, data=data)


@app.get("/cache/get-many", response_model=GetManyResponse, tags=["Get"])
def cache_get_many(ids: list[str] = Query(default_factory=list)) -> GetManyResponse:
    items = get_many(ids)
    return GetManyResponse(items=items, id_count=len(items))


@app.delete("/cache/delete-one/{item_id}", response_model=DeleteOneResponse, tags=["Set"])
def cache_delete_one(item_id: str) -> DeleteOneResponse:
    return DeleteOneResponse(id=item_id, deleted=delete_one(item_id))


@app.delete("/cache/delete-prefix/{cache_prefix}", response_model=DeleteByPrefixResponse, tags=["Set"])
def cache_delete_prefix(cache_prefix: str) -> DeleteByPrefixResponse:
    deleted_count = delete_by_prefix(cache_prefix=cache_prefix)
    return DeleteByPrefixResponse(cache_prefix=cache_prefix, deleted_count=deleted_count)


@app.get("/cache/get-many-by-prefix", response_model=CachedIDsResponse, tags=["Get"])
def cache_get_many_by_prefix(cache_prefix: str) -> CachedIDsResponse:
    ids = get_cached_ids(cache_prefix=cache_prefix)
    return CachedIDsResponse(ids=ids, id_count=len(ids))


@app.delete("/cache/clear-all", response_model=ClearCacheResponse, tags=["Set"])
def cache_clear_all() -> ClearCacheResponse:
    return ClearCacheResponse(cleared=clear_all())


@app.get("/cache/memory-usage", response_model=CacheMemoryUsageResponse, tags=["Get"])
def cache_memory_usage() -> CacheMemoryUsageResponse:
    return CacheMemoryUsageResponse(
        used_memory_bytes=get_used_memory_size(),
        used_memory_mb=get_used_memory_mb(),
        id_count=get_id_count(),
    )
