#!/usr/bin/env python3
"""EXPLAIN (ANALYZE) 결과를 파싱해 근거 메트릭과 함께 성능 문제를 보고하는 스크립트.

- 입력: EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 출력 파일 또는 stdin(`-`)
- 텍스트 포맷도 받지만 제한된 분석만 제공 (JSON 포맷 권장)
- DB에 접속하지 않는 읽기 전용 도구. 모든 권장사항은 제안일 뿐 실행하지 않는다.
- 표준 라이브러리만 사용 (의존성 없음)

사용법:
    python parse_explain.py explain.json
    psql -Atc "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT ..." | python parse_explain.py -
    python parse_explain.py explain.json --top 10
"""
import argparse
import json
import re
import sys
from typing import Any

THRESHOLDS = {
    "seq_scan_rows": 1000,          # 문제로 간주할 Seq Scan 최소 행 수
    "nested_loop_inner_rows": 10000,  # rows x loops 기준
    "time_share_pct": 20,           # 배타 시간이 전체의 이 비율 이상이면 주목
    "row_estimate_ratio": 5,        # 예상/실제 행 수 오차 배율
    "filter_waste_ratio": 0.5,      # 필터로 버려진 행 비율
    "filter_waste_min_rows": 1000,
    "heap_fetch_ratio": 0.2,        # Index Only Scan에서 heap fetch 비율
    "heap_fetch_min": 1000,
    "jit_share_pct": 20,            # JIT 시간이 실행 시간의 이 비율 이상이면 주목
    "planning_dominance_ms": 10,    # 계획 시간이 이 값 이상이면서 실행 시간의 2배 이상
}

