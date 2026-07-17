#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["psycopg2-binary>=2.9.9"]
# ///
"""PostgreSQL 쿼리 벤치마크 도구.

측정 원칙:
- 한 벤치마크 안에서 모든 반복은 같은 방식으로 측정한다.
  * --timing client (기본): 클라이언트 왕복 시간 (perf_counter)
  * --timing server: 매 반복을 EXPLAIN (ANALYZE...)로 실행해 서버 보고 Execution Time 사용
  두 방식을 한 표본 집합에 섞지 않는다.
- EXPLAIN ANALYZE는 쿼리를 실제로 실행한다. DML(INSERT/UPDATE/DELETE/MERGE)은
  --allow-writes 없이 벤치마크할 수 없다.
- 이 스크립트는 사용자가 --compare-file의 pre_setup/post_cleanup에 직접 적은 SQL만
  실행하며, 실행 전 각 문장을 출력한다. 스스로 DDL이나 ALTER SYSTEM을 만들지 않는다.

사용법:
    uv run scripts/benchmark_query.py --database mydb --user postgres \
        --query "SELECT ..." --iterations 20 --warmup 3

    uv run scripts/benchmark_query.py --database mydb --user postgres \
        --compare-file comparison.json --iterations 15 --json-output
"""

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

GUC_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")
READ_ONLY_KEYWORDS = ("select", "with", "table", "values", "show", "explain")


@dataclass
class BenchmarkResult:
    name: str
    query: str
    timing_mode: str
    iterations: int
    execution_times_ms: list[float] = field(default_factory=list)
    rows_returned: int = 0
    error: str | None = None

    @property
    def stats(self) -> dict[str, float]:
        times = self.execution_times_ms
        if not times:
            return {}
        avg = statistics.mean(times)
        ordered = sorted(times)
        p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
        return {
            "avg_ms": round(avg, 3),
            "median_ms": round(statistics.median(times), 3),
            "min_ms": round(min(times), 3),
            "max_ms": round(max(times), 3),
            "p95_ms": round(p95, 3),
            "std_dev_ms": round(statistics.stdev(times), 3) if len(times) > 1 else 0.0,
            "cv": round(statistics.stdev(times) / avg, 4)
            if len(times) > 1 and avg > 0
            else 0.0,
        }


def leading_keyword(query: str) -> str:
    """주석을 걷어내고 첫 키워드를 반환한다 (쓰기 쿼리 감지용 휴리스틱)."""
    text = re.sub(r"^\s*(--[^\n]*\n|/\*.*?\*/\s*)*", "", query, flags=re.DOTALL)
    match = re.match(r"\s*([a-zA-Z]+)", text)
    return match.group(1).lower() if match else ""


