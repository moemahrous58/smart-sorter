import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import os

# 1. إعداد الصفحة
st.set_page_config(page_title="AI E-Waste Sorter", layout="centered", page_icon="♻️")

# --- دالة إعداد الموديل ---
def configure_gemini(api_key):
    try:
        genai.configure(api_key=api_key)
        # استخدام الموديل الأحدث والأسرع (يدعم الصور والنصوص معاً)
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        return None

# --- دالة الربط مع Google Sheets ---
def save_to_sheets(data):
    try:
        # التأكد من وجود البيانات السرية في Secrets
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
        client = gspread.authorize(creds)
        
        # افتح الجدول (تأكد من تسميته E-Waste Database في حسابك)
        sheet = client.open("E-Waste Database").sheet1
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, data.get('model'), data.get('type'), data.get('gold_mg'), data.get('value_usd')]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ البيانات في Google Sheets: {e}")
        return False

# --- الواجهة الرئيسية وإدارة مفتاح API ---
if 'api_key' not in st.session_state:
    # محاولة جلب المفتاح من Secrets أولاً كافتراضي
    st.session_state.api_key = st.secrets.get("GEMINI_API_KEY", "")

st.title("📸 نظام فرز الخردة الإلكترونية الذكي")

# التحقق إذا كان المفتاح يعمل أو يحتاج تحديث
with st.sidebar:
    st.header("⚙️ الإعدادات")
    new_key = st.text_input("Gemini API Key:", value=st.session_state.api_key, type="password")
    if st.button("تحديث المفتاح"):
        st.session_state.api_key = new_key
        st.success("تم تحديث المفتاح!")

if not st.session_state.api_key:
    st.warning("⚠️ يرجى إدخال مفتاح Gemini API في القائمة الجانبية للبدء.")
    st.stop()

model = configure_gemini(st.session_state.api_key)

# --- رفع أو التقاط الصورة ---
option = st.radio("اختر طريقة إدخال الصورة:", ("كاميرا الموبايل", "رفع صورة من الاستوديو"))

if option == "كاميرا الموبايل":
    img_file = st.camera_input("التقط صورة للقطعة")
else:
    img_file = st.file_uploader("اختر صورة", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة الجاري تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل وحفظ البيانات", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري التعرف على القطعة وتقدير القيمة..."):
            try:
                # البرومبت الاحترافي لاستخراج JSON
                prompt = """
                Analyze this electronic component. 
                Identify:
                1. Exact Model Name.
                2. Component Type (CPU, RAM, IC, etc.).
                3. Estimated Gold Content in milligrams (mg) based on recycling standards.
                4. Estimated scrap value in USD.
                
                You MUST respond ONLY with a JSON object like this:
                {"model": "Intel Pentium Pro", "type": "CPU", "gold_mg": 500, "value_usd": 35.5}
                """
                
                response = model.generate_content([prompt, img])
                
                # تنظيف النص المستخرج وتحويله لقاموس Python
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(res_text)
                
                # عرض النتائج
                st.subheader("📊 نتائج التحليل:")
                col1, col2 = st.columns(2)
                col1.metric("الموديل", data['model'])
                col1.metric("النوع", data['type'])
                col2.metric("كمية الذهب", f"{data['gold_mg']} mg")
                col2.metric("القيمة التقديرية", f"${data['value_usd']}")
                
                # حفظ في Google Sheets
                if save_to_sheets(data):
                    st.success("✅ تم حفظ البيانات في السحابة بنجاح!")
                    st.balloons()
                    
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "quota" in error_str.lower():
                    st.error("❌ انتهت الحصة المسموحة (Quota) لهذا المفتاح. يرجى إدخال مفتاح API جديد في القائمة الجانبية.")
                    # تصفير المفتاح لطلب واحد جديد
                    st.session_state.api_key = ""
                elif "404" in error_str:
                    st.error("❌ الموديل المستخدم غير مدعوم حالياً. تأكد من استخدام موديل gemini-1.5-flash.")
                else:
                    st.error(f"حدث خطأ أثناء التحليل: {e}")

# Footer
st.markdown("---")
st.caption("Powered by Gemini 1.5 Flash AI | Connected to Google Sheets")
