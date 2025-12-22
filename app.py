import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import os

# 1. إعداد الصفحة
st.set_page_config(page_title="AI E-Waste Sorter v3", layout="centered", page_icon="♻️")

# --- 2. دالة الاتصال بـ Google Sheets ---
def save_to_sheets(data):
    try:
        # جلب الاعتمادات من Secrets
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # تصحيح الـ Private Key في حال وجود مشاكل في التنسيق
        creds_dict = dict(google_info)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # فتح الملف (تأكد أن الاسم مطابق تماماً في حسابك)
        sheet = client.open("E-Waste Database").sheet1
        
        # تجهيز السطر للحفظ
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            timestamp, 
            data.get('model', 'Unknown'), 
            data.get('type', 'Unknown'), 
            data.get('gold_mg', 0), 
            data.get('value_usd', 0)
        ]
        
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال بـ Google Sheets: {e}")
        return False

# --- 3. دالة إعداد الموديل ---
def configure_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
        # استخدام الموديل الأحدث لحل مشكلة 404
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        return None

# --- 4. إدارة مفتاح API ---
if 'api_key' not in st.session_state:
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

st.title("♻️ نظام فرز الخردة الإلكترونية الذكي")

with st.sidebar:
    st.header("⚙️ الإعدادات")
    new_key = st.text_input("Gemini API Key:", value=st.session_state.api_key, type="password")
    if st.button("تحديث المفتاح"):
        st.session_state.api_key = new_key
        st.rerun()

if not st.session_state.api_key:
    st.warning("⚠️ يرجى إدخال مفتاح Gemini API في القائمة الجانبية.")
    st.stop()

model = configure_gemini(st.session_state.api_key)

# --- 5. واجهة المستخدم (الصور) ---
upload_option = st.radio("مصدر الصورة:", ("رفع من الاستوديو", "التقاط بالكاميرا"))

if upload_option == "التقاط بالكاميرا":
    img_file = st.camera_input("صوّر القطعة")
else:
    img_file = st.file_uploader("اختر صورة", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة الجاري معالجتها", use_container_width=True)
    
    if st.button("🚀 تحليل وحفظ في قاعدة البيانات", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري التعرف والتقدير..."):
            try:
                # البرومبت لاستخراج JSON دقيق
                prompt = """
                Analyze this electronic component image.
                Return ONLY a JSON object with these keys:
                {"model": "name", "type": "CPU/RAM", "gold_mg": number, "value_usd": number}
                """
                
                response = model.generate_content([prompt, img])
                
                # تنظيف الرد
                raw_json = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(raw_json)
                
                # عرض النتائج للمستخدم
                st.subheader("📊 النتائج المستخرجة:")
                c1, c2 = st.columns(2)
                c1.metric("الموديل", data['model'])
                c1.metric("النوع", data['type'])
                c2.metric("ذهب (mg)", data['gold_mg'])
                c2.metric("القيمة ($)", data['value_usd'])
                
                # --- تفعيل دالة الحفظ (بدون تعليق) ---
                success = save_to_sheets(data)
                
                if success:
                    st.success("✅ تم التعرف وحفظ البيانات في Google Sheets بنجاح!")
                    st.balloons()
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    st.error("⚠️ انتهت حصة المفتاح (Quota). أدخل مفتاحاً جديداً في الجانب.")
                elif "404" in error_str:
                    st.error("❌ خطأ 404: تأكد من تحديث ملف requirements.txt إلى google-generativeai>=0.8.3")
                else:
                    st.error(f"حدث خطأ: {e}")

# Footer
st.markdown("---")
st.caption("نظام فرز ذكي متصل بالسحابة | v3.0 Final")
