## Cache Redis Service

Service to:
- Read rows from a BigQuery table
- Convert each row to JSON
- Use the `id` column (or custom id field) as the cache key
- Save and read from Memorystore Redis

## Structure

- `api/app.py`: FastAPI application and endpoints
- `api/schema.py`: Request/response schemas
- `functions/cache.py`: Cache functions and BigQuery loader
- `main.py`: Local runner

## Environment variables

- `REDIS_HOST` (default: `localhost`)
- `REDIS_PORT` (default: `6379`)
- `REDIS_DB` (default: `0`)
- `REDIS_PASSWORD` (optional)
- `CACHE_PREFIX` (default: `cache`)
- `GOOGLE_APPLICATION_CREDENTIALS` (for BigQuery auth)

## Run

```bash
uv run python main.py
```

## Endpoints

- `POST /cache/set-one`
- `GET /cache/get-one/{item_id}`
- `POST /cache/set-many`
- `POST /cache/get-many`
- `GET /cache/ids`
- `DELETE /cache/clear-all`
- `POST /cache/load-from-bigquery`
