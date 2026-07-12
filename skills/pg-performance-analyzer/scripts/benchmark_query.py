#!/usr/bin/env python3
"""
PostgreSQL 쿼리 성능 벤치마크 자동화 스크립트
여러 번 실행하여 평균, 중앙값, 표준편차 등을 측정
"""
import sys
import json
import time
import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import argparse


@dataclass
class QueryResult:
    """쿼리 실행 결과"""
    query: str
    execution_time_ms: float
    rows_returned: int
    plan_time_ms: Optional[float] = None


@dataclass
class BenchmarkResult:
    """벤치마크 결과"""
    query: str
    iterations: int
    execution_times_ms: List[float]
    avg_time_ms: float
    median_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    coefficient_of_variation: float  # 변동계수 (표준편차/평균)
    total_rows: int


class QueryBenchmark:
    """쿼리 벤치마크 실행기"""
    
    def __init__(self, connection_params: Dict[str, str]):
        """
        Args:
            connection_params: 데이터베이스 연결 파라미터
                - host, port, database, user, password
        """
        self.connection_params = connection_params
        self.conn = None
        
    def connect(self):
        """데이터베이스 연결"""
        try:
            import psycopg2
            self.conn = psycopg2.connect(**self.connection_params)
            return True
        except ImportError:
            print("Error: psycopg2 not installed. Install with: pip install psycopg2-binary")
            return False
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.conn:
            self.conn.close()
    
    def execute_query(self, query: str, explain: bool = False) -> QueryResult:
        """단일 쿼리 실행 및 시간 측정"""
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        cursor = self.conn.cursor()
        
        # EXPLAIN ANALYZE 모드
        if explain:
            query_to_run = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        else:
            query_to_run = query
        
        # 실행 시간 측정
        start_time = time.perf_counter()
        cursor.execute(query_to_run)
        rows = cursor.fetchall()
        end_time = time.perf_counter()
        
        execution_time_ms = (end_time - start_time) * 1000
        
        # EXPLAIN 결과에서 실제 실행 시간 추출
        plan_time_ms = None
        if explain and rows:
            try:
                plan_data = rows[0][0][0]  # JSON 결과
                plan_time_ms = plan_data.get('Execution Time', 0)
            except (KeyError, IndexError):
                pass
        
        cursor.close()
        
        return QueryResult(
            query=query,
            execution_time_ms=plan_time_ms if plan_time_ms else execution_time_ms,
            rows_returned=len(rows),
            plan_time_ms=plan_time_ms
        )
    
    def run_benchmark(
        self,
        query: str,
        iterations: int = 10,
        warmup_iterations: int = 2,
        explain_on_first: bool = True
    ) -> BenchmarkResult:
        """
        벤치마크 실행
        
        Args:
            query: 실행할 쿼리
            iterations: 반복 횟수
            warmup_iterations: 워밍업 반복 횟수 (결과에서 제외)
            explain_on_first: 첫 번째 실행에서 EXPLAIN ANALYZE 사용
        
        Returns:
            BenchmarkResult 객체
        """
        print(f"Starting benchmark: {iterations} iterations (+ {warmup_iterations} warmup)")
        
        # 워밍업 실행 (캐시 워밍업)
        for i in range(warmup_iterations):
            print(f"  Warmup {i+1}/{warmup_iterations}...", end='\r')
            self.execute_query(query)
        print(f"  Warmup completed" + " " * 20)
        
        # 실제 벤치마크 실행
        execution_times = []
        total_rows = 0
        
        for i in range(iterations):
            print(f"  Iteration {i+1}/{iterations}...", end='\r')
            
            # 첫 번째에만 EXPLAIN 사용 (선택적)
            use_explain = explain_on_first and i == 0
            result = self.execute_query(query, explain=use_explain)
            
            execution_times.append(result.execution_time_ms)
            total_rows = result.rows_returned
            
            # 각 쿼리 사이 약간의 대기 (캐시 영향 감소)
            time.sleep(0.1)
        
        print(f"  Benchmark completed" + " " * 20)
        
        # 통계 계산
        avg_time = statistics.mean(execution_times)
        median_time = statistics.median(execution_times)
        min_time = min(execution_times)
        max_time = max(execution_times)
        
        # 표준편차 (2개 이상의 샘플 필요)
        if len(execution_times) > 1:
            std_dev = statistics.stdev(execution_times)
            cv = (std_dev / avg_time) if avg_time > 0 else 0
        else:
            std_dev = 0
            cv = 0
        
        return BenchmarkResult(
            query=query,
            iterations=iterations,
            execution_times_ms=execution_times,
            avg_time_ms=avg_time,
            median_time_ms=median_time,
            min_time_ms=min_time,
            max_time_ms=max_time,
            std_dev_ms=std_dev,
            coefficient_of_variation=cv,
            total_rows=total_rows
        )
    
    def compare_queries(
        self,
        queries: List[Dict[str, str]],
        iterations: int = 10
    ) -> List[BenchmarkResult]:
        """
        여러 쿼리 비교 벤치마크
        
        Args:
            queries: 쿼리 딕셔너리 리스트 [{'name': 'Query A', 'sql': 'SELECT ...'}]
            iterations: 각 쿼리당 반복 횟수
        
        Returns:
            벤치마크 결과 리스트
        """
        results = []
        
        for i, query_info in enumerate(queries, 1):
            name = query_info.get('name', f'Query {i}')
            sql = query_info['sql']
            
            print(f"\n{'='*60}")
            print(f"Benchmarking: {name}")
            print(f"{'='*60}")
            
            result = self.run_benchmark(sql, iterations=iterations)
            results.append(result)
        
        return results


