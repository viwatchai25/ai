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


# --- 3. เชื่อมต่อ API (Auto-Discovery) ---
@st.cache_resource
def setup_genai():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})

        # ค้นหาโมเดลอัตโนมัติ
        try:
            available_models = list(client.models.list())
            target_model = None
            # เน้นหา Flash ก่อน เพราะเร็วและรองรับ Context ยาว
            keywords = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

            for kw in keywords:
                for m in available_models:
                    if kw in m.name:
                        target_model = m.name
                        break
                if target_model: break
        except:
            # ถ้า list models ไม่ได้ ให้ใช้ค่า Default
            target_model = "models/gemini-1.5-flash"

        if not target_model: target_model = "models/gemini-1.5-flash"

        return client, target_model
    except Exception as e:
        st.error(f"⚠️ Key Error: {e}")
        return None, None


client, MODEL_NAME = setup_genai()


# --- 4. ฟังก์ชัน Retry Logic (ปรับปรุงใหม่ แสดง Error จริง) ---
def generate_safe(client, model, contents):
    last_error = ""
    # ลอง 3 รอบ
    for i in range(3):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:  # โควตาเต็ม ให้รอ
                time.sleep(2 + i)  # รอ 2, 3, 4 วินาที
                continue
            elif "404" in last_error:  # หาโมเดลไม่เจอ ลองใช้ชื่อสำรอง
                try:
                    return client.models.generate_content(model="gemini-1.5-flash-latest", contents=contents)
                except Exception as e2:
                    last_error = str(e2)
                    time.sleep(1)
                    continue
            else:
                # Error อื่นๆ ให้รอแป๊บแล้วลองใหม่
                time.sleep(1)
                continue

    # ถ้าหลุดลูปมาแสดงว่าล้มเหลว
    raise Exception(f"Failed after 3 retries. Last error: {last_error}")


# --- 5. ฟังก์ชัน PDF (ตัดทอนข้อมูลอัตโนมัติ) ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    c = page.extract_text()
                    if c: text += c

            # --- IMPORTANT: ตัดทอนข้อมูล (Data Truncation) ---
            # จำกัดไม่เกิน 40,000 ตัวอักษรเพื่อป้องกัน System Busy / Quota Limit
            max_chars = 40000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[เนื้อหาถูกตัดทอนบางส่วนเนื่องจากยาวเกินไป]..."

        except:
            pass
    return text


# --- 6. Admin & Sidebar ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    if MODEL_NAME:
        st.success(f"✅ AI Ready: {MODEL_NAME.split('/')[-1]}")
    else:
        st.error("❌ API Key Error")

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

                    # ตรวจสอบว่ามีข้อมูล PDF จริงไหม
                    if len(context) < 10:
                        st.warning("⚠️ ไฟล์ PDF อ่านไม่ออก หรือไม่มีข้อความ (อาจเป็นไฟล์ภาพ)")
                    else:
                        response = generate_safe(
                            client,
                            MODEL_NAME,
                            [f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                        )
                        st.markdown(response.text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})

                except Exception as e:
                    # แสดง Error ที่แท้จริงออกมา
                    st.error(f"เกิดข้อผิดพลาด: {e}")

                    if "403" in str(e) or "API key" in str(e):
                        st.info("💡 คำแนะนำ: Key ของคุณอาจถูกระงับหรือใช้ไม่ได้ กรุณาสร้าง Key ใหม่")
                    elif "429" in str(e):
                        st.info("💡 คำแนะนำ: ระบบทำงานหนักเกินไป กรุณารอ 1 นาที")
    else:
        st.warning("กรุณาอัปโหลด PDF และตรวจสอบ API Key")