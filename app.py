import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
import time
from PIL import Image

# --- 1. System Prompt ---
SYSTEM_PROMPT = """
บทบาท: คุณคือ Digital CMRU AI Service ผู้เชี่ยวชาญด้านข้อมูลอัจฉริยะของมหาวิทยาลัยราชภัฏเชียงใหม่
ลักษณะการตอบ: สุภาพ มีหางเสียง (ครับ/ค่ะ) อ้างอิงข้อมูลจาก PDF ที่แนบมาเท่านั้น
"""

# --- 2. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Digital CMRU Ai Service", page_icon="🤖")


# --- 3. ฟังก์ชันดึงรายการ API Keys ทั้งหมดที่มีใน Secrets ---
def get_all_api_keys():
    keys = []
    # ตรวจสอบ Key หลัก
    if "GEMINI_API_KEY" in st.secrets:
        keys.append(st.secrets["GEMINI_API_KEY"])
    # ตรวจสอบ Key สำรองตัวอื่นๆ (Key_2, Key_3, ...)
    i = 2
    while f"GEMINI_API_KEY_{i}" in st.secrets:
        keys.append(st.secrets[f"GEMINI_API_KEY_{i}"])
        i += 1
    return keys


# --- 4. ฟังก์ชันสร้าง Client ตามลำดับ Key ปัจจุบัน ---
def get_gemini_client():
    available_keys = get_all_api_keys()
    if not available_keys:
        st.error("⚠️ ไม่พบ API Key ในระบบ Secrets")
        st.stop()

    # ใช้ค่า index จาก session_state มาเลือก Key (ใช้ % เพื่อให้วนลูปกลับมาตัวแรกได้)
    current_idx = st.session_state.get("key_index", 0) % len(available_keys)

    return genai.Client(
        api_key=available_keys[current_idx],
        http_options={'api_version': 'v1beta'}
    )


# --- 5. ฟังก์ชันดึงข้อความจาก PDF ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    content = page.extract_text()
                    if content: text += content
        except:
            pass
    return text


# --- 6. จัดการ Session State ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

# --- 7. UI ส่วนหัวและ Admin ---
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        st.image(Image.open('795.jpg'), use_container_width=True)
    except:
        st.write("📌 **DIGITAL CMRU**")

st.markdown("<h1 style='text-align: center;'>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Admin")
    admin_pw = st.text_input("รหัสผ่าน", type="password")
    if admin_pw == "admin123":
        up_file = st.file_uploader("อัปโหลด PDF", type="pdf")
        if up_file:
            with open("data.pdf", "wb") as f:
                f.write(up_file.getbuffer())
            st.success("อัปเดตไฟล์สำเร็จ!")

    st.divider()
    total_keys = len(get_all_api_keys())
    current_key_num = (st.session_state.key_index % total_keys) + 1
    st.info(f"🔑 กำลังใช้ Account ที่: {current_key_num} จากทั้งหมด {total_keys}")

# --- 8. ส่วนแชทและระบบ Auto-Switch Key ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("พิมพ์คำถามที่นี่..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf"):
        with st.chat_message("assistant"):
            with st.spinner("กำลังประมวลผล..."):
                all_keys = get_all_api_keys()
                max_attempts = len(all_keys)
                attempts = 0
                success = False

                while not success and attempts < max_attempts:
                    try:
                        client = get_gemini_client()
                        context = get_pdf_text("data.pdf")

                        response = client.models.generate_content(
                            model="gemini-1.5-flash-latest",
                            contents=[
                                f"Instruction: {SYSTEM_PROMPT}",
                                f"Context: {context}",
                                f"Query: {prompt}"
                            ]
                        )
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        success = True
                    except Exception as e:
                        if "429" in str(e):  # กรณีโควตาเต็ม
                            st.session_state.key_index += 1  # สลับ index ไปตัวถัดไป
                            attempts += 1
                            if attempts < max_attempts:
                                st.warning(
                                    f"โควตา Account ที่ {attempts} เต็ม กำลังสลับไปใช้ Account ที่ {attempts + 1}...")
                                time.sleep(1)  # รอเล็กน้อยก่อนลองใหม่
                            else:
                                st.error("⚠️ ขออภัยครับ โควตาทุก Account เต็มแล้วจริงๆ กรุณารอสัก 2-3 นาทีครับ")
                        else:
                            st.error(f"เกิดข้อผิดพลาดทางเทคนิค: {e}")
                            break
    else:
        st.warning("กรุณาอัปโหลดไฟล์ข้อมูลก่อนครับ")