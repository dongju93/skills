---
name: pg-performance-analyzer
description: PostgreSQL performance analysis and optimization for modern versions (15-18). Use when triaging slow queries with pg_stat_statements, interpreting EXPLAIN (ANALYZE, BUFFERS) output, diagnosing sort/hash spills, bad row estimates, filter waste, or I/O-bound nodes, designing index changes (including PostgreSQL 18 skip-scan trade-offs), reviewing AIO (io_method) and planner settings, or benchmarking a query before/after an optimization. Produces read-only diagnostics and proposed changes with risk and verification notes; never auto-applies DDL or ALTER SYSTEM.
---

# PostgreSQL Performance Analyzer (PostgreSQL 15-18)

느린 쿼리의 **발견 → 진단 → 개선안 설계 → 검증**을 다루는 스킬. 진단은 읽기 전용으로 수행하고, 변경(DDL, 설정)은 근거·위험도·롤백·검증 방법과 함께 **제안만** 한다.

## 원칙

1. **읽기 전용 진단 우선.** `pg_stat_statements`, `pg_stat_user_indexes`, `EXPLAIN` 수집까지는 자유롭게 실행한다. 부속 스크립트는 DB를 변경하지 않는다 (`parse_explain.py`는 DB 접속 자체가 없고, `benchmark_query.py`는 사용자가 파일에 직접 적은 setup SQL만 실행한다).
2. **DDL과 `ALTER SYSTEM`은 자동 실행하지 않는다.** 항상 다음 형식으로 제안한다: 변경 SQL + 근거 메트릭 + 위험도 + 롤백 SQL + 적용 후 검증 SQL.
3. **전후 벤치마크는 같은 측정 방식으로.** 클라이언트 왕복 시간과 서버 보고 시간을 한 표본에 섞지 않는다 (`--timing client|server`).
4. **전역 설정 변경은 환경 정보 확인 후.** RAM, `max_connections`, 워크로드 유형을 모른 채 `work_mem`·autovacuum 전역값을 제안하지 않는다. 쿼리 단위 문제는 `SET LOCAL`부터.
5. **EXPLAIN ANALYZE는 쿼리를 실제 실행한다.** DML 분석 시 트랜잭션으로 감싸 롤백하거나 복제 환경에서 수행한다.

## 워크플로우

### Step 1: 느린 쿼리 식별 (읽기 전용)

```sql
-- 누적 시간 기준 상위 쿼리 (pg_stat_statements 확장 필요)
SELECT query, calls, total_exec_time, mean_exec_time, stddev_exec_time, rows,
       shared_blks_read, temp_blks_written
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;

-- 스필이 잦은 쿼리 (work_mem 후보)
SELECT query, calls, temp_blks_written
FROM pg_stat_statements
WHERE temp_blks_written > 0
ORDER BY temp_blks_written DESC
LIMIT 10;
```

### Step 2: EXPLAIN 수집 및 파싱

```bash
# JSON 포맷으로 수집 (BUFFERS 필수, track_io_timing이 켜져 있으면 I/O 시간도 포함됨)
psql -Atc "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ..." > explain.json

# 파싱 - 병목 노드(배타 시간 기준), 스필, 필터 낭비, 추정 오차를 근거와 함께 보고
python scripts/parse_explain.py explain.json

# stdin도 가능
psql -Atc "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ..." | python scripts/parse_explain.py -

# 시간 소비 상위 노드 개수 조정
python scripts/parse_explain.py explain.json --top 10
```

파서가 감지하는 항목 (모두 출력에 실재하는 메트릭 기반):

