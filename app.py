import streamlit as st
from google import genai
from google.genai import types
import time
import os
from PIL import Image

# --- 1. กำหนดลักษณะการตอบ (Prompt Instruction) ---
SYSTEM_PROMPT = """
บทบาท: คุณคือ Digital CMRU AI Service ผู้เชี่ยวชาญด้านข้อมูลอัจฉริยะของมหาวิทยาลัยราชภัฏเชียงใหม่
ลักษณะการตอบ:
1. ให้ข้อมูลที่แม่นยำ สุภาพ และมีความเป็นมืออาชีพ มีหางเสียง (ครับ/ค่ะ)
2. ตอบคำถามโดยอ้างอิงข้อมูลจากไฟล์เอกสารที่ระบบ Digital CMRU มอบให้เท่านั้น
3. หากไม่พบคำตอบในเอกสาร ให้ตอบว่า "ขออภัยครับ ไม่พบข้อมูลที่ท่านต้องการในฐานระบบ Digital CMRU ครับ"
4. เน้นการสรุปประเด็นสำคัญให้เข้าใจง่ายและชัดเจน
"""

# --- 2. การตั้งค่าหน้าเว็บและ Theme ---
st.set_page_config(
    page_title="Digital CMRU Ai Service",
    page_icon="🤖",
    layout="centered"
)

# แก้ไข CSS และ Parameter unsafe_allow_html ให้ถูกต้อง
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #003399;
        color: white;
        border-radius: 8px;
        width: 100%;
    }
    .stChatInputContainer {
        padding-bottom: 20px;
    }
    h1 {
        color: #003399;
        font-family: 'Sarabun', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวของระบบพร้อมโลโก้ ---
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        # ดึงรูปจากไฟล์ 795.jpg ที่คุณอัปโหลด
        image = Image.open('795.jpg')
        st.image(image, use_container_width=True)
    except Exception:
        st.write("📌 **DIGITAL CMRU**")

st.markdown("<h1 style='text-align: center;'>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>ระบบบริการข้อมูลอัจฉริยะ มหาวิทยาลัยราชภัฏเชียงใหม่</p>",
            unsafe_allow_html=True)

# --- 4. การตั้งค่า API ---
try:
    # ดึงค่าจาก Streamlit Secrets (ต้องตั้งค่าในหน้าเว็บ Streamlit Cloud)
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    st.error("⚠️ ไม่พบ API Key กรุณาตั้งค่า GEMINI_API_KEY ใน Settings > Secrets")
    st.stop()

DB_FILE = "file_id.txt"


def save_file_id(fid):
    with open(DB_FILE, "w") as f:
        f.write(fid)


def load_file_id():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return f.read().strip()
    return None


# --- 5. การจัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_id" not in st.session_state:
    st.session_state.file_id = load_file_id()

# --- 6. ส่วน Admin (Sidebar) ---
with st.sidebar:
    st.markdown("### ⚙️ ผู้ดูแลระบบ")
    admin_password = st.text_input("กรอกรหัสผ่าน", type="password")

    if admin_password == "admin123":
        st.success("เข้าสู่ระบบสำเร็จ")
        uploaded_file = st.file_uploader("อัปโหลดเอกสารความรู้ (PDF)", type="pdf")
        if uploaded_file:
            with st.spinner("กำลังประมวลผลไฟล์..."):
                with open("temp_master.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # ใช้ parameter 'file' ตาม SDK ล่าสุด
                google_file = client.files.upload(file="temp_master.pdf")
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)

                st.session_state.file_id = google_file.name
                save_file_id(google_file.name)
                st.success("อัปเดตข้อมูลสำเร็จ!")
                # ลบไฟล์ชั่วคราว
                if os.path.exists("temp_master.pdf"):
                    os.remove("temp_master.pdf")

    st.divider()
    if st.session_state.file_id:
        st.info("✅ ฐานข้อมูลพร้อมใช้งาน")
    else:
        st.warning("❌ ยังไม่มีข้อมูลในระบบ")

# --- 7. ส่วนแชทสำหรับผู้ใช้งาน ---
st.divider()

# แสดงประวัติการสนทนา
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# รับคำถามจาก User
if prompt := st.chat_input("พิมพ์คำถามของท่านที่นี่..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.file_id:
        with st.chat_message("assistant"):
            with st.spinner("Digital CMRU AI กำลังหาคำตอบ..."):
                try:
                    target_file = client.files.get(name=st.session_state.file_id)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT
                        ),
                        contents=[target_file, prompt]
                    )
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("ขออภัย ระบบขัดข้องชั่วคราว (ไฟล์อาจหมดอายุ 48 ชม.) กรุณาให้ Admin อัปโหลดใหม่")
    else:
        st.warning("ขณะนี้ยังไม่มีข้อมูลในระบบ กรุณารอ Admin อัปโหลดฐานข้อมูลครับ")