# Tổng quan

Đây là dự án demo nghiên cứu cách LLM sử dụng tools/ api
Model được sử dụng là Groq (llama-3.3-70b-versatile/ llama-3.1-8b-instant)

## Các công cụ được sử dụng

AI Agent được trang bị các công cụ sau để xử lý yêu cầu của người dùng:

1. **Gửi Email**: 
   - Tích hợp xác thực Google OAuth2 để kết nối an toàn với tài khoản Gmail của người dùng.
   - Khi người dùng yêu cầu gửi email, AI sẽ tự động tạo bản nháp. Hệ thống sẽ tạm dừng luồng thực thi và hiển thị một biểu mẫu trên giao diện người dùng để xem xét, chỉnh sửa và xác nhận trước khi email được gửi đi thực sự. Cách làm này để tạm thời khắc phục vấn đề chat history chưa được lưu lại, khiến AI không thể nhớ thông tin người dùng đã cung cấp ở các câu trước.
   - Cụ thể quy trình: người dùng nhập prompt -> Groq phân tích và trả về file json nội dung mail-> tool gọi draft_email -> hiển thị kết quả cho người dùng xem xét và chỉnh sửa -> người dùng xác nhận -> gửi email thật. Tất cả đều diễn ra trong 1 session
2. **Tra cứu Thời tiết**: Tự động lấy thông tin thời tiết thời gian thực tại bất kỳ địa điểm nào dựa trên api của Openweather
3. **Lấy Tọa độ (Geocoding)**: Chuyển đổi tên thành phố, quốc gia thành tọa độ địa lý (Vĩ độ/Kinh độ) phục vụ cho API thời tiết.
4. **Máy tính Toán học**: Tính toán chính xác các biểu thức toán học phức tạp để khắc phục nhược điểm tính toán của các mô hình ngôn ngữ lớn. Sử dụng chính thư viện toán học của Python
5. **Đọc file PDF**: Trích xuất nội dung văn bản từ các tệp PDF được tải lên để AI xử lý và tóm tắt. Giới hạn 5 trang / 8000 ký tự

## Yêu cầu hệ thống và Cài đặt

1. **Cài đặt thư viện**:
   Sử dụng lệnh sau để cài đặt các gói phụ thuộc cần thiết:
   ```bash
   pip install -r requirements.txt
   ```

2. **Cấu hình biến môi trường (Groq API)**:
   - Tạo một tệp có tên `.env` tại thư mục gốc của dự án.
   - Bổ sung Groq API Key vào tệp `.env`:
     ```env
     GROQ_API_KEY=your_groq_api_key_here
     ```

3. **Cấu hình xác thực Gmail OAuth2**:
   - Truy cập Google Cloud Console, tạo một Project và kích hoạt Gmail API.
   - Tạo OAuth 2.0 Client IDs (chọn loại ứng dụng Desktop).
   - Tải tệp JSON chứa thông tin xác thực, đổi tên thành `credentials.json` và lưu vào thư mục gốc của dự án.

## Hướng dẫn sử dụng

Khởi chạy ứng dụng web Streamlit bằng lệnh:
```bash
streamlit run app.py
```

- **Giao diện Trò chuyện**: Tương tác với Agent thông qua giao diện chính ở phần màn hình bên trái.
- **Lịch sử Gọi hàm**: Phần màn hình bên phải sẽ hiển thị chi tiết các quyết định gọi hàm của AI theo thời gian thực, bao gồm tham số truyền vào và kết quả trả về từ mỗi hàm.
- **Bảng Điều khiển**: Quản lý trạng thái kết nối tài khoản Gmail (Cho phép truy cập / Ngắt kết nối).

## Cấu trúc Mã nguồn

- `app.py`: Tệp giao diện chính của ứng dụng viết bằng Streamlit. Quản lý trạng thái người dùng và biểu mẫu xác nhận bản nháp email.
- `processor.py`: Lõi xử lý luồng AI. Quản lý việc kết nối với Groq API, thiết lập System Prompt và điều phối luồng Function Calling.
- `tools/`: Thư mục chứa mã nguồn của từng công cụ riêng biệt (`email_tool.py`, `weather_tool.py`, `pdf_tool.py`, ...).

