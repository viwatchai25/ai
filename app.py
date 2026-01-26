import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
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
    .stButton>button { background-color: #003399; color: white; border-radius: 8px; }
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
st.markdown("<p style='text-align: center; color: #666;'>ระบบบริการข้อมูลถาวร มหาวิทยาลัยราชภัฏเชียงใหม่</p>",
            unsafe_allow_html=True)

# --- 3. การตั้งค่า API ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except:
    st.error("⚠️ กรุณาตั้งค่า API Key ในระบบ Secrets")
    st.stop()


# --- 4. ฟังก์ชันดึงข้อความจาก PDF ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    text += content
    return text


# --- 5. การจัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 6. ส่วน Admin (Sidebar) สำหรับอัปโหลดไฟล์ถาวร ---
with st.sidebar:
    st.markdown("### ⚙️ ผู้ดูแลระบบ (Admin)")
    admin_password = st.text_input("รหัสผ่าน", type="password")

    if admin_password == "admin123":
        uploaded_file = st.file_uploader("อัปโหลดไฟล์ฐานข้อมูล (จะถูกตั้งชื่อเป็น data.pdf)", type="pdf")
        if uploaded_file:
            with open("data.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("อัปเดตไฟล์ข้อมูลถาวรสำเร็จ!")

    st.divider()
    if os.path.exists("data.pdf"):
        st.info("✅ ฐานข้อมูล PDF พร้อมใช้งาน (ถาวร)")
    else:
        st.warning("⚠️ ยังไม่มีไฟล์ data.pdf ในระบบ")

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
                    # 1. อ่าน Text จาก PDF
                    context_text = get_pdf_text("data.pdf")

                    # 2. ส่งคำถามไปที่ Gemini โดยแนบ Context ไปใน Prompt เลย
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",  # ใช้ Flash เพื่อความเร็ว
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        ),
                        contents=[f"ข้อมูลอ้างอิงจากเอกสาร:\n{context_text}", f"คำถามจากผู้ใช้: {prompt}"]
                    )

                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
    else:
        st.warning("ขออภัย ระบบยังไม่มีฐานข้อมูลสำหรับตอบคำถาม")