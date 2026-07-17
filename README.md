# dongju93 Agent Skills

Codex를 비롯한 Agent Skills 호환 에이전트에서 사용할 수 있는 스킬 모음입니다. 각 스킬은 [Agent Skills](https://agentskills.io/) 형식에 따라 독립된 폴더와 `SKILL.md`로 구성됩니다.

## Available skills

| Skill                                                        | Description                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`pg-performance-analyzer`](skills/pg-performance-analyzer/) | PostgreSQL 15–18의 느린 쿼리를 `pg_stat_statements`로 식별하고 `EXPLAIN (ANALYZE, BUFFERS)`를 근거로 병목·스필·필터 낭비·추정 오차·I/O를 진단합니다. PG18 skip scan·AIO를 포함한 인덱스·쿼리·설정 개선안과 동일 방식의 전후 벤치마크를 제공하되, DDL과 `ALTER SYSTEM`은 자동 적용하지 않습니다.                                                                        |
| [`python-secure-coding`](skills/python-secure-coding/)       | KISA 「Python 시큐어코딩 가이드」(2023) 분류 체계를 2026년 기준으로 재구성한 리뷰 기준입니다. KISA 2024–2026 공급망 자료와 Python 문서·OWASP Top 10:2025·PyPA 관행을 반영하며, KISA 공식 2026 Python 가이드는 아닙니다. 소스→싱크 데이터 흐름·프레임워크 보호 우회·의존성·빌드 공급망을 추적하고, 발견 항목을 CWE·심각도·악용 전제·수정안·검증 방법과 함께 보고합니다. |
| [`python-stdlib-first`](skills/python-stdlib-first/)         | 대상 Python 버전을 먼저 확정하고 3.10–3.14(3.9 EOL 이후 하한)의 모듈·API 추가 및 제거 여부를 공식 문서나 로컬 인터프리터로 검증해 런타임 의존성에 표준 라이브러리를 우선 적용합니다. 표준 라이브러리가 의미·성능·보안·호환성 요구를 충족하지 못하면 서드파티 패키지 사용 이유를 명시합니다.                                                                            |
| [`docker-authoring`](skills/docker-authoring/)               | 프로덕션용 Dockerfile·Compose를 작성·리뷰하고 BuildKit·Buildx, 멀티스테이지·캐시, 개발·운영 분리, 헬스체크·비밀·비루트 실행을 다룹니다. 종료·OOM, 빌드, 네트워크, 로그, 이미지·디스크 문제와 보안 하드닝을 증거 기반으로 진단하며, 진단 전용 요청에서는 파일이나 Docker 상태를 변경하지 않습니다.                                                                      |

## When to use `pg-performance-analyzer` vs Timescale `pg-aiguide`

PostgreSQL 작업에는 두 스킬이 상호 보완적입니다. [timescale/pg-aiguide](https://github.com/timescale/pg-aiguide)의 `postgres` 스킬과 역할이 다르므로 작업 성격에 따라 선택하세요.

**`pg-performance-analyzer`를 사용할 때 — 운영 중인 DB의 성능 문제 발견과 검증:**

- `pg_stat_statements`로 느린 쿼리·스필 잦은 쿼리를 찾을 때
- `EXPLAIN (ANALYZE, BUFFERS)` 출력을 해석할 때 — 배타 시간 기준 병목 노드, 정렬/해시 디스크 스필, 필터 낭비, 행 수 추정 오차, heap fetch, JIT 과점유를 근거 메트릭과 함께 보고
- 인덱스·설정 변경의 효과를 전후 벤치마크로 검증할 때 (측정 방식 혼합 없음)
- PostgreSQL 15–18 버전별 기능의 활용 여부를 판단할 때 — PG18 skip scan 통합 기준, AIO(`io_method`) 설정의 재시작/reload/세션 구분

**Timescale `pg-aiguide`를 권장할 때 — 설계와 안전한 적용:**

- 테이블·스키마 설계: 데이터 타입, 제약조건, FK 인덱스, JSONB, 파티셔닝
- 프로덕션 마이그레이션: DDL 잠금 수준 평가, `CREATE INDEX CONCURRENTLY`, `NOT VALID` 후 검증, 배치 백필, 롤백 계획, 무중단 스키마 변경
- TimescaleDB: 하이퍼테이블 전환 판단, 압축·보존 정책, continuous aggregate

**함께 쓰는 흐름:** `pg-performance-analyzer`로 병목을 발견하고 개선안을 벤치마크로 검증한 뒤, 그 DDL을 프로덕션에 적용하는 절차(잠금·롤백·무중단)는 `pg-aiguide`의 마이그레이션 가이드를 따르는 구성이 가장 안전합니다. `pg-performance-analyzer`는 DDL과 `ALTER SYSTEM`을 자동 실행하지 않고 근거·위험도·롤백·검증 SQL과 함께 제안만 합니다.

## Installation

대화형으로 설치할 스킬과 대상 에이전트를 선택합니다.

```bash
npx skills add dongju93/skills
```

## Usage

설치 후 에이전트에 작업을 요청하면 관련 스킬이 자동으로 선택됩니다. 이름을 지정해 명시적으로 호출할 수도 있습니다.

```text
Use $pg-performance-analyzer to analyze this EXPLAIN ANALYZE output.
Use $python-secure-coding to review this Django view for security weaknesses.
Use $python-stdlib-first before adding a third-party dependency for this Python task.
Use $docker-authoring to write a production Dockerfile, or to diagnose why this container exits with code 137.
```
