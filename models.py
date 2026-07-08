import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# 1. Şirket (Tenant / Müşteri) Modeli
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_name = Column(String, nullable=False)
    # Her şirketin sensörlerinden veri toplarken kullanacağı benzersiz gizli anahtar
    api_key = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # İlişkiler
    devices = relationship("Device", back_populates="tenant")

# 2. Cihaz (Sensör) Modeli
class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    device_name = Column(String, nullable=False) # Örn: "Mutfak Buzdolabı", "Depo-A"
    device_type = Column(String, nullable=False) # Örn: "Temperature", "Humidity"

    # İlişkiler
    tenant = relationship("Tenant", back_populates="devices")
    data_logs = relationship("DataLog", back_populates="device")

# 3. Gerçek Zamanlı Veri Günlüğü (Data Log) Modeli
class DataLog(Base):
    __tablename__ = "data_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    # Güvenlik katmanı: Sorguları hızlandırmak ve izolasyonu sağlamak için burada da tenant_id tutuyoruz
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    
    value = Column(Float, nullable=False) # Sensörden gelen ölçüm değeri (Örn: 24.5)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    device = relationship("Device", back_populates="data_logs")