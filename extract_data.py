import os
import json
from datasets import load_dataset

def extract_xlam_subset():
    dataset = load_dataset("Salesforce/xlam-function-calling-60k", split="train")
    subset_data = []

   weather_keywords = ["weather", "temperature", "forecast", "climate", "rain", "wind"]
   math_keywords = ["math", "calculator", "calculate", "expression", "add", "multiply", "divide", "subtract"]

    for item in dataset:
        tools_str = str(item['tools']).lower()
        query_str = item['query'].lower()

        is_weather = any(kw in tools_str or kw in query_str for kw in weather_keywords)
        is_math = any(kw in tools_str or kw in query_str for kw in math_keywords)

        if is_weather or is_math:
            cleaned_sample = {
                "tools": item["tools"],
                "user_query": item["query"],
                "expected_action": item["answers"]
            }
            subset_data.append(cleaned_sample)

        if len(subset_data) >= 1000:
            break

    os.makedirs("data", exist_ok=True)
    output_path = "data/demo_dataset.jsonl"

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in subset_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    extract_xlam_subset()