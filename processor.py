import os
import sys
import json
import concurrent.futures
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

from groq import Groq

from tools.weather_tool import get_current_weather, weather_tool_declaration
from tools.math_tool import calculate_expression, math_tool_declaration
from tools.pdf_tool import read_pdf_file, pdf_tool_declaration
from tools.coordinates_tool import get_coordinates, coords_tool_declaration
from tools.email_tool import draft_email, email_draft_declaration

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

MODEL_ID = "llama-3.3-70b-versatile"
#MODEL_ID = "llama-3.1-8b-instant"

AVAILABLE_FUNCTIONS = {
    "get_current_weather": get_current_weather,
    "calculate_expression": calculate_expression,
    "read_pdf_file": read_pdf_file,
    "get_coordinates": get_coordinates,
    "draft_email": draft_email
}

tools = [
    {
        "type": "function",
        "function": weather_tool_declaration,
    },
    {
        "type": "function",
        "function": math_tool_declaration,
    },
    {
        "type": "function",
        "function": pdf_tool_declaration,
    },
    {
        "type": "function",
        "function": coords_tool_declaration,
    },
    {
        "type": "function",
        "function": email_draft_declaration,
    }
]

def classify_intent(user_prompt: str) -> str:
    router_prompt = """Bạn là một bộ định tuyến (Router). 
    Nhiệm vụ của bạn là đọc câu hỏi của người dùng và phân loại nó vào các nhóm sau. 
    Nếu câu hỏi có nhiều yêu cầu, hãy trả về TẤT CẢ các từ khóa tương ứng, cách nhau bằng dấu phẩy. 
    Tuyệt đối CHỈ TRẢ VỀ CÁC TỪ KHÓA, không giải thích gì thêm:

- THOI_TIET: Nếu câu hỏi hỏi về thời tiết, nhiệt độ.
- TOAN_HOC: Nếu câu hỏi chứa phép tính toán học.
- DOC_PDF: Nếu người dùng yêu cầu đọc tài liệu, tóm tắt file PDF.
- EMAIL: Nếu người dùng yêu cầu soạn hoặc gửi email.
- KIEN_THUC_CHUNG: Các câu hỏi giao tiếp bình thường, hỏi kiến thức chung (VD: xin chào, quả chuối màu gì, ai là tổng thống...)"""

    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()

def execute_tool_parallel(tool_call):
    function_name = tool_call.function.name
    try:
        function_args = json.loads(tool_call.function.arguments)
    except Exception as e:
        return tool_call.id, function_name, {}, {"error": f"Lỗi định dạng tham số từ model: {str(e)}"}

    if function_name in AVAILABLE_FUNCTIONS:
        func = AVAILABLE_FUNCTIONS[function_name]
        try:
            tool_output = func(**function_args)
        except Exception as e:
            tool_output = {"error": f"Lỗi khi thực thi tool: {str(e)}"}
    else:
        tool_output = {"error": f"Tool '{function_name}' không được hỗ trợ."}

    return tool_call.id, function_name, function_args, tool_output
        
def process_user_prompt(user_prompt: str) -> dict:
    """Xử lý prompt của user qua Groq Function Calling.

    Nhận đầu vào là user prompt, phân loại ý định, định tuyến tool, rồi thực thi tool nếu cần.
    """
    intent = classify_intent(user_prompt).upper()
    print(f"Router phân loại: {intent}")

    tools_to_use = []
    system_prompts = []

    if "THOI_TIET" in intent:
        tools_to_use.extend([
            {"type": "function", "function": coords_tool_declaration},
            {"type": "function", "function": weather_tool_declaration},
        ])
        system_prompts.append(
            "Bạn là chuyên gia thời tiết. Hãy gọi tool để lấy tọa độ, sau đó xem thời tiết."
        )

    if "TOAN_HOC" in intent:
        tools_to_use.append({"type": "function", "function": math_tool_declaration})
        system_prompts.append("Hãy dùng tool calculate_expression để tính toán chính xác.")

    if "DOC_PDF" in intent:
        tools_to_use.append({"type": "function", "function": pdf_tool_declaration})
        system_prompts.append(
            "Bạn là chuyên gia đọc PDF. Hãy dùng tool phù hợp để đọc và tóm tắt nội dung file PDF."
        )

    if "EMAIL" in intent:
        tools_to_use.append({"type": "function", "function": email_draft_declaration})
        system_prompts.append(
            "Bạn là trợ lý email. Hãy gọi tool draft_email để soạn email lịch sự, đầy đủ và chuyên nghiệp."
        )

    if not tools_to_use:
        tools_to_use = None
        system_prompt = "Bạn là trợ lý AI thân thiện. Hãy trả lời câu hỏi của người dùng một cách tự nhiên."
    else:
        system_prompt = (
            " ".join(system_prompts)
            + " Hãy thực hiện các bước tuần tự theo yêu cầu."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    max_iterations = 5
    iteration = 0

    result = {
        "user_prompt": user_prompt,
        "tool_calls": [],
        "tool_results": [],
        "steps": [],
        "final_answer": None,
    }

    while iteration < max_iterations:
        try:
            kwargs = {
                "model": MODEL_ID,
                "messages": messages,
                "temperature": 0,
            }
            if tools_to_use:
                kwargs["tools"] = tools_to_use
                kwargs["tool_choice"] = "auto"

            response = client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e)
            if "400" in error_str and "tool" in error_str.lower():
                try:
                    response_fallback = client.chat.completions.create(
                        model=MODEL_ID,
                        messages=messages,
                        temperature=0,
                    )
                    result["final_answer"] = (
                        response_fallback.choices[0].message.content
                        + "\n\n(Lưu ý: Hệ thống gặp khó khăn khi gọi công cụ, câu trả lời dựa trên kiến thức gốc của AI.)"
                    )
                    return result
                except Exception as fallback_error:
                    result["final_answer"] = (
                        f"Lỗi hệ thống khi gọi AI (Fallback failed): {str(fallback_error)}"
                    )
                    return result
            result["final_answer"] = f"Hệ thống gặp lỗi API: {error_str}"
            return result

        response_message = response.choices[0].message

        if not getattr(response_message, "tool_calls", None):
            result["final_answer"] = response_message.content
            return result

        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response_message.tool_calls
            ],
        })

        has_tool_error = False
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(execute_tool_parallel, tc) for tc in response_message.tool_calls]
            for future in concurrent.futures.as_completed(futures):
                t_id, function_name, function_args, tool_output = future.result()

                result["tool_calls"].append({"name": function_name, "arguments": function_args})
                result["tool_results"].append({"name": function_name, "output": tool_output})
                result["steps"].append({"tool": function_name, "output": tool_output})

                if isinstance(tool_output, dict) and "error" in tool_output:
                    has_tool_error = True

                messages.append({
                    "role": "tool",
                    "tool_call_id": t_id,
                    "name": function_name,
                    "content": json.dumps(tool_output, ensure_ascii=False),
                })

        if has_tool_error:
            messages.append({
                "role": "system",
                "content": (
                    "Công cụ vừa gọi trả về lỗi. DỪNG gọi thêm công cụ. "
                    "Hãy thông báo lỗi này cho người dùng ngay lập tức."
                ),
            })

        iteration += 1

    result["final_answer"] = "Hệ thống đã đạt giới hạn vòng lặp suy luận nhưng chưa tìm ra câu trả lời."
    return result
