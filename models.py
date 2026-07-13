import uuid
import hashlib
import secrets
from sqlalchemy import Column, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone

# 1. Şirket (Tenant / Müşteri) Modeli
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String, nullable=False)
    # Her şirketin sensörlerinden veri toplarken kullanacağı benzersiz gizli anahtar (SHA-256 hash olarak saklanır)
    api_key = Column(String, unique=True, index=True)

    # İlişkiler (cascade: tenant silinirse cihazları da silinir)
    devices = relationship("Device", back_populates="tenant", cascade="all, delete-orphan")

    @staticmethod
    def generate_api_key():
        """Ham API Key üretir ve (ham_key, hash_değeri) tuple döndürür."""
        raw_key = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, hashed

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Gelen ham key'i hash'ler (doğrulama için)."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

# 2. Cihaz (Sensör) Modeli
class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    device_name = Column(String, nullable=False) # Örn: "Mutfak Buzdolabı", "Depo-A"
    device_type = Column(String, nullable=False) # Örn: "Temperature", "Humidity"

    # İlişkiler
    tenant = relationship("Tenant", back_populates="devices")
    # cascade: cihaz silinirse veri logları da silinir
    data_logs = relationship("DataLog", back_populates="device", cascade="all, delete-orphan")

# 3. Gerçek Zamanlı Veri Günlüğü (Data Log) Modeli
class DataLog(Base):
    __tablename__ = "data_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    # Güvenlik katmanı: Sorguları hızlandırmak ve izolasyonu sağlamak için burada da tenant_id tutuyoruz
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    value = Column(Float, nullable=False) # Sensörden gelen ölçüm değeri (Örn: 24.5)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    device = relationship("Device", back_populates="data_logs")