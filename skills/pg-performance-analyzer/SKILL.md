---
name: pg-performance-analyzer
description: PostgreSQL performance analysis and optimization for modern versions (15-18). Use when analyzing EXPLAIN ANALYZE results, identifying query bottlenecks, suggesting index optimizations including skip scan and multi-value lookups, evaluating asynchronous I/O configurations, or benchmarking query performance. Triggered by requests to analyze slow queries, interpret execution plans with modern PostgreSQL features, recommend indexes leveraging latest optimizer capabilities (self-join elimination, OR-to-array transformation, incremental sort, materialized CTE optimizations), or measure query performance metrics considering AIO subsystem, VACUUM improvements, and hardware acceleration.
---

# PostgreSQL Performance Analyzer (Modern Versions 15-18)

PostgreSQL 현대 버전(15-18)의 모든 성능 최적화 기능을 완전히 활용하는 종합 분석, 최적화 및 벤치마킹 도구.

## PostgreSQL 현대 버전 핵심 기능 요약

### PostgreSQL 15 (2022)
- **정렬 성능 대폭 향상**: 단일 컬럼 정렬 25%+ 개선, work_mem 초과 시 40% 개선
- **MERGE 명령어**: 조건부 INSERT/UPDATE/DELETE 통합
- **논리 복제 개선**: Row/column filters, 준비된 트랜잭션 지원
- **압축 백업**: gzip, LZ4, Zstandard 지원

### PostgreSQL 16 (2023)
- **CPU 가속 (SIMD)**: x86, ARM 아키텍처 지원 (ASCII, JSON 처리)
- **Hash 인덱스 빌드 최적화**: 5-15% 속도 향상
- **메모리 관리 개선**: 할당 헤더 크기 16B→8B 감소
- **libpq load balancing**: 랜덤 호스트 연결 분산
- **논리 복제 from standby**: 워크로드 분산 가능

### PostgreSQL 17 (2024)
- **VACUUM 메모리 20x 감소**: 대폭 향상된 메모리 효율
- **I/O 레이어 개선**: Streaming I/O, vectored I/O (readv/writev)
- **B-tree 멀티값 검색**: IN clause 성능 대폭 개선
- **높은 동시성 쓰기 2x**: Atomic 변수 활용, LWLock 경합 제거
- **Incremental sort 강화**: 대용량 데이터셋 처리 개선
- **Materialized CTE 통계 전파**: 더 나은 쿼리 플래닝
- **COPY 성능 2x**: 대용량 행 내보내기 개선

### PostgreSQL 18 (2025)
- **Asynchronous I/O (AIO)**: io_uring/worker, Sequential scans 2-3x 향상
- **Skip Scan**: 다중 컬럼 B-tree 인덱스 prefix 생략 최적화
- **Self-join 자동 제거**: 불필요한 조인 제거
- **OR 절 배열 변환**: 인덱스 활용 극대화
- **Hash join 메모리 최적화**: 더 적은 메모리로 더 나은 성능
- **병렬 GIN 인덱스 빌드**: JSON, full-text 인덱스 가속화
- **Virtual generated columns**: 저장 공간 절약, 쓰기 성능 향상
- **UUIDv7 네이티브 지원**: 타임스탬프 기반, 인덱스 효율 극대화
- **Temporal constraints**: 시간 범위 중첩 방지
- **하드웨어 가속**: ARM NEON, AVX-512, NUMA awareness

## 핵심 기능

### 1. EXPLAIN ANALYZE 종합 해석

PostgreSQL 15-18의 모든 메트릭과 최적화 패턴을 자동 파싱하여 성능 병목 지점 식별.

**사용법:**
```python
# EXPLAIN 출력 파싱 (text 및 JSON 포맷 지원)
python scripts/parse_explain.py explain_output.txt

# 파이프 사용
cat explain_result.txt | python scripts/parse_explain.py -
```

**현대 PostgreSQL에서 감지하는 최적화 기회:**

**PostgreSQL 18 기능:**
- Sequential scans (AIO 최적화 가능 여부)
- Skip scan 기회 (다중 컬럼 인덱스)
- Self-join 제거 가능성
- OR 절의 배열 변환 기회
- AIO 서브시스템 활용도

**PostgreSQL 17 기능:**
- Streaming I/O 활용 여부
- B-tree 멀티값 검색 최적화 (IN clause)
- Incremental sort 기회
- Materialized CTE 통계 전파 여부
- 높은 동시성 쓰기 패턴

**PostgreSQL 16 기능:**
- SIMD 가속 활용 (ASCII, JSON 처리)
- Hash 인덱스 최적화 가능성

**PostgreSQL 15 기능:**
- 정렬 최적화 기회 (단일 컬럼, work_mem 조정)
- MERGE 명령어 활용 가능성

