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
ลักษณะการตอบ: สุภาพ เป็นกันเอง มีหางเสียง (ครับ/ค่ะ) และมีความเป็นมืออาชีพ
หน้าที่: ตอบคำถามโดยอ้างอิงข้อมูลจาก 'เอกสารแนบ' เท่านั้น หากข้อมูลไม่เพียงพอให้แจ้งผู้ใช้ตามตรง
"""

# --- 2. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Digital CMRU Ai Service", page_icon="🤖")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #003399; color: white; border-radius: 8px; width: 100%; }
    h1 { color: #003399; font-family: 'Sarabun', sans-serif; text-align: center; }
    .stChatInput { position: fixed; bottom: 0; }
    </style>
    """, unsafe_allow_html=True)

# ส่วนหัว
col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    try:
        st.image(Image.open('795.jpg'), use_container_width=True)
    except:
        st.markdown("### 🌐 DIGITAL CMRU")
st.markdown("<h1>Digital CMRU Ai Service</h1>", unsafe_allow_html=True)


# --- 3. ฟังก์ชันเชื่อมต่อ API (Force Stable Model) ---
@st.cache_resource
def get_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        # ใช้ v1beta เพื่อความยืดหยุ่น แต่เราจะบังคับ model name ทีหลัง
        return genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    except Exception as e:
        st.error(f"⚠️ API Error: {e}")
        return None


client = get_client()


# --- 4. ฟังก์ชัน Retry Logic (หัวใจสำคัญแก้ 429) ---
def generate_with_retry(client, model_name, contents):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents
            )
        except Exception as e:
            error_msg = str(e)
            # ถ้าเป็น Error 429 (Quota) หรือ 503 (Server Overload) ให้รอแล้วลองใหม่
            if "429" in error_msg or "503" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # รอ 2, 4, 6 วินาที
                    time.sleep(wait_time)
                    continue
                else:
                    raise e  # ถ้าลองครบ 3 รอบแล้วยังไม่ได้ ให้แจ้ง Error จริง
            else:
                raise e  # ถ้าเป็น Error อื่น (เช่น 404) ให้แจ้งเลย


# --- 5. ฟังก์ชันดึง Text จาก PDF ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    c = page.extract_text()
                    if c: text += c
        except:
            pass
    return text


# --- 6. Session State & Sidebar ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    if os.path.exists("data.pdf"):
        st.info("✅ Database Ready")

    # แสดงเครดิต
    st.caption("Powered by Google Cloud Credit")

# --- 7. Chat Interface ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client:
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.markdown("⏳ *AI กำลังค้นหาข้อมูล...*")

            try:
                context = get_pdf_text("data.pdf")

                # เรียกใช้ฟังก์ชัน Retry แทนการเรียกตรงๆ
                # ใช้โมเดล 'gemini-1.5-flash' ซึ่งเสถียรที่สุดสำหรับ Billing Plan
                response = generate_with_retry(
                    client,
                    model_name="gemini-1.5-flash",
                    contents=[
                        f"System: {SYSTEM_PROMPT}",
                        f"Context: {context}",
                        f"User: {prompt}"
                    ]
                )

                status_placeholder.empty()  # ลบข้อความกำลังโหลด
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})

            except Exception as e:
                status_placeholder.empty()
                if "429" in str(e):
                    st.error("⚠️ ระบบกำลังทำงานหนัก กรุณารอ 10 วินาทีแล้วถามใหม่ครับ")
                elif "404" in str(e):
                    st.error("⚠️ ไม่พบโมเดล (ลองเปลี่ยน API Key ใหม่หากเพิ่งเปิด Billing)")
                else:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
    else:
        st.warning("กรุณาอัปโหลดไฟล์ PDF ก่อนใช้งาน")