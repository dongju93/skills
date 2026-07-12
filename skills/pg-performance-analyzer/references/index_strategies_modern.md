# PostgreSQL Index Strategies

PostgreSQL 인덱스 설계와 최적화를 위한 포괄적인 가이드입니다.

## Index Types Overview

### 1. B-tree Index (Default)

**특징:**
- 가장 일반적인 인덱스 타입
- 등식, 범위 검색, 정렬에 효과적
- 대부분의 데이터 타입 지원

**사용 사례:**
```sql
-- 기본 B-tree
CREATE INDEX idx_users_email ON users(email);

-- 복합 인덱스 (순서 중요!)
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);

-- 내림차순
CREATE INDEX idx_posts_date_desc ON posts(created_at DESC);

-- 표현식 인덱스
CREATE INDEX idx_users_lower_email ON users(LOWER(email));
```

**Best Practices:**
- 선택도가 높은 컬럼 우선 (카디널리티 높음)
- WHERE 절의 컬럼 순서와 동일하게
- 자주 조회되는 컬럼 포함

### 2. Hash Index

**특징:**
- 등식 비교만 지원 (=)
- 범위 검색 불가
- B-tree보다 빠른 등식 검색 (이론상)
- PostgreSQL 10+ WAL 지원

**사용 사례:**
```sql
-- 해시 인덱스
CREATE INDEX idx_users_uuid_hash ON users USING hash(uuid);

-- 주의: 범위 검색 불가
-- WHERE uuid = 'xxx'  ✅
-- WHERE uuid > 'xxx'  ❌
```

**사용 권장:**
- 매우 큰 테이블에서 등식 검색만 필요한 경우
- 일반적으로 B-tree가 더 범용적

### 3. GiST (Generalized Search Tree)

**특징:**
- 기하학적 데이터, 전문 검색, 범위 타입 지원
- 손실 압축 허용
- 확장 가능

**사용 사례:**
```sql
-- 지리 데이터
CREATE INDEX idx_locations_geom ON locations USING gist(geom);

-- 범위 타입
CREATE INDEX idx_events_period ON events USING gist(period);

-- 전문 검색 (tsvector)
CREATE INDEX idx_documents_search ON documents USING gist(search_vector);
```

### 4. GIN (Generalized Inverted Index)

**특징:**
- 배열, JSONB, 전문 검색에 최적
- 읽기 빠름, 쓰기 느림
- 인덱스 크기가 큼

**사용 사례:**
```sql
-- 배열 검색
CREATE INDEX idx_tags_arr ON posts USING gin(tags);

-- JSONB
CREATE INDEX idx_data_jsonb ON documents USING gin(data);

-- JSONB 특정 경로
CREATE INDEX idx_data_path ON documents USING gin((data->'user'->'email'));

-- 전문 검색
CREATE INDEX idx_content_fts ON articles USING gin(to_tsvector('english', content));
```

### 5. BRIN (Block Range Index)

**특징:**
- 매우 큰 테이블에 효과적
- 물리적 순서와 논리적 순서가 일치할 때 최적
- 인덱스 크기 매우 작음
- 범위 검색에 적합

**사용 사례:**
```sql
-- 시계열 데이터 (순차적으로 삽입)
CREATE INDEX idx_logs_timestamp ON logs USING brin(timestamp);

-- 주의: 데이터가 물리적으로 정렬되어야 효과적
-- 삽입 순서와 검색 순서가 일치할 때 사용
```

### 6. SP-GiST (Space-Partitioned GiST)

**특징:**
- 비균형 파티션 데이터 구조
- 전화번호, IP 주소, 텍스트 검색

**사용 사례:**
```sql
-- IP 주소
CREATE INDEX idx_logs_ip ON logs USING spgist(ip_address inet_ops);

-- 텍스트 패턴
CREATE INDEX idx_names_prefix ON users USING spgist(name text_pattern_ops);
```

## Index Design Patterns

### Pattern 1: Covering Index (Index-Only Scan)

**목표:** 테이블 접근 없이 인덱스만으로 쿼리 완료

