import streamlit as st
import requests
import pandas as pd
import os
import re

# API base URL'i environment variable'dan oku (SSRF koruması: hardcoded localhost kaldırıldı)
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# UUID format doğrulama fonksiyonu (Path Traversal / SSRF koruması)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)

def is_valid_uuid(value: str) -> bool:
    """Verilen string'in geçerli UUID formatında olup olmadığını kontrol eder."""
    return bool(UUID_PATTERN.match(value.strip()))

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
    
    # Arayüzü 4 farklı sekmeye bölüyoruz (Veri Gönder eklendi)
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Veri İzleme", "➕ Cihaz Ekle", "📡 Veri Gönder", "🗑️ Cihaz Sil"])
    
    # --- SEKME 1: VERİ İZLEME (GET) ---
    with tab1:
        st.subheader("Cihaz Verilerini İzle")
        device_id_to_watch = st.text_input("İzlenecek Cihaz ID:")
        
        if device_id_to_watch:
            if not is_valid_uuid(device_id_to_watch):
                st.error("❌ Geçersiz Cihaz ID formatı! UUID formatında olmalıdır (örn: 550e8400-e29b-41d4-a716-446655440000).")
            else:
                with st.spinner("Veriler API'den çekiliyor..."):
                    response = requests.get(f"{API_BASE}/api/data/{device_id_to_watch.strip()}", headers=headers)
                    
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
        with st.form("add_device_form"):
            new_device_name = st.text_input("Cihaz Adı (Örn: Fabrika-Motor-Sensörü)")
            new_device_type = st.text_input("Cihaz Türü (Örn: Sıcaklık)")
            submit_button = st.form_submit_button("Cihazı Ekle")
            
            if submit_button:
                if new_device_name and new_device_type:
                    payload = {"device_name": new_device_name, "device_type": new_device_type}
                    res = requests.post(f"{API_BASE}/api/devices/", json=payload, headers=headers)
                    
                    if res.status_code == 200:
                        st.success(f"✅ Cihaz başarıyla eklendi! Cihaz ID: {res.json().get('device_id')}")
                    else:
                        st.error(f"Cihaz eklenemedi. Hata Kodu: {res.status_code}")
                else:
                    st.warning("Lütfen cihaz adı ve türünü boş bırakmayın.")

    # --- SEKME 3: VERİ GÖNDER (POST DATA) ---
    with tab3:
        st.subheader("Sensörden Manuel Veri Gönder (Simülasyon)")
        with st.form("send_data_form"):
            target_device_id = st.text_input("Hedef Cihaz ID:")
            # Sayısal veri girişi için number_input kullanıyoruz
            sensor_value = st.number_input("Sensör Değeri:", value=0.0, format="%.2f")
            send_data_button = st.form_submit_button("Veriyi İlet")
            
            if send_data_button:
                if target_device_id:
                    if not is_valid_uuid(target_device_id):
                        st.error("❌ Geçersiz Cihaz ID formatı! UUID formatında olmalıdır.")
                    else:
                        payload = {"device_id": target_device_id.strip(), "value": sensor_value}
                        res = requests.post(f"{API_BASE}/api/data/", json=payload, headers=headers)
                        
                        if res.status_code == 200:
                            st.success(f"✅ Veri başarıyla işlendi! Değer: {res.json().get('value')}")
                        elif res.status_code == 404:
                            st.error("❌ Cihaz bulunamadı veya yetkiniz yok!")
                        else:
                            st.error(f"Veri gönderilemedi. Hata Kodu: {res.status_code}")
                else:
                    st.warning("Lütfen hedef cihaz ID'sini girin.")

    # --- SEKME 4: CİHAZ SİL (DELETE) ---
    with tab4:
        st.subheader("Sistemden Cihaz Kaldır")
        with st.form("delete_device_form"):
            device_id_to_delete = st.text_input("Silinecek Cihazın ID'si:")
            delete_button = st.form_submit_button("Cihazı Kalıcı Olarak Sil")
            
            if delete_button:
                if device_id_to_delete:
                    if not is_valid_uuid(device_id_to_delete):
                        st.error("❌ Geçersiz Cihaz ID formatı! UUID formatında olmalıdır.")
                    else:
                        res = requests.delete(f"{API_BASE}/api/devices/{device_id_to_delete.strip()}", headers=headers)
                        
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