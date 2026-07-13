# Resmi ve hafif bir Python imajı kullanıyoruz
FROM python:3.11-slim

# Non-root kullanıcı oluştur (Güvenlik: container escape saldırılarını önler)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Konteyner içindeki çalışma dizinini belirliyoruz
WORKDIR /app

# Önce sadece kütüphane listesini kopyalayıp yüklüyoruz (Cache avantajı için)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Şimdi tüm proje dosyalarımızı konteynerin içine kopyalıyoruz
COPY . .

# Root olmayan kullanıcıya geç
USER appuser

# FastAPI'nin çalışacağı portu dışarı açıyoruz
EXPOSE 8000

# Konteyner başlatıldığında çalıştırılacak komut
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]