**공통 감지 항목:**
- Inefficient Nested Loops (Hash/Merge Join 권장)
- Poor row estimation (실제 vs 계획 > 5x 차이)
- High time-consuming nodes (전체 시간의 >20%)
- Buffer usage 패턴
- Index scan efficiency

**출력 형식:**
```json
{
  "summary": {
    "postgresql_version": "18.x",
    "detected_features": {
      "pg18": ["aio_enabled", "skip_scan_available"],
      "pg17": ["streaming_io", "incremental_sort"],
      "pg16": ["simd_acceleration"],
      "pg15": ["sort_optimizations"]
    },
    "total_execution_time_ms": 1234.56,
    "aio_enabled": true,
    "io_method": "io_uring",
    "total_nodes": 15,
    "problematic_nodes": 3,
    "optimization_opportunities": {
      "skip_scan_candidates": 2,
      "self_join_elimination": true,
      "or_to_array_conversion": false,
      "incremental_sort_applicable": true,
      "aio_improvement_potential": "high"
    },
    "critical_issues": [
      {
        "node_type": "Seq Scan",
        "issue": "대량 Sequential Scan (50,000 rows) - AIO로 성능 향상 가능 (PG18)",
        "time_ms": 890.23,
        "pg_version_notes": "PostgreSQL 18 AIO는 이 패턴에서 2-3x 성능 향상",
        "buffer_usage": {
          "shared_hit": 1200,
          "shared_read": 3400,
          "shared_dirtied": 0
        },
        "recommendations": [
          "[PG18] Skip scan 가능 인덱스: CREATE INDEX ON users (status, email)",
          "[PG18] AIO 설정: io_method = 'io_uring' (Linux)",
          "[PG17] Streaming I/O 활용 고려"
        ]
      },
      {
        "node_type": "Nested Loop",
        "issue": "비효율적 조인 - Hash Join으로 전환 가능",
        "pg_version_notes": "PostgreSQL 17-18은 Hash Join 메모리 효율 크게 개선",
        "recommendations": [
          "[PG17-18] work_mem 증가 (이전 버전보다 적은 메모리로 동일 성능)",
          "[All] 조인 컬럼 인덱스 생성"
        ]
      },
      {
        "node_type": "Sort",
        "issue": "대량 정렬 작업 - work_mem 초과",
        "pg_version_notes": "PostgreSQL 15+ 배치 정렬 알고리즘으로 40% 개선",
        "recommendations": [
          "[PG15+] work_mem 증가로 in-memory 정렬 유도",
          "[PG15] 단일 컬럼 정렬 시 25%+ 자동 개선"
        ]
      }
    ]
  },
  "modern_pg_recommendations": [
    "[PG18] AIO 서브시스템 활용으로 I/O 병목 해결",
    "[PG18] Skip scan 인덱스로 중복 인덱스 3개 → 1개 통합 가능",
    "[PG17] VACUUM 메모리 사용량 20x 감소로 더 자주 실행 가능",
    "[PG16] SIMD 가속으로 JSON 처리 최적화",
    "[PG15+] 정렬 워크로드 자동 최적화"
  ]
}
```

### 2. 현대 PostgreSQL 인덱스 최적화 전략

PostgreSQL 15-18의 모든 인덱싱 기능을 활용한 종합 전략.

**최적화 우선순위:**
1. **[PG18] Skip Scan 인덱스** - 중복 인덱스 제거, 단일 인덱스로 다중 패턴 지원
2. **[PG17] B-tree 멀티값 검색** - IN clause 최적화
3. **[PG16] Hash 인덱스 빌드 개선** - 5-15% 빠른 생성
4. **[PG15+] 정렬 최적화** - 인덱스 순서 고려
5. **[All] Covering 인덱스** - Index-only scans
6. **[All] Partial 인덱스** - 필터링된 서브셋

**PostgreSQL 18: Skip Scan (획기적)**
```sql
-- 이전: 다중 쿼리 패턴에 중복 인덱스 필요
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status_email ON users(status, email);

-- PostgreSQL 18: 단일 인덱스로 모든 패턴 지원
DROP INDEX idx_users_status;
DROP INDEX idx_users_email;
CREATE INDEX idx_users_status_email ON users(status, email);

-- 이제 모든 패턴이 효율적:
SELECT * FROM users WHERE status = 'active' AND email = 'test@example.com';  -- 일반 scan
SELECT * FROM users WHERE email = 'test@example.com';                         -- skip scan 자동!
SELECT * FROM users WHERE status = 'active';                                  -- prefix scan

-- Skip scan은 플래너가 자동 결정
-- 인덱스 유지보수 비용 66% 감소 (3개→1개)
```

