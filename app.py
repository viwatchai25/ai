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


# --- 3. ฟังก์ชันดึงรายการ API Keys ทั้งหมด ---
def get_all_api_keys():
    keys = []
    if "GEMINI_API_KEY" in st.secrets:
        keys.append(st.secrets["GEMINI_API_KEY"])
    i = 2
    while f"GEMINI_API_KEY_{i}" in st.secrets:
        keys.append(st.secrets[f"GEMINI_API_KEY_{i}"])
        i += 1
    return keys


# --- 4. ฟังก์ชันสร้าง Client ---
def get_gemini_client():
    available_keys = get_all_api_keys()
    if not available_keys:
        st.error("⚠️ ไม่พบ API Key ในระบบ Secrets")
        st.stop()
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
    all_keys = get_all_api_keys()
    total_keys = len(all_keys)
    current_key_num = (st.session_state.key_index % total_keys) + 1
    st.info(f"🔑 ใช้ Account ที่: {current_key_num}/{total_keys}")

# --- 8. ส่วนแชทและระบบ Auto-Switch Model & Key (Fixed NameError) ---
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
                model_names = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash-8b"]

                success = False
                key_attempts = 0
                last_error = ""  # ใช้เก็บ Error ล่าสุดเพื่อเลี่ยง NameError

                while not success and key_attempts < len(all_keys):
                    client = get_gemini_client()
                    context = get_pdf_text("data.pdf")

                    for model_name in model_names:
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=[
                                    f"Instruction: {SYSTEM_PROMPT}",
                                    f"Context: {context}",
                                    f"Query: {prompt}"
                                ]
                            )
                            st.markdown(response.text)
                            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                            success = True
                            break
                        except Exception as error_obj:
                            last_error = str(error_obj)
                            if "404" in last_error:
                                continue
                            elif "429" in last_error:
                                st.session_state.key_index += 1
                                key_attempts += 1
                                break
                            else:
                                st.error(f"เกิดข้อผิดพลาด: {last_error}")
                                success = True
                                break

                    if not success and "429" not in last_error:
                        break
    else:
        st.warning("กรุณาอัปโหลดไฟล์ข้อมูลก่อนครับ")