```sql
-- Before: Index Scan + Heap Fetch
CREATE INDEX idx_orders_user ON orders(user_id);

SELECT user_id, amount, created_at
FROM orders
WHERE user_id = 123;
-- Plan: Index Scan → Heap Fetch (느림)

-- After: Covering Index
CREATE INDEX idx_orders_user_cover 
ON orders(user_id) 
INCLUDE (amount, created_at);

-- Plan: Index Only Scan (빠름)
```

**주의사항:**
- INCLUDE는 PostgreSQL 11+
- VACUUM으로 visibility map 갱신 필요
- 인덱스 크기 증가 고려

### Pattern 2: Partial Index

**목표:** 자주 조회되는 서브셋만 인덱싱

```sql
-- 전체 인덱스 (불필요하게 큼)
CREATE INDEX idx_users_status ON users(status);

-- 부분 인덱스 (작고 빠름)
CREATE INDEX idx_active_users ON users(status) 
WHERE status = 'active';

CREATE INDEX idx_pending_orders ON orders(id)
WHERE status IN ('pending', 'processing');

-- 쿼리는 동일한 조건 사용해야 함
SELECT * FROM users WHERE status = 'active';  -- 인덱스 사용 ✅
SELECT * FROM users WHERE status = 'inactive';  -- 인덱스 사용 ❌
```

**이점:**
- 인덱스 크기 감소
- 유지보수 비용 감소
- 더 나은 캐시 효율

### Pattern 3: Multi-Column Index Order

**원칙:** 선택도 높은 컬럼 → 낮은 컬럼 순서

```sql
-- ❌ 잘못된 순서
CREATE INDEX idx_orders_bad ON orders(status, user_id, created_at);
-- status는 선택도가 낮음 (active, pending 등 몇 개만 존재)

-- ✅ 올바른 순서
CREATE INDEX idx_orders_good ON orders(user_id, created_at, status);
-- user_id가 가장 선택도 높음

-- 선택도 확인
SELECT 
  attname,
  n_distinct,
  correlation
FROM pg_stats
WHERE tablename = 'orders'
ORDER BY abs(n_distinct) DESC;
```

**쿼리 패턴 고려:**
```sql
-- 이 인덱스로...
CREATE INDEX idx_orders_multi ON orders(user_id, status, created_at);

-- 다음 쿼리들이 모두 커버됨:
WHERE user_id = 1                                    ✅
WHERE user_id = 1 AND status = 'active'              ✅
WHERE user_id = 1 AND status = 'active' AND created_at > '2024-01-01'  ✅

-- 하지만 이건 안 됨:
WHERE status = 'active'                              ❌
WHERE created_at > '2024-01-01'                      ❌
WHERE status = 'active' AND created_at > '2024-01-01'  ❌
```

### Pattern 3.5: PG18 Skip Scan과 인덱스 통합 기준

PostgreSQL 18의 B-tree skip scan은 `(a, b)` 복합 인덱스에서 선두 컬럼 `a` 조건 없이
`WHERE b = ...`를 처리할 수 있게 한다. 플래너가 비용 기반으로 자동 선택하며
**켜고 끄는 GUC는 존재하지 않는다.**

**동작 원리와 한계:** skip scan은 `a`의 distinct 값마다 인덱스를 다시 하강한다.
따라서 이득은 `a`의 카디널리티가 낮을 때(대략 수십 이하)에 국한된다.
`a`의 distinct 값이 많으면 사실상 인덱스 전체를 훑게 되어, 플래너가 seq scan을
선택하거나 단일 컬럼 인덱스 대비 크게 느려진다.

**단일 컬럼 인덱스를 복합 인덱스로 통합하기 전 체크리스트:**

```sql
-- 1. 선두 컬럼의 카디널리티 확인 (낮을 때만 skip scan 후보)
SELECT attname, n_distinct FROM pg_stats
WHERE tablename = 'users' AND attname = 'status';

-- 2. 통합 후보 인덱스만 남긴 상태를 가정하고 실제 플랜 확인
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM users WHERE email = 'x@example.com';
-- PG18의 "Index Searches: N"이 n_distinct(선두 컬럼) 수준이면 skip scan 동작 중

-- 3. 삭제 전 벤치마크로 동등 성능 확인. 조회 회귀가 있으면 단일 인덱스 유지.
--    삭제는 되돌릴 수 있게: DROP INDEX CONCURRENTLY, 롤백은 재생성 SQL 준비.
```

