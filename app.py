import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
import time
from PIL import Image

# --- 1. กำหนดลักษณะการตอบ (System Prompt) ---
SYSTEM_PROMPT = """
บทบาท: คุณคือ Digital CMRU AI Service ผู้เชี่ยวชาญด้านข้อมูลอัจฉริยะของมหาวิทยาลัยราชภัฏเชียงใหม่
ลักษณะการตอบ:
1. ให้ข้อมูลที่แม่นยำ สุภาพ และมีความเป็นมืออาชีพ มีหางเสียง (ครับ/ค่ะ)
2. ตอบคำถามโดยใช้ "ข้อมูลอ้างอิงจากเอกสาร" ที่ส่งไปให้เท่านั้น
3. หากไม่พบคำตอบในเอกสาร ให้ตอบว่า "ขออภัยครับ ไม่พบข้อมูลที่ท่านต้องการในฐานระบบ Digital CMRU ครับ"
4. เน้นการสรุปประเด็นสำคัญให้เข้าใจง่าย
"""

# --- 2. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Digital CMRU Ai Service", page_icon="🤖")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #003399; color: white; border-radius: 8px; width: 100%; }
    h1 { color: #003399; font-family: 'Sarabun', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# ส่วนหัวระบบ
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        st.image(Image.open('795.jpg'), use_container_width=True)
    except:
        st.write("📌 **DIGITAL CMRU**")

st.markdown("<h1 style='text-align: center;'>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>ระบบบริการข้อมูลอัจฉริยะ มหาวิทยาลัยราชภัฏเชียงใหม่</p>",
            unsafe_allow_html=True)

# --- 3. การตั้งค่า API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(
        api_key=API_KEY,
        http_options={'api_version': 'v1beta'}  # เปลี่ยนเป็น v1beta เพื่อให้รองรับโมเดลใหม่ๆ ได้ดีขึ้น
    )
except:
    st.error("⚠️ ไม่พบ API Key ในระบบ Secrets")
    st.stop()


# --- 4. ฟังก์ชันดึงข้อความจาก PDF ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content = page.extract_text()
                    if content: text += content
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ PDF ได้: {e}")
    return text


# --- 5. การจัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 6. ส่วน Admin (Sidebar) ---
with st.sidebar:
    st.markdown("### ⚙️ ผู้ดูแลระบบ (Admin)")
    admin_password = st.text_input("รหัสผ่าน", type="password")

    if admin_password == "admin123":
        uploaded_file = st.file_uploader("อัปโหลดเอกสารความรู้ (PDF)", type="pdf")
        if uploaded_file:
            with open("data.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("อัปเดตไฟล์ data.pdf สำเร็จ!")

    st.divider()
    if os.path.exists("data.pdf"):
        st.info("✅ ฐานข้อมูลพร้อมใช้งาน (Permanent)")

# --- 7. ส่วนแชทสำหรับผู้ใช้งาน ---
st.divider()

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("พิมพ์คำถามของท่านที่นี่..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf"):
        with st.chat_message("assistant"):
            with st.spinner("Digital CMRU AI กำลังประมวลผล..."):
                try:
                    context_text = get_pdf_text("data.pdf")

                    # เปลี่ยนชื่อโมเดลเป็น gemini-1.5-flash-latest เพื่อแก้ปัญหา 404
                    response = client.models.generate_content(
                        model="gemini-1.5-flash-latest",
                        contents=[
                            f"คำสั่งระบบ: {SYSTEM_PROMPT}",
                            f"ข้อมูลอ้างอิง: {context_text}",
                            f"คำถาม: {prompt}"
                        ]
                    )

                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    if "429" in str(e):
                        st.error("⚠️ โควตาการใช้งานเต็มชั่วคราว กรุณารอ 1-2 นาทีครับ")
                    elif "404" in str(e):
                        st.error("⚠️ ไม่พบโมเดลในระบบ (404) กรุณาแจ้งผู้พัฒนาเพื่อตรวจสอบชื่อโมเดลครับ")
                    else:
                        st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.warning("กรุณาอัปโหลดไฟล์ data.pdf ก่อนใช้งานครับ")