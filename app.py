import streamlit as st
from google import genai
from google.genai import types
import time
import os

# --- 1. กำหนดลักษณะการตอบ (Prompt Instruction) ---
# คุณสามารถแก้ข้อความในนี้เพื่อให้ AI มีบุคลิกตามที่คุณต้องการได้เลย
SYSTEM_PROMPT = """
บทบาท: คุณคือผู้ช่วยอัจฉริยะที่เชี่ยวชาญด้านสมุนไพรที่เก่งมากคนหนึ่ง
ลักษณะการตอบ:
1. สุภาพ มีหางเสียง (ครับ/ค่ะ) และเป็นกันเองเหมือนพี่สอนน้อง
2. ตอบคำถามโดยอ้างอิงข้อมูลจากไฟล์ PDF ที่แนบมาเท่านั้น
3. หากข้อมูลในไฟล์ไม่มี ให้ตอบว่า "ขออภัยครับ ข้อมูลส่วนนี้ไม่มีในเอกสารที่ผมได้รับมาครับ" 
4. ห้ามเดาหรือใช้ความรู้ภายนอกมาตอบเด็ดขาด
5. หากคำตอบมีเนื้อหาเยอะ ให้สรุปเป็นข้อๆ (Bullet points) เพื่อให้ดาวน์โหลดข้อมูลได้ง่าย
"""

# --- การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Knowledge Bot", layout="centered")
st.title("📚 ระบบสืบค้นข้อมูลอัจฉริยะ")

# --- ส่วนการตั้งค่า API ---
#API_KEY = "xxxxx"
# แก้จาก API_KEY = "AIza..." เป็นตัวนี้
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

DB_FILE = "file_id.txt"


def save_file_id(fid):
    with open(DB_FILE, "w") as f:
        f.write(fid)


def load_file_id():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return f.read().strip()
    return None


# --- ส่วนการจัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_id" not in st.session_state:
    st.session_state.file_id = load_file_id()

# --- ส่วน Admin (Sidebar) ---
with st.sidebar:
    st.header("⚙️ ผู้ดูแลระบบ")
    admin_password = st.text_input("รหัสผ่าน Admin", type="password")

    if admin_password == "admin123":
        uploaded_file = st.file_uploader("อัปโหลดเอกสารหลัก (PDF)", type="pdf")
        if uploaded_file:
            with st.spinner("กำลังอัปเดตไฟล์..."):
                with open("temp_master.pdf", "wb") as f:
                    f.write(uploaded_file.getbuffer())

                google_file = client.files.upload(file="temp_master.pdf")
                while google_file.state.name == "PROCESSING":
                    time.sleep(2)
                    google_file = client.files.get(name=google_file.name)

                st.session_state.file_id = google_file.name
                save_file_id(google_file.name)
                st.success("อัปเดตฐานความรู้เรียบร้อย!")

    if st.session_state.file_id:
        st.info(f"สถานะ: มีข้อมูลในระบบพร้อมตอบ")

# --- ส่วนหน้าจอสำหรับผู้ใช้งาน (Users) ---
st.divider()

# แสดงประวัติการแชท
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ส่วนรับคำถาม
if prompt := st.chat_input("สอบถามข้อมูลจากเอกสาร..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if st.session_state.file_id:
        with st.chat_message("assistant"):
            with st.spinner("กำลังประมวลผลคำตอบ..."):
                try:
                    target_file = client.files.get(name=st.session_state.file_id)

                    # เรียกใช้ Gemini พร้อมกับ System Instruction ที่เราตั้งไว้
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT  # <--- จุดที่ใส่ Instruction
                        ),
                        contents=[target_file, prompt]
                    )

                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error("ไม่สามารถดึงข้อมูลได้ (ไฟล์อาจหมดอายุ หรือ API ขัดข้อง)")
    else:
        st.warning("ขณะนี้ระบบยังไม่มีข้อมูลเอกสาร กรุณารอผู้ดูแลระบบอัปโหลดไฟล์ครับ")