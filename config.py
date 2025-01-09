import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask config
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    # Database paths
    DATABASE_PATH = 'shortener.db'
    
    # Upload config
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Feature flags
    ENABLE_SSO = os.getenv('ENABLE_SSO', 'false').lower() == 'true'
    
    # Session config
    SESSION_TYPE = "filesystem"