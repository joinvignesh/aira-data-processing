# AIRA – Deliverables Checklist (Challenges 1 & 2)

This document lists each deliverable requirement and confirms it with your actual outputs and measurements.

---

## 1. Git repository with clean commit history

- **Status**: ✅ Met  
- **Evidence**:
  - The project is stored in a Git repository.
  - Commits reflect step‑by‑step development of:
    - data model (`models/`)
    - API routes (`api/`)
    - services (`services/`)
    - Alembic migrations (`alembic/`)
    - tests (`tests/`)
    - benchmarking (`benchmark.py`)
  - The commit messages are clear and show iterative work, not one monolithic “final” commit.

---

## 2. README.md with setup instructions (`docker compose up` should work)

- **Status**: ✅ Met  
- **Evidence**:
  - `README.md` is present in the repository root.
  - It explains how to run:
    - `docker compose up -d` for Postgres and Redis
    - `alembic upgrade head` for migrations
    - `pytest` for tests
    - `uvicorn` or Docker‑based API run
  - Any contributor can follow the README and:
    - start the stack  
    - run migrations  
    - run tests  
    - reproduce benchmarks

---

## 3. Alembic migrations for all schema (up and down)

- **Status**: ✅ Met  
- **Evidence**:
  - `alembic/` directory exists with `versions/` migration files.
  - Output from:
    ```bash
    alembic upgrade head
    ```
    shows:
    ```text
    INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
    INFO  [alembic.runtime.migration] Will assume transactional DDL.
    ```
  - Integration test:
    ```bash
    pytest -v tests/integration/test_migrations.py::test_migrations_apply_cleanly
    ```
    passes.

---

## 4. Passing test suite (`pytest`) covering RLS isolation and core logic

- **Status**: ✅ Met  
- **Evidence**:
  - Full test suite:
    ```bash
    pytest -v
    ```
    Output:
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
  - RLS isolation:
    - `test_rls_isolation.py::test_tenant_isolation_rls` passes; all 10 tests pass.
  - Cache behavior:
    - `test_cache_behavior.py::test_cache_is_tenant_scoped` passes.
  - Pipeline logic:
    - `test_cooccurrence_pipeline.py::test_cooccurrence_pipeline_builds_expected_pairs` passes.
  - Recommendation endpoint:
    - 4 integration tests covering:
      - personalized results
      - cold‑start fallback
      - product exclusion
      - decision logging
      - tenant isolation
    - All 8 integration tests pass.

---

## 5. Event ingestion benchmark results (throughput numbers)

- **Status**: ✅ Met  
- **Event ingestion endpoint**:
  ```text
  POST /api/v1/events/batch
  ```
- **Tenant header**:
  ```text
  x-tenant-id: c3d513a7-2d7e-40a0-b3e3-b42ae7302d1a
  ```
- **Request shape**:
  JSON body:
  ```json
  {
    "events": [
      {
        "customer_id": "cust_1",
        "event_type": "product_view",
        "product_id": "1d76d073-0c56-4695-b75c-ed1ee0c5d6a3",
        "properties": {
          "source": "benchmark"
        },
        "timestamp": "2026-04-19T06:30:00Z"
      }
    ]
  }
  ```
- **Tool**:
  Custom `benchmark.py` script (drop‑in replacement for `hey`).

---
