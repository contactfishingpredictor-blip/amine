import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration de base - Gmail uniquement"""
    
    # ===== CONFIGURATION GÉNÉRALE =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    APP_NAME = "Fishing Predictor Pro"
    APP_VERSION = "2.2.0"
    
    # ===== CONFIGURATION EMAIL GMAIL UNIQUEMENT =====
    GMAIL_USER = os.getenv('GMAIL_USER')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'contactfishingpredictor@gmail.com')
    EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Fishing Predictor Pro')
    
    # ===== API KEYS =====
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    STORMGLASS_API_KEY = os.getenv('STORMGLASS_API_KEY')
    WORLDTIDES_API_KEY = os.getenv('WORLDTIDES_API_KEY')
    METEO_CONCEPT_TOKEN = os.getenv('METEO_CONCEPT_TOKEN')
    WEKEO_USER = os.getenv('WEKEO_USER')
    WEKEO_PASSWORD = os.getenv('WEKEO_PASSWORD')
    
    # ===== CHEMINS ET FICHIERS =====
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CACHE_DIR = os.path.join(BASE_DIR, 'api_cache')
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    
    FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')
    ALERTS_FILE = os.path.join(DATA_DIR, 'alerts_subscriptions.json')
    EMAIL_LOGS_FILE = os.path.join(DATA_DIR, 'email_logs.json')
    
    # ===== DATABASE =====
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/fishing.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ===== CONSTANTES =====
    SEAWATER_DENSITY = 1025
    SALINITY_MEDITERRANEAN = 38.0
    ATMOSPHERIC_PRESSURE_SEA = 1013.25
    
    # ===== LIMITES API =====
    API_LIMITS = {
        'openweather': {'max_per_day': 1000, 'cache_duration': 30*60},
        'stormglass': {'max_per_day': 10, 'cache_duration': 6*60*60},
        'worldtides': {'max_per_day': 10, 'cache_duration': 6*60*60},
        'nominatim': {'max_per_hour': 1, 'cache_duration': 24*60*60},
        'emodnet': {'max_per_hour': 10, 'cache_duration': 7*24*60*60},
        'openmeteo': {'max_per_hour': 100, 'cache_duration': 30*60},
        'meteoconcept': {'max_per_day': 100, 'cache_duration': 60*60}
    }
    
    # ===== CACHE =====
    WEATHER_CACHE_DURATION = 30 * 60  # 30 minutes
    
    # ===== URLS API =====
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    STORMGLASS_URL = "https://api.stormglass.io/v2"
    WORLDTIDES_URL = "https://www.worldtides.info/api/v3"
    METEO_CONCEPT_URL = "https://api.meteo-concept.com/api"
    
    # ===== CONFIGURATION GMAIL POUR RENDER =====
    @property
    def GMAIL_CONFIG(self):
        """Configuration Gmail optimisée"""
        return {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,  # Port TLS
            'sender_email': self.GMAIL_USER,
            'sender_name': self.EMAIL_FROM_NAME,
            'username': self.GMAIL_USER,
            'password': self.GMAIL_APP_PASSWORD,
            'use_tls': True,
            'timeout': 30
        }
    
    def check_gmail_config(self):
        """Vérifie la configuration Gmail"""
        try:
            has_gmail = bool(self.GMAIL_USER and '@gmail.com' in self.GMAIL_USER)
            has_password = bool(self.GMAIL_APP_PASSWORD and len(self.GMAIL_APP_PASSWORD) >= 16)
            
            return {
                'gmail_ready': has_gmail and has_password,
                'user_configured': has_gmail,
                'password_configured': has_password,
                'sender': self.GMAIL_USER
            }
        except:
            return {'gmail_ready': False}
    
    @classmethod
    def validate_config(cls):
        """Valide la configuration"""
        print("\n" + "="*50)
        print("🔧 VALIDATION CONFIGURATION GMAIL")
        print("="*50)
        
        # Vérification Gmail
        print(f"📧 GMAIL_USER: {'✅ ' + cls.GMAIL_USER if cls.GMAIL_USER else '❌ Manquant'}")
        
        if cls.GMAIL_APP_PASSWORD:
            if len(cls.GMAIL_APP_PASSWORD) >= 16:
                print(f"🔑 GMAIL_APP_PASSWORD: ✅ Format correct ({len(cls.GMAIL_APP_PASSWORD)} caractères)")
            else:
                print(f"🔑 GMAIL_APP_PASSWORD: ❌ MAUVAIS FORMAT! Doit être 16+ caractères")
        else:
            print(f"🔑 GMAIL_APP_PASSWORD: ❌ Manquant")
        
        # Vérifier si Gmail est opérationnel
        has_gmail = bool(cls.GMAIL_USER and cls.GMAIL_APP_PASSWORD and 
                        len(cls.GMAIL_APP_PASSWORD) >= 16 and 
                        '@gmail.com' in cls.GMAIL_USER)
        
        if not has_gmail:
            print("\n❌ GMAIL NON CONFIGURÉ!")
            print("   Pour générer un App Password correct:")
            print("   1. Active 2FA sur https://myaccount.google.com/security")
            print("   2. Généres un App Password: 'Sécurité' → 'Mots de passe d'application'")
            print("   3. Sélectionne 'Autre', nomme 'Render'")
            print("   4. Copie les 16 caractères SANS les espaces")
            return False
        
        print("\n✅ GMAIL PRÊT")
        print("="*50)
        return True

# Instance de configuration
config = Config()