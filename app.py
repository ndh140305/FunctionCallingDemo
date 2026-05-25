import os
import json
import streamlit as st
from dotenv import load_dotenv

from evaluate import process_user_prompt

load_dotenv()

st.set_page_config(
    page_title="Tool-Augmented AI Agent",
    layout="wide"
)

st.title("Demo kỹ thuật Function Calling của chatbot")
st.caption("Demo các vấn đề hiện đại về KHMT")
st.markdown("---")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "logs" not in st.session_state:
    st.session_state.logs = []

col_chat, col_log = st.columns([3, 2])

with col_chat:
    st.subheader("Chatbot")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Tạo thư mục data nếu chưa có
    os.makedirs("data", exist_ok=True)

    col_upload, col_input = st.columns([1, 12])

    with col_upload:
        with st.popover("➕", help="Tải lên tài liệu PDF"):
            st.markdown("### Tải lên tài liệu PDF")
            uploaded_file = st.file_uploader("Chọn file PDF", type=["pdf"], label_visibility="collapsed")
            if uploaded_file is not None:
                file_path = os.path.join("data", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Đã tải lên thành công!")
                st.info(f"Đường dẫn file: `{file_path}`")
            
            st.markdown("---")
            st.markdown("### Các file PDF sẵn có:")
            pdf_files = [f for f in os.listdir("data") if f.endswith(".pdf")]
            if pdf_files:
                for file in pdf_files:
                    st.code(f"data/{file}", language="text")
            else:
                st.info("Thư mục `data/` chưa có file PDF nào.")

    with col_input:
        user_query = st.chat_input("Ask Grok")

    # Xử lý khi người dùng gửi câu hỏi
    if user_query:
        # Hiển thị câu hỏi của user lập tức
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