# 값이 클수록 심각. 이슈 정렬에 사용.
SEVERITY_ORDER = {"high": 0, "medium": 1, "info": 2}


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class JsonPlanAnalyzer:
    """EXPLAIN (FORMAT JSON) 출력 분석기."""

    def __init__(self, data: list[dict[str, Any]]):
        self.root = data[0]
        self.planning_time = _num(self.root.get("Planning Time"))
        self.execution_time = _num(self.root.get("Execution Time"))
        self.nodes: list[dict[str, Any]] = []
        self.issues: list[dict[str, Any]] = []
        self.features: set[str] = set()
        self.notes: list[str] = []

    def analyze(self) -> dict[str, Any]:
        self._walk(self.root["Plan"], depth=0)
        self._check_plan_level()
        return self._report()

    # ---- 노드 순회 -------------------------------------------------------

    def _walk(self, node: dict[str, Any], depth: int) -> float:
        """노드를 분석하고 포함(inclusive) 시간(ms)을 반환한다."""
        loops = max(int(_num(node.get("Actual Loops", 1))), 1)
        # Actual Total Time은 루프당 평균이므로 loops를 곱해 포함 시간을 구한다.
        inclusive_ms = _num(node.get("Actual Total Time")) * loops

        children_ms = 0.0
        for child in node.get("Plans", []):
            children_ms += self._walk(child, depth + 1)

        # InitPlan/SubPlan/병렬 워커 평균 때문에 음수가 될 수 있어 0으로 클램프.
        exclusive_ms = max(inclusive_ms - children_ms, 0.0)

        info = self._collect(node, depth, loops, inclusive_ms, exclusive_ms)
        self._detect_issues(node, info)
        self.nodes.append(info)
        return inclusive_ms

    def _collect(
        self,
        node: dict[str, Any],
        depth: int,
        loops: int,
        inclusive_ms: float,
        exclusive_ms: float,
    ) -> dict[str, Any]:
        node_type = node.get("Node Type", "Unknown")
        actual_rows = int(_num(node.get("Actual Rows")))
        info: dict[str, Any] = {
            "node_type": node_type,
            "relation": node.get("Relation Name"),
            "index": node.get("Index Name"),
            "depth": depth,
            "loops": loops,
            "plan_rows": int(_num(node.get("Plan Rows"))),
            "actual_rows_per_loop": actual_rows,
            "actual_rows_total": actual_rows * loops,
            "inclusive_ms": round(inclusive_ms, 3),
            "exclusive_ms": round(exclusive_ms, 3),
        }

        buffers = {}
        for key in (
            "Shared Hit Blocks", "Shared Read Blocks",
            "Shared Dirtied Blocks", "Shared Written Blocks",
            "Temp Read Blocks", "Temp Written Blocks",
        ):
            v = int(_num(node.get(key)))
            if v:
                buffers[key.lower().replace(" ", "_")] = v
        # track_io_timing이 켜진 경우만 존재. PG 버전에 따라 키 이름이 다르다.
        io_read = _num(node.get("I/O Read Time")) or _num(node.get("Shared I/O Read Time"))
        io_write = _num(node.get("I/O Write Time")) or _num(node.get("Shared I/O Write Time"))
        if io_read:
            buffers["io_read_time_ms"] = round(io_read, 3)
        if io_write:
            buffers["io_write_time_ms"] = round(io_write, 3)
        if buffers:
            info["buffers"] = buffers

        for src, dst in (
            ("Rows Removed by Filter", "rows_removed_by_filter"),
            ("Rows Removed by Join Filter", "rows_removed_by_join_filter"),
            ("Rows Removed by Index Recheck", "rows_removed_by_index_recheck"),
            ("Heap Fetches", "heap_fetches"),
            ("Exact Heap Blocks", "exact_heap_blocks"),
            ("Lossy Heap Blocks", "lossy_heap_blocks"),
            ("Hash Batches", "hash_batches"),
            ("Peak Memory Usage", "peak_memory_kb"),
            ("Workers Planned", "workers_planned"),
            ("Workers Launched", "workers_launched"),
            ("Index Searches", "index_searches"),
        ):
            if src in node:
                info[dst] = int(_num(node[src]))

        if "Sort Method" in node:
            info["sort_method"] = node["Sort Method"]
            info["sort_space_kb"] = int(_num(node.get("Sort Space Used")))
            info["sort_space_type"] = node.get("Sort Space Type")

        # 관찰 가능한 기능 흔적 수집 (버전 추정이 아니라 출력에 실재하는 필드 기준)
        if "Index Searches" in node:
            self.features.add("index_searches_field (PG18+: multi-value/skip scan 효율 지표)")
        if node.get("Async Capable"):
            self.features.add("async_append (PG14+)")
        if node_type == "Incremental Sort":
            self.features.add("incremental_sort")
        if node_type == "Memoize":
            self.features.add("memoize (PG14+)")
        if node_type in ("Gather", "Gather Merge"):
            self.features.add("parallel_query")

        return info

    # ---- 이슈 감지 -------------------------------------------------------

    def _add_issue(
        self,
        severity: str,
        info: dict[str, Any],
        issue: str,
        evidence: dict[str, Any],
        suggestions: list[str],
    ) -> None:
        self.issues.append({
            "severity": severity,
            "node_type": info["node_type"],
            "relation": info.get("relation"),
            "issue": issue,
            "evidence": evidence,
            "suggestions": suggestions,
        })

    def _detect_issues(self, node: dict[str, Any], info: dict[str, Any]) -> None:
        node_type = info["node_type"]
        rows_total = info["actual_rows_total"]
        removed = info.get("rows_removed_by_filter", 0)

        # 1. 대량 Seq Scan (+ 필터로 버려지는 행이 많으면 인덱스 후보)
        if node_type == "Seq Scan" and rows_total + removed * info["loops"] > THRESHOLDS["seq_scan_rows"]:
            filter_cond = node.get("Filter", "")
            suggestions = []
            if filter_cond:
                cols = self._filter_columns(filter_cond)
                suggestions.append(
                    f"인덱스 후보 검토: CREATE INDEX CONCURRENTLY ON {info.get('relation') or '<table>'} ({cols}) "
                    "-- 생성 전 pg_stats의 n_distinct로 선택도 확인"
                )
            else:
                suggestions.append("필터 없는 전체 스캔 - 반환 행이 실제로 모두 필요한지 쿼리 자체를 재검토")
            self._add_issue(
                "medium" if removed else "info", info,
                f"대량 Sequential Scan ({rows_total:,}행 반환, 필터로 {removed:,}행/루프 제거)",
                {"rows": rows_total, "rows_removed_by_filter": removed, "filter": filter_cond or None},
                suggestions,
            )

        # 2. 필터 낭비율이 높은 Index Scan (인덱스 조건이 아닌 필터로 대부분 걸러짐)
        if "Index Scan" in node_type and removed >= THRESHOLDS["filter_waste_min_rows"]:
            per_loop = info["actual_rows_per_loop"]
            waste = removed / (removed + per_loop) if (removed + per_loop) else 0
            if waste > THRESHOLDS["filter_waste_ratio"]:
                self._add_issue(
                    "high", info,
                    f"인덱스로 읽은 행의 {waste:.0%}가 필터에서 버려짐 (제거 {removed:,}행/루프)",
                    {"rows_removed_by_filter": removed, "rows_returned_per_loop": per_loop,
                     "filter": node.get("Filter")},
                    ["필터 컬럼을 포함한 복합 인덱스 또는 partial index 검토",
                     "조건이 표현식이면 expression index 검토"],
                )

        # 3. 고비용 Nested Loop
        if node_type == "Nested Loop" and rows_total > THRESHOLDS["nested_loop_inner_rows"]:
            self._add_issue(
                "medium", info,
                f"고비용 Nested Loop ({info['actual_rows_per_loop']:,}행 x {info['loops']}루프)",
                {"rows_total": rows_total},
                ["조인 컬럼 인덱스 확인",
                 "세션에서 SET LOCAL work_mem 증가 후 Hash Join으로 바뀌는지 EXPLAIN으로 확인 (전역 변경 아님)"],
            )

        # 4. 행 수 추정 오차 (루프당 기준으로 비교)
        plan_rows, actual = info["plan_rows"], info["actual_rows_per_loop"]
        if plan_rows > 0 and actual > 0:
            ratio = max(actual / plan_rows, plan_rows / actual)
            if ratio > THRESHOLDS["row_estimate_ratio"]:
                self._add_issue(
                    "medium", info,
                    f"통계 부정확 (예상 {plan_rows:,}, 실제 {actual:,}/루프, {ratio:.1f}x 오차)",
                    {"plan_rows": plan_rows, "actual_rows_per_loop": actual},
                    ["ANALYZE <table>로 통계 갱신",
                     "반복되면 ALTER TABLE ... SET STATISTICS 상향 또는 CREATE STATISTICS(다중 컬럼 상관) 검토"],
                )

        # 5. 정렬 디스크 스필
        if info.get("sort_space_type") == "Disk" or "external" in str(info.get("sort_method", "")).lower():
            self._add_issue(
                "high", info,
                f"정렬 디스크 스필 (method={info.get('sort_method')}, {info.get('sort_space_kb', 0):,}kB)",
                {"sort_method": info.get("sort_method"), "sort_space_kb": info.get("sort_space_kb")},
                ["해당 쿼리에서만 SET LOCAL work_mem 증가 (전역 상향은 세션x연산 수만큼 곱해지므로 위험)",
                 "ORDER BY 컬럼 인덱스로 정렬 자체 제거 가능한지 검토"],
            )

        # 6. Hash 스필 (배치 > 1)
        if info.get("hash_batches", 0) > 1:
            self._add_issue(
                "high", info,
                f"Hash 디스크 스필 (batches={info['hash_batches']}, peak {info.get('peak_memory_kb', 0):,}kB)",
                {"hash_batches": info["hash_batches"], "peak_memory_kb": info.get("peak_memory_kb")},
                ["SET LOCAL work_mem 또는 hash_mem_multiplier 상향 후 batches=1이 되는지 확인",
                 "조인 전에 행 수를 줄이는 조건/사전 필터 검토"],
            )

        # 7. Bitmap lossy 블록
        if info.get("lossy_heap_blocks", 0) > 0:
            self._add_issue(
                "medium", info,
                f"Bitmap lossy 모드 (exact={info.get('exact_heap_blocks', 0):,}, lossy={info['lossy_heap_blocks']:,})",
                {"lossy_heap_blocks": info["lossy_heap_blocks"]},
                ["work_mem 부족으로 비트맵이 압축됨 - SET LOCAL work_mem 증가 검토"],
            )

        # 8. Index Only Scan인데 heap fetch가 많음
        heap_fetches = info.get("heap_fetches", 0)
        if node_type == "Index Only Scan" and heap_fetches >= THRESHOLDS["heap_fetch_min"]:
            base = max(rows_total, 1)
            if heap_fetches / base > THRESHOLDS["heap_fetch_ratio"]:
                self._add_issue(
                    "medium", info,
                    f"Index Only Scan이 heap을 {heap_fetches:,}회 접근 (visibility map 미갱신)",
                    {"heap_fetches": heap_fetches, "rows": rows_total},
                    ["VACUUM <table>로 visibility map 갱신",
                     "쓰기가 많은 테이블이면 autovacuum 튜닝을 테이블 단위로 검토"],
                )

        # 9. temp 블록 사용 (해시/정렬 외 일반 스필 포함)
        temp_written = info.get("buffers", {}).get("temp_written_blocks", 0)
        if temp_written > 0 and not info.get("hash_batches", 0) > 1 \
                and info.get("sort_space_type") != "Disk":
            self._add_issue(
                "medium", info,
                f"임시 파일 쓰기 발생 ({temp_written:,} blocks)",
                {"temp_written_blocks": temp_written},
                ["work_mem 부족 신호 - 해당 쿼리 한정으로 SET LOCAL work_mem 조정 검토"],
            )

        # 10. 병렬 워커 미달
        planned = info.get("workers_planned")
        launched = info.get("workers_launched")
        if planned is not None and launched is not None and launched < planned:
            self._add_issue(
                "medium", info,
                f"병렬 워커 미달 (계획 {planned}, 실행 {launched})",
                {"workers_planned": planned, "workers_launched": launched},
                ["max_worker_processes / max_parallel_workers 대비 동시 병렬 쿼리 수 확인"],
            )

        # 11. I/O 대기 비중이 큰 노드 (track_io_timing 필요)
        io_ms = info.get("buffers", {}).get("io_read_time_ms", 0)
        if io_ms and info["inclusive_ms"] > 0 and io_ms / info["inclusive_ms"] > 0.5:
            self._add_issue(
                "info", info,
                f"노드 시간의 {io_ms / info['inclusive_ms']:.0%}가 I/O 읽기 대기 ({io_ms:.1f}ms)",
                {"io_read_time_ms": io_ms, "shared_read_blocks":
                 info.get("buffers", {}).get("shared_read_blocks")},
                ["반복 실행 시에도 read가 많으면 shared_buffers/캐시 적중 검토",
                 "PG18이면 AIO(io_method) 검토 대상 - 단, io_method 변경은 서버 재시작 필요"],
            )

    def _check_plan_level(self) -> None:
        # JIT 오버헤드
        jit = self.root.get("JIT")
        if jit:
            self.features.add("jit")
            jit_ms = _num(jit.get("Timing", {}).get("Total"))
            if self.execution_time and jit_ms / self.execution_time * 100 > THRESHOLDS["jit_share_pct"]:
                self.issues.append({
                    "severity": "medium",
                    "node_type": "JIT",
                    "relation": None,
                    "issue": f"JIT 컴파일이 실행 시간의 {jit_ms / self.execution_time:.0%} 차지 ({jit_ms:.1f}ms)",
                    "evidence": {"jit_total_ms": jit_ms, "execution_time_ms": self.execution_time},
                    "suggestions": ["짧은 쿼리에서 반복된다면 세션에서 SET jit = off 비교 벤치마크",
                                    "jit_above_cost 상향 검토"],
                })

        # 계획 시간이 지배적인 경우
        if (self.planning_time >= THRESHOLDS["planning_dominance_ms"]
                and self.planning_time > self.execution_time * 2):
            self.issues.append({
                "severity": "info",
                "node_type": "Planner",
                "relation": None,
                "issue": f"계획 시간({self.planning_time:.1f}ms)이 실행 시간({self.execution_time:.1f}ms)보다 큼",
                "evidence": {"planning_time_ms": self.planning_time,
                             "execution_time_ms": self.execution_time},
                "suggestions": ["자주 실행되는 쿼리면 prepared statement / plan_cache_mode 검토",
                                "파티션이 많다면 파티션 프루닝 조건 확인"],
            })

        # 트리거 시간
        for trig in self.root.get("Triggers", []):
            t_ms = _num(trig.get("Time"))
            if self.execution_time and t_ms / self.execution_time > 0.2:
                self.issues.append({
                    "severity": "medium",
                    "node_type": "Trigger",
                    "relation": trig.get("Relation"),
                    "issue": f"트리거 '{trig.get('Trigger Name')}'가 {t_ms:.1f}ms 소요",
                    "evidence": {"trigger_time_ms": t_ms, "calls": trig.get("Calls")},
                    "suggestions": ["트리거 내부 쿼리를 별도로 EXPLAIN ANALYZE",
                                    "대량 DML이면 FK 대상 컬럼 인덱스 확인"],
                })

    # ---- 리포트 ----------------------------------------------------------

    def _filter_columns(self, filter_str: str) -> str:
        columns = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:[=<>~]|IS |LIKE )", filter_str)
        exclude = {"AND", "OR", "NOT", "IS", "NULL", "LIKE", "ANY", "ALL"}
        cols = [c for c in dict.fromkeys(columns) if c.upper() not in exclude]
        return ", ".join(cols) if cols else "<filter 컬럼 확인 필요>"

    def _report(self) -> dict[str, Any]:
        self.issues.sort(key=lambda i: SEVERITY_ORDER.get(i["severity"], 9))

        top = sorted(self.nodes, key=lambda n: n["exclusive_ms"], reverse=True)
        top_nodes = []
        for n in top:
            pct = (n["exclusive_ms"] / self.execution_time * 100) if self.execution_time else 0
            entry = {
                "node_type": n["node_type"],
                "relation": n.get("relation"),
                "index": n.get("index"),
                "exclusive_ms": n["exclusive_ms"],
                "pct_of_execution": round(pct, 1),
                "rows_total": n["actual_rows_total"],
            }
            if pct >= THRESHOLDS["time_share_pct"]:
                entry["hot"] = True
            top_nodes.append(entry)

        return {
            "input_format": "json",
            "summary": {
                "planning_time_ms": self.planning_time,
                "execution_time_ms": self.execution_time,
                "total_nodes": len(self.nodes),
                "issue_count": {
                    sev: sum(1 for i in self.issues if i["severity"] == sev)
                    for sev in ("high", "medium", "info")
                },
                "detected_plan_features": sorted(self.features),
            },
            "top_time_nodes": top_nodes,
            "issues": self.issues,
            "nodes": self.nodes,
            "notes": [
                "exclusive_ms는 자식 노드 시간을 뺀 근사값이다 (병렬 워커/InitPlan은 오차 존재).",
                "모든 suggestions는 제안이며 이 스크립트는 어떤 SQL도 실행하지 않는다. "
                "DDL은 적용 전 선택도 확인과 벤치마크가 필요하다.",
            ] + self.notes,
        }


