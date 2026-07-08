from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import engine, get_db
import models

class DeviceCreate(BaseModel):
    device_name: str
    device_type: str

class DataLogCreate(BaseModel):
    device_id: str
    value: float

# Veritabanı tablolarını otomatik olarak oluşturur (SQLite sensorpulse.db dosyasını yaratır)
models.Base.metadata.create_all(bind=engine)

# FastAPI uygulamasını başlatıyoruz
app = FastAPI(
    title="SensorPulse SaaS API",
    description="Gerçek Zamanlı IoT Cihaz İzleme Platformu İçin Arka Uç Servisi",
    version="1.0.0"
)

# 1. Kök Dizin (Health Check) Uç Noktası
@app.get("/")
def read_root():
    return {"mesaj": "SensorPulse API sorunsuz çalışıyor!", "durum": "aktif"}

# 2. Yeni Bir Şirket (Tenant) Kayıt Uç Noktası
@app.post("/api/tenants/")
def create_tenant(company_name: str, db: Session = Depends(get_db)):
    # models.py içindeki Tenant sınıfından yeni bir kayıt oluşturuyoruz
    yeni_tenant = models.Tenant(company_name=company_name)
    
    db.add(yeni_tenant)
    db.commit()
    db.refresh(yeni_tenant) # Oluşan ID ve API Key'i almak için yeniliyoruz
    
    return {
        "mesaj": "Şirket başarıyla sisteme eklendi.",
        "company_name": yeni_tenant.company_name,
        "tenant_id": yeni_tenant.id,
        "api_key": yeni_tenant.api_key
    }

# --- GÜVENLİK KATMANI ---
def verify_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    """Gelen istekteki Header içinde x-api-key olup olmadığını ve doğruluğunu kontrol eder."""
    tenant = db.query(models.Tenant).filter(models.Tenant.api_key == x_api_key).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Geçersiz veya eksik API Anahtarı!"
        )
    return tenant

# --- 3. Cihaz (Sensör) Kayıt Uç Noktası ---
@app.post("/api/devices/")
def create_device(
    device: DeviceCreate, 
    db: Session = Depends(get_db), 
    current_tenant: models.Tenant = Depends(verify_api_key)
):
    yeni_cihaz = models.Device(
        tenant_id=current_tenant.id,
        device_name=device.device_name,
        device_type=device.device_type
    )
    db.add(yeni_cihaz)
    db.commit()
    db.refresh(yeni_cihaz)
    
    return {"mesaj": "Cihaz başarıyla kaydedildi", "device_id": yeni_cihaz.id}

# --- 4. Gerçek Zamanlı Veri Gönderme Uç Noktası ---
@app.post("/api/data/")
def ingest_data(
    data: DataLogCreate, 
    db: Session = Depends(get_db), 
    current_tenant: models.Tenant = Depends(verify_api_key)
):
    # Cihazın gerçekten bu şirkete ait olup olmadığını kontrol ediyoruz
    cihaz = db.query(models.Device).filter(
        models.Device.id == data.device_id,
        models.Device.tenant_id == current_tenant.id
    ).first()
    
    if not cihaz:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı veya size ait değil!")
        
    yeni_veri = models.DataLog(
        device_id=cihaz.id,
        tenant_id=current_tenant.id,
        value=data.value
    )
    db.add(yeni_veri)
    db.commit()
    
    return {"mesaj": "Veri başarıyla işlendi", "value": yeni_veri.value}