from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Geliştirme aşamasında SQLite kullanıyoruz, ileride Docker'da PostgreSQL'e çevireceğiz.
SQLALCHEMY_DATABASE_URL = "sqlite:///./sensorpulse.db"

engine = create_engine(
    # SQLite'a özel: Birden fazla thread'in aynı anda erişebilmesi için gerekli
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Veritabanı oturumu (Session) yönetimi için bağımlılık fonksiyonu
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()