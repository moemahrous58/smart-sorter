import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import os

# 1. إعداد الصفحة
st.set_page_config(page_title="Smart Sorter v4", layout="centered", page_icon="♻️")

# --- 2. دالة الاتصال بـ Google Sheets ---
def save_to_sheets(data):
    try:
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(google_info)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("E-Waste Database").sheet1
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, data.get('model'), data.get('type'), data.get('gold_mg'), data.get('value_usd')]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ فشل الحفظ في Sheets: {e}")
        return False

# --- 3. دالة استدعاء الموديل (الحل السحري لخطأ 404) ---
def get_model_safely(api_key):
    try:
        genai.configure(api_key=api_key)
        # محاولات استدعاء الموديل بصيغ مختلفة لتجنب خطأ 404
        test_models = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-pro', 'models/gemini-1.5-pro']
        
        for model_name in test_models:
            try:
                m = genai.GenerativeModel(model_name)
                # اختبار بسيط جداً للتأكد من أن الموديل "يسمعنا"
                m.generate_content("ping", generation_config={"max_output_tokens": 1})
                return m, model_name
            except:
                continue
        return None, None
    except:
        return None, None

# --- 4. إدارة مفتاح API ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

st.title("🛡️ نظام الفرز الإلكتروني (v4.0)")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    user_key = st.text_input("Gemini API Key", value=st.session_state.api_key, type="password")
    if st.button("تحديث المفتاح ونظام الموديلات"):
        st.session_state.api_key = user_key
        st.rerun()

# استدعاء الموديل
model, active_model_name = get_model_safely(st.session_state.api_key)

if not model:
    st.error("❌ لا تزال مشكلة 404 قائمة (الموديل غير متاح).")
    st.info("💡 الحل الوحيد المتبقي: اذهب لـ Streamlit Cloud واعمل **Reboot** للتطبيق، أو استخدم API Key جديد تماماً من Google AI Studio.")
    st.stop()
else:
    st.success(f"✅ تم الاتصال بنجاح عبر: {active_model_name}")

# --- 5. واجهة العمل ---
img_file = st.camera_input("صوّر القطعة (CPU/RAM)")

if not img_file:
    img_file = st.file_uploader("أو اختر صورة من الاستوديو", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة الجاري تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل والحفظ الفوري", type="primary", use_container_width=True):
        with st.spinner(f"جاري استخدام {active_model_name}..."):
            try:
                prompt = """
                Analyze this part. Return ONLY JSON:
                {"model": "name", "type": "CPU/RAM", "gold_mg": number, "value_usd": number}
                """
                response = model.generate_content([prompt, img])
                
                # استخراج JSON
                raw_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(raw_text)
                
                # عرض النتائج
                st.subheader("📊 البيانات المستخرجة:")
                col1, col2 = st.columns(2)
                col1.metric("الموديل", data['model'])
                col2.metric("ذهب (mg)", f"{data['gold_mg']} mg")
                
                # الحفظ الفعلي (تم تفعيلها)
                if save_to_sheets(data):
                    st.success("✅ تم التحليل والحفظ في Google Sheets!")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"⚠️ خطأ في التحليل: {e}")