통계와 벤치마크 없이 "PG18이니 단일 컬럼 인덱스를 지워도 된다"고 일반화하지 말 것.

### Pattern 4: Expression Index

**목표:** 함수나 표현식을 사용하는 쿼리 최적화

```sql
-- 대소문자 무시 검색
CREATE INDEX idx_users_email_lower ON users(LOWER(email));

SELECT * FROM users WHERE LOWER(email) = 'user@example.com';
-- 쿼리가 정확히 동일한 표현식 사용해야 함

-- 날짜 추출
CREATE INDEX idx_orders_year ON orders(EXTRACT(YEAR FROM created_at));

SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2024;

-- JSONB 경로
CREATE INDEX idx_data_email ON users((data->>'email'));

SELECT * FROM users WHERE data->>'email' = 'user@example.com';
```

### Pattern 5: JSONB Indexing Strategies

```sql
-- 1. 전체 JSONB GIN 인덱스
CREATE INDEX idx_data_gin ON documents USING gin(data);

-- 모든 키-값 검색 가능
WHERE data @> '{"user": {"name": "John"}}'  ✅
WHERE data ? 'user'                          ✅

-- 2. 특정 경로 B-tree 인덱스
CREATE INDEX idx_data_email ON users((data->>'email'));

-- 특정 키만 빠름
WHERE data->>'email' = 'user@example.com'   ✅

-- 3. 복합 전략
CREATE INDEX idx_data_type_gin ON documents USING gin((data->'metadata'));
CREATE INDEX idx_data_id ON documents((data->>'id'));

-- type별 검색 + 특정 ID 검색 모두 최적화
```

## Index Maintenance

### Monitoring Index Usage

```sql
-- 사용되지 않는 인덱스 찾기
SELECT
  schemaname,
  relname,
  indexrelname,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelid NOT IN (
    SELECT conindid FROM pg_constraint
  )
ORDER BY pg_relation_size(indexrelid) DESC;

-- 중복 인덱스 찾기
SELECT
  pg_size_pretty(sum(pg_relation_size(idx))::bigint) AS size,
  (array_agg(idx))[1] AS idx1,
  (array_agg(idx))[2] AS idx2,
  (array_agg(idx))[3] AS idx3,
  (array_agg(idx))[4] AS idx4
FROM (
  SELECT
    indexrelid::regclass AS idx,
    (indrelid::text || E'\n' || indclass::text || E'\n' || 
     indkey::text || E'\n' || coalesce(indexprs::text, '') || E'\n' || 
     coalesce(indpred::text, '')) AS key
  FROM pg_index
) sub
GROUP BY key
HAVING count(*) > 1
ORDER BY sum(pg_relation_size(idx)) DESC;
```

### REINDEX

```sql
-- 인덱스 재구축 (bloat 제거)
REINDEX INDEX idx_users_email;

-- 테이블의 모든 인덱스 재구축
REINDEX TABLE users;

-- 동시 재구축 (온라인, PostgreSQL 12+)
REINDEX INDEX CONCURRENTLY idx_users_email;
```

### VACUUM and Analyze

```sql
-- VACUUM으로 dead tuple 제거
VACUUM ANALYZE users;

-- VACUUM FULL (테이블 잠금, 완전 재구축)
VACUUM FULL users;

-- Autovacuum 설정 조정
ALTER TABLE users SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE users SET (autovacuum_analyze_scale_factor = 0.05);
```

## Advanced Strategies

### Bloom Filter Index (Extension)

```sql
-- 다중 컬럼 OR 조건에 효과적
CREATE EXTENSION bloom;

CREATE INDEX idx_users_bloom ON users USING bloom(
  firstname,
  lastname,
  email,
  phone
);

-- 효과적인 쿼리
WHERE firstname = 'John' OR lastname = 'Doe' OR email LIKE '%@example.com';
```

