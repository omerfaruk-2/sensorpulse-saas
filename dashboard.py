import streamlit as st
import requests
import pandas as pd

# Sayfa ayarları
st.set_page_config(page_title="SensorPulse Admin", page_icon="🚀", layout="wide")

st.title(" SensorPulse Yönetim ve İzleme Paneli")
st.markdown("API Key'inizi kullanarak cihazlarınızı yönetebilir ve verileri canlı izleyebilirsiniz.")

# Yan menü (Sidebar)
with st.sidebar:
    st.header("🔑 Kimlik Doğrulama")
    api_key = st.text_input("Şirket API Key:", type="password")

# Kullanıcı API Key girdiyse paneli göster
if api_key:
    headers = {"x-api-key": api_key}
    
    # Arayüzü 3 farklı sekmeye bölüyoruz
    tab1, tab2, tab3 = st.tabs(["📊 Veri İzleme", "➕ Cihaz Ekle", "🗑️ Cihaz Sil"])
    
    # --- SEKME 1: VERİ İZLEME (GET) ---
    with tab1:
        st.subheader("Cihaz Verilerini İzle")
        device_id_to_watch = st.text_input("İzlenecek Cihaz ID:")
        
        if device_id_to_watch:
            with st.spinner("Veriler API'den çekiliyor..."):
                response = requests.get(f"http://localhost:8000/api/data/{device_id_to_watch}", headers=headers)
                
            if response.status_code == 200:
                veriler = response.json()
                
                if len(veriler) > 0:
                    st.success(f"{len(veriler)} adet veri başarıyla çekildi!")
                    df = pd.DataFrame(veriler)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.set_index('timestamp')
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.metric(label="Son Sensör Değeri", value=f"{df['value'].iloc[0]}")
                        st.dataframe(df[['value']].head(10))
                    with col2:
                        st.line_chart(df['value'])
                else:
                    st.warning("Bu cihaza ait henüz hiç veri yok.")
            elif response.status_code == 404:
                st.error("❌ Cihaz bulunamadı veya size ait değil!")
            else:
                st.error(f"Hata: Geçersiz API Key veya sistem hatası ({response.status_code})")

    # --- SEKME 2: CİHAZ EKLE (POST) ---
    with tab2:
        st.subheader("Sisteme Yeni Cihaz Kayıt Et")
        # Form kullanıyoruz ki kullanıcı 'Ekle' butonuna basmadan istek atılmasın
        with st.form("add_device_form"):
            new_device_name = st.text_input("Cihaz Adı (Örn: Fabrika-Motor-Sensörü)")
            new_device_type = st.text_input("Cihaz Türü (Örn: Sıcaklık)")
            submit_button = st.form_submit_button("Cihazı Ekle")
            
            if submit_button:
                if new_device_name and new_device_type:
                    payload = {"device_name": new_device_name, "device_type": new_device_type}
                    res = requests.post("http://localhost:8000/api/devices/", json=payload, headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"✅ Cihaz başarıyla eklendi! Cihaz ID: {res.json().get('device_id')}")
                    else:
                        st.error(f"Cihaz eklenemedi. Hata Kodu: {res.status_code}")
                else:
                    st.warning("Lütfen cihaz adı ve türünü boş bırakmayın.")

    # --- SEKME 3: CİHAZ SİL (DELETE) ---
    with tab3:
        st.subheader("Sistemden Cihaz Kaldır")
        with st.form("delete_device_form"):
            device_id_to_delete = st.text_input("Silinecek Cihazın ID'si:")
            delete_button = st.form_submit_button("Cihazı Kalıcı Olarak Sil")
            
            if delete_button:
                if device_id_to_delete:
                    res = requests.delete(f"http://localhost:8000/api/devices/{device_id_to_delete}", headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"✅ Cihaz başarıyla silindi!")
                    elif res.status_code == 404:
                        st.error("❌ Cihaz bulunamadı veya silme yetkiniz yok!")
                    else:
                        st.error(f"Silme işlemi başarısız. Hata Kodu: {res.status_code}")
                else:
                    st.warning("Lütfen silinecek cihazın ID'sini girin.")
else:
    st.info("Lütfen sol menüden API Key bilginizi girerek sisteme giriş yapın.")