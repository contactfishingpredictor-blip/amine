"""Fishing Predictor Pro - Application Flask principale (Version scientifique corrigée)"""
import os
import json
import logging
import sys
import time
import math
import hashlib
import random
import concurrent.futures
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, redirect
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from advanced_predictor import ScientificFishingPredictor
from config import config

# ===== IMPORT BATHYMÉTRIE GEBCO (AJOUTÉ EN HAUT) =====
try:
    from bathymetry_gebco import gebco
    BATHYMETRY_ENABLED = True
    print("✅ Module bathymétrie GEBCO chargé")
except ImportError as e:
    BATHYMETRY_ENABLED = False
    print(f"⚠️ Module bathymétrie non disponible: {e}")
except Exception as e:
    BATHYMETRY_ENABLED = False
    print(f"⚠️ Erreur chargement bathymétrie: {e}")

# ===== CONFIGURATION SILENCIEUSE =====
logging.basicConfig(level=logging.WARNING)
logging.getLogger('wekeo_handler').setLevel(logging.ERROR)
logging.getLogger('__main__').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('hda').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('requests').setLevel(logging.ERROR)

# ===== DONNÉES OCÉANOGRAPHIQUES RÉELLES =====
try:
    from real_ocean_data import real_ocean
    REAL_OCEAN_ENABLED = True
    print("✅ Module données océanographiques réelles chargé")
except ImportError as e:
    REAL_OCEAN_ENABLED = False
    print(f"⚠️ Real ocean data module not available: {e}")

# ===== INTÉGRATION WEKEO =====
try:
    from wekeo_handler import get_wind_data, test_connection

    class WekeoEnhancerSimple:
        def get_wind_data(self, lat, lon):
            return get_wind_data(lat, lon)
        def test_connection(self):
            return test_connection()

    wekeo_enhancer = WekeoEnhancerSimple()
    WEKEO_ENABLED = True
    print("✅ Module WEkEO chargé - Prêt pour données réelles")
except ImportError as e:
    WEKEO_ENABLED = False
    print(f"⚠️ Module WEkEO non disponible: {e}")
except Exception as e:
    WEKEO_ENABLED = False
    print(f"⚠️ Erreur chargement WEkEO: {e}")

app = Flask(__name__, template_folder='templates', static_folder='static')
predictor = ScientificFishingPredictor()

# ===== CONFIGURATION EMAIL GMAIL UNIQUEMENT =====
GMAIL_USER = config.GMAIL_USER
GMAIL_PASSWORD = config.GMAIL_APP_PASSWORD
EMAIL_FROM = config.EMAIL_FROM
EMAIL_FROM_NAME = config.EMAIL_FROM_NAME

# ===== API KEYS =====
OPENWEATHER_API_KEY = config.OPENWEATHER_API_KEY
STORMGLASS_API_KEY = config.STORMGLASS_API_KEY
WORLDTIDES_API_KEY = config.WORLDTIDES_API_KEY
NOMINATIM_API = "https://nominatim.openstreetmap.org/reverse"
FAVORITES_FILE = config.FAVORITES_FILE
ALERTS_FILE = config.ALERTS_FILE
EMAIL_LOGS_FILE = config.EMAIL_LOGS_FILE

# ===== CONFIGURATION DE LIMITATION D'APPELS API =====
API_RATE_LIMITS = {
    'openweather': {'max_per_hour':60,'max_per_day':1000,'cache_duration':30*60,'use_cache_only':False,'count_today':0,'last_reset':None},
    'stormglass': {'max_per_day':10,'cache_duration':6*60*60,'use_cache_only':True},
    'worldtides': {'max_per_day':10,'cache_duration':6*60*60,'use_cache_only':True},
    'nominatim': {'max_per_hour':1,'cache_duration':24*60*60,'use_cache_only':False},
    'emodnet': {'max_per_hour':10,'cache_duration':7*24*60*60,'use_cache_only':True}
}

# ===== SYSTÈME DE CACHE PERSISTANT SUR DISQUE =====
CACHE_DIR = config.CACHE_DIR
os.makedirs(CACHE_DIR, exist_ok=True)

def save_to_cache(api_name: str, params: dict, data: dict, duration_hours: int = 24):
    """Sauvegarde les données dans un cache persistant sur disque"""
    try:
        param_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(f"{api_name}_{param_str}".encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{api_name}_{cache_key}.json")
        cache_data = {'data':data,'timestamp':time.time(),'expires_at':time.time()+(duration_hours*3600),'api_name':api_name,'params':params}
        with open(cache_file, 'w', encoding='utf-8') as f: json.dump(cache_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde cache: {e}")
        return False

def load_from_cache(api_name: str, params: dict, max_age_hours: int = 24):
    """Charge les données depuis le cache persistant"""
    try:
        param_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(f"{api_name}_{param_str}".encode()).hexdigest()
        cache_file = os.path.join(CACHE_DIR, f"{api_name}_{cache_key}.json")
        if not os.path.exists(cache_file): return None
        with open(cache_file, 'r', encoding='utf-8') as f: cache_data = json.load(f)
        current_time = time.time()
        if current_time > cache_data.get('expires_at', 0):
            os.remove(cache_file); return None
        cache_age = current_time - cache_data.get('timestamp', 0)
        if cache_age > max_age_hours * 3600: return None
        return cache_data['data']
    except Exception: return None

# ===== CACHE MÉMOIRE POUR DONNÉES FRÉQUEMMENT UTILISÉES =====
weather_cache = {}
WEATHER_CACHE_DURATION = config.WEATHER_CACHE_DURATION
WEATHER_CONDITIONS_FR = {'Clear':'Ciel dégagé','Sunny':'Ensoleillé','Clouds':'Nuageux','Cloudy':'Nuageux','Rain':'Pluie','Drizzle':'Bruine','Thunderstorm':'Orage','Snow':'Neige','Mist':'Brume','Fog':'Brouillard','Haze':'Brume','Dust':'Poussiéreux','Smoke':'Fumée','Ash':'Cendres','Squall':'Rafales','Tornado':'Tornade'}

# ===== CACHE SERVEUR (3 heures) =====
SERVER_CACHE = {}
CACHE_DURATION = 3 * 60 * 60  # 3 heures en secondes

def get_cached(key, compute_func, max_age=CACHE_DURATION):
    """Récupère depuis le cache ou calcule"""
    import time
    now = time.time()

    if key in SERVER_CACHE:
        data, timestamp = SERVER_CACHE[key]
        if now - timestamp < max_age:
            return data, True

    data = compute_func()
    SERVER_CACHE[key] = (data, now)
    return data, False

# ===== FONCTIONS EMAIL GMAIL UNIQUEMENT =====
def send_confirmation_email(email: str, confirmation_id: str) -> bool:
    """Envoie un email de confirmation d'abonnement via Gmail"""
    try: return send_confirmation_email_gmail(email, confirmation_id)
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}"); return False

def send_confirmation_email_gmail(email: str, confirmation_id: str) -> bool:
    """Envoie un email de confirmation d'abonnement via Gmail"""
    try:
        if not GMAIL_USER or not GMAIL_PASSWORD:
            print("❌ Configuration Gmail manquante"); return False
        timestamp = datetime.now().strftime('%d/%m/%Y à %H:%M')
        html_content = f"""
        <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Confirmation d'abonnement - Fishing Predictor Pro</title><style>body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;max-width:600px;margin:0 auto;padding:20px;}}.header{{background:linear-gradient(135deg,#f59e0b 0%,#d97706 100%);color:white;padding:30px;text-align:center;border-radius:10px 10px 0 0;}}.content{{background:#f8fafc;padding:30px;border-radius:0 0 10px 10px;}}.button{{display:inline-block;background:#3b82f6;color:white;padding:12px 24px;text-decoration:none;border-radius:5px;font-weight:bold;margin:10px 0;}}.footer{{text-align:center;margin-top:30px;padding-top:20px;border-top:1px solid #e2e8f0;color:#64748b;font-size:0.9em;}}.confirmation-id{{background:#e0f2fe;padding:15px;border-radius:5px;font-family:monospace;font-weight:bold;text-align:center;margin:20px 0;}}</style></head><body>
        <div class="header"><h1>🎣 Fishing Predictor Pro</h1><h2>Confirmation d'abonnement</h2></div><div class="content"><p>Bonjour,</p><p>Merci de vous être abonné aux alertes de pêche de <strong>Fishing Predictor Pro</strong> !</p><p><strong>✅ Votre abonnement a été confirmé avec succès.</strong></p><div class="confirmation-id">ID de confirmation : {confirmation_id}<br>Date : {timestamp}</div><p>Vous recevrez désormais des alertes par email lorsque :</p><ul><li>🎯 Les conditions de pêche seront excellentes (score ≥ 85%)</li><li>🌸 Les saisons de pêche changent</li><li>📅 Des événements de pêche spéciaux sont prévus</li></ul><p style="text-align: center;"><a href="https://fishing-activity.onrender.com" class="button">Consulter les prédictions</a></p><p><strong>Pour gérer vos préférences ou vous désabonner :</strong><br>Visitez la page <a href="https://fishing-activity.onrender.com/alerts">Alertes Intelligentes</a> ou cliquez sur le lien de désabonnement présent dans chaque email.</p><p>Bonne pêche ! 🐟</p><p><em>L'équipe Fishing Predictor Pro</em></p></div><div class="footer"><p>Cet email a été envoyé à {email}</p><p>© 2024 Fishing Predictor Pro - Tous droits réservés</p><p><small>Vous recevez cet email car vous vous êtes abonné aux alertes sur notre site.</small></p></div></body></html>"""
        text_content = f"Confirmation d'abonnement - Fishing Predictor Pro\n\nBonjour,\n\nMerci de vous être abonné aux alertes de pêche de Fishing Predictor Pro !\n\n✅ Votre abonnement a été confirmé avec succès.\n\nID de confirmation : {confirmation_id}\nDate : {timestamp}\n\nVous recevrez désormais des alertes par email lorsque les conditions de pêche seront excellentes.\n\nPour gérer vos préférences ou vous désabonner :\nVisitez https://fishing-activity.onrender.com/alerts ou cliquez sur le lien de désabonnement présent dans chaque email.\n\nBonne pêche !\n\nL'équipe Fishing Predictor Pro\n\n---\nCet email a été envoyé à {email}\n© 2026 Fishing Predictor Pro"
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg['To'] = email
        msg['Subject'] = "🎣 Confirmation d'abonnement aux alertes - Fishing Predictor Pro"
        if text_content: msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
        server.ehlo(); server.starttls(); server.ehlo()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg); server.quit()
        save_email_log(email, 'confirmation', confirmation_id, True)
        print(f"✅ Email de confirmation envoyé à {email}"); return True
    except Exception as e:
        print(f"❌ Erreur envoi email Gmail: {e}")
        save_email_log(email, 'confirmation', confirmation_id, False); return False

def test_gmail_configuration():
    """Teste la connexion SMTP Gmail avec les credentials configurés."""
    if not GMAIL_USER or not GMAIL_PASSWORD:
        print("⚠️ Configuration Gmail incomplète (utilisateur ou mot de passe manquant)")
        return False
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.quit()
        print("✅ Connexion Gmail SMTP réussie")
        return True
    except Exception as e:
        print(f"⚠️ Échec du test Gmail SMTP : {e}")
        return False

def save_email_log(email: str, email_type: str, confirmation_id: str, sent: bool):
    """Sauvegarde les logs d'emails envoyés"""
    try:
        os.makedirs(os.path.dirname(EMAIL_LOGS_FILE), exist_ok=True)
        logs = []
        if os.path.exists(EMAIL_LOGS_FILE):
            with open(EMAIL_LOGS_FILE, 'r', encoding='utf-8') as f: logs = json.load(f)
        log_entry = {'to':email,'type':email_type,'confirmation_id':confirmation_id,'sent':sent,'timestamp':datetime.now().isoformat(),'server':'Gmail SMTP'}
        logs.append(log_entry)
        with open(EMAIL_LOGS_FILE, 'w', encoding='utf-8') as f: json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"⚠️ Erreur sauvegarde log email: {e}")

# ===== FONCTIONS MÉTÉO AVEC CACHE =====
def get_openweather_data_with_limits(lat: float, lon: float):
    """Récupère les données météo avec gestion des limites d'API"""
    params = {'lat': lat, 'lon': lon}
    cached_data = load_from_cache('openweather', params, max_age_hours=1)
    if cached_data: return {'success': True, 'weather': cached_data, 'source': 'cache'}
    limits = API_RATE_LIMITS['openweather']
    if limits.get('use_cache_only', False): return get_fallback_weather_data(lat, lon)
    if limits['count_today'] >= limits['max_per_day']: return get_fallback_weather_data(lat, lon)
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params_api = {'lat':lat,'lon':lon,'appid':OPENWEATHER_API_KEY,'units':'metric','lang':'fr'}
        response = requests.get(url, params=params_api, timeout=5)
        if response.status_code == 200:
            data = response.json()
            API_RATE_LIMITS['openweather']['count_today'] += 1
            wind_deg = data['wind'].get('deg', 0)
            wind_direction = get_wind_direction_name(wind_deg)
            wind_impact = get_wind_fishing_impact(wind_deg, lat, lon)

            # Calcul avancé de la hauteur des vagues
            wind_speed_kmh = data['wind']['speed'] * 3.6
            wave_height = calculate_wave_height(wind_speed_kmh)

            weather_info = {
                'temperature':data['main']['temp'],
                'feels_like':data['main']['feels_like'],
                'pressure':data['main']['pressure'],
                'humidity':data['main']['humidity'],
                'wind_speed':wind_speed_kmh,
                'wind_direction':wind_deg,
                'wind_direction_abbr':wind_direction['abbreviation'],
                'wind_direction_name':wind_direction['name'],
                'wind_direction_icon':wind_direction['icon'],
                'wind_fishing_impact':wind_impact,
                'wind_offshore': False,
                'wind_onshore':is_wind_onshore(lat, lon, wind_deg),
                'wave_height': round(wave_height, 2),
                'condition':data['weather'][0]['main'],
                'condition_description':data['weather'][0]['description'],
                'condition_fr':WEATHER_CONDITIONS_FR.get(data['weather'][0]['main'], data['weather'][0]['main']),
                'icon':data['weather'][0]['icon'],
                'clouds':data['clouds']['all'],
                'visibility':data.get('visibility', 10000)/1000,
                'sunrise':datetime.fromtimestamp(data['sys']['sunrise']).isoformat(),
                'sunset':datetime.fromtimestamp(data['sys']['sunset']).isoformat(),
                'location':data['name'],
                'country':data['sys']['country'],
                'timestamp':datetime.now().isoformat(),
                'score':calculate_weather_score({'temperature':data['main']['temp'],'wind_speed':wind_speed_kmh,'pressure':data['main']['pressure'],'condition':data['weather'][0]['main'],'wind_direction':wind_deg})
            }
            save_to_cache('openweather', {'lat': lat, 'lon': lon}, weather_info, 12)
            return {'success': True, 'weather': weather_info, 'source': 'api'}
        elif response.status_code == 429:
            API_RATE_LIMITS['openweather']['use_cache_only'] = True
            return get_fallback_weather_data(lat, lon)
        else: return get_fallback_weather_data(lat, lon)
    except Exception as e: return get_fallback_weather_data(lat, lon)

