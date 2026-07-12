#!/usr/bin/env python3
"""
EXPLAIN ANALYZE 결과를 파싱하고 성능 문제를 식별하는 스크립트
"""
import re
import json
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class NodeAnalysis:
    """쿼리 실행 노드 분석 결과"""
    node_type: str
    actual_time: float
    rows: int
    loops: int
    total_cost: float
    issues: List[str]
    recommendations: List[str]


class ExplainAnalyzer:
    """EXPLAIN ANALYZE 결과 분석기"""
    
    # 성능 문제 임계값
    THRESHOLDS = {
        'seq_scan_rows': 1000,  # Seq Scan 시 문제로 간주할 최소 행 수
        'nested_loop_rows': 10000,  # Nested Loop 시 문제로 간주할 최소 행 수
        'time_percentage': 20,  # 전체 시간의 20% 이상을 차지하면 주목
        'row_estimation_ratio': 5,  # 실제/예상 행 수 비율이 5배 이상이면 통계 문제
    }
    
    def __init__(self, explain_output: str):
        self.raw_output = explain_output
        self.nodes: List[Dict[str, Any]] = []
        self.total_time: float = 0
        self.issues: List[str] = []
        self.recommendations: List[str] = []
        
    def parse(self) -> Dict[str, Any]:
        """EXPLAIN ANALYZE 결과 파싱"""
        # JSON 형식인 경우
        if self.raw_output.strip().startswith('['):
            return self._parse_json()
        # 텍스트 형식인 경우
        else:
            return self._parse_text()
    
    def _parse_json(self) -> Dict[str, Any]:
        """JSON 형식 EXPLAIN 파싱"""
        try:
            data = json.loads(self.raw_output)
            plan = data[0]['Plan']
            self.total_time = data[0].get('Execution Time', 0)
            self._analyze_plan_node(plan)
            return self._generate_report()
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return {'error': f'JSON 파싱 실패: {str(e)}'}
    
    def _parse_text(self) -> Dict[str, Any]:
        """텍스트 형식 EXPLAIN 파싱"""
        lines = self.raw_output.split('\n')
        
        # 전체 실행 시간 추출
        for line in lines:
            if 'Execution Time:' in line or 'Total runtime:' in line:
                match = re.search(r'([\d.]+)\s*ms', line)
                if match:
                    self.total_time = float(match.group(1))
        
        # 각 노드 분석
        current_node = {}
        for line in lines:
            line = line.strip()
            if not line or line.startswith('---'):
                continue
            
            # 노드 타입 추출
            node_match = re.match(r'^([\w\s]+?)\s+(?:on|->)', line)
            if node_match:
                if current_node:
                    self._analyze_text_node(current_node)
                current_node = {'type': node_match.group(1).strip(), 'raw': line}
            elif current_node:
                current_node['raw'] = current_node.get('raw', '') + ' ' + line
        
        if current_node:
            self._analyze_text_node(current_node)
        
        return self._generate_report()
    
    def _analyze_plan_node(self, node: Dict[str, Any], depth: int = 0):
        """재귀적으로 플랜 노드 분석"""
        node_type = node.get('Node Type', 'Unknown')
        actual_time = node.get('Actual Total Time', 0)
        rows = node.get('Actual Rows', 0)
        loops = node.get('Actual Loops', 1)
        total_cost = node.get('Total Cost', 0)
        plan_rows = node.get('Plan Rows', 0)
        
        node_info = {
            'type': node_type,
            'actual_time': actual_time,
            'rows': rows,
            'loops': loops,
            'total_cost': total_cost,
            'plan_rows': plan_rows,
            'depth': depth
        }
        
        # 성능 이슈 감지
        issues = []
        recommendations = []
        
        # 1. Sequential Scan 검사
        if node_type == 'Seq Scan' and rows > self.THRESHOLDS['seq_scan_rows']:
            relation = node.get('Relation Name', 'unknown')
            filter_cond = node.get('Filter', '')
            issues.append(f"대량 Sequential Scan ({rows:,} rows on {relation})")
            if filter_cond:
                recommendations.append(
                    f"인덱스 생성 고려: CREATE INDEX ON {relation} ({self._extract_filter_columns(filter_cond)})"
                )
        
        # 2. Nested Loop 검사
        if node_type == 'Nested Loop' and rows * loops > self.THRESHOLDS['nested_loop_rows']:
            issues.append(f"고비용 Nested Loop ({rows:,} rows × {loops} loops)")
            recommendations.append("Hash Join 또는 Merge Join으로 전환 고려 (work_mem 증가 또는 인덱스 추가)")
        
        # 3. 행 수 추정 오차 검사
        if plan_rows > 0 and rows > 0:
            estimation_ratio = max(rows / plan_rows, plan_rows / rows)
            if estimation_ratio > self.THRESHOLDS['row_estimation_ratio']:
                issues.append(f"통계 부정확 (예상: {plan_rows:,}, 실제: {rows:,}, 비율: {estimation_ratio:.1f}x)")
                recommendations.append("ANALYZE 명령으로 테이블 통계 갱신")
        
        # 4. 시간 점유율 검사
        if self.total_time > 0:
            time_percentage = (actual_time / self.total_time) * 100
            if time_percentage > self.THRESHOLDS['time_percentage']:
                issues.append(f"높은 시간 점유율 ({time_percentage:.1f}%)")
        
        # 5. Index Scan이지만 많은 행을 읽는 경우
        if 'Index Scan' in node_type and rows > 10000:
            issues.append(f"비효율적 Index Scan ({rows:,} rows)")
            recommendations.append("인덱스 선택도가 낮음 - 쿼리 조건 재검토 또는 다른 인덱스 사용")
        
        node_info['issues'] = issues
        node_info['recommendations'] = recommendations
        self.nodes.append(node_info)
        
        # 하위 노드 재귀 분석
        if 'Plans' in node:
            for child in node['Plans']:
                self._analyze_plan_node(child, depth + 1)
    
    def _analyze_text_node(self, node_data: Dict[str, str]):
        """텍스트 형식 노드 분석"""
        raw = node_data.get('raw', '')
        node_type = node_data.get('type', 'Unknown')
        
        # 시간과 행 수 추출
        time_match = re.search(r'actual time=([\d.]+)\.\.([\d.]+)', raw)
        rows_match = re.search(r'rows=(\d+)', raw)
        loops_match = re.search(r'loops=(\d+)', raw)
        
        actual_time = float(time_match.group(2)) if time_match else 0
        rows = int(rows_match.group(1)) if rows_match else 0
        loops = int(loops_match.group(1)) if loops_match else 1
        
        node_info = {
            'type': node_type,
            'actual_time': actual_time,
            'rows': rows,
            'loops': loops,
            'issues': [],
            'recommendations': []
        }
        
        # 간단한 이슈 감지 (JSON 파싱과 유사한 로직)
        if 'Seq Scan' in node_type and rows > self.THRESHOLDS['seq_scan_rows']:
            node_info['issues'].append(f"대량 Sequential Scan ({rows:,} rows)")
            node_info['recommendations'].append("적절한 인덱스 생성 검토")
        
        if 'Nested Loop' in node_type and rows * loops > self.THRESHOLDS['nested_loop_rows']:
            node_info['issues'].append(f"고비용 Nested Loop ({rows:,} × {loops})")
            node_info['recommendations'].append("조인 방식 최적화 검토")
        
        self.nodes.append(node_info)
    
    def _extract_filter_columns(self, filter_str: str) -> str:
        """필터 조건에서 컬럼명 추출"""
        # 간단한 컬럼 추출 (개선 가능)
        columns = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>]', filter_str)
        return ', '.join(set(columns)) if columns else 'relevant_columns'
    
    def _generate_report(self) -> Dict[str, Any]:
        """분석 결과 리포트 생성"""
        # 문제가 있는 노드 수집
        problematic_nodes = [n for n in self.nodes if n.get('issues')]
        
        # 전체 요약
        summary = {
            'total_execution_time_ms': self.total_time,
            'total_nodes': len(self.nodes),
            'problematic_nodes': len(problematic_nodes),
            'critical_issues': []
        }
        
        # 심각한 이슈 수집
        for node in problematic_nodes:
            for issue in node.get('issues', []):
                summary['critical_issues'].append({
                    'node_type': node['type'],
                    'issue': issue,
                    'time_ms': node.get('actual_time', 0),
                    'recommendations': node.get('recommendations', [])
                })
        
        # 이슈를 시간순으로 정렬
        summary['critical_issues'].sort(key=lambda x: x['time_ms'], reverse=True)
        
        return {
            'summary': summary,
            'detailed_nodes': self.nodes,
            'overall_recommendations': self._generate_overall_recommendations()
        }
    
    def _generate_overall_recommendations(self) -> List[str]:
        """전체적인 최적화 권장사항 생성"""
        recommendations = []
        
        # Sequential Scan이 많은 경우
        seq_scans = [n for n in self.nodes if n['type'] == 'Seq Scan']
        if len(seq_scans) > 3:
            recommendations.append("다수의 Sequential Scan 발견 - 인덱스 전략 전면 재검토 필요")
        
        # Nested Loop이 많은 경우
        nested_loops = [n for n in self.nodes if 'Nested Loop' in n['type']]
        if len(nested_loops) > 2:
            recommendations.append("work_mem 설정 증가로 Hash/Merge Join 유도 고려")
        
        # 통계 오차가 많은 경우
        stat_issues = [n for n in self.nodes if any('통계' in i for i in n.get('issues', []))]
        if len(stat_issues) > 2:
            recommendations.append("전체 데이터베이스 통계 갱신 필요 (ANALYZE)")
        
        return recommendations


def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("사용법: python parse_explain.py <explain_file.txt>")
        print("또는: cat explain_output.txt | python parse_explain.py -")
        sys.exit(1)
    
    # 입력 읽기
    if sys.argv[1] == '-':
        explain_output = sys.stdin.read()
    else:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            explain_output = f.read()
    
    # 분석 실행
    analyzer = ExplainAnalyzer(explain_output)
    result = analyzer.parse()
    
    # 결과 출력
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