def print_benchmark_result(result: BenchmarkResult):
    """벤치마크 결과를 보기 좋게 출력"""
    print(f"\n{'='*60}")
    print(f"Benchmark Results")
    print(f"{'='*60}")
    print(f"Query: {result.query[:100]}...")
    print(f"Iterations: {result.iterations}")
    print(f"Rows returned: {result.total_rows}")
    print(f"\nTiming Statistics (ms):")
    print(f"  Average:     {result.avg_time_ms:>10.3f}")
    print(f"  Median:      {result.median_time_ms:>10.3f}")
    print(f"  Min:         {result.min_time_ms:>10.3f}")
    print(f"  Max:         {result.max_time_ms:>10.3f}")
    print(f"  Std Dev:     {result.std_dev_ms:>10.3f}")
    print(f"  CV:          {result.coefficient_of_variation:>10.1%}")
    print(f"\nAll execution times: {[f'{t:.3f}' for t in result.execution_times_ms]}")


def print_comparison(results: List[BenchmarkResult]):
    """여러 쿼리 비교 결과 출력"""
    print(f"\n{'='*80}")
    print(f"Query Comparison (sorted by average time)")
    print(f"{'='*80}")
    
    # 평균 시간 기준 정렬
    sorted_results = sorted(results, key=lambda r: r.avg_time_ms)
    
    # 가장 빠른 쿼리를 기준으로 비율 계산
    baseline = sorted_results[0].avg_time_ms
    
    print(f"\n{'Rank':<6} {'Query':<40} {'Avg (ms)':<12} {'Relative':<10}")
    print(f"{'-'*80}")
    
    for i, result in enumerate(sorted_results, 1):
        query_preview = result.query[:37] + "..." if len(result.query) > 40 else result.query
        ratio = result.avg_time_ms / baseline
        print(f"{i:<6} {query_preview:<40} {result.avg_time_ms:>10.3f}  {ratio:>8.2f}x")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='PostgreSQL Query Benchmark Tool')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', type=int, default=5432, help='Database port')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--user', required=True, help='Database user')
    parser.add_argument('--password', default='', help='Database password')
    parser.add_argument('--query', help='Single query to benchmark')
    parser.add_argument('--query-file', help='File containing query to benchmark')
    parser.add_argument('--compare-file', help='JSON file with multiple queries to compare')
    parser.add_argument('--iterations', type=int, default=10, help='Number of iterations')
    parser.add_argument('--warmup', type=int, default=2, help='Number of warmup iterations')
    parser.add_argument('--json-output', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    # 연결 파라미터 설정
    conn_params = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    # 벤치마크 실행
    benchmark = QueryBenchmark(conn_params)
    
    if not benchmark.connect():
        sys.exit(1)
    
    try:
        # 단일 쿼리 벤치마크
        if args.query or args.query_file:
            if args.query:
                query = args.query
            else:
                with open(args.query_file, 'r') as f:
                    query = f.read()
            
            result = benchmark.run_benchmark(
                query,
                iterations=args.iterations,
                warmup_iterations=args.warmup
            )
            
            if args.json_output:
                print(json.dumps({
                    'query': result.query,
                    'iterations': result.iterations,
                    'avg_time_ms': result.avg_time_ms,
                    'median_time_ms': result.median_time_ms,
                    'min_time_ms': result.min_time_ms,
                    'max_time_ms': result.max_time_ms,
                    'std_dev_ms': result.std_dev_ms,
                    'cv': result.coefficient_of_variation
                }, indent=2))
            else:
                print_benchmark_result(result)
        
        # 여러 쿼리 비교
        elif args.compare_file:
            with open(args.compare_file, 'r') as f:
                queries = json.load(f)
            
            results = benchmark.compare_queries(queries, iterations=args.iterations)
            
            if args.json_output:
                print(json.dumps([{
                    'query': r.query,
                    'avg_time_ms': r.avg_time_ms,
                    'median_time_ms': r.median_time_ms
                } for r in results], indent=2))
            else:
                print_comparison(results)
        
        else:
            print("Error: Specify --query, --query-file, or --compare-file")
            sys.exit(1)
    
    finally:
        benchmark.disconnect()


if __name__ == '__main__':
    main()
