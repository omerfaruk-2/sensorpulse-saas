import os
from fastapi import FastAPI, Depends, Header, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Annotated
from datetime import datetime # Tarih formatı için eklendi
from database import engine, get_db
import models
import logging
import time
import uuid as uuid_module
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- PYDANTIC MODELLER (Input Validation Güçlendirilmiş) ---

class DeviceCreate(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100, description="Cihaz adı")
    device_type: str = Field(..., min_length=1, max_length=50, description="Cihaz türü")

class DataLogCreate(BaseModel):
    device_id: str = Field(..., description="Hedef cihaz UUID'si")
    value: Annotated[float, Field(ge=-1000000.0, le=1000000.0, description="Sensör değeri")]

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v):
        try:
            uuid_module.UUID(v)
        except ValueError:
            raise ValueError("Geçersiz device_id formatı. UUID bekleniyor.")
        return v

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

# --- CORS (Cross-Origin Resource Sharing) POLİTİKASI ---
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["x-api-key", "x-admin-key"],
)

# --- RATE LIMITING ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- LOGLAMA (LOGGING) AYARLARI ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- MIDDLEWARE (Tüm İstekleri Yakalayan Ara Katman + Güvenlik Başlıkları) ---
@app.middleware("http")
async def log_and_secure(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(
        f"IP: {request.client.host} | Method: {request.method} | "
        f"Path: {request.url.path} | Status: {response.status_code} | "
        f"Time: {process_time:.4f}s"
    )
    
    # --- GÜVENLİK BAŞLIKLARI ---
    # FastAPI'de middleware icinde headerlari bu sekilde eklemek bazen starlette arka planinda silinir, 
    # garantilemek icin set headers yapmaliyiz
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# 1. Kök Dizin (Health Check) Uç Noktası
@app.get("/")
def read_root():
    return {"mesaj": "SensorPulse API sorunsuz çalisiyor!", "durum": "aktif"}

# --- ADMIN GÜVENLİK KATMANI ---
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

def verify_admin_key(x_admin_key: str = Header(default=None)):
    """Tenant oluşturma gibi yönetim işlemleri için admin key doğrulaması."""
    if not x_admin_key or not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yetkisiz erişim! Geçerli bir admin anahtarı gerekli."
        )
    return x_admin_key

# 2. Yeni Bir Şirket (Tenant) Kayıt Uç Noktası (Admin korumalı)
@app.post("/api/tenants/")
def create_tenant(
    company_name: str,
    db: Session = Depends(get_db),
    admin_key: str = Depends(verify_admin_key)
):
    # Hash'li API Key üret
    raw_key, hashed_key = models.Tenant.generate_api_key()
    
    # models.py içindeki Tenant sınıfından yeni bir kayıt oluşturuyoruz
    yeni_tenant = models.Tenant(company_name=company_name, api_key=hashed_key)
    
    db.add(yeni_tenant)
    db.commit()
    db.refresh(yeni_tenant) # Oluşan ID'yi almak için yeniliyoruz
    
    return {
        "mesaj": "Şirket başarıyla sisteme eklendi.",
        "company_name": yeni_tenant.company_name,
        "tenant_id": yeni_tenant.id,
        "api_key": raw_key  # Ham key SADECE BU YANIT'ta gösterilir, bir daha erişilemez!
    }

# --- GÜVENLİK KATMANI (Hash'li API Key Doğrulama) ---
def verify_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    """Gelen istekteki Header içinde x-api-key olup olmadığını ve doğruluğunu kontrol eder."""
    hashed_key = models.Tenant.hash_key(x_api_key)
    tenant = db.query(models.Tenant).filter(models.Tenant.api_key == hashed_key).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Geçersiz veya eksik API Anahtari!"
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
@limiter.limit("60/minute")
def ingest_data(
    request: Request,
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
        raise HTTPException(status_code=404, detail="Cihaz bulunamadi veya size ait değil!")
        
    yeni_veri = models.DataLog(
        device_id=cihaz.id,
        tenant_id=current_tenant.id,
        value=data.value
    )
    db.add(yeni_veri)
    db.commit()
    
    return {"mesaj": "Veri başariyla işlendi", "value": yeni_veri.value}

# --- 5. Cihaz Verilerini Okuma (Dashboard) Uç Noktası ---
@app.get("/api/data/{device_id}", response_model=List[DataLogResponse])
def get_device_data(
    device_id: str,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maks. döndürülecek kayıt sayısı")] = 10,
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
    
    return {"mesaj": f"{cihaz.device_name} isimli cihaz başariyla silindi."}