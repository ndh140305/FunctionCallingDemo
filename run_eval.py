"""
run_eval.py

Chạy đánh giá chatbot Function Calling trên eval_dataset.jsonl.

Metrics được tính:
  - Tool Selection Accuracy   : % câu mà tập tool được gọi KHỚP HOÀN TOÀN với expected
  - Precision (macro avg)     : trong số tool được gọi, bao nhiêu % đúng
  - Recall (macro avg)        : trong số tool cần gọi, bao nhiêu % được gọi
  - F1 Score (macro avg)      : trung bình điều hòa Precision và Recall
  - No-Tool Rate              : % câu model không gọi tool nào (khi lẽ ra phải gọi)
  - Hallucination Rate        : % câu model gọi tool không tồn tại
  - Per-category Accuracy     : accuracy riêng cho weather / math / pdf
  - Avg latency               : thời gian xử lý trung bình mỗi câu (giây)
"""

import json
import os
import sys
import time
from collections import defaultdict
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

# Import pipeline chính từ evaluate.py
from evaluate import process_user_prompt, AVAILABLE_FUNCTIONS

# ─── Cấu hình ─────────────────────────────────────────────────────────────────

EVAL_PATH  = "data/eval_dataset.jsonl"
RESULT_PATH = "data/eval_results.jsonl"

# Giới hạn số mẫu chạy (None = chạy tất cả)
MAX_SAMPLES = 50


# ─── Helpers ──────────────────────────────────────────────────────────────────

KNOWN_TOOLS = set(AVAILABLE_FUNCTIONS.keys())

def compute_set_metrics(predicted: set, expected: set) -> dict:
    """Tính precision, recall, F1 giữa 2 tập tool names."""
    if not expected and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not expected:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not predicted:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}

    tp = len(predicted & expected)
    precision = tp / len(predicted)
    recall    = tp / len(expected)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def get_category(expected_tools: list[str]) -> str:
    """Phân loại câu hỏi dựa trên expected tools."""
    tool_set = set(expected_tools)
    if "get_current_weather" in tool_set:
        return "weather"
    if "calculate_expression" in tool_set:
        return "math"
    if "read_pdf_file" in tool_set:
        return "pdf"
    return "other"


# ─── Evaluation Loop ──────────────────────────────────────────────────────────

def run_evaluation():
    if not os.path.exists(EVAL_PATH):
        print(f"[ERROR] Không tìm thấy {EVAL_PATH}")
        print("  Hãy chạy: python build_eval_dataset.py trước.")
        return

    samples = []
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if MAX_SAMPLES:
        samples = samples[:MAX_SAMPLES]

    total = len(samples)
    print(f"\n{'='*60}")
    print(f"  Bắt đầu đánh giá: {total} mẫu")
    print(f"  Model: llama-3.3-70b-versatile (Groq)")
    print(f"{'='*60}\n")

    # Tích lũy số liệu
    exact_match_count = 0
    no_tool_count     = 0
    hallucination_count = 0
    precisions, recalls, f1s = [], [], []
    category_stats = defaultdict(lambda: {"total": 0, "exact": 0})
    latencies = []
    results   = []

    for idx, sample in enumerate(samples, 1):
        query          = sample["user_query"]
        expected_tools = set(sample["expected_tools"])
        category       = get_category(sample["expected_tools"])

        print(f"[{idx:>3}/{total}] {category.upper():7} | {query[:70]}")

        t0 = time.time()
        try:
            output = process_user_prompt(query)
        except Exception as e:
            print(f"          ⚠ Lỗi: {e}")
            output = {"tool_calls": [], "tool_results": [], "final_answer": f"ERROR: {e}"}
        latency = time.time() - t0

        predicted_tools = {tc["name"] for tc in output.get("tool_calls", [])}

        # Metrics
        exact = (predicted_tools == expected_tools)
        no_tool = len(predicted_tools) == 0
        hallucination = bool(predicted_tools - KNOWN_TOOLS)

        m = compute_set_metrics(predicted_tools, expected_tools)

        exact_match_count  += int(exact)
        no_tool_count      += int(no_tool)
        hallucination_count += int(hallucination)
        precisions.append(m["precision"])
        recalls.append(m["recall"])
        f1s.append(m["f1"])
        latencies.append(latency)

        category_stats[category]["total"] += 1
        category_stats[category]["exact"] += int(exact)

        status = "✅" if exact else ("🔇" if no_tool else "❌")
        print(f"          {status} expected={sorted(expected_tools)} | got={sorted(predicted_tools)} | {latency:.1f}s")

        # Lưu kết quả chi tiết
        results.append({
            "query":           query,
            "category":        category,
            "expected_tools":  sorted(expected_tools),
            "predicted_tools": sorted(predicted_tools),
            "exact_match":     exact,
            "no_tool":         no_tool,
            "hallucination":   hallucination,
            "precision":       round(m["precision"], 4),
            "recall":          round(m["recall"],    4),
            "f1":              round(m["f1"],        4),
            "latency_sec":     round(latency,        2),
            "final_answer":    output.get("final_answer", ""),
        })

    # ─── Lưu kết quả chi tiết ──────────────────────────────────────────────────
    os.makedirs("data", exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ─── In báo cáo tổng hợp ───────────────────────────────────────────────────
    avg_p  = sum(precisions) / total if total else 0
    avg_r  = sum(recalls)    / total if total else 0
    avg_f1 = sum(f1s)        / total if total else 0
    avg_lat = sum(latencies) / total if total else 0

    print(f"\n{'='*60}")
    print(f"  KẾT QUẢ ĐÁNH GIÁ  ({total} mẫu)")
    print(f"{'='*60}")
    print(f"  Tool Selection Accuracy : {exact_match_count}/{total}  = {exact_match_count/total*100:5.1f}%")
    print(f"  Precision (macro avg)   : {avg_p*100:5.1f}%")
    print(f"  Recall    (macro avg)   : {avg_r*100:5.1f}%")
    print(f"  F1 Score  (macro avg)   : {avg_f1*100:5.1f}%")
    print(f"  No-Tool Rate            : {no_tool_count}/{total}  = {no_tool_count/total*100:5.1f}%")
    print(f"  Hallucination Rate      : {hallucination_count}/{total}  = {hallucination_count/total*100:5.1f}%")
    print(f"  Avg Latency             : {avg_lat:.2f}s / query")
    print(f"{'─'*60}")
    print(f"  Accuracy theo danh mục:")
    for cat in ["weather", "math", "pdf", "other"]:
        s = category_stats.get(cat)
        if s and s["total"] > 0:
            acc = s["exact"] / s["total"] * 100
            print(f"    [{cat:<8}]  {s['exact']}/{s['total']}  =  {acc:5.1f}%")
    print(f"{'─'*60}")
    print(f"  Kết quả chi tiết → {RESULT_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_evaluation()
