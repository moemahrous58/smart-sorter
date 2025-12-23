import streamlit as st
import google.generativeai as genai
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import json

# 1. إعداد الصفحة
st.set_page_config(page_title="Smart Sorter v5.1", layout="centered", page_icon="♻️")

# --- 2. دالة الحفظ في Google Sheets ---
def save_to_sheets(data):
    try:
        # ملاحظة: بيانات Google Sheets تظل في Secrets لأمان ملف الاعتمادات
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

# --- 3. محرك التبادل الثلاثي للحسابات (مفاتيح مدمجة) ---
def get_working_ai_engine():
    # المفاتيح مدمجة هنا مباشرة بناءً على طلبك
    keys = [
        "AIzaSyCPl8pCcUQxK_q2f7B80jluNTeLsexnjhE",
        "AIzaSyA-gnMmgKg_0k4BpnvJ7K252Y5lRnfY7Sk",
        "AIzaSyCnfi7_J3xMzfxBqn8-S8lPeLrbxruXb8g"
    ]
    
    # قائمة أسماء الموديلات المحتملة لتجاوز خطأ 404 الشهير
    model_names = ['gemini-1.5-flash', 'models/gemini-1.5-flash']

    for i, key in enumerate(keys):
        if not key: continue
        
        try:
            genai.configure(api_key=key)
            for m_name in model_names:
                try:
                    m = genai.GenerativeModel(m_name)
                    # اختبار سريع (Ping) للتأكد من فاعلية الحساب والموديل
                    m.generate_content("test", generation_config={"max_output_tokens": 1})
                    return m, m_name, i+1 # نجاح! إعادة الموديل ورقم الحساب
                except:
                    continue
        except:
            continue
            
    return None, None, None

# --- 4. واجهة التطبيق الرئيسية ---
st.title("♻️ نظام الفرز الإلكتروني الذكي (v5.1)")
st.markdown("---")

# إدارة الحالة (Session State) لضمان عدم إعادة الفحص عند كل تفاعل
if 'active_engine' not in st.session_state:
    with st.spinner("🔄 جاري فحص الحسابات المتاحة وتجهيز المحرك..."):
        model, m_name, account_num = get_working_ai_engine()
        st.session_state.active_engine = model
        st.session_state.engine_name = m_name
        st.session_state.account_id = account_num

# عرض حالة الاتصال في الواجهة
if st.session_state.active_engine:
    st.success(f"✅ متصل بنجاح | الحساب النشط: ({st.session_state.account_id}) | الموديل: {st.session_state.engine_name}")
else:
    st.error("❌ فشل الاتصال بجميع الحسابات المدمجة. تأكد من صلاحية المفاتيح.")
    if st.button("🔄 إعادة محاولة الاتصال"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# --- 5. منطقة العمل ورفع الصور ---
img_file = st.file_uploader("📤 ارفع صورة المعالج أو الرامة المراد فحصها", type=['jpg', 'jpeg', 'png'])

if img_file:
    img = Image.open(img_file)
    st.image(img, caption="🖼️ الصورة الجاري تحليلها", use_container_width=True)
    
    if st.button("🚀 بدء التحليل والحفظ التلقائي", type="primary", use_container_width=True):
        with st.spinner("⏳ جاري تحليل الصورة واستخراج بيانات المعادن..."):
            try:
                # البرومبت المحسن لضمان رد JSON نظيف
                prompt = """Analyze this electronic component. 
                Identify the model, type, estimated gold content in mg, and scrap value in USD.
                Return ONLY a JSON object: 
                {"model": "name", "type": "CPU/RAM", "gold_mg": number, "value_usd": number}"""
                
                response = st.session_state.active_engine.generate_content([prompt, img])
                
                # معالجة النصوص وتنظيفها من علامات Markdown البرمجية
                res_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(res_text)
                
                # عرض النتائج في واجهة المستخدم
                st.subheader("📊 نتائج الفحص التقديرية:")
                col1, col2 = st.columns(2)
                col1.metric("الموديل", data.get('model', 'غير معروف'))
                col1.metric("النوع", data.get('type', 'غير معروف'))
                col2.metric("كمية الذهب", f"{data.get('gold_mg', 0)} mg")
                col2.metric("القيمة ($)", f"{data.get('value_usd', 0)} USD")
                
                # تنفيذ عملية الحفظ
                if save_to_sheets(data):
                    st.success("✅ تم استخراج البيانات وحفظها في قاعدة البيانات بنجاح!")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"⚠️ حدث خطأ أثناء التحليل: {e}")
                st.info("نصيحة: إذا تكرر الخطأ، جرب تحديث الصفحة لتغيير حساب الـ API المستخدم.")

# تذييل الصفحة
st.markdown("---")
st.caption("نظام فرز الخردة الإلكترونية v5.1 | مدعوم بذكاء Gemini ومربوط بـ Google Sheets")
