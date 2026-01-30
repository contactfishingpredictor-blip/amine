"""
Configuration centrale sécurisée pour Fishing Predictor Pro
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration de base"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Email Configuration (Gmail)
    GMAIL_USER = os.getenv('GMAIL_USER')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    
    # API Keys - TOUTES LES CLÉS
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    STORMGLASS_API_KEY = os.getenv('STORMGLASS_API_KEY')
    WORLDTIDES_API_KEY = os.getenv('WORLDTIDES_API_KEY')
    METEO_CONCEPT_TOKEN = os.getenv('METEO_CONCEPT_TOKEN')
    WEKEO_API_TOKEN = os.getenv('WEKEO_API_TOKEN')
    
    # URLs d'API
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    STORMGLASS_URL = "https://api.stormglass.io/v2"
    WORLDTIDES_URL = "https://www.worldtides.info/api/v3"
    METEO_CONCEPT_URL = "https://api.meteo-concept.com/api"
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/fishing.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    CACHE_DIR = os.path.join(BASE_DIR, 'api_cache')
    TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
    STATIC_DIR = os.path.join(BASE_DIR, 'static')
    
    # Files
    FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')
    ALERTS_FILE = os.path.join(DATA_DIR, 'alerts_subscriptions.json')
    EMAIL_LOGS_FILE = os.path.join(DATA_DIR, 'email_logs.json')
    
    # API Rate Limits
    API_LIMITS = {
        'openweather': {'max_per_day': 1000, 'cache_duration': 30*60},
        'stormglass': {'max_per_day': 10, 'cache_duration': 6*60*60},
        'worldtides': {'max_per_day': 10, 'cache_duration': 6*60*60},
        'nominatim': {'max_per_hour': 1, 'cache_duration': 24*60*60},
        'emodnet': {'max_per_hour': 10, 'cache_duration': 7*24*60*60},
        'openmeteo': {'max_per_hour': 100, 'cache_duration': 30*60},
        'meteoconcept': {'max_per_day': 100, 'cache_duration': 60*60}
    }
    
    # Email Configuration
    EMAIL_CONFIG = {
        'enabled': True,
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': GMAIL_USER,
        'sender_name': 'Fishing Predictor Pro',
        'use_tls': True
    }
    
    # Weather Cache
    WEATHER_CACHE_DURATION = 30 * 60  # 30 minutes
    
    # Application
    APP_NAME = "Fishing Predictor Pro"
    APP_VERSION = "2.1.0"  # Mise à jour version
    
    # Constantes scientifiques
    SEAWATER_DENSITY = 1025  # kg/m³ (Méditerranée)
    SALINITY_MEDITERRANEAN = 38.0  # g/L
    ATMOSPHERIC_PRESSURE_SEA = 1013.25  # hPa
    
    @classmethod
    def validate_config(cls):
        """Valide que toutes les configurations requises sont présentes"""
        required_vars = ['GMAIL_USER', 'GMAIL_APP_PASSWORD', 'SECRET_KEY']
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Variables d'environnement manquantes: {', '.join(missing)}")
        
        # Vérifier les APIs disponibles
        available_apis = []
        if cls.OPENWEATHER_API_KEY: available_apis.append("OpenWeather")
        if cls.STORMGLASS_API_KEY: available_apis.append("StormGlass")
        if cls.METEO_CONCEPT_TOKEN: available_apis.append("MeteoConcept")
        if cls.WORLDTIDES_API_KEY: available_apis.append("WorldTides")
        
        print(f"📡 APIs disponibles: {', '.join(available_apis) if available_apis else 'Aucune (mode simulé)'}")
        
        return True

# Instance de configuration
config = Config()