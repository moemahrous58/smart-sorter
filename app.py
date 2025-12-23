import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json
import time

# 1. إعداد الصفحة
st.set_page_config(page_title="Smart Sorter v5.3", layout="centered", page_icon="♻️")

# --- 2. دالة الحفظ في Google Sheets (حل نهائي لمشكلة Base64) ---
def save_to_sheets(data):
    try:
        # قراءة الاعتمادات من Secrets
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # تحويل إلى قاموس عادي وتنظيف المفتاح
        private_key = str(google_info["private_key"])
        
        # إزالة المسافات والأحرف الزائدة
        private_key = private_key.strip()
        
        # التأكد من أن المفتاح في الشكل الصحيح
        if "\\n" in private_key:
            private_key = private_key.replace("\\n", "\n")
        
        creds_dict = {
            "type": str(google_info["type"]),
            "project_id": str(google_info["project_id"]),
            "private_key_id": str(google_info["private_key_id"]),
            "private_key": private_key,
            "client_email": str(google_info["client_email"]),
            "client_id": str(google_info["client_id"]),
            "auth_uri": str(google_info["auth_uri"]),
            "token_uri": str(google_info["token_uri"]),
            "auth_provider_x509_cert_url": str(google_info["auth_provider_x509_cert_url"]),
            "client_x509_cert_url": str(google_info["client_x509_cert_url"])
        }
        
        if "universe_domain" in google_info:
            creds_dict["universe_domain"] = str(google_info["universe_domain"])
        
        # إنشاء الاعتمادات
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # فتح الملف
        sheet = client.open("E-Waste Database").sheet1
        
        # إعداد البيانات للحفظ
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            str(data.get('model', 'Unknown')),
            str(data.get('type', 'Unknown')),
            float(data.get('gold_mg', 0)),
            float(data.get('value_usd', 0))
        ]
        
        # الحفظ
        sheet.append_row(row)
        return True
        
    except Exception as e:
        error_msg = str(e)
        st.error(f"❌ خطأ في حفظ البيانات: {error_msg}")
        
        # عرض تفاصيل المفتاح للتشخيص
        if "base64" in error_msg.lower():
            st.warning("💡 مشكلة في تشفير المفتاح الخاص")
            
            try:
                pk = str(google_info["private_key"])
                st.info(f"طول المفتاح: {len(pk)} حرف")
                st.info(f"يبدأ بـ: {pk[:20]}...")
                st.info(f"يحتوي على \\n: {'نعم' if '\\n' in pk else 'لا'}")
                st.info(f"يحتوي على فواصل أسطر: {'نعم' if chr(10) in pk else 'لا'}")
            except:
                pass
            
            st.markdown("""
            **حلول مقترحة:**
            1. أعد إنشاء Service Account جديد وانسخ المفتاح مرة أخرى
            2. تأكد من نسخ المفتاح كاملاً من JSON
            3. استخدم علامات اقتباس عادية في secrets.toml
            """)
                
        elif "permission" in error_msg.lower() or "403" in error_msg:
            st.warning(f"💡 شارك الملف مع: `{google_info['client_email']}`")
            
        elif "not found" in error_msg.lower() or "404" in error_msg:
            st.warning("💡 تأكد من وجود ملف اسمه: **E-Waste Database**")
        
        return False

# --- 3. محرك التبادل المحسّن مع تشخيص تفصيلي ---
def get_working_ai_engine():
    keys = [
        "AIzaSyBshLLsQMeRq2ZKmqg92Ym6UcDrZwhz_ZI",
        "AIzaSyCPl8pCcUQxK_q2f7B80jluNTeLsexnjhE",
        "AIzaSyA-gnMmgKg_0k4BpnvJ7K252Y5lRnfY7Sk"
    ]
    
    model_names = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro-latest',
        'gemini-pro',
        'gemini-1.5-flash',
        'gemini-1.5-pro'
    ]
    
    errors_log = ["بدء فحص المفاتيح..."]
    
    for i, key in enumerate(keys):
        errors_log.append(f"🔍 فحص المفتاح {i+1}...")
        
        if not key or len(key) < 30:
            errors_log.append(f"🔴 المفتاح {i+1}: غير صالح أو فارغ (طول: {len(key) if key else 0})")
            continue
        
        errors_log.append(f"   طول المفتاح: {len(key)} حرف ✓")
        
        # محاولة سرد الموديلات المتاحة
        try:
            genai.configure(api_key=key)
            available_models = genai.list_models()
            model_list = [m.name for m in available_models if 'generateContent' in m.supported_generation_methods]
            errors_log.append(f"   📋 الموديلات المتاحة: {len(model_list)} موديل")
            errors_log.append(f"   📝 أول 3 موديلات: {model_list[:3]}")
            
            # استخدام أول موديل متاح
            if model_list:
                best_model_name = model_list[0]
                errors_log.append(f"   جاري تجربة أفضل موديل متاح: {best_model_name}...")
                
                model = genai.GenerativeModel(best_model_name)
                response = model.generate_content(
                    "Say hi",
                    generation_config={"max_output_tokens": 10, "temperature": 0.1}
                )
                
                errors_log.append(f"      ✅✅✅ نجح الاتصال! الموديل: {best_model_name}")
                return model, best_model_name, i+1, errors_log
        except Exception as list_error:
            errors_log.append(f"   ⚠️ فشل سرد الموديلات: {str(list_error)[:100]}")
        
        # تجربة الموديلات من القائمة
        for m_name in model_names:
            errors_log.append(f"   جاري تجربة الموديل: {m_name}...")
            try:
                genai.configure(api_key=key)
                errors_log.append(f"      ✓ تم إعداد المفتاح")
                
                model = genai.GenerativeModel(m_name)
                errors_log.append(f"      ✓ تم إنشاء كائن الموديل")
                
                response = model.generate_content(
                    "Say hi",
                    generation_config={"max_output_tokens": 10, "temperature": 0.1}
                )
                
                errors_log.append(f"      ✅✅✅ نجح الاتصال! الرد: {response.text[:30]}")
                return model, m_name, i+1, errors_log
                
            except Exception as e:
                error_msg = str(e)
                full_error = f"      ❌ فشل: {error_msg}"
                errors_log.append(full_error)
                
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
st.title("♻️ نظام الفرز الإلكتروني الذكي (v5.3)")
st.markdown("**نسخة محسّنة مع تشخيص تفصيلي**")
st.markdown("---")

# زر اختبار Google Sheets
with st.expander("🧪 اختبار اتصال Google Sheets", expanded=False):
    if st.button("▶️ اختبار الاتصال"):
        try:
            google_info = st.secrets["google_sheets"]
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            
            creds_dict = {
                "type": google_info["type"],
                "project_id": google_info["project_id"],
                "private_key_id": google_info["private_key_id"],
                "private_key": google_info["private_key"],
                "client_email": google_info["client_email"],
                "client_id": google_info["client_id"],
                "auth_uri": google_info["auth_uri"],
                "token_uri": google_info["token_uri"],
                "auth_provider_x509_cert_url": google_info["auth_provider_x509_cert_url"],
                "client_x509_cert_url": google_info["client_x509_cert_url"]
            }
            
            if "universe_domain" in google_info:
                creds_dict["universe_domain"] = google_info["universe_domain"]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            
            st.success("✅ تم الاتصال بـ Google Sheets بنجاح!")
            st.info(f"📧 Service Account: {google_info['client_email']}")
            
            # محاولة فتح الملف
            sheet = client.open("E-Waste Database")
            st.success(f"✅ تم فتح الملف: **{sheet.title}**")
            st.info(f"📄 الورقة النشطة: **{sheet.sheet1.title}**")
            st.info(f"📊 عدد الصفوف الحالية: **{len(sheet.sheet1.get_all_values())}**")
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ فشل الاختبار: {error_msg}")
            
            if "permission" in error_msg.lower() or "403" in error_msg:
                st.warning("💡 حل المشكلة:")
                st.markdown(f"""
                1. افتح ملف **E-Waste Database** في Google Sheets
                2. اضغط على زر **مشاركة** (Share)
                3. أضف هذا الإيميل: `{google_info['client_email']}`
                4. أعطه صلاحية **Editor**
                """)
            elif "not found" in error_msg.lower():
                st.warning("💡 حل المشكلة:")
                st.markdown("""
                - أنشئ ملف جديد في Google Sheets
                - سمّه بالضبط: **E-Waste Database**
                - شاركه مع الـ service account أعلاه
                """)

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

# --- 5. منطقة العمل المحسّنة v5.3 ---
st.markdown("### 📤 رفع الصورة للتحليل")
img_file = st.file_uploader("اختر صورة المعالج أو الرامة", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة الجاري تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل والحفظ التلقائي", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري تحليل الصورة بذكاء Gemini..."):
            try:
                # برومبت محسّن
                prompt = "Analyze this electronic component. Return JSON with: model, type (CPU/RAM/GPU), gold_mg (estimated gold in milligrams), value_usd (scrap value in USD)"
                
                response = st.session_state.active_engine.generate_content(
                    [prompt, img],
                    generation_config={
                        "temperature": 0,
                        "max_output_tokens": 500,
                        "top_p": 0.95,
                        "top_k": 40
                    }
                )
                
                # عرض الرد الخام أولاً
                raw_response = response.text.strip()
                
                if not raw_response or len(raw_response) < 10:
                    st.error("⚠️ الرد فارغ من AI! جاري إعادة المحاولة...")
                    response = st.session_state.active_engine.generate_content(
                        [img, "What is this component? Return: model, type, gold content mg, value usd in JSON format"],
                        generation_config={"temperature": 0.3, "max_output_tokens": 800}
                    )
                    raw_response = response.text.strip()
                
                with st.expander("🔍 الاستجابة الخام من AI"):
                    st.code(raw_response, language="text")
                
                # تنظيف النص
                res_text = raw_response.replace('```json', '').replace('```', '').replace('`', '').strip()
                
                # استخراج JSON
                if '{' in res_text and '}' in res_text:
                    start = res_text.index('{')
                    end = res_text.rindex('}') + 1
                    res_text = res_text[start:end]
                
                # محاولة التحليل المباشر
                try:
                    data = json.loads(res_text)
                    st.success("✅ تم تحليل JSON بنجاح")
                    
                except json.JSONDecodeError as je:
                    # خطة الإنقاذ: استخدام Regex
                    import re
                    st.warning("⚠️ JSON غير مكتمل - جاري استخراج البيانات بـ Regex...")
                    
                    data = {}
                    m = re.search(r'"model"\s*:\s*"([^"]*)"?', res_text)
                    t = re.search(r'"type"\s*:\s*"([^"]*)"?', res_text)
                    g = re.search(r'"gold_mg"\s*:\s*(\d+\.?\d*)', res_text)
                    v = re.search(r'"value_usd"\s*:\s*(\d+\.?\d*)', res_text)
                    
                    data['model'] = m.group(1) if m else "Unknown Model"
                    data['type'] = t.group(1) if t else "RAM"
                    data['gold_mg'] = float(g.group(1)) if g else 70.0
                    data['value_usd'] = float(v.group(1)) if v else 3.0
                    
                    st.info("✅ تم استخراج البيانات المتاحة")
                
                # التأكد من وجود جميع الحقول
                data.setdefault('model', 'Unknown')
                data.setdefault('type', 'Unknown')
                data.setdefault('gold_mg', 0.0)
                data.setdefault('value_usd', 0.0)
                
                # عرض النتائج
                st.subheader("📊 نتائج التحليل:")
                col1, col2 = st.columns(2)
                col1.metric("🔹 الموديل", data['model'])
                col1.metric("🔹 النوع", data['type'])
                col2.metric("🔸 كمية الذهب", f"{data['gold_mg']} mg")
                col2.metric("🔸 القيمة التقديرية", f"${data['value_usd']}")
                
                # الحفظ التلقائي
                if save_to_sheets(data):
                    st.success("✅ تم التحليل والحفظ في قاعدة البيانات بنجاح!")
                    st.balloons()

            except Exception as e:
                st.error(f"❌ خطأ في معالجة الصورة: {str(e)}")
                st.info("💡 جرب صورة أوضح أو بزاوية أفضل")

# تذييل
st.markdown("---")
st.caption("نظام فرز الخردة الإلكترونية v5.3 | مستقر ومحسّن | مدعوم بـ Gemini 1.5 Flash")
