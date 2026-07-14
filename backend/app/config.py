import os


basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    DB_NAME = os.getenv("DB_NAME", "neondb")
    DB_USER = os.getenv("DB_USER", "neondb_owner")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "npg_OQNst5Sm2Vyx")  
    
    DB_HOST = os.getenv("DB_HOST", "ep-still-thunder-adkxyevh-pooler.c-2.us-east-1.aws.neon.tech")
    DB_PORT = os.getenv("DB_PORT", "5432")

    _db_url = os.getenv("DATABASE_URL")
    if not _db_url:
        _db_url = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    else:
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif _db_url.startswith("postgresql://") and "+psycopg" not in _db_url and "+psycopg2" not in _db_url:
            _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "&channel_binding=require" in _db_url:
            _db_url = _db_url.replace("&channel_binding=require", "")
        if "?channel_binding=require" in _db_url:
            _db_url = _db_url.replace("?channel_binding=require", "?sslmode=require")

    from sqlalchemy.pool import NullPool
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,
        "pool_pre_ping": True,
        "connect_args": {
            "connect_timeout": 10
        }
    }

    # Cloudinary Config
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER = os.getenv("EMAIL_USER", "msriraghuram@gmail.com")
    EMAIL_PASS = os.getenv("EMAIL_PASS", "usxqkvmvceifmdwm")  

    UPLOAD_FOLDER = os.path.join(basedir, "../../frontend/static/uploads/products")
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB

    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    UPLOAD_REELS_FOLDER = os.path.join(basedir, "../../frontend/static/uploads/reels")
    ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "webm"}
