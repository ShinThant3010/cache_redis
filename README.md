# Cache Redis API

FastAPI service for loading and serving cached JSON objects from Redis, with optional bulk loading from BigQuery.

## 1. What this service does

This service exposes REST endpoints to:
- write one or many records into Redis
- read one or many records from Redis
- list/delete keys by prefix
- clear all keys in the selected Redis database
- report Redis memory usage and key count
- load records from BigQuery and cache them in Redis

Typical use case: pre-load recommendation data into Redis and retrieve it with low latency by key.

## 2. High-level flow

1. Client sends data directly (`/cache/set-one`, `/cache/set-many`) or requests BigQuery ingestion (`/cache/set-many-bigquery`).
2. Service serializes records to JSON strings and writes to Redis.
3. Clients read cached records through single or bulk read endpoints.
4. Operators use prefix/memory/clear endpoints for maintenance and visibility.

## 3. Data & Dependencies

### Data
- Redis values are JSON strings generated from Python dictionaries.
- BigQuery ingestion reads `SELECT * FROM project.dataset.table` with optional `WHERE` clause.

### External dependencies
- Redis (local Redis or GCP Memorystore for Redis).
- BigQuery (only required for `/cache/set-many-bigquery`).
- Service-account credentials for BigQuery access.

## 4. Tech Stack

- Python 3.11+
- FastAPI + Uvicorn
- `redis` Python client
- `google-cloud-bigquery`
- Dependency/runtime management with `uv`

## 5. Prerequisites & Access

- Python 3.11+ installed.
- Reachable Redis endpoint (`REDISHOST`, `REDISPORT`).
- For BigQuery ingestion:
  - `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service-account JSON file.
  - Service account has BigQuery read access.
- For Cloud Run deployment:
  - Cloud Run service has network path to Redis (VPC connector).

## 6. Local setup

Install dependencies:

Option A (`uv`):
```bash
uv sync
```

Option B (`venv` + pip):
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 7. Project Structure

- `main.py`: local entrypoint that runs Uvicorn with reload
- `api/app.py`: FastAPI app, middleware, and route handlers
- `api/schema.py`: Pydantic request/response models
- `functions/cache.py`: Redis + BigQuery logic
- `tests/conftest.py`: shared pytest fixtures and in-memory Redis fake
- `tests/test_cache_functions.py`: unit tests for cache logic
- `tests/test_api.py`: API tests with FastAPI `TestClient`
- `Dockerfile`: container build/runtime
- `cloudbuild.yaml`: Cloud Build pipeline to build, push, and deploy to Cloud Run

## 8. How data is stored in Redis

- Values are JSON strings.
- Keys are:
  - `item_id` directly, or
  - `"{key_prefix}:{item_id}"` when `key_prefix` is provided (bulk flows).
- `ttl_seconds` is optional.
  - `set-one`: uses `SET key value EX ttl` when provided.
  - `set-many`: uses `MSET` without TTL, or pipeline `SET ... EX ttl` with TTL.

## 9. API Contract

### 9.1 API Endpoints

Write operations:
- `POST /cache/set-one`
- `POST /cache/set-many`
- `POST /cache/set-many-bigquery`
- `DELETE /cache/delete-one/{item_id}`
- `DELETE /cache/delete-prefix/{cache_prefix}`
- `DELETE /cache/clear-all`

Read operations:
- `GET /cache/get-one/{item_id}`
- `POST /cache/get-many`
- `GET /cache/get-many-by-prefix?cache_prefix=...`
- `GET /cache/memory-usage`

### 9.2 Example - Request, Response

`POST /cache/set-one`

Request:

```json
{
  "id": "abc123",
  "data": {"name": "alpha"},
  "ttl_seconds": 3600
}
```

Response:

```json
{"success": true}
```

`POST /cache/set-many`

Request:

```json
{
  "items": [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}],
  "id_field": "id",
  "ttl_seconds": 45,
  "key_prefix": "user"
}
```

Response:

```json
{"count": 2}
```

`POST /cache/set-many-bigquery`

Request:

```json
{
  "table_path": "project.dataset.table",
  "id_field": "id",
  "where_clause": "active = true",
  "ttl_seconds": 90,
  "key_prefix": "usr"
}
```

Response:

```json
{"count": 2}
```

`DELETE /cache/delete-one/{item_id}`

Request:
- Path param: `item_id=item-1`
- Body: none

Response:

```json
{"id": "item-1", "deleted": true}
```

`DELETE /cache/delete-prefix/{cache_prefix}`

Request:
- Path param: `cache_prefix=user`
- Body: none

Response:

```json
{"cache_prefix": "user", "deleted_count": 2}
```

`DELETE /cache/clear-all`

Request:
- Body: none

Response:

```json
{"cleared": 2}
```

`GET /cache/get-one/{item_id}`

Request:
- Path param: `item_id=abc123`
- Body: none

Response:

```json
{"id": "abc123", "data": {"name": "alpha"}}
```

`POST /cache/get-many`

Request:
- Body:

```json
{"ids": ["TH_UNI_041", "TH_UNI_042"]}
```

Response:

```json
{
  "id_count": 2,
  "items": {
    "user:1": {"id": "1", "name": "a"},
    "user:2": {"id": "2", "name": "b"}
  }
}
```

`GET /cache/get-many-by-prefix?cache_prefix=...`

Request:
- Query param: `cache_prefix=user`
- Body: none

Response:

```json
{"id_count": 2, "ids": ["user:1", "user:2"]}
```

`GET /cache/memory-usage`

Request:
- Body: none

Response:

```json
{"used_memory_bytes": 12345, "used_memory_mb": 0.01, "id_count": 42}
```

### 9.3 Error Handling & Status Codes

- `200 OK`: successful read/write/delete/memory operations.
- `400 Bad Request`:
  - `POST /cache/set-many` when `id_field` is missing in one or more items.
- `422 Unprocessable Entity`:
  - request validation errors from FastAPI/Pydantic (e.g., invalid types, invalid `ttl_seconds` value).
- `500 Internal Server Error`:
  - unhandled runtime errors (e.g., Redis/BigQuery connectivity failures).

## 10. Configuration (config.yaml, env vars)

### `config.yaml`

- Current status: no `config.yaml` is used by application code.

### Environment variables

- `REDISHOST` (default: `localhost`)
- `REDISPORT` (required in practice; should be numeric, e.g. `6379`)
- `GOOGLE_APPLICATION_CREDENTIALS` (required for BigQuery ingestion)

Example `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
REDISHOST=127.0.0.1
REDISPORT=6379
```

## 11. Testing (pytest)

Run unit + API tests:

```bash
pytest -q
```

If `pytest` is missing:

```bash
uv add --dev pytest
pytest -q
```

## 12. Build & Deploy to Cloud Run (Cloud Build)

`cloudbuild.yaml` pipeline:
1. Build Docker image
2. Push image to Artifact Registry
3. Deploy to Cloud Run

Run:

```bash
gcloud builds submit
```

Default substitutions in `cloudbuild.yaml`:
- `_REGION=asia-southeast1`
- `_REPO_NAME=hyde-cache-pipeline-api`
- `_VPC_CONNECTOR_NAME=redis-test-connector`
- `_SA_NAME=test-result-data-api-sa`

Deployed endpoint (current):
- Base URL: `https://hyde-cache-pipeline-api-810737581373.asia-southeast1.run.app`
- Swagger: `https://hyde-cache-pipeline-api-810737581373.asia-southeast1.run.app/docs`