**PostgreSQL 18: AIO와 함께 Sequential Scan 최적화**
```sql
-- Sequential Scan이 불가피한 경우
-- PostgreSQL 18 AIO로 2-3x 성능 향상

-- 1. 인덱스 추가 (가능한 경우)
CREATE INDEX idx_users_email ON users(email);

-- 2. AIO 설정 최적화 (Linux)
ALTER SYSTEM SET io_method = 'io_uring';
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET io_combine_limit = '256kB';
SELECT pg_reload_conf();

-- 3. AIO 활용 확인
SELECT * FROM pg_aios;
```

**PostgreSQL 18: OR 절 최적화**
```sql
-- PostgreSQL 18은 OR 절을 자동으로 배열로 변환하여 인덱스 효율 극대화
-- 코드 변경 불필요 - 플래너가 자동 처리

-- 쿼리 (변경 없음)
SELECT * FROM users 
WHERE status = 'active' OR status = 'pending' OR status = 'processing';

-- PostgreSQL 18 내부 처리:
-- → WHERE status = ANY(ARRAY['active', 'pending', 'processing'])

-- 인덱스가 훨씬 효율적으로 활용됨
CREATE INDEX idx_users_status ON users(status);

-- IN clause도 마찬가지
WHERE status IN ('active', 'pending', 'processing')
-- → 자동 최적화됨
```

**PostgreSQL 17: B-tree 멀티값 검색 (IN clause 대폭 개선)**
```sql
-- PostgreSQL 17+는 IN clause를 단일 B-tree 스캔으로 처리
-- 이전: 각 값마다 별도 index scan → 느림
-- PG17+: 같은 leaf page의 값들을 한번에 처리 → 빠름

-- 예시
SELECT * FROM orders 
WHERE status IN ('processing', 'delivered', 'shipped');

-- PostgreSQL 17+: 단일 Index Scan, 같은 leaf page 값들 batch 처리
-- 성능 향상: 값의 수와 데이터 분포에 따라 달라지지만 상당함

-- 최적 인덱스
CREATE INDEX idx_orders_status ON orders(status);
```

**PostgreSQL 17: Incremental Sort 활용**
```sql
-- PostgreSQL 17은 Incremental sort를 더 효율적으로 처리
-- 부분적으로 정렬된 데이터를 활용

-- 예시: status로 이미 인덱스가 있는 경우
CREATE INDEX idx_users_status_created ON users(status, created_at);

SELECT * FROM users 
WHERE status = 'active'
ORDER BY status, created_at, name;  -- name은 인덱스에 없음

-- PostgreSQL 17: Incremental sort로 name만 추가 정렬
-- → 전체 정렬보다 훨씬 효율적
-- → 대용량 데이터셋에서 특히 효과적
```

**PostgreSQL 16: Hash 인덱스 빌드 최적화**
```sql
-- PostgreSQL 16에서 Hash 인덱스 빌드가 5-15% 빨라짐
-- 특정 워크로드(equality 검색 전용)에서 유용

-- Hash 인덱스는 = 연산에만 사용 가능
CREATE INDEX idx_users_email_hash ON users USING hash(email);

-- 적합한 경우:
-- 1. WHERE email = 'specific@email.com' (equality만)
-- 2. B-tree보다 작은 인덱스 크기
-- 3. 업데이트가 적은 테이블

-- 부적합한 경우:
-- 1. 범위 검색 (>, <, BETWEEN)
-- 2. 정렬 필요 (ORDER BY)
-- 3. UNIQUE 제약 조건 (PG16은 지원 안함)
```

**PostgreSQL 15+: 정렬 최적화를 고려한 인덱스**
```sql
-- PostgreSQL 15+는 정렬이 크게 개선됨
-- 단일 컬럼 정렬: 25%+ 자동 향상
-- work_mem 초과 시: 40% 개선 (배치 정렬)

-- 정렬이 빈번한 쿼리
SELECT name FROM users ORDER BY name;

-- 인덱스로 정렬 회피
CREATE INDEX idx_users_name ON users(name);

-- 하지만 PostgreSQL 15+는 정렬 자체도 빨라서
-- 소량 데이터라면 인덱스 없이도 충분히 빠름
-- → 벤치마크로 결정
```

**PostgreSQL 18: Virtual Generated Columns (기본값)**
```sql
-- PostgreSQL 18에서 GENERATED 컬럼은 기본적으로 virtual
-- 저장 공간 절약, 쓰기 성능 향상

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  subtotal DECIMAL(10,2),
  tax_rate DECIMAL(5,4) DEFAULT 0.0875,
  
  -- Virtual (기본값) - 읽을 때만 계산, 저장 안함
  total DECIMAL(10,2) GENERATED ALWAYS AS (subtotal * (1 + tax_rate)),
  
  -- Stored가 필요한 경우에만 명시 (쓰기 시 저장)
  cached_total DECIMAL(10,2) GENERATED ALWAYS AS (subtotal * (1 + tax_rate)) STORED
);

-- Virtual 컬럼에 인덱스 필요 시:
CREATE INDEX idx_orders_total ON orders((subtotal * (1 + tax_rate)));

-- 장점:
-- 1. 저장 공간 절약 (값을 저장하지 않음)
-- 2. INSERT/UPDATE 빠름 (계산 안함)
-- 3. 항상 최신 값 (재계산 불필요)

-- 단점:
-- 1. SELECT 시 매번 계산 (복잡한 계산이면 느림)
-- 2. 인덱스는 expression index 필요
```

