import streamlit as st
from google import genai
from google.genai import types
import time
import os
from PIL import Image

# --- 1. กำหนดลักษณะการตอบ (Prompt Instruction) ---
SYSTEM_PROMPT = """
บทบาท: คุณคือ Digital CMRU AI Service ผู้เชี่ยวชาญด้านข้อมูลอัจฉริยะ
ลักษณะการตอบ:
1. ให้ข้อมูลที่แม่นยำ สุภาพ และมีความเป็นมืออาชีพ
2. ตอบคำถามโดยอ้างอิงข้อมูลจากไฟล์เอกสารที่ระบบ Digital CMRU มอบให้เท่านั้น
3. หากไม่พบคำตอบในเอกสาร ให้ตอบว่า "ขออภัยครับ ไม่พบข้อมูลที่ท่านต้องการในฐานระบบ Digital CMRU ครับ"
4. เน้นการสรุปประเด็นสำคัญให้เข้าใจง่าย
"""

# --- 2. การตั้งค่าหน้าเว็บธีม IT & AI ---
st.set_page_config(
    page_title="Digital CMRU Ai Service",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS สำหรับปรับแต่ง Theme
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        background-color: #1a237e;
        color: white;
        border-radius: 10px;
    }
    .stTextInput>div>div>input {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_stdio=True)

# --- 3. ส่วนหัวของระบบพร้อมโลโก้ ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # ตรวจสอบชื่อไฟล์โลโก้ที่คุณอัปโหลดขึ้น GitHub (สมมติว่าชื่อ logo.png)
    try:
        image = Image.open('795.jpg')
        st.image(image, use_container_width=True)
    except:
        st.header("🌐 DIGITAL CMRU")

st.markdown("<h1 style='text-align: center; color: #1a237e;'>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #5c6bc0;'>ระบบบริการข้อมูลอัจฉริยะ มหาวิทยาลัยราชภัฏเชียงใหม่</p>",
            unsafe_allow_html=True)

# --- 4. การตั้งค่า API ---
# ใช้ Secrets จาก Streamlit Cloud เพื่อความปลอดภัย
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except:
    st.error("กรุณาตั้งค่า GEMINI_API_KEY ใน Streamlit Secrets")
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
    st.image("795.jpg", width=100)
    st.header("⚙️ Admin Control")
    admin_password = st.text_input("รหัสผ่านผู้ดูแลระบบ", type="password")

    if admin_password == "admin123":
        uploaded_file = st.file_uploader("อัปโหลดฐานข้อมูลความรู้ (PDF)", type="pdf")
        if uploaded_file:
            with st.spinner("กำลังอัปเดตระบบ AI..."):
                with open("temp_master.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())

                google_file = client.files.upload(file="temp_master.pdf")
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)

                st.session_state.file_id = google_file.name
                save_file_id(google_file.name)
                st.success("อัปเดตฐานข้อมูล Digital CMRU เรียบร้อย!")

    if st.session_state.file_id:
        st.caption("✅ ระบบ AI พร้อมให้บริการ")

# --- 7. ส่วนหน้าจอแชทสำหรับผู้ใช้งาน ---
st.divider()

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("สอบถามข้อมูลที่ท่านต้องการทราบ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.file_id:
        with st.chat_message("assistant"):
            with st.spinner("AI กำลังค้นหาคำตอบ..."):
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
                    st.error("ขออภัย ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง")
    else:
        st.warning("ขณะนี้ยังไม่มีข้อมูลในระบบ Digital CMRU Ai")