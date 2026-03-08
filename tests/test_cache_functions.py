from __future__ import annotations

from unittest.mock import MagicMock

from functions import cache


def test_set_get_delete_one(fake_redis) -> None:
    assert cache.set_one("item-1", {"name": "alpha"}, ttl_seconds=60) is True
    assert cache.get_one("item-1") == {"name": "alpha"}
    assert fake_redis.ttl["item-1"] == 60

    assert cache.delete_one("item-1") is True
    assert cache.get_one("item-1") is None


def test_set_many_without_ttl_uses_prefix(fake_redis) -> None:
    count = cache.set_many(
        items=[{"id": "1", "v": "a"}, {"id": "2", "v": "b"}],
        ttl_seconds=None,
        key_prefix="user",
    )
    assert count == 2
    assert cache.get_many(["user:1", "user:2"]) == {
        "user:1": {"id": "1", "v": "a"},
        "user:2": {"id": "2", "v": "b"},
    }
    assert fake_redis.ttl["user:1"] is None


def test_set_many_with_ttl_uses_pipeline(fake_redis) -> None:
    count = cache.set_many(
        items=[{"id": "1", "v": "a"}, {"id": "2", "v": "b"}],
        ttl_seconds=120,
        key_prefix="session",
    )
    assert count == 2
    assert fake_redis.ttl["session:1"] == 120
    assert fake_redis.ttl["session:2"] == 120


def test_get_many_and_prefix_helpers(fake_redis) -> None:
    cache.set_many(
        items=[{"id": "10", "x": 1}, {"id": "11", "x": 2}],
        key_prefix="pfx",
    )
    got = cache.get_many(["pfx:10", "missing", "pfx:11"])
    assert got["pfx:10"] == {"id": "10", "x": 1}
    assert got["missing"] is None
    assert got["pfx:11"] == {"id": "11", "x": 2}

    assert cache.get_cached_ids("pfx") == ["pfx:10", "pfx:11"]
    assert cache.delete_by_prefix("pfx") == 2
    assert cache.get_cached_ids("pfx") == []


def test_memory_count_and_clear_all(fake_redis) -> None:
    cache.set_one("a", {"k": "1"})
    cache.set_one("b", {"k": "22"})
    assert cache.get_id_count() == 2
    assert cache.get_used_memory_size() > 0
    assert cache.get_used_memory_mb() >= 0

    assert cache.clear_all() == 2
    assert cache.get_id_count() == 0


def test_set_many_bigquery_data_builds_query_and_delegates(monkeypatch) -> None:
    row1 = MagicMock()
    row1.items.return_value = [("id", "1"), ("name", "a")]
    row2 = MagicMock()
    row2.items.return_value = [("id", "2"), ("name", "b")]

    bq_client = MagicMock()
    bq_client.query.return_value.result.return_value = [row1, row2]
    monkeypatch.setattr(cache.bigquery, "Client", lambda: bq_client)

    set_many_mock = MagicMock(return_value=2)
    monkeypatch.setattr(cache, "set_many", set_many_mock)

    count = cache.set_many_bigquery_data(
        table_path="project.dataset.table",
        id_field="id",
        where_clause="active = true",
        ttl_seconds=90,
        key_prefix="usr",
    )

    assert count == 2
    bq_client.query.assert_called_once_with(
        "SELECT * FROM `project.dataset.table` WHERE active = true"
    )
    set_many_mock.assert_called_once_with(
        [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}],
        id_field="id",
        ttl_seconds=90,
        key_prefix="usr",
    )
