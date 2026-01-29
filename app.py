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
        # ใช้ v1beta เพื่อความเข้ากันได้สูงสุด
        return genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
    except Exception as e:
        st.error(f"⚠️ Key Error: {e}")
        return None


client = get_client()


# --- 4. ฟังก์ชัน PDF (ตัดทอนข้อมูลป้องกัน System Busy) ---
def get_pdf_text(pdf_path):
    text = ""
    if os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    c = page.extract_text()
                    if c: text += c
            # ตัดทอนข้อมูลเหลือ 40,000 ตัวอักษร
            if len(text) > 40000: text = text[:40000]
        except:
            pass
    return text


# --- 5. Admin & Model Selector (แก้ Code Error ตรงนี้) ---
if "chat_history" not in st.session_state: st.session_state.chat_history = []

FOUND_MODEL = None

with st.sidebar:
    st.header("⚙️ Admin")
    if st.text_input("Password", type="password") == "admin123":
        if f := st.file_uploader("Upload PDF", type="pdf"):
            with open("data.pdf", "wb") as file: file.write(f.getbuffer())
            st.success("Saved!")

    st.divider()
    st.subheader("🛠️ Connection Status")

    if client:
        try:
            # 1. ดึงรายชื่อโมเดล (แบบปลอดภัย ไม่เช็ค attribute ลึก)
            models = list(client.models.list())

            # 2. แปลงเป็น list ของ "ชื่อ" (String) เท่านั้น เพื่อความง่าย
            model_names = []
            for m in models:
                # เช็คแค่ว่ามี attribute 'name' หรือไม่ (มาตรฐานสุดๆ)
                if hasattr(m, 'name'):
                    model_names.append(m.name)

            # 3. ค้นหาโมเดลที่ต้องการจากชื่อ
            # ลำดับความสำคัญ: Flash (เร็ว/ถูก) > Pro (เก่ง)
            priority_keywords = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]

            for keyword in priority_keywords:
                for name in model_names:
                    # กรองเอาเฉพาะตัวที่ไม่ใช่ 2.0 (เพราะโควตา 0) และมี keyword ที่เราอยากได้
                    if keyword in name and "gemini-2.0" not in name:
                        FOUND_MODEL = name
                        break
                if FOUND_MODEL: break

            # Fallback: ถ้าหาไม่เจอเลย ให้ใช้ Hardcode ค่ามาตรฐาน
            if not FOUND_MODEL:
                FOUND_MODEL = "models/gemini-1.5-flash"
                st.warning("⚠️ ใช้ค่า Default Model (เนื่องจากค้นหาไม่เจอ)")
            else:
                st.success(f"✅ Active: **{FOUND_MODEL.split('/')[-1]}**")

        except Exception as e:
            # ถ้า API List พังจริงๆ ให้บังคับใช้ค่านี้ไปเลย
            FOUND_MODEL = "models/gemini-1.5-flash"
            st.error(f"List Error (Using Default): {e}")

# --- 6. Chat Logic (Retry System) ---
st.divider()
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามข้อมูลได้เลยครับ..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if os.path.exists("data.pdf") and client and FOUND_MODEL:
        with st.chat_message("assistant"):
            with st.spinner(f"AI กำลังทำงาน..."):
                try:
                    context = get_pdf_text("data.pdf")

                    # Retry Logic แบบง่าย
                    success = False
                    for i in range(3):  # ลอง 3 ครั้ง
                        try:
                            response = client.models.generate_content(
                                model=FOUND_MODEL,
                                contents=[f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                            )
                            st.markdown(response.text)
                            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                            success = True
                            break
                        except Exception as e:
                            # ถ้าเป็น 429 ให้รอ
                            if "429" in str(e):
                                time.sleep(2)
                                continue
                            elif "404" in str(e):
                                # ถ้าชื่อโมเดลผิด ลองเปลี่ยนชื่อหน้างาน
                                try:
                                    fallback_model = "gemini-1.5-flash-latest"
                                    response = client.models.generate_content(
                                        model=fallback_model,
                                        contents=[f"System: {SYSTEM_PROMPT}", f"Context: {context}", f"User: {prompt}"]
                                    )
                                    st.markdown(response.text)
                                    st.session_state.chat_history.append(
                                        {"role": "assistant", "content": response.text})
                                    success = True
                                    break
                                except:
                                    continue
                            else:
                                st.error(f"Error: {e}")
                                break

                    if not success:
                        st.error("⚠️ ระบบไม่สามารถตอบกลับได้ในขณะนี้ (ลองกดถามใหม่อีกครั้ง)")

                except Exception as e:
                    st.error(f"Critical Error: {e}")
    else:
        if not os.path.exists("data.pdf"):
            st.warning("กรุณาอัปโหลด PDF ก่อนใช้งาน")
        elif not FOUND_MODEL:
            st.error("ตรวจสอบ API Key")