- **배타 시간 기준 병목 노드** — 자식 노드 시간을 뺀 시간으로 순위 산정
- **정렬/해시 디스크 스필** — `Sort Method: external merge`, `Hash Batches > 1`, temp blocks
- **필터 낭비** — `Rows Removed by Filter` 비율이 높은 Seq/Index Scan → 인덱스 후보
- **행 수 추정 오차** — 예상/실제 5배 이상 → ANALYZE·확장 통계 후보
- **Index Only Scan의 heap fetch** — visibility map 미갱신 신호
- **Bitmap lossy 블록, 병렬 워커 미달, JIT 과점유, 계획 시간 지배, 트리거 시간**
- **I/O 대기 비중** — `track_io_timing` 활성 시 노드별 I/O 시간
- **플랜에 실재하는 기능 흔적** — `Index Searches`(PG18+), Incremental Sort, Memoize 등

주의: EXPLAIN 출력에는 서버 버전이 없다. 버전 확인은 `SHOW server_version;`으로 직접 한다. 텍스트 포맷 입력도 받지만 분석 범위가 좁으므로 JSON 포맷을 권장한다.

### Step 3: 개선안 설계

증상별 대응은 `references/optimization_patterns_modern.md`, 인덱스 설계는 `references/index_strategies_modern.md`, PG18 AIO는 `references/aio_tuning_pg18.md` 참조.

제안 형식 예시:

```markdown
## 제안: orders.status 부분 인덱스
- 근거: Seq Scan에서 450,000행이 필터로 제거됨 (반환 50,000행), status='active'가 전체의 10%
- 변경: CREATE INDEX CONCURRENTLY idx_orders_active ON orders(id) WHERE status = 'active';
- 위험도: 낮음 (CONCURRENTLY - 쓰기 차단 없음, 실패 시 INVALID 인덱스 정리 필요)
- 롤백: DROP INDEX CONCURRENTLY idx_orders_active;
- 검증: EXPLAIN으로 인덱스 사용 확인 후 benchmark_query.py 전후 비교
```

### Step 4: 벤치마크 검증

```bash
# 단일 쿼리 (기본: 클라이언트 왕복 시간, 서버 버전 자동 표시)
uv run scripts/benchmark_query.py \
  --database mydb --user postgres \
  --query "SELECT * FROM users WHERE email = 'test@example.com'" \
  --iterations 20 --warmup 3

# 서버 보고 시간으로 측정 (매 반복 EXPLAIN ANALYZE - 방식 혼합 없음)
uv run scripts/benchmark_query.py \
  --database mydb --user postgres \
  --query-file query.sql --timing server --iterations 15

# 플랜 저장 (표본과 별도로 수집됨) 후 파서와 연계
uv run scripts/benchmark_query.py \
  --database mydb --user postgres \
  --query "SELECT ..." --plan-output plan.json
python scripts/parse_explain.py plan.json
```

전후 비교 (`pre_setup`/`settings`/`post_cleanup` 지원 — 각 문장은 실행 전 그대로 출력됨):

```json
[
  {
    "name": "Before - single-column index",
    "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
    "pre_setup": ["CREATE INDEX IF NOT EXISTS idx_email ON users(email)"]
  },
  {
    "name": "After - composite index only",
    "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
    "pre_setup": [
      "DROP INDEX IF EXISTS idx_email",
      "CREATE INDEX IF NOT EXISTS idx_status_email ON users(status, email)"
    ],
    "post_cleanup": ["CREATE INDEX IF NOT EXISTS idx_email ON users(email)"],
    "settings": {"work_mem": "64MB"}
  }
]
```

```bash
uv run scripts/benchmark_query.py \
  --database mydb --user postgres \
  --compare-file comparison.json --iterations 20 --json-output
```

- `settings`는 세션 `SET`으로 적용되고 변형이 끝나면 `RESET ALL`로 복원된다. 서버 재시작이 필요한 설정(`io_method` 등)은 세션에서 바꿀 수 없으므로 에러로 보고된다.
- DML 벤치마크는 `--allow-writes` 필수, `--rollback-each` 병용 권장.
- 프로덕션이 아닌 프로덕션 규모 데이터 사본에서 수행한다.

### Step 5: 지속 모니터링 (읽기 전용)

