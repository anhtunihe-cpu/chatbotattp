import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Cấu hình trang giao diện Streamlit
st.set_page_config(page_title="Hệ thống Tiếp nhận Cảnh báo Ngộ độc Thực phẩm", layout="centered")
st.title("🤖 Chatbot Tiếp Nhận Cảnh Báo Ngộ Độc Thực Phẩm")
st.write("Mô hình sử dụng: Google Gemini (Miễn phí)")

# Lấy API Key an toàn từ Secrets của Streamlit Cloud (hoặc điền ở Sidebar khi test dưới máy)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Nhập Gemini API Key nếu chạy ở máy local:", type="password")

# Định nghĩa cấu trúc dữ liệu cần bóc tách
class FoodPoisoningReport(BaseModel):
    thoi_gian_nhan_tin: str = Field(description="Thời gian/giờ giấc cụ thể xảy ra vụ việc nếu có đề cập (ví dụ: 14h, buổi tối...)")
    ngay_xay_ra: str = Field(description="Ngày, tháng, năm xảy ra vụ ngộ độc thực phẩm (ví dụ: 15/05/2026, hôm qua...)")
    tinh_thanh: str = Field(description="Tên tỉnh hoặc thành phố nơi xảy ra vụ việc")
    xa_phuong_huyen: str = Field(description="Tên xã, phường, thị trấn hoặc quận, huyện")
    so_nguoi_mac: int = Field(description="Số lượng người bị ngộ độc thực phẩm (mắc bệnh). Nếu không nhắc tới ghi -1")
    so_nguoi_chet: int = Field(description="Số lượng người tử vong do ngộ độc thực phẩm. Nếu không nhắc tới ghi 0")
    mon_an_ngo_doc: str = Field(description="Tên các món ăn, thực phẩm nghi ngờ gây ra ngộ độc")

# Khởi tạo lịch sử cuộc trò chuyện
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là chatbot y tế. Hãy cung cấp nội dung phản ánh của người dân về vụ ngộ độc thực phẩm."}
    ]

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý khi người dùng nhắn tin
if prompt := st.chat_input("Nhập nội dung phản ánh tại đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("⚠️ Hệ thống thiếu API Key! Vui lòng cấu hình GEMINI_API_KEY trong mục Secrets trên Streamlit Cloud.")
    else:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔄 Gemini đang phân tích dữ liệu...")
            
            try:
                # Khởi tạo client Gemini
                client = genai.Client(api_key=api_key)
                
                # Gọi cấu trúc dữ liệu từ Gemini model gemini-2.5-flash (rất nhanh và miễn phí)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Đọc văn bản sau và trích xuất thông tin ngộ độc thực phẩm: {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction="Bạn là trợ lý y tế chuyên bóc tách thông tin chính xác từ văn bản phản ánh sự cố.",
                        response_mime_type="application/json",
                        response_schema=FoodPoisoningReport,
                    ),
                )
                
                # Chuyển đổi kết quả JSON text trả về thành Object python
                import json
                extracted_data = json.loads(response.text)
                
                # Hiển thị kết quả ra màn hình
                response_text = f"**Hệ thống ghi nhận thông tin phản ánh:**\n\n"
                response_text += f"- 🕒 **Thời gian:** {extracted_data.get('thoi_gian_nhan_tin')}\n"
                response_text += f"- 📅 **Ngày xảy ra:** {extracted_data.get('ngay_xay_ra')}\n"
                response_text += f"- 📍 **Địa điểm:** {extracted_data.get('xa_phuong_huyen')}, {extracted_data.get('tinh_thanh')}\n"
                response_text += f"- 🤢 **Số người mắc:** {extracted_data.get('so_nguoi_mac') if extracted_data.get('so_nguoi_mac') != -1 else 'Chưa rõ'} người\n"
                response_text += f"- 💀 **Số người tử vong:** {extracted_data.get('so_nguoi_chet')} người\n"
                response_text += f"- 🍲 **Món ăn nghi ngờ:** {extracted_data.get('mon_an_ngo_doc')}\n"
                
                message_placeholder.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi kết nối Gemini: {e}")
