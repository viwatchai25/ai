import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
import time
from PIL import Image

# --- 1. กำหนดลักษณะการตอบ (Prompt Instruction) ---
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

# ส่วนหัวของระบบ
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        st.image(Image.open('795.jpg'), use_container_width=True)
    except:
        st.write("📌 **DIGITAL CMRU**")

st.markdown("<h1 style='text-align: center;'>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>ระบบบริการข้อมูลอัจฉริยะ มหาวิทยาลัยราชภัฏเชียงใหม่</p>",
            unsafe_allow_html=True)

# --- 3. การตั้งค่า API (แก้ไขเพื่อแก้ Error 404) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    # บังคับใช้ API เวอร์ชัน v1 เพื่อความเสถียรและลดปัญหา Model Not Found
    client = genai.Client(
        api_key=API_KEY,
        http_options={'api_version': 'v1'}
    )
except:
    st.error("⚠️ กรุณาตั้งค่า API Key ในระบบ Secrets")
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
                    if content:
                        text += content
        except Exception as e:
            st.error(f"ไม่สามารถอ่านไฟล์ PDF ได้: {e}")
    return text


# --- 5. การจัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 6. ส่วน Admin (Sidebar) สำหรับอัปโหลดไฟล์ถาวร ---
with st.sidebar:
    st.markdown("### ⚙️ ผู้ดูแลระบบ (Admin)")
    admin_password = st.text_input("รหัสผ่าน", type="password")

    if admin_password == "admin123":
        st.success("Admin Mode Active")
        uploaded_file = st.file_uploader("อัปโหลดเอกสารความรู้ (PDF)", type="pdf")
        if uploaded_file:
            with open("data.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("อัปเดตไฟล์ข้อมูล data.pdf สำเร็จ!")

    st.divider()
    if os.path.exists("data.pdf"):
        st.info("✅ ฐานข้อมูลพร้อมใช้งาน (Permanent)")
    else:
        st.warning("⚠️ ระบบยังไม่มีไฟล์ data.pdf")

# --- 7. ส่วนแชทสำหรับผู้ใช้งาน ---
st.divider()

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("สอบถามข้อมูลของท่านได้ที่นี่..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf"):
        with st.chat_message("assistant"):
            with st.spinner("Digital CMRU AI กำลังประมวลผลคำตอบ..."):
                try:
                    # 1. อ่านข้อมูลจาก PDF
                    context_text = get_pdf_text("data.pdf")

                    # 2. ส่งไปยังโมเดลที่รองรับ (ใช้ gemini-2.0-flash หรือรุ่นล่าสุดที่คุณมี)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        ),
                        contents=[f"ข้อมูลจากเอกสาร PDF:\n{context_text}", f"คำถาม: {prompt}"]
                    )

                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
    else:
        st.warning("ขณะนี้ระบบยังไม่มีฐานข้อมูล กรุณาติดต่อ Admin เพื่ออัปโหลดไฟล์ครับ")