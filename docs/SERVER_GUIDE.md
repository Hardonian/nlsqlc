# nlsqlc Enterprise Server & Microservice Gateway Guide

## Running the Server Daemon

Start the high-performance HTTP gateway daemon:

```sh
python3 tools/server.py --host 0.0.0.0 --port 8080 --schema /etc/nlsql/production.nlschema --policy /etc/nlsql/production.nlpolicy
```

## API Endpoints

### 1. `POST /v1/compile`
Compile Query IR to parameterized SQL.

```sh
curl -X POST http://localhost:8080/v1/compile \
  -H "Content-Type: application/json" \
  -H "X-Client-ID: tenant-123" \
  -d '{
    "ir": "(nlsql 1 (query (from orders o) (select (field (column o total_amount) total)) (limit 10)))",
    "dialect": "postgres"
  }'
```

Response:
```json
{
  "status": "OK",
  "sql": "SELECT \"o\".\"total_amount\" AS \"total\" FROM \"public\".\"orders\" AS \"o\" WHERE \"o\".\"tenant_id\" = $1 LIMIT 10",
  "fingerprint": "12849182390192301",
  "complexity": 4,
  "risk": "LOW",
  "relevance_score": 0.714,
  "duration_ms": 0.45
}
```

### 2. `POST /v1/validate`
Validate Query IR syntax and policy compliance.

```sh
curl -X POST http://localhost:8080/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"ir": "(nlsql 1 (query (from orders o) (select (field (column o id) id))))"}'
```

### 3. `GET /metrics`
Prometheus metrics scrape target.

```sh
curl http://localhost:8080/metrics
```

### 4. `POST /v1/schema/reload`
Hot-reload schema and policy files without restarting the process.

```sh
curl -X POST http://localhost:8080/v1/schema/reload
```
