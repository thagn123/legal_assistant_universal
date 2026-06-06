import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.query_planner import QueryPlanner

planner = QueryPlanner()
q = "Đất nhà tôi bị thu hồi để làm đường, hòa giải tại xã không thành. Bước tiếp theo là gì?"
plan = planner.plan(q)

with open("planner_test_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Query: {q}\n")
    f.write(f"Detected Domain: {plan.detected_domain}\n")
    f.write(f"Domain Confidence: {plan.domain_confidence}\n")
    f.write(f"Dispute Type: {plan.dispute_type}\n")
    f.write(f"Strategy: {plan.retrieval_strategy}\n")
    f.write(f"Variants: {plan.query_variants}\n")
    f.write(f"Entities: {plan.extracted_entities}\n")
