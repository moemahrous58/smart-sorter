import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import time

# 1. إعداد الصفحة
st.set_page_config(page_title="Smart Sorter v5.2", layout="centered", page_icon="♻️")

# --- 2. دالة الحفظ في Google Sheets ---
def save_to_sheets(data):
    try:
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(google_info)
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("E-Waste Database").sheet1
        
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            data.get('model'), 
            data.get('type'), 
            data.get('gold_mg'), 
            data.get('value_usd')
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"❌ خطأ في حفظ البيانات (Sheets): {e}")
        return False

# --- 3. محرك التبادل المحسّن مع تشخيص تفصيلي ---
def get_working_ai_engine():
    keys = [
        "AIzaSyBshLLsQMeRq2ZKmqg92Ym6UcDrZwhz_ZI",  # المفتاح الجديد
        "AIzaSyCPl8pCcUQxK_q2f7B80jluNTeLsexnjhE",
        "AIzaSyA-gnMmgKg_0k4BpnvJ7K252Y5lRnfY7Sk"
    ]
    
    # موديلات متعددة للتجربة
    model_names = [
        'gemini-1.5-flash',
        'gemini-1.5-flash-latest',
        'gemini-pro-vision',
        'gemini-1.5-pro'
    ]
    
    errors_log = ["بدء فحص المفاتيح..."]
    
    for i, key in enumerate(keys):
        errors_log.append(f"🔍 فحص المفتاح {i+1}...")
        
        if not key or len(key) < 30:
            errors_log.append(f"🔴 المفتاح {i+1}: غير صالح أو فارغ (طول: {len(key) if key else 0})")
            continue
        
        errors_log.append(f"   طول المفتاح: {len(key)} حرف ✓")
        
        for m_name in model_names:
            errors_log.append(f"   جاري تجربة الموديل: {m_name}...")
            try:
                # إعداد المفتاح
                genai.configure(api_key=key)
                errors_log.append(f"      ✓ تم إعداد المفتاح")
                
                # إنشاء الموديل
                model = genai.GenerativeModel(m_name)
                errors_log.append(f"      ✓ تم إنشاء كائن الموديل")
                
                # اختبار بسيط جدًا
                response = model.generate_content(
                    "Say hi",
                    generation_config={
                        "max_output_tokens": 10,
                        "temperature": 0.1
                    }
                )
                
                # إذا وصلنا هنا، فالاتصال نجح!
                errors_log.append(f"      ✅✅✅ نجح الاتصال! الرد: {response.text[:30]}")
                return model, m_name, i+1, errors_log
                
            except Exception as e:
                error_msg = str(e)
                full_error = f"      ❌ فشل: {error_msg}"
                errors_log.append(full_error)
                
                # تحليل نوع الخطأ
                if "429" in error_msg or "quota" in error_msg.lower():
                    errors_log.append(f"      📊 التشخيص: تجاوز الحد المسموح (Quota)")
                elif "403" in error_msg or "permission" in error_msg.lower() or "disabled" in error_msg.lower():
                    errors_log.append(f"      🔒 التشخيص: API غير مفعّل أو الصلاحيات غير كافية")
                elif "404" in error_msg:
                    errors_log.append(f"      🔍 التشخيص: الموديل غير موجود أو غير متاح")
                elif "invalid" in error_msg.lower() or "401" in error_msg:
                    errors_log.append(f"      🔑 التشخيص: المفتاح غير صحيح")
                elif "DEADLINE_EXCEEDED" in error_msg or "timeout" in error_msg.lower():
                    errors_log.append(f"      ⏱️ التشخيص: انتهت مهلة الاتصال")
                else:
                    errors_log.append(f"      ❓ التشخيص: خطأ غير معروف")
                
                time.sleep(0.5)
                continue
    
    errors_log.append("❌ انتهى الفحص - فشلت جميع المحاولات")
    return None, None, None, errors_log

# --- 4. واجهة التطبيق الرئيسية ---
st.title("♻️ نظام الفرز الإلكتروني الذكي (v5.2)")
st.markdown("**نسخة محسّنة مع تشخيص تفصيلي**")
st.markdown("---")

# إدارة الحالة
if 'active_engine' not in st.session_state:
    with st.spinner("🔄 جاري فحص الحسابات المتاحة..."):
        model, m_name, account_num, logs = get_working_ai_engine()
        st.session_state.active_engine = model
        st.session_state.engine_name = m_name
        st.session_state.account_id = account_num
        st.session_state.connection_logs = logs

# عرض سجل الاتصال
with st.expander("📋 عرض سجل محاولات الاتصال (للتشخيص)", expanded=True):
    if 'connection_logs' in st.session_state and st.session_state.connection_logs:
        for log in st.session_state.connection_logs:
            if "✅" in log:
                st.success(log)
            elif "🔴" in log or "❌" in log:
                st.error(log)
            elif "⚠️" in log or "📊" in log or "🔒" in log or "🔍" in log or "🔑" in log or "⏱️" in log or "❓" in log:
                st.warning(log)
            else:
                st.info(log)
    else:
        st.warning("⚠️ لا توجد سجلات - هذا يعني أن الفحص لم يتم بشكل صحيح")

# عرض حالة الاتصال
if st.session_state.active_engine:
    st.success(f"✅ متصل بنجاح | الحساب النشط: ({st.session_state.account_id}) | الموديل: {st.session_state.engine_name}")
else:
    st.error("❌ فشل الاتصال بجميع الحسابات والموديلات المتاحة")
    
    st.markdown("### 🔍 خطوات الحل المقترحة:")
    st.markdown("""
    1. **تفعيل Gemini API:**
       - افتح [Google AI Studio](https://aistudio.google.com/app/apikey)
       - تأكد من تفعيل الـ API من القائمة الجانبية
    
    2. **التحقق من المفتاح:**
       - انسخ المفتاح من AI Studio مباشرة
       - تأكد من عدم وجود مسافات زائدة
    
    3. **تفعيل الموديل:**
       - بعض الموديلات تحتاج تفعيل يدوي
       - جرب التشغيل التجريبي في AI Studio أولاً
    
    4. **التحقق من المنطقة:**
       - بعض المناطق قد لا تدعم Gemini API
       - جرب استخدام VPN إذا لزم الأمر
    """)
    
    if st.button("🔄 إعادة محاولة الاتصال", type="primary"):
        st.session_state.clear()
        st.rerun()
    
    st.stop()

# --- 5. منطقة العمل ---
st.markdown("### 📤 رفع الصورة للتحليل")
img_file = st.file_uploader("اختر صورة المعالج أو الرامة", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة الجاري تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل والحفظ التلقائي", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري تحليل الصورة..."):
            try:
                prompt = """Analyze this electronic component carefully. 
                Identify: model name, type (CPU/RAM/GPU), estimated gold content in mg, and scrap value in USD.
                Return ONLY a valid JSON object with this exact structure:
                {"model": "component_name", "type": "CPU or RAM or GPU", "gold_mg": number, "value_usd": number}
                Do not include any other text, just the JSON."""
                
                response = st.session_state.active_engine.generate_content(
                    [prompt, img],
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 500
                    }
                )
                
                # تنظيف النص
                res_text = response.text.strip()
                res_text = res_text.replace('```json', '').replace('```', '').strip()
                
                # محاولة استخراج JSON
                if '{' in res_text and '}' in res_text:
                    start = res_text.index('{')
                    end = res_text.rindex('}') + 1
                    res_text = res_text[start:end]
                
                data = json.loads(res_text)
                
                # عرض النتائج
                st.subheader("📊 نتائج الفحص:")
                col1, col2 = st.columns(2)
                col1.metric("الموديل", data.get('model', 'غير معروف'))
                col1.metric("النوع", data.get('type', 'غير معروف'))
                col2.metric("كمية الذهب", f"{data.get('gold_mg', 0)} mg")
                col2.metric("القيمة ($)", f"${data.get('value_usd', 0)}")
                
                # الحفظ
                if save_to_sheets(data):
                    st.success("✅ تم الحفظ في قاعدة البيانات بنجاح!")
                    st.balloons()
                    
            except json.JSONDecodeError as je:
                st.error(f"⚠️ خطأ في تحليل الاستجابة: {je}")
                st.code(res_text, language="text")
            except Exception as e:
                st.error(f"❌ خطأ أثناء التحليل: {e}")

# تذييل
st.markdown("---")
st.caption("نظام فرز الخردة الإلكترونية v5.2 | تشخيص محسّن | مدعوم بـ Gemini")
