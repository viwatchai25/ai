import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import os
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


# --- 3. ฟังก์ชันเชื่อมต่อ API และค้นหาโมเดล (แก้ไขจุดที่ Error) ---
@st.cache_resource
def configure_genai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        # ใช้ v1beta เพื่อให้เห็นโมเดลเยอะที่สุด
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})

        # ดึงรายชื่อโมเดลทั้งหมด
        available_models = client.models.list()
        selected_model = None

        # คำค้นหาตามลำดับความต้องการ (Flash เร็วและถูกที่สุด > Pro เก่งกว่า > หรือรุ่นอื่นๆ)
        priority_keywords = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

        # วนลูปหาโมเดลที่ชื่อตรงกับที่เราอยากได้ (ตัดการเช็ค attribute ที่ error ออก)
        # เราแปลงเป็น list ก่อนเพื่อความชัวร์ในการวนลูป
        model_list = list(available_models)

        for keyword in priority_keywords:
            for m in model_list:
                # ตรวจสอบแค่ชื่อก็เพียงพอแล้ว
                if keyword in m.name:
                    selected_model = m.name
                    break
            if selected_model: break

        if not selected_model:
            # ถ้าหาไม่เจอเลย ให้ลองใช้ชื่อ default (เผื่อฟลุ๊ค)
            selected_model = "gemini-1.5-flash"

        return client, selected_model
    except Exception as e:
        # แสดง error แต่ไม่หยุดโปรแกรม เพื่อให้ user เห็นปัญหา
        st.error(f"⚠️ ตั้งค่าระบบไม่สำเร็จ: {e}")
        return None, None


client, MODEL_NAME = configure_genai()


# --- 4. ฟังก์ชันดึง Text จาก PDF ---
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


# --- 5. Session State ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

# --- 6. Admin Sidebar ---
with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    if MODEL_NAME:
        # แสดงชื่อโมเดลสั้นๆ (ตัด parts/models/ ออก)
        display_name = MODEL_NAME.split('/')[-1]
        st.caption(f"🚀 Model: **{display_name}**")
    else:
        st.error("❌ No Model Found")

    if os.path.exists("data.pdf"):
        st.info("✅ Database Ready")

# --- 7. Chat Interface ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client and MODEL_NAME:
        with st.chat_message("assistant"):
            with st.spinner(f"AI กำลังค้นหาคำตอบ..."):
                try:
                    context = get_pdf_text("data.pdf")

                    response = client.models.generate_content(
                        model=MODEL_NAME,  # ใช้ชื่อที่ระบบหามาให้
                        contents=[
                            f"System: {SYSTEM_PROMPT}",
                            f"Context: {context}",
                            f"User: {prompt}"
                        ]
                    )
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    if "429" in str(e):
                        st.warning("⚠️ โควตาเต็มชั่วคราว กรุณารอ 30 วินาที")
    else:
        if not os.path.exists("data.pdf"):
            st.warning("กรุณาอัปโหลดไฟล์ PDF ก่อนใช้งาน")
        if not client or not MODEL_NAME:
            st.error("ระบบ AI ยังไม่พร้อมทำงาน (ตรวจสอบ API Key)")