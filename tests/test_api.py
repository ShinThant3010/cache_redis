from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_set_get_many_and_runtime_header(fake_redis) -> None:
    set_resp = client.post(
        "/cache/set-many",
        json={
            "items": [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}],
            "id_field": "id",
            "key_prefix": "user",
            "ttl_seconds": 45,
        },
    )
    assert set_resp.status_code == 200
    assert set_resp.json() == {"count": 2}
    assert "x-runtime-respone" in set_resp.headers

    get_resp = client.post("/cache/get-many", json={"ids": ["user:1", "user:2"]})
    assert get_resp.status_code == 200
    assert get_resp.json() == {
        "id_count": 2,
        "items": {
            "user:1": {"id": "1", "name": "a"},
            "user:2": {"id": "2", "name": "b"},
        },
    }


def test_get_many_requires_wrapped_ids_body(fake_redis) -> None:
    client.post("/cache/set-one", json={"id": "TH_UNI_041", "data": {"name": "a"}})
    client.post("/cache/set-one", json={"id": "TH_UNI_042", "data": {"name": "b"}})

    response = client.post("/cache/get-many", json=["TH_UNI_041", "TH_UNI_042"])

    assert response.status_code == 422


def test_set_many_missing_id_field_returns_400(fake_redis) -> None:
    response = client.post(
        "/cache/set-many",
        json={"items": [{"wrong_id": "x", "name": "nope"}], "id_field": "id"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Missing id field in item: id"


def test_get_many_by_prefix_and_clear_all(fake_redis) -> None:
    client.post("/cache/set-one", json={"id": "abc:1", "data": {"a": 1}})
    client.post("/cache/set-one", json={"id": "abc:2", "data": {"a": 2}})

    ids_resp = client.get("/cache/get-many-by-prefix", params={"cache_prefix": "abc"})
    assert ids_resp.status_code == 200
    assert ids_resp.json() == {"id_count": 2, "ids": ["abc:1", "abc:2"]}

    clear_resp = client.delete("/cache/clear-all")
    assert clear_resp.status_code == 200
    assert clear_resp.json() == {"cleared": 2}


def test_set_many_bigquery_endpoint_delegates(monkeypatch) -> None:
    monkeypatch.setattr("api.app.set_many_bigquery_data", lambda **_: 5)

    response = client.post(
        "/cache/set-many-bigquery",
        json={
            "table_path": "project.dataset.table",
            "id_field": "id",
            "where_clause": "country = 'TH'",
            "ttl_seconds": 30,
            "key_prefix": "u",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"count": 5}
