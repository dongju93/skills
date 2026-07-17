# PostgreSQL 18 Asynchronous I/O (AIO) Tuning Guide

PostgreSQL 18의 비동기 I/O 서브시스템 튜닝 가이드. **설정별 적용 방식(재시작/reload/세션)이 다르므로 먼저 컨텍스트 표를 확인할 것.**

## 설정 컨텍스트 요약 (가장 중요)

| 설정                         | 컨텍스트   | 적용 방법                                             |
| ---------------------------- | ---------- | ----------------------------------------------------- |
| `io_method`                  | postmaster | **서버 재시작 필수.** `pg_reload_conf()` 무효         |
| `io_max_combine_limit`       | postmaster | **서버 재시작 필수** (공유 메모리 할당 크기 결정)     |
| `io_workers`                 | sighup     | `postgresql.conf` 수정 후 reload (`pg_reload_conf()`) |
| `io_combine_limit`           | user       | 세션 `SET` 가능. `io_max_combine_limit`이 상한        |
| `effective_io_concurrency`   | user       | 세션/테이블스페이스 단위 `SET` 가능. PG18 기본값 16   |
| `maintenance_io_concurrency` | user       | 세션 `SET` 가능                                       |

## AIO 개요

PostgreSQL 18은 I/O 요청을 동기 대기 없이 큐잉하는 AIO 서브시스템을 도입했다.

**적용 대상 (PG18 기준):** sequential scan, bitmap heap scan, VACUUM. 일반 index scan의 개별 랜덤 읽기는 대상이 아니다.

**기대 효과:** I/O 대기가 병목인 워크로드에서 sequential scan 등이 유의미하게 빨라질 수 있다 (공개 벤치마크에서 2-3x 사례가 보고되나, 스토리지·캐시 적중률에 따라 차이가 크다 — 반드시 자기 환경에서 벤치마크).

## io_method 선택

```sql
-- 현재 값 확인
SHOW io_method;   -- PG18 기본값: worker
```

**1. `io_uring` (Linux 전용)**

- 요구사항: Linux 커널 5.1+, liburing과 함께 빌드된 바이너리, 충분한 memlock 한도
- 가장 낮은 오버헤드. Linux 프로덕션에서 우선 검토

**2. `worker` (기본값, 모든 플랫폼)**

- I/O 워커 프로세스가 대신 읽기 수행. `io_workers`(기본 3, 1-32)로 워커 수 조절
- macOS/Windows 및 io_uring을 쓸 수 없는 컨테이너 환경의 선택지

**3. `sync` (기존 동작)**

- AIO 이전 동기 방식. 문제 발생 시 되돌리는 용도

**변경 절차 (재시작 필요):**

```sql
ALTER SYSTEM SET io_method = 'io_uring';
-- 이후 유지보수 윈도우에 서버 재시작. pg_reload_conf()로는 적용되지 않는다.
-- 재시작 후 확인:
SHOW io_method;
```

## effective_io_concurrency

동시 발행 가능한 I/O 요청 수. PG18에서 기본값이 16으로 상향됐다.

**시작값 제안 (벤치마크로 조정 전제):**

| 스토리지                        | 시작값                          |
| ------------------------------- | ------------------------------- |
| 로컬 NVMe/SSD                   | 100-200                         |
| 클라우드 블록 스토리지 (EBS 등) | 50-200 (프로비저닝 IOPS에 맞춤) |
| HDD                             | 2-8                             |

전역으로 바꾸기 전에 세션에서 확인한다:

```sql
SET effective_io_concurrency = 200;
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;  -- 대상 쿼리로 전후 비교
```

값을 올려도 스토리지가 IOPS를 못 받아주면 효과가 없고 대기열만 길어진다. 높일수록 좋은 값이 아니다.

## 워크로드별 시작점 (모두 벤치마크 전제)

```sql
-- OLTP: 랜덤 읽기 위주 - AIO 이득이 제한적, 보수적으로
SET effective_io_concurrency = 100;
SET io_combine_limit = '128kB';

-- OLAP/배치: sequential scan 위주 - AIO 이득 큼
SET effective_io_concurrency = 200;
SET io_combine_limit = '256kB';   -- io_max_combine_limit이 허용하는 범위 내
```

`io_combine_limit`은 인접 블록을 하나의 I/O로 합치는 상한이다. `io_max_combine_limit`(재시작 필요)이 이를 다시 제한하므로, 큰 값을 쓰려면 두 값을 함께 계획한다.

## 모니터링

```sql
-- 진행 중인 AIO 핸들 (superuser 또는 pg_read_all_stats 필요)
SELECT pid, state, operation, target_desc, length
FROM pg_aios
LIMIT 20;

-- pg_aios에는 backend_type 컬럼이 없다 - pid로 pg_stat_activity와 조인
SELECT a.backend_type, COUNT(*) AS active_aios
FROM pg_aios io
JOIN pg_stat_activity a USING (pid)
GROUP BY a.backend_type;

-- 백엔드 유형별 I/O 통계 (누적)
SELECT backend_type, object, context, reads, read_time, writes, write_time
FROM pg_stat_io
WHERE reads > 0
ORDER BY read_time DESC;
```

**EXPLAIN 해석 주의:** AIO에서는 백엔드가 I/O를 직접 대기하지 않을 수 있어, `EXPLAIN ANALYZE`의 노드 타이밍이 실제 I/O 부하를 과소 보고할 수 있다. 스토리지가 바쁜데 플랜 타이밍이 온화하면 `pg_aios`/`pg_stat_io`로 교차 확인한다.

## 체크리스트

1. `io_method` 변경은 재시작 계획(유지보수 윈도우)과 함께 제안한다
2. io_uring 사용 전 커널 버전·liburing 빌드·memlock 한도를 확인한다
3. `effective_io_concurrency`는 세션에서 벤치마크 후 전역 반영을 판단한다
4. 컨테이너/제한된 환경에서 io_uring이 막혀 있으면 `worker` + `io_workers` 조정으로 대응한다
5. 변경 전후를 동일 측정 방식으로 벤치마크한다 (`benchmark_query.py --timing server`)
