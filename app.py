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
except KeyError as e:
    st.error(f"⚠️ خطأ: مفتاح '{e}' غير موجود في Secrets")
    st.info("تأكد من إضافة GEMINI_API_KEY و google_sheets في إعدادات Streamlit Cloud")
    st.stop()
except Exception as e:
    st.error(f"⚠️ خطأ في قراءة Secrets: {e}")
    st.stop()

# 3. إعداد Google Sheets مع التحقق الأفضل
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
        
        # إنشاء رؤوس الأعمدة إذا لم تكن موجودة
        if not sheet.row_values(1):
            sheet.append_row(["التاريخ", "الاسم", "الفئة", "الحالة"])
            st.info("✅ تم إنشاء رؤوس الأعمدة في Google Sheets")
        
        return sheet
    
    except gspread.SpreadsheetNotFound:
        st.error("❌ لم يتم العثور على 'E-Waste Database'")
        st.warning("""
        **تأكد من:**
        - إنشاء ملف Google Sheets بهذا الاسم بالضبط
        - مشاركته مع البريد الموجود في ملف JSON الخاص بـ Service Account
        """)
        return None
    
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال بـ Google Sheets: {e}")
        return None

# 4. إعداد Gemini - إصلاح دالة البحث
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_working_model():
    """البحث عن موديل Gemini متاح - بدون اختبار generate_content"""
    # ترتيب من الأكثر استقراراً للأقل
    test_models = [
        'gemini-1.5-pro',          # الأفضل والأكثر موثوقية
        'gemini-pro-vision',       # موديل قديم لكن مضمون
        'gemini-1.5-flash-8b',     # خفيف وسريع
        'gemini-1.5-pro-latest',   # آخر إصدار
        'gemini-1.5-flash',        # قد لا يعمل في بعض المناطق
    ]
    
    for model_name in test_models:
        try:
            model = genai.GenerativeModel(model_name)
            # لا نختبر generate_content هنا لأنه قد يفشل بدون صورة
            return model, model_name
        except Exception:
            continue
    
    return None, None

model, working_model_name = get_working_model()

if not model:
    st.error("❌ جميع موديلات Gemini غير متاحة حالياً")
    st.warning("""
    **الحلول الممكنة:**
    1. تحقق من صحة GEMINI_API_KEY
    2. تأكد من تفعيل Gemini API في Google AI Studio
    3. تحقق من الحصة المتاحة (Quota)
    4. جرّب إنشاء API Key جديد
    """)
    st.stop()
else:
    st.success(f"✅ متصل بنجاح | الموديل: **{working_model_name}**")

# 5. واجهة التطبيق
st.markdown("""
<div style="background-color:#e3f2fd;padding:12px;border-radius:8px;margin-bottom:15px;border-right:4px solid #2196f3;">
    💡 <b>نصيحة:</b> التقط الصورة بكاميرا الهاتف أولاً، ثم ارفعها هنا لتجنب إغلاق التطبيق.
</div>
""", unsafe_allow_html=True)

