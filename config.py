"""
Configuration centrale sécurisée pour Fishing Predictor Pro
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration de base"""
    
    # ===== CONFIGURATION GÉNÉRALE =====
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    APP_NAME = "Fishing Predictor Pro"
    APP_VERSION = "2.1.0"
    
    # ===== CONFIGURATION EMAIL (CRITIQUE) =====
    GMAIL_USER = os.getenv('GMAIL_USER')  # contactfishingpredictor@gmail.com
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')  # opyr jyhe vjsr rftu
    
    # ===== API KEYS =====
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    STORMGLASS_API_KEY = os.getenv('STORMGLASS_API_KEY')
    WORLDTIDES_API_KEY = os.getenv('WORLDTIDES_API_KEY')
    METEO_CONCEPT_TOKEN = os.getenv('METEO_CONCEPT_TOKEN')
    WEKEO_API_TOKEN = os.getenv('WEKEO_API_TOKEN')
    
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
    
    # ===== CONFIGURATION EMAIL =====
    @property
    def EMAIL_CONFIG(self):
        """Configuration email dynamique"""
        sender_email = self.GMAIL_USER if self.GMAIL_USER else 'contactfishingpredictor@gmail.com'
        return {
            'enabled': True,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': sender_email,
            'sender_name': 'Fishing Predictor Pro',
            'use_tls': True
        }
    
    def check_email_config(self):
        """Vérifie la configuration email de manière silencieuse"""
        try:
            has_gmail_user = bool(self.GMAIL_USER and '@' in self.GMAIL_USER)
            has_gmail_pass = bool(self.GMAIL_APP_PASSWORD and len(self.GMAIL_APP_PASSWORD) >= 8)
            
            return {
                'email_system_ready': has_gmail_user and has_gmail_pass,
                'gmail_user_configured': has_gmail_user,
                'gmail_password_configured': has_gmail_pass,
                'sender_email': self.GMAIL_USER if has_gmail_user else None
            }
        except:
            return {'email_system_ready': False}
    
    @classmethod
    def validate_config(cls):
        """Valide que toutes les configurations requises sont présentes"""
        print("\n" + "="*50)
        print("🔧 VALIDATION DE LA CONFIGURATION")
        print("="*50)
        
        # Vérification critique des emails
        print(f"📧 GMAIL_USER: {'✅ ' + cls.GMAIL_USER if cls.GMAIL_USER else '❌ MANQUANT'}")
        print(f"🔑 GMAIL_APP_PASSWORD: {'✅ ' + ('*' * 8) if cls.GMAIL_APP_PASSWORD else '❌ MANQUANT'}")
        
        required_vars = ['GMAIL_USER', 'GMAIL_APP_PASSWORD', 'SECRET_KEY']
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            print(f"\n🚨 Variables manquantes: {', '.join(missing)}")
            print("   ⚠️ Les emails NE fonctionneront PAS sans ces variables")
            return False
        
        # Vérifier les APIs
        print("\n📡 APIs DISPONIBLES:")
        apis = [
            ('OpenWeather', cls.OPENWEATHER_API_KEY),
            ('StormGlass', cls.STORMGLASS_API_KEY),
            ('WorldTides', cls.WORLDTIDES_API_KEY),
            ('MeteoConcept', cls.METEO_CONCEPT_TOKEN),
        ]
        
        for name, key in apis:
            print(f"   {name}: {'✅' if key else '❌'}")
        
        print("="*50 + "\n")
        return True

# Instance de configuration
config = Config()
