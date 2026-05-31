import os
import json
import streamlit as st
from dotenv import load_dotenv

from processor import process_user_prompt
from tools.email_tool import authenticate_gmail_flow, TOKEN_PATH

load_dotenv()

st.set_page_config(
    page_title="Tool-Augmented AI Agent",
    layout="wide"
)

with st.sidebar:
    st.markdown("""
        <style>
        .gmail-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        }
        .status-connected {
            color: #4CAF50;
            font-weight: bold;
        }
        .status-disconnected {
            color: #FF5722;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("#### Kết nối Gmail")
    
    is_connected = os.path.exists(TOKEN_PATH)
    
    if is_connected:
        st.markdown('Trạng thái: <span class="status-connected">● Đã liên kết thành công</span>', unsafe_allow_html=True)
        if st.button("Ngắt kết nối Gmail", use_container_width=True):
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH)
            st.toast("Đã hủy quyền truy cập Gmail!")
            st.rerun()
    else:
        st.markdown('Trạng thái: <span class="status-disconnected">● Chưa được cấp quyền</span>', unsafe_allow_html=True)        
        if st.button("Kết nối với Google Gmail", type="primary", use_container_width=True):
            with st.spinner("Đang mở trình duyệt để xác thực OAuth2..."):
                try:
                    authenticate_gmail_flow()
                    st.toast("Kết nối Gmail thành công!")
                    st.rerun()
                except FileNotFoundError as fnf:
                    st.error(str(fnf))
                except Exception as e:
                    st.error(f"Lỗi kết nối: {str(e)}")
                    
    st.markdown('</div>', unsafe_allow_html=True)

st.title("Demo kỹ thuật Function Calling của chatbot")
st.caption("Demo các vấn đề hiện đại về KHMT")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "logs" not in st.session_state:
    st.session_state.logs = []

col_chat, col_log = st.columns([3, 2])

st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > div:has(div.stButton) {
        border-radius: 25px;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

with col_chat:
    st.subheader("Chatbot")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Tạo thư mục data nếu chưa có
    os.makedirs("data", exist_ok=True)

    # col_upload, col_input = st.columns([1, 12])

    # with col_upload:
    #     with st.popover("➕", help="Tải lên tài liệu PDF"):
    #         st.markdown("### Tải lên tài liệu PDF")
    #         uploaded_file = st.file_uploader("Chọn file PDF", type=["pdf"], label_visibility="collapsed")
    #         if uploaded_file is not None:
    #             file_path = os.path.join("data", uploaded_file.name)
    #             with open(file_path, "wb") as f:
    #                 f.write(uploaded_file.getbuffer())
    #             st.success("Đã tải lên thành công!")
    #             st.info(f"Đường dẫn file: `{file_path}`")
            
    #         st.markdown("---")
    #         st.markdown("### Các file PDF sẵn có:")
    #         pdf_files = [f for f in os.listdir("data") if f.endswith(".pdf")]
    #         if pdf_files:
    #             for file in pdf_files:
    #                 st.code(f"data/{file}", language="text")
    #         else:
    #             st.info("Thư mục `data/` chưa có file PDF nào.")

    # with col_input:
    #     user_query = st.chat_input("Ask Grok")

    input_container = st.container()
    
    with input_container:
        c1, c2 = st.columns([1, 10], gap="small")

        with c1:
            with st.popover("+", help="Tải lên tài liệu PDF"):
                st.markdown("### 📄 Quản lý tài liệu")
                uploaded_file = st.file_uploader("Chọn file PDF", type=["pdf"])
                if uploaded_file is not None:
                    file_path = os.path.join("data", uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success("Tải lên thành success!")
                
                st.markdown("---")
                pdf_files = [f for f in os.listdir("data") if f.endswith(".pdf")]
                if pdf_files:
                    for file in pdf_files:
                        st.caption(f"📁 {file}")

        with c2:
            user_query = st.chat_input("Ask Grok...")

    if user_query:
        with st.chat_message("user"):
            st.markdown(user_query)
        st.session_state.messages.append({"role": "user", "content": user_query})

        with st.spinner("Agent đang suy nghĩ và điều phối công cụ..."):
            try:
                output = process_user_prompt(user_query)
                final_answer = output["final_answer"]
                tool_calls = output["tool_calls"]
                tool_results = output["tool_results"]
            except Exception as e:
                final_answer = f"Hệ thống gặp lỗi: {str(e)}"
                tool_calls, tool_results = [], []

        with st.chat_message("assistant"):
            st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})

        # Lưu log để hiển thị ở cột bên phải
        st.session_state.logs.append({
            "query": user_query,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
        })
        st.rerun()  # Rerun để hiển thị log mới nhất ở cột bên phải

with col_log:
    st.subheader("Tool call logs")

    if st.session_state.logs:
        latest_log = st.session_state.logs[-1]
        tool_calls = latest_log["tool_calls"]
        tool_results = latest_log["tool_results"]

        if tool_calls:
            st.success("Phát hiện LLM gọi Tool thành công!")
            
            for i, (tc, tr) in enumerate(zip(tool_calls, tool_results)):
                st.markdown(f"**[Tool Call {i+1}] Tên Tool:** `{tc['name']}`")
                
                st.json(tc['arguments'])
                
                st.markdown("Tool được thực thi và trả về kết quả:")
                
                st.info(f"Dữ liệu Tool: {tr['output']}")
        else:
            st.warning("Câu hỏi này LLM tự suy luận trực tiếp, không cần kích hoạt Tool.")
    else:
        st.info("Chưa có log nào. Hãy gửi câu hỏi để bắt đầu!")