```sql
-- 미사용 인덱스 (제약조건 소속 제외 후 검토)
SELECT schemaname, relname, indexrelname, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;

-- 대기 이벤트 분포
SELECT wait_event_type, wait_event, COUNT(*)
FROM pg_stat_activity
WHERE wait_event IS NOT NULL
GROUP BY 1, 2 ORDER BY 3 DESC;

-- PG18: 진행 중인 비동기 I/O (pg_aios에는 backend_type이 없어 pid로 조인)
SELECT a.backend_type, COUNT(*) AS active_aios
FROM pg_aios io JOIN pg_stat_activity a USING (pid)
GROUP BY a.backend_type;
```

## 버전별 성능 기능 요약 (정확성 우선)

| 버전 | 주요 성능 기능 | 활용 방법 |
| --- | --- | --- |
| 15 | 정렬 알고리즘 개선, `MERGE` | 자동 적용. 별도 설정 없음 |
| 16 | SIMD 가속(ASCII/JSON), Hash 인덱스 빌드 개선 | 자동 적용 |
| 17 | VACUUM 메모리 대폭 감소, B-tree IN-list 멀티값 검색, Streaming I/O, `io_combine_limit` | 자동 적용. IN-list는 인덱스만 있으면 됨 |
| 18 | AIO(`io_method`), B-tree Skip Scan, Self-join 제거, OR→배열 변환, 병렬 GIN 빌드, `uuidv7()`, temporal constraint, virtual generated column, `EXPLAIN`의 `Index Searches` | 아래 상세 참조 |

### PG18 기능의 정확한 제어 방법

- **Skip Scan**: 플래너가 비용 기반으로 자동 선택. **`enable_skip_scan` 같은 GUC는 존재하지 않는다.**
- **OR→배열 변환**: 자동. **`enable_or_transformation` GUC는 존재하지 않는다.**
- **Self-join 제거**: `enable_self_join_elimination` (기본 `on`) — PG18에서 유일하게 추가된 이 계열 플래너 GUC.
- **AIO**: `io_method`(`sync`/`worker`/`io_uring`)는 **postmaster 컨텍스트 — 서버 재시작 필요. `pg_reload_conf()`로는 적용되지 않는다.** `io_workers`는 reload로 변경 가능, `io_combine_limit`은 세션 `SET` 가능. 상세는 `references/aio_tuning_pg18.md`.
- **EXPLAIN `Index Searches: N`**: 인덱스 하강 횟수. IN-list·skip scan 효율 확인에 사용 (parse_explain.py가 감지).

### Skip Scan 판단 절차 (인덱스 통합 전 필수)

Skip scan은 `(a, b)` 인덱스에서 선두 컬럼 `a` 없이 `WHERE b = ...`를 처리할 수 있게 하지만, **`a`의 distinct 값 수만큼 인덱스를 반복 하강**한다. `a`의 카디널리티가 크면 사실상 전체 인덱스 스캔이 되어 단일 인덱스보다 훨씬 느리다.

```sql
-- 1. 선두 컬럼 카디널리티 확인 (수십 이하일 때만 skip scan 후보)
SELECT attname, n_distinct FROM pg_stats
WHERE tablename = 'users' AND attname = 'status';

-- 2. 실제 플랜과 Index Searches 확인
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM users WHERE email = 'x@example.com';
-- Index Searches가 n_distinct(status) 수준이면 skip scan 동작 중

-- 3. 단일 컬럼 인덱스 삭제는 벤치마크로 동등 성능 확인 후에만.
--    쓰기 감소 이득 < 조회 회귀 위험이면 유지한다.
```

## 설정 튜닝 가이드 (안전 순서)

### work_mem — 전역 상향 금지, 증거 기반 단계 적용

`work_mem`은 **쿼리당이 아니라 정렬/해시 연산마다, 세션마다** 소비될 수 있다. 전역 128MB는 `연산 수 × 동시 세션` 배수로 곱해져 메모리 고갈을 일으킬 수 있다.

