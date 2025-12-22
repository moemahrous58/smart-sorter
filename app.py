import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd

# 1. إعداد الصفحة وتنسيقها
st.set_page_config(page_title="E-Waste Smart Sorter", layout="centered", page_icon="♻️")
st.title("📸 نظام فرز المخلفات الإلكترونية الذكي")

# 2. جلب الإعدادات من Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    google_info = st.secrets["google_sheets"]
except Exception as e:
    st.error("⚠️ خطأ: لم يتم العثور على الإعدادات السرية (Secrets). تأكد من إضافتها في Streamlit Cloud.")
    st.stop()

# 3. إعداد Google Sheets مع التخزين المؤقت (Caching)
@st.cache_resource
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
        client = gspread.authorize(creds)
        # فتح ملف "E-Waste Database"
        return client.open("E-Waste Database").sheet1
    except Exception as e:
        st.error(f"❌ فشل الاتصال بـ Google Sheets: {e}")
        return None

# 4. إعداد Gemini (التعديل المطلوب لضمان التوافق)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 5. واجهة التطبيق - حل مشكلة إغلاق الموبايل
st.markdown("""
<div style="background-color:#f0f2f6;padding:15px;border-radius:10px;margin-bottom:20px;border-right: 5px solid #ff4b4b;">
    💡 <b>ملاحظة هامة:</b> لتجنب إغلاق المتصفح، التقط الصورة بكاميرا الهاتف أولاً، ثم ارفعها هنا.
</div>
""", unsafe_allow_html=True)

img_file = st.file_uploader("اختر صورة للقطعة من الاستوديو", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة التي سيتم تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل وحفظ البيانات", type="primary"):
        with st.spinner("جاري التواصل مع الذكاء الاصطناعي..."):
            try:
                # طلب التحليل من Gemini
                prompt = """Analyze this electronic component. 
                Return exactly in this format: Name | Category | Condition"""
                
                response = model.generate_content([prompt, img])
                result = response.text.strip()
                
                # 6. توزيع البيانات وحفظها في Google Sheets
                sheet = connect_to_sheets()
                if sheet:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    parts = [p.strip() for p in result.split("|")]
                    
                    # ملء البيانات الناقصة لضمان عدم حدوث خطأ في الأعمدة
                    while len(parts) < 3: parts.append("غير محدد")
                    
                    row_to_add = [timestamp] + parts[:3]
                    sheet.append_row(row_to_add)
                    
                    st.success("✅ تم التحليل بنجاح وتم تسجيل البيانات!")
                    
                    # عرض البيانات المضافة في جدول
                    df_display = pd.DataFrame([parts[:3]], columns=["الاسم", "الفئة", "الحالة"])
                    st.table(df_display)

            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
                if "404" in str(e):
                    st.info("تلميح: تأكد من تحديث ملف requirements.txt إلى google-generativeai==0.8.3")

# تذييل الصفحة
st.markdown("---")
st.caption("نظام فرز المخلفات الإلكترونية v2.0 | 2025")
