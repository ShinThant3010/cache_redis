from __future__ import annotations

import fnmatch
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from functions import cache


class FakePipeline:
    def __init__(self, client: FakeRedis) -> None:
        self.client = client
        self.ops: list[tuple[str, str, int | None]] = []

    def set(self, key: str, value: str, ex: int | None = None) -> FakePipeline:
        self.ops.append((key, value, ex))
        return self

    def execute(self) -> list[bool]:
        results: list[bool] = []
        for key, value, ex in self.ops:
            results.append(self.client.set(key, value, ex=ex))
        return results


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttl: dict[str, int | None] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        self.ttl[key] = ex
        return True

    def mset(self, mapping: dict[str, str]) -> bool:
        for key, value in mapping.items():
            self.store[key] = value
            self.ttl[key] = None
        return True

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttl.pop(key, None)
                deleted += 1
        return deleted

    def scan_iter(self, match: str) -> Iterator[str]:
        for key in list(self.store):
            if fnmatch.fnmatch(key, match):
                yield key

    def dbsize(self) -> int:
        return len(self.store)

    def flushdb(self) -> bool:
        self.store.clear()
        self.ttl.clear()
        return True

    def info(self, section: str) -> dict[str, int]:
        if section != "memory":
            return {}
        bytes_used = sum(len(value.encode("utf-8")) for value in self.store.values())
        return {"used_memory": bytes_used}


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    client = FakeRedis()
    monkeypatch.setattr(cache, "_redis_client", lambda: client)
    return client
