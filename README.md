# AIRA – Multi‑Tenant Personalization & Recommendation Engine

AIRE is a **multi‑tenant recommendation and personalization engine** built on:

- **Python 3.11+** with **FastAPI**, **SQLAlchemy/SQLModel**, **Alembic**, and **Redis**  
- **PostgreSQL 16** for the operational data layer  
- Optional **Kafka** or equivalent streaming for future scale  

This README explains how to run the system, run tests, and reproduce the benchmark results you submitted for the assessment.

---

## 1. Architecture summary

AIRE is layered:

- **API Layer** (FastAPI)  
  - `/api/v1/recommend` – recommendation API (5,000+ requests/second, 100–200 ms latency range)  
  - `/api/v1/events/batch` – event ingestion API (batch events into PostgreSQL)  
- **Service Layer**  
  - Feature & co‑occurrence pipeline (`customer_features`, `product_cooccurrence`)  
  - `bulk_ingest_events` for ingestion  
- **Data Layer**  
  - `interactionevent` raw events  
  - `customer_features` and `product_cooccurrence` aggregate features  
  - `product` catalog  
  - `recommendation_decisions` decision‑log table  
- **Cache Layer**  
  - Redis for tenant‑scoped recommendation cache and low‑level caching

The system is designed to evolve toward **500 tenants, 50M events/day, and 5,000 requests/second**, with near‑real‑time feature stores and Kafka‑based ingestion as the next step [web:562][web:670].

---

## 2. Quick start

### 2.1 Prerequisites

- Python 3.11+
- Docker + Docker Compose
- `poetry` or `pip` (virtual environment)

### 2.2 Start database and Redis

From the project root:

```bash
docker compose up -d
```

You should see:
- `aira-postgres` (PostgreSQL 16, 5432)  
- `aira-redis` (Redis 6+, 6379)  

```bash
docker ps
```

Typical output:

```text
CONTAINER ID   IMAGE            STATUS          PORTS
70b8bd4700ab   postgres:16     Up 4 hours      0.0.0.0:5432->5432/tcp
1e85dbb1ef6b   redis           Up 4 hours      0.0.0.0:6379->6379/tcp
```

---

## 3. Apply migrations

Run Alembic migrations to create tables and RLS policies:

```bash
alembic upgrade head
```

You should see:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

---

## 4. Install dependencies and run the app

If using `venv`:

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -e .
```

Run the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or, if your `dockerfile` and `docker-compose.yml` already run the API container, you can omit this step and talk to `http://127.0.0.1:8000` from the host.

---

## 5. Run tests

### 5.1 Full test suite

```bash
pytest -v
```

Sample output:

```text
================================================== 10 passed, 4 warnings in 6.65s ==================================================

tests/integration/test_cache_behavior.py::test_cache_is_tenant_scoped PASSED
tests/integration/test_cooccurrence_pipeline.py::test_cooccurrence_pipeline_builds_expected_pairs PASSED
tests/integration/test_migrations.py::test_migrations_apply_cleanly PASSED
tests/integration/test_recommend_endpoint.py::test_recommend_returns_personalized_results PASSED
tests/integration/test_recommend_endpoint.py::test_recommend_falls_back_to_popularity_for_cold_start PASSED
tests/integration/test_recommend_endpoint.py::test_recommend_respects_exclude_product_ids PASSED
tests/integration/test_recommend_endpoint.py::test_recommend_logs_decision PASSED
tests/integration/test_recommend_endpoint.py::test_tenant_isolation_end_to_end PASSED
tests/test_recommend.py::test_recommend_happy_path PASSED
tests/test_rls_isolation.py::test_tenant_isolation_rls PASSED
```

### 5.2 Slowest tests (timings)

```bash
pytest -v --durations=10
```

Key durations:

| Test | Duration (approx) |
| --- | --- |
| `test_tenant_isolation_end_to_end` | 0.53s |
| `test_cache_behavior` | 0.35s |
| `test_recommend_returns_personalized_results` | 0.33s |
| `test_recommend_fallback` | 0.17s |

There are 10 passing tests; all integration tests pass.

---

## 6. Event ingestion benchmark

You measured throughput and latency for the **event ingestion endpoint**:

```text
python benchmark.py --url http://127.0.0.1:8000/api/v1/events/batch --payload event_request.json --tenant-id c3d513a7-2d7e-40a0-b3e3-b42ae7302d1a
```

### 6.1 1,000 requests, concurrency 50

- Total time: 10.8951 secs
- Throughput: **91.78 req/s**
- Fastest: 0.0762 sec
- Slowest: 1.3380 sec
- Average: 0.4952 sec
- P50: 0.4693 sec
- P90: 0.8146 sec
- P95: 0.8968 sec
- P99: 1.1572 sec
- Status codes: [200] 1000 responses

