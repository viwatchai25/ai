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


# --- 3. เชื่อมต่อ Client ---
@st.cache_resource
def get_client():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        # ลองใช้ v1beta เพราะมักจะเห็นโมเดลเยอะกว่า
        return genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    except Exception as e:
        st.error(f"⚠️ Key Error: {e}")
        return None


client = get_client()


# --- 4. ฟังก์ชัน PDF ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    c = page.extract_text()
                    if c: text += c
            # ตัดทอนข้อมูล 40k
            if len(text) > 40000: text = text[:40000]
        except:
            pass
    return text


# --- 5. Admin & Diagnostics (จุดสำคัญแก้ปัญหา) ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# ตัวแปรเก็บชื่อโมเดลที่ค้นเจอ
FOUND_MODEL = None

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    st.subheader("🛠️ System Diagnostics")

    if client:
        try:
            # 1. ดึงรายชื่อโมเดลทั้งหมดออกมาดู
            with st.spinner("Checking models..."):
                models = list(client.models.list())

            # 2. กรองหาโมเดลที่ใช้ generateContent ได้
            valid_models = []
            for m in models:
                if "generateContent" in m.supported_generation_methods:
                    # ตัด gemini-2.0 ออกเพราะโควตา 0
                    if "gemini-2.0" not in m.name:
                        valid_models.append(m.name)

            # 3. เลือกโมเดลที่ดีที่สุดจากรายการที่มีอยู่จริง
            if valid_models:
                # ลำดับความชอบ: Flash > Pro > 1.0
                priority = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

                for p in priority:
                    for v in valid_models:
                        if p in v:
                            FOUND_MODEL = v
                            break
                    if FOUND_MODEL: break

                # ถ้ายังไม่เจอใน priority ให้เอาตัวแรกที่มีเลย
                if not FOUND_MODEL:
                    FOUND_MODEL = valid_models[0]

                st.success(f"✅ Active Model: **{FOUND_MODEL.split('/')[-1]}**")
                with st.expander("ดูรายชื่อโมเดลทั้งหมด"):
                    st.write(valid_models)
            else:
                st.error("❌ Key นี้ไม่พบโมเดลที่ใช้งานได้เลย")

        except Exception as e:
            st.error(f"Error Checking Models: {e}")

# --- 6. Chat Logic ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client and FOUND_MODEL:
        with st.chat_message("assistant"):
            with st.spinner(f"AI ({FOUND_MODEL.split('/')[-1]}) กำลังทำงาน..."):
                try:
                    context = get_pdf_text("data.pdf")

                    # เรียกใช้โมเดลที่ค้นเจอมาแล้ว (ไม่ต้องเดาชื่อ)
                    response = client.models.generate_content(
                        model=FOUND_MODEL,
                        contents=[f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                    )
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    if "429" in str(e):
                        st.info("💡 ระบบทำงานหนัก กรุณารอ 5-10 วินาที")
    else:
        if not FOUND_MODEL:
            st.error("⚠️ ไม่สามารถระบุโมเดลได้ (ตรวจสอบ API Key)")
        elif not os.path.exists("data.pdf"):
            st.warning("กรุณาอัปโหลด PDF ก่อนใช้งาน")