class TextPlanAnalyzer:
    """텍스트 포맷 EXPLAIN 출력의 제한적 분석기. JSON 포맷 사용을 권장."""

    NODE_RE = re.compile(
        r"^\s*(?:->\s*)?(?P<type>[A-Z][A-Za-z ]+?)"
        r"(?:\s+(?:on|using)\s+(?P<rel>\S+))?\s+\(cost="
    )
    ACTUAL_RE = re.compile(r"actual time=[\d.]+\.\.(?P<time>[\d.]+) rows=(?P<rows>\d+) loops=(?P<loops>\d+)")

    def __init__(self, text: str):
        self.text = text

    def analyze(self) -> dict[str, Any]:
        planning = execution = 0.0
        nodes: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = []

        for line in self.text.splitlines():
            if "Planning Time:" in line:
                m = re.search(r"([\d.]+)\s*ms", line)
                planning = float(m.group(1)) if m else 0.0
                continue
            if "Execution Time:" in line or "Total runtime:" in line:
                m = re.search(r"([\d.]+)\s*ms", line)
                execution = float(m.group(1)) if m else 0.0
                continue

            nm = self.NODE_RE.match(line)
            if nm:
                node: dict[str, Any] = {
                    "node_type": nm.group("type").strip(),
                    "relation": nm.group("rel"),
                }
                am = self.ACTUAL_RE.search(line)
                if am:
                    node["inclusive_ms"] = float(am.group("time")) * int(am.group("loops"))
                    node["actual_rows_total"] = int(am.group("rows")) * int(am.group("loops"))
                    node["loops"] = int(am.group("loops"))
                nodes.append(node)
                continue

            # 직전 노드의 상세 라인들
            if not nodes:
                continue
            last = nodes[-1]
            stripped = line.strip()
            if stripped.startswith("Rows Removed by Filter:"):
                last["rows_removed_by_filter"] = int(re.search(r"(\d+)", stripped).group(1))
            elif stripped.startswith("Sort Method:"):
                last["sort_method"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Heap Fetches:"):
                last["heap_fetches"] = int(re.search(r"(\d+)", stripped).group(1))
            elif stripped.startswith("Index Searches:"):
                last["index_searches"] = int(re.search(r"(\d+)", stripped).group(1))
            elif "Batches:" in stripped:
                bm = re.search(r"Batches:\s*(\d+)", stripped)
                if bm:
                    last["hash_batches"] = int(bm.group(1))

        for n in nodes:
            rows = n.get("actual_rows_total", 0)
            if n["node_type"].startswith("Seq Scan") and rows > THRESHOLDS["seq_scan_rows"]:
                issues.append({
                    "severity": "info",
                    "node_type": n["node_type"], "relation": n.get("relation"),
                    "issue": f"대량 Sequential Scan ({rows:,}행)",
                    "evidence": {"rows": rows},
                    "suggestions": ["JSON 포맷으로 재수집 후 필터/버퍼 근거와 함께 재분석 권장"],
                })
            if "external" in str(n.get("sort_method", "")).lower():
                issues.append({
                    "severity": "high",
                    "node_type": n["node_type"], "relation": n.get("relation"),
                    "issue": f"정렬 디스크 스필 ({n['sort_method']})",
                    "evidence": {"sort_method": n["sort_method"]},
                    "suggestions": ["해당 쿼리에서만 SET LOCAL work_mem 증가 검토"],
                })
            if n.get("hash_batches", 0) > 1:
                issues.append({
                    "severity": "high",
                    "node_type": n["node_type"], "relation": n.get("relation"),
                    "issue": f"Hash 디스크 스필 (batches={n['hash_batches']})",
                    "evidence": {"hash_batches": n["hash_batches"]},
                    "suggestions": ["SET LOCAL work_mem / hash_mem_multiplier 상향 검토"],
                })

        return {
            "input_format": "text",
            "summary": {
                "planning_time_ms": planning,
                "execution_time_ms": execution,
                "total_nodes": len(nodes),
                "issue_count": {
                    sev: sum(1 for i in issues if i["severity"] == sev)
                    for sev in ("high", "medium", "info")
                },
                "detected_plan_features": [],
            },
            "top_time_nodes": sorted(
                (n for n in nodes if "inclusive_ms" in n),
                key=lambda n: n["inclusive_ms"], reverse=True,
            ),
            "issues": issues,
            "nodes": nodes,
            "notes": [
                "텍스트 포맷은 버퍼/스필/추정 오차 분석이 제한된다. "
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)으로 재수집을 권장한다.",
            ],
        }


def load_json_plan(raw: str) -> list[dict[str, Any]] | None:
    """입력에서 EXPLAIN JSON을 최대한 관대하게 추출한다."""
    for candidate in (raw, raw[raw.find("["):raw.rfind("]") + 1] if "[" in raw else ""):
        if not candidate.strip():
            continue
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list) and data and isinstance(data[0], dict) and "Plan" in data[0]:
            return data
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EXPLAIN (ANALYZE) 출력 분석기 (읽기 전용, DB 접속 없음)")
    parser.add_argument("input", help="EXPLAIN 출력 파일 경로 또는 '-' (stdin)")
    parser.add_argument("--top", type=int, default=5,
                        help="시간 소비 상위 노드 표시 개수 (기본 5)")
    args = parser.parse_args()

    if args.input == "-":
        raw = sys.stdin.read()
    else:
        with open(args.input, encoding="utf-8") as f:
            raw = f.read()

    data = load_json_plan(raw)
    if data is not None:
        result = JsonPlanAnalyzer(data).analyze()
    else:
        result = TextPlanAnalyzer(raw).analyze()

    result["top_time_nodes"] = result["top_time_nodes"][:args.top]
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
