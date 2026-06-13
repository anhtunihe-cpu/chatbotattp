import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from streamlit_mic_recorder import mic_recorder  # Thư viện thu âm trực tiếp
import json

# Cấu hình giao diện tối ưu cho màn hình điện thoại
st.set_page_config(page_title="Tổng đài Cảnh báo Ngộ độc", layout="centered")

st.title("🎙️ Tổng Đài Tiếp Nhận Báo Cáo Ngộ Độc")
st.write("Chạm vào nút ghi âm bên dưới và nói trực tiếp nội dung phản ánh.")

# Lấy API Key an toàn từ Secrets hoặc Sidebar
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("Nhập Gemini API Key nếu chạy ở máy local:", type="password")

# Định nghĩa cấu trúc dữ liệu bóc tách
class FoodPoisoningReport(BaseModel):
    thoi_gian_nhan_tin: str = Field(description="Thời gian/giờ giấc cụ thể xảy ra vụ việc hoặc cuộc gọi (ví dụ: 14h, buổi tối...)")
    ngay_xay_ra: str = Field(description="Ngày, tháng, năm xảy ra vụ ngộ độc thực phẩm (ví dụ: 15/05/2026, hôm qua...)")
    tinh_thanh: str = Field(description="Tên tỉnh hoặc thành phố nơi xảy ra vụ việc")
    xa_phuong_huyen: str = Field(description="Tên xã, phường, thị trấn hoặc quận, huyện")
    so_nguoi_mac: int = Field(description="Số lượng người bị ngộ độc thực phẩm (mắc bệnh). Nếu không nhắc tới ghi -1")
    so_nguoi_chet: int = Field(description="Số lượng người tử vong do ngộ độc thực phẩm. Nếu không nhắc tới ghi 0")
    mon_an_ngo_doc: str = Field(description="Tên các món ăn, thực phẩm nghi ngờ gây ra ngộ độc")

# Thiết kế nút bấm thu âm to rõ cho giao diện điện thoại
st.markdown("### 🔴 Nhấn để ghi âm lời nói:")

# Khởi chạy component ghi âm trực tiếp qua Microphone của thiết bị
audio_record = mic_recorder(
    start_prompt="🎤 Bắt đầu ghi âm cuộc gọi",
    stop_prompt="🛑 Dừng nói & Gửi báo cáo",
    key='recorder',
    format="wav" # Định dạng âm thanh chuẩn dễ xử lý
)

# Nếu người dùng vừa thực hiện ghi âm xong
if audio_record is not None:
    # Lấy dữ liệu bytes âm thanh trực tiếp từ bộ nhớ đệm của thiết bị
    audio_bytes = audio_record['bytes']
    
    # Phát lại đoạn âm thanh vừa nói để người dùng kiểm tra (Tùy chọn)
    st.audio(audio_bytes, format='audio/wav')
    
    if not api_key:
        st.error("⚠️ Hệ thống chưa được cấu hình API Key từ nhà phát triển.")
    else:
        with st.spinner("🎧 Gemini đang lắng nghe giọng nói của bạn và xử lý dữ liệu..."):
            try:
                # Định dạng file để truyền qua API Gemini
                audio_part = types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/wav",
                )
                
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        audio_part,
                        "Hãy nghe đoạn âm thanh tiếng Việt này và trích xuất dữ liệu vụ ngộ độc theo cấu trúc yêu cầu."
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction="Bạn là tổng đài viên y tế thông minh. Nhiệm vụ của bạn là nghe giọng nói của người dân (có thể nói giọng vùng miền Bắc/Trung/Nam, nói nhanh hoặc hoảng loạn), hiểu chính xác ngữ cảnh và bóc tách thông tin vụ việc.",
                        response_mime_type="application/json",
                        response_schema=FoodPoisoningReport,
                    ),
                )
                
                # Phân rã dữ liệu JSON nhận được
                extracted_data = json.loads(response.text)
                
                # Hiển thị kết quả trực quan ngay trên màn hình điện thoại
                st.success("✅ Đã ghi nhận và xử lý xong báo cáo!")
                
                st.markdown("### 📊 Thông tin sự cố bóc tách được:")
                st.info(f"""
                * 🕒 **Thời gian:** {extracted_data.get('thoi_gian_nhan_tin')}
                * 📅 **Ngày xảy ra:** {extracted_data.get('ngay_xay_ra')}
                * 📍 **Địa bàn xảy ra:** {extracted_data.get('xa_phuong_huyen')}, {extracted_data.get('tinh_thanh')}
                * 🤢 **Số ca mắc:** {extracted_data.get('so_nguoi_mac') if extracted_data.get('so_nguoi_mac') != -1 else 'Chưa rõ'} người
                * 💀 **Số ca tử vong:** {extracted_data.get('so_nguoi_chet')} người
                * 🍲 **Thực phẩm nghi ngờ:** {extracted_data.get('mon_an_ngo_doc')}
                """)
                
            except Exception as e:
                st.error(f"Có lỗi xảy ra trong quá trình nhận diện giọng nói: {e}")
