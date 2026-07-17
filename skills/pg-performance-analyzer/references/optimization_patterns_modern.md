# PostgreSQL Performance Optimization Patterns

이 문서는 EXPLAIN ANALYZE 결과에서 자주 발견되는 성능 패턴과 최적화 전략을 정리합니다.

## Common Performance Anti-Patterns

### 1. Sequential Scan on Large Tables

**증상:**

- `Seq Scan` 노드가 수천~수만 행 이상 스캔
- WHERE 절이 있음에도 불구하고 전체 테이블 스캔

**원인:**

- 적절한 인덱스 부재
- 인덱스가 있지만 선택도가 낮음 (결과가 테이블의 큰 비율)
- 통계 정보 부족으로 플래너가 잘못된 판단
- 인덱스가 있지만 함수나 표현식 사용으로 인덱스 사용 불가

**해결책:**

```sql
-- 1. 기본 인덱스 생성
CREATE INDEX idx_users_email ON users(email);

-- 2. 부분 인덱스 (조건부)
CREATE INDEX idx_active_users ON users(status)
WHERE status = 'active';

-- 3. 표현식 인덱스
CREATE INDEX idx_users_lower_email ON users(LOWER(email));

-- 4. 통계 갱신
ANALYZE users;

-- 5. 통계 타겟 증가 (기본 100 → 1000)
ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;
ANALYZE users;
```

### 2. Nested Loop with Large Datasets

**증상:**

- `Nested Loop` 노드가 수만~수십만 행 처리
- 내부 루프가 수천 번 반복
- 전체 실행 시간의 큰 비율 차지

**원인:**

- 조인 컬럼에 인덱스 부재
- work_mem이 너무 작아 Hash Join 불가
- 통계 오류로 플래너가 작은 데이터셋 예상

**해결책:**

```sql
-- 1. 조인 컬럼에 인덱스 추가
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- 2. work_mem 증가 (세션 단위)
SET work_mem = '256MB';

-- 3. Hash Join 강제 (테스트 목적)
SET enable_nestloop = off;

-- 4. 다중 컬럼 인덱스로 커버링
CREATE INDEX idx_orders_user_date
ON orders(user_id, created_at)
INCLUDE (amount, status);
```

### 3. Large Hash/Sort Operations

**증상:**

- `Hash` 또는 `Sort` 노드가 디스크로 스필
- "Buckets: X Batches: Y" 에서 Batches > 1
- 임시 파일 생성 경고

**원인:**

- work_mem 설정이 실제 작업량에 비해 부족
- 조인 또는 정렬할 데이터가 예상보다 많음

**해결책:**

```sql
-- 1. work_mem은 해당 쿼리에서만 증가 (트랜잭션 종료 시 자동 복원)
--    work_mem은 쿼리당이 아니라 정렬/해시 "연산마다" 소비될 수 있으므로
--    전역 상향은 동시 세션 x 연산 수만큼 곱해져 메모리 고갈 위험이 있다.
BEGIN;
SET LOCAL work_mem = '256MB';
-- ... 스필이 확인된 쿼리 실행 ...
COMMIT;

-- 2. 쿼리 재작성으로 정렬 제거
-- Before: ORDER BY + LIMIT
SELECT * FROM large_table ORDER BY created_at LIMIT 100;

-- After: 인덱스 활용
CREATE INDEX idx_created_at ON large_table(created_at);
-- 인덱스 스캔으로 이미 정렬되어 있음

-- 3. 서브쿼리로 정렬 범위 축소
SELECT * FROM (
  SELECT * FROM large_table
  WHERE status = 'active'  -- 먼저 필터링
) AS t ORDER BY created_at;
```

### 4. Index Scan with Poor Selectivity

**증상:**

- `Index Scan` 또는 `Index Only Scan` 사용 중
- 하지만 수만 행 이상 읽음
- Seq Scan보다 느림

**원인:**

- 인덱스 선택도가 매우 낮음 (조건에 맞는 행이 전체의 큰 비율)
- 인덱스 스캔 후 테이블 접근 (heap fetch) 비용이 높음
- 잘못된 인덱스 선택

**해결책:**

```sql
-- 1. 선택도 확인
SELECT
  n_distinct,
  (SELECT COUNT(*) FROM users WHERE status = 'active') * 100.0 / COUNT(*)
    AS selectivity_percent
FROM pg_stats
WHERE tablename = 'users' AND attname = 'status';

-- 2. 선택도가 낮으면 Seq Scan이 나음
-- 부분 인덱스로 크기 축소
CREATE INDEX idx_inactive_users ON users(id)
WHERE status = 'inactive';  -- 소수만 해당

-- 3. 커버링 인덱스로 heap fetch 제거
CREATE INDEX idx_users_status_cover
ON users(status)
INCLUDE (name, email, created_at);

-- 4. 복합 조건으로 선택도 향상
CREATE INDEX idx_users_status_date
ON users(status, created_at)
WHERE status = 'active';
```

### 5. Bitmap Heap Scan Inefficiency

**증상:**

