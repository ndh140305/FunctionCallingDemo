import os
import pypdf

def read_pdf_file(file_path: str) -> dict:
    """Đọc và trích xuất nội dung văn bản từ một file PDF cục bộ.

    Args:
        file_path: Đường dẫn tới file PDF (ví dụ: 'data/document.pdf').

    Returns:
        dict: Chứa thông tin kết quả trích xuất văn bản hoặc thông tin lỗi.
    """
    # Chuẩn hóa đường dẫn
    normalized_path = os.path.normpath(file_path)
    
    if not os.path.exists(normalized_path):
        return {"error": f"Không tìm thấy file tại đường dẫn: {file_path}"}
    
    try:
        reader = pypdf.PdfReader(normalized_path)
        num_pages = len(reader.pages)
        
        extracted_text = ""
        # Đọc tối đa 5 trang đầu để tránh vượt quá giới hạn token
        max_pages_to_read = min(num_pages, 5)
        
        for i in range(max_pages_to_read):
            page_text = reader.pages[i].extract_text()
            if page_text:
                extracted_text += f"--- TRANG {i+1} ---\n{page_text}\n"
        
        # Giới hạn số ký tự tối đa khoảng 8000 ký tự
        max_chars = 8000
        if len(extracted_text) > max_chars:
            extracted_text = extracted_text[:max_chars] + "\n... [Nội dung bị cắt bớt do quá dài] ..."
            
        if not extracted_text.strip():
            return {
                "file_name": os.path.basename(normalized_path),
                "total_pages": num_pages,
                "error": "Không thể trích xuất văn bản từ file PDF này (có thể là file dạng ảnh quét hoặc file được bảo mật)."
            }
            
        return {
            "file_name": os.path.basename(normalized_path),
            "total_pages": num_pages,
            "read_pages": max_pages_to_read,
            "content": extracted_text.strip()
        }
    except Exception as e:
        return {"error": f"Lỗi khi đọc file PDF: {str(e)}"}

# Khai báo tool schema cho LLM Function Calling
pdf_tool_declaration = {
    "name": "read_pdf_file",
    "description": "Đọc và trích xuất văn bản từ một file PDF cục bộ để phân tích, tóm tắt hoặc trả lời câu hỏi.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Đường dẫn tới file PDF cần đọc, ví dụ: 'data/report.pdf'",
            },
        },
        "required": ["file_path"],
    },
}