```sql
-- 1단계: 스필 증거 확인 (parse_explain.py의 sort/hash spill 이슈, pg_stat_statements.temp_blks_written)
-- 2단계: 해당 쿼리/트랜잭션에서만
BEGIN;
SET LOCAL work_mem = '256MB';
-- ... 문제 쿼리 ...
COMMIT;
-- 3단계: 특정 롤/유저 단위
ALTER ROLE reporting_user SET work_mem = '64MB';
-- 4단계(최후): 전역 - RAM, max_connections, 워크로드 확인 후에만 제안
```

### 플래너 비용 파라미터 (SSD 환경)

```sql
-- 세션에서 효과 확인 후 전역 반영 제안
SET random_page_cost = 1.1;          -- 기본 4.0은 HDD 가정
SET effective_cache_size = '<RAM의 50-75%>';
```

### autovacuum — 전역이 아닌 테이블 단위부터

```sql
-- 변경이 잦은 특정 테이블만 조정 (전역 scale_factor 변경보다 안전)
ALTER TABLE hot_table SET (autovacuum_vacuum_scale_factor = 0.05);
-- PG17+는 VACUUM 메모리 효율이 크게 개선되어 더 빈번한 실행의 비용이 낮다
```

### AIO (PG18) — 재시작 계획과 함께 제안

```sql
-- io_method 변경은 재시작이 필요하므로 유지보수 윈도우에 계획한다
ALTER SYSTEM SET io_method = 'io_uring';   -- Linux 5.1+, 그 외 플랫폼은 'worker'
-- 적용: 서버 재시작 (pg_reload_conf()로는 적용 안 됨)
-- 확인: SHOW io_method;

-- 재시작 없이 조정 가능한 것들
ALTER SYSTEM SET io_workers = 8;           -- reload로 적용 (io_method='worker'일 때만 유효)
SELECT pg_reload_conf();
SET io_combine_limit = '256kB';            -- 세션 단위 (io_max_combine_limit로 상한 제한됨)
SET effective_io_concurrency = 200;        -- 세션/테이블스페이스 단위로 벤치마크 후 결정
```

## Quick Reference

```bash
# EXPLAIN 분석 (파일 또는 stdin, DB 접속 없음)
python scripts/parse_explain.py explain.json [--top N]

# 벤치마크 (서버 버전 자동 감지·표시)
uv run scripts/benchmark_query.py --database <db> --user <user> \
  --query "<sql>" [--timing client|server] [--plan-output plan.json]

# 전후 비교
uv run scripts/benchmark_query.py --database <db> --user <user> \
  --compare-file comparison.json [--json-output]
```

참조 문서:

- `references/optimization_patterns_modern.md` — 증상별 최적화 패턴, 쿼리 재작성
- `references/index_strategies_modern.md` — 인덱스 타입/설계, skip scan 시대의 인덱스 통합 기준
- `references/aio_tuning_pg18.md` — AIO 설정 컨텍스트(재시작/reload/세션), 워크로드별 시작값

## 의존성

- `parse_explain.py`: 표준 라이브러리만 사용 (Python 3.10+)
- `benchmark_query.py`: PEP 723 인라인 메타데이터 포함 — `uv run scripts/benchmark_query.py ...`로 실행하면 psycopg2가 자동 준비된다. uv가 없으면 `pip install psycopg2-binary`
- DB 확장: `CREATE EXTENSION pg_stat_statements;` (Step 1에 필요)

## 스킬 범위

이 스킬은 **성능 문제의 발견과 검증**에 집중한다. 스키마 설계, 안전한 마이그레이션 절차(잠금 수준, `NOT VALID`, 배치 백필), TimescaleDB 하이퍼테이블은 [timescale/pg-aiguide](https://github.com/timescale/pg-aiguide)의 `postgres` 스킬이 더 적합하다 — 저장소 README의 스킬 선택 가이드 참조.