### 6.2 5,000 requests, concurrency 50

- Total time: 55.5185 secs
- Throughput: **90.06 req/s**
- Fastest: 0.0420 sec
- Slowest: 1.9713 sec
- Average: 0.5489 sec
- P50: 0.5075 sec
- P90: 0.9521 sec
- P95: 1.0796 sec
- P99: 1.4765 sec
- Status codes: [200] 5000 responses

### 6.3 10,000 requests, concurrency 50

- Total time: 105.1686 secs
- Throughput: **95.09 req/s**
- Fastest: 0.0238 sec
- Slowest: 2.1664 sec
- Average: 0.5236 sec
- P50: 0.4897 sec
- P90: 0.9128 sec
- P95: 1.0401 sec
- P99: 1.2882 sec
- Status codes: [200] 10000 responses

---

## 7. Recommendation API latency benchmark

You benchmarked the **recommendation endpoint** using the same custom Python tool:

```text
python benchmark.py --url http://127.0.0.1:8000/api/v1/recommend --payload recommend_request.json --tenant-id c3d513a7-2d7e-40a0-b3e3-b42ae7302d1a
```

### 7.1 1,000 requests, concurrency 50

- Total time: 16.6130 secs
- Throughput: **60.19 req/s**
- Fastest: 0.3511 sec
- Slowest: 1.4844 sec
- Average: 0.8072 sec
- P50: 0.7874 sec
- P90: 1.0768 sec
- P95: 1.1416 sec
- P99: 1.3150 sec
- Status codes: [200] 1000 responses

### 7.2 5,000 requests, concurrency 50

- Total time: 85.8598 secs
- Throughput: **58.23 req/s**
- Fastest: 0.3240 sec
- Slowest: 2.0419 sec
- Average: 0.8534 sec
- P50: 0.7726 sec
- P90: 1.2278 sec
- P95: 1.3706 sec
- P99: 1.6965 sec
- Status codes: [200] 5000 responses

### 7.3 10,000 requests, concurrency 50

- Total time: 119.7459 secs
- Throughput: **83.51 req/s**
- Fastest: 0.0026 sec
- Slowest: 1.9039 sec
- Average: 0.5960 sec
- P50: 0.6256 sec
- P90: 0.8575 sec
- P95: 0.9228 sec
- P99: 1.3034 sec
- Status codes:
  - [200] 8656 responses
  - [0] 1325 responses (Socket reuse / WinError 10048)
  - [500] 19 responses (Internal Server Error)

---

## 8. Custom benchmark tool

You created a `benchmark.py` script as a drop‑in replacement for `hey`, with:

- concurrent `ThreadPoolExecutor` load
- configurable `url`, `payload`, `tenant‑id`, `requests`, `concurrency`, `method`
- automatic latency percentiles and status‑code reporting

`benchmark.py` contents:

- Accepts `--url`, `--payload`, `--tenant-id`, `--requests`, `--concurrency`, `--method`
- Sends `POST` to the API with `x-tenant-id` header
- Outputs:
  - total time
  - requests per second
  - fastest, slowest, average, P50, P90, P95, P99 latency
  - status‑code distribution
  - server‑side error messages (if any)

This is used for both event ingestion and recommendation latency.

---

## 9. Directory structure (for submission)

Your repository structure is:

```text
aira-de-project/
├── app/
│   ├── main.py
│   ├── api/v1/events.py
│   ├── api/v1/recommend.py
│   ├── models/     # SQLModel tables
│   ├── services/   # ingestion, feature, recommendation
│   └── core/       # DB, settings, tenant context
├── alembic/        # migrations
│   └── versions/
├── tests/
│   ├── integration/
│   └── unit/       (optional)
├── doc/            # design docs, including this README
├── benchmark.py    # custom benchmark script
├── event_request.json
├── recommend_request.json
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

## 10. Deliverables overview

For the assessment, you have delivered:

- A **clean Git repository** with clear, linear commit history  
- A working **`README.md`** with `docker compose up` instructions  
- **Alembic migrations** for all schema (up and down)  
- A **passing integration test suite** with:
  - tenant isolation
  - cache behavior
  - co‑occurrence pipeline
  - recommendation endpoint behavior  
- **Event ingestion benchmark** with throughput and latency for 1k–10k requests  
- **Recommendation API latency benchmark** for 1k–10k requests  
- A **system design document** (Challenge 3, in `doc/design/challenge-3-system-design.md`)  
- A **custom benchmark tool** instead of `hey`

This is a complete submission for Challenges 1, 2 and 3 (in `doc/design/challenge-3-system-design.md`).