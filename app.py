import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# إعداد الصفحة
st.set_page_config(page_title="نظام فرز E-Waste", layout="centered")
st.title("📸 نظام فرز المخلفات الإلكترونية الذكي")

# جلب الإعدادات من Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    google_info = st.secrets["google_sheets"]
except Exception as e:
    st.error("خطأ في قراءة Secrets. تأكد من إضافتها في Streamlit Cloud.")
    st.stop()

# إعداد Google Sheets بالاسم المطلوب
def connect_to_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
    client = gspread.authorize(creds)
    # استخدام اسم الملف الخاص بك
    return client.open("E-Waste Database").sheet1

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# واجهة التطبيق
img_file = st.camera_input("التقط صورة للقطعة الإلكترونية")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة الملتقطة", use_container_width=True)
    
    if st.button("بدء التحليل بالذكاء الاصطناعي 🔍"):
        with st.spinner("جاري التحليل وحفظ البيانات..."):
            try:
                # طلب التحليل
                prompt = "Identify this electronic component. Return exactly: Name | Category | Condition"
                response = model.generate_content([prompt, img])
                result_text = response.text
                
                # حفظ في Google Sheets
                sheet = connect_to_sheets()
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ترتيب البيانات
                parts = [p.strip() for p in result_text.split("|")]
                row = [timestamp] + parts
                
                sheet.append_row(row)
                
                st.success(f"تم التحليل والحفظ بنجاح! ✅")
                st.write(f"النتيجة: {result_text}")
                
            except Exception as e:
                st.error(f"حدث خطأ: {str(e)}")
                if "404" in str(e):
                    st.warning("تلميح: يرجى تحديث مكتبة google-generativeai في ملف requirements.txt")