img_file = st.file_uploader(
    "📤 اختر صورة القطعة الإلكترونية",
    type=['jpg', 'jpeg', 'png'],
    help="صيغ مدعومة: JPG, JPEG, PNG"
)

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة التي سيتم تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل وحفظ البيانات", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري التحليل باستخدام الذكاء الاصطناعي..."):
            try:
                # Prompt محسّن مع أمثلة
                prompt = """Analyze this electronic component/waste carefully.

Respond EXACTLY in this format (no extra text):
Name | Category | Condition

Examples:
- DDR2 RAM Module | Memory Component | Good
- USB Type-A Cable | Cable | Fair
- Li-ion Battery 18650 | Power Component | Damaged
- PCB Board | Circuit Board | Poor

Rules:
- Name: Be specific (include model/type if visible)
- Category: Circuit Board, Memory, Cable, Battery, Connector, Display, Capacitor, Resistor, etc.
- Condition: Good (working), Fair (minor damage), Poor (major damage), Damaged (not working)"""

                response = model.generate_content([prompt, img])
                result = response.text.strip()
                
                # تنظيف النتيجة من أي نص إضافي
                if '\n' in result:
                    result = result.split('\n')[0]
                
                # إزالة أي markdown formatting
                result = result.replace('*', '').replace('`', '')
                
                # حفظ في Google Sheets
                sheet = connect_to_sheets()
                if sheet:
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    parts = [p.strip() for p in result.split("|")]
                    
                    # ملء البيانات الناقصة
                    while len(parts) < 3:
                        parts.append("غير محدد")
                    
                    row_to_add = [timestamp] + parts[:3]
                    sheet.append_row(row_to_add)
                    
                    st.success("✅ تم التحليل والحفظ في Google Sheets بنجاح!")
                    
                    # عرض النتائج بشكل جميل
                    st.markdown("### 📊 نتيجة التحليل:")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("الاسم", parts[0])
                    with col2:
                        st.metric("الفئة", parts[1])
                    with col3:
                        # تحديد أيقونة حسب الحالة
                        condition_lower = parts[2].lower()
                        if 'good' in condition_lower or 'جيد' in condition_lower:
                            icon = "🟢"
                        elif 'fair' in condition_lower or 'متوسط' in condition_lower:
                            icon = "🟡"
                        else:
                            icon = "🔴"
                        st.metric("الحالة", f"{icon} {parts[2]}")
                    
                    # عرض في جدول منسق
                    st.markdown("---")
                    df = pd.DataFrame([parts[:3]], columns=["الاسم", "الفئة", "الحالة"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                else:
                    st.warning("⚠️ تم التحليل بنجاح لكن فشل الحفظ في Google Sheets")
                    st.info(f"النتيجة: **{result}**")
            
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ حدث خطأ أثناء التحليل: {error_msg}")
                
                # رسائل مساعدة حسب نوع الخطأ
                if "quota" in error_msg.lower() or "resource_exhausted" in error_msg.lower():
                    st.warning("⚠️ تم تجاوز حد الاستخدام اليومي. حاول مرة أخرى غداً أو استخدم API Key آخر.")
                elif "permission" in error_msg.lower():
                    st.warning("⚠️ مشكلة في صلاحيات Google Sheets. تأكد من مشاركة الملف مع Service Account.")
                elif "rate limit" in error_msg.lower():
                    st.warning("⚠️ طلبات كثيرة جداً. انتظر دقيقة وحاول مرة أخرى.")
                elif "api key" in error_msg.lower():
                    st.warning("⚠️ مشكلة في مفتاح API. تحقق من GEMINI_API_KEY.")
                else:
                    st.info("💡 جرّب تحديث الصفحة أو استخدام صورة أخرى.")

# معلومات إضافية
with st.expander("ℹ️ معلومات ومساعدة"):
    st.markdown(f"""
    **الموديل المستخدم:** `{working_model_name}`
    
    **كيفية الاستخدام:**
    1. التقط صورة واضحة للقطعة الإلكترونية
    2. ارفع الصورة من معرض الصور
    3. اضغط على زر "بدء التحليل"
    4. سيتم التحليل والحفظ تلقائياً
    
    **نصائح للحصول على أفضل نتائج:**
    - استخدم إضاءة جيدة
    - تأكد من وضوح الصورة
    - صوّر القطعة من زاوية واضحة
    - تجنب الظلال القوية
    
    **المتطلبات:**
    - مفتاح Gemini API صالح
    - ملف "E-Waste Database" في Google Sheets
    - صلاحيات Service Account صحيحة
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#666;padding:10px;">
    <p style="margin:5px 0;">🌍 <b>نظام فرز المخلفات الإلكترونية الذكي</b></p>
    <p style="margin:5px 0;font-size:0.9em;">v2.3 | Powered by Gemini AI & Streamlit</p>
    <p style="margin:5px 0;font-size:0.85em;">© 2025 - بيئة نظيفة، مستقبل أفضل 🌱</p>
</div>
""", unsafe_allow_html=True)
