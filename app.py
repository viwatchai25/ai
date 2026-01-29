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


# --- 3. ตั้งค่า Client (บังคับใช้ 1.5 Flash เท่านั้น) ---
@st.cache_resource
def setup_genai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        # ใช้ v1beta เพื่อความเข้ากันได้
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        return client
    except Exception as e:
        st.error(f"⚠️ Key Error: {e}")
        return None


client = setup_genai()


# --- 4. ฟังก์ชัน Retry Logic (หัวใจสำคัญ) ---
def generate_safe(client, contents):
    # รายชื่อโมเดลที่ "อนุญาต" ให้ใช้ (ตัด 2.0 ทิ้งไปเลย)
    safe_models = [
        "gemini-1.5-flash",  # ตัวเลือกที่ 1 (เสถียรสุด)
        "models/gemini-1.5-flash",  # ตัวเลือกที่ 2 (ชื่อเต็ม)
        "gemini-1.5-flash-latest",  # ตัวเลือกที่ 3 (ล่าสุด)
        "gemini-1.5-flash-001"  # ตัวเลือกที่ 4 (เวอร์ชันระบุเลข)
    ]

    last_error = ""

    # วนลูปโมเดลที่ปลอดภัย
    for model_name in safe_models:
        try:
            # ลองยิง API
            return client.models.generate_content(model=model_name, contents=contents)
        except Exception as e:
            error_text = str(e)
            last_error = error_text

            # ถ้าเป็น 429 (Resource Exhausted) ของ 1.5 Flash -> ให้รอแล้วลองใหม่ที่ตัวเดิม
            if "429" in error_text:
                time.sleep(2)
                try:
                    return client.models.generate_content(model=model_name, contents=contents)
                except:
                    continue  # ถ้ายังไม่ได้ ไปลองชื่ออื่น

            # ถ้าเป็น 404 (Not Found) -> ไปลองชื่อถัดไปทันที
            if "404" in error_text:
                continue

            # Error อื่นๆ -> ข้ามไปลองตัวอื่น
            continue

    # ถ้าลองทุกชื่อแล้วยังไม่ได้
    raise Exception(f"All models failed. Last error: {last_error}")


# --- 5. ฟังก์ชัน PDF (ตัดทอนข้อมูล 40k) ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    c = page.extract_text()
                    if c: text += c

            # ตัดทอนข้อมูลให้เหลือ 40,000 ตัวอักษร
            if len(text) > 40000:
                text = text[:40000] + "\n...[ตัดทอนข้อมูล]..."
        except:
            pass
    return text


# --- 6. Sidebar ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")
    st.divider()
    if os.path.exists("data.pdf"):
        st.success("✅ Database Ready")
    else:
        st.warning("⚠️ No PDF")

# --- 7. Chat ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client:
        with st.chat_message("assistant"):
            with st.spinner("AI กำลังค้นหาคำตอบ..."):
                try:
                    context = get_pdf_text("data.pdf")

                    if len(context) < 5:
                        st.error("⚠️ ไฟล์ PDF ไม่มีข้อความ")
                    else:
                        # เรียกฟังก์ชันที่ปลอดภัย
                        response = generate_safe(
                            client,
                            [f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                        )
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})

                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    if "429" in str(e):
                        st.info("💡 ระบบกำลังทำงานหนัก กรุณารอ 10 วินาที")
    else:
        st.warning("กรุณาอัปโหลด PDF ก่อนใช้งาน")