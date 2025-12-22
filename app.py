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
    st.error("⚠️ خطأ في الإعدادات السرية (Secrets).")
    st.stop()

# 3. إعداد Google Sheets
@st.cache_resource
def connect_to_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(google_info), scope)
        client = gspread.authorize(creds)
        sheet = client.open("E-Waste Database").sheet1
        
        # إنشاء رؤوس إذا لم تكن موجودة
        if not sheet.row_values(1):
            sheet.append_row(["التاريخ", "الاسم", "الفئة", "الحالة"])
        
        return sheet
    except Exception as e:
        st.error(f"❌ فشل الاتصال بـ Google Sheets: {e}")
        return None

# 4. إعداد Gemini - للنسخة المجانية فقط!
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_working_model():
    """البحث عن موديل متاح - مخصص للنسخة المجانية"""
    # الموديلات المتاحة في النسخة المجانية بالترتيب
    free_models = [
        'gemini-pro-vision',    # ✅ الأفضل للنسخة المجانية
        'gemini-pro',           # ✅ نص فقط (احتياطي)
    ]
    
    for model_name in free_models:
        try:
            model = genai.GenerativeModel(model_name)
            return model, model_name
        except Exception:
            continue
    
    return None, None

model, working_model_name = get_working_model()

if not model:
    st.error("❌ فشل الاتصال بـ Gemini")
    st.warning("""
    **تحقق من:**
    1. صحة GEMINI_API_KEY في Secrets
    2. تفعيل Gemini API من Google AI Studio
    3. الحصة المتاحة (Quota) لم تنفد
    
    **رابط إنشاء API Key:**
    https://makersuite.google.com/app/apikey
    """)
    st.stop()
else:
    st.success(f"✅ متصل بنجاح | الموديل: **{working_model_name}**")
    
    # تنبيه إذا كان الموديل المستخدم نص فقط
    if working_model_name == 'gemini-pro':
        st.warning("⚠️ الموديل الحالي لا يدعم الصور. سيتم استخدام وصف نصي فقط.")

# 5. واجهة التطبيق
st.markdown("""
<div style="background-color:#e3f2fd;padding:12px;border-radius:8px;margin-bottom:15px;border-right:4px solid #2196f3;">
    💡 <b>نصيحة:</b> التقط الصورة بكاميرا الهاتف أولاً، ثم ارفعها هنا.
</div>
""", unsafe_allow_html=True)

img_file = st.file_uploader(
    "📤 اختر صورة القطعة الإلكترونية",
    type=['jpg', 'jpeg', 'png']
)

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة التي سيتم تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل وحفظ البيانات", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري التحليل..."):
            try:
                # Prompt محسّن للنسخة المجانية
                prompt = """Analyze this electronic component/waste image carefully.

You must respond EXACTLY in this format (no extra text):
Name | Category | Condition

Examples of correct responses:
- DDR2 RAM Module | Memory Component | Good
- USB Type-A Cable | Cable | Fair
- Li-ion Battery | Power Component | Damaged
- Laptop Motherboard | Circuit Board | Poor

Guidelines:
- Name: Specific component name (be precise based on what you see)
- Category: Choose from: Circuit Board, Memory, Cable, Battery, Connector, Display, Capacitor, Processor, Hard Drive, Power Supply
- Condition: Choose from: Good (fully working), Fair (minor wear), Poor (damaged but fixable), Damaged (not working)

Be specific and accurate based on the image."""

                # محاولة التحليل
                if working_model_name == 'gemini-pro-vision':
                    # الموديل يدعم الصور
                    response = model.generate_content([prompt, img])
                else:
                    # الموديل نص فقط - نطلب من المستخدم الوصف
                    st.warning("⚠️ الموديل الحالي لا يدعم تحليل الصور مباشرة.")
                    user_description = st.text_input(
                        "صف القطعة الإلكترونية التي في الصورة:",
                        placeholder="مثال: ذاكرة RAM من نوع DDR2"
                    )
                    if not user_description:
                        st.info("⬆️ يرجى إدخال وصف للقطعة أعلاه")
                        st.stop()
                    
                    full_prompt = f"{prompt}\n\nUser description: {user_description}"
                    response = model.generate_content(full_prompt)
                
                result = response.text.strip()
                
                # تنظيف النتيجة
                if '\n' in result:
                    result = result.split('\n')[0]
                result = result.replace('*', '').replace('`', '').strip()
                
                # التحقق من الصيغة
                if '|' not in result:
                    st.error("❌ فشل التحليل: الصيغة غير صحيحة")
                    st.info(f"النتيجة: {result}")
                    st.stop()
                
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
                    
                    st.success("✅ تم التحليل والحفظ بنجاح!")
                    
                    # عرض النتائج
                    st.markdown("### 📊 نتيجة التحليل:")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("الاسم", parts[0])
                    with col2:
                        st.metric("الفئة", parts[1])
                    with col3:
                        condition_lower = parts[2].lower()
                        if 'good' in condition_lower:
                            icon = "🟢"
                        elif 'fair' in condition_lower:
                            icon = "🟡"
                        else:
                            icon = "🔴"
                        st.metric("الحالة", f"{icon} {parts[2]}")
                    
                    # جدول
                    st.markdown("---")
                    df = pd.DataFrame([parts[:3]], columns=["الاسم", "الفئة", "الحالة"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                else:
                    st.warning("⚠️ تم التحليل لكن فشل الحفظ في Google Sheets")
                    st.info(f"النتيجة: **{result}**")
            
            except Exception as e:
                error_msg = str(e)
                st.error(f"❌ حدث خطأ: {error_msg}")
                
                # رسائل مساعدة
                if "404" in error_msg or "not found" in error_msg.lower():
                    st.warning("""
                    ⚠️ **الموديل غير متاح**
                    
                    هذا يحدث عادة مع النسخة المجانية من Gemini API.
                    
                    **الحلول:**
                    1. تأكد أنك تستخدم `gemini-pro-vision` (مضمن في الكود)
                    2. جرّب إنشاء API Key جديد من: https://makersuite.google.com/app/apikey
                    3. إذا استمرت المشكلة، قد تحتاج للترقية للنسخة المدفوعة
                    """)
                elif "quota" in error_msg.lower():
                    st.warning("⚠️ تم تجاوز الحد اليومي. حاول غداً أو استخدم API Key آخر.")
                elif "billing" in error_msg.lower():
                    st.warning("⚠️ تحتاج لتفعيل الفوترة (Billing) في Google Cloud Console")
                else:
                    st.info("💡 جرّب تحديث الصفحة أو استخدم صورة أخرى")

# معلومات
with st.expander("ℹ️ معلومات النسخة المجانية"):
    st.markdown(f"""
    **الموديل المستخدم:** `{working_model_name}`
    
    **حدود النسخة المجانية:**
    - ✅ 60 طلب في الدقيقة
    - ✅ 1,500 طلب في اليوم
    - ✅ مجاني تماماً
    
    **للحصول على أداء أفضل:**
    - قم بالترقية للنسخة المدفوعة في Google Cloud Console
    - استخدم موديلات 1.5 الأحدث (gemini-1.5-pro, gemini-1.5-flash)
    
    **رابط إنشاء API Key:**
    https://makersuite.google.com/app/apikey
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#666;padding:10px;">
    <p style="margin:5px 0;">🌍 <b>نظام فرز المخلفات الإلكترونية</b></p>
    <p style="margin:5px 0;font-size:0.9em;">v2.3 Free Edition | Powered by Gemini AI</p>
</div>
""", unsafe_allow_html=True)
