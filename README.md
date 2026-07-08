# SensorPulse SaaS 

SensorPulse, işletmelerin IoT cihazlarından ve sensörlerinden gelen verileri gerçek zamanlı olarak toplamalarını ve izlemelerini sağlayan, Multi-Tenant (Çoklu Kiracı) mimarisine sahip bir B2B SaaS arka uç (backend) servisidir.

##  Kullanılan Teknolojiler
* **Framework:** FastAPI (Python)
* **Veritabanı:** SQLite (Geliştirme) / PostgreSQL (Üretim)
* **ORM:** SQLAlchemy
* **Konteynerleştirme:** Docker & Docker Compose

##  Temel Özellikler
1. **Multi-Tenancy:** Her şirketin verisi ve cihazları benzersiz `tenant_id` ve `api_key` ile tamamen izole edilir.
2. **Güvenli Veri Akışı:** Tüm sensör veri gönderimleri HTTP Headers üzerinden API Key doğrulaması gerektirir.
3. **Gerçek Zamanlı Hız:** FastAPI'nin asenkron yapısı sayesinde yüksek hacimli veri işleme kapasitesi.

##  Hızlı Başlangıç (Docker ile)

Projeyi bilgisayarınızda çalıştırmak için Docker'ın kurulu olması yeterlidir:

```bash
# Projeyi klonlayın
git clone [https://github.com/omerfaruk-2/sensorpulse-saas.git](https://github.com/omerfaruk-2/sensorpulse-saas.git)

# Proje dizinine girin
cd sensorpulse-saas

# Docker Compose ile ayağa kaldırın
docker-compose up -d --builds