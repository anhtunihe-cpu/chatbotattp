import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import json
import os

# Cấu hình trang giao diện Streamlit
st.set_page_config(page_title="Hệ thống Tiếp nhận Cảnh báo Ngộ độc Thực phẩm", layout="centered")
st.title("🎙️ Chatbot Nghe & Phân Tích Cảnh Báo Ngộ Độc")
st.write("Tải lên file ghi âm cuộc gọi hoặc nhập văn bản phản ánh. Gemini sẽ tự nghe và bóc tách dữ liệu.")

# Lấy API Key an toàn từ Secrets hoặc Sidebar
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Nhập Gemini API Key nếu chạy ở máy local:", type="password")

# Định nghĩa cấu trúc dữ liệu bóc tách bằng Pydantic
class FoodPoisoningReport(BaseModel):
    thoi_gian_nhan_tin: str = Field(description="Thời gian/giờ giấc cụ thể xảy ra vụ việc hoặc cuộc gọi nếu có đề cập (ví dụ: 14h, buổi tối...)")
    ngay_xay_ra: str = Field(description="Ngày, tháng, năm xảy ra vụ ngộ độc thực phẩm (ví dụ: 15/05/2026, hôm qua...)")
    tinh_thanh: str = Field(description="Tên tỉnh hoặc thành phố nơi xảy ra vụ việc")
    xa_phuong_huyen: str = Field(description="Tên xã, phường, thị trấn hoặc quận, huyện")
    so_nguoi_mac: int = Field(description="Số lượng người bị ngộ độc thực phẩm (mắc bệnh). Nếu không nhắc tới ghi -1")
    so_nguoi_chet: int = Field(description="Số lượng người tử vong do ngộ độc thực phẩm. Nếu không nhắc tới ghi 0")
    mon_an_ngo_doc: str = Field(description="Tên các món ăn, thực phẩm nghi ngờ gây ra ngộ độc")

# Khu vực 1: Tải file âm thanh (Tính năng mới)
st.subheader("📁 Cách 1: Tải lên file ghi âm phản ánh")
uploaded_audio = st.file_uploader("Chọn file âm thanh cuộc gọi (Hỗ trợ mp3, wav, m4a, ogg...)", type=["mp3", "wav", "m4a", "ogg"])

# Biến lưu trữ nội dung gửi đi cho Gemini
contents_to_send = None

if uploaded_audio is not None:
    # Hiển thị trình phát nhạc để người dùng nghe lại tại chỗ
    st.audio(uploaded_audio)
    
    # Đọc dữ liệu binary của file âm thanh để gửi trực tiếp qua API
    audio_bytes = uploaded_audio.read()
    
    # Chuẩn bị dữ liệu gửi cho Gemini dạng InlineData
    audio_part = types.Part.from_bytes(
        data=audio_bytes,
        mime_type=uploaded_audio.type,
    )
    
    contents_to_send = [
        audio_part,
        "Hãy lắng nghe kỹ đoạn hội thoại/ghi âm này và trích xuất thông tin vụ ngộ độc thực phẩm theo cấu trúc yêu cầu."
    ]
    
    if st.button("🚀 Bắt đầu nghe và phân tích file âm thanh"):
        if not api_key:
            st.error("⚠️ Vui lòng cấu hình GEMINI_API_KEY!")
        else:
            with st.spinner("🎧 Gemini đang lắng nghe và phân tích âm thanh... Vui lòng đợi trong giây lát..."):
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=contents_to_send,
                        config=types.GenerateContentConfig(
                            system_instruction="Bạn là chuyên viên y tế cấp cao. Nhiệm vụ của bạn là nghe file âm thanh phản ánh sự cố ngộ độc thực phẩm, hiểu tiếng Việt cực tốt (bao gồm cả tiếng địa phương/nói lắp) và bóc tách dữ liệu chính xác.",
                            response_mime_type="application/json",
                            response_schema=FoodPoisoningReport,
                        ),
                    )
                    
                    # Xử lý kết quả trả về
                    extracted_data = json.loads(response.text)
                    st.success("🎉 Đã phân tích âm thanh thành công!")
                    
                    # Hiển thị kết quả ra bảng/giao diện đẹp mắt
                    st.markdown("### 📊 Kết quả trích xuất từ file ghi âm:")
                    st.write(f"- 🕒 **Thời gian:** {extracted_data.get('thoi_gian_nhan_tin')}")
                    st.write(f"- 📅 **Ngày xảy ra:** {extracted_data.get('ngay_xay_ra')}")
                    st.write(f"- 📍 **Địa điểm:** {extracted_data.get('xa_phuong_huyen')}, {extracted_data.get('tinh_thanh')}")
                    st.write(f"- 🤢 **Số người mắc:** {extracted_data.get('so_nguoi_mac') if extracted_data.get('so_nguoi_mac') != -1 else 'Chưa rõ'} người")
                    st.write(f"- 💀 **Số người tử vong:** {extracted_data.get('so_nguoi_chet')} người")
                    st.write(f"- 🍲 **Món ăn nghi ngờ:** {extracted_data.get('mon_an_ngo_doc')}")
                    
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi khi xử lý âm thanh: {e}")

st.write("---")

# Khu vực 2: Khung Chat văn bản truyền thống
st.subheader("💬 Cách 2: Trò chuyện/Nhập văn bản truyền thống")
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Nếu không có file âm thanh, bạn có thể gõ văn bản phản ánh vào đây nhé!"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Nhập nội dung phản ánh văn bản tại đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not api_key:
        st.error("⚠️ Thiếu API Key!")
    else:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔄 Gemini đang phân tích văn bản...")
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Đọc văn bản sau và trích xuất thông tin ngộ độc thực phẩm: {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction="Bạn là trợ lý y tế chuyên bóc tách thông tin chính xác từ văn bản.",
                        response_mime_type="application/json",
                        response_schema=FoodPoisoningReport,
                    ),
                )
                extracted_data = json.loads(response.text)
                response_text = f"**Ghi nhận thông tin văn bản:**\n\n"
                response_text += f"- 🕒 **Thời gian:** {extracted_data.get('thoi_gian_nhan_tin')}\n"
                response_text += f"- 📅 **Ngày xảy ra:** {extracted_data.get('ngay_xay_ra')}\n"
                response_text += f"- 📍 **Địa điểm:** {extracted_data.get('xa_phuong_huyen')}, {extracted_data.get('tinh_thanh')}\n"
                response_text += f"- 🤢 **Số người mắc:** {extracted_data.get('so_nguoi_mac') if extracted_data.get('so_nguoi_mac') != -1 else 'Chưa rõ'} người\n"
                response_text += f"- 💀 **Số người tử vong:** {extracted_data.get('so_nguoi_chet')} người\n"
                response_text += f"- 🍲 **Món ăn nghi ngờ:** {extracted_data.get('mon_an_ngo_doc')}\n"
                
                message_placeholder.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Lỗi: {e}")
