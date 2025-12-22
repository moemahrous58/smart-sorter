import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# إعداد الصفحة
st.set_page_config(page_title="E-Waste Smart Sorter", layout="centered")
st.title("📸 نظام فرز المخلفات الإلكترونية")

# جلب الإعدادات من Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    google_info = st.secrets["google_sheets"]
except Exception as e:
    st.error("⚠️ تأكد من ضبط الإعدادات السرية (Secrets) في Streamlit Cloud")
    st.stop()

# إعداد Google Sheets (تم تثبيت اسم الملف)
@st.cache_resource
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
        client = gspread.authorize(creds)
        # فتح الملف بالاسم الذي حددته
        sheet = client.open("E-Waste Database").sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ فشل الاتصال بجدول البيانات: {e}")
        return None

# إعداد Gemini
genai.configure(api_key=GEMINI_API_KEY)
# قمنا بتغيير الموديل إلى الإصدار الأكثر استقراراً لتجنب خطأ 404
model = genai.GenerativeModel('gemini-1.5-flash')

# واجهة التطبيق (تم تغييرها لضمان استقرار الموبايل)
st.info("💡 نصيحة: إذا انغلق المتصفح، حاول التقاط الصورة بكاميرا الهاتف أولاً ثم اخترها من 'المعرض'.")
img_file = st.file_uploader("التقط صورة للقطعة أو اخترها من المعرض", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة المختارة", use_container_width=True)
    
    if st.button("🚀 بدء التحليل والحفظ", type="primary"):
        with st.spinner("جاري معالجة الصورة..."):
            try:
                # التحليل
                prompt = "Identify this electronic waste. Format: Name | Category | Condition"
                response = model.generate_content([prompt, img])
                result = response.text.strip()
                
                # الحفظ في الشيت
                sheet = connect_to_sheets()
                if sheet:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    parts = [p.strip() for p in result.split("|")]
                    # التأكد من ملء البيانات
                    while len(parts) < 3: parts.append("N/A")
                    
                    sheet.append_row([timestamp] + parts[:3])
                    
                    st.success("✅ تم التحليل وحفظ البيانات في 'E-Waste Database'")
                    st.markdown(f"**النتيجة المستخرجة:** `{result}`")
            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {e}")
