import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask config
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Database paths
    DATABASE_PATH = 'shortener.db'
    
    # Upload config
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Feature flags
    ENABLE_SSO = os.getenv('ENABLE_SSO', 'false').lower() == 'true'
    
    # Microsoft Entra ID config (only used if SSO is enabled)
    CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
    CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
    AUTHORITY = os.getenv('AZURE_AUTHORITY', 'https://login.microsoftonline.com/common')
    REDIRECT_PATH = "/getAToken"
    SCOPE = ["User.Read"]
    
    # Session config
    SESSION_TYPE = "filesystem"