class QueryBenchmark:
    def __init__(self, connection_params: dict[str, Any]):
        self.connection_params = connection_params
        self.conn = None
        self.server_version: str = "unknown"

    def connect(self) -> bool:
        try:
            import psycopg2
        except ImportError:
            print(
                "Error: psycopg2가 없습니다. `uv run scripts/benchmark_query.py ...`로 실행하면"
                " 인라인 메타데이터로 자동 설치됩니다.",
                file=sys.stderr,
            )
            return False
        try:
            self.conn = psycopg2.connect(**self.connection_params)
            # CREATE INDEX CONCURRENTLY 같은 pre_setup DDL이 암묵적 트랜잭션에
            # 갇히지 않도록 autocommit으로 둔다.
            self.conn.autocommit = True
            with self.conn.cursor() as cur:
                cur.execute("SHOW server_version")
                self.server_version = cur.fetchone()[0]
            return True
        except Exception as e:
            print(f"Connection failed: {e}", file=sys.stderr)
            return False

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()

    # ---- 실행 프리미티브 ---------------------------------------------------

    def run_sql(self, sql_text: str, *, announce: bool = True) -> None:
        """setup/cleanup용. 실행 전 문장을 그대로 보여준다."""
        if announce:
            print(f"  [setup] {sql_text}")
        with self.conn.cursor() as cur:
            cur.execute(sql_text)

    def apply_settings(self, settings: dict[str, Any]) -> None:
        from psycopg2 import sql as pgsql

        for name, value in settings.items():
            if not GUC_NAME_RE.match(name):
                raise ValueError(f"잘못된 GUC 이름: {name!r}")
            stmt = pgsql.SQL("SET {} = {}").format(
                pgsql.Identifier(name), pgsql.Literal(str(value))
            )
            print(f"  [setting] SET {name} = {value}")
            with self.conn.cursor() as cur:
                cur.execute(stmt)

    def reset_settings(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("RESET ALL")

    def time_client(self, query: str) -> tuple[float, int]:
        with self.conn.cursor() as cur:
            start = time.perf_counter()
            cur.execute(query)
            rows = cur.fetchall() if cur.description else []
            elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, len(rows)

    def time_server(self, query: str) -> tuple[float, int, Any]:
        """서버 보고 Execution Time(ms)을 반환. EXPLAIN ANALYZE는 쿼리를 실제 실행한다."""
        with self.conn.cursor() as cur:
            cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
            plan = cur.fetchone()[0]
        top = plan[0] if isinstance(plan, list) else plan
        exec_ms = float(top.get("Execution Time", 0))
        rows = int(top.get("Plan", {}).get("Actual Rows", 0))
        return exec_ms, rows, plan

    def capture_plan(self, query: str) -> Any:
        _, _, plan = self.time_server(query)
        return plan

    # ---- 벤치마크 ----------------------------------------------------------

    def run_benchmark(
        self,
        query: str,
        *,
        name: str = "query",
        iterations: int = 10,
        warmup: int = 2,
        timing_mode: str = "client",
        rollback_each: bool = False,
    ) -> BenchmarkResult:
        result = BenchmarkResult(
            name=name, query=query, timing_mode=timing_mode, iterations=iterations
        )

        print(f"  {iterations} iterations (+{warmup} warmup, timing={timing_mode})")

        def one_iteration() -> tuple[float, int]:
            if rollback_each:
                with self.conn.cursor() as cur:
                    cur.execute("BEGIN")
            try:
                if timing_mode == "server":
                    ms, rows, _ = self.time_server(query)
                else:
                    ms, rows = self.time_client(query)
            finally:
                if rollback_each:
                    with self.conn.cursor() as cur:
                        cur.execute("ROLLBACK")
            return ms, rows

        for i in range(warmup):
            print(f"  warmup {i + 1}/{warmup}...", end="\r")
            one_iteration()

        for i in range(iterations):
            print(f"  iteration {i + 1}/{iterations}...", end="\r")
            ms, rows = one_iteration()
            result.execution_times_ms.append(ms)
            result.rows_returned = rows
            time.sleep(0.05)
        print(" " * 40, end="\r")
        return result

    def compare(
        self,
        variants: list[dict[str, Any]],
        *,
        iterations: int,
        warmup: int,
        timing_mode: str,
        allow_writes: bool,
        rollback_each: bool,
    ) -> list[BenchmarkResult]:
        """variants 항목: {name, sql, pre_setup: [..], settings: {..}, post_cleanup: [..]}"""
        results = []
        for i, variant in enumerate(variants, 1):
            name = variant.get("name", f"Query {i}")
            sql_text = variant["sql"]
            print(f"\n=== [{i}/{len(variants)}] {name} ===")

            if not allow_writes and leading_keyword(sql_text) not in READ_ONLY_KEYWORDS:
                results.append(
                    BenchmarkResult(
                        name=name,
                        query=sql_text,
                        timing_mode=timing_mode,
                        iterations=0,
                        error="쓰기 쿼리로 보임 - --allow-writes 필요",
                    )
                )
                print(f"  skipped: {results[-1].error}")
                continue

            try:
                for stmt in variant.get("pre_setup", []):
                    self.run_sql(stmt)
                if variant.get("settings"):
                    self.apply_settings(variant["settings"])

                result = self.run_benchmark(
                    sql_text,
                    name=name,
                    iterations=iterations,
                    warmup=warmup,
                    timing_mode=timing_mode,
                    rollback_each=rollback_each,
                )
            except Exception as e:
                result = BenchmarkResult(
                    name=name,
                    query=sql_text,
                    timing_mode=timing_mode,
                    iterations=0,
                    error=str(e),
                )
                print(f"  error: {e}")
            finally:
                try:
                    for stmt in variant.get("post_cleanup", []):
                        self.run_sql(stmt)
                finally:
                    self.reset_settings()

            results.append(result)
        return results


# ---- 출력 ---------------------------------------------------------------


def print_result(result: BenchmarkResult) -> None:
    print(f"\n=== Benchmark: {result.name} (timing={result.timing_mode}) ===")
    if result.error:
        print(f"  ERROR: {result.error}")
        return
    print(f"  Query: {result.query[:100]}{'...' if len(result.query) > 100 else ''}")
    print(f"  Rows: {result.rows_returned}")
    for key, value in result.stats.items():
        print(f"  {key:>12}: {value}")


def print_comparison(results: list[BenchmarkResult]) -> None:
    valid = [r for r in results if not r.error and r.execution_times_ms]
    if not valid:
        print("\n비교할 유효한 결과가 없습니다.")
        return
    baseline = min(r.stats["median_ms"] for r in valid)
    print(f"\n{'=' * 76}")
    print(f"{'Name':<36} {'median(ms)':>12} {'p95(ms)':>10} {'relative':>10}")
    print("-" * 76)
    for r in sorted(valid, key=lambda r: r.stats["median_ms"]):
        rel = r.stats["median_ms"] / baseline if baseline > 0 else 0
        print(
            f"{r.name[:36]:<36} {r.stats['median_ms']:>12.3f} "
            f"{r.stats['p95_ms']:>10.3f} {rel:>9.2f}x"
        )
    for r in results:
        if r.error:
            print(f"{r.name[:36]:<36} {'(error: ' + r.error[:30] + ')':>34}")


def to_json(results: list[BenchmarkResult], server_version: str) -> str:
    return json.dumps(
        {
            "server_version": server_version,
            "results": [
                {
                    "name": r.name,
                    "query": r.query,
                    "timing_mode": r.timing_mode,
                    "iterations": r.iterations,
                    "rows_returned": r.rows_returned,
                    "error": r.error,
                    "stats": r.stats,
                    "execution_times_ms": [round(t, 3) for t in r.execution_times_ms],
                }
                for r in results
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PostgreSQL 쿼리 벤치마크 (측정 방식 단일화, setup/settings 지원)"
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", default="")
    parser.add_argument("--query", help="벤치마크할 단일 쿼리")
    parser.add_argument("--query-file", help="쿼리가 담긴 파일")
    parser.add_argument(
        "--compare-file",
        help="비교 변형 JSON 파일: [{name, sql, pre_setup, settings, post_cleanup}]",
    )
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument(
        "--timing",
        choices=("client", "server"),
        default="client",
        help="client: 왕복 시간 / server: EXPLAIN ANALYZE 보고 시간 (혼합 없음)",
    )
    parser.add_argument(
        "--allow-writes", action="store_true", help="DML로 보이는 쿼리의 벤치마크 허용"
    )
    parser.add_argument(
        "--rollback-each",
        action="store_true",
        help="각 반복을 BEGIN/ROLLBACK으로 감싼다 (DML 반복 시 데이터 보존)",
    )
    parser.add_argument(
        "--plan-output",
        help="워밍업 후 표본과 별도로 EXPLAIN JSON을 이 파일에 저장 "
        "(parse_explain.py 입력용)",
    )
    parser.add_argument("--json-output", action="store_true")
    args = parser.parse_args()

    conn_params = {
        "host": args.host,
        "port": args.port,
        "database": args.database,
        "user": args.user,
        "password": args.password,
    }

    benchmark = QueryBenchmark(conn_params)
    if not benchmark.connect():
        sys.exit(1)
    print(f"PostgreSQL server version: {benchmark.server_version}")

    try:
        if args.query or args.query_file:
            if args.query:
                query = args.query
            else:
                with open(args.query_file, encoding="utf-8") as f:
                    query = f.read()

            if (
                not args.allow_writes
                and leading_keyword(query) not in READ_ONLY_KEYWORDS
            ):
                print(
                    "이 쿼리는 데이터를 변경하는 것으로 보입니다. 반복 실행에 동의하면 "
                    "--allow-writes를 지정하세요. (--rollback-each 병용 권장)",
                    file=sys.stderr,
                )
                sys.exit(1)

            if args.plan_output:
                plan = benchmark.capture_plan(query)
                with open(args.plan_output, "w", encoding="utf-8") as f:
                    json.dump(plan, f, indent=2, ensure_ascii=False)
                print(f"EXPLAIN plan saved: {args.plan_output} (표본에는 미포함)")

            result = benchmark.run_benchmark(
                query,
                iterations=args.iterations,
                warmup=args.warmup,
                timing_mode=args.timing,
                rollback_each=args.rollback_each,
            )

            if args.json_output:
                print(to_json([result], benchmark.server_version))
            else:
                print_result(result)

        elif args.compare_file:
            with open(args.compare_file, encoding="utf-8") as f:
                variants = json.load(f)
            results = benchmark.compare(
                variants,
                iterations=args.iterations,
                warmup=args.warmup,
                timing_mode=args.timing,
                allow_writes=args.allow_writes,
                rollback_each=args.rollback_each,
            )
            if args.json_output:
                print(to_json(results, benchmark.server_version))
            else:
                print_comparison(results)
        else:
            parser.error("--query, --query-file, --compare-file 중 하나가 필요합니다")
    finally:
        benchmark.disconnect()


if __name__ == "__main__":
    main()
