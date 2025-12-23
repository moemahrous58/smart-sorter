if st.button("🧪 اختبار Google Sheets"):
    try:
        google_info = st.secrets["google_sheets"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(google_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        st.success("✅ تم الاتصال بنجاح!")
        st.write(f"📧 Service Account: {google_info['client_email']}")
        
        # محاولة فتح الملف
        sheet = client.open("E-Waste Database")
        st.success(f"✅ تم فتح الملف: {sheet.title}")
        st.write(f"📄 الورقة الأولى: {sheet.sheet1.title}")
        
    except Exception as e:
        st.error(f"❌ فشل: {e}")
