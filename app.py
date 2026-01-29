import streamlit as st
from google import genai
import os

st.set_page_config(page_title="API Key Tester", page_icon="🛠️")

st.markdown("""
    <style>
    .stButton>button { background-color: #28a745; color: white; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛠️ เครื่องมือตรวจสอบ API Key")

# 1. ดึง Key จาก Secrets มาแสดง (ถ้ามี)
try:
    secret_key = st.secrets["GEMINI_API_KEY"]
    st.success("✅ พบ GEMINI_API_KEY ใน Secrets")
    use_secret = st.checkbox("ใช้ Key จาก Secrets ทดสอบ", value=True)
except:
    secret_key = ""
    st.warning("⚠️ ไม่พบ Key ใน Secrets")
    use_secret = False

# 2. ช่องกรอก Key ทดสอบ (เผื่ออยากลอง Key ใหม่สดๆ)
manual_key = st.text_input("หรือกรอก API Key ใหม่ที่นี่เพื่อทดสอบ:", type="password")

if st.button("เริ่มการตรวจสอบเดี๋ยวนี้ (Run Diagnostics)"):
    # เลือก Key ที่จะใช้
    target_key = secret_key if use_secret and not manual_key else manual_key

    if not target_key:
        st.error("❌ กรุณาใส่ API Key ก่อนครับ")
        st.stop()

    client = genai.Client(api_key=target_key, http_options={'api_version': 'v1beta'})

    st.divider()

    # --- STEP 1: ทดสอบการเชื่อมต่อ (List Models) ---
    st.subheader("1. ทดสอบการเชื่อมต่อ Server")
    try:
        models = list(client.models.list())
        model_names = [m.name for m in models if hasattr(m, 'name')]
        st.success(f"✅ เชื่อมต่อสำเร็จ! มองเห็นทั้งหมด {len(model_names)} โมเดล")
        with st.expander("ดูรายชื่อโมเดลทั้งหมด"):
            st.write(model_names)
    except Exception as e:
        st.error(f"❌ เชื่อมต่อไม่ได้: {e}")
        st.stop()  # ถ้าขั้นนี้ไม่ผ่าน ให้หยุดเลย

    # --- STEP 2: ทดสอบโควตา (Generate Content) ---
    st.subheader("2. ทดสอบการส่งข้อความ (เช็คโควตา)")

    # ลองโมเดลมาตรฐาน
    test_models = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro"]

    for model_name in test_models:
        st.write(f"กำลังทดสอบยิงไปที่: `{model_name}` ...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Hello, this is a connection test."
            )
            st.success(f"✅ **ผ่าน!** โมเดล {model_name} ตอบกลับมาว่า: \"{response.text}\"")
            st.balloons()
            break  # ถ้าเจอตัวที่ผ่านแล้ว ให้หยุดเทส
        except Exception as e:
            st.error(f"❌ {model_name} ล้มเหลว: {e}")
            if "429" in str(e):
                st.warning("👉 สาเหตุ: โควตาเต็ม (Quota Exceeded) หรือยังไม่ได้ผูก Billing")
            elif "404" in str(e):
                st.warning("👉 สาเหตุ: หาโมเดลไม่เจอ (ชื่อผิด หรือ Key ไม่มีสิทธิ์)")
            elif "403" in str(e):
                st.warning("👉 สาเหตุ: API Key ถูกระงับ หรือเป็น Key ผิด")