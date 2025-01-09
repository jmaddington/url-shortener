import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask config
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    DEBUG = True  # Enable debug mode
    
    # Database paths
    DATABASE_PATH = 'shortener.db'
    
    # Upload config
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Feature flags
    ENABLE_SSO = True
    
    # Session config
    SESSION_TYPE = "filesystem"