## 13. Observability

Current observability features:
- Per-request runtime response header: `x-runtime-respone` (current key spelling in code).
- Memory and key-count endpoint: `GET /cache/memory-usage`.

Not currently included in repo:
- Structured logging guidance.
- Dashboards/alerts/runbooks.

## 14. Common Troubleshootings

- `ValueError` on startup/request due to `REDISPORT`: set `REDISPORT` explicitly to numeric value.
- BigQuery endpoint fails with auth errors: verify `GOOGLE_APPLICATION_CREDENTIALS` and IAM permissions.
- Cloud Run cannot reach Redis: verify VPC connector and network path.
- Prefix operations return empty: verify keys were written with matching prefix format (`prefix:id`).

## 15. Important implementation details

- Runtime header name is `x-runtime-respone` (typo retained in current code).
- `set-one` and `get-one` operate on exact raw key IDs.
- Prefix behavior is primarily in bulk operations and prefix helper endpoints.

## 16. Known Limitations / Assumptions

- No built-in authentication/authorization at application layer.
- No `config.yaml` support in current code.
- `where_clause` is directly interpolated into SQL string (caller must pass trusted input).

## 17. Versioning / Change Log

Current API metadata version in app: `0.1.0`.

Change log:
- `2026-03-09`: README restructured with API contract, data dependencies, troubleshooting, performance, limitations, and verification flow sections.

## 18. Quick verification flow

1. `POST /cache/set-one`
2. `GET /cache/get-one/{id}`
3. `GET /cache/memory-usage`
4. `DELETE /cache/delete-one/{id}`
5. `pytest -q`