def get_fallback_weather_data(lat: float, lon: float): return generate_consistent_weather(lat, lon)

def get_wind_direction_name(degrees: float) -> dict:
    """Convertit les degrés en direction du vent"""
    directions = [('N','Nord',0,11.25),('NNE','Nord-Nord-Est',11.25,33.75),('NE','Nord-Est',33.75,56.25),('ENE','Est-Nord-Est',56.25,78.75),('E','Est',78.75,101.25),('ESE','Est-Sud-Est',101.25,123.75),('SE','Sud-Est',123.75,146.25),('SSE','Sud-Sud-Est',146.25,168.75),('S','Sud',168.75,191.25),('SSO','Sud-Sud-Ouest',191.25,213.75),('SO','Sud-Ouest',213.75,236.25),('OSO','Ouest-Sud-Ouest',236.25,258.75),('O','Ouest',258.75,281.25),('ONO','Ouest-Nord-Ouest',281.25,303.75),('NO','Nord-Ouest',303.75,326.25),('NNO','Nord-Nord-Ouest',326.25,348.75),('N','Nord',348.75,360)]
    degrees = degrees % 360
    for abbrev, name, min_deg, max_deg in directions:
        if min_deg <= degrees <= max_deg:
            return {'abbreviation':abbrev,'name':name,'degrees':degrees,'icon':get_wind_direction_icon(degrees)}
    return {'abbreviation':'N','name':'Nord','degrees':degrees,'icon':'⬆️'}

def get_wind_direction_icon(degrees: float) -> str:
    """Retourne un emoji pour la direction du vent"""
    if 337.5 <= degrees <= 360 or 0 <= degrees < 22.5: return '⬆️'
    elif 22.5 <= degrees < 67.5: return '↗️'
    elif 67.5 <= degrees < 112.5: return '➡️'
    elif 112.5 <= degrees < 157.5: return '↘️'
    elif 157.5 <= degrees < 202.5: return '⬇️'
    elif 202.5 <= degrees < 247.5: return '↙️'
    elif 247.5 <= degrees < 292.5: return '⬅️'
    else: return '↖️'

def get_wind_fishing_impact(degrees: float, spot_lat: float = 36.8, spot_lon: float = 10.1) -> str:
    """Détermine l'impact du vent sur la pêche selon la direction"""
    direction = get_wind_direction_name(degrees); abbrev = direction['abbreviation']
    if abbrev in ['N', 'NNE', 'NE']: return "Vent de nord - Bon pour la pêche côtière, apporte des nutriments"
    elif abbrev in ['E', 'ENE', 'ESE']: return "Vent d'est - Peut rendre la mer agitée, prudence"
    elif abbrev in ['S', 'SSE', 'SSO']: return "Vent du sud - Chaud, peut réduire l'activité des poissons"
    elif abbrev in ['O', 'ONO', 'OSO']: return "Vent d'ouest - Favorable pour le surfcasting"
    elif abbrev in ['NO', 'NNO']: return "Vent de nord-ouest - Excellent pour la pêche, mer claire"
    elif abbrev in ['SO', 'SE']: return "Vent de sud/sud-est - Apporte eaux chaudes, bon pour certaines espèces"
    else: return "Direction variable - Conditions moyennes"

def is_wind_offshore(lat, lon, wind_direction):
    """Fonction désactivée - retourne toujours False"""
    return False

def is_wind_onshore(lat, lon, wind_direction):
    """Vent onshore = vent qui souffle de la mer vers la terre"""
    # En Tunisie, la mer est à l'EST, donc vent d'est = onshore
    return (0 <= wind_direction <= 90) or (270 <= wind_direction <= 360)

def get_cached_weather(lat: float, lon: float, force_refresh: bool = False):
    """Récupère les données météo avec cache intelligent et limitation"""
    cache_key = f"{lat:.4f}_{lon:.4f}"; now = time.time()
    if not force_refresh and cache_key in weather_cache:
        cached_data, timestamp = weather_cache[cache_key]
        if now - timestamp < WEATHER_CACHE_DURATION: return cached_data
    weather_result = get_openweather_data_with_limits(lat, lon)
    if weather_result['success']: weather_cache[cache_key] = (weather_result, now)
    return weather_result

