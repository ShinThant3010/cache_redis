from typing import Any

from pydantic import BaseModel, Field


class SetOneRequest(BaseModel):
    id: str
    data: dict[str, Any]
    ttl_seconds: int | None = Field(default=None, ge=1)


class SetOneResponse(BaseModel):
    success: bool


class SetManyRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    id_field: str = "id"
    ttl_seconds: int | None = Field(default=None, ge=1)
    key_prefix: str | None = None


class SetManyResponse(BaseModel):
    count: int

class LoadFromBigQueryRequest(BaseModel):
    table_path: str = Field(description="project.dataset.table")
    id_field: str = "id"
    where_clause: str | None = None
    ttl_seconds: int | None = Field(default=None, ge=1)
    key_prefix: str | None = None


class LoadFromBigQueryResponse(BaseModel):
    count: int


class GetOneResponse(BaseModel):
    id: str
    data: dict[str, Any] | None


class GetManyRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class GetManyResponse(BaseModel):
    items: dict[str, dict[str, Any] | None]


class DeleteOneResponse(BaseModel):
    id: str
    deleted: bool


class DeleteByPrefixResponse(BaseModel):
    cache_prefix: str
    deleted_count: int


class CachedIDsResponse(BaseModel):
    ids: list[str]


class ClearCacheResponse(BaseModel):
    cleared: int