**PostgreSQL 18: UUIDv7 (타임스탬프 기반, 인덱스 효율 극대화)**
```sql
-- PostgreSQL 18은 UUIDv7 네이티브 지원
-- UUIDv4보다 인덱스 성능 압도적 우수

CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT uuidv7(),  -- 네이티브 함수
  event_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 타임스탬프 순서가 보장되어 B-tree 인덱스 효율 극대화
CREATE INDEX idx_events_id ON events(id);  -- 매우 효율적!

-- 비교:
-- UUIDv4: 완전 랜덤 → 인덱스 분할, 쓰기 성능 저하, 캐시 비효율
-- UUIDv7: 순차적 → 인덱스 효율, 쓰기 성능 우수, 캐시 친화적

-- 마이그레이션 전략
-- 1. 새 테이블: UUIDv7 사용
-- 2. 기존 테이블: 점진적 전환 또는 유지 (호환성)
```

**PostgreSQL 18: Temporal Constraints (시간 범위 중첩 방지)**
```sql
-- PostgreSQL 18은 시간 범위 제약조건 네이티브 지원
-- 복잡한 트리거나 EXCLUDE 제약조건 불필요

-- 회의실 예약 시스템
CREATE TABLE room_bookings (
  room_id INTEGER,
  user_id INTEGER,
  booking_period TSTZRANGE,
  PRIMARY KEY (room_id, booking_period WITHOUT OVERLAPS)
);

-- 자동으로 중첩 방지 - 실패하면 에러
INSERT INTO room_bookings VALUES 
  (1, 100, '[2025-01-01 10:00, 2025-01-01 12:00)');
  
-- 중첩 시도 → 에러
INSERT INTO room_bookings VALUES 
  (1, 101, '[2025-01-01 11:00, 2025-01-01 13:00)');
-- ERROR: conflicting key value violates exclusion constraint

-- UNIQUE도 지원
CREATE TABLE employee_assignments (
  employee_id INTEGER,
  project_id INTEGER,
  assignment_period DATERANGE,
  UNIQUE (employee_id, assignment_period WITHOUT OVERLAPS)
);

-- FOREIGN KEY도 지원 (복잡한 참조 무결성)
```

**PostgreSQL 18: 병렬 GIN 인덱스 빌드**
```sql
-- JSONB 및 full-text 인덱스가 병렬로 빌드됨
-- 이전: B-tree, BRIN만 병렬 지원
-- PG18: GIN도 병렬 지원!

-- 병렬 워커 설정
SET max_parallel_maintenance_workers = 4;

-- GIN 인덱스 생성 (자동으로 병렬 처리)
CREATE INDEX CONCURRENTLY idx_docs_content 
ON documents USING gin(content);

-- JSONB 인덱스도 병렬 빌드
CREATE INDEX CONCURRENTLY idx_data_jsonb 
ON logs USING gin(data jsonb_path_ops);

-- 대용량 테이블에서 빌드 시간 대폭 단축
-- 예: 1억 행 테이블, 4 workers → 4배 가까이 빨라짐
```

**참조 문서:**
- `references/index_strategies_modern.md` - PostgreSQL 15-18 인덱스 종합 가이드
- `references/optimization_patterns_modern.md` - 버전별 최적화 패턴
- `references/aio_tuning_pg18.md` - AIO 서브시스템 전문 튜닝

### 3. 쿼리 성능 벤치마킹

PostgreSQL 현대 버전의 모든 기능을 고려한 종합 벤치마킹.

**기본 사용법:**
```bash
# 단일 쿼리 벤치마크
python scripts/benchmark_query.py \
  --database mydb \
  --user postgres \
  --query "SELECT * FROM users WHERE email = 'test@example.com'" \
  --iterations 20 \
  --pg-version auto  # 자동 버전 감지

# 버전별 기능 비교
python scripts/benchmark_query.py \
  --database mydb \
  --user postgres \
  --query-file query.sql \
  --iterations 20 \
  --warmup 3 \
  --analyze-modern-features  # PG 15-18 기능 분석
```

