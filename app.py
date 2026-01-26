import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
from PIL import Image

# --- 1. System Prompt สำหรับอัตลักษณ์ Digital CMRU ---
SYSTEM_PROMPT = """
บทบาท: คุณคือ Digital CMRU AI Service ผู้เชี่ยวชาญด้านข้อมูลอัจฉริยะของมหาวิทยาลัยราชภัฏเชียงใหม่
ลักษณะการตอบ: สุภาพ มีหางเสียง (ครับ/ค่ะ) ให้ข้อมูลที่แม่นยำและเป็นมืออาชีพ
เงื่อนไข: ตอบคำถามโดยใช้ข้อมูลจาก 'เอกสารอ้างอิง' ที่แนบมาเท่านั้น หากไม่มีในเอกสารให้แจ้งว่าไม่พบข้อมูล
"""

# --- 2. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Digital CMRU Ai Service", page_icon="🤖")

# Custom CSS เพื่อความสวยงามแนว IT/AI
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #003399; color: white; border-radius: 8px; width: 100%; }
    h1 { color: #003399; font-family: 'Sarabun', sans-serif; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ส่วนหัวของระบบ
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        st.image(Image.open('795.jpg'), use_container_width=True)
    except:
        st.markdown("### 🌐 DIGITAL CMRU")

st.markdown("<h1>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align: center; color: #666;'>ระบบบริการข้อมูลอัจฉริยะ (Powered by Google Cloud Credits)</p>",
    unsafe_allow_html=True)

# --- 3. การตั้งค่า API (ใช้ Account ที่มี Credit ฟรี) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(
        api_key=API_KEY,
        http_options={'api_version': 'v1'}  # ใช้เวอร์ชัน Stable สำหรับแผน Pay-as-you-go
    )
except:
    st.error("⚠️ กรุณาตั้งค่า GEMINI_API_KEY ใน Streamlit Secrets")
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
            st.warning(f"ไม่สามารถอ่านไฟล์ได้: {e}")
    return text


# --- 5. จัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 6. ส่วน Admin (Sidebar) ---
with st.sidebar:
    st.header("⚙️ สำหรับผู้ดูแลระบบ")
    admin_pw = st.text_input("รหัสผ่าน Admin", type="password")
    if admin_pw == "admin123":
        up_file = st.file_uploader("อัปโหลดฐานข้อมูลความรู้ (PDF)", type="pdf")
        if up_file:
            with open("data.pdf", "wb") as f:
                f.write(up_file.getbuffer())
            st.success("อัปเดตไฟล์สำเร็จ! ระบบพร้อมให้บริการ")

    st.divider()
    if os.path.exists("data.pdf"):
        st.info("✅ ฐานข้อมูลพร้อมใช้งาน (ถาวร)")
    else:
        st.warning("⚠️ ยังไม่มีไฟล์ data.pdf ในระบบ")

# --- 7. ส่วนหน้าจอแชทสำหรับผู้ใช้งาน ---
st.divider()

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("พิมพ์คำถามของท่านที่นี่..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf"):
        with st.chat_message("assistant"):
            with st.spinner("กำลังประมวลผลคำตอบ..."):
                try:
                    # ดึงข้อมูลจาก PDF มาเป็นบริบท (Context)
                    context_text = get_pdf_text("data.pdf")

                    # เรียกใช้ Gemini 1.5 Flash (ซึ่งโควตาจะปลดล็อคแล้ว)
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=[
                            f"System Instruction: {SYSTEM_PROMPT}",
                            f"เอกสารอ้างอิง: {context_text}",
                            f"คำถามจากผู้ใช้: {prompt}"
                        ]
                    )

                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.warning("ขณะนี้ระบบยังไม่มีฐานข้อมูล กรุณาแจ้ง Admin ให้ทำการอัปโหลดไฟล์ครับ")