from flask import Flask, render_template, request, jsonify, send_from_directory, make_response, redirect
from datetime import datetime, timedelta
import math, random, json, os, time, concurrent.futures, hashlib
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from advanced_predictor import ScientificFishingPredictor

# Import de la configuration centralisée
from config import config

app = Flask(__name__, template_folder='templates', static_folder='static')
predictor = ScientificFishingPredictor()

# ===== CONFIGURATION EMAIL GMAIL =====
GMAIL_USER = config.GMAIL_USER
GMAIL_PASSWORD = config.GMAIL_APP_PASSWORD
EMAIL_CONFIG = config.EMAIL_CONFIG

OPENWEATHER_API_KEY = config.OPENWEATHER_API_KEY
STORMGLASS_API_KEY = config.STORMGLASS_API_KEY
WORLDTIDES_API_KEY = config.WORLDTIDES_API_KEY
NOMINATIM_API = "https://nominatim.openstreetmap.org/reverse"
FAVORITES_FILE = config.FAVORITES_FILE
ALERTS_FILE = config.ALERTS_FILE

# ===== CONFIGURATION DE LIMITATION D'APPELS API =====
API_RATE_LIMITS = {
    'openweather': {
        'max_per_hour': 60,
        'max_per_day': 1000,
        'cache_duration': 30 * 60,
        'use_cache_only': False,
        'count_today': 0,
        'last_reset': None
    },
    'stormglass': {
        'max_per_day': 10,
        'cache_duration': 6 * 60 * 60,
        'use_cache_only': True
    },
    'worldtides': {
        'max_per_day': 10,
        'cache_duration': 6 * 60 * 60,
        'use_cache_only': True
    },
    'nominatim': {
        'max_per_hour': 1,
        'cache_duration': 24 * 60 * 60,
        'use_cache_only': False
    },
    'emodnet': {
        'max_per_hour': 10,
        'cache_duration': 7 * 24 * 60 * 60,
        'use_cache_only': True
    }
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
        
        cache_data = {
            'data': data,
            'timestamp': time.time(),
            'expires_at': time.time() + (duration_hours * 3600),
            'api_name': api_name,
            'params': params
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        
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
        
        if not os.path.exists(cache_file):
            return None
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        current_time = time.time()
        if current_time > cache_data.get('expires_at', 0):
            os.remove(cache_file)
            return None
        
        cache_age = current_time - cache_data.get('timestamp', 0)
        max_age_seconds = max_age_hours * 3600
        
        if cache_age > max_age_seconds:
            return None
        
        print(f"📦 Données chargées depuis le cache: {api_name}")
        return cache_data['data']
    
    except Exception as e:
        print(f"⚠️ Erreur chargement cache: {e}")
        return None

# ===== CACHE MÉMOIRE POUR DONNÉES FRÉQUEMMENT UTILISÉES =====
weather_cache = {}
WEATHER_CACHE_DURATION = config.WEATHER_CACHE_DURATION

WEATHER_CONDITIONS_FR = {
    'Clear': 'Ciel dégagé',
    'Sunny': 'Ensoleillé',
    'Clouds': 'Nuageux',
    'Cloudy': 'Nuageux',
    'Rain': 'Pluie',
    'Drizzle': 'Bruine',
    'Thunderstorm': 'Orage',
    'Snow': 'Neige',
    'Mist': 'Brume',
    'Fog': 'Brouillard',
    'Haze': 'Brume',
    'Dust': 'Poussiéreux',
    'Smoke': 'Fumée',
    'Ash': 'Cendres',
    'Squall': 'Rafales',
    'Tornado': 'Tornade'
}

# ===== FONCTIONS EMAIL GMAIL =====

def send_gmail(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
    """Envoie un email via Gmail SMTP"""
    try:
        if not EMAIL_CONFIG['enabled']:
            print(f"⚠️ Envoi d'email désactivé, email non envoyé à: {to_email}")
            return False
        
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['sender_email']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Ajouter les versions texte et HTML
        if text_content:
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Connexion au serveur SMTP
        print(f"📧 Connexion à Gmail SMTP...")
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.ehlo()
        
        if EMAIL_CONFIG.get('use_tls', True):
            server.starttls()
            server.ehlo()
        
        # Authentification
        print(f"📧 Authentification avec: {GMAIL_USER}")
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        
        # Envoi de l'email
        print(f"📧 Envoi de l'email à: {to_email}")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email envoyé avec succès à: {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur envoi email Gmail: {e}")
        return False

def send_confirmation_email(email: str, confirmation_id: str) -> bool:
    """Envoie un email de confirmation d'abonnement via Gmail"""
    try:
        timestamp = datetime.now().strftime('%d/%m/%Y à %H:%M')
        
        # Contenu HTML de l'email
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Confirmation d'abonnement - Fishing Predictor Pro</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.9em; }}
                .confirmation-id {{ background: #e0f2fe; padding: 15px; border-radius: 5px; font-family: monospace; font-weight: bold; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎣 Fishing Predictor Pro</h1>
                <h2>Confirmation d'abonnement</h2>
            </div>
            <div class="content">
                <p>Bonjour,</p>
                
                <p>Merci de vous être abonné aux alertes de pêche de <strong>Fishing Predictor Pro</strong> !</p>
                
                <p><strong>✅ Votre abonnement a été confirmé avec succès.</strong></p>
                
                <div class="confirmation-id">
                    ID de confirmation : {confirmation_id}<br>
                    Date : {timestamp}
                </div>
                
                <p>Vous recevrez désormais des alertes par email lorsque :</p>
                <ul>
                    <li>🎯 Les conditions de pêche seront excellentes (score ≥ 85%)</li>
                    <li>🌸 Les saisons de pêche changent</li>
                    <li>📅 Des événements de pêche spéciaux sont prévus</li>
                </ul>
                
                <p style="text-align: center;">
                    <a href="http://localhost:5000" class="button">Consulter les prédictions</a>
                </p>
                
                <p><strong>Pour gérer vos préférences ou vous désabonner :</strong><br>
                Visitez la page <a href="http://localhost:5000/alerts">Alertes Intelligentes</a> ou cliquez sur le lien de désabonnement présent dans chaque email.</p>
                
                <p>Bonne pêche ! 🐟</p>
                
                <p><em>L'équipe Fishing Predictor Pro</em></p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé à {email}</p>
                <p>© 2024 Fishing Predictor Pro - Tous droits réservés</p>
                <p><small>Vous recevez cet email car vous vous êtes abonné aux alertes sur notre site.</small></p>
            </div>
        </body>
        </html>
        """
        
        # Version texte simple
        text_content = f"""
        Confirmation d'abonnement - Fishing Predictor Pro
        
        Bonjour,
        
        Merci de vous être abonné aux alertes de pêche de Fishing Predictor Pro !
        
        ✅ Votre abonnement a été confirmé avec succès.
        
        ID de confirmation : {confirmation_id}
        Date : {timestamp}
        
        Vous recevrez désormais des alertes par email lorsque les conditions de pêche seront excellentes.
        
        Pour gérer vos préférences ou vous désabonner :
        Visitez http://localhost:5000/alerts ou cliquez sur le lien de désabonnement présent dans chaque email.
        
        Bonne pêche !
        
        L'équipe Fishing Predictor Pro
        
        ---
        Cet email a été envoyé à {email}
        © 2024 Fishing Predictor Pro
        """
        
        # Envoyer l'email
        email_sent = send_gmail(
            to_email=email,
            subject="🎣 Confirmation d'abonnement aux alertes - Fishing Predictor Pro",
            html_content=html_content,
            text_content=text_content
        )
        
        # Sauvegarder le log
        save_email_log(email, 'confirmation', confirmation_id, email_sent)
        
        return email_sent
        
    except Exception as e:
        print(f"❌ Erreur préparation email: {e}")
        return False

def save_email_log(email: str, email_type: str, confirmation_id: str, sent: bool):
    """Sauvegarde les logs d'emails envoyés"""
    try:
        log_file = config.EMAIL_LOGS_FILE
        os.makedirs(config.DATA_DIR, exist_ok=True)
        
        logs = []
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        log_entry = {
            'to': email,
            'type': email_type,
            'confirmation_id': confirmation_id,
            'sent': sent,
            'timestamp': datetime.now().isoformat(),
            'server': 'Gmail SMTP'
        }
        
        logs.append(log_entry)
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        print(f"📋 Log email sauvegardé: {email} - {'✅ Envoyé' if sent else '❌ Échec'}")
        
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde log email: {e}")

# ===== FONCTIONS AVEC GESTION DE LIMITATION =====

def get_openweather_data_with_limits(lat: float, lon: float):
    """Récupère les données météo avec gestion des limites d'API"""
    params = {'lat': lat, 'lon': lon}
    
    cached_data = load_from_cache('openweather', params, max_age_hours=1)
    if cached_data:
        return {'success': True, 'weather': cached_data, 'source': 'cache'}
    
    limits = API_RATE_LIMITS['openweather']
    
    if limits.get('use_cache_only', False):
        print("⚠️ OpenWeatherMap: Mode cache seulement activé")
        return get_fallback_weather_data(lat, lon)
    
    if limits['count_today'] >= limits['max_per_day']:
        print(f"⚠️ Limite quotidienne OpenWeather atteinte: {limits['count_today']}/{limits['max_per_day']}")
        return get_fallback_weather_data(lat, lon)
    
    try:
        print(f"🌤️ Appel OpenWeatherMap pour: {lat}, {lon}")
        url = "https://api.openweathermap.org/data/2.5/weather"
        params_api = {
            'lat': lat,
            'lon': lon,
            'appid': OPENWEATHER_API_KEY,
            'units': 'metric',
            'lang': 'fr'
        }
        
        response = requests.get(url, params=params_api, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Données OpenWeatherMap reçues: {data['name']}")
            
            API_RATE_LIMITS['openweather']['count_today'] += 1
            
            wind_deg = data['wind'].get('deg', 0)
            wind_direction = get_wind_direction_name(wind_deg)
            wind_impact = get_wind_fishing_impact(wind_deg, lat, lon)
            
            weather_info = {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'pressure': data['main']['pressure'],
                'humidity': data['main']['humidity'],
                'wind_speed': data['wind']['speed'] * 3.6,
                'wind_direction': wind_deg,
                'wind_direction_abbr': wind_direction['abbreviation'],
                'wind_direction_name': wind_direction['name'],
                'wind_direction_icon': wind_direction['icon'],
                'wind_fishing_impact': wind_impact,
                'wind_offshore': is_wind_offshore(lat, lon, wind_deg),
                'wind_onshore': is_wind_onshore(lat, lon, wind_deg),
                'condition': data['weather'][0]['main'],
                'condition_description': data['weather'][0]['description'],
                'condition_fr': WEATHER_CONDITIONS_FR.get(data['weather'][0]['main'], data['weather'][0]['main']),
                'icon': data['weather'][0]['icon'],
                'clouds': data['clouds']['all'],
                'visibility': data.get('visibility', 10000) / 1000,
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).isoformat(),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).isoformat(),
                'location': data['name'],
                'country': data['sys']['country'],
                'timestamp': datetime.now().isoformat(),
                'score': calculate_weather_score({
                    'temperature': data['main']['temp'],
                    'wind_speed': data['wind']['speed'] * 3.6,
                    'pressure': data['main']['pressure'],
                    'condition': data['weather'][0]['main'],
                    'wind_direction': wind_deg
                })
            }
            
            save_to_cache('openweather', {'lat': lat, 'lon': lon}, weather_info, 12)
            
            return {'success': True, 'weather': weather_info, 'source': 'api'}
        
        elif response.status_code == 429:
            print("⚠️ OpenWeatherMap: Limite d'API atteinte (429)")
            API_RATE_LIMITS['openweather']['use_cache_only'] = True
            return get_fallback_weather_data(lat, lon)
        
        else:
            print(f"⚠️ OpenWeatherMap erreur HTTP: {response.status_code}")
            return get_fallback_weather_data(lat, lon)
            
    except Exception as e:
        print(f"⚠️ Exception OpenWeatherMap: {e}")
        return get_fallback_weather_data(lat, lon)

def get_fallback_weather_data(lat: float, lon: float):
    """Données météo de secours (modèle cohérent)"""
    print(f"🔄 Utilisation des données de secours pour {lat}, {lon}")
    return generate_consistent_weather(lat, lon)

def get_wind_direction_name(degrees: float) -> dict:
    """Convertit les degrés en direction du vent"""
    directions = [
        ('N', 'Nord', 0, 11.25),
        ('NNE', 'Nord-Nord-Est', 11.25, 33.75),
        ('NE', 'Nord-Est', 33.75, 56.25),
        ('ENE', 'Est-Nord-Est', 56.25, 78.75),
        ('E', 'Est', 78.75, 101.25),
        ('ESE', 'Est-Sud-Est', 101.25, 123.75),
        ('SE', 'Sud-Est', 123.75, 146.25),
        ('SSE', 'Sud-Sud-Est', 146.25, 168.75),
        ('S', 'Sud', 168.75, 191.25),
        ('SSO', 'Sud-Sud-Ouest', 191.25, 213.75),
        ('SO', 'Sud-Ouest', 213.75, 236.25),
        ('OSO', 'Ouest-Sud-Ouest', 236.25, 258.75),
        ('O', 'Ouest', 258.75, 281.25),
        ('ONO', 'Ouest-Nord-Ouest', 281.25, 303.75),
        ('NO', 'Nord-Ouest', 303.75, 326.25),
        ('NNO', 'Nord-Nord-Ouest', 326.25, 348.75),
        ('N', 'Nord', 348.75, 360)
    ]
    
    degrees = degrees % 360
    
    for abbrev, name, min_deg, max_deg in directions:
        if min_deg <= degrees <= max_deg:
            return {
                'abbreviation': abbrev,
                'name': name,
                'degrees': degrees,
                'icon': get_wind_direction_icon(degrees)
            }
    
    return {'abbreviation': 'N', 'name': 'Nord', 'degrees': degrees, 'icon': '⬆️'}

def get_wind_direction_icon(degrees: float) -> str:
    """Retourne un emoji pour la direction du vent"""
    if 337.5 <= degrees <= 360 or 0 <= degrees < 22.5:
        return '⬆️'
    elif 22.5 <= degrees < 67.5:
        return '↗️'
    elif 67.5 <= degrees < 112.5:
        return '➡️'
    elif 112.5 <= degrees < 157.5:
        return '↘️'
    elif 157.5 <= degrees < 202.5:
        return '⬇️'
    elif 202.5 <= degrees < 247.5:
        return '↙️'
    elif 247.5 <= degrees < 292.5:
        return '⬅️'
    else:
        return '↖️'

def get_wind_fishing_impact(degrees: float, spot_lat: float = 36.8, spot_lon: float = 10.1) -> str:
    """Détermine l'impact du vent sur la pêche selon la direction"""
    direction = get_wind_direction_name(degrees)
    abbrev = direction['abbreviation']
    
    if abbrev in ['N', 'NNE', 'NE']:
        return "Vent de nord - Bon pour la pêche côtière, apporte des nutriments"
    elif abbrev in ['E', 'ENE', 'ESE']:
        return "Vent d'est - Peut rendre la mer agitée, prudence"
    elif abbrev in ['S', 'SSE', 'SSO']:
        return "Vent du sud - Chaud, peut réduire l'activité des poissons"
    elif abbrev in ['O', 'ONO', 'OSO']:
        return "Vent d'ouest - Favorable pour le surfcasting"
    elif abbrev in ['NO', 'NNO']:
        return "Vent de nord-ouest - Excellent pour la pêche, mer claire"
    elif abbrev in ['SO', 'SE']:
        return "Vent de sud/sud-est - Apporte eaux chaudes, bon pour certaines espèces"
    else:
        return "Direction variable - Conditions moyennes"

def is_wind_offshore(lat: float, lon: float, wind_direction: float) -> bool:
    """Détermine si le vent est offshore (vent de terre) - DANGEREUX"""
    direction_info = get_wind_direction_name(wind_direction)
    return direction_info['abbreviation'] in ['E', 'ENE', 'ESE']

def is_wind_onshore(lat: float, lon: float, wind_direction: float) -> bool:
    """Détermine si le vent est onshore (vent de mer)"""
    direction_info = get_wind_direction_name(wind_direction)
    return direction_info['abbreviation'] in ['O', 'ONO', 'OSO', 'NO', 'SO']

def get_cached_weather(lat: float, lon: float, force_refresh: bool = False):
    """Récupère les données météo avec cache intelligent et limitation"""
    cache_key = f"{lat:.4f}_{lon:.4f}"
    now = time.time()
    
    if not force_refresh and cache_key in weather_cache:
        cached_data, timestamp = weather_cache[cache_key]
        if now - timestamp < WEATHER_CACHE_DURATION:
            print(f"📦 Utilisation du cache météo mémoire pour {lat}, {lon}")
            return cached_data
    
    weather_result = get_openweather_data_with_limits(lat, lon)
    
    if weather_result['success']:
        weather_cache[cache_key] = (weather_result, now)
    
    return weather_result

def generate_consistent_weather(lat: float, lon: float):
    """Génère des données météo COHÉRENTES basées sur la position et l'heure"""
    now = datetime.now()
    hour = now.hour
    day_of_year = now.timetuple().tm_yday
    
    hour_block = hour // 3
    stable_key = f"{lat:.2f}_{lon:.2f}_{day_of_year}_{hour_block}"
    stable_hash = int(hashlib.md5(stable_key.encode()).hexdigest()[:8], 16)
    
    base_temp = 20 + (36.8 - lat) * 0.5
    
    hour_sin = math.sin(hour * math.pi / 12)
    temp = base_temp + hour_sin * 6
    
    month = now.month
    if 6 <= month <= 8:
        temp += 8
    elif 3 <= month <= 5:
        temp += 4
    elif 9 <= month <= 11:
        temp += 2
    
    if 12 <= hour <= 18:
        wind = 12 + (hour - 12) * 2
    else:
        wind = 8 + abs(hour_sin) * 4
    
    pressure = 1015 + math.sin(hour * math.pi / 6) * 8
    
    condition_index = (stable_hash // 1000) % 4
    conditions = ['Clear', 'Clouds', 'Partly Cloudy', 'Mostly Sunny']
    conditions_fr = ['Ciel dégagé', 'Nuageux', 'Partiellement nuageux', 'Très ensoleillé']
    
    wave_height = min(1.5, max(0.2, wind / 25))
    
    wind_direction = stable_hash % 360
    wind_direction_info = get_wind_direction_name(wind_direction)
    wind_impact = get_wind_fishing_impact(wind_direction, lat, lon)
    
    weather_info = {
        'temperature': round(temp, 1),
        'feels_like': round(temp - 2, 1),
        'pressure': round(pressure, 1),
        'humidity': 60 + int(hour_sin * 15),
        'wind_speed': round(wind, 1),
        'wind_direction': wind_direction,
        'wind_direction_abbr': wind_direction_info['abbreviation'],
        'wind_direction_name': wind_direction_info['name'],
        'wind_direction_icon': wind_direction_info['icon'],
        'wind_fishing_impact': wind_impact,
        'wind_offshore': is_wind_offshore(lat, lon, wind_direction),
        'wind_onshore': is_wind_onshore(lat, lon, wind_direction),
        'condition': conditions[condition_index],
        'condition_description': conditions[condition_index].lower(),
        'condition_fr': conditions_fr[condition_index],
        'icon': '02d',
        'clouds': 20 + condition_index * 20,
        'visibility': 10,
        'sunrise': (now.replace(hour=6, minute=30, second=0)).isoformat(),
        'sunset': (now.replace(hour=18, minute=45, second=0)).isoformat(),
        'location': f'Position ({lat:.2f}, {lon:.2f})',
        'country': 'TN',
        'timestamp': now.isoformat(),
        'score': 0.7 + (stable_hash % 100) / 500,
        'wave_height': round(wave_height, 1),
        'turbidity': 1.0 + condition_index * 0.2,
        'source': 'modèle cohérent',
        'stable_id': stable_key
    }
    
    return {'success': True, 'weather': weather_info}

def get_emodnet_bathymetry_with_cache(lat: float, lon: float) -> float:
    """Récupère la bathymétrie EMODnet avec cache persistant"""
    params = {'lat': lat, 'lon': lon}
    
    cached_data = load_from_cache('emodnet', params, max_age_hours=168)
    if cached_data:
        return cached_data
    
    if API_RATE_LIMITS['emodnet'].get('use_cache_only', True):
        return None
    
    try:
        url = "https://ows.emodnet-bathymetry.eu/wms"
        params_api = {
            'service': 'WMS',
            'version': '1.3.0',
            'request': 'GetFeatureInfo',
            'layers': 'emodnet:mean_multicolour',
            'styles': '',
            'crs': 'EPSG:4326',
            'bbox': f'{lon-0.01},{lat-0.01},{lon+0.01},{lat+0.01}',
            'width': 101,
            'height': 101,
            'query_layers': 'emodnet:mean_multicolour',
            'info_format': 'application/json',
            'x': 50,
            'y': 50
        }
        
        response = requests.get(url, params=params_api, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                depth = data['features'][0]['properties'].get('GRAY_INDEX', 0)
                if depth > 0:
                    result = abs(depth) * 10
                    save_to_cache('emodnet', params, result, 168)
                    return result
    
    except Exception as e:
        print(f"⚠️ Erreur EMODnet: {e}")
    
    return None

def get_tide_data_with_cache(lat: float, lon: float) -> dict:
    """Récupère les données de marée avec cache"""
    params = {'lat': lat, 'lon': lon}
    
    cached_data = load_from_cache('worldtides', params, max_age_hours=12)
    if cached_data:
        return cached_data
    
    if API_RATE_LIMITS['worldtides'].get('use_cache_only', True):
        return get_fallback_tide_data(lat, lon)
    
    try:
        url = "https://www.worldtides.info/api/v3"
        params_api = {
            'lat': lat,
            'lon': lon,
            'key': WORLDTIDES_API_KEY,
            'date': 'today',
            'days': 1,
            'datum': 'CD',
            'step': 3600
        }
        
        response = requests.get(url, params=params_api, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            save_to_cache('worldtides', params, data, 12)
            return data
    
    except Exception as e:
        print(f"⚠️ Erreur WorldTides: {e}")
    
    return get_fallback_tide_data(lat, lon)

def get_fallback_tide_data(lat: float, lon: float) -> dict:
    """Données de marée de secours"""
    now = int(time.time())
    tide_height = 0.5 + math.sin(now / 18000) * 0.3
    
    return {
        'status': 200,
        'heights': [{'dt': now, 'height': tide_height}],
        'extremes': [
            {'dt': now + 18000, 'height': 0.8, 'type': 'High'},
            {'dt': now + 28800, 'height': 0.2, 'type': 'Low'}
        ]
    }

def get_location_name_with_cache(lat: float, lon: float) -> dict:
    """Récupère le nom de localisation avec cache"""
    params = {'lat': lat, 'lon': lon}
    
    cached_data = load_from_cache('nominatim', params, max_age_hours=24)
    if cached_data:
        return cached_data
    
    if API_RATE_LIMITS['nominatim'].get('use_cache_only', False):
        return get_fallback_location_data(lat, lon)
    
    try:
        url = NOMINATIM_API
        params_api = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'zoom': 10,
            'addressdetails': 1
        }
        headers = {'User-Agent': 'FishingPredictorPro/1.0'}
        
        response = requests.get(url, params=params_api, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            result = {
                'success': True,
                'name': data.get('display_name', f'Position {lat:.4f}, {lon:.4f}'),
                'address': data.get('address', {}),
                'type': data.get('type', 'water')
            }
            save_to_cache('nominatim', params, result, 24)
            return result
    
    except Exception as e:
        print(f"⚠️ Erreur Nominatim: {e}")
    
    return get_fallback_location_data(lat, lon)

def get_fallback_location_data(lat: float, lon: float) -> dict:
    """Données de localisation de secours"""
    if lat > 37.0:
        region = 'Nord Tunisie'
    elif lat > 36.0:
        region = 'Tunis'
    elif lat > 35.0:
        region = 'Sahel'
    else:
        region = 'Sud Tunisie'
    
    return {
        'success': True,
        'name': f'Position près de {region} ({lat:.4f}, {lon:.4f})',
        'type': 'water',
        'address': {'state': region, 'country': 'Tunisie'}
    }

def calculate_weather_score(weather_data: dict) -> float:
    """Calcule un score de 0-1 pour la pêche basé sur la météo RÉELLE"""
    score = 0.7
    
    temp = weather_data.get('temperature', 20)
    if 15 <= temp <= 25:
        score += 0.2
    elif 10 <= temp <= 30:
        score += 0.1
    else:
        score -= 0.1
    
    wind_speed = weather_data.get('wind_speed', 10)
    if wind_speed < 20:
        score += 0.1
    elif wind_speed > 30:
        score -= 0.2
    
    pressure = weather_data.get('pressure', 1015)
    if 1010 <= pressure <= 1020:
        score += 0.1
    
    condition = weather_data.get('condition', 'Clear')
    if 'Rain' not in condition and 'Thunderstorm' not in condition:
        score += 0.1
    
    wave_height = weather_data.get('wave_height', 0.5)
    if wave_height < 1.0:
        score += 0.1
    elif wave_height > 1.5:
        score -= 0.1
    
    wind_direction = weather_data.get('wind_direction', 0)
    if is_wind_offshore(36.8, 10.1, wind_direction):
        score -= 0.2
    
    return min(1.0, max(0.3, score))

def calculate_depth_factor(depth: float, species: str) -> float:
    species_depths = {'loup':[3,20],'daurade':[2,15],'pageot':[10,60],'thon':[10,100],'sar':[5,25],'mulet':[1,10],'marbré':[2,15],'rouget':[5,30],'sériole':[10,50],'bonite':[5,40]}
    optimal_range = species_depths.get(species, [5, 20])
    min_depth, max_depth = optimal_range
    if min_depth <= depth <= max_depth: return 1.0
    elif depth < min_depth:
        distance = min_depth - depth
        return max(0.5, 1.0 - (distance / min_depth * 0.5))
    else:
        distance = depth - max_depth
        return max(0.5, 1.0 - (distance / max_depth * 0.5))

def get_optimal_depth(species: str) -> str:
    depths = {'loup':"3-20m",'daurade':"2-15m",'pageot':"10-60m",'thon':"10-100m",'sar':"5-25m",'mulet':"1-10m",'marbré':"2-15m",'rouget':"5-30m",'sériole':"10-50m",'bonite':"5-40m"}
    return depths.get(species, "5-20m")

def get_optimal_seabed(species: str) -> str:
    seabeds = {'loup':"rocheux/mixte",'daurade':"sable/herbier",'pageot':"rocheux",'thon':"pélagique",'sar':"rocheux",'mulet':"sable",'marbré':"sable",'rouget':"sable/vasard",'sériole':"mixte",'bonite':"pélagique"}
    return seabeds.get(species, "mixte")

def is_depth_optimal(depth: float, species: str) -> bool:
    optimal_ranges = {'loup':(3,20),'daurade':(2,15),'pageot':(10,60),'thon':(10,100),'sar':(5,25)}
    if species in optimal_ranges:
        min_depth, max_depth = optimal_ranges[species]
        return min_depth <= depth <= max_depth
    return 5 <= depth <= 20

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

def assess_fishing_suitability(bathymetry) -> dict:
    depth = bathymetry.get('depth',10)
    seabed = bathymetry.get('seabed_type','mixed')
    suitability = {'surfcasting':depth<10 and seabed in ['sand','mixed'],'rock_fishing':seabed in ['rock','mixed'] and depth<30,'boat_fishing':depth>5,'spearfishing':depth<20 and seabed in ['rock','grass']}
    if suitability.get('surfcasting'): best_technique="surfcasting"
    elif suitability.get('rock_fishing'): best_technique="pêche depuis les rochers"
    elif suitability.get('boat_fishing'): best_technique="pêche en bateau"
    else: best_technique="pêche à soutenir"
    return {**suitability,'best_technique':best_technique,'risk_level':'low' if depth>3 else 'medium'}

def get_real_bathymetry(lat:float,lon:float)->dict:
    print(f"🔍 Recherche bathymétrie réelle pour: {lat}, {lon}")
    try:
        print("🌊 Tentative EMODnet avec cache...")
        depth = get_emodnet_bathymetry_with_cache(lat,lon)
        if depth and depth>0:
            seabed_type = determine_seabed_type_emodnet(lat,lon,depth)
            return {'success':True,'depth':round(depth,1),'seabed_type':seabed_type,'source':'EMODnet (cache)','accuracy':'haute','confidence':0.8}
    except Exception as e: print(f"⚠️ EMODnet échoué: {e}")
    print("🔧 Utilisation du modèle scientifique...")
    return predictor.get_bathymetry_data(lat,lon)

def determine_seabed_type_emodnet(lat:float,lon:float,depth:float)->str:
    if lat>37.0:
        if depth<10: return "rock"
        elif depth<25: return "mixed"
        else: return "mud"
    elif lat>36.5 and lon>10.8:
        if depth<5: return "sand"
        elif depth<15: return "grass"
        else: return "rock"
    elif lat>35.5:
        if depth<3: return "sand"
        elif depth<10: return "grass"
        elif depth<20: return "mixed"
        else: return "mud"
    elif lat<34.0:
        if depth<8: return "sand"
        else: return "mud"
    else:
        if depth<5: return "sand"
        elif depth<15: return "mixed"
        else: return "mud"

def get_stormglass_marine_data(lat:float,lon:float)->dict:
    params = {'lat': lat, 'lon': lon}
    
    cached_data = load_from_cache('stormglass', params, max_age_hours=24)
    if cached_data:
        return cached_data
    
    simulated_data = {
        'waterTemperature': {'sg': 18 + math.sin(time.time() / 36000) * 5},
        'waveHeight': {'sg': 0.5 + math.sin(time.time() / 18000) * 0.3},
        'wavePeriod': {'sg': 5 + math.sin(time.time() / 24000) * 2},
        'currentSpeed': {'sg': 0.1 + math.sin(time.time() / 12000) * 0.05}
    }
    
    save_to_cache('stormglass', params, simulated_data, 24)
    return simulated_data

# ===== NOUVELLES FONCTIONS POUR LES 3 FACTEURS SCIENTIFIQUES =====

def get_marine_data_multi_source(lat: float, lon: float) -> dict:
    """Combine Stormglass, Open-Météo et estimations pour données marines"""
    marine_data = {
        'water_temperature': None,
        'chlorophyll': None,
        'current_speed': None,
        'salinity': config.SALINITY_MEDITERRANEAN,
        'sources': []
    }
    
    # 1. Essayer Stormglass (si clé disponible)
    if config.STORMGLASS_API_KEY:
        try:
            url = f"{config.STORMGLASS_URL}/weather/point"
            params = {
                'lat': lat,
                'lng': lon,
                'params': 'waterTemperature,chlorophyll'
            }
            headers = {'Authorization': config.STORMGLASS_API_KEY}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'hours' in data and len(data['hours']) > 0:
                    marine_data['water_temperature'] = data['hours'][0].get('waterTemperature', {}).get('sg')
                    marine_data['chlorophyll'] = data['hours'][0].get('chlorophyll', {}).get('sg')
                    marine_data['sources'].append('Stormglass')
                    print(f"✅ Données Stormglass reçues")
        except Exception as e:
            print(f"⚠️ Erreur Stormglass: {e}")
    
    # 2. Essayer Open-Météo (gratuit, pas de clé)
    if not marine_data['water_temperature']:
        try:
            url = config.OPEN_METEO_URL
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m',
                'hourly': 'temperature_2m',
                'timezone': 'auto'
            }
            
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                air_temp = data['current']['temperature_2m']
                # Estimer température eau depuis température air
                marine_data['water_temperature'] = estimate_water_from_air(air_temp)
                marine_data['sources'].append('Open-Météo')
                print(f"✅ Données Open-Météo reçues")
        except Exception as e:
            print(f"⚠️ Erreur Open-Météo: {e}")
    
    # 3. Estimation si pas de données
    if not marine_data['water_temperature']:
        marine_data['water_temperature'] = estimate_water_from_position(lat, lon)
        marine_data['chlorophyll'] = predictor.estimate_chlorophyll(datetime.now().month, lat, lon)
        marine_data['sources'].append('Modèle scientifique')
        print(f"🔬 Utilisation du modèle scientifique")
    
    # 4. Estimation du courant
    current_data = predictor.calculate_tidal_current(lat, lon, datetime.now())
    marine_data['current_speed'] = current_data['speed_mps']
    
    return marine_data

def estimate_water_from_air(air_temp: float) -> float:
    """Estime température eau depuis température air pour la Tunisie"""
    month = datetime.now().month
    # Modèle spécifique à la Tunisie
    if 6 <= month <= 9:  # Été
        return max(air_temp - 4.0, 22.0)  # Min 22°C en été
    elif 12 <= month or month <= 2:  # Hiver
        return min(air_temp + 2.0, 16.0)  # Max 16°C en hiver
    else:  # Printemps/Automne
        return air_temp - 2.0

def estimate_water_from_position(lat: float, lon: float) -> float:
    """Estime température eau basée sur position et saison"""
    month = datetime.now().month
    # Températures moyennes pour la Tunisie par région
    if lat > 37.0:  # Nord
        base_temp = {1:14,2:14,3:15,4:17,5:20,6:23,7:26,8:27,9:25,10:22,11:19,12:16}.get(month, 20)
    elif lat > 36.0:  # Centre (Tunis, Sousse)
        base_temp = {1:15,2:15,3:16,4:18,5:21,6:24,7:27,8:28,9:26,10:23,11:20,12:17}.get(month, 20)
    else:  # Sud (Sfax, Djerba)
        base_temp = {1:16,2:16,3:17,4:19,5:22,6:25,7:28,8:29,9:27,10:24,11:21,12:18}.get(month, 20)
    
    # Variation journalière
    hour = datetime.now().hour
    hour_variation = math.sin(hour * math.pi / 12) * 1.5
    
    return round(base_temp + hour_variation, 1)

# ===== ROUTES API =====

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
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        
        print(f"🌤️ API Météo pour: {lat}, {lon}, refresh: {refresh}")
        
        weather_result = get_cached_weather(lat, lon, force_refresh=refresh)
        
        return jsonify({
            'status': 'success',
            'weather': weather_result['weather'],
            'source': weather_result.get('source', 'cache'),
            'cached': weather_result.get('source') == 'cache',
            'api_limits': {
                'openweather_today': API_RATE_LIMITS['openweather']['count_today'],
                'openweather_max': API_RATE_LIMITS['openweather']['max_per_day'],
                'cache_mode': API_RATE_LIMITS['openweather'].get('use_cache_only', False)
            },
            'next_refresh': (datetime.now() + timedelta(minutes=30)).isoformat()
        })
        
    except Exception as e:
        print(f"❌ Erreur API météo: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/tunisian_prediction')
def api_tunisian_prediction():
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')
        
        print(f"🎣 Prédiction améliorée pour: {lat}, {lon}, {species}")
        
        # ✅ AJOUTER : Récupérer données marines
        marine_data = get_marine_data_multi_source(lat, lon)
        
        cache_key = f"prediction_{lat:.4f}_{lon:.4f}_{species}"
        cached_prediction = load_from_cache('prediction', {'lat': lat, 'lon': lon, 'species': species}, max_age_hours=1)
        
        if cached_prediction:
            print(f"📦 Prédiction chargée depuis le cache")
            return jsonify(cached_prediction)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_location = executor.submit(get_location_name_with_cache, lat, lon)
            future_bathymetry = executor.submit(get_real_bathymetry, lat, lon)
            future_weather = executor.submit(get_cached_weather, lat, lon)
            
            location_info = future_location.result()
            bathymetry = future_bathymetry.result()
            weather_result = future_weather.result()
        
        if weather_result['success']:
            real_weather = weather_result['weather']
            
            predictor_weather = {
                'temperature': real_weather['temperature'],
                'wind_speed': real_weather['wind_speed'],
                'pressure': real_weather['pressure'],
                'wave_height': real_weather.get('wave_height', 0.5),
                'turbidity': real_weather.get('turbidity', 1.0),
                'humidity': real_weather['humidity'],
                'condition': real_weather['condition'],
                'wind_direction': real_weather['wind_direction'],
                # ✅ AJOUTER LES NOUVEAUX FACTEURS
                'water_temperature': marine_data['water_temperature'],
                'salinity': marine_data['salinity'],
                'current_speed': marine_data['current_speed']
            }
            
            weather_source = real_weather.get('source', 'OpenWeatherMap')
        else:
            fallback_weather = generate_consistent_weather(lat, lon)['weather']
            
            predictor_weather = {
                'temperature': fallback_weather['temperature'],
                'wind_speed': fallback_weather['wind_speed'],
                'pressure': fallback_weather['pressure'],
                'wave_height': fallback_weather['wave_height'],
                'turbidity': fallback_weather['turbidity'],
                'humidity': fallback_weather['humidity'],
                'condition': fallback_weather['condition'],
                'wind_direction': fallback_weather['wind_direction'],
                # ✅ AJOUTER LES NOUVEAUX FACTEURS (estimés)
                'water_temperature': marine_data['water_temperature'],
                'salinity': marine_data['salinity'],
                'current_speed': marine_data['current_speed']
            }
            
            weather_source = 'modèle cohérent'
        
        # ✅ AJOUTER : Calculer l'oxygène et chlorophylle
        oxygen_level = predictor.calculate_dissolved_oxygen(
            marine_data['water_temperature'],
            marine_data['salinity'],
            predictor_weather['pressure']
        )
        
        chlorophyll_level = marine_data.get('chlorophyll', 
            predictor.estimate_chlorophyll(datetime.now().month, lat, lon))
        
        current_data = predictor.calculate_tidal_current(lat, lon, datetime.now())
        
        # Ajouter à predictor_weather
        predictor_weather.update({
            'oxygen': oxygen_level,
            'chlorophyll': chlorophyll_level
        })
        
        # Appeler le prédicteur amélioré
        prediction = predictor.predict_daily_activity(
            lat, lon, datetime.now(), species, predictor_weather
        )
        
        depth = bathymetry.get('depth', 10)
        depth_factor = calculate_depth_factor(depth, species)
        weather_score = calculate_weather_score(predictor_weather)
        
        final_score = (
            prediction['activity_score'] * 0.35 +
            depth_factor * 0.25 +
            weather_score * 0.40
        ) * 100
        
        prediction_id = hashlib.md5(
            f"{lat:.4f}_{lon:.4f}_{species}_{datetime.now().strftime('%Y%m%d%H')}".encode()
        ).hexdigest()[:12]
        
        response_data = {
            'status': 'success',
            'prediction_id': prediction_id,
            'stable': True,
            'valid_until': (datetime.now() + timedelta(minutes=60)).isoformat(),
            'scores': {
                'final': round(final_score),
                'environmental': round(prediction['environmental_score'] * 100),
                'behavioral': round(prediction['behavioral_score'] * 100),
                'bathymetry_factor': round(depth_factor * 100),
                'weather_factor': round(weather_score * 100),
                'components': {
                    'scientific': round(prediction['environmental_score'] * 100),
                    'depth': round(depth_factor * 100),
                    'regional': round(prediction['regional_factor'] * 100),
                    'weather': round(weather_score * 100)
                }
            },
            'weather': {
                'temperature': predictor_weather['temperature'],
                'wind_speed': predictor_weather['wind_speed'],
                'wind_direction': predictor_weather.get('wind_direction', 0),
                'wind_direction_abbr': real_weather.get('wind_direction_abbr', 'N'),
                'wind_direction_name': real_weather.get('wind_direction_name', 'Nord'),
                'wind_direction_icon': real_weather.get('wind_direction_icon', '⬆️'),
                'wind_fishing_impact': real_weather.get('wind_fishing_impact', 'neutre'),
                'wind_offshore': real_weather.get('wind_offshore', False),
                'wind_onshore': real_weather.get('wind_onshore', False),
                'pressure': predictor_weather['pressure'],
                'humidity': predictor_weather.get('humidity', 60),
                'condition': predictor_weather['condition'],
                'condition_fr': weather_result['weather'].get('condition_fr', predictor_weather['condition']),
                'wave_height': predictor_weather['wave_height'],
                'updated': datetime.now().isoformat(),
                'source': weather_source
            },
            # ✅ AJOUTER DANS RESPONSE_DATA :
            'scientific_factors': prediction.get('scientific_factors', {
                'dissolved_oxygen': {'value': oxygen_level, 'unit': 'mg/L'},
                'chlorophyll_a': {'value': chlorophyll_level, 'unit': 'mg/m³'},
                'tidal_current': current_data
            }),
            'marine_data_sources': marine_data['sources'],
            'recommendations': {
                'tips': [
                    f"Opportunité: {prediction['fishing_opportunity']}",
                    f"Heures optimales: {', '.join([str(h['hour'])+'h' for h in prediction['best_fishing_hours'][:3]])}",
                    f"Profondeur optimale: {get_optimal_depth(species)}",
                    f"Type de fond recommandé: {get_optimal_seabed(species)}",
                    f"Météo: {weather_result['weather'].get('condition_fr', predictor_weather['condition'])}, "
                    f"{predictor_weather['temperature']:.1f}°C, "
                    f"Vent: {predictor_weather['wind_speed']:.1f} km/h ({real_weather.get('wind_direction_name', 'N')})"
                ],
                'techniques': prediction.get('recommended_techniques', ['surfcasting', 'pêche à soutenir'])
            },
            'bathymetry': {
                **bathymetry,
                'optimal_for_species': is_depth_optimal(depth, species),
                'zone': location_info.get('address', {}).get('state', 'Zone côtière'),
                'recommended_fishing': [
                    f"Profondeur: {depth}m ({'optimale' if is_depth_optimal(depth, species) else 'sous-optimale'})",
                    f"Type de fond: {bathymetry.get('seabed_description', 'mixte')}",
                    f"Précision: {bathymetry.get('accuracy', 'moyenne')}"
                ]
            },
            'location': {
                'lat': lat,
                'lon': lon,
                'name': location_info.get('name', f'Spot ({lat:.4f}, {lon:.4f})'),
                'type': location_info.get('type', 'water'),
                'region': location_info.get('address', {}).get('state', 'Tunisie')
            },
            'metadata': {
                'species': species,
                'timestamp': datetime.now().isoformat(),
                'data_source': bathymetry.get('source', 'modèle scientifique'),
                'weather_source': weather_source,
                'prediction_stable': True,
                'cache_duration_minutes': 60,
                'next_update_recommended': (datetime.now() + timedelta(minutes=60)).strftime('%H:%M'),
                'api_usage_info': {
                    'openweather_calls_today': API_RATE_LIMITS['openweather']['count_today'],
                    'using_cache': weather_result.get('source') == 'cache'
                }
            }
        }
        
        save_to_cache('prediction', {'lat': lat, 'lon': lon, 'species': species}, response_data, 1)
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Erreur prédiction: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'fallback': {
                'scores': {'final': 65},
                'recommendations': {'tips': ['Utilisez notre modèle scientifique pour des prédictions précises']}
            }
        })

@app.route('/api/location_search')
def api_location_search():
    """Recherche de localisations par nom"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'status': 'error',
                'message': 'Paramètre "q" requis'
            })
        
        if ',' in query:
            try:
                lat, lon = map(float, query.split(','))
                return jsonify({
                    'status': 'success',
                    'results': [{
                        'lat': lat,
                        'lon': lon,
                        'name': f'Position ({lat:.4f}, {lon:.4f})',
                        'type': 'coordinates'
                    }]
                })
            except:
                pass
        
        locations = []
        
        tunisian_cities = [
            {'name': 'Tunis', 'lat': 36.8065, 'lon': 10.1815},
            {'name': 'Bizerte', 'lat': 37.2747, 'lon': 9.8739},
            {'name': 'Sousse', 'lat': 35.8254, 'lon': 10.6360},
            {'name': 'Hammamet', 'lat': 36.4000, 'lon': 10.6000},
            {'name': 'Monastir', 'lat': 35.7833, 'lon': 10.8333},
            {'name': 'Mahdia', 'lat': 35.5047, 'lon': 11.0622},
            {'name': 'Sfax', 'lat': 34.7400, 'lon': 10.7600},
            {'name': 'Djerba', 'lat': 33.8078, 'lon': 10.8451},
            {'name': 'Tabarka', 'lat': 36.9540, 'lon': 8.7580},
            {'name': 'Zarzis', 'lat': 33.5000, 'lon': 11.1167},
            {'name': 'Kélibia', 'lat': 36.8475, 'lon': 11.0940},
            {'name': 'La Marsa', 'lat': 36.8782, 'lon': 10.3247},
            {'name': 'Gammarth', 'lat': 36.9000, 'lon': 10.3167}
        ]
        
        for city in tunisian_cities:
            if query.lower() in city['name'].lower():
                locations.append({
                    'lat': city['lat'],
                    'lon': city['lon'],
                    'name': city['name'],
                    'type': 'city'
                })
        
        if not locations and len(query) > 2:
            locations = [{
                'lat': 36.8065,
                'lon': 10.1815,
                'name': 'Tunis',
                'type': 'city'
            }]
        
        return jsonify({
            'status': 'success',
            'query': query,
            'results': locations[:10]
        })
        
    except Exception as e:
        print(f"❌ Erreur recherche localisation: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/spot_info')
def api_spot_info():
    """Informations détaillées sur un spot de pêche"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        
        location_info = get_location_name_with_cache(lat, lon)
        bathymetry = get_real_bathymetry(lat, lon)
        weather_result = get_cached_weather(lat, lon)
        
        spot_data = {
            'status': 'success',
            'coordinates': {'lat': lat, 'lon': lon},
            'location': location_info,
            'bathymetry': bathymetry,
            'weather': weather_result['weather'] if weather_result['success'] else None,
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'spot_quality': 'good' if bathymetry.get('depth', 0) > 2 else 'poor',
                'accessibility': 'easy' if lat > 36.0 and lon > 10.0 else 'medium',
                'popularity': 'high' if 36.5 < lat < 37.0 and 10.0 < lon < 11.0 else 'medium'
            },
            'recommendations': {
                'best_season': ['printemps', 'automne'],
                'best_time': ['matin', 'soir'],
                'techniques': ['surfcasting', 'pêche à soutenir'],
                'baits': ['vers', 'crevettes', 'sardines']
            }
        }
        
        return jsonify(spot_data)
        
    except Exception as e:
        print(f"❌ Erreur info spot: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/forecast_10days')
def api_forecast_10days():
    """Prévisions sur 10 jours (simplifiées)"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        species = request.args.get('species', 'loup')
        
        forecast = []
        
        for day in range(10):
            date = datetime.now() + timedelta(days=day)
            
            weather = generate_consistent_weather(lat, lon)
            
            prediction = predictor.predict_daily_activity(
                lat, lon, date, species, weather['weather']
            )
            
            depth = 10 + day % 5
            depth_factor = calculate_depth_factor(depth, species)
            weather_score = calculate_weather_score(weather['weather'])
            
            final_score = (
                prediction['activity_score'] * 0.4 +
                depth_factor * 0.3 +
                weather_score * 0.3
            ) * 100
            
            forecast.append({
                'day': day + 1,
                'date': date.strftime('%Y-%m-%d'),
                'score': round(final_score),
                'weather': {
                    'temperature': round(weather['weather']['temperature'], 1),
                    'condition': weather['weather']['condition_fr'],
                    'wind_speed': round(weather['weather']['wind_speed'], 1),
                    'wind_direction': weather['weather']['wind_direction_name']
                },
                'best_hours': prediction['best_fishing_hours'][:2],
                'recommendation': prediction['fishing_opportunity']
            })
        
        return jsonify({
            'status': 'success',
            'forecast': forecast,
            'location': f'Position ({lat:.4f}, {lon:.4f})',
            'species': species,
            'average_score': round(sum([day['score'] for day in forecast]) / len(forecast))
        })
        
    except Exception as e:
        print(f"❌ Erreur prévisions 10 jours: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'fallback': {
                'forecast': [],
                'average_score': 65
            }
        })

@app.route('/api/fishing_calendar')
def api_fishing_calendar():
    """Calendrier de pêche mensuel"""
    try:
        species = request.args.get('species', 'loup')
        month = int(request.args.get('month', datetime.now().month))
        
        calendars = {
            'loup': {
                'name': 'Loup de Mer',
                'months': {
                    1: 'moyenne', 2: 'moyenne', 3: 'bonne', 4: 'excellente',
                    5: 'excellente', 6: 'bonne', 7: 'moyenne', 8: 'moyenne',
                    9: 'bonne', 10: 'excellente', 11: 'excellente', 12: 'bonne'
                },
                'tips': [
                    'Privilégiez les zones rocheuses',
                    'Pêche au vif ou au leurre',
                    'Meilleure période: mars-juin et sept-nov'
                ]
            },
            'daurade': {
                'name': 'Daurade Royale',
                'months': {
                    1: 'faible', 2: 'faible', 3: 'moyenne', 4: 'bonne',
                    5: 'excellente', 6: 'excellente', 7: 'excellente', 8: 'bonne',
                    9: 'bonne', 10: 'moyenne', 11: 'moyenne', 12: 'faible'
                },
                'tips': [
                    'Zones sablonneuses avec herbiers',
                    'Appâts: vers, crustacés',
                    'Pêche fine recommandée'
                ]
            },
            'pageot': {
                'name': 'Pageot Commun',
                'months': {
                    1: 'faible', 2: 'faible', 3: 'moyenne', 4: 'bonne',
                    5: 'excellente', 6: 'excellente', 7: 'excellente', 8: 'bonne',
                    9: 'moyenne', 10: 'moyenne', 11: 'faible', 12: 'faible'
                },
                'tips': [
                    'Fonds rocheux',
                    'Pêche en dérive',
                    'Taille minimale: 20cm'
                ]
            }
        }
        
        if species not in calendars:
            species = 'loup'
        
        calendar_data = calendars[species]
        
        return jsonify({
            'status': 'success',
            'species': species,
            'species_name': calendar_data['name'],
            'current_month': month,
            'current_month_name': datetime(2024, month, 1).strftime('%B'),
            'activity': calendar_data['months'][month],
            'calendar': calendar_data['months'],
            'tips': calendar_data['tips'],
            'best_months': [m for m, activity in calendar_data['months'].items() 
                           if activity in ['excellente', 'bonne']]
        })
        
    except Exception as e:
        print(f"❌ Erreur calendrier: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/tide_chart')
def api_tide_chart():
    """Graphique des marées pour 24h"""
    try:
        lat = float(request.args.get('lat', 36.8065))
        lon = float(request.args.get('lon', 10.1815))
        
        tide_data = get_tide_data_with_cache(lat, lon)
        
        now = datetime.now()
        tide_points = []
        
        for hour in range(24):
            time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            tide_height = 0.5 + 0.3 * math.sin(hour * math.pi / 12)
            
            tide_points.append({
                'time': time.strftime('%H:%M'),
                'height': round(tide_height, 2),
                'is_high': tide_height > 0.7,
                'is_low': tide_height < 0.3
            })
        
        return jsonify({
            'status': 'success',
            'location': f'Position ({lat:.4f}, {lon:.4f})',
            'tide_data': tide_data,
            'chart_points': tide_points,
            'next_high_tide': get_next_high_tide(tide_data),
            'next_low_tide': get_next_low_tide(tide_data),
            'current_height': tide_data.get('heights', [{}])[0].get('height', 0.5),
            'recommendations': {
                'best_fishing_tide': 'marée montante',
                'worst_fishing_tide': 'marée basse fixe',
                'tips': [
                    'Pêchez 2h avant et après la marée haute',
                    'Évitez les marées trop basses',
                    'Marée montante = meilleure activité'
                ]
            }
        })
        
    except Exception as e:
        print(f"❌ Erreur graphique marée: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/moon_phase')
def api_moon_phase():
    """Phase de la lune actuelle"""
    try:
        from datetime import datetime
        
        def calculate_moon_phase(date):
            days_in_cycle = 29.530588853
            known_new_moon = datetime(2024, 1, 11)
            
            days_since = (date - known_new_moon).days
            days_in_current = days_since % days_in_cycle
            
            if days_in_current < 1.84566:
                return 'Nouvelle Lune'
            elif days_in_current < 5.53699:
                return 'Premier Croissant'
            elif days_in_current < 9.22831:
                return 'Premier Quartier'
            elif days_in_current < 12.91963:
                return 'Lune Gibbeuse Croissante'
            elif days_in_current < 16.61096:
                return 'Pleine Lune'
            elif days_in_current < 20.30228:
                return 'Lune Gibbeuse Décroissante'
            elif days_in_current < 23.99361:
                return 'Dernier Quartier'
            else:
                return 'Dernier Croissant'
        
        current_date = datetime.now()
        phase = calculate_moon_phase(current_date)
        
        fishing_impact = {
            'Nouvelle Lune': 'Très bon - forte activité nocturne',
            'Pleine Lune': 'Bon - bonne visibilité nocturne',
            'Premier Quartier': 'Moyen',
            'Dernier Quartier': 'Moyen',
            'Premier Croissant': 'Bon en soirée',
            'Dernier Croissant': 'Bon en matinée',
            'Lune Gibbeuse Croissante': 'Très bon',
            'Lune Gibbeuse Décroissante': 'Très bon'
        }
        
        return jsonify({
            'status': 'success',
            'date': current_date.strftime('%Y-%m-%d'),
            'moon_phase': phase,
            'fishing_impact': fishing_impact.get(phase, 'Moyen'),
            'illumination': '0%' if phase == 'Nouvelle Lune' else 
                           '100%' if phase == 'Pleine Lune' else '50%',
            'next_full_moon': (current_date + timedelta(days=14)).strftime('%Y-%m-%d'),
            'next_new_moon': (current_date + timedelta(days=7)).strftime('%Y-%m-%d'),
            'tips': [
                'Nouvelle Lune: excellente pour la pêche nocturne',
                'Pleine Lune: privilégiez les leurres brillants',
                'Évitez les changements de phase pour une pêche régulière'
            ]
        })
        
    except Exception as e:
        print(f"❌ Erreur phase lunaire: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/api/favorites', methods=['GET'])
def api_favorites():
    """API pour gérer les favoris (version simplifiée)"""
    try:
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
        else:
            favorites = []
        
        return jsonify({
            'status': 'success',
            'favorites': favorites,
            'count': len(favorites)
        })
        
    except Exception as e:
        print(f"❌ Erreur favoris: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'favorites': []
        })

@app.route('/api/favorites', methods=['POST'])
def api_favorites_post():
    """Ajouter un favori"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Données manquantes'})
        
        favorites = []
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
        
        # Générer un ID unique
        favorite_id = hashlib.md5(f"{data.get('name')}{data.get('lat')}{data.get('lon')}{time.time()}".encode()).hexdigest()[:8]
        data['id'] = favorite_id
        data['added_date'] = datetime.now().isoformat()
        
        favorites.append(data)
        
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Favori ajouté: {favorite_id} - {data.get('name')}")
        return jsonify({'status': 'success', 'id': favorite_id})
        
    except Exception as e:
        print(f"❌ Erreur ajout favori: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/favorites', methods=['DELETE'])
def api_favorites_delete():
    """Supprimer un favori"""
    try:
        # Essayer de récupérer l'ID depuis les paramètres d'abord
        favorite_id = request.args.get('id')
        
        # Si non trouvé dans les paramètres, essayer dans le corps JSON
        if not favorite_id and request.json:
            favorite_id = request.json.get('id')
        
        if not favorite_id:
            print("❌ ID manquant pour suppression de favori")
            return jsonify({'status': 'error', 'message': 'ID manquant'})
        
        print(f"🔍 Tentative de suppression du favori ID: {favorite_id}")
        
        if os.path.exists(FAVORITES_FILE):
            with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
            
            print(f"📋 Nombre de favoris avant suppression: {len(favorites)}")
            print(f"📋 IDs disponibles: {[f.get('id') for f in favorites]}")
            
            initial_count = len(favorites)
            # Comparer les IDs en tant que chaînes
            favorites = [f for f in favorites if str(f.get('id')) != str(favorite_id)]
            
            print(f"📋 Nombre de favoris après suppression: {len(favorites)}")
            
            if len(favorites) < initial_count:
                with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(favorites, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Favori supprimé: {favorite_id}")
                return jsonify({'status': 'success', 'message': 'Favori supprimé'})
            else:
                print(f"❌ Favori non trouvé: {favorite_id}")
                return jsonify({'status': 'error', 'message': 'Favori non trouvé'})
        
        return jsonify({'status': 'error', 'message': 'Aucun favori'})
        
    except Exception as e:
        print(f"❌ Erreur suppression favori: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/real_bathymetry')
def api_real_bathymetry():
    try:
        lat=float(request.args.get('lat',36.8065))
        lon=float(request.args.get('lon',10.1815))
        bathymetry=get_real_bathymetry(lat,lon)
        tide_data=get_tide_data_with_cache(lat,lon)
        location=get_location_name_with_cache(lat,lon)
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
    except Exception as e: 
        return jsonify({'status':'error','message':str(e)})

@app.route('/api/species_by_season')
def api_species_by_season():
    current_month=datetime.now().month
    if current_month in [12,1,2]: season='hiver'; recommended=['loup','daurade','merlan','corbeau']
    elif current_month in [3,4,5]: season='printemps'; recommended=['loup','daurade','pageot','maquereau']
    elif current_month in [6,7,8]: season='été'; recommended=['daurade','pageot','mulet','marbré','sériole']
    else: season='automne'; recommended=['loup','daurade','pageot','rouget','sar']
    species_list=[]
    species_icons={'loup':'🐟','daurade':'🐠','pageot':'🐡','maquereau':'🦈','merlan':'🐟','corbeau':'🐠','mulet':'🐡','marbré':'🦈','sériole':'🐟','rouget':'🐠','sar':'🐡','thon':'🦈'}
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
        if current_month in [3, 4, 5]:
            current_season = 'printemps'
        elif current_month in [6, 7, 8]:
            current_season = 'été'
        elif current_month in [9, 10, 11]:
            current_season = 'automne'
        else:
            current_season = 'hiver'
        
        return jsonify({
            'status': 'success',
            'seasons': seasonal_data,
            'current_season': current_season,
            'current_month': current_month,
            'tips': {
                'printemps': 'Meilleure saison pour le loup et la daurade',
                'été': 'Idéal pour la pêche en mer et les espèces tropicales',
                'automne': 'Bon compromis température/activité',
                'hiver': 'Privilégiez les journées ensoleillées'
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# ===== API ALERTES EMAIL =====

@app.route('/api/alerts/subscribe', methods=['POST'])
def api_alerts_subscribe():
    """API pour s'abonner aux alertes"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Données manquantes'})
        
        email = data.get('email', '').strip().lower()
        preferences = data.get('preferences', {})
        
        if not email or '@' not in email:
            return jsonify({'status': 'error', 'message': 'Email invalide'})
        
        # Vérifier le format de l'email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'status': 'error', 'message': 'Format email invalide'})
        
        # Charger les abonnements existants
        subscriptions = []
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
        
        # Vérifier si l'email est déjà abonné
        existing_index = -1
        for i, sub in enumerate(subscriptions):
            if sub['email'] == email:
                existing_index = i
                break
        
        # Générer un ID de confirmation
        confirmation_id = hashlib.md5(f"{email}{time.time()}".encode()).hexdigest()[:12].upper()
        
        subscription_data = {
            'email': email,
            'preferences': {
                'excellent_conditions': preferences.get('excellentConditions', True),
                'seasonal_reminders': preferences.get('seasonalReminders', True),
                'weekly_tips': preferences.get('weeklyTips', False),
                'favorite_spots': preferences.get('favoriteSpots', True)
            },
            'confirmed': True,
            'confirmation_id': confirmation_id,
            'subscribed_at': datetime.now().isoformat(),
            'last_alert_sent': None,
            'alert_count': 0,
            'active': True
        }
        
        if existing_index >= 0:
            # Mettre à jour l'abonnement existant
            subscriptions[existing_index] = subscription_data
            message = "Abonnement mis à jour"
        else:
            # Nouvel abonnement
            subscriptions.append(subscription_data)
            message = "Abonnement créé"
        
        # Sauvegarder
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscriptions, f, ensure_ascii=False, indent=2)
        
        # Envoyer l'email de confirmation
        email_sent = send_confirmation_email(email, confirmation_id)
        
        print(f"✅ Abonnement aux alertes: {email}")
        print(f"   Confirmation ID: {confirmation_id}")
        print(f"   Email envoyé: {email_sent}")
        
        return jsonify({
            'status': 'success',
            'message': f'{message} avec succès',
            'confirmation_id': confirmation_id,
            'email_sent': email_sent,
            'email': email
        })
        
    except Exception as e:
        print(f"❌ Erreur abonnement alertes: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/alerts/unsubscribe', methods=['POST'])
def api_alerts_unsubscribe():
    """API pour se désabonner des alertes"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'status': 'error', 'message': 'Email manquant'})
        
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
            
            # Filtrer pour supprimer cet email
            original_count = len(subscriptions)
            subscriptions = [sub for sub in subscriptions if sub['email'] != email]
            
            if len(subscriptions) < original_count:
                with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(subscriptions, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Désabonnement: {email}")
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
        
        if not email:
            return jsonify({'status': 'error', 'message': 'Email manquant'})
        
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
            
            for sub in subscriptions:
                if sub['email'] == email:
                    return jsonify({
                        'status': 'success',
                        'subscribed': True,
                        'data': sub
                    })
        
        return jsonify({'status': 'success', 'subscribed': False})
        
    except Exception as e:
        print(f"❌ Erreur vérification statut: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/alerts/send_test')
def api_alerts_send_test():
    """API de test pour envoyer une alerte de test"""
    try:
        email = request.args.get('email')
        
        if not email and os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
                subscriptions = json.load(f)
            
            if subscriptions:
                email = subscriptions[0]['email']
        
        if email:
            confirmation_id = hashlib.md5(f"test_{email}_{time.time()}".encode()).hexdigest()[:12].upper()
            email_sent = send_confirmation_email(email, f"TEST-{confirmation_id}")
            
            return jsonify({
                'status': 'success',
                'message': f'Email de test envoyé à {email}',
                'email_sent': email_sent
            })
        
        return jsonify({'status': 'error', 'message': 'Aucun email disponible'})
        
    except Exception as e:
        print(f"❌ Erreur test email: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/admin/email_logs')
def admin_email_logs():
    """Page admin pour voir les logs d'emails"""
    try:
        log_file = config.EMAIL_LOGS_FILE
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Trier par date (du plus récent au plus ancien)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return render_template('email_logs.html', logs=logs, count=len(logs))
        
    except Exception as e:
        return f"Erreur: {e}"

# ===== FONCTIONS DE MAINTENANCE DU CACHE =====

def cleanup_old_cache():
    """Nettoie les fichiers de cache expirés"""
    try:
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(CACHE_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if time.time() > cache_data.get('expires_at', 0):
                        os.remove(filepath)
                        print(f"🗑️ Fichier cache expiré supprimé: {filename}")
                
                except Exception as e:
                    os.remove(filepath)
                    print(f"🗑️ Fichier cache corrompu supprimé: {filename}")
    
    except Exception as e:
        print(f"⚠️ Erreur nettoyage cache: {e}")

# ===== ROUTES STATIQUES =====

@app.route('/static/js/leaflet.js')
def serve_leaflet_js():
    """Servir Leaflet localement si le CDN échoue"""
    try:
        return send_from_directory('static/js', 'leaflet.js')
    except:
        return '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>', 200, {'Content-Type': 'text/javascript'}

@app.route('/static/css/leaflet.css')
def serve_leaflet_css():
    """Servir Leaflet CSS localement si le CDN échoue"""
    try:
        return send_from_directory('static/css', 'leaflet.css')
    except:
        return '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>', 200, {'Content-Type': 'text/css'}

@app.route('/test_meteo_simple')
def test_meteo_simple():
    return render_template('test_meteo_simple.html')

@app.route('/test_mobile_simple')
def test_mobile_simple():
    return render_template('test_mobile_simple.html')

# ===== ROUTES SITEMAP ET ROBOTS (CORRIGÉES) =====

@app.route('/robots.txt')
def robots():
    """Fichier robots.txt CORRIGÉ - permet l'accès à Googlebot"""
    robots_content = """User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /
Sitemap: https://fishing-activity.onrender.com/sitemap.xml
"""
    return robots_content, 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap():
    """Génère le sitemap dynamiquement avec date actuelle"""
    base_url = 'https://fishing-activity.onrender.com'
    today = datetime.now().strftime('%Y-%m-%d')
    
    pages = [
        {'url': '/', 'priority': '1.0', 'changefreq': 'daily'},
        {'url': '/predictions', 'priority': '0.9', 'changefreq': 'weekly'},
        {'url': '/species_selector', 'priority': '0.8', 'changefreq': 'weekly'},
        {'url': '/favorites', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/science', 'priority': '0.7', 'changefreq': 'monthly'},
        {'url': '/alerts', 'priority': '0.6', 'changefreq': 'monthly'},
    ]
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
    
    for page in pages:
        xml += f'''  <url>
    <loc>{base_url}{page['url']}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
'''
    
    xml += '</urlset>'
    
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache 1 heure
    return response

@app.route('/google-verification')
def google_verification():
    """Page de vérification pour Google"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Verification Page</title>
        <meta name="robots" content="index, follow">
        <meta name="googlebot" content="index, follow">
    </head>
    <body>
        <h1>✅ Googlebot Verification</h1>
        <p>This page verifies that Googlebot can access the site.</p>
        <p>Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><a href="/">Return to homepage</a></p>
    </body>
    </html>
    """

@app.route('/test-robots-access')
def test_robots_access():
    """Page pour tester l'accès robots.txt"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Robots.txt Access</title>
    </head>
    <body>
        <h1>Test d'accès Robots.txt</h1>
        <p><a href="/robots.txt" target="_blank">Voir robots.txt</a></p>
        <p><a href="https://fishing-activity.onrender.com/robots.txt" target="_blank">Voir robots.txt (URL complète)</a></p>
        <p><a href="https://search.google.com/test/robots-txt" target="_blank">Tester avec l'outil Google</a></p>
        <p><a href="/">Retour à l'accueil</a></p>
    </body>
    </html>
    """

if __name__=='__main__':
    # Créer les répertoires nécessaires
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.STATIC_DIR + '/js', exist_ok=True)
    os.makedirs(config.STATIC_DIR + '/css', exist_ok=True)
    os.makedirs(config.TEMPLATES_DIR, exist_ok=True)
    
    # Initialiser les fichiers de données
    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    if not os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    
    # Créer le template pour les logs d'emails
    email_logs_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Logs d'Emails - Fishing Predictor Pro</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
            h1 { color: #333; }
            .log-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .log-item.success { border-left: 5px solid #10b981; }
            .log-item.error { border-left: 5px solid #ef4444; }
            .log-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
            .log-email { font-weight: bold; color: #3b82f6; }
            .log-time { color: #64748b; font-size: 0.9em; }
            .log-content { background: #f8fafc; padding: 10px; border-radius: 5px; font-family: monospace; }
            .status-success { color: #10b981; font-weight: bold; }
            .status-error { color: #ef4444; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📧 Logs d'Emails</h1>
            <p>Total: {{ count }} emails envoyés via Gmail</p>
            <div id="logs">
                {% for log in logs %}
                <div class="log-item {% if log.sent %}success{% else %}error{% endif %}">
                    <div class="log-header">
                        <span class="log-email">{{ log.to }}</span>
                        <span class="log-time">{{ log.timestamp }}</span>
                    </div>
                    <div class="log-content">
                        Type: {{ log.type }}<br>
                        Confirmation ID: {{ log.confirmation_id }}<br>
                        Statut: <span class="{% if log.sent %}status-success{% else %}status-error{% endif %}">
                            {% if log.sent %}✅ ENVOYÉ{% else %}❌ ÉCHEC{% endif %}
                        </span><br>
                        Serveur: {{ log.server }}
                    </div>
                </div>
                {% endfor %}
            </div>
            <div style="margin-top: 20px;">
                <a href="/alerts" style="color: #3b82f6;">← Retour aux alertes</a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    # Sauvegarder le template
    with open('templates/email_logs.html', 'w', encoding='utf-8') as f:
        f.write(email_logs_template)
    
    cleanup_old_cache()
    
    # Valider la configuration
    try:
        config.validate_config()
        print("✅ Configuration validée avec succès")
    except ValueError as e:
        print(f"⚠️ Attention: {e}")
        print("   L'application va démarrer avec les valeurs par défaut")
    
    print("="*60)
    print("🎣 FISHING PREDICTOR PRO - VERSION AVEC EMAILS GMAIL")
    print("="*60)
    print(f"✅ Configuration Gmail: {GMAIL_USER}")
    print(f"✅ SMTP: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
    print("✅ Système d'emails activé")
    print("="*60)
    print("🌐 Accès:")
    print("   http://127.0.0.1:5000")
    print("   http://localhost:5000")
    print("   Logs emails: http://localhost:5000/admin/email_logs")
    print("="*60)
    
    print("\n🧪 Test de connexion Gmail...")
    try:
        # Test rapide de connexion SMTP
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.quit()
        print("✅ Connexion Gmail SMTP réussie !")
    except Exception as e:
        print(f"⚠️ Erreur connexion Gmail: {e}")
        print("   Vérifiez:")
        print("   1. Que le mot de passe d'application est correct")
        print("   2. Que les applications moins sécurisées sont activées")
        print("   3. Que l'accès SMTP est autorisé sur le compte Gmail")
    
    print("\n🚀 Démarrage du serveur...")
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
