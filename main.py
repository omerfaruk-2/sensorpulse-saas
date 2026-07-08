from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc  # Sıralama için eklendi
from typing import List      # Tip belirleme için eklendi
from datetime import datetime # Tarih formatı için eklendi
from database import engine, get_db
import models

class DeviceCreate(BaseModel):
    device_name: str
    device_type: str

class DataLogCreate(BaseModel):
    device_id: str
    value: float

class DataLogResponse(BaseModel):
    id: str
    device_id: str
    value: float
    timestamp: datetime

    class Config:
        from_attributes = True# SQLAlchemy modellerini okuyabilmesi için kritik ayar

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

# --- 5. Cihaz Verilerini Okuma (Dashboard) Uç Noktası ---
@app.get("/api/data/{device_id}", response_model=List[DataLogResponse])
def get_device_data(
    device_id: str,
    limit: int = 10, # İstemci aksini belirtmezse sadece son 10 veriyi getir
    db: Session = Depends(get_db),
    current_tenant: models.Tenant = Depends(verify_api_key)
):
    # 1. Güvenlik Kontrolü: Cihaz bu şirkete mi ait? (Yatay Yetki Yükseltme saldırısını önler)
    cihaz = db.query(models.Device).filter(
        models.Device.id == device_id,
        models.Device.tenant_id == current_tenant.id
    ).first()
    
    if not cihaz:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadi veya yetkiniz yok!")
        
    # 2. Sorgu: Verileri tarihe göre yeniden eskiye (DESC) sırala ve limitle
    veriler = db.query(models.DataLog).filter(
        models.DataLog.device_id == device_id,
        models.DataLog.tenant_id == current_tenant.id
    ).order_by(desc(models.DataLog.timestamp)).limit(limit).all()
    
    return veriler

# --- 6. Cihaz Silme Uç Noktası (DELETE) ---
@app.delete("/api/devices/{device_id}")
def delete_device(
    device_id: str, 
    db: Session = Depends(get_db), 
    current_tenant: models.Tenant = Depends(verify_api_key)
):
    # Silinecek cihazı bul ve bu şirkete ait olduğundan emin ol
    cihaz = db.query(models.Device).filter(
        models.Device.id == device_id,
        models.Device.tenant_id == current_tenant.id
    ).first()
    
    if not cihaz:
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı veya silme yetkiniz yok!")
        
    db.delete(cihaz)
    db.commit()
    
    return {"mesaj": f"{cihaz.device_name} isimli cihaz başarıyla silindi."}