**PostgreSQL 버전 간 기능 비교:**
```json
// version_comparison.json
[
  {
    "name": "PostgreSQL 15 - Improved Sort",
    "sql": "SELECT name FROM users ORDER BY name LIMIT 10000",
    "notes": "PG15: 25%+ faster single-column sort"
  },
  {
    "name": "PostgreSQL 17 - Multi-value IN",
    "sql": "SELECT * FROM orders WHERE status IN ('processing', 'delivered', 'shipped')",
    "notes": "PG17: Single B-tree scan for multiple values"
  },
  {
    "name": "PostgreSQL 18 - Skip Scan",
    "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
    "pre_setup": ["CREATE INDEX idx_users_status_email ON users(status, email)"],
    "notes": "PG18: Skip scan eliminates need for separate index"
  },
  {
    "name": "PostgreSQL 18 - AIO",
    "sql": "SELECT COUNT(*) FROM large_table WHERE status = 'active'",
    "settings": {
      "io_method": "io_uring",
      "effective_io_concurrency": 200
    },
    "notes": "PG18: 2-3x faster with AIO"
  }
]
```

```bash
python scripts/benchmark_query.py \
  --compare-file version_comparison.json \
  --iterations 15
```

**출력 통계 (현대 버전 특화):**
- Average, median, min, max 실행 시간
- Standard deviation, Coefficient of variation
- **[PG18]** AIO 메트릭 (pg_aios)
- **[PG17]** Streaming I/O 활용도
- **[PG17]** Incremental sort 사용 여부
- **[PG16]** SIMD 가속 활용
- **[PG15]** 정렬 최적화 적용 여부
- **[All]** Buffer usage 상세 정보
- **[All]** Skip scan / Multi-value lookup 사용 여부

## 워크플로우

### Step 1: 느린 쿼리 식별

```sql
-- pg_stat_statements로 느린 쿼리 찾기
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  stddev_exec_time,
  rows
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- 100ms 이상
ORDER BY total_exec_time DESC
LIMIT 20;

-- EXPLAIN ANALYZE 실행 (PostgreSQL 17+ 개선된 출력)
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT JSON) 
SELECT * FROM orders 
WHERE user_id = 123 AND status = 'pending';

-- PostgreSQL 18: AIO 활용 확인
SELECT * FROM pg_aios;
```

### Step 2: 종합 파싱 및 분석

```bash
# EXPLAIN 출력 저장
psql -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ..." > explain.txt

# PostgreSQL 현대 버전 전용 파싱
python scripts/parse_explain.py explain.txt --detect-modern-features > analysis.json

# 버전별 최적화 기회 확인
cat analysis.json | jq '.modern_pg_recommendations'

# PostgreSQL 18 특화 기회
cat analysis.json | jq '.optimization_opportunities'
```

### Step 3: 권장사항 검토 및 적용

**참조 가이드 선택:**
```bash
# 종합 인덱스 전략
view references/index_strategies_modern.md

# 버전별 최적화 패턴
view references/optimization_patterns_modern.md

# PostgreSQL 18 AIO 튜닝
view references/aio_tuning_pg18.md
```

**최적화 적용 예시:**
```sql
-- [PG18] Skip scan 인덱스 (중복 제거)
CREATE INDEX CONCURRENTLY idx_users_status_email 
ON users(status, email);

-- [PG18] AIO 활성화 (Linux)
ALTER SYSTEM SET io_method = 'io_uring';
ALTER SYSTEM SET effective_io_concurrency = 200;
SELECT pg_reload_conf();

-- [PG18] 새로운 플래너 옵션 활성화
SET enable_self_join_elimination = on;
SET enable_skip_scan = on;
SET enable_or_transformation = on;

-- [PG17] Incremental sort 활용
SET enable_incremental_sort = on;

-- [PG17+] Hash Join 메모리 최적화
SET work_mem = '128MB';  -- PG17+는 더 효율적

-- [PG18] Virtual generated column 활용
ALTER TABLE orders 
ADD COLUMN total DECIMAL(10,2) GENERATED ALWAYS AS (subtotal * (1 + tax_rate));

-- [PG18] UUIDv7 마이그레이션 (새 테이블)
CREATE TABLE new_events (
  id UUID PRIMARY KEY DEFAULT uuidv7(),
  ...
);

-- [PG18] Temporal constraint 추가
ALTER TABLE room_bookings 
ADD PRIMARY KEY (room_id, booking_period WITHOUT OVERLAPS);
```

### Step 4: 벤치마크 및 검증

```bash
# 최적화 전후 비교
cat > optimization_comparison.json << 'EOF'
[
  {
    "name": "Before - Multiple indexes",
    "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
    "pre_setup": [
      "CREATE INDEX idx_email ON users(email)",
      "CREATE INDEX idx_status ON users(status)",
      "CREATE INDEX idx_status_email ON users(status, email)"
    ]
  },
  {
    "name": "After - Skip scan single index (PG18)",
    "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
    "pre_setup": [
      "DROP INDEX IF EXISTS idx_email",
      "DROP INDEX IF EXISTS idx_status",
      "CREATE INDEX idx_status_email ON users(status, email)"
    ]
  }
]
EOF

python scripts/benchmark_query.py \
  --compare-file optimization_comparison.json \
  --iterations 20 \
  --analyze-modern-features
```

### Step 5: 지속적 모니터링

```sql
-- PostgreSQL 18: AIO 모니터링
SELECT backend_type, COUNT(*) as active_aios
FROM pg_aios
GROUP BY backend_type;

-- PostgreSQL 17+: VACUUM 진행률
SELECT * FROM pg_stat_progress_vacuum;

-- 인덱스 사용률 추적
SELECT 
  schemaname, tablename, indexname,
  idx_scan, idx_tup_read, idx_tup_fetch,
  pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE idx_scan < 100  -- 사용 빈도 낮음
ORDER BY pg_relation_size(indexrelid) DESC;

-- PostgreSQL 17: 개선된 pg_wait_events
SELECT wait_event_type, wait_event, COUNT(*)
FROM pg_stat_activity
WHERE wait_event IS NOT NULL
GROUP BY wait_event_type, wait_event
ORDER BY COUNT(*) DESC;

-- 쿼리 성능 추적
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  stddev_exec_time,
  (total_exec_time / SUM(total_exec_time) OVER ()) * 100 as pct_total_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY total_exec_time DESC
LIMIT 20;
```

## PostgreSQL 현대 버전 특화 설정

### PostgreSQL 18: AIO 서브시스템

```sql
-- Linux (io_uring 권장)
ALTER SYSTEM SET io_method = 'io_uring';
ALTER SYSTEM SET io_combine_limit = '256kB';
ALTER SYSTEM SET io_max_combine_limit = '512kB';
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET maintenance_io_concurrency = 20;

-- 비-Linux (worker 방식)
ALTER SYSTEM SET io_method = 'worker';
ALTER SYSTEM SET effective_io_concurrency = 100;

SELECT pg_reload_conf();

-- 확인
SHOW io_method;
SELECT * FROM pg_aios;
```

### PostgreSQL 18: 쿼리 최적화 플래너 옵션

```sql
-- 새로운 최적화 기능 활성화
ALTER SYSTEM SET enable_self_join_elimination = on;
ALTER SYSTEM SET enable_skip_scan = on;
ALTER SYSTEM SET enable_or_transformation = on;
SELECT pg_reload_conf();
```

### PostgreSQL 17: Incremental Sort 및 병렬 처리

```sql
-- Incremental sort (기본 on, 확인용)
SHOW enable_incremental_sort;  -- should be 'on'

-- 병렬 sequential scans 최적화
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET parallel_tuple_cost = 0.01;
```

### PostgreSQL 17+: Hash Join 메모리 최적화

```sql
-- PostgreSQL 17+는 Hash Join이 매우 효율적
-- 이전 버전보다 적은 메모리로 동일 성능

-- 권장 시작값
ALTER SYSTEM SET work_mem = '64MB';      -- PG16: 128MB 필요했던 것
ALTER SYSTEM SET hash_mem_multiplier = 2.0;

-- 복잡한 분석 쿼리 (세션별)
SET work_mem = '256MB';
```

### PostgreSQL 17: VACUUM 최적화

```sql
-- PostgreSQL 17은 VACUUM 메모리 사용량이 20x 감소
-- 더 자주, 더 적극적으로 실행 가능

-- 더 낮은 threshold로 더 빈번한 vacuum
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.05;  -- 기본: 0.2
ALTER SYSTEM SET autovacuum_analyze_scale_factor = 0.025;  -- 기본: 0.1

-- Vacuum 비용 제한 완화 (PG17은 효율적)
ALTER SYSTEM SET autovacuum_vacuum_cost_limit = 1000;  -- 기본: 200
```

### PostgreSQL 16: CPU 가속 (SIMD)

```sql
-- PostgreSQL 16+는 자동으로 SIMD 활용
-- 별도 설정 불필요, CPU가 지원하면 자동 활성화

-- 확인 (로그에 표시됨)
-- x86: SSE, AVX 사용
-- ARM: NEON 사용

-- JSON 처리, ASCII 변환 등에서 자동 가속
```

### PostgreSQL 15: 정렬 최적화

```sql
-- PostgreSQL 15+는 정렬이 자동으로 최적화됨
-- work_mem 조정으로 최대 효과

-- 정렬 빈번한 워크로드
ALTER SYSTEM SET work_mem = '128MB';  -- 기본: 4MB

-- 단일 컬럼 정렬은 25%+ 자동 향상
-- work_mem 초과 시 배치 정렬로 40% 향상
```

### PostgreSQL 18: 병렬 GIN 인덱스 빌드

```sql
-- GIN 인덱스 빌드를 병렬화
ALTER SYSTEM SET max_parallel_maintenance_workers = 4;
SELECT pg_reload_conf();

-- JSONB 또는 full-text 인덱스 생성
CREATE INDEX CONCURRENTLY idx_docs_content 
ON documents USING gin(content);
-- → 자동으로 병렬 빌드
```

## Quick Reference

### EXPLAIN 분석 (현대 버전 특화)
```bash
python scripts/parse_explain.py <file> --detect-modern-features
```

### 쿼리 벤치마크 (버전 자동 감지)
```bash
python scripts/benchmark_query.py --database <db> --user <user> --query "<sql>" --pg-version auto
```

### 최적화 패턴 가이드
```bash
view references/optimization_patterns_modern.md
```

### 인덱스 전략 (PG 15-18)
```bash
view references/index_strategies_modern.md
```

### AIO 튜닝 (PG18)
```bash
view references/aio_tuning_pg18.md
```

## 의존성

**Python 패키지:**
```bash
pip install --break-system-packages psycopg2-binary>=2.9.9
```

**PostgreSQL 확장:**
```sql
CREATE EXTENSION pg_stat_statements;  -- 쿼리 통계
CREATE EXTENSION bloom;                -- Bloom filter 인덱스 (선택)
```

## Best Practices (PostgreSQL 현대 버전)

1. **[PG18] AIO 활성화** - Linux에서 io_uring로 2-3x 향상
2. **[PG18] Skip scan 우선** - 중복 인덱스 제거, 유지보수 비용 감소
3. **[PG18] UUIDv7 사용** - 새 프로젝트의 UUID primary key
4. **[PG17] VACUUM 더 자주** - 메모리 20x 감소로 비용 낮음
5. **[PG17] IN clause 활용** - B-tree 멀티값 검색 최적화됨
6. **[PG16] Hash 인덱스 고려** - Equality 검색 전용 워크로드
7. **[PG15+] 정렬 최적화 활용** - work_mem 조정으로 최대 효과
8. **[All] EXPLAIN에 BUFFERS 포함** - 필수 메트릭
9. **[All] 다중 iteration 벤치마크** - 신뢰성 확보
10. **[All] 프로덕션 규모 데이터 테스트** - 실제 볼륨 반영
11. **[All] CONCURRENTLY 사용** - 라이브 시스템 인덱스 생성
12. **[All] 정기적 ANALYZE** - 통계 최신 유지
13. **[PG18] Virtual generated columns** - 저장 공간 절약
14. **[PG18] Temporal constraints** - 시간 범위 중첩 방지
15. **[PG17+] Incremental sort 활용** - 부분 정렬 데이터 효율

## 일반적 시나리오

### 시나리오 A: 신규 프로젝트 (PostgreSQL 18)

```sql
-- 1. 최신 기능 전부 활용
ALTER SYSTEM SET io_method = 'io_uring';  -- AIO
ALTER SYSTEM SET enable_skip_scan = on;
ALTER SYSTEM SET enable_self_join_elimination = on;

-- 2. UUID Primary Key는 UUIDv7
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT uuidv7(),
  ...
);

-- 3. Virtual generated columns 활용
CREATE TABLE orders (
  subtotal DECIMAL(10,2),
  tax_rate DECIMAL(5,4),
  total DECIMAL(10,2) GENERATED ALWAYS AS (subtotal * (1 + tax_rate))
);

-- 4. Temporal constraints로 중첩 방지
CREATE TABLE bookings (
  resource_id INTEGER,
  booking_period TSTZRANGE,
  PRIMARY KEY (resource_id, booking_period WITHOUT OVERLAPS)
);

-- 5. Skip scan 인덱스 전략
CREATE INDEX idx_users_status_email ON users(status, email);
-- → WHERE email = ... 도 자동 최적화

-- 6. 병렬 GIN 인덱스
SET max_parallel_maintenance_workers = 4;
CREATE INDEX idx_docs_content ON documents USING gin(content);
```

### 시나리오 B: 기존 프로젝트 최적화

```sql
-- 1. 현재 성능 병목 식별
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- 2. PostgreSQL 버전 확인
SHOW server_version;

-- 3. 버전별 최적화 적용
-- PG18: AIO, Skip scan
-- PG17: VACUUM 더 자주, Hash join 메모리 감소
-- PG16: Hash 인덱스 고려
-- PG15: work_mem 조정으로 정렬 최적화

-- 4. 중복 인덱스 정리 (PG18 Skip scan 활용)
-- 5. 벤치마크로 검증
-- 6. 점진적 배포
```

### 시나리오 C: 느린 분석 쿼리 최적화

