"""
Retrieval Benchmark Script — LexAI / ULKA

30 Vietnamese legal queries → measure retrieval quality per checklist targets.

Usage:
    # With live backend (recommended for real metrics):
    BASE_URL=http://localhost:8001 python scripts/benchmark_retrieval.py

    # Without live backend (TestClient fallback — no real MongoDB, mostly fallback):
    python scripts/benchmark_retrieval.py

Output:
    qa/retrieval_benchmark_results.json
    qa/retrieval_benchmark_report.md

Targets (from docs/production_qa_checklist.md):
    top-1 domain accuracy  >= 85%
    top-3 domain accuracy  >= 90%
    cross-domain error     = 0%
    empty rate             = 0%
    fallback/demo rate     <= 30%
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is on sys.path so `src` is importable when running
# directly: python scripts/benchmark_retrieval.py
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Force UTF-8 stdout on Windows so Vietnamese characters print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 30 benchmark queries ──────────────────────────────────────────────────────

BENCHMARK_QUERIES: List[Dict[str, Any]] = [
    # dat_dai (Q01–Q08)
    {"id": "Q01", "query": "Hàng xóm lấn chiếm đất sổ đỏ của tôi 50cm, tôi làm gì?", "expected_domain": "dat_dai"},
    {"id": "Q02", "query": "Chưa có sổ đỏ ở 20 năm, bên cạnh đòi lấy đất, làm sao?", "expected_domain": "dat_dai"},
    {"id": "Q03", "query": "GCN QSDĐ bị UBND thu hồi không bồi thường, khiếu nại ở đâu?", "expected_domain": "dat_dai"},
    {"id": "Q04", "query": "Bản photo sổ đỏ có giá trị pháp lý tranh chấp không?", "expected_domain": "dat_dai"},
    {"id": "Q05", "query": "Đất mua bằng giấy tay, bên bán không công chứng, xử lý thế nào?", "expected_domain": "dat_dai"},
    {"id": "Q06", "query": "UBND ra quyết định thu hồi đất sai quy trình, tôi có quyền khiếu nại?", "expected_domain": "dat_dai"},
    {"id": "Q07", "query": "Thủ tục sang tên sổ đỏ sau khi mua bán đất?", "expected_domain": "dat_dai"},
    {"id": "Q08", "query": "Đất tranh chấp đã qua hòa giải UBND không thành, bước tiếp theo?", "expected_domain": "dat_dai"},
    # lao_dong (Q09–Q14)
    {"id": "Q09", "query": "Công ty sa thải không có lý do, không trả lương tháng cuối, tôi đòi gì?", "expected_domain": "lao_dong"},
    {"id": "Q10", "query": "Bị cho thôi việc trái luật, thời hạn khởi kiện là bao lâu?", "expected_domain": "lao_dong"},
    {"id": "Q11", "query": "Công ty trả lương dưới mức lương tối thiểu vùng, tôi có quyền gì?", "expected_domain": "lao_dong"},
    {"id": "Q12", "query": "Tai nạn lao động tại xưởng, công ty không bồi thường, phải làm sao?", "expected_domain": "lao_dong"},
    {"id": "Q13", "query": "Hợp đồng lao động hết hạn mà công ty không ký tiếp, quyền lợi của tôi?", "expected_domain": "lao_dong"},
    {"id": "Q14", "query": "Bên thuê nhà không trả tiền đặt cọc khi hết hợp đồng thuê?", "expected_domain": "hop_dong"},
    # gia_dinh / dan_su (Q15–Q19)
    {"id": "Q15", "query": "Muốn ly hôn đơn phương vì chồng bạo lực, có con 3 tuổi, làm thế nào?", "expected_domain": "gia_dinh"},
    {"id": "Q16", "query": "Sau ly hôn tranh chấp quyền nuôi con dưới 36 tháng tuổi, ai được nuôi?", "expected_domain": "gia_dinh"},
    {"id": "Q17", "query": "Vợ chồng ly hôn, nhà chung tài sản chia như thế nào?", "expected_domain": "gia_dinh"},
    {"id": "Q18", "query": "Cha mẹ mất không có di chúc, anh chị em tranh chấp thừa kế nhà đất?", "expected_domain": "dan_su"},
    {"id": "Q19", "query": "Di chúc viết tay có giá trị pháp lý không, cần điều kiện gì?", "expected_domain": "dan_su"},
    # hop_dong (Q20–Q23)
    {"id": "Q20", "query": "Hợp đồng đã ký bên kia không thực hiện, tôi đòi phạt vi phạm được không?", "expected_domain": "hop_dong"},
    {"id": "Q21", "query": "Đặt cọc mua bán nhà, bên bán đổi ý không bán nữa, lấy lại tiền cọc thế nào?", "expected_domain": "hop_dong"},
    {"id": "Q22", "query": "Hợp đồng dịch vụ chưa ký, bên kia đã nhận tiền rồi không làm, đòi lại được không?", "expected_domain": "hop_dong"},
    {"id": "Q23", "query": "Điều khoản phạt trong hợp đồng thương mại tối đa bao nhiêu phần trăm?", "expected_domain": "hop_dong"},
    # hanh_chinh (Q24–Q25)
    {"id": "Q24", "query": "Bị phạt vi phạm hành chính oan, thủ tục khiếu nại quyết định xử phạt?", "expected_domain": "hanh_chinh"},
    {"id": "Q25", "query": "Cơ quan nhà nước ra quyết định sai, tôi khởi kiện hành chính ở đâu?", "expected_domain": "hanh_chinh"},
    # edge cases (Q26–Q30)
    {"id": "Q26", "query": "so do cua toi bi hang xom tranh chap ranh gioi", "expected_domain": "dat_dai"},  # no diacritics
    {"id": "Q27", "query": "Sa thải trái luật + tranh chấp đất đai cùng lúc, cần ưu tiên cái gì trước?", "expected_domain": "lao_dong"},  # multi-domain
    {"id": "Q28", "query": "Hôm nay thời tiết đẹp, đi đâu ăn?", "expected_domain": "general"},  # non-legal
    {"id": "Q29", "query": "luat lao dong viet nam quy dinh gi ve thi gian nghi phep nam", "expected_domain": "lao_dong"},  # no diacritics
    {"id": "Q30", "query": "Công ty nợ lương 3 tháng, giờ tuyên bố phá sản, quyền lợi công nhân?", "expected_domain": "lao_dong"},
]

# Critical domains where cross-domain error = 0% (hard gate)
_CRITICAL_CROSS_DOMAIN_PAIRS: List[Tuple[str, str]] = [
    ("dat_dai", "lao_dong"),
    ("lao_dong", "dat_dai"),
    ("gia_dinh", "lao_dong"),
    ("hop_dong", "lao_dong"),
]


# ── Client setup ──────────────────────────────────────────────────────────────

def _build_client(base_url: str):
    """Return (client, mode) — 'http' or 'testclient'."""
    if base_url:
        try:
            import httpx
            # 60s timeout: first request loads the embedding model (~15s) + Atlas latency
            c = httpx.Client(base_url=base_url, timeout=60.0)
            c.get("/health")  # connectivity check
            # Warmup: embed one dummy request so model is cached before timed queries
            try:
                c.post("/retrieval/similar-cases",
                       json={"situation": "warmup", "limit": 1, "include_community": False},
                       headers={"X-User-ID": "benchmark_warmup"})
                print("[INFO] Warmup request done (embedding model loaded).")
            except Exception:
                pass
            return c, "http"
        except Exception as exc:
            print(f"[WARN] Cannot reach {base_url}: {exc} — falling back to TestClient")

    # TestClient fallback
    from fastapi.testclient import TestClient
    from src.api.app import create_app
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    c = TestClient(app, raise_server_exceptions=False)
    return c, "testclient"


def _post(client, mode: str, path: str, payload: dict) -> dict:
    headers = {"X-User-ID": "benchmark_user"}
    t0 = time.perf_counter()
    try:
        if mode == "http":
            resp = client.post(path, json=payload, headers=headers)
        else:
            resp = client.post(path, json=payload, headers=headers)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        if resp.status_code == 200:
            return {"ok": True, "body": resp.json(), "elapsed_ms": elapsed_ms, "status": 200}
        return {"ok": False, "body": {}, "elapsed_ms": elapsed_ms, "status": resp.status_code}
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"ok": False, "body": {}, "elapsed_ms": elapsed_ms, "status": -1, "error": str(exc)}


# ── Per-query measurement ──────────────────────────────────────────────────────

def _run_one(client, mode: str, q: Dict[str, Any]) -> Dict[str, Any]:
    qid = q["id"]
    query = q["query"]
    expected = q["expected_domain"]

    result = _post(client, mode, "/retrieval/similar-cases", {
        "situation": query,
        "include_community": False,
        "persist_anonymized": False,
        "limit": 6,
    })

    body = result["body"]
    ok = result["ok"]

    top_1_domain: Optional[str] = None
    top_3_domains: List[str] = []
    top_1_score: float = 0.0
    top_3_scores: List[float] = []
    is_fallback = False
    is_demo = False
    empty_result = True

    if ok and body:
        cases = body.get("official_cases", [])
        is_fallback = body.get("fallback_used", False) or body.get("search_mode") in ("demo_fallback", "keyword")
        empty_result = len(cases) == 0

        for i, case in enumerate(cases[:3]):
            dom = case.get("domain", "")
            score = case.get("similarity_score", 0.0)
            if i == 0:
                top_1_domain = dom
                top_1_score = score
            top_3_domains.append(dom)
            top_3_scores.append(score)
            if case.get("is_demo"):
                is_demo = True

    # Domain match
    top1_match = (top_1_domain == expected) if top_1_domain else (expected == "general")
    top3_match = (expected in top_3_domains) if top_3_domains else (expected == "general")

    # Cross-domain error: critical pair mismatch
    cross_domain_error = False
    if top_1_domain and top_1_domain != expected and expected != "general":
        for src, bad in _CRITICAL_CROSS_DOMAIN_PAIRS:
            if expected == src and top_1_domain == bad:
                cross_domain_error = True

    return {
        "query_id": qid,
        "query": query,
        "expected_domain": expected,
        "top_1_domain": top_1_domain,
        "top_3_domains": top_3_domains,
        "top_1_score": top_1_score,
        "top_3_scores": top_3_scores,
        "top1_match": top1_match,
        "top3_match": top3_match,
        "is_fallback": is_fallback,
        "is_demo": is_demo,
        "empty_result": empty_result,
        "cross_domain_error": cross_domain_error,
        "http_ok": ok,
        "elapsed_ms": result["elapsed_ms"],
        "notes": "" if ok else f"HTTP {result.get('status')}",
    }


# ── Metrics computation ───────────────────────────────────────────────────────

def _compute_metrics(rows: List[Dict[str, Any]], mode: str) -> Dict[str, Any]:
    total = len(rows)
    non_general = [r for r in rows if r["expected_domain"] != "general"]

    top1_correct = sum(1 for r in non_general if r["top1_match"])
    top3_correct = sum(1 for r in non_general if r["top3_match"])
    fallback_demo = sum(1 for r in rows if r["is_fallback"] or r["is_demo"])
    empty = sum(1 for r in rows if r["empty_result"])
    cross_err = sum(1 for r in rows if r["cross_domain_error"])
    http_errors = sum(1 for r in rows if not r["http_ok"])

    scores = [r["top_1_score"] for r in rows if r["top_1_score"] > 0]
    avg_top1_score = round(sum(scores) / len(scores), 4) if scores else 0.0

    n_non_general = len(non_general) or 1
    top1_acc = round(top1_correct / n_non_general * 100, 1)
    top3_acc = round(top3_correct / n_non_general * 100, 1)
    fallback_rate = round(fallback_demo / total * 100, 1)
    empty_rate = round(empty / total * 100, 1)
    cross_err_rate = round(cross_err / n_non_general * 100, 1)

    # Worst 5 by score
    sorted_by_score = sorted(rows, key=lambda r: r["top_1_score"])
    worst_5 = [{"id": r["query_id"], "score": r["top_1_score"], "fallback": r["is_fallback"]} for r in sorted_by_score[:5]]

    # Gate evaluation
    targets = {
        "top1_accuracy_pct": {"value": top1_acc, "target": 85.0, "op": ">="},
        "top3_accuracy_pct": {"value": top3_acc, "target": 90.0, "op": ">="},
        "cross_domain_error_pct": {"value": cross_err_rate, "target": 0.0, "op": "=="},
        "empty_rate_pct": {"value": empty_rate, "target": 0.0, "op": "=="},
        "fallback_demo_rate_pct": {"value": fallback_rate, "target": 30.0, "op": "<="},
    }
    gate_fails = []
    for name, spec in targets.items():
        v, t, op = spec["value"], spec["target"], spec["op"]
        if op == ">=" and v < t:
            gate_fails.append(f"{name}: {v} < {t} (target)")
        elif op == "==" and v != t:
            gate_fails.append(f"{name}: {v} != {t} (target)")
        elif op == "<=" and v > t:
            gate_fails.append(f"{name}: {v} > {t} (target)")

    return {
        "mode": mode,
        "total_queries": total,
        "non_general_queries": len(non_general),
        "top1_domain_accuracy_pct": top1_acc,
        "top3_domain_accuracy_pct": top3_acc,
        "fallback_demo_rate_pct": fallback_rate,
        "empty_rate_pct": empty_rate,
        "cross_domain_error_rate_pct": cross_err_rate,
        "average_top1_score": avg_top1_score,
        "http_error_count": http_errors,
        "worst_5_queries": worst_5,
        "gate_fails": gate_fails,
        "gate_pass": len(gate_fails) == 0,
        "targets": targets,
    }


# ── Report writers ────────────────────────────────────────────────────────────

def _write_json(rows: List[Dict], metrics: Dict, qa_dir: Path):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        "rows": rows,
    }
    out = qa_dir / "retrieval_benchmark_results.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON: {out}")


def _write_md(rows: List[Dict], metrics: Dict, qa_dir: Path):
    m = metrics
    gate_label = "✅ PASS" if m["gate_pass"] else "❌ FAIL"

    lines = [
        "# Retrieval Benchmark Report — LexAI / ULKA",
        f"\n**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Mode:** {m['mode']} (testclient = no real MongoDB)",
        f"**Gate:** {gate_label}\n",
        "## Metrics vs Targets\n",
        "| Metric | Value | Target | Status |",
        "|---|---|---|---|",
    ]
    target_rows = [
        ("top-1 domain accuracy", f"{m['top1_domain_accuracy_pct']}%", "≥85%", m["top1_domain_accuracy_pct"] >= 85),
        ("top-3 domain accuracy", f"{m['top3_domain_accuracy_pct']}%", "≥90%", m["top3_domain_accuracy_pct"] >= 90),
        ("cross-domain error", f"{m['cross_domain_error_rate_pct']}%", "0%", m["cross_domain_error_rate_pct"] == 0),
        ("empty rate", f"{m['empty_rate_pct']}%", "0%", m["empty_rate_pct"] == 0),
        ("fallback/demo rate", f"{m['fallback_demo_rate_pct']}%", "≤30%", m["fallback_demo_rate_pct"] <= 30),
        ("avg top-1 score", str(m["average_top1_score"]), "≥0.55", m["average_top1_score"] >= 0.55),
    ]
    for name, value, target, passing in target_rows:
        icon = "✅" if passing else "❌"
        lines.append(f"| {name} | {value} | {target} | {icon} |")

    if m["gate_fails"]:
        lines += ["\n## Gate Failures\n"]
        for fail in m["gate_fails"]:
            lines.append(f"- ❌ {fail}")

    lines += [
        "\n## Per-query Results\n",
        "| ID | Expected | Top-1 | Score | T1✓ | T3✓ | Fallback | Demo | Empty | XDomain |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['query_id']} | {r['expected_domain']} | {r['top_1_domain'] or '—'} "
            f"| {r['top_1_score']:.2f} | {'✅' if r['top1_match'] else '❌'} "
            f"| {'✅' if r['top3_match'] else '❌'} | {'Y' if r['is_fallback'] else ''} "
            f"| {'Y' if r['is_demo'] else ''} | {'Y' if r['empty_result'] else ''} "
            f"| {'⚠️' if r['cross_domain_error'] else ''} |"
        )

    lines += ["\n## Worst 5 Queries by Score\n", "| ID | Score | Fallback |", "|---|---|---|"]
    for w in m["worst_5_queries"]:
        lines.append(f"| {w['id']} | {w['score']:.3f} | {'Y' if w['fallback'] else ''} |")

    if m["mode"] == "testclient":
        lines += [
            "\n> **Note:** Results from TestClient with no real MongoDB.",
            "> All queries use demo fallback data. Metrics reflect fallback behavior,",
            "> NOT real retrieval quality. Run with a live backend for meaningful benchmarks.",
        ]

    out = qa_dir / "retrieval_benchmark_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] MD:   {out}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    base_url = os.getenv("BASE_URL", "").rstrip("/")
    qa_dir = Path(__file__).parent.parent / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Base URL: {base_url or '(none — TestClient fallback)'}")
    print(f"[INFO] Running {len(BENCHMARK_QUERIES)} benchmark queries...")

    client, mode = _build_client(base_url)
    print(f"[INFO] Mode: {mode}\n")

    rows: List[Dict[str, Any]] = []
    for i, q in enumerate(BENCHMARK_QUERIES, 1):
        sys.stdout.write(f"  [{i:02d}/{len(BENCHMARK_QUERIES)}] {q['id']} — {q['query'][:60]}... ")
        sys.stdout.flush()
        row = _run_one(client, mode, q)
        rows.append(row)
        t1 = "✅" if row["top1_match"] else "❌"
        fb = " (fallback)" if row["is_fallback"] else ""
        print(f"{t1} top1={row['top_1_domain'] or '—'} score={row['top_1_score']:.2f}{fb} {row['elapsed_ms']}ms")

    metrics = _compute_metrics(rows, mode)

    print(f"\n{'='*60}")
    print(f"  Benchmark complete — mode={mode}")
    print(f"  top-1 accuracy : {metrics['top1_domain_accuracy_pct']}% (target ≥85%)")
    print(f"  top-3 accuracy : {metrics['top3_domain_accuracy_pct']}% (target ≥90%)")
    print(f"  fallback/demo  : {metrics['fallback_demo_rate_pct']}% (target ≤30%)")
    print(f"  empty rate     : {metrics['empty_rate_pct']}% (target 0%)")
    print(f"  cross-domain   : {metrics['cross_domain_error_rate_pct']}% (target 0%)")
    print(f"  gate           : {'PASS' if metrics['gate_pass'] else 'FAIL'}")
    if metrics["gate_fails"]:
        for fail in metrics["gate_fails"]:
            print(f"  ❌ {fail}")
    print(f"{'='*60}\n")

    _write_json(rows, metrics, qa_dir)
    _write_md(rows, metrics, qa_dir)

    if mode == "testclient":
        print(
            "\n[WARN] TestClient mode: metrics reflect demo/fallback behavior only.\n"
            "       Set BASE_URL=http://localhost:8001 and run with a live backend\n"
            "       to measure real retrieval quality.\n"
        )

    return 0 if metrics["gate_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
