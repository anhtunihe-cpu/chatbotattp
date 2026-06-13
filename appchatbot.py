import streamlit as st
from openai import OpenAI
from pydantic import BaseModel, Field
import json

# Cấu hình trang giao diện Streamlit
st.set_page_config(page_title="Hệ thống Tiếp nhận Cảnh báo Ngộ độc Thực phẩm", layout="centered")
st.title("🤖 Chatbot Tiếp Nhận Cảnh Báo Ngộ Độc Thực Phẩm")
st.write("Nhập thông tin phản ánh của người dân vào ô chat bên dưới. Hệ thống sẽ tự động nhận diện và trích xuất các thông tin cần thiết.")

# Khởi tạo OpenAI Client (Nhập API key của bạn hoặc lấy từ Streamlit secrets)
# Bạn có thể thay đổi base_url nếu dùng các dịch vụ LLM khác
api_key = st.sidebar.text_input("Nhập OpenAI API Key:", type="password")

# Định nghĩa cấu trúc dữ liệu cần trích xuất bằng Pydantic
class FoodPoisoningReport(BaseModel):
    thoi_gian_nhan_tin: str = Field(description="Thời gian/giờ giấc người dân báo tin hoặc xảy ra vụ việc nếu có đề cập cụ thể (ví dụ: 14h, buổi tối...)")
    ngay_xay_ra: str = Field(description="Ngày, tháng, năm xảy ra vụ ngộ độc thực phẩm (ví dụ: 15/05/2026, hôm qua...)")
    tinh_thanh: str = Field(description="Tên tỉnh hoặc thành phố nơi xảy ra vụ việc")
    xa_phuong_huyen: str = Field(description="Tên xã, phường, thị trấn hoặc quận, huyện xảy ra vụ việc")
    so_nguoi_mac: int = Field(description="Số lượng người bị ngộ độc thực phẩm (mắc bệnh). Nếu không có ghi -1")
    so_nguoi_chet: int = Field(description="Số lượng người tử vong do ngộ độc thực phẩm. Nếu không có hoặc không nhắc tới ghi 0")
    mon_an_ngo_doc: str = Field(description="Tên các món ăn, thực phẩm nghi ngờ gây ra ngộ độc (ví dụ: bánh mì, trà sữa, nấm độc...)")

# Khởi tạo lịch sử cuộc trò chuyện trong Session State của Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là chatbot tiếp nhận thông tin sự cố y tế. Hãy cung cấp thông tin hoặc đoạn văn bản phản ánh của người dân về vụ ngộ độc thực phẩm."}
    ]

# Hiển thị lịch sử chat ra màn hình
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý khi người dùng gửi tin nhắn (Prompt)
if prompt := st.chat_input("Nhập nội dung phản ánh tại đây..."):
    # Hiển thị tin nhắn người dùng
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kiểm tra xem đã điền API Key chưa
    if not api_key:
        st.error("⚠️ Vui lòng nhập OpenAI API Key ở thanh bên (Sidebar) để tiếp tục!")
    else:
        client = OpenAI(api_key=api_key)
        
        # Tạo hiệu ứng chờ phản hồi từ Assistant
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🔄 Đang phân tích dữ liệu và trích xuất thông tin...")
            
            try:
                # Gọi API OpenAI sử dụng tính năng Structured Outputs (beta/parsed)
                completion = client.beta.chat.completions.parse(
                    model="gpt-4o-mini", # Model rẻ và xử lý trích xuất cấu trúc cực tốt
                    messages=[
                        {"role": "system", "content": "Bạn là trợ lý y tế chuyên trách tiếp nhận báo cáo ngộ độc thực phẩm. Nhiệm vụ của bạn là đọc phản ánh của người dân và trích xuất chính xác các trường thông tin được yêu cầu."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format=FoodPoisoningReport,
                )
                
                # Lấy kết quả đã được parse theo định dạng Pydantic
                extracted_data = completion.choices[0].message.parsed
                
                # Tạo nội dung phản hồi thân thiện cho người dùng
                response_text = f"**Cám ơn bạn đã cung cấp thông tin. Hệ thống đã ghi nhận và tự động phân tích cuộc gọi/phản ánh này như sau:**\n\n"
                response_text += f"- 🕒 **Thời gian:** {extracted_data.thoi_gian_nhan_tin}\n"
                response_text += f"- 📅 **Ngày xảy ra:** {extracted_data.ngay_xay_ra}\n"
                response_text += f"- 📍 **Địa điểm:** {extracted_data.xa_phuong_huyen}, {extracted_data.tinh_thanh}\n"
                response_text += f"- 🤢 **Số người mắc:** {extracted_data.so_nguoi_mac if extracted_data.so_nguoi_mac != -1 else 'Chưa rõ'} người\n"
                response_text += f"- 💀 **Số người tử vong:** {extracted_data.so_nguoi_chet} người\n"
                response_text += f"- 🍲 **Món ăn nghi ngờ ngộ độc:** {extracted_data.mon_an_ngo_doc}\n"
                
                # Cập nhật kết quả lên màn hình chat
                message_placeholder.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # Hiển thị thêm hộp JSON thô ở dưới để kiểm tra nếu muốn lưu vào Database
                with st.expander("📊 Xem dữ liệu cấu trúc JSON hệ thống nhận được"):
                    st.json(extracted_data.model_dump())
                    
            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi kết nối hoặc xử lý dữ liệu: {e}")