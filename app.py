import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# 1. إعداد الصفحة
st.set_page_config(page_title="نظام الفرز الذكي", layout="centered")
st.title("📸 نظام فرز المخلفات الإلكترونية")

# 2. جلب الإعدادات من Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    google_info = st.secrets["google_sheets"]
except Exception as e:
    st.error("خطأ في قراءة الإعدادات السرية (Secrets). تأكد من إضافتها في Streamlit.")
    st.stop()

# 3. إعداد Google Sheets
def connect_to_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
    client = gspread.authorize(creds)
    # اسم الملف الذي حددته
    return client.open("E-Waste Database").sheet1

# 4. إعداد Gemini (تم تحديث اسم النموذج وطريقة الاستدعاء لحل خطأ 404)
genai.configure(api_key=GEMINI_API_KEY)
# استخدمنا gemini-1.5-flash كنموذج افتراضي مع معالجة الأخطاء
model = genai.GenerativeModel('gemini-1.5-flash')

# 5. واجهة التطبيق
img_file = st.camera_input("التقط صورة للقطعة الإلكترونية")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة التي تم التقاطها", use_container_width=True)
    
    if st.button("بدء التحليل بالذكاء الاصطناعي 🔍"):
        with st.spinner("جاري التحليل..."):
            try:
                # طلب التحليل من Gemini
                prompt = "Identify this electronic component. Return only: Name, Category, Condition (New/Used). Format: Name | Category | Condition"
                response = model.generate_content([prompt, img])
                result = response.text
                
                st.success("تم التحليل بنجاح!")
                st.write(f"النتيجة: {result}")
                
                # 6. حفظ البيانات في Google Sheets
                sheet = connect_to_sheets()
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # تقسيم النتيجة وحفظها
                data_row = result.split("|")
                row_to_add = [now] + [item.strip() for item in data_row]
                
                sheet.append_row(row_to_add)
                st.info(f"تم تسجيل البيانات في ملف 'E-Waste Database' بنجاح ✅")
                
            except Exception as e:
                st.error(f"حدث خطأ: {str(e)}")
                st.info("نصيحة: تأكد من تحديث مكتبة google-generativeai في ملف requirements.txt")