def generate_consistent_weather(lat: float, lon: float):
    """Génère des données météo COHÉRENTES basées sur la position et la date (pas l'heure)"""
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    # Utiliser seulement la date, pas l'heure, pour la stabilité
    stable_key = f"{lat:.2f}_{lon:.2f}_{day_of_year}"
    stable_hash = int(hashlib.md5(stable_key.encode()).hexdigest()[:8], 16)

    base_temp = 20 + (36.8 - lat) * 0.5
    # Variation diurne approximative mais cohérente
    temp = base_temp + 5  # température moyenne de jour

    month = now.month
    if 6 <= month <= 8: temp += 8
    elif 3 <= month <= 5: temp += 4
    elif 9 <= month <= 11: temp += 2

    # Vent basé sur la position et la date (stable)
    wind = 8 + (stable_hash % 15)
    pressure = 1015 + (stable_hash % 20) - 10

    condition_index = (stable_hash // 1000) % 4
    conditions = ['Clear', 'Clouds', 'Partly Cloudy', 'Mostly Sunny']
    conditions_fr = ['Ciel dégagé', 'Nuageux', 'Partiellement nuageux', 'Très ensoleillé']

    wave_height = calculate_wave_height(wind)

    # Direction basée sur la position (stable)
    base_direction = (lon * 10 + lat * 5) % 360
    wind_direction = (base_direction + (stable_hash % 30) - 15) % 360

    wind_direction_info = get_wind_direction_name(wind_direction)
    wind_impact = get_wind_fishing_impact(wind_direction, lat, lon)

    weather_info = {
        'temperature':round(temp,1),
        'feels_like':round(temp-2,1),
        'pressure':round(pressure,1),
        'humidity':60 + (stable_hash % 30),
        'wind_speed':round(wind,1),
        'wind_direction':wind_direction,
        'wind_direction_abbr':wind_direction_info['abbreviation'],
        'wind_direction_name':wind_direction_info['name'],
        'wind_direction_icon':wind_direction_info['icon'],
        'wind_fishing_impact':wind_impact,
        'wind_offshore': False,
        'wind_onshore':is_wind_onshore(lat,lon,wind_direction),
        'wave_height': round(wave_height, 1),
        'condition':conditions[condition_index],
        'condition_description':conditions[condition_index].lower(),
        'condition_fr':conditions_fr[condition_index],
        'icon':'02d',
        'clouds':20+condition_index*20,
        'visibility':10,
        'sunrise':(now.replace(hour=6,minute=30,second=0)).isoformat(),
        'sunset':(now.replace(hour=18,minute=45,second=0)).isoformat(),
        'location':f'Position ({lat:.2f}, {lon:.2f})',
        'country':'TN',
        'timestamp':now.isoformat(),
        'score':0.7 + (stable_hash % 100)/500,
        'turbidity':1.0+condition_index*0.2,
        'source':'modèle cohérent',
        'stable_id':stable_key
    }
    return {'success': True, 'weather': weather_info}

def calculate_wave_height(wind_speed_kmh: float) -> float:
    """Calcule la hauteur des vagues en fonction de la vitesse du vent (km/h)"""
    if wind_speed_kmh < 10:
        return 0.2
    elif wind_speed_kmh < 20:
        return 0.2 + (wind_speed_kmh - 10) * 0.04
    elif wind_speed_kmh < 30:
        return 0.6 + (wind_speed_kmh - 20) * 0.06
    elif wind_speed_kmh < 40:
        return 1.2 + (wind_speed_kmh - 30) * 0.08
    elif wind_speed_kmh < 50:
        return 2.0 + (wind_speed_kmh - 40) * 0.10
    elif wind_speed_kmh < 60:
        return 3.0 + (wind_speed_kmh - 50) * 0.12
    else:
        return 4.2 + (wind_speed_kmh - 60) * 0.15

def get_real_bathymetry(lat: float, lon: float) -> dict:
    """Bathymétrie précise - GEBCO 2025 500m + TES spots"""
    try:
        if BATHYMETRY_ENABLED:
            result = gebco.get_depth_with_fallback(lat, lon)
            result['seabed_type'] = estimate_seabed_type(lat, lon, result['depth'])
            seabed_desc = {
                'sand': 'Sableux',
                'rock': 'Rocheux',
                'grass': 'Herbier',
                'mixed': 'Mixte',
                'mud': 'Vaseux'
            }
            result['seabed_description'] = seabed_desc.get(
                result['seabed_type'],
                'Mixte'
            )
            result['success'] = True
            result['accuracy'] = result.get('accuracy', 'haute')
            return result
        else:
            # Fallback si module non disponible
            return {
                'success': True,
                'depth': 20.0,
                'seabed_type': 'mixed',
                'seabed_description': 'Mixte',
                'source': 'Modèle par défaut (module non chargé)',
                'accuracy': 'basse',
                'confidence': 0.5
            }
    except Exception as e:
        print(f"⚠️ Erreur bathymétrie GEBCO: {e}")
        return {
            'success': True,
            'depth': 20.0,
            'seabed_type': 'mixed',
            'seabed_description': 'Mixte',
            'source': 'Modèle par défaut',
            'accuracy': 'basse',
            'confidence': 0.5
        }

def estimate_seabed_type(lat: float, lon: float, depth: float) -> str:
    """Estimation du type de fond selon les zones Tunisie"""
    if 36.8 <= lat <= 37.0 and 10.9 <= lon <= 11.2:
        return 'rock'
    if 36.92 <= lat <= 36.98 and 8.72 <= lon <= 8.80:
        return 'rock'
    if 37.25 <= lat <= 37.30 and 9.85 <= lon <= 9.90:
        return 'rock'
    if 36.84 <= lat <= 36.86 and 11.08 <= lon <= 11.10:
        return 'rock'
    if depth < 10 and 35.7 <= lat <= 35.9 and 10.8 <= lon <= 11.0:
        return 'grass'
    if 37.15 <= lat <= 37.18 and 10.17 <= lon <= 10.20:
        return 'grass'
    if depth < 15:
        return 'sand'
    if 35.8 <= lat <= 36.5 and 10.5 <= lon <= 10.7:
        return 'sand'
    if depth > 50:
        return 'mud'
    return 'mixed'

def get_tide_data_with_cache(lat: float, lon: float) -> dict:
    """Récupère les données de marée - VERSION CORRIGÉE"""
    params = {'lat': lat, 'lon': lon}
    cached_data = load_from_cache('worldtides', params, max_age_hours=6)
    if cached_data: return cached_data
    fallback_data = get_fallback_tide_data(lat, lon)
    save_to_cache('worldtides', params, fallback_data, 6)
    return fallback_data

def get_fallback_tide_data(lat: float, lon: float) -> dict:
    """Données de marée de secours - AMÉLIORÉE"""
    now = datetime.now(); today = now.date()
    start_time = datetime(today.year, today.month, today.day, 0, 0, 0)
    start_timestamp = int(start_time.timestamp())
    base_height = 0.5; amplitude = 0.3; lon_offset = lon / 15.0
    heights = []; extremes = []
    for i in range(48):
        current_time = start_timestamp + i * 1800; hours_from_midnight = i * 0.5
        tide_progress = (hours_from_midnight + lon_offset) / 12.4
        height = base_height + amplitude * math.sin(2 * math.pi * tide_progress)
        heights.append({'dt':current_time,'date':datetime.fromtimestamp(current_time).isoformat()+'+01:00','height':round(height,2)})
    for cycle in range(4):
        cycle_start = cycle * 6.2; max_height = -999; max_hour = cycle_start
        for offset in range(-5, 6):
            check_hour = cycle_start + offset * 0.5
            if 0 <= check_hour < 24:
                idx = int(check_hour * 2)
                if idx < len(heights) and heights[idx]['height'] > max_height:
                    max_height = heights[idx]['height']; max_hour = check_hour
        high_tide_time = start_timestamp + int(max_hour * 3600)
        extremes.append({'dt':high_tide_time,'date':datetime.fromtimestamp(high_tide_time).isoformat()+'+01:00','height':round(max_height,2),'type':'High'})
        low_hour = cycle_start + 3.1; min_height = 999; min_hour = low_hour
        for offset in range(-5, 6):
            check_hour = low_hour + offset * 0.5
            if 0 <= check_hour < 24:
                idx = int(check_hour * 2)
                if idx < len(heights) and heights[idx]['height'] < min_height:
                    min_height = heights[idx]['height']; min_hour = check_hour
        low_tide_time = start_timestamp + int(min_hour * 3600)
        extremes.append({'dt':low_tide_time,'date':datetime.fromtimestamp(low_tide_time).isoformat()+'+01:00','height':round(min_height,2),'type':'Low'})
    extremes.sort(key=lambda x: x['dt'])
    if len(extremes) > 4: extremes = extremes[:4]
    return {'status':200,'heights':heights,'extremes':extremes,'callCount':0,'copyright':'Modèle de marée méditerranéenne - Fishing Predictor Pro','requestLat':lat,'requestLon':lon,'responseLat':lat,'responseLon':lon,'datum':'CD','timezone':'Africa/Tunis','model':'semi-diurnal','amplitude':round(amplitude,2),'mean_height':round(base_height,2)}

def get_location_name_with_cache(lat: float, lon: float) -> dict:
    """Récupère le nom de localisation avec cache"""
    params = {'lat': lat, 'lon': lon}
    cached_data = load_from_cache('nominatim', params, max_age_hours=24)
    if cached_data: return cached_data
    if API_RATE_LIMITS['nominatim'].get('use_cache_only', False): return get_fallback_location_data(lat, lon)
    try:
        url = NOMINATIM_API
        params_api = {'lat':lat,'lon':lon,'format':'json','zoom':10,'addressdetails':1}
        headers = {'User-Agent': 'FishingPredictorPro/1.0'}
        response = requests.get(url, params=params_api, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            result = {'success':True,'name':data.get('display_name', f'Position {lat:.4f}, {lon:.4f}'),'address':data.get('address', {}),'type':data.get('type', 'water')}
            save_to_cache('nominatim', params, result, 24); return result
    except Exception as e: print(f"⚠️ Erreur Nominatim: {e}")
    return get_fallback_location_data(lat, lon)

def get_fallback_location_data(lat: float, lon: float) -> dict:
    """Données de localisation de secours"""
    if lat > 37.0: region = 'Nord Tunisie'
    elif lat > 36.0: region = 'Tunis'
    elif lat > 35.0: region = 'Sahel'
    else: region = 'Sud Tunisie'
    return {'success':True,'name':f'Position près de {region} ({lat:.4f}, {lon:.4f})','type':'water','address':{'state':region,'country':'Tunisie'}}

def calculate_weather_score(weather_data: dict) -> float:
    """Calcule un score de 0-1 pour la pêche basé sur la météo RÉELLE"""
    score = 0.7; temp = weather_data.get('temperature', 20)
    if 15 <= temp <= 25: score += 0.2
    elif 10 <= temp <= 30: score += 0.1
    else: score -= 0.1
    wind_speed = weather_data.get('wind_speed', 10)
    if wind_speed < 20: score += 0.1
    elif wind_speed > 30: score -= 0.2
    pressure = weather_data.get('pressure', 1015)
    if 1010 <= pressure <= 1020: score += 0.1
    condition = weather_data.get('condition', 'Clear')
    if 'Rain' not in condition and 'Thunderstorm' not in condition: score += 0.1
    wave_height = weather_data.get('wave_height', 0.5)
    if wave_height < 1.0: score += 0.1
    elif wave_height > 1.5: score -= 0.1
    wind_direction = weather_data.get('wind_direction', 0)
    if is_wind_offshore(36.8, 10.1, wind_direction): score -= 0.2
    return min(1.0, max(0.3, score))

def calculate_depth_factor(depth: float, species: str) -> float:
    species_depths = {'loup':[3,20],'daurade':[2,15],'pageot':[10,60],'thon':[10,100],'sar':[5,25],'mulet':[1,10],'marbré':[2,15],'rouget':[5,30],'sériole':[10,50],'bonite':[5,40]}
    optimal_range = species_depths.get(species, [5, 20])
    min_depth, max_depth = optimal_range
    if min_depth <= depth <= max_depth: return 1.0
    elif depth < min_depth:
        distance = min_depth - depth; return max(0.5, 1.0 - (distance / min_depth * 0.5))
    else:
        distance = depth - max_depth; return max(0.5, 1.0 - (distance / max_depth * 0.5))

def get_optimal_depth(species: str) -> str:
    depths = {'loup':"3-20m",'daurade':"2-15m",'pageot':"10-60m",'thon':"10-100m",'sar':"5-25m",'mulet':"1-10m",'marbré':"2-15m",'rouget':"5-30m",'sériole':"10-50m",'bonite':"5-40m"}
    return depths.get(species, "5-20m")

def get_optimal_seabed(species: str) -> str:
    seabeds = {'loup':"rocheux/mixte",'daurade':"sable/herbier",'pageot':"rocheux",'thon':"pélagique",'sar':"rocheux",'mulet':"sable",'marbré':"sable",'rouget':"sable/vasard",'sériole':"mixte",'bonite':"pélagique"}
    return seabeds.get(species, "mixte")

def get_next_high_tide(tide_data) -> dict:
    if 'extremes' in tide_data:
        for extreme in tide_data['extremes']:
            if extreme.get('type') == 'High':
                return {'time':datetime.fromtimestamp(extreme['dt']).strftime('%H:%M'),'height':extreme['height']}
    return {'time':'N/A','height':0}

def get_next_low_tide(tide_data) -> dict:
    if 'extremes' in tide_data:
        for extreme in tide_data['extremes']:
            if extreme.get('type') == 'Low':
                return {'time':datetime.fromtimestamp(extreme['dt']).strftime('%H:%M'),'height':extreme['height']}
    return {'time':'N/A','height':0}

def get_marine_data_multi_source(lat: float, lon: float) -> dict:
    """Version utilisant notre nouveau handler de données réelles"""
    marine_data = {
        'water_temperature': None,
        'chlorophyll': None,
        'current_speed': None,
        'salinity': config.SALINITY_MEDITERRANEAN,
        'wind_speed_kmh': None,
        'wind_direction_deg': None,
        'wave_height': None,
        'dissolved_oxygen': None,
        'data_quality': 'real',
        'data_source': 'open-meteo'
    }

    try:
        # Utiliser notre nouveau handler
        from wekeo_handler import get_water_temperature, get_chlorophyll, get_ocean_current, get_wave_height, get_dissolved_oxygen

        # Récupérer les données réelles
        temp_data = get_water_temperature(lat, lon)
        if temp_data and 'value' in temp_data:
            marine_data['water_temperature'] = temp_data['value']
            marine_data['data_quality'] = temp_data.get('quality', 'high')
            marine_data['data_source'] = temp_data.get('source', 'open-meteo')

        chl_data = get_chlorophyll(lat, lon)
        if chl_data and 'value' in chl_data:
            marine_data['chlorophyll'] = chl_data['value']

        current_data = get_ocean_current(lat, lon)
        if current_data and 'speed_ms' in current_data:
            marine_data['current_speed'] = current_data['speed_ms']

        wave_data = get_wave_height(lat, lon)
        if wave_data and 'value' in wave_data:
            marine_data['wave_height'] = wave_data['value']

        oxygen_data = get_dissolved_oxygen(lat, lon)
        if oxygen_data and 'value' in oxygen_data:
            marine_data['dissolved_oxygen'] = oxygen_data['value']

    except Exception as e:
        print(f"⚠️ Erreur récupération données réelles: {e}")

    # Récupérer le vent depuis OpenWeatherMap (déjà présent)
    weather_result = get_cached_weather(lat, lon)
    if weather_result['success']:
        marine_data['wind_speed_kmh'] = weather_result['weather']['wind_speed']
        marine_data['wind_direction_deg'] = weather_result['weather']['wind_direction']

    return marine_data


# ===== FONCTION INTERNE POUR RÉUTILISATION DES PRÉVISIONS 24H =====
def api_24h_forecast_internal(lat, lon, species):
    """Version interne de api_24h_forecast pour réutilisation"""
    try:
        current_time = datetime.now()
        hourly_data = []

        # Fonction interne pour obtenir TOUTES les données marines
        def get_complete_marine_data(target_time):
            """Retourne toutes les données marines pour une date/heure spécifique"""
            # Météo pour cette heure
            weather_result = get_cached_weather(lat, lon)
            weather = weather_result['weather'] if weather_result['success'] else generate_consistent_weather(lat, lon)['weather']

            # Données marines multi-sources
            marine = get_marine_data_multi_source(lat, lon)

            # Température de l'eau estimée
            water_temp = predictor.estimate_water_from_position(lat, lon)

            # Oxygène dissous
            oxygen = predictor.calculate_dissolved_oxygen(
                water_temp,
                config.SALINITY_MEDITERRANEAN,
                weather['pressure']
            )

            # Chlorophylle
            chlorophyll = marine.get('chlorophyll',
                predictor.estimate_chlorophyll(target_time.month, lat, lon))

            # Courant tidal
            current = predictor.calculate_tidal_current(lat, lon, target_time)

            return {
                'temperature': weather['temperature'],
                'wind_speed': marine.get('wind_speed_kmh', weather['wind_speed']) / 3.6,
                'wind_direction': marine.get('wind_direction_deg', weather['wind_direction']),
                'pressure': weather['pressure'],
                'wave_height': weather.get('wave_height', calculate_wave_height(weather['wind_speed'])),
                'turbidity': weather.get('turbidity', 1.0),
                'humidity': weather['humidity'],
                'condition': weather['condition'],
                'water_temperature': water_temp,
                'salinity': config.SALINITY_MEDITERRANEAN,
                'current_speed': current['speed_mps'],
                'oxygen': oxygen,
                'chlorophyll': chlorophyll
            }

        # Calculer pour CHAQUE heure avec les données COMPLÈTES
        for hour_offset in range(24):
            forecast_time = current_time + timedelta(hours=hour_offset)

            # Données marines COMPLÈTES pour cette heure
            marine_data = get_complete_marine_data(forecast_time)

            # Prédiction COMPLÈTE pour cette heure
            prediction = predictor.predict_daily_activity(
                lat,
                lon,
                forecast_time,
                species,
                marine_data
            )

            # Récupération du score (déjà en pourcentage 0-100)
            score = int(round(prediction['score']))

            hourly_data.append({
                'hour': forecast_time.hour,
                'time': forecast_time.strftime('%H:%M'),
                'score': score,
                'timestamp': forecast_time.timestamp()
            })

        hours = [f"{d['hour']}h" for d in hourly_data]
        scores = [d['score'] for d in hourly_data]

        return jsonify({
            'status': 'success',
            'hours': hours,
            'scores': scores,
            'current_score': scores[0] if scores else 0
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ===== NOUVELLE ROUTE API POUR LA PRESSION 24h =====
@app.route('/api/pressure_24h')
def api_pressure_24h():
    """Données de pression sur 24h pour le pictogramme"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        
        # Récupérer les données météo actuelles
        weather_result = get_cached_weather(lat, lon)
        
        if not weather_result['success']:
            return jsonify({'status': 'error', 'message': 'Pas de données météo'})
        
        current_pressure = weather_result['weather'].get('pressure', 1015)
        
        # Générer une tendance réaliste sur 24h
        hours = []
        pressures = []
        
        # Heure actuelle
        now = datetime.now()
        
        for i in range(24):
            hour_time = now + timedelta(hours=i)
            hour_str = hour_time.strftime('%Hh')
            hours.append(hour_str)
            
            # Variation sinusoïdale réaliste (±3 hPa sur 24h)
            # + tendance à la baisse ou hausse selon la météo
            variation = math.sin(i * math.pi / 12) * 2
            
            # Simulation d'une tendance (si la pression actuelle est en baisse)
            trend = 0
            if i < 12:
                trend = -0.2 * i  # Baisse progressive
            else:
                trend = -2.4 + 0.2 * (i - 12)  # Remontée
            
            pressure = current_pressure + variation + trend
            pressures.append(round(pressure, 1))
        
        # Déterminer la tendance globale
        first_3 = sum(pressures[:3]) / 3
        last_3 = sum(pressures[-3:]) / 3
        
        if last_3 > first_3 + 1:
            trend = "hausse"
            icon = "📈"
            color = "#ef4444"
        elif last_3 < first_3 - 1:
            trend = "baisse"
            icon = "📉"
            color = "#10b981"
        else:
            trend = "stable"
            icon = "➡️"
            color = "#f59e0b"
        
        # Message selon la tendance
        if trend == "baisse" and current_pressure < 1020:
            message = "✅ Pression en baisse - Bon pour la pêche !"
        elif trend == "baisse":
            message = "👍 Pression en baisse - Activité stimulée"
        elif trend == "hausse" and current_pressure > 1020:
            message = "⚠️ Pression en hausse - Poissons moins actifs"
        else:
            message = "➡️ Pression stable - Conditions normales"
        
        return jsonify({
            'status': 'success',
            'hours': hours,
            'pressures': pressures,
            'current': current_pressure,
            'min': min(pressures),
            'max': max(pressures),
            'trend': trend,
            'trend_icon': icon,
            'trend_color': color,
            'message': message,
            'unit': 'hPa'
        })
        
    except Exception as e:
        print(f"❌ Erreur API pression: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# ===== ROUTES PRINCIPALES =====
@app.route('/')
def index(): return render_template('index.html')

@app.route('/species_selector')
def species_selector(): return render_template('species_selector.html')

@app.route('/predictions')
def predictions(): return render_template('predictions.html')

@app.route('/favorites')
def favorites(): return render_template('favorites.html')

@app.route('/science')
def science(): return render_template('science.html')

@app.route('/alerts')
def alerts(): return render_template('alertes.html')

@app.route('/api/current_weather')
def api_current_weather():
    try:
        lat = float(request.args.get('lat', 36.8065)); lon = float(request.args.get('lon', 10.1815))
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        weather_result = get_cached_weather(lat, lon, force_refresh=refresh)
        return jsonify({'status':'success','weather':weather_result['weather'],'source':weather_result.get('source','cache'),'cached':weather_result.get('source')=='cache','api_limits':{'openweather_today':API_RATE_LIMITS['openweather']['count_today'],'openweather_max':API_RATE_LIMITS['openweather']['max_per_day'],'cache_mode':API_RATE_LIMITS['openweather'].get('use_cache_only',False)},'next_refresh':(datetime.now()+timedelta(minutes=30)).isoformat()})
    except Exception as e:
        print(f"❌ Erreur API météo: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/quick_score')
def api_quick_score():
    """Route ULTRA-RAPIDE - score immédiat depuis cache"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')

        cache_key = f"quick_{lat:.4f}_{lon:.4f}_{species}"

        def compute_quick():
            weather = get_cached_weather(lat, lon)
            base_score = 65
            if weather['success']:
                wind = weather['weather']['wind_speed']
                if wind < 15:
                    base_score += 10
                elif wind > 25:
                    base_score -= 10
            return {
                'score': base_score,
                'source': 'quick'
            }

        data, from_cache = get_cached(cache_key, compute_quick)

        return jsonify({
            'status': 'success',
            'score': data['score'],
            'quick': True,
            'cached': from_cache,
            'last_update': datetime.now().isoformat(),
            'next_update': (datetime.now() + timedelta(hours=3)).isoformat()
        })

    except Exception as e:
        return jsonify({'status': 'error', 'score': 65})

@app.route('/api/tunisian_prediction')
def api_tunisian_prediction():
    try:
        lat = float(request.args.get('lat', 36.8065)); lon = float(request.args.get('lon', 10.1815)); species = request.args.get('species', 'loup')
        cache_key = f"prediction_{lat:.4f}_{lon:.4f}_{species}"
        cached_prediction = load_from_cache('prediction', {'lat': lat, 'lon': lon, 'species': species}, max_age_hours=1)
        if cached_prediction: return jsonify(cached_prediction)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_location = executor.submit(get_location_name_with_cache, lat, lon)
            future_bathymetry = executor.submit(get_real_bathymetry, lat, lon)
            future_weather = executor.submit(get_cached_weather, lat, lon)
            location_info = future_location.result()
            bathymetry = future_bathymetry.result()
            weather_result = future_weather.result()

        marine_data = get_marine_data_multi_source(lat, lon)

        if weather_result['success']:
            real_weather = weather_result['weather']
            predictor_weather = {
                'temperature':real_weather['temperature'],
                'wind_speed':marine_data.get('wind_speed_kmh', real_weather['wind_speed'])/3.6,
                'wind_direction':marine_data.get('wind_direction_deg', real_weather['wind_direction']),
                'pressure':real_weather['pressure'],
                'wave_height':real_weather.get('wave_height', 0.5),
                'turbidity':real_weather.get('turbidity', 1.0),
                'humidity':real_weather['humidity'],
                'condition':real_weather['condition'],
                'water_temperature':marine_data['water_temperature'],
                'salinity':marine_data['salinity'],
                'current_speed':marine_data['current_speed']
            }
            weather_source = real_weather.get('source', 'OpenWeatherMap')
        else:
            fallback_weather = generate_consistent_weather(lat, lon)['weather']
            predictor_weather = {
                'temperature':fallback_weather['temperature'],
                'wind_speed':marine_data.get('wind_speed_kmh', fallback_weather['wind_speed'])/3.6,
                'wind_direction':marine_data.get('wind_direction_deg', fallback_weather['wind_direction']),
                'pressure':fallback_weather['pressure'],
                'wave_height':fallback_weather['wave_height'],
                'turbidity':fallback_weather['turbidity'],
                'humidity':fallback_weather['humidity'],
                'condition':fallback_weather['condition'],
                'water_temperature':marine_data['water_temperature'],
                'salinity':marine_data['salinity'],
                'current_speed':marine_data['current_speed']
            }
            weather_source = 'modèle cohérent'

        oxygen_level = predictor.calculate_dissolved_oxygen(marine_data['water_temperature'],marine_data['salinity'],predictor_weather['pressure'])
        chlorophyll_level = marine_data.get('chlorophyll', predictor.estimate_chlorophyll(datetime.now().month, lat, lon))
        current_data = predictor.calculate_tidal_current(lat, lon, datetime.now())
        predictor_weather.update({'oxygen': oxygen_level,'chlorophyll': chlorophyll_level})

        prediction = predictor.predict_daily_activity(lat, lon, datetime.now(), species, predictor_weather)

        depth = bathymetry.get('depth', 10)
        depth_factor = calculate_depth_factor(depth, species)
        weather_score = calculate_weather_score(predictor_weather)

        # Récupérer le score de l'advanced_predictor (déjà en pourcentage 0-100)
        activity_score_percent = prediction['score']

        # 👇 NOUVELLE VERSION : Utiliser le pictogramme comme source de vérité
        forecast_response = api_24h_forecast_internal(lat, lon, species)
        if forecast_response.status_code == 200:
            try:
                forecast_data = json.loads(forecast_response.data)
                if forecast_data.get('scores') and len(forecast_data['scores']) > 0:
                    # L'heure actuelle correspond à l'index de l'heure courante
                    current_hour = datetime.now().hour
                    # Chercher l'index de l'heure actuelle dans le pictogramme
                    current_index = -1
                    for i, h in enumerate(forecast_data['hours']):
                        if h == f"{current_hour}h":
                            current_index = i
                            break

                    if current_index >= 0:
                        final_score = forecast_data['scores'][current_index]
                    else:
                        # Fallback si l'heure n'est pas trouvée
                        final_score = forecast_data['scores'][0]
                else:
                    final_score = forecast_data['current_score']
            except Exception as e:
                print(f"⚠️ Erreur parsing forecast: {e}")
                final_score = round(
                    activity_score_percent * 0.35 +
                    depth_factor * 25 +
                    weather_score * 40
                )
        else:
            # Fallback sur l'ancien calcul
            final_score = round(
                activity_score_percent * 0.35 +
                depth_factor * 25 +
                weather_score * 40
            )

        final_score = max(0, min(100, final_score))

        prediction_id = hashlib.md5(f"{lat:.4f}_{lon:.4f}_{species}_{datetime.now().strftime('%Y%m%d')}".encode()).hexdigest()[:12]

        response_data = {
            'status':'success',
            'prediction_id':prediction_id,
            'stable':True,
            'valid_until':(datetime.now()+timedelta(minutes=60)).isoformat(),
            'scores':{
                'final':int(final_score),
                'environmental':int(round(prediction['environmental_score']*100)),
                'behavioral':int(round(prediction['behavioral_score']*100)),
                'bathymetry_factor':int(round(depth_factor*100)),
                'weather_factor':int(round(weather_score*100)),
                'components':{
                    'scientific':int(round(prediction['environmental_score']*100)),
                    'depth':int(round(depth_factor*100)),
                    'regional':int(round(prediction['regional_factor']*100)),
                    'weather':int(round(weather_score*100))
                }
            },
            'weather':{
                'temperature':predictor_weather['temperature'],
                'wind_speed':marine_data.get('wind_speed_kmh',0),
                'wind_direction':predictor_weather.get('wind_direction',0),
                'wind_direction_abbr':real_weather.get('wind_direction_abbr','N'),
                'wind_direction_name':real_weather.get('wind_direction_name','Nord'),
                'wind_direction_icon':real_weather.get('wind_direction_icon','⬆️'),
                'wind_fishing_impact':real_weather.get('wind_fishing_impact','neutre'),
                'wind_offshore': False,
                'wind_onshore':real_weather.get('wind_onshore',False),
                'pressure':predictor_weather['pressure'],
                'humidity':predictor_weather.get('humidity',60),
                'condition':predictor_weather['condition'],
                'condition_fr':weather_result['weather'].get('condition_fr', predictor_weather['condition']),
                'wave_height':predictor_weather['wave_height'],
                'updated':datetime.now().isoformat(),
                'source':weather_source
            },
            'scientific_factors':prediction.get('scientific_factors',{
                'dissolved_oxygen':{'value':oxygen_level,'unit':'mg/L'},
                'chlorophyll_a':{'value':chlorophyll_level,'unit':'mg/m³'},
                'tidal_current':current_data
            }),
            'recommendations':{
                'tips':[
                    f"Opportunité: {prediction['fishing_opportunity']}",
                    f"Heures optimales: {', '.join([str(h['hour'])+'h' for h in prediction['best_fishing_hours'][:3]])}",
                    f"Profondeur optimale: {get_optimal_depth(species)}",
                    f"Type de fond recommandé: {get_optimal_seabed(species)}",
                    f"Météo: {weather_result['weather'].get('condition_fr', predictor_weather['condition'])}, {predictor_weather['temperature']:.1f}°C, Vent: {marine_data.get('wind_speed_kmh', 0):.1f} km/h"
                ],
                'techniques':prediction.get('recommended_techniques', ['surfcasting', 'pêche à soutenir'])
            },
            'bathymetry':{
                **bathymetry,
                'optimal_for_species':is_depth_optimal(depth, species),
                'zone':location_info.get('address', {}).get('state', 'Zone côtière'),
                'recommended_fishing':[
                    f"Profondeur: {depth}m ({'optimale' if is_depth_optimal(depth, species) else 'sous-optimale'})",
                    f"Type de fond: {bathymetry.get('seabed_description', 'mixte')}",
                    f"Précision: {bathymetry.get('accuracy', 'moyenne')}"
                ]
            },
            'location':{
                'lat':lat,
                'lon':lon,
                'name':location_info.get('name', f'Spot ({lat:.4f}, {lon:.4f})'),
                'type':location_info.get('type', 'water'),
                'region':location_info.get('address', {}).get('state', 'Tunisie')
            },
            'metadata':{
                'species':species,
                'timestamp':datetime.now().isoformat(),
                'data_source':bathymetry.get('source', 'modèle scientifique'),
                'weather_source':weather_source,
                'prediction_stable':True,
                'cache_duration_minutes':60,
                'next_update_recommended':(datetime.now()+timedelta(minutes=60)).strftime('%H:%M'),
                'api_usage_info':{
                    'openweather_calls_today':API_RATE_LIMITS['openweather']['count_today'],
                    'using_cache':weather_result.get('source')=='cache'
                },
                'cache': {
                    'cached_at': datetime.now().isoformat(),
                    'expires_at': (datetime.now() + timedelta(hours=3)).isoformat(),
                    'cache_duration_hours': 3
                }
            }
        }

        save_to_cache('prediction', {'lat': lat, 'lon': lon, 'species': species}, response_data, 1)
        return jsonify(response_data)
    except Exception as e:
        print(f"❌ Erreur prédiction: {e}")
        return jsonify({'status':'error','message':str(e),'fallback':{'scores':{'final':65},'recommendations':{'tips':['Utilisez notre modèle scientifique pour des prédictions précises']}}})

@app.route('/api/24h_forecast')
def api_24h_forecast():
    """Prévisions sur 24h scientifiquement exactes - MÊME niveau de détail pour toutes les heures"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')

        current_time = datetime.now()
        hourly_data = []

        # Fonction interne pour obtenir TOUTES les données marines
        def get_complete_marine_data(target_time):
            """Retourne toutes les données marines pour une date/heure spécifique"""
            # Météo pour cette heure
            weather_result = get_cached_weather(lat, lon)
            weather = weather_result['weather'] if weather_result['success'] else generate_consistent_weather(lat, lon)['weather']

            # Données marines multi-sources
            marine = get_marine_data_multi_source(lat, lon)

            # Température de l'eau estimée
            water_temp = predictor.estimate_water_from_position(lat, lon)

            # Oxygène dissous
            oxygen = predictor.calculate_dissolved_oxygen(
                water_temp,
                config.SALINITY_MEDITERRANEAN,
                weather['pressure']
            )

            # Chlorophylle
            chlorophyll = marine.get('chlorophyll',
                predictor.estimate_chlorophyll(target_time.month, lat, lon))

            # Courant tidal
            current = predictor.calculate_tidal_current(lat, lon, target_time)

            return {
                'temperature': weather['temperature'],
                'wind_speed': marine.get('wind_speed_kmh', weather['wind_speed']) / 3.6,
                'wind_direction': marine.get('wind_direction_deg', weather['wind_direction']),
                'pressure': weather['pressure'],
                'wave_height': weather.get('wave_height', calculate_wave_height(weather['wind_speed'])),
                'turbidity': weather.get('turbidity', 1.0),
                'humidity': weather['humidity'],
                'condition': weather['condition'],
                'water_temperature': water_temp,
                'salinity': config.SALINITY_MEDITERRANEAN,
                'current_speed': current['speed_mps'],
                'oxygen': oxygen,
                'chlorophyll': chlorophyll
            }

        # Calculer pour CHAQUE heure avec les données COMPLÈTES
        for hour_offset in range(24):
            forecast_time = current_time + timedelta(hours=hour_offset)

            # Données marines COMPLÈTES pour cette heure
            marine_data = get_complete_marine_data(forecast_time)

            # Prédiction COMPLÈTE pour cette heure
            prediction = predictor.predict_daily_activity(
                lat,
                lon,
                forecast_time,
                species,
                marine_data
            )

            # Récupération du score (déjà en pourcentage 0-100)
            score = int(round(prediction['score']))

            hourly_data.append({
                'hour': forecast_time.hour,
                'time': forecast_time.strftime('%H:%M'),
                'score': score,
                'timestamp': forecast_time.timestamp()
            })

        # Extraire les listes
        hours = [f"{d['hour']}h" for d in hourly_data]
        scores = [d['score'] for d in hourly_data]

        # Le score actuel est simplement la première heure
        current_score = scores[0]
        current_hour = current_time.hour

        # Trouver le meilleur score (parmi toutes les heures)
        best_score = max(scores)
        best_indices = [i for i, s in enumerate(scores) if s == best_score]
        best_idx = best_indices[0]
        best_hour = hours[best_idx]
        best_time = hourly_data[best_idx]['time']
        best_hour_number = hourly_data[best_idx]['hour']

        # Comparer avec le score actuel (qui est déjà dans la liste)
        if current_score == best_score and best_idx == 0:
            note = "🔥 Le meilleur moment est MAINTENANT !"
        elif current_score == best_score:
            note = f"🔥 Meilleur moment également à {best_hour}"
        else:
            note = None

        # Calculer la tendance (comparer les premières heures)
        if len(scores) >= 4:
            if scores[3] > scores[0] + 3:
                trend = 'rising'
            elif scores[3] < scores[0] - 3:
                trend = 'falling'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        # Meilleurs créneaux (fenêtres de 3h)
        best_windows = []
        window_size = 3
        for i in range(len(hourly_data) - window_size + 1):
            window_scores = scores[i:i+window_size]
            avg_score = sum(window_scores) / window_size
            best_windows.append({
                'start': hourly_data[i]['time'],
                'end': hourly_data[i+window_size-1]['time'],
                'avg_score': round(avg_score, 1),
                'peak': max(window_scores),
                'start_hour': hourly_data[i]['hour'],
                'end_hour': hourly_data[i+window_size-1]['hour']
            })

        best_windows.sort(key=lambda x: x['avg_score'], reverse=True)

        response = {
            'status': 'success',
            'hours': hours,
            'scores': scores,
            'current_hour': current_hour,
            'current_score': current_score,
            'best_hour': best_hour,
            'best_time': best_time,
            'best_hour_number': best_hour_number,
            'best_score': best_score,
            'best_windows': best_windows[:3],
            'trend': trend,
            'note': note,
            'metadata': {
                'location': {'lat': lat, 'lon': lon},
                'species': species,
                'data_source': 'scientific_complete',
                'timestamp': datetime.now().isoformat()
            }
        }

        return jsonify(response)

    except Exception as e:
        print(f"❌ Erreur prévisions 24h: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e),
            'hours': [f"{h}h" for h in range(24)],
            'scores': [0]*24,
            'current_score': 0,
            'best_hour': '--',
            'best_time': '--:--',
            'best_score': 0
        })

@app.route('/api/location_search')
def api_location_search():
    """Recherche de localisations par nom"""
    try:
        query = request.args.get('q', '').strip()
        if not query: return jsonify({'status':'error','message':'Paramètre "q" requis'})
        if ',' in query:
            try:
                lat, lon = map(float, query.split(','))
                return jsonify({'status':'success','results':[{'lat':lat,'lon':lon,'name':f'Position ({lat:.4f}, {lon:.4f})','type':'coordinates'}]})
            except: pass
        locations = []
        tunisian_cities = [
            {'name':'Tunis','lat':36.8065,'lon':10.1815},
            {'name':'Bizerte','lat':37.2747,'lon':9.8739},
            {'name':'Sousse','lat':35.8254,'lon':10.6360},
            {'name':'Hammamet','lat':36.4000,'lon':10.6000},
            {'name':'Monastir','lat':35.7833,'lon':10.8333},
            {'name':'Mahdia','lat':35.5047,'lon':11.0622},
            {'name':'Sfax','lat':34.7400,'lon':10.7600},
            {'name':'Djerba','lat':33.8078,'lon':10.8451},
            {'name':'Tabarka','lat':36.9540,'lon':8.7580},
            {'name':'Zarzis','lat':33.5000,'lon':11.1167},
            {'name':'Kélibia','lat':36.8475,'lon':11.0940},
            {'name':'La Marsa','lat':36.8782,'lon':10.3247},
            {'name':'Gammarth','lat':36.9000,'lon':10.3167}
        ]
        for city in tunisian_cities:
            if query.lower() in city['name'].lower():
                locations.append({'lat':city['lat'],'lon':city['lon'],'name':city['name'],'type':'city'})
        if not locations and len(query) > 2:
            locations = [{'lat':36.8065,'lon':10.1815,'name':'Tunis','type':'city'}]
        return jsonify({'status':'success','query':query,'results':locations[:10]})
    except Exception as e:
        print(f"❌ Erreur recherche localisation: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/spot_info')
def api_spot_info():
    """Informations détaillées sur un spot de pêche"""
    try:
        lat = float(request.args.get('lat', 36.8065)); lon = float(request.args.get('lon', 10.1815))
        location_info = get_location_name_with_cache(lat, lon)
        bathymetry = get_real_bathymetry(lat, lon)
        weather_result = get_cached_weather(lat, lon)
        spot_data = {
            'status':'success',
            'coordinates':{'lat':lat,'lon':lon},
            'location':location_info,
            'bathymetry':bathymetry,
            'weather':weather_result['weather'] if weather_result['success'] else None,
            'metadata':{
                'timestamp':datetime.now().isoformat(),
                'spot_quality':'good' if bathymetry.get('depth',0)>2 else 'poor',
                'accessibility':'easy' if lat>36.0 and lon>10.0 else 'medium',
                'popularity':'high' if 36.5<lat<37.0 and 10.0<lon<11.0 else 'medium'
            },
            'recommendations':{
                'best_season':['printemps','automne'],
                'best_time':['matin','soir'],
                'techniques':['surfcasting','pêche à soutenir'],
                'baits':['vers','crevettes','sardines']
            }
        }
        return jsonify(spot_data)
    except Exception as e:
        print(f"❌ Erreur info spot: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/fishing_calendar')
def api_fishing_calendar():
    """Calendrier de pêche mensuel"""
    try:
        species = request.args.get('species', 'loup'); month = int(request.args.get('month', datetime.now().month))
        calendars = {
            'loup':{
                'name':'Loup de Mer',
                'months':{1:'moyenne',2:'moyenne',3:'bonne',4:'excellente',5:'excellente',6:'bonne',7:'moyenne',8:'moyenne',9:'bonne',10:'excellente',11:'excellente',12:'bonne'},
                'tips':['Privilégiez les zones rocheuses','Pêche au vif ou au leurre','Meilleure période: mars-juin et sept-nov']
            },
            'daurade':{
                'name':'Daurade Royale',
                'months':{1:'faible',2:'faible',3:'moyenne',4:'bonne',5:'excellente',6:'excellente',7:'excellente',8:'bonne',9:'bonne',10:'moyenne',11:'moyenne',12:'faible'},
                'tips':['Zones sablonneuses avec herbiers','Appâts: vers, crustacés','Pêche fine recommandée']
            },
            'pageot':{
                'name':'Pageot Commun',
                'months':{1:'faible',2:'faible',3:'moyenne',4:'bonne',5:'excellente',6:'excellente',7:'excellente',8:'bonne',9:'moyenne',10:'moyenne',11:'faible',12:'faible'},
                'tips':['Fonds rocheux','Pêche en dérive','Taille minimale: 20cm']
            }
        }
        if species not in calendars: species = 'loup'
        calendar_data = calendars[species]
        return jsonify({
            'status':'success',
            'species':species,
            'species_name':calendar_data['name'],
            'current_month':month,
            'current_month_name':datetime(2024,month,1).strftime('%B'),
            'activity':calendar_data['months'][month],
            'calendar':calendar_data['months'],
            'tips':calendar_data['tips'],
            'best_months':[m for m, activity in calendar_data['months'].items() if activity in ['excellente','bonne']]
        })
    except Exception as e:
        print(f"❌ Erreur calendrier: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/tide_chart')
def api_tide_chart():
    """Graphique des marées pour 24h"""
    try:
        lat = float(request.args.get('lat', 36.8065)); lon = float(request.args.get('lon', 10.1815))
        tide_data = get_tide_data_with_cache(lat, lon)
        now = datetime.now(); tide_points = []
        for hour in range(24):
            time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            tide_height = 0.5 + 0.3 * math.sin(hour * math.pi / 12)
            tide_points.append({
                'time':time.strftime('%H:%M'),
                'height':round(tide_height,2),
                'is_high':tide_height>0.7,
                'is_low':tide_height<0.3
            })
        return jsonify({
            'status':'success',
            'location':f'Position ({lat:.4f}, {lon:.4f})',
            'tide_data':tide_data,
            'chart_points':tide_points,
            'next_high_tide':get_next_high_tide(tide_data),
            'next_low_tide':get_next_low_tide(tide_data),
            'current_height':tide_data.get('heights',[{}])[0].get('height',0.5) if tide_data.get('heights') else 0.5,
            'recommendations':{
                'best_fishing_tide':'marée montante',
                'worst_fishing_tide':'marée basse fixe',
                'tips':['Pêchez 2h avant et après la marée haute','Évitez les marées trop basses','Marée montante = meilleure activité']
            }
        })
    except Exception as e:
        print(f"❌ Erreur graphique marée: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/moon_phase')
def api_moon_phase():
    """Phase de la lune actuelle"""
    try:
        def calculate_moon_phase(date):
            days_in_cycle = 29.530588853; known_new_moon = datetime(2024, 1, 11)
            days_since = (date - known_new_moon).days; days_in_current = days_since % days_in_cycle
            if days_in_current < 1.84566: return 'Nouvelle Lune'
            elif days_in_current < 5.53699: return 'Premier Croissant'
            elif days_in_current < 9.22831: return 'Premier Quartier'
            elif days_in_current < 12.91963: return 'Lune Gibbeuse Croissante'
            elif days_in_current < 16.61096: return 'Pleine Lune'
            elif days_in_current < 20.30228: return 'Lune Gibbeuse Décroissante'
            elif days_in_current < 23.99361: return 'Dernier Quartier'
            else: return 'Dernier Croissant'
        current_date = datetime.now(); phase = calculate_moon_phase(current_date)
        fishing_impact = {
            'Nouvelle Lune':'Très bon - forte activité nocturne',
            'Pleine Lune':'Bon - bonne visibilité nocturne',
            'Premier Quartier':'Moyen',
            'Dernier Quartier':'Moyen',
            'Premier Croissant':'Bon en soirée',
            'Dernier Croissant':'Bon en matinée',
            'Lune Gibbeuse Croissante':'Très bon',
            'Lune Gibbeuse Décroissante':'Très bon'
        }
        return jsonify({
            'status':'success',
            'date':current_date.strftime('%Y-%m-%d'),
            'moon_phase':phase,
            'fishing_impact':fishing_impact.get(phase,'Moyen'),
            'illumination':'0%' if phase=='Nouvelle Lune' else '100%' if phase=='Pleine Lune' else '50%',
            'next_full_moon':(current_date+timedelta(days=14)).strftime('%Y-%m-%d'),
            'next_new_moon':(current_date+timedelta(days=7)).strftime('%Y-%m-%d'),
            'tips':['Nouvelle Lune: excellente pour la pêche nocturne','Pleine Lune: privilégiez les leurres brillants','Évitez les changements de phase pour une pêche régulière']
        })
    except Exception as e:
        print(f"❌ Erreur phase lunaire: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/favorites', methods=['GET'])
def api_favorites():
    """API pour gérer les favoris (version simplifiée)"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f: favorites = json.load(f)
        else: favorites = []
        return jsonify({'status':'success','favorites':favorites,'count':len(favorites)})
    except Exception as e:
        print(f"❌ Erreur favoris: {e}")
        return jsonify({'status':'error','message':str(e),'favorites':[]})

@app.route('/api/favorites', methods=['POST'])
def api_favorites_post():
    """Ajouter un favori"""
    try:
        data = request.json
        if not data: return jsonify({'status': 'error', 'message': 'Données manquantes'})
        favorites = []
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f: favorites = json.load(f)
        favorite_id = hashlib.md5(f"{data.get('name')}{data.get('lat')}{data.get('lon')}{time.time()}".encode()).hexdigest()[:8]
        data['id'] = favorite_id; data['added_date'] = datetime.now().isoformat()
        favorites.append(data)
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f: json.dump(favorites, f, ensure_ascii=False, indent=2)
        return jsonify({'status': 'success', 'id': favorite_id})
    except Exception as e:
        print(f"❌ Erreur ajout favori: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/favorites', methods=['DELETE'])
def api_favorites_delete():
    """Supprimer un favori"""
    try:
        favorite_id = request.args.get('id')
        if not favorite_id and request.json: favorite_id = request.json.get('id')
        if not favorite_id: return jsonify({'status': 'error', 'message': 'ID manquant'})
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f: favorites = json.load(f)
            initial_count = len(favorites); favorites = [f for f in favorites if str(f.get('id')) != str(favorite_id)]
            if len(favorites) < initial_count:
                with open(FAVORITES_FILE, 'w', encoding='utf-8') as f: json.dump(favorites, f, ensure_ascii=False, indent=2)
                return jsonify({'status': 'success', 'message': 'Favori supprimé'})
            else: return jsonify({'status': 'error', 'message': 'Favori non trouvé'})
        return jsonify({'status': 'error', 'message': 'Aucun favori'})
    except Exception as e:
        print(f"❌ Erreur suppression favori: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/real_bathymetry')
def api_real_bathymetry():
    try:
        lat=float(request.args.get('lat',36.8065)); lon=float(request.args.get('lon',10.1815))
        bathymetry=get_real_bathymetry(lat,lon); tide_data=get_tide_data_with_cache(lat,lon); location=get_location_name_with_cache(lat,lon)
        return jsonify({
            'status':'success',
            'data':{
                'coordinates':{'lat':lat,'lon':lon},
                'bathymetry':bathymetry,
                'tides':{
                    'current_height':tide_data.get('heights',[{}])[0].get('height',0.5) if tide_data.get('heights') else 0.5,
                    'next_high_tide':get_next_high_tide(tide_data),
                    'next_low_tide':get_next_low_tide(tide_data)
                },
                'location':location,
                'fishing_suitability':assess_fishing_suitability(bathymetry),
                'timestamp':datetime.now().isoformat()
            }
        })
    except Exception as e: return jsonify({'status':'error','message':str(e)})

@app.route('/api/species_by_season')
def api_species_by_season():
    current_month=datetime.now().month
    if current_month in [12,1,2]: season='hiver'; recommended=['loup','daurade','merlan','corbeau']
    elif current_month in [3,4,5]: season='printemps'; recommended=['loup','daurade','pageot','maquereau']
    elif current_month in [6,7,8]: season='été'; recommended=['daurade','pageot','mulet','marbré','sériole']
    else: season='automne'; recommended=['loup','daurade','pageot','rouget','sar']
    species_list=[]; species_icons={'loup':'🐟','daurade':'🐠','pageot':'🐡','maquereau':'🦈','merlan':'🐟','corbeau':'🐠','mulet':'🐡','marbré':'🦈','sériole':'🐟','rouget':'🐠','sar':'🐡','thon':'🦈'}
    for sp in recommended: species_list.append({'key':sp,'name':sp.capitalize(),'icon':species_icons.get(sp,'🐟')})
    return jsonify({
        'status':'success',
        'current_season':season,
        'current_month':current_month,
        'recommended_species':species_list
    })

@app.route('/api/all_species_complete')
def api_all_species_complete():
    species_data=[
        {'key':'loup','name':'Loup de Mer','scientific':'Dicentrarchus labrax','category':'surface','difficulty':'moyenne','popularity':5,'seasons':['printemps','été','automne','hiver'],'color':'#3b82f6','icon':'🐟'},
        {'key':'daurade','name':'Daurade Royale','scientific':'Sparus aurata','category':'surface','difficulty':'facile','popularity':5,'seasons':['été','automne'],'color':'#10b981','icon':'🐠'},
        {'key':'pageot','name':'Pageot Commun','scientific':'Pagellus erythrinus','category':'fond','difficulty':'moyenne','popularity':4,'seasons':['printemps','été'],'color':'#f59e0b','icon':'🐡'},
        {'key':'thon','name':'Thon Rouge','scientific':'Thunnus thynnus','category':'large','difficulty':'difficile','popularity':4,'seasons':['été'],'color':'#ef4444','icon':'🦈'},
        {'key':'sar','name':'Sar','scientific':'Diplodus sargus','category':'surface','difficulty':'moyenne','popularity':4,'seasons':['printemps','été','automne'],'color':'#8b5cf6','icon':'🐠'},
        {'key':'mulet','name':'Mulet','scientific':'Mugilidae','category':'surface','difficulty':'facile','popularity':3,'seasons':['été','automne'],'color':'#06b6d4','icon':'🐟'},
        {'key':'marbré','name':'Marbré','scientific':'Lithognathus mormyrus','category':'fond','difficulty':'moyenne','popularity':3,'seasons':['été'],'color':'#f97316','icon':'🐡'},
        {'key':'rouget','name':'Rouget','scientific':'Mullus surmuletus','category':'fond','difficulty':'moyenne','popularity':4,'seasons':['printemps','été','automne'],'color':'#ef4444','icon':'🐠'},
        {'key':'sériole','name':'Sériole','scientific':'Seriola dumerili','category':'large','difficulty':'difficile','popularity':3,'seasons':['été'],'color':'#f59e0b','icon':'🦈'},
        {'key':'bonite','name':'Bonite','scientific':'Sarda sarda','category':'large','difficulty':'moyenne','popularity':3,'seasons':['été'],'color':'#3b82f6','icon':'🐟'},
        {'key':'corbeau','name':'Corbeau','scientific':'Sciaena umbra','category':'fond','difficulty':'moyenne','popularity':3,'seasons':['hiver','printemps'],'color':'#1e293b','icon':'🐠'},
        {'key':'espadon','name':'Espadon','scientific':'Xiphias gladius','category':'large','difficulty':'difficile','popularity':4,'seasons':['été'],'color':'#64748b','icon':'🦈'},
        {'key':'mérou','name':'Mérou','scientific':'Epinephelus marginatus','category':'fond','difficulty':'difficile','popularity':4,'seasons':['été','automne'],'color':'#475569','icon':'🐡'},
        {'key':'merlan','name':'Merlan','scientific':'Merlangius merlangus','category':'fond','difficulty':'facile','popularity':3,'seasons':['hiver','printemps'],'color':'#cbd5e1','icon':'🐟'},
        {'key':'merlu','name':'Merlu','scientific':'Merluccius merluccius','category':'fond','difficulty':'moyenne','popularity':3,'seasons':['toute l\'année'],'color':'#94a3b8','icon':'🐠'},
        {'key':'orphie','name':'Orphie','scientific':'Belone belone','category':'surface','difficulty':'facile','popularity':2,'seasons':['printemps','été'],'color':'#22c55e','icon':'🐟'}
    ]
    return jsonify({'status':'success','species':species_data})

@app.route('/api/scientific_factors')
def api_scientific_factors():
    """API pour les facteurs scientifiques (oxygène, chlorophylle, courant)"""
    try:
        lat = float(request.args.get('lat', 36.8065)); lon = float(request.args.get('lon', 10.1815)); species = request.args.get('species', 'loup')
        weather_result = get_cached_weather(lat, lon)
        if weather_result['success']:
            real_weather = weather_result['weather']
            water_temp = predictor.estimate_water_from_position(lat, lon)
            oxygen_level = predictor.calculate_dissolved_oxygen(water_temp,config.SALINITY_MEDITERRANEAN,real_weather['pressure'])
            month = datetime.now().month; chlorophyll_level = predictor.estimate_chlorophyll(month, lat, lon)
            current_data = predictor.calculate_tidal_current(lat, lon, datetime.now())
            species_profile = predictor.species_profiles.get(species, predictor.species_profiles["loup"])
            return jsonify({
                'status':'success',
                'factors':{
                    'dissolved_oxygen':{
                        'value':round(oxygen_level,2),
                        'unit':'mg/L',
                        'optimal_range':f"{species_profile.get('oxygen_optimal', [5.0, 8.0])[0]}-{species_profile.get('oxygen_optimal', [5.0, 8.0])[1]} mg/L",
                        'status':'optimal' if species_profile.get('oxygen_optimal', [5.0, 8.0])[0] <= oxygen_level <= species_profile.get('oxygen_optimal', [5.0, 8.0])[1] else 'suboptimal',
                        'impact':'Favorable' if oxygen_level>6.0 else 'Modéré' if oxygen_level>4.0 else 'Défavorable'
                    },
                    'chlorophyll_a':{
                        'value':round(chlorophyll_level,2),
                        'unit':'mg/m³',
                        'optimal_range':f"{species_profile.get('chlorophyll_optimal', [0.8, 3.0])[0]}-{species_profile.get('chlorophyll_optimal', [0.8, 3.0])[1]} mg/m³",
                        'status':'optimal' if species_profile.get('chlorophyll_optimal', [0.8, 3.0])[0] <= chlorophyll_level <= species_profile.get('chlorophyll_optimal', [0.8, 3.0])[1] else 'suboptimal',
                        'impact':'Productivité élevée' if chlorophyll_level>2.0 else 'Productivité moyenne' if chlorophyll_level>1.0 else 'Productivité faible'
                    },
                    'tidal_current':{
                        'speed_mps':current_data['speed_mps'],
                        'speed_knots':current_data['speed_knots'],
                        'direction':current_data['direction'],
                        'fishing_impact':current_data['fishing_impact'],
                        'optimal_range':f"{species_profile.get('current_preference', [0.1, 0.8])[0]}-{species_profile.get('current_preference', [0.1, 0.8])[1]} m/s",
                        'status':'optimal' if species_profile.get('current_preference', [0.1, 0.8])[0] <= current_data['speed_mps'] <= species_profile.get('current_preference', [0.1, 0.8])[1] else 'suboptimal'
                    },
                    'water_temperature':{
                        'value':round(water_temp,1),
                        'unit':'°C',
                        'optimal_range':f"{species_profile.get('temp_optimal', [15, 24])[0]}-{species_profile.get('temp_optimal', [15, 24])[1]}°C",
                        'status':'optimal' if species_profile.get('temp_optimal', [15, 24])[0] <= water_temp <= species_profile.get('temp_optimal', [15, 24])[1] else 'suboptimal'
                    }
                },
                'location':{'lat':lat,'lon':lon,'region':'Nord' if lat>37.0 else 'Centre' if lat>36.0 else 'Sud'},
                'species':species,
                'timestamp':datetime.now().isoformat()
            })
        else: return jsonify({'status':'error','message':'Impossible de récupérer les données météo'})
    except Exception as e:
        print(f"❌ Erreur facteurs scientifiques: {e}")
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/seasonal_calendar')
def api_seasonal_calendar():
    """Calendrier saisonnier des espèces"""
    try:
        seasonal_data = {
            'printemps': ['loup', 'daurade', 'pageot', 'maquereau', 'sar'],
            'été': ['daurade', 'pageot', 'thon', 'sériole', 'mulet'],
            'automne': ['loup', 'daurade', 'pageot', 'rouget', 'sar'],
            'hiver': ['loup', 'daurade', 'merlan', 'corbeau', 'merlu']
        }
        current_month = datetime.now().month
        if current_month in [3, 4, 5]: current_season = 'printemps'
        elif current_month in [6, 7, 8]: current_season = 'été'
        elif current_month in [9, 10, 11]: current_season = 'automne'
        else: current_season = 'hiver'
        return jsonify({
            'status':'success',
            'seasons':seasonal_data,
            'current_season':current_season,
            'current_month':current_month,
            'tips':{
                'printemps':'Meilleure saison pour le loup et la daurade',
                'été':'Idéal pour la pêche en mer et les espèces tropicales',
                'automne':'Bon compromis température/activité',
                'hiver':'Privilégiez les journées ensoleillées'
            }
        })
    except Exception as e: return jsonify({'status':'error','message':str(e)})

@app.route('/api/prediction_details')
def api_prediction_details():
    """Détails de prédiction pour le dashboard"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')

        prediction_result = predictor.predict_daily_activity(
            lat, lon, datetime.now(), species,
            get_cached_weather(lat, lon)['weather']
        )

        return jsonify({
            'status': 'success',
            'score': int(round(prediction_result['activity_score'])),
            'details': prediction_result,
            'recommendations': prediction_result.get('recommended_techniques', []),
            'best_hours': prediction_result.get('best_fishing_hours', []),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erreur détails prédiction: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'fallback': {'score': 65, 'details': {}}
        })

@app.route('/api/spot_analysis')
def api_spot_analysis():
    """Analyse détaillée d'un spot"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))

        bathymetry = get_real_bathymetry(lat, lon)
        weather = get_cached_weather(lat, lon)
        tide = get_tide_data_with_cache(lat, lon)
        location = get_location_name_with_cache(lat, lon)

        analysis = {
            'status': 'success',
            'coordinates': {'lat': lat, 'lon': lon},
            'name': location.get('name', f'Spot ({lat:.4f}, {lon:.4f})'),
            'bathymetry': bathymetry,
            'weather': weather['weather'] if weather['success'] else {},
            'tide': {
                'current': tide.get('heights', [{}])[0].get('height', 0.5) if tide.get('heights') else 0.5,
                'next_high': get_next_high_tide(tide),
                'next_low': get_next_low_tide(tide)
            },
            'fishing_suitability': assess_fishing_suitability(bathymetry),
            'distance': None,
            'details': {
                'current_impact': get_wind_fishing_impact(
                    weather['weather'].get('wind_direction', 0) if weather['success'] else 0,
                    lat, lon
                ),
                'risk_level': 'low' if bathymetry.get('depth', 0) > 3 else 'medium',
                'accessibility': 'easy' if lat > 36.0 and lon > 10.0 else 'medium'
            },
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(analysis)
    except Exception as e:
        print(f"❌ Erreur analyse spot: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/wind_forecast')
def api_wind_forecast():
    """Données de vent pour l'animation"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))

        weather = get_cached_weather(lat, lon)
        if weather['success']:
            wind_data = {
                'speed': weather['weather'].get('wind_speed', 10),
                'direction': weather['weather'].get('wind_direction', 0),
                'direction_name': weather['weather'].get('wind_direction_name', 'Nord'),
                'is_offshore': False,
                'is_onshore': weather['weather'].get('wind_onshore', False),
                'impact': weather['weather'].get('wind_fishing_impact', 'Neutre')
            }
        else:
            wind_data = {
                'speed': 10,
                'direction': 0,
                'direction_name': 'Nord',
                'is_offshore': False,
                'is_onshore': False,
                'impact': 'Neutre'
            }

        return jsonify({
            'status': 'success',
            'wind': wind_data,
            'particles_count': 150,
            'animation_speed': 1,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erreur données vent: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/quick_check')
def api_quick_check():
    """Vérification rapide pour décision immédiate"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')

        weather = get_cached_weather(lat, lon)
        prediction = predictor.predict_daily_activity(
            lat, lon, datetime.now(), species,
            weather['weather'] if weather['success'] else {}
        )

        score = int(round(prediction['activity_score']))
        wind_speed = weather['weather'].get('wind_speed', 10) if weather['success'] else 10
        is_offshore = False
        current_hour = datetime.now().hour
        is_daytime = 6 <= current_hour <= 19

        if is_offshore:
            decision = 'danger'
            message = '❌ DANGER VENT OFFSHORE - NE PAS PÊCHER'
            color = '#ef4444'
        elif score >= 85 and wind_speed < 15 and is_daytime:
            decision = 'excellent'
            message = '✅ CONDITIONS OPTIMALES - PARTEZ MAINTENANT !'
            color = '#10b981'
        elif score >= 70 and wind_speed < 20:
            decision = 'good'
            message = '🟡 BONNES CONDITIONS - BON MOMENT'
            color = '#f59e0b'
        else:
            decision = 'poor'
            message = '🔴 CONDITIONS SOUS-OPTIMALES - ATTENDRE'
            color = '#dc2626'

        return jsonify({
            'status': 'success',
            'decision': decision,
            'message': message,
            'color': color,
            'data': {
                'score': score,
                'wind_speed': wind_speed,
                'is_offshore': is_offshore,
                'hour': current_hour,
                'is_daytime': is_daytime
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Erreur vérification rapide: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Erreur de vérification',
            'decision': 'unknown'
        })

@app.route('/api/save_spot', methods=['POST'])
def api_save_spot():
    """Sauvegarder un spot personnalisé - VERSION CORRIGÉE"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Données manquantes'})

        favorites = []
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)

        import time
        spot_id_str = f"{data.get('name', '')}{data.get('lat', 0)}{data.get('lon', 0)}{time.time()}"
        spot_id = hashlib.md5(spot_id_str.encode('utf-8')).hexdigest()[:8]

        spot_data = {
            'id': spot_id,
            'name': data.get('name', 'Spot sans nom'),
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'type': data.get('type', 'custom'),
            'depth': data.get('depth', '?'),
            'description': data.get('description', 'Spot personnalisé'),
            'details': data.get('details', {}),
            'created_at': datetime.now().isoformat()
        }

        favorites.append(spot_data)

        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)

        return jsonify({
            'status': 'success',
            'id': spot_id,
            'message': 'Spot sauvegardé avec succès'
        })
    except Exception as e:
        print(f"❌ Erreur sauvegarde spot: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/distance_calculation')
def api_distance_calculation():
    """Calculer la distance entre deux points"""
    try:
        lat1 = float(request.args.get('lat1', 36.8065))
        lon1 = float(request.args.get('lon1', 10.1815))
        lat2 = float(request.args.get('lat2', 36.8065))
        lon2 = float(request.args.get('lon2', 10.1815))

        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        travel_time_minutes = round((distance / 50) * 60)

        return jsonify({
            'status': 'success',
            'distance_km': round(distance, 2),
            'travel_time_minutes': travel_time_minutes,
            'coordinates': {
                'from': {'lat': lat1, 'lon': lon1},
                'to': {'lat': lat2, 'lon': lon2}
            }
        })
    except Exception as e:
        print(f"❌ Erreur calcul distance: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/test_dashboard_data')
def api_test_dashboard_data():
    """Données de test pour le dashboard"""
    return jsonify({
        'status': 'success',
        'weather': {
            'temperature': 22.5,
            'feels_like': 23.1,
            'wind_speed': 12.3,
            'wind_direction_name': 'Nord-Est',
            'pressure': 1013,
            'condition_fr': 'Ensoleillé',
            'clouds': 15,
            'is_offshore': False
        },
        'prediction': {
            'score': 78,
            'text': 'Bonnes conditions pour pêcher',
            'color': '#f59e0b'
        },
        'instant_conditions': [
            {'icon': '🌅', 'label': 'Période', 'value': 'Jour'},
            {'icon': '🎣', 'label': 'Act. poisson', 'value': 'Élevée'},
            {'icon': '👥', 'label': 'Fréquentation', 'value': 'Moyenne'},
            {'icon': '🌡️', 'label': 'Eau estimée', 'value': '22°C'}
        ],
        'spot_details': {
            'current': 'Faible',
            'moonPhase': 'Premier quartier',
            'tide': 'Montante',
            'oxygen': '7.2 mg/L',
            'phytoplankton': 'Moyenne',
            'chlorophyll': '0.8 µg/L'
        },
        'timestamp': datetime.now().isoformat()
    })

# ===== API ALERTES EMAIL =====
@app.route('/api/alerts/subscribe', methods=['POST'])
def api_alerts_subscribe():
    """API pour s'abonner aux alertes - VERSION GMAIL"""
    try:
        if not request.data: return jsonify({'status':'error','message':'Aucune donnée reçue'}), 400
        try: data = request.get_json()
        except Exception: return jsonify({'status':'error','message':'Format JSON invalide'}), 400
        if not data: return jsonify({'status':'error','message':'Données manquantes'}), 400
        email = data.get('email', '').strip().lower(); preferences = data.get('preferences', {})
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'status':'error','message':'Adresse email invalide. Exemple: nom@domaine.com'}), 400
        subscriptions = []; alerts_file = ALERTS_FILE
        try:
            if os.path.exists(alerts_file):
                with open(alerts_file, 'r', encoding='utf-8') as f: subscriptions = json.load(f)
        except: subscriptions = []
        existing_index = -1
        for i, sub in enumerate(subscriptions):
            if sub.get('email') == email: existing_index = i; break
        import secrets; confirmation_id = f"SUB-{secrets.token_hex(6).upper()}"
        subscription_data = {
            'email':email,
            'preferences':{
                'excellent_conditions':preferences.get('excellentConditions',True),
                'seasonal_reminders':preferences.get('seasonalReminders',True),
                'weekly_tips':preferences.get('weeklyTips',False),
                'favorite_spots':preferences.get('favoriteSpots',True)
            },
            'confirmed':True,
            'confirmation_id':confirmation_id,
            'subscribed_at':datetime.now().isoformat(),
            'last_alert_sent':None,
            'alert_count':0,
            'active':True
        }
        if existing_index >= 0:
            subscriptions[existing_index] = subscription_data; operation = "mise à jour"
        else:
            subscriptions.append(subscription_data); operation = "création"
        try:
            os.makedirs(os.path.dirname(alerts_file), exist_ok=True)
            with open(alerts_file, 'w', encoding='utf-8') as f: json.dump(subscriptions, f, ensure_ascii=False, indent=2)
        except Exception:
            return jsonify({'status':'error','message':'Erreur technique lors de l\'enregistrement.'}), 500
        email_sent = False
        try: email_sent = send_confirmation_email_gmail(email, confirmation_id)
        except Exception: pass
        return jsonify({
            'status':'success',
            'message':f'Abonnement {operation} avec succès.',
            'confirmation_id':confirmation_id,
            'email_sent':email_sent,
            'email':email,
            'timestamp':datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status':'error','message':'Une erreur technique est survenue.','suggestion':'Veuillez réessayer dans quelques instants.'}), 500

@app.route('/api/alerts/unsubscribe', methods=['POST'])
def api_alerts_unsubscribe():
    """API pour se désabonner des alertes"""
    try:
        data = request.json; email = data.get('email', '').strip().lower()
        if not email: return jsonify({'status': 'error', 'message': 'Email manquant'})
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f: subscriptions = json.load(f)
            original_count = len(subscriptions); subscriptions = [sub for sub in subscriptions if sub['email'] != email]
            if len(subscriptions) < original_count:
                with open(ALERTS_FILE, 'w', encoding='utf-8') as f: json.dump(subscriptions, f, ensure_ascii=False, indent=2)
                return jsonify({'status': 'success', 'message': 'Désabonnement réussi'})
        return jsonify({'status': 'error', 'message': 'Email non trouvé'})
    except Exception as e:
        print(f"❌ Erreur désabonnement: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/alerts/status')
def api_alerts_status():
    """Vérifier le statut d'abonnement d'un email"""
    try:
        email = request.args.get('email', '').strip().lower()
        if not email: return jsonify({'status': 'error', 'message': 'Email manquant'})
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f: subscriptions = json.load(f)
            for sub in subscriptions:
                if sub['email'] == email:
                    return jsonify({'status':'success','subscribed':True,'data':sub})
        return jsonify({'status': 'success', 'subscribed': False})
    except Exception as e:
        print(f"❌ Erreur vérification statut: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin/email_logs')
def admin_email_logs():
    """Page admin pour voir les logs d'emails"""
    try:
        log_file = EMAIL_LOGS_FILE
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f: logs = json.load(f)
        else: logs = []
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return render_template('email_logs.html', logs=logs, count=len(logs))
    except Exception as e: return f"Erreur: {e}"

# ===== FONCTIONS DE MAINTENANCE DU CACHE =====
def cleanup_old_cache():
    """Nettoie les fichiers de cache expirés"""
    try:
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CACHE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f: cache_data = json.load(f)
                    if time.time() > cache_data.get('expires_at', 0): os.remove(filepath)
                except Exception: os.remove(filepath)
    except Exception: pass

# ===== ROUTES STATIQUES =====
@app.route('/static/js/leaflet.js')
def serve_leaflet_js():
    """Servir Leaflet localement si le CDN échoue"""
    try: return send_from_directory('static/js', 'leaflet.js')
    except: return '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>', 200, {'Content-Type': 'text/javascript'}

@app.route('/static/css/leaflet.css')
def serve_leaflet_css():
    """Servir Leaflet CSS localement si le CDN échoue"""
    try: return send_from_directory('static/css', 'leaflet.css')
    except: return '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>', 200, {'Content-Type': 'text/css'}

@app.route('/test_meteo_simple')
def test_meteo_simple(): return render_template('test_meteo_simple.html')

@app.route('/test_mobile_simple')
def test_mobile_simple(): return render_template('test_mobile_simple.html')

# ===== ROUTES SITEMAP ET ROBOTS (CORRIGÉES) =====
@app.route('/robots.txt')
def robots():
    """Fichier robots.txt ULTRA-SIMPLE pour débloquer Google"""
    robots_content = """User-agent: *
Allow: /

Sitemap: https://fishing-activity.onrender.com/sitemap.xml
"""
    response = make_response(robots_content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'; response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.route('/test-google-access')
def test_google_access():
    """Page spéciale pour vérifier l'accès Google"""
    html = f"""<!DOCTYPE html><html><head><title>Test Accès Google</title><meta name="robots" content="index, follow"></head><body><h1>✅ Page accessible à Google</h1><p>Heure: {datetime.now().isoformat()}</p><p><a href="/robots.txt" target="_blank">Voir robots.txt</a></p><p><a href="/sitemap.xml" target="_blank">Voir sitemap.xml</a></p></body></html>"""
    return html

@app.route('/sitemap.xml')
def sitemap(): return send_from_directory('static', 'sitemap.xml')

@app.route('/ping')
def ping(): return jsonify({'status':'ok','timestamp':datetime.now().isoformat(),'service':'fishing-predictor-pro'})

@app.route('/sitemap')
def sitemap_redirect(): return redirect('/sitemap.xml')

@app.route('/google-verification')
def google_verification():
    """Page de vérification pour Google"""
    return f"""<!DOCTYPE html><html><head><title>Google Verification Page</title><meta name="robots" content="index, follow"><meta name="googlebot" content="index, follow"></head><body><h1>✅ Googlebot Verification</h1><p>This page verifies that Googlebot can access the site.</p><p>Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p><p><a href="/">Return to homepage</a></p></body></html>"""

@app.route('/test-robots-access')
def test_robots_access():
    """Page pour tester l'accès robots.txt"""
    return """<!DOCTYPE html><html><head><title>Test Robots.txt Access</title></head><body><h1>Test d'accès Robots.txt</h1><p><a href="/robots.txt" target="_blank">Voir robots.txt</a></p><p><a href="https://fishing-activity.onrender.com/robots.txt" target="_blank">Voir robots.txt (URL complète)</a></p><p><a href="https://search.google.com/test/robots-txt" target="_blank">Tester avec l'outil Google</a></p><p><a href="/">Retour à l'accueil</a></p></body></html>"""

@app.route('/api/alerts/health')
def api_alerts_health():
    """Endpoint de santé pour vérifier le système d'alertes"""
    health_data = {
        'status':'healthy',
        'timestamp':datetime.now().isoformat(),
        'components':{
            'gmail_configured':bool(GMAIL_USER and GMAIL_PASSWORD),
            'alerts_file':os.path.exists(ALERTS_FILE),
            'email_logs':os.path.exists(EMAIL_LOGS_FILE),
            'data_dir':os.path.exists(config.DATA_DIR)
        }
    }
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r') as f:
                subscriptions = json.load(f); health_data['subscriptions_count'] = len(subscriptions)
    except: health_data['components']['alerts_file'] = 'corrupted'
    return jsonify(health_data)

# ===== NOUVELLES ROUTES POUR ADMIN GMAIL =====
@app.route('/admin/gmail_test')
def admin_gmail_test():
    """Page pour tester Gmail"""
    has_config = bool(GMAIL_USER and GMAIL_PASSWORD)
    return f"""<!DOCTYPE html><html><head><title>Test Gmail</title><style>body{{font-family:Arial,sans-serif;margin:20px;}}.success{{color:green;}}.error{{color:red;}}.test-form{{margin-top:20px;}}</style></head><body><h1>🔧 Test Configuration Gmail</h1><p>Gmail User défini: <strong class="{'success' if GMAIL_USER else 'error'}">{'✅ OUI' if GMAIL_USER else '❌ NON'}</strong></p><p>App Password défini: <strong class="{'success' if GMAIL_PASSWORD else 'error'}">{'✅ OUI' if GMAIL_PASSWORD else '❌ NON'}</strong></p><p>Email d'envoi: {EMAIL_FROM}</p><p>Nom d'envoi: {EMAIL_FROM_NAME}</p><div class="test-form"><h2>Test d'envoi</h2><form action="/admin/send_gmail_test" method="POST"><input type="email" name="email" placeholder="Votre email" required style="padding:8px;width:300px;"><button type="submit" style="padding:8px 16px;background:#3b82f6;color:white;border:none;border-radius:4px;">Envoyer un test Gmail</button></form></div><h2>API de test</h2><ul><li><a href="/api/test-gmail" target="_blank">/api/test-gmail</a> - Test complet Gmail</li><li><a href="/api/email-config" target="_blank">/api/email-config</a> - Configuration email</li><li><a href="/api/email-logs" target="_blank">/api/email-logs</a> - Logs d'emails</li></ul><h2>Logs</h2><a href="/admin/email_logs" target="_blank">Voir les logs d'emails</a><br><br><a href="/alerts">← Retour aux alertes</a></body></html>"""

@app.route('/admin/send_gmail_test', methods=['POST'])
def admin_send_gmail_test():
    """Envoie un email de test via Gmail"""
    try:
        email = request.form.get('email')
        if not email: return "❌ Email manquant"
        import secrets, time; confirmation_id = f"TEST-{int(time.time())}-{secrets.token_hex(4).upper()}"
        result = send_confirmation_email_gmail(email, confirmation_id)
        if result:
            return f"""<h1>✅ Email de test Gmail envoyé !</h1><p>Email: {email}</p><p>ID: {confirmation_id}</p><p><a href="/admin/gmail_test">← Retour au test Gmail</a></p>"""
        else:
            return f"""<h1>❌ Échec de l'envoi Gmail</h1><p>Impossible d'envoyer l'email à {email}</p><p>Vérifiez votre configuration Gmail dans .env</p><p><a href="/admin/gmail_test">← Retour au test Gmail</a></p>"""
    except Exception as e: return f"❌ Erreur: {str(e)}"

# ===== NOUVELLES ROUTES POUR DONNÉES RÉELLES =====

@app.route('/api/real_ocean_info')
def api_real_ocean_info():
    """Informations sur les données océanographiques RÉELLES"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))

        if REAL_OCEAN_ENABLED:
            all_data = real_ocean.get_all_fishing_data(lat, lon)

            response = {
                'status': 'success',
                'location': {'lat': lat, 'lon': lon},
                'has_real_data': True,
                'sources': {
                    'sst': all_data.get('sea_temperature', {}).get('source', 'unknown'),
                    'chlorophyll': all_data.get('chlorophyll', {}).get('source', 'unknown'),
                    'weather': all_data.get('marine_weather', {}).get('source', 'unknown')
                },
                'data': {
                    'sea_temperature': all_data.get('sea_temperature', {}),
                    'chlorophyll': all_data.get('chlorophyll', {}),
                    'marine_weather': all_data.get('marine_weather', {})
                },
                'timestamp': datetime.now().isoformat()
            }

            sst_source = response['sources']['sst'].lower()
            if 'climatologie' in sst_source or 'moyenne' in sst_source:
                response['data_type'] = 'climatology'
                response['data_note'] = 'Données climatologiques réelles (moyennes mensuelles)'
            elif 'open-meteo' in sst_source or 'noaa' in sst_source:
                response['data_type'] = 'real_time'
                response['data_note'] = 'Données satellites en temps réel'
            else:
                response['data_type'] = 'estimated'
                response['data_note'] = 'Données estimées par modèle'

            return jsonify(response)
        else:
            return jsonify({
                'status': 'error',
                'message': 'Module données réelles non disponible',
                'has_real_data': False
            })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/forecast_10days')
def api_forecast_10days():
    """Prévisions 10 jours - utilise données réelles si disponibles"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')

        print(f"📊 Prévisions 10 jours demandées pour ({lat}, {lon}) - {species}")

        # Essayer d'abord les données réelles Open-Meteo
        try:
            forecast = get_openmeteo_10day_forecast(lat, lon)
            if forecast['success']:
                return process_real_forecast(forecast['data'], lat, lon, species)
        except Exception as e:
            print(f"⚠️ Prévisions réelles échouées: {e}")

        # Fallback sur simulation
        return api_forecast_10days_fallback(lat, lon, species)

    except Exception as e:
        print(f"❌ Erreur prévisions: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

def get_openmeteo_10day_forecast(lat: float, lon: float) -> dict:
    """Récupère prévisions Open-Meteo (données horaires incluses)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            'latitude': lat,
            'longitude': lon,
            'hourly': 'temperature_2m,relativehumidity_2m,precipitation,windspeed_10m,winddirection_10m,weathercode',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max,winddirection_10m_dominant,weathercode',
            'timezone': 'Africa/Tunis',
            'forecast_days': 10
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            return {
                'success': True,
                'data': response.json(),
                'source': 'Open-Meteo',
                'timestamp': datetime.now().isoformat()
            }
        else:
            print(f"⚠️ Open-Meteo erreur {response.status_code}")
            return {'success': False}

    except Exception as e:
        print(f"⚠️ Open-Meteo exception: {e}")
        return {'success': False}

def process_real_forecast(forecast_data: dict, lat: float, lon: float, species: str) -> dict:
    """Transforme prévisions réelles pour la pêche avec pénalité vent et fiabilité"""
    daily = forecast_data.get('daily', {})
    hourly = forecast_data.get('hourly', {})
    days = len(daily.get('time', []))

    results = []

    # Récupérer la température de l'eau (si possible)
    water_temp_base = 20.0
    if REAL_OCEAN_ENABLED:
        try:
            sst_data = real_ocean.get_sea_surface_temperature(lat, lon)
            water_temp_base = sst_data.get('value', 20.0)
        except Exception:
            water_temp_base = 20.0

    for i in range(days):
        date_str = daily['time'][i]
        date = datetime.strptime(date_str, '%Y-%m-%d')

        # Données quotidiennes
        temp_max = daily['temperature_2m_max'][i]
        temp_min = daily['temperature_2m_min'][i]
        temp_avg = (temp_max + temp_min) / 2

        wind_speed = daily['windspeed_10m_max'][i]
        wind_direction = daily['winddirection_10m_dominant'][i]
        weather_code = daily.get('weathercode', [0] * days)[i]
        precipitation = daily.get('precipitation_sum', [0] * days)[i]

        condition_map = {
            0: 'Ciel dégagé', 1: 'Principalement clair', 2: 'Partiellement nuageux',
            3: 'Couvert', 45: 'Brouillard', 51: 'Bruine légère', 53: 'Bruine modérée',
            61: 'Pluie légère', 63: 'Pluie modérée', 65: 'Pluie forte',
            80: 'Averses légères', 81: 'Averses modérées', 95: 'Orage'
        }
        condition = condition_map.get(weather_code, 'Inconnu')

        # Température de l'eau ajustée
        water_temp = water_temp_base + (temp_avg - 20) * 0.1

        # Calcul de la hauteur des vagues
        wave_height = calculate_wave_height(wind_speed)

        # Construction des données horaires de vent
        hourly_wind = []
        if hourly and 'time' in hourly:
            for j, time_str in enumerate(hourly['time']):
                if time_str.startswith(date_str):
                    h = int(time_str[11:13])
                    speed = hourly['windspeed_10m'][j]
                    direction = hourly['winddirection_10m'][j]
                    direction_info = get_wind_direction_name(direction)
                    hourly_wind.append({
                        'time': f"{h:02d}h",
                        'speed_kmh': round(speed, 1),
                        'direction_deg': direction,
                        'direction_name': direction_info['name'],
                        'direction_abbr': direction_info['abbreviation'],
                        'direction_icon': direction_info['icon']
                    })

        # Construction des données pour le prédicteur
        weather_for_prediction = {
            'temperature': temp_avg,
            'wind_speed': wind_speed / 3.6,  # conversion km/h en m/s
            'wind_direction': wind_direction,
            'pressure': 1015,  # valeur par défaut
            'wave_height': wave_height,
            'turbidity': 1.0 + (precipitation * 0.1),
            'humidity': 60 + (precipitation * 5),
            'condition': 'Clear' if weather_code == 0 else 'Rain' if precipitation > 1 else 'Clouds',
            'water_temperature': water_temp,
            'salinity': config.SALINITY_MEDITERRANEAN,
            'current_speed': 0.2
        }

        # Prédiction
        prediction = predictor.predict_daily_activity(lat, lon, date, species, weather_for_prediction)

        # Récupérer le score de base (déjà en pourcentage 0-100)
        base_score = prediction['score']

        # === CORRECTION : AJOUTER UNE PÉNALITÉ POUR VENT FORT ===
        wind_penalty = 1.0
        if wind_speed > 40:
            wind_penalty = 0.3  # Très forte pénalité
            alert = "VENT TRÈS FORT - Pêche dangereuse"
        elif wind_speed > 30:
            wind_penalty = 0.5  # Forte pénalité
            alert = "VENT FORT - Conditions difficiles"
        elif wind_speed > 20:
            wind_penalty = 0.7  # Pénalité modérée
            alert = "VENT MODÉRÉ - Prudence"
        elif wind_speed > 15:
            wind_penalty = 0.9  # Légère pénalité
            alert = "Vent sensible"
        else:
            alert = "Vent favorable"

        # Appliquer la pénalité
        final_score = int(round(base_score * wind_penalty))

        # S'assurer que le score reste dans des limites raisonnables
        final_score = max(10, min(98, final_score))

        print(f"📊 Jour {i+1}: vent={wind_speed}km/h, base={base_score}%, penalty={wind_penalty:.2f}, final={final_score}% - {alert}")

        # Définir la confiance selon l'échéance
        day_num = i + 1
        if day_num == 1:
            confidence = 0.95
        elif day_num == 2:
            confidence = 0.90
        elif day_num == 3:
            confidence = 0.85
        elif day_num == 4:
            confidence = 0.75
        elif day_num == 5:
            confidence = 0.65
        elif day_num == 6:
            confidence = 0.55
        elif day_num == 7:
            confidence = 0.50
        elif day_num == 8:
            confidence = 0.45
        elif day_num == 9:
            confidence = 0.40
        else:
            confidence = 0.35

        note = None
        if day_num > 5:
            note = "Données simulées – tendance uniquement"

        results.append({
            'day': day_num,
            'date': date_str,
            'score': final_score,  # Score pénalisé
            'confidence': confidence,
            'note': note,
            'weather': {
                'temp_avg': round(temp_avg, 1),
                'temp_min': round(temp_min, 1),
                'temp_max': round(temp_max, 1),
                'condition': condition,
                'wind_speed': round(wind_speed, 1),
                'wind_direction': get_wind_direction_name(wind_direction)['name'],
                'wind_direction_deg': wind_direction,
                'precipitation': round(precipitation, 1),
                'water_temperature': round(water_temp, 1),
                'wave_height': round(wave_height, 2)
            },
            'wind': {
                'speed': round(wind_speed, 1),
                'direction': wind_direction,
                'direction_name': get_wind_direction_name(wind_direction)['name']
            },
            'best_hours': prediction['best_fishing_hours'][:2],
            'recommendation': alert,  # Message d'alerte
            'data_source': 'real_forecast',
            'hourly_wind': hourly_wind  # ← AJOUT CRUCIAL DES DONNÉES HORAIRES
        })

    scores = [day['score'] for day in results]

    return jsonify({
        'status': 'success',
        'forecast': results,
        'location': f'Position ({lat:.4f}, {lon:.4f})',
        'species': species,
        'average_score': int(round(sum(scores) / len(scores))) if scores else 0,
        'source': 'Open-Meteo (données réelles)',
        'trend': 'improving' if len(scores) > 1 and scores[-1] > scores[0] else 'stable',
        'timestamp': datetime.now().isoformat()
    })
def generate_forecast_weather(lat: float, lon: float, date: datetime) -> dict:
    """Génère des données météo variées pour les prévisions (fallback)"""
    day_of_year = date.timetuple().tm_yday
    unique_key = f"{lat:.2f}_{lon:.2f}_{day_of_year}"
    unique_hash = int(hashlib.md5(unique_key.encode()).hexdigest()[:8], 16)
    month = date.month
    if 6 <= month <= 8: base_temp = 25 + (lat - 36.0) * 0.5
    elif 12 <= month or month <= 2: base_temp = 15 + (lat - 36.0) * 0.3
    else: base_temp = 20 + (lat - 36.0) * 0.4
    temp_variation = ((unique_hash % 100) / 100) * 6 - 3; temperature = base_temp + temp_variation
    wind_speed = 10 + ((unique_hash // 100) % 100) / 100 * 15
    wind_direction = (unique_hash % 360); wind_direction_info = get_wind_direction_name(wind_direction)
    pressure = 1015 + ((unique_hash // 10000) % 100) / 100 * 20 - 10
    conditions_list = ['Clear', 'Clouds', 'Partly Cloudy', 'Mostly Sunny', 'Light Rain']
    conditions_fr_list = ['Ciel dégagé', 'Nuageux', 'Partiellement nuageux', 'Très ensoleillé', 'Pluie légère']
    condition_idx = (unique_hash // 1000) % len(conditions_list)
    return {'temperature':round(temperature,1),'wind_speed':round(wind_speed,1),'wind_direction':wind_direction,'wind_direction_name':wind_direction_info['name'],'pressure':round(pressure,1),'condition':conditions_list[condition_idx],'condition_fr':conditions_fr_list[condition_idx],'humidity':60+(unique_hash%20),'wave_height':round(0.3+(unique_hash%100)/100*1.2,1),'turbidity':1.0+(unique_hash%10)/10}

def assess_fishing_suitability(bathymetry) -> dict:
    depth = bathymetry.get('depth',10); seabed = bathymetry.get('seabed_type','mixed')
    suitability = {'surfcasting':depth<10 and seabed in ['sand','mixed'],'rock_fishing':seabed in ['rock','mixed'] and depth<30,'boat_fishing':depth>5,'spearfishing':depth<20 and seabed in ['rock','grass']}
    if suitability.get('surfcasting'): best_technique="surfcasting"
    elif suitability.get('rock_fishing'): best_technique="pêche depuis les rochers"
    elif suitability.get('boat_fishing'): best_technique="pêche en bateau"
    else: best_technique="pêche à soutenir"
    return {**suitability,'best_technique':best_technique,'risk_level':'low' if depth>3 else 'medium'}

def is_depth_optimal(depth: float, species: str) -> bool:
    optimal_ranges = {'loup':(3,20),'daurade':(2,15),'pageot':(10,60),'thon':(10,100),'sar':(5,25)}
    if species in optimal_ranges:
        min_depth, max_depth = optimal_ranges[species]; return min_depth <= depth <= max_depth
    return 5 <= depth <= 20

@app.route('/api/quick-test-wekeo')
def quick_test_wekeo():
    """Test RAPIDE WEkEO - PAS besoin de modifier le code existant"""
    try:
        lat = 36.8065
        lon = 10.1815

        print("\n⚡ TEST RAPIDE WEKEO - DÉBUT ⚡")
        print(f"1. WEKEO_ENABLED = {WEKEO_ENABLED}")

        result = {}

        if WEKEO_ENABLED:
            print("2. Appel direct à wekeo_enhancer.get_wind_data()...")
            try:
                wind_data = wekeo_enhancer.get_wind_data(lat, lon)
                print(f"   ✅ SUCCÈS: {wind_data}")
                result['wekeo'] = wind_data
            except Exception as e:
                print(f"   ❌ ERREUR: {e}")
                result['wekeo_error'] = str(e)
        else:
            print("2. WEkEO désactivé")
            result['wekeo'] = "disabled"

        print("3. Test get_marine_data_multi_source()...")
        marine_data = get_marine_data_multi_source(lat, lon)
        print(f"   📊 Résultat: source={marine_data.get('data_source')}, vent={marine_data.get('wind_speed_kmh')} km/h")
        result['marine_data'] = marine_data

        print("⚡ TEST RAPIDE WEKEO - FIN ⚡\n")

        return jsonify({
            'status': 'success',
            'test': result,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        print(f"❌ ERREUR test rapide: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# ===== ROUTE API POUR TEST BATHYMÉTRIE DEPUIS F12 =====
@app.route('/api/depth')
def api_depth():
    """API pour tester la bathymétrie depuis la console F12"""
    try:
        lat = float(request.args.get('lat', 36.908))
        lon = float(request.args.get('lon', 10.288))
        
        # Vérifier si le module est disponible
        if not BATHYMETRY_ENABLED:
            return jsonify({
                'error': 'Module bathymétrie non disponible',
                'depth': 4.0,  # Valeur par défaut
                'source': 'Valeur par défaut',
                'confidence': 0.5
            }), 200
        
        # Utiliser l'instance globale importée
        result = gebco.get_depth_with_fallback(lat, lon)
        
        # Ajouter des infos de debug
        try:
            spot_check = gebco._tunisia_expert(lat, lon)
            spot_active = spot_check['success']
            spot_name = spot_check.get('source', 'Aucun')
        except:
            spot_active = False
            spot_name = 'Erreur vérification'
        
        response = {
            'depth': result['depth'],
            'source': result['source'],
            'confidence': result.get('confidence', 0),
            'accuracy': result.get('accuracy', 'moyenne'),
            'debug': {
                'spot_expert_active': spot_active,
                'spot_name': spot_name,
                'coordinates': {'lat': lat, 'lon': lon},
                'zone': result.get('zone', 'Inconnue')
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"❌ Erreur API depth: {e}")
        return jsonify({
            'error': str(e),
            'depth': 4.0,  # Fallback
            'source': 'Fallback',
            'confidence': 0.3
        }), 200  # 200 pour éviter l'erreur dans la console


@app.route('/api/bathymetry_test')
def api_bathymetry_test():
    """Page de test HTML pour la bathymétrie"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Bathymétrie</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #1a1a2e; color: white; }
            .container { max-width: 600px; margin: auto; padding: 20px; background: #16213e; border-radius: 10px; }
            input { padding: 10px; margin: 5px; width: 200px; background: #0f3460; color: white; border: 1px solid #e94560; }
            button { padding: 10px 20px; background: #e94560; color: white; border: none; cursor: pointer; }
            #result { margin-top: 20px; padding: 15px; background: #0f3460; border-radius: 5px; white-space: pre-wrap; }
            .success { color: #4caf50; }
            .warning { color: #ff9800; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌊 Test Bathymétrie Tunisie</h1>
            <div>
                <label>Latitude:</label>
                <input type="number" id="lat" step="0.001" value="36.908">
                <label>Longitude:</label>
                <input type="number" id="lon" step="0.001" value="10.288">
                <button onclick="testDepth()">Tester</button>
            </div>
            <div>
                <button onclick="testGammarth()">Marina Gammarth</button>
                <button onclick="testSousse()">Sousse Port</button>
                <button onclick="testBizerte()">Bizerte</button>
            </div>
            <div id="result"></div>
        </div>
        <script>
            async function testDepth() {
                const lat = document.getElementById('lat').value;
                const lon = document.getElementById('lon').value;
                const resultDiv = document.getElementById('result');
                
                resultDiv.innerHTML = 'Chargement...';
                
                try {
                    const response = await fetch(`/api/depth?lat=${lat}&lon=${lon}`);
                    const data = await response.json();
                    
                    let html = '<strong>Résultat:</strong><br>';
                    html += `Profondeur: <span class="success">${data.depth} m</span><br>`;
                    html += `Source: ${data.source}<br>`;
                    html += `Confiance: ${data.confidence*100}%<br>`;
                    html += `Précision: ${data.accuracy}<br>`;
                    html += `<hr>`;
                    html += `<strong>Debug:</strong><br>`;
                    html += `Spot expert actif: ${data.debug.spot_expert_active ? '✅' : '❌'}<br>`;
                    html += `Spot: ${data.debug.spot_name}<br>`;
                    html += `Zone: ${data.debug.zone}<br>`;
                    
                    if (data.debug.spot_expert_active) {
                        html += `<p class="success">✅ SPOT EXPERT ACTIVÉ !</p>`;
                    } else {
                        html += `<p class="warning">⚠️ Spot expert NON activé</p>`;
                    }
                    
                    resultDiv.innerHTML = html;
                } catch (e) {
                    resultDiv.innerHTML = `Erreur: ${e.message}`;
                }
            }
            
            function testGammarth() {
                document.getElementById('lat').value = 36.908;
                document.getElementById('lon').value = 10.288;
                testDepth();
            }
            
            function testSousse() {
                document.getElementById('lat').value = 35.8213;
                document.getElementById('lon').value = 10.6387;
                testDepth();
            }
            
            function testBizerte() {
                document.getElementById('lat').value = 37.27;
                document.getElementById('lon').value = 9.87;
                testDepth();
            }
            
            // Test automatique au chargement
            window.onload = testGammarth;
        </script>
    </body>
    </html>
    """

# ===== DÉMARRAGE DE L'APPLICATION =====
if __name__=='__main__':
    print("\n" + "="*60)
    print("🎣 FISHING PREDICTOR PRO - DÉMARRAGE")
    print("="*60)
    email_ok = test_gmail_configuration()
    if not email_ok:
        print("\n⚠️ ATTENTION: La configuration Gmail a échoué!")
        print("   Les emails NE seront PAS envoyés, mais l'application démarrera.")
    else: print("\n✅ Configuration Gmail validée!")
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.STATIC_DIR + '/js', exist_ok=True)
    os.makedirs(config.STATIC_DIR + '/css', exist_ok=True)
    os.makedirs(config.TEMPLATES_DIR, exist_ok=True)
    for file_path in [ALERTS_FILE, FAVORITES_FILE, EMAIL_LOGS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f: json.dump([], f, ensure_ascii=False, indent=2)
    try: config.validate_config()
    except Exception as e: print(f"⚠️ Validation config: {e}")
    cleanup_old_cache()
    print("\n🚀 DÉMARRAGE DU SERVEUR...")
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)