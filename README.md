#  SensorPulse SaaS Platformu (B2B IoT Arka Uç Mimarisi)

SensorPulse, işletmelerin IoT sensörlerinden gelen verileri gerçek zamanlı ve güvenli bir şekilde toplamalarını, izlemelerini ve yönetmelerini sağlayan, **Multi-Tenant (Çoklu Kiracı)** mimarisine sahip uçtan uca bir SaaS projesidir. 

Proje, modern yazılım geliştirme yaşam döngüsü (SDLC) prensiplerine sadık kalınarak, asenkron ağ programlama ve mikroservis yaklaşımıyla geliştirilmiştir.

##  Sistem Mimarisi ve Teknoloji Yığını (Tech Stack)

Sistem üç ana katmandan oluşmaktadır:

1.  **Arka Uç (Backend) - FastAPI (Python):** Asenkron (async/await) yapısı sayesinde donanımı yormadan aynı anda on binlerce HTTP isteğini işleyebilir.
2.  **Veritabanı Katmanı - SQLAlchemy ORM:** Nesne-ilişkisel eşleme kullanılarak veritabanı şemaları oluşturulmuştur. (Şu an geliştirme için SQLite kullanılmaktadır, üretim ortamı için PostgreSQL hedeflenmektedir).
3.  **Ön Yüz / Yönetim Paneli - Streamlit:** Saf Python ile yazılmış, API ile entegre çalışan gerçek zamanlı bir B2B gösterge panelidir.
4.  **Altyapı ve Dağıtım - Docker & Docker Compose:** "Benim bilgisayarımda çalışıyordu" sorununu ortadan kaldırmak için sistem tamamen konteynerleştirilmiştir.

##  Temel Mühendislik Kararları ve Güvenlik

* **Multi-Tenancy (Mantıksal İzolasyon):** Veritabanındaki her cihaza ve sensör verisine benzersiz bir `tenant_id` damgası vurulur. A şirketinin verileri ile B şirketinin verileri asla birbirine karışmaz.
* **Header Tabanlı API Güvenliği:** Her bir HTTP POST/GET/DELETE isteğinde özel bir FastAPI Middleware'i (Ara Katman) devreye girer. İstemci `x-api-key` başlığını (header) göndermezse veya geçersiz bir anahtar gönderirse, sistem `401 Unauthorized` döner ve isteği reddeder.
* **İzlenebilirlik (Logging Middleware):** Sisteme gelen her bir istek, IP adresi, işlem süresi (milisaniye) ve HTTP durum kodu ile birlikte arka planda loglanır.

##  API Uç Noktaları (Endpoints)

Sistem RESTful mimari standartlarına tam uyumlu olarak tasarlanmıştır:
* `GET /api/data/{device_id}`: Belirli bir cihaza ait sensör verilerini zamana göre sıralı getirir.
* `POST /api/devices/`: Sisteme yeni bir IoT cihazı tanımlar.
* `POST /api/data/`: Sensörlerden gelen anlık ölçüm verilerini (Data Ingestion) sisteme kaydeder.
* `DELETE /api/devices/{device_id}`: Cihazı sistemden kalıcı olarak siler.

##  Nasıl Çalıştırılır? (Docker Kurulumu)

Projeyi ayağa kaldırmak için bilgisayarınızda Docker'ın yüklü olması yeterlidir.

1. Depoyu bilgisayarınıza klonlayın:
   ```bash
   git clone [https://github.com/omerfaruk-2/sensorpulse-saas.git](https://github.com/omerfaruk-2/sensorpulse-saas.git)
