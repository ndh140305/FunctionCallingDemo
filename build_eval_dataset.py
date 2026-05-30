"""
build_eval_dataset.py

Dùng Groq API để phân loại từng query trong demo_dataset.jsonl.
Với mỗi query, hỏi LLM: "Tool nào trong 4 tool hiện có cần dùng để trả lời?"
Nếu không tool nào phù hợp → loại bỏ mẫu đó.

Output: data/eval_dataset.jsonl
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
from groq import Groq

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

INPUT_PATH   = "data/demo_dataset.jsonl"
OUTPUT_PATH  = "data/eval_dataset.jsonl"

CLASSIFIER_MODEL = "llama-3.1-8b-instant"

BATCH_START = 601
BATCH_END   = 1000

REQUEST_DELAY = 0.5

MAX_RETRIES = 3

TOOL_DESCRIPTIONS = """
Bạn là classifier. Nhiệm vụ: xác định tool nào cần dùng để trả lời query.

Danh sách tool có sẵn:
1. get_coordinates  – Chuyển tên địa danh → tọa độ lat/lon. Phải gọi TRƯỚC khi gọi get_current_weather.
2. get_current_weather – Lấy thời tiết hiện tại theo tọa độ (nhiệt độ, mô tả, độ ẩm, gió). Luôn cần get_coordinates trước.
3. calculate_expression – Tính toán biểu thức toán học thuần túy (sqrt, sin, log, phép tính số học...).
4. read_pdf_file – Đọc và trích xuất nội dung từ file PDF.

Quy tắc:
- Nếu query hỏi về thời tiết / nhiệt độ / khí hậu của địa điểm → trả về ["get_coordinates", "get_current_weather"]
- Nếu query yêu cầu tính toán biểu thức toán học cụ thể → trả về ["calculate_expression"]
- Nếu query yêu cầu đọc / tóm tắt file PDF → trả về ["read_pdf_file"]
- Nếu query KHÔNG phù hợp với bất kỳ tool nào (tài chính, cơ sở dữ liệu, đặt hàng, lập lịch, v.v.) → trả về []

Trả lời chỉ bằng JSON array, không giải thích thêm.
Ví dụ hợp lệ: ["get_coordinates", "get_current_weather"]
Ví dụ hợp lệ: ["calculate_expression"]
Ví dụ hợp lệ: []
"""

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def classify_with_llm(query: str) -> list[str]:
    """
    Gửi query lên Groq, nhận lại danh sách tool cần gọi.
    Trả về list rỗng nếu không phù hợp hoặc gặp lỗi parse.
    """
    prompt = f'Query: "{query}"\n\nTrả lời (chỉ JSON array):'

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=CLASSIFIER_MODEL,
                messages=[
                    {"role": "system", "content": TOOL_DESCRIPTIONS},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0,
                max_tokens=64,
            )
            raw = response.choices[0].message.content.strip()

            start = raw.find("[")
            end   = raw.rfind("]") + 1
            if start != -1 and end > start:
                parsed = json.loads(raw[start:end])
                valid_tools = {
                    "get_coordinates", "get_current_weather",
                    "calculate_expression", "read_pdf_file",
                }
                return [t for t in parsed if t in valid_tools]
            return []

        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                wait = 2 ** attempt * 2
                print(f"          ⏳ Rate limit – chờ {wait}s...")
                time.sleep(wait)
            else:
                print(f"          ⚠ Lỗi classify: {err_str[:80]}")
                return []

    return []


def build_eval_dataset():
    if not os.path.exists(INPUT_PATH):
        print(f"[ERROR] Không tìm thấy {INPUT_PATH}")
        return

    all_samples = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if row.get("user_query"):
                    all_samples.append(row)
            except json.JSONDecodeError:
                continue

    batch_samples = all_samples[BATCH_START - 1 : BATCH_END]
    total         = len(batch_samples)

    processed_queries = set()
    existing_rows = []
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        processed_queries.add(r["user_query"])
                        existing_rows.append(r)
                    except Exception:
                        pass
        if processed_queries:
            print(f"  ↩ Resume: đã có {len(processed_queries)} mẫu, bỏ qua...")

    kept = len(existing_rows)
    skipped_none = 0
    category_counts = {
        "weather": sum(1 for r in existing_rows if "get_current_weather" in r["expected_tools"]),
        "math":    sum(1 for r in existing_rows if "calculate_expression" in r["expected_tools"]),
        "pdf":     sum(1 for r in existing_rows if "read_pdf_file" in r["expected_tools"]),
    }

    print(f"\n{'='*60}")
    print(f"  Build Eval Dataset  (LLM classifier: {CLASSIFIER_MODEL})")
    print(f"{'='*60}")
    print(f"  Batch              : [{BATCH_START} – {BATCH_END}]  ({total:,} mẫu)")
    print(f"  Đã có trong output : {len(processed_queries):,} mẫu (resume)")
    print()

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_PATH, "a", encoding="utf-8") as fout:
        for idx, row in enumerate(batch_samples, BATCH_START):
            query = row["user_query"]

            if query in processed_queries:
                continue

            print(f"[{idx:>4}/{BATCH_END}] {query[:72]}")

            tools = classify_with_llm(query)
            time.sleep(REQUEST_DELAY)

            if not tools:
                skipped_none += 1
                print(f"         → ⊘ Không phù hợp, bỏ qua")
                continue

            eval_row = {
                "user_query":     query,
                "expected_tools": tools,
                "original_expected_action": row.get("expected_action", ""),
            }
            fout.write(json.dumps(eval_row, ensure_ascii=False) + "\n")
            fout.flush()
            kept += 1

            cat_label = (
                "weather" if "get_current_weather" in tools else
                "math"    if "calculate_expression" in tools else
                "pdf"     if "read_pdf_file"        in tools else "other"
            )
            category_counts[cat_label] = category_counts.get(cat_label, 0) + 1
            print(f"         → ✅ [{cat_label}] {tools}")

    newly_added = kept - len(existing_rows)
    print(f"\n{'='*60}")
    print(f"  Hoàn thành!")
    print(f"{'='*60}")
    print(f"  Batch [{BATCH_START}–{BATCH_END}]         : {total:>6,} mẫu")
    print(f"  Thêm mới batch này  : {newly_added:>6,} mẫu")
    print(f"  Bị loại (batch này) : {skipped_none:>6,} mẫu (không phù hợp tool)")
    print(f"  Tổng output hiện có : {kept:>6,} mẫu")
    print(f"{'─'*60}")
    for cat, cnt in category_counts.items():
        if cnt:
            print(f"  Nhóm [{cat:<8}]    : {cnt:>6,} mẫu")
    print(f"{'─'*60}")
    print(f"  Output → {OUTPUT_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    build_eval_dataset()
