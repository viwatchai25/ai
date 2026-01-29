import streamlit as st
from google import genai
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


# --- 3. ฟังก์ชันเชื่อมต่อและค้นหาโมเดลอัตโนมัติ (แก้ 404) ---
@st.cache_resource
def setup_genai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})

        # 1. ดึงรายชื่อโมเดลทั้งหมดที่ Key นี้มองเห็น
        available_models = list(client.models.list())

        # 2. ค้นหาโมเดล Flash ที่ดีที่สุด
        target_model = None
        # ลำดับการค้นหา: เอา Flash ล่าสุด -> Flash ธรรมดา -> หรือ Pro
        keywords = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

        for kw in keywords:
            for m in available_models:
                if kw in m.name:
                    target_model = m.name
                    break
            if target_model: break

        # 3. ถ้าหาไม่เจอจริงๆ ให้ใช้ค่า Default (Fallback)
        if not target_model:
            target_model = "gemini-1.5-flash"

        return client, target_model
    except Exception as e:
        st.error(f"⚠️ API Error: {e}")
        return None, None


client, MODEL_NAME = setup_genai()


# --- 4. ฟังก์ชัน Retry (แก้ 429 Resource Exhausted) ---
def generate_safe(client, model, contents):
    for i in range(3):  # ลองใหม่ 3 ครั้ง
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if "429" in str(e):  # ถ้าโควตาเต็ม ให้รอ
                time.sleep(2 * (i + 1))
                continue
            elif "404" in str(e):  # ถ้าหาโมเดลไม่เจอในรอบนี้
                # ลองเปลี่ยนชื่อโมเดลแบบ Hardcode เป็นทางเลือกสุดท้าย
                try:
                    return client.models.generate_content(model="models/gemini-1.5-flash-latest", contents=contents)
                except:
                    raise e
            else:
                raise e
    raise Exception("System Busy")


# --- 5. ฟังก์ชัน PDF ---
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


# --- 6. Admin Sidebar ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    if MODEL_NAME:
        st.success(f"✅ Connected: {MODEL_NAME.split('/')[-1]}")
    else:
        st.error("❌ Disconnected")

# --- 7. Chat ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client and MODEL_NAME:
        with st.chat_message("assistant"):
            with st.spinner("AI กำลังค้นหาคำตอบ..."):
                try:
                    context = get_pdf_text("data.pdf")
                    response = generate_safe(
                        client,
                        MODEL_NAME,
                        [f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                    )
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    st.caption("คำแนะนำ: ลองสร้าง API Key ใหม่จาก Google AI Studio")
    else:
        st.warning("ระบบยังไม่พร้อม (กรุณาอัปโหลด PDF หรือตรวจสอบ API Key)")