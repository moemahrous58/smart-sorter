import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import json
import datetime
import pandas as pd

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="Smart Sorter Pro", layout="wide", initial_sidebar_state="expanded")

# --- 2. تهيئة الذاكرة المؤقتة (Offline Mode Storage) ---
if 'offline_queue' not in st.session_state:
    st.session_state.offline_queue = []

# --- 3. وظائف الاتصال والتحليل ---
def connect_to_sheets():
    """الاتصال بجدول بيانات جوجل باستخدام المفاتيح السرية"""
    try:
        creds_dict = dict(st.secrets["google_sheets"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)
        return client.open("E-Waste Database").sheet1
    except:
        return None

def analyze_component(image, api_key):
    """تحليل الصورة عبر Gemini Flash 1.5"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        # ضغط الصورة قبل الإرسال لتوفير البيانات
        image.thumbnail((1024, 1024))
        prompt = """Analyze this E-waste part. Return ONLY a JSON object: 
        {"model": "name", "type": "CPU/RAM", "gold_mg": 0.0, "value_usd": 0.0}"""
        response = model.generate_content([prompt, image])
        clean_text = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_text)
    except Exception as e:
        return str(e)

# --- 4. القائمة الجانبية (إعدادات وإدارة الأوفلاين) ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    worker_name = st.text_input("اسم العامل الحالي:", value="Admin")
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    st.subheader("📦 العمليات المعلقة (Offline)")
    st.info(f"العمليات بانتظار الرفع: {len(st.session_state.offline_queue)}")
    
    if st.button("🚀 مزامنة البيانات السحابية", use_container_width=True):
        if st.session_state.offline_queue:
            sheet = connect_to_sheets()
            if sheet:
                with st.spinner("جاري المزامنة..."):
                    sheet.append_rows(st.session_state.offline_queue)
                    st.session_state.offline_queue = []
                    st.success("تمت المزامنة!")
                    st.rerun()
            else:
                st.error("فشل الاتصال بالإنترنت!")
        else:
            st.write("لا توجد بيانات للرفع.")

# --- 5. الواجهة الرئيسية (Tabs) ---
tab_scan, tab_report = st.tabs(["📸 الفرز الذكي", "📊 التقارير والتحميل"])

with tab_scan:
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        source = st.radio("مصدر الصورة:", ["الكاميرا المباشرة", "معرض الصور"], horizontal=True)
        if source == "الكاميرا المباشرة":
            img_file = st.camera_input("التقط صورة للقطعة")
        else:
            img_file = st.file_uploader("اختر صورة من الجهاز", type=["jpg", "jpeg", "png"])

    if img_file:
        img = Image.open(img_file)
        with col_preview:
            st.image(img, caption="الصورة الملتقطة", width=300)
            btn_analyze = st.button("🔍 بدء التحليل بالذكاء الاصطناعي", type="primary")

        if btn_analyze:
            if not api_key:
                st.error("يرجى إعداد مفتاح API أولاً!")
            else:
                with st.spinner("جاري التعرف على المكونات..."):
                    result = analyze_component(img, api_key)
                    
                    if isinstance(result, dict):
                        st.success("تم التحليل بنجاح!")
                        # التدقيق البشري
                        with st.expander("📝 مراجعة البيانات قبل الحفظ", expanded=True):
                            c1, c2 = st.columns(2)
                            final_model = c1.text_input("الموديل", value=result['model'])
                            final_gold = c2.number_input("الذهب المقدر (mg)", value=float(result['gold_mg']))
                            
                            save_option = st.radio("خيارات الحفظ:", ["رفع سحابي فوري", "حفظ محلي (أوفلاين)"])
                            
                            if st.button("💾 تأكيد الحفظ"):
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                row = [timestamp, worker_name, final_model, result['type'], final_gold, result['value_usd']]
                                
                                if save_option == "رفع سحابي فوري":
                                    sheet = connect_to_sheets()
                                    if sheet:
                                        sheet.append_row(row)
                                        st.toast("تم الرفع للسحابة!", icon="📡")
                                    else:
                                        st.session_state.offline_queue.append(row)
                                        st.warning("انقطع الاتصال، تم الحفظ في قائمة الأوفلاين.")
                                else:
                                    st.session_state.offline_queue.append(row)
                                    st.toast("تم الحفظ محلياً", icon="💾")
                    else:
                        st.error(f"خطأ في التحليل: {result}")

with tab_report:
    st.header("📈 إحصائيات قاعدة البيانات")
    sheet = connect_to_sheets()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            m1, m2, m3 = st.columns(3)
            m1.metric("إجمالي القطع", len(df))
            m2.metric("إجمالي الذهب (mg)", f"{df['gold_mg'].sum():.1f}")
            m3.metric("القيمة التقديرية ($)", f"{df['value_usd'].sum():.2f}")
            
            # زر تحميل التقرير
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 تحميل التقرير (Excel/CSV)", data=csv, file_name="inventory.csv", mime="text/csv")
            
            st.dataframe(df.sort_values(by=df.columns[0], ascending=False), use_container_width=True)
        else:
            st.info("لا توجد بيانات سحابية حتى الآن.")
    else:
        st.error("أنت تتصفح حالياً بدون اتصال بالإنترنت.")