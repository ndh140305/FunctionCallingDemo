import os
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PATH = os.path.join('data', 'token.json')
CREDENTIALS_PATH = 'credentials.json'

def authenticate_gmail_flow():
    """Khởi chạy luồng xác thực Google OAuth2 từ credentials.json và lưu token truy cập."""
    if not os.path.exists(CREDENTIALS_PATH):
        raise FileNotFoundError(
            "Không tìm thấy file 'credentials.json' trong thư mục gốc. "
            "Vui lòng tải xuống từ Google Cloud Console (OAuth Desktop Credentials) và đặt tại đây."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    os.makedirs('data', exist_ok=True)
    with open(TOKEN_PATH, 'w', encoding='utf-8') as token_file:
        token_file.write(creds.to_json())
    
    return creds

def send_gmail(recipient: str, subject: str, body: str) -> dict:
    """Gửi email tới người nhận thông qua Gmail API sử dụng tài khoản đã xác thực.

    Args:
        recipient: Địa chỉ email người nhận.
        subject: Tiêu đề của email.
        body: Nội dung của email (hỗ trợ định dạng HTML hoặc Plaintext).

    Returns:
        dict: Kết quả trạng thái gửi email.
    """
    if not os.path.exists(TOKEN_PATH):
        return {
            "error": "Người dùng chưa cấp quyền truy cập Gmail. "
                     "Hãy nhắc người dùng nhấp vào nút 'Kết nối với Google Gmail' "
                     "ở thanh công cụ bên trái (Sidebar) trước khi bạn có thể thực hiện gửi email."
        }

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w', encoding='utf-8') as token_file:
                token_file.write(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body, 'html', 'utf-8')
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        send_response = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        return {
            "status": "success",
            "message": f"Email đã được gửi thành công tới {recipient}!",
            "message_id": send_response.get('id')
        }

    except Exception as e:
        return {"error": f"Lỗi xảy ra trong quá trình gửi email qua Gmail API: {str(e)}"}

gmail_send_declaration = {
    "name": "send_gmail",
    "description": (
        "Gửi email tới người dùng. BẮT BUỘC phải hỏi ý kiến xác nhận của người dùng "
        "kèm nội dung nháp (tiêu đề, người nhận, nội dung) trước khi thực thi công cụ này. "
        "Nếu tool trả về lỗi chưa cấp quyền, hãy thông báo người dùng cấp quyền ở Sidebar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "Địa chỉ email của người nhận thư.",
            },
            "subject": {
                "type": "string",
                "description": "Tiêu đề của email (được sinh tự động dựa trên prompt của người dùng).",
            },
            "body": {
                "type": "string",
                "description": (
                    "Nội dung email dạng HTML hoặc Plaintext (được tự động sinh chi tiết, "
                    "lịch sự và chuyên nghiệp dựa trên prompt của người dùng)."
                ),
            },
        },
        "required": ["recipient", "subject", "body"],
    },
}
