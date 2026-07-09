#  SensorPulse SaaS Platformu (B2B IoT Arka Uç Mimarisi)

SensorPulse, işletmelerin IoT sensörlerinden gelen verileri gerçek zamanlı ve güvenli bir şekilde toplamalarını, izlemelerini ve yönetmelerini sağlayan, **Multi-Tenant (Çoklu Kiracı)** mimarisine sahip uçtan uca bir SaaS projesidir. 

Proje, modern yazılım geliştirme yaşam döngüsü (SDLC) prensiplerine sadık kalınarak, asenkron ağ programlama ve mikroservis yaklaşımıyla geliştirilmiştir.

##  Sistem Mimarisi ve Teknoloji Yığını (Tech Stack)

Sistem üç ana katmandan oluşmaktadır:

1.  **Backend - FastAPI (Python):** Asenkron (async/await) yapısı sayesinde donanımı yormadan aynı anda on binlerce HTTP isteğini işleyebilir.
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

##  Tasarım ve Mühendislik Kararları

* **Veri Minimizasyonu (Tenant ID Gizliliği):** İstemciye (Client) dönen yanıtlarda (GET isteklerinde) şirketlere ait `tenant_id` bilgisi güvenlik gereği özellikle gizlenmiştir. İstemci kendi API Key'i ile bağlandığı için sistem izolasyonu arka planda yönetir; bu sayede hem gereksiz veri transferi (bant genişliği israfı) önlenir hem de sistemin iç şeması dışarıya sızdırılmaz.
* **Veri Yaşam Döngüsü ve Temizlik:** IoT projelerinde veritabanının kontrolsüzce şişmesini engellemek kritik olduğundan, cihaz silme (DELETE) mekanizması kurgulanmıştır. (Mevcut yapıda veriler doğrudan silinmektedir, ancak daha büyük çaplı bir üretim ortamında `is_active=False` etiketlemesiyle "Soft Delete" yapısına geçiş planlanmaktadır).

##  Nasıl Çalıştırılır? (Docker Kurulumu)

Projeyi ayağa kaldırmak için bilgisayarınızda Docker'ın yüklü olması yeterlidir.

1. Depoyu bilgisayarınıza klonlayın:
   ```bash
   git clone [https://github.com/omerfaruk-2/sensorpulse-saas.git](https://github.com/omerfaruk-2/sensorpulse-saas.git)

2. Proje dizinine girip konteynerleri başlatın: docker-compose up -d --build
3. Servislere erişin:
API Dokümantasyonu (Swagger): http://localhost:8000/docs
Yönetim Paneli (Streamlit): Yeni bir terminalde streamlit run dashboard.py komutunu çalıştırarak panele erişebilirsiniz.
