import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import pandas as pd

# 1. إعداد الصفحة
st.set_page_config(page_title="E-Waste Smart Sorter", layout="centered", page_icon="♻️")
st.title("📸 نظام فرز المخلفات الإلكترونية الذكي")

# 2. جلب الإعدادات من Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    google_info = st.secrets["google_sheets"]
except Exception as e:
    st.error("⚠️ خطأ: لم يتم العثور على الإعدادات السرية (Secrets).")
    st.info("تأكد من إضافة GEMINI_API_KEY و google_sheets في إعدادات Streamlit Cloud")
    st.stop()

# 3. إعداد Google Sheets مع التخزين المؤقت
@st.cache_resource
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
        client = gspread.authorize(creds)
        sheet = client.open("E-Waste Database").sheet1
        
        # التحقق من وجود الرؤوس
        if not sheet.row_values(1):
            sheet.append_row(["التاريخ", "الاسم", "الفئة", "الحالة"])
        
        return sheet
    except gspread.SpreadsheetNotFound:
        st.error("❌ لم يتم العثور على ملف 'E-Waste Database'")
        st.info("تأكد من:\n- إنشاء ملف بهذا الاسم تماماً\n- مشاركته مع البريد الموجود في ملف JSON")
        return None
    except Exception as e:
        st.error(f"❌ فشل الاتصال بـ Google Sheets: {e}")
        return None

# 4. إعداد Gemini - الإصلاح الرئيسي هنا!
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # قائمة الموديلات المتاحة للتجربة بالترتيب
    MODELS_TO_TRY = [
        'gemini-1.5-pro',           # الأفضل والأكثر استقراراً
        'gemini-1.5-flash-8b',      # سريع وخفيف
        'gemini-pro-vision',        # النسخة القديمة الموثوقة
        'gemini-1.5-pro-latest',    # آخر إصدار
    ]
    
    model = None
    model_name = None
    
    # محاولة الاتصال بكل موديل حتى ينجح واحد
    for model_name in MODELS_TO_TRY:
        try:
            model = genai.GenerativeModel(model_name)
            # اختبار سريع
            test_response = model.generate_content("Hi")
            st.success(f"✅ تم الاتصال بـ Gemini بنجاح (الموديل: {model_name})")
            break
        except Exception as e:
            continue
    
    if model is None:
        st.error("❌ فشل الاتصال بجميع موديلات Gemini")
        st.warning("""
        **الحلول الممكنة:**
        1. تحقق من صحة GEMINI_API_KEY
        2. تأكد من تفعيل Gemini API في Google Cloud Console
        3. تحقق من الحصة المتاحة (Quota)
        """)
        st.stop()
        
except Exception as e:
    st.error(f"❌ خطأ في إعداد Gemini: {e}")
    st.stop()

# 5. واجهة التطبيق
st.markdown("""
<div style="background-color:#e8f4f8;padding:15px;border-radius:10px;margin-bottom:20px;border-right: 5px solid #1f77b4;">
    💡 <b>نصيحة:</b> التقط الصورة بكاميرا الهاتف أولاً، ثم ارفعها هنا لتجنب إغلاق التطبيق.
</div>
""", unsafe_allow_html=True)

img_file = st.file_uploader("📤 اختر صورة القطعة الإلكترونية", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة التي سيتم تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل وحفظ البيانات", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري التحليل باستخدام الذكاء الاصطناعي..."):
            try:
                # طلب التحليل من Gemini
                prompt = """Analyze this electronic component/waste carefully.

Respond ONLY with this exact format (no extra text):
Name | Category | Condition

Where:
- Name: Specific component name (e.g., "DDR2 RAM Module", "USB Cable")
- Category: Type (Circuit Board, Memory, Cable, Battery, Connector, etc.)
- Condition: Good/Fair/Poor/Damaged

Example: DDR2 RAM Module | Memory Component | Good"""
                
                response = model.generate_content([prompt, img])
                result = response.text.strip()
                
                # تنظيف النتيجة من أي نص إضافي
                if '\n' in result:
                    result = result.split('\n')[0]
                
                # 6. حفظ البيانات في Google Sheets
                sheet = connect_to_sheets()
                if sheet:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    parts = [p.strip() for p in result.split("|")]
                    
                    # ملء البيانات الناقصة
                    while len(parts) < 3:
                        parts.append("غير محدد")
                    
                    row_to_add = [timestamp] + parts[:3]
                    sheet.append_row(row_to_add)
                    
                    # عرض النتيجة بشكل جميل
                    st.success("✅ تم التحليل والحفظ بنجاح!")
                    
                    st.markdown("### 📊 نتيجة التحليل:")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("الاسم", parts[0], delta=None)
                    with col2:
                        st.metric("الفئة", parts[1], delta=None)
                    with col3:
                        # تحديد لون حسب الحالة
                        condition = parts[2].lower()
                        if 'good' in condition or 'جيد' in condition:
                            st.markdown(f"**الحالة**  \n🟢 {parts[2]}")
                        elif 'fair' in condition or 'متوسط' in condition:
                            st.markdown(f"**الحالة**  \n🟡 {parts[2]}")
                        else:
                            st.markdown(f"**الحالة**  \n🔴 {parts[2]}")
                    
                    # عرض في جدول أيضاً
                    st.markdown("---")
                    df_display = pd.DataFrame([parts[:3]], columns=["الاسم", "الفئة", "الحالة"])
                    st.dataframe(df_display, use_container_width=True)
                    
                else:
                    st.warning("⚠️ تم التحليل لكن فشل الحفظ في Google Sheets")
                    st.info(f"النتيجة: {result}")

            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ حدث خطأ: {error_msg}")
                
                # رسائل مساعدة حسب نوع الخطأ
                if "404" in error_msg:
                    st.warning("الموديل غير متاح. جرّب تحديث الكود لاستخدام موديل آخر.")
                elif "quota" in error_msg.lower():
                    st.warning("⚠️ تم تجاوز حد الاستخدام اليومي. حاول مرة أخرى غداً.")
                elif "api key" in error_msg.lower():
                    st.warning("⚠️ مشكلة في مفتاح API. تحقق من GEMINI_API_KEY في Secrets.")
                elif "permission" in error_msg.lower():
                    st.warning("⚠️ تحقق من صلاحيات Google Sheets API.")

# معلومات إضافية
with st.expander("ℹ️ معلومات ومساعدة"):
    st.markdown(f"""
    **الموديل المستخدم حالياً:** `{model_name if model_name else 'غير متصل'}`
    
    **كيفية الاستخدام:**
    1. التقط صورة واضحة للقطعة الإلكترونية
    2. ارفع الصورة باستخدام الزر أعلاه
    3. اضغط على "بدء التحليل"
    4. سيتم تحليل الصورة وحفظها تلقائياً
    
    **المتطلبات:**
    - مفتاح Gemini API صالح ومُفعّل
    - ملف Google Sheets باسم "E-Waste Database"
    - صلاحيات Service Account صحيحة
    
    **إذا واجهت مشكلة:**
    - تأكد من وضوح الصورة
    - جرّب صورة بإضاءة جيدة
    - تحقق من اتصال الإنترنت
    """)

# تذييل
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#666;">
    <p>🌍 <b>نظام فرز المخلفات الإلكترونية الذكي</b> | النسخة 2.1</p>
    <p style="font-size:0.9em;">Powered by Gemini AI & Streamlit | 2025</p>
</div>
""", unsafe_allow_html=True)