```sql
-- 1. EXPLAIN ANALYZE 확인
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT ... FROM large_table WHERE ...;

-- 2. PostgreSQL 17+ 최적화 활용
-- - Streaming I/O로 Sequential scan 빠름
-- - B-tree multi-value lookup으로 IN clause 빠름
-- - Incremental sort로 부분 정렬 효율

-- 3. PostgreSQL 18 AIO로 I/O 병목 해결
ALTER SYSTEM SET io_method = 'io_uring';
ALTER SYSTEM SET effective_io_concurrency = 500;  -- 분석 워크로드

-- 4. work_mem 증가 (PG17+ Hash join 효율적)
SET work_mem = '256MB';

-- 5. 병렬 처리 활용
SET max_parallel_workers_per_gather = 4;
```

### 시나리오 D: 대용량 INSERT/UPDATE 최적화

```sql
-- 1. PostgreSQL 17 고동시성 쓰기 최적화 활용
-- → Atomic 변수로 2x 향상

-- 2. COPY 명령 사용 (PG17: 2x 향상)
COPY large_table FROM 'data.csv' WITH (FORMAT csv);

-- 3. Batch INSERT
INSERT INTO table VALUES (...), (...), ...;  -- 1000개씩

-- 4. Virtual generated columns 활용
-- → INSERT/UPDATE 시 계산 안함

-- 5. 인덱스 일시 삭제 고려 (대량 INSERT)
DROP INDEX ...;
-- ... INSERT ...
CREATE INDEX CONCURRENTLY ...;
```

### 시나리오 E: 버전 업그레이드 후 최적화

```sql
-- PostgreSQL 18로 업그레이드 후

-- 1. pg_upgrade로 통계 보존 확인 (PG18)
-- → ANALYZE 불필요

-- 2. 새 기능 활성화
ALTER SYSTEM SET io_method = 'io_uring';
ALTER SYSTEM SET enable_skip_scan = on;
ALTER SYSTEM SET enable_self_join_elimination = on;
SELECT pg_reload_conf();

-- 3. 중복 인덱스 정리 (Skip scan 활용)
-- 예: idx_status, idx_email → idx_status_email 하나로

-- 4. VACUUM 더 자주 실행 (PG17+ 메모리 효율)
ALTER SYSTEM SET autovacuum_vacuum_scale_factor = 0.05;

-- 5. work_mem 감소 가능 (PG17+ Hash join 효율)
ALTER SYSTEM SET work_mem = '64MB';  -- 이전: 128MB

-- 6. 주요 쿼리 벤치마크
-- → 자동 최적화 확인
```

## 리소스

### scripts/parse_explain.py
PostgreSQL 15-18 전용 종합 EXPLAIN ANALYZE 파서.

**핵심 기능:**
- 버전별 최적화 기회 자동 감지
- PostgreSQL 18: Skip scan, AIO, Self-join 제거
- PostgreSQL 17: Streaming I/O, Incremental sort, Multi-value lookup
- PostgreSQL 16: SIMD 가속 활용
- PostgreSQL 15: 정렬 최적화 기회
- 버전 자동 감지 및 권장사항

### scripts/benchmark_query.py
PostgreSQL 현대 버전 기능을 고려한 종합 벤치마킹 도구.

**핵심 기능:**
- PostgreSQL 버전 자동 감지
- 버전별 기능 활용도 분석
- PG18: AIO 메트릭, Skip scan 확인
- PG17: Streaming I/O, Incremental sort
- 통계 메트릭 (avg, median, stddev, CV)
- JSON 출력 (자동화용)

### references/optimization_patterns_modern.md
PostgreSQL 15-18 버전별 최적화 패턴 종합 가이드.

**포함 내용:**
- 버전별 주요 기능 상세 설명
- 최적화 패턴 및 안티패턴
- 쿼리 재작성 전략
- 설정 튜닝 (버전별)
- 모니터링 쿼리
- 실전 예제

### references/index_strategies_modern.md
PostgreSQL 15-18 인덱스 설계 종합 가이드.

**포함 내용:**
- 모든 인덱스 타입 (B-tree, GIN, GiST, BRIN, Hash 등)
- PostgreSQL 18: Skip scan, Temporal constraints, UUIDv7
- PostgreSQL 17: Multi-value lookups, Incremental sort
- PostgreSQL 16: Hash 인덱스 빌드 최적화
- 다중 컬럼 인덱스 순서 결정
- JSONB 인덱싱 (버전별 개선사항)
- 인덱스 유지보수 및 모니터링

### references/aio_tuning_pg18.md
PostgreSQL 18 AIO 서브시스템 전문 튜닝 가이드.

**포함 내용:**
- io_method 선택 (io_uring vs worker vs sync)
- effective_io_concurrency 최적값 결정
- 워크로드별 AIO 설정
- 벤치마킹 방법론
- pg_aios 모니터링
- 하드웨어 고려사항 (SSD, HDD, NVMe, 클라우드)