- `Bitmap Heap Scan` + `Bitmap Index Scan` 사용
- "Recheck Cond" 비율이 높음
- "Heap Blocks: exact=X lossy=Y"에서 lossy가 많음

**원인:**

- work_mem이 작아 비트맵이 압축됨 (lossy 모드)
- 인덱스로 필터링 후 재검사 비용이 높음

**해결책:**

```sql
-- 1. work_mem 증가
SET work_mem = '256MB';

-- 2. 더 선택적인 인덱스로 변경
-- Before: 단일 컬럼
CREATE INDEX idx_orders_date ON orders(created_at);

-- After: 복합 인덱스
CREATE INDEX idx_orders_date_status
ON orders(created_at, status);

-- 3. 조건 재작성
-- Before: 범위 + 등식
WHERE created_at >= '2024-01-01' AND status = 'completed'

-- After: 등식을 먼저 (선택도 높음)
WHERE status = 'completed' AND created_at >= '2024-01-01'
```

## Query Rewriting Patterns

### Pattern 1: EXISTS vs IN vs JOIN

```sql
-- ❌ 느림: IN with subquery (대량 데이터)
SELECT * FROM orders o
WHERE o.user_id IN (SELECT id FROM users WHERE country = 'US');

-- ✅ 빠름: EXISTS (early termination)
SELECT * FROM orders o
WHERE EXISTS (
  SELECT 1 FROM users u
  WHERE u.id = o.user_id AND u.country = 'US'
);

-- ✅ 빠름: INNER JOIN (적절한 인덱스 있을 때)
SELECT o.* FROM orders o
INNER JOIN users u ON u.id = o.user_id
WHERE u.country = 'US';
```

### Pattern 2: Correlated Subquery → JOIN

```sql
-- ❌ 느림: Correlated subquery
SELECT u.name, (
  SELECT COUNT(*) FROM orders o
  WHERE o.user_id = u.id
) AS order_count
FROM users u;

-- ✅ 빠름: JOIN with GROUP BY
SELECT u.name, COUNT(o.id) AS order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
GROUP BY u.id, u.name;
```

### Pattern 3: UNION ALL > UNION

```sql
-- ❌ 느림: UNION (중복 제거 정렬 필요)
SELECT id, name FROM users WHERE type = 'A'
UNION
SELECT id, name FROM users WHERE type = 'B';

-- ✅ 빠름: UNION ALL (중복 허용)
SELECT id, name FROM users WHERE type = 'A'
UNION ALL
SELECT id, name FROM users WHERE type = 'B';
```

### Pattern 4: LIMIT with ORDER BY

```sql
-- ❌ 느림: 전체 정렬 후 LIMIT
SELECT * FROM large_table
ORDER BY created_at DESC
LIMIT 10;

-- ✅ 빠름: 인덱스 + 커버링
CREATE INDEX idx_created_cover
ON large_table(created_at DESC)
INCLUDE (id, name, status);
-- Top-N heapsort 또는 인덱스 스캔으로 최적화
```

## Statistics and Planner Tuning

### Row Estimation Issues

**통계 업데이트:**

```sql
-- 전체 데이터베이스
ANALYZE;

-- 특정 테이블
ANALYZE users;

-- 통계 타겟 증가 (더 정확한 히스토그램)
ALTER TABLE users ALTER COLUMN email SET STATISTICS 1000;
ANALYZE users;
```

**플래너 힌트 (주의해서 사용):**

```sql
-- Random page cost 조정 (SSD의 경우)
SET random_page_cost = 1.1;  -- 기본값 4.0

-- Effective cache size 증가
SET effective_cache_size = '8GB';

-- CPU 비용 조정
SET cpu_tuple_cost = 0.01;
SET cpu_index_tuple_cost = 0.005;
```

## Configuration Parameters

### Work Memory

```sql
-- 조인, 정렬, 해시 작업용 메모리
SET work_mem = '256MB';  -- 기본 4MB

-- 주의: 동시 연결 수 고려
-- 총 메모리 = work_mem × max_connections × 복잡한 쿼리 당 연산 수
```

### Shared Buffers

```ini
# postgresql.conf
shared_buffers = 4GB  # 시스템 RAM의 25%
```

### Maintenance Work Memory

```sql
-- 인덱스 생성, VACUUM 등
SET maintenance_work_mem = '1GB';  -- 기본 64MB
```

## Monitoring Queries

### Long Running Queries

```sql
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state != 'idle'
  AND query NOT LIKE '%pg_stat_activity%'
ORDER BY duration DESC;
```

### Table Bloat

```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
  pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                 pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Index Usage

```sql
SELECT
  schemaname,
  relname,
  indexrelname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;  -- 사용되지 않는 인덱스 찾기
```

### Cache Hit Ratio

```sql
SELECT
  sum(heap_blks_read) AS heap_read,
  sum(heap_blks_hit) AS heap_hit,
  sum(heap_blks_hit) * 100.0 /
    NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) AS cache_hit_ratio
FROM pg_statio_user_tables;
-- 목표: 99% 이상
```
