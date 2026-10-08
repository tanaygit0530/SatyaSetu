import json
import time
from pathlib import Path
from typing import List, Dict, Any
from app.services.verification_orchestrator import VerificationOrchestrator
from app.schemas.enums import Verdict

def evaluate_subset(sample_size_per_class: int = 2):
    """
    Evaluates a balanced slice from the 175-claim dataset and calculates
    precision, recall, F1, accuracy, and latency breakdown.
    """
    dataset_path = Path(__file__).parent / "data" / "evaluation_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    by_verdict: Dict[str, List[Dict[str, Any]]] = {}
    for item in data:
        by_verdict.setdefault(item["expected_verdict"], []).append(item)
        
    sampled: List[Dict[str, Any]] = []
    for v, items in by_verdict.items():
        sampled.extend(items[:sample_size_per_class])
        
    orc = VerificationOrchestrator()
    results = []
    latencies = []
    
    print(f"Starting evaluation of {len(sampled)} claims across 5 verdict classes...")
    for idx, item in enumerate(sampled, 1):
        claim = item["claim_text"]
        expected = item["expected_verdict"]
        t0 = time.perf_counter()
        res = orc.verify(content=claim)
        dur_ms = int((time.perf_counter() - t0) * 1000)
        actual = res.overall_verdict.value if res.overall_verdict else "CANNOT_BE_CONFIRMED"
        latencies.append(dur_ms)
        
        match = (expected == actual)
        results.append({
            "id": item["claim_id"],
            "claim": claim,
            "expected": expected,
            "actual": actual,
            "match": match,
            "dur_ms": dur_ms,
            "timing_ms": res.timing_ms or {}
        })
        print(f"[{idx}/{len(sampled)}] '{claim[:40]}...' Expected: {expected} | Actual: {actual} | Match: {match} ({dur_ms}ms)")

    # Metrics computation
    total = len(results)
    correct = sum(1 for r in results if r["match"])
    accuracy = correct / total if total > 0 else 0.0
    
    # Per-class metrics
    classes = ["VERIFIED", "FALSE", "PARTLY_SUPPORTED", "OUTDATED", "CANNOT_BE_CONFIRMED"]
    print("\n" + "="*50)
    print("EVALUATION SCOREBOARD")
    print("="*50)
    print(f"Total Evaluated: {total}")
    print(f"Overall Accuracy: {accuracy*100:.1f}% ({correct}/{total})")
    
    for c in classes:
        tp = sum(1 for r in results if r["expected"] == c and r["actual"] == c)
        fp = sum(1 for r in results if r["expected"] != c and r["actual"] == c)
        fn = sum(1 for r in results if r["expected"] == c and r["actual"] != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        print(f"Class {c:20s}: Precision: {prec*100:.1f}%, Recall: {rec*100:.1f}%, F1: {f1:.2f} (TP={tp}, FP={fp}, FN={fn})")
        
    latencies.sort()
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p90 = latencies[int(len(latencies) * 0.9)] if latencies else 0
    print(f"\nLatency: P50 = {p50}ms | P90 = {p90}ms | Avg = {sum(latencies)/len(latencies):.0f}ms")
    print("="*50 + "\n")
    return results

if __name__ == "__main__":
    evaluate_subset(sample_size_per_class=1)
