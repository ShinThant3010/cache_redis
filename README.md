# Cache Redis API

FastAPI service for loading and serving cached JSON objects from Redis, with optional bulk loading from BigQuery.

## What this project does

This service exposes REST endpoints to:
- write one or many records into Redis
- read one or many records from Redis
- list/delete keys by prefix
- clear all keys in the selected Redis database
- report Redis memory usage and key count
- load records from BigQuery and cache them in Redis

Typical use case: pre-load recommendation data into Redis and retrieve it with low latency by key.

## Tech stack

- Python 3.11+
- FastAPI + Uvicorn
- GCP Memorystore for Redis (`redis` Python client)
- Google BigQuery (`google-cloud-bigquery`)
- Dependency/runtime management via `uv`

## Project structure

- `main.py`: local entrypoint that runs Uvicorn
- `api/app.py`: FastAPI app and route handlers
- `api/schema.py`: Pydantic request/response models
- `functions/cache.py`: Redis + BigQuery logic
- `tests/conftest.py`: shared pytest fixtures (in-memory Redis fake)
- `tests/test_cache_functions.py`: unit tests for core cache logic
- `tests/test_api.py`: API endpoint tests with FastAPI `TestClient`
- `Dockerfile`: container image build/runtime
- `cloudbuild.yaml`: Cloud Build pipeline to build, push, and deploy to Cloud Run

## How data is stored in Redis

- Values are JSON strings (serialized from Python dicts).
- Keys are:
  - `item_id` directly, or
  - `"{key_prefix}:{item_id}"` when a prefix is provided (bulk endpoints only)
- `ttl_seconds` is optional. If provided, each key gets expiration.

## Environment variables

Current code reads these variable names:

- `REDISHOST` (default: `localhost`)
- `REDISPORT` (required in practice; should be numeric, e.g. `6379`)
- `GOOGLE_APPLICATION_CREDENTIALS` (required for BigQuery load endpoint)

Example `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/service-account.json"
REDISHOST=127.0.0.1
REDISPORT=6379
```

## Local development

### 1. Install dependencies

```bash
uv sync
```

### 2. Run the API

```bash
uv run python main.py
```

### 3. Open API docs (local)

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 4. Run tests

```bash
pytest -q
```

If `pytest` is missing:

```bash
uv add --dev pytest
pytest -q
```

## Deployed service (Cloud Run)

- API base URL: `https://hyde-cache-pipeline-api-810737581373.asia-southeast1.run.app`
- Swagger UI: `https://hyde-cache-pipeline-api-810737581373.asia-southeast1.run.app/docs`

## API endpoints

### Write operations

- `POST /cache/set-one`
  - Body: `{ "id": "...", "data": { ... }, "ttl_seconds": 3600 }`
  - Stores one key/value.

- `POST /cache/set-many`
  - Body includes `items`, optional `id_field`, optional `ttl_seconds`, optional `key_prefix`
  - Stores many records in bulk.

- `POST /cache/set-many-bigquery`
  - Body includes `table_path`, optional `id_field`, optional `where_clause`, optional `ttl_seconds`, optional `key_prefix`
  - Reads rows from BigQuery and caches them via bulk set.

- `DELETE /cache/delete-one/{item_id}`
  - Deletes a single key.

- `DELETE /cache/delete-prefix/{cache_prefix}`
  - Deletes all keys matching `{cache_prefix}:*`.

- `DELETE /cache/clear-all`
  - Flushes the current Redis DB.

### Read operations

- `GET /cache/get-one/{item_id}`
  - Returns one cached JSON object (or `null` if missing).

- `GET /cache/get-many?ids=id1&ids=id2`
  - Query param: repeated `ids` values
  - Returns map of key -> object/null.

- `GET /cache/get-many-by-prefix?cache_prefix=...`
  - Returns sorted key list for prefix.

- `GET /cache/memory-usage`
  - Returns memory usage bytes/MB and DB key count.

## BigQuery load behavior

`/cache/set-many-bigquery` builds query as:

```sql
SELECT * FROM `project.dataset.table` [WHERE ...]
```

Notes:
- `table_path` must be in `project.dataset.table` format.
- `where_clause` is appended directly to SQL.
- The service account in `GOOGLE_APPLICATION_CREDENTIALS` needs BigQuery read permissions.

## Cloud Run deployment

`cloudbuild.yaml` pipeline:
1. Build image
2. Push to Artifact Registry
3. Deploy to Cloud Run with VPC connector and service account

Run:

```bash
gcloud builds submit
```

Important deployment requirement: Cloud Run service must have network path to Redis (VPC connector configured).

## Known implementation notes

- Runtime header key is `x-runtime-respone` (typo in header name).
- `set-one`/`get-one` operate on raw key IDs; prefixed key handling is mainly in bulk methods and prefix utilities.
- `REDISPORT` fallback in code is not a valid numeric default, so set `REDISPORT` explicitly.

## Quick verification flow

1. `POST /cache/set-one`
2. `GET /cache/get-one/{id}`
3. `GET /cache/memory-usage`
4. `DELETE /cache/delete-one/{id}`
5. `pytest -q`

If all succeed, core API/cache behavior and serialization paths are working.