### Constraint Exclusion + Partial Indexes

```sql
-- 파티션된 테이블의 각 파티션에 부분 인덱스
CREATE TABLE orders_2024_q1 PARTITION OF orders
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE INDEX idx_orders_2024_q1_user 
ON orders_2024_q1(user_id)
WHERE created_at >= '2024-01-01' AND created_at < '2024-04-01';
```

## Common Mistakes

### ❌ 1. Over-Indexing

```sql
-- 너무 많은 인덱스는 INSERT/UPDATE 성능 저하
CREATE INDEX idx1 ON users(email);
CREATE INDEX idx2 ON users(name);
CREATE INDEX idx3 ON users(status);
CREATE INDEX idx4 ON users(created_at);
CREATE INDEX idx5 ON users(email, name);  -- 중복!
CREATE INDEX idx6 ON users(email, status);  -- 중복!
```

**해결:** 쿼리 패턴 분석 후 필요한 인덱스만 유지

### ❌ 2. Wrong Column Order

```sql
-- 잘못된 순서
CREATE INDEX idx_orders_bad ON orders(status, user_id);

-- status는 카디널리티 낮음 (pending, completed 등 몇 개)
-- user_id는 카디널리티 높음 (유저 수만큼)

-- 올바른 순서
CREATE INDEX idx_orders_good ON orders(user_id, status);
```

### ❌ 3. Not Using INCLUDE

```sql
-- PostgreSQL 11 이전 방식
CREATE INDEX idx_orders_all ON orders(user_id, amount, created_at, status);

-- 문제: amount, created_at, status가 WHERE 절에 없는데도 인덱스에 포함
-- 인덱스 크기 증가 + B-tree 효율 저하

-- PostgreSQL 11+ 권장
CREATE INDEX idx_orders_better 
ON orders(user_id) 
INCLUDE (amount, created_at, status);
```

### ❌ 4. Ignoring Index Bloat

```sql
-- 인덱스 bloat 확인
SELECT
  schemaname,
  relname,
  indexrelname,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- Bloat 제거
REINDEX INDEX CONCURRENTLY idx_users_email;
```

## Decision Tree: Which Index Type?

```
Query Type?
├─ Equality (=)
│  ├─ Single column → B-tree
│  ├─ Multiple columns → B-tree (multi-column)
│  └─ Many columns with OR → Bloom
│
├─ Range (<, >, BETWEEN)
│  ├─ Small table → B-tree
│  └─ Very large sequential data → BRIN
│
├─ Pattern matching (LIKE, ~)
│  ├─ Prefix match → B-tree with text_pattern_ops
│  ├─ Full-text search → GIN with tsvector
│  └─ Complex pattern → GIN or GiST
│
├─ Array/JSONB
│  ├─ Containment (@>, <@) → GIN
│  ├─ Existence (?) → GIN
│  └─ Specific path → B-tree expression index
│
├─ Geospatial
│  ├─ 2D queries → GiST
│  └─ Complex geometries → GiST
│
└─ Only reading subset of data
   └─ Consider partial index
```

## Performance Checklist

**인덱스 생성 전:**
- [ ] 쿼리 패턴 분석 (pg_stat_statements)
- [ ] 선택도 확인 (n_distinct)
- [ ] 기존 인덱스 확인 (중복 방지)
- [ ] 인덱스 크기 예상 (테이블 크기 × 컬럼 크기)

**인덱스 생성 후:**
- [ ] EXPLAIN ANALYZE로 검증
- [ ] Index-Only Scan 가능한지 확인
- [ ] pg_stat_user_indexes로 사용률 모니터링
- [ ] 정기적인 VACUUM ANALYZE

**최적화 주기:**
- [ ] 주간: pg_stat_statements로 느린 쿼리 확인
- [ ] 월간: 미사용 인덱스 제거
- [ ] 분기: REINDEX CONCURRENTLY로 bloat 제거
- [ ] 연간: 인덱스 전략 재검토
