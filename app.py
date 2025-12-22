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
except KeyError as e:
    st.error(f"⚠️ خطأ في قراءة Secrets: {e}")
    st.info("تأكد من إضافة GEMINI_API_KEY و google_sheets في إعدادات Streamlit Cloud")
    st.stop()
except Exception as e:
    st.error(f"خطأ غير متوقع: {e}")
    st.stop()

# إعداد Google Sheets
@st.cache_resource
def connect_to_sheets():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            dict(google_info), scope
        )
        client = gspread.authorize(creds)
        sheet = client.open("E-Waste Database").sheet1
        
        # التحقق من وجود رؤوس الأعمدة
        headers = sheet.row_values(1)
        if not headers:
            sheet.append_row(["التاريخ", "الاسم", "الفئة", "الحالة"])
        
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("❌ لم يتم العثور على ملف 'E-Waste Database'")
        st.info("تأكد من مشاركة الملف مع البريد الإلكتروني في ملف JSON")
        return None
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ Google Sheets: {e}")
        return None

# إعداد Gemini مع معالجة الأخطاء
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # استخدام الموديل الصحيح المتوفر
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    st.success("✅ تم الاتصال بـ Gemini AI بنجاح")
except Exception as e:
    st.error(f"خطأ في إعداد Gemini: {e}")
    st.info("جرّب استخدام 'gemini-pro-vision' أو 'gemini-1.5-pro' بدلاً من ذلك")
    st.stop()

# واجهة التطبيق
st.markdown("### 📷 التقط صورة للقطعة الإلكترونية")
img_file = st.camera_input("اضغط لالتقاط الصورة")

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="الصورة الملتقطة", use_container_width=True)
    
    if st.button("🔍 بدء التحليل بالذكاء الاصطناعي", type="primary"):
        with st.spinner("⏳ جاري التحليل وحفظ البيانات..."):
            try:
                # طلب التحليل مع prompt محسّن
                prompt = """Analyze this electronic component/waste carefully.
Provide ONLY the following information separated by | (pipe symbol):
Name | Category | Condition

Example format: "RAM Module | Memory Component | Good"

Rules:
- Name: Specific component name
- Category: Type (Circuit Board, Cable, Battery, etc.)
- Condition: Good/Fair/Poor/Damaged"""

                response = model.generate_content([prompt, img])
                result_text = response.text.strip()
                
                # عرض النتيجة
                st.success("✅ تم التحليل بنجاح!")
                st.markdown(f"**النتيجة:** `{result_text}`")
                
                # حفظ في Google Sheets
                sheet = connect_to_sheets()
                if sheet:
                    try:
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # تقسيم النتيجة
                        parts = [p.strip() for p in result_text.split("|")]
                        
                        # التأكد من وجود 3 أجزاء على الأقل
                        while len(parts) < 3:
                            parts.append("غير محدد")
                        
                        row = [timestamp] + parts[:3]
                        sheet.append_row(row)
                        
                        st.success("💾 تم حفظ البيانات في Google Sheets!")
                        
                        # عرض ملخص
                        st.markdown("---")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("الاسم", parts[0])
                        with col2:
                            st.metric("الفئة", parts[1])
                        with col3:
                            st.metric("الحالة", parts[2])
                            
                    except Exception as e:
                        st.error(f"خطأ في حفظ البيانات: {e}")
                        st.warning("تم التحليل بنجاح لكن فشل الحفظ في Google Sheets")
                
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ حدث خطأ: {error_msg}")
                
                # معالجة أخطاء محددة
                if "404" in error_msg or "not found" in error_msg.lower():
                    st.warning("""
                    **حل المشكلة:**
                    1. جرّب تغيير الموديل في الكود إلى:
                       - `gemini-pro-vision`
                       - `gemini-1.5-pro-latest`
                    2. تأكد من تحديث `google-generativeai` إلى آخر إصدار
                    """)
                elif "quota" in error_msg.lower():
                    st.warning("تم تجاوز حد الاستخدام اليومي لـ API")
                elif "api key" in error_msg.lower():
                    st.warning("تحقق من صحة GEMINI_API_KEY في Secrets")

# معلومات إضافية
with st.expander("ℹ️ معلومات النظام"):
    st.markdown("""
    **كيفية الاستخدام:**
    1. التقط صورة واضحة للقطعة الإلكترونية
    2. اضغط على زر "بدء التحليل"
    3. سيتم تحليل الصورة وحفظ البيانات تلقائياً
    
    **المتطلبات:**
    - مفتاح Gemini API صالح
    - ملف Google Sheets باسم "E-Waste Database"
    - بيانات اعتماد Google Service Account
    """)

# Footer
st.markdown("---")
st.markdown("🌍 **نظام ذكي لإدارة المخلفات الإلكترونية** | Powered by Gemini AI")
