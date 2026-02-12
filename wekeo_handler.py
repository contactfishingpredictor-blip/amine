# wekeo_handler.py - VERSION CORRIGÉE AVEC ENDPOINT WEKEO FONCTIONNEL
"""
Handler WEkEO fonctionnel avec cascade intelligente
WEkEO → Open-Meteo → Modèle climatique
"""
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
import shutil
from typing import Optional, Dict, Tuple
import hashlib
import json
import time
import math
import requests
import logging

# Configurer un logger silencieux
logging.getLogger("hda").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# ===== IMPORT HDA AVEC PATCH D'ENDPOINT =====
# FORCER l'URL correcte AVANT l'import
os.environ['HDA_URL'] = "https://wekeo.copernicus.eu/api/"

try:
    from hda import Client, Configuration
    HDA_AVAILABLE = True
    
    # PATCH CRITIQUE : forcer l'endpoint sans '2'
    try:
        import hda.api
        hda.api.ENTRY_POINT = "https://wekeo.copernicus.eu/api/"
        print("✅ WEkEO endpoint patché: wekeo.copernicus.eu")
    except:
        pass
        
except ImportError:
    HDA_AVAILABLE = False
    print("⚠️ Bibliothèque hda non disponible")

try:
    import netCDF4
    NETCDF_AVAILABLE = True
except ImportError:
    NETCDF_AVAILABLE = False
    print("⚠️ Bibliothèque netCDF4 non disponible")

class WekeoEnhancedHandler:
    """Handler WEkEO amélioré avec corrections et cascade"""
    
    def __init__(self):
        self.username = os.getenv('WEKEO_USERNAME', 'aminech')
        self.password = os.getenv('WEKEO_PASSWORD', 'Nour2024')
        self.client = None
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'wekeo_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Datasets optimisés
        self.datasets = {
            'wind': 'EO:ECMWF:DAT:REANALYSIS_ERA5_SINGLE_LEVELS',
            'sst_med': 'EO:MO:DAT:SST_MED_SST_L4_REP_OBSERVATIONS_010_021',
        }
        
        self._init_client()
        print(f"✅ WEkEO Handler initialisé - Client: {'✅ Connecté' if self.client else '❌ Non connecté'}")
    
    def _init_client(self):
        """Initialisation robuste du client - CORRIGÉ avec endpoint manuel"""
        if not HDA_AVAILABLE:
            print("ℹ️ Bibliothèque hda non disponible")
            return False
        
        try:
            # ===== PATCH ENDPOINT SUPPLÉMENTAIRE =====
            try:
                import hda.api
                hda.api.ENTRY_POINT = "https://wekeo.copernicus.eu/api/"
                os.environ['HDA_URL'] = "https://wekeo.copernicus.eu/api/"
            except:
                pass
            
            # Essayer les méthodes d'initialisation
            methods = [
                self._init_via_config,  # Méthode officielle avec URL forcée
                self._init_via_simple,  # Fallback .hdarc
            ]
            
            for method in methods:
                try:
                    self.client = method()
                    if self.client:
                        print(f"  ✅ Méthode {method.__name__} réussie")
                        
                        # Test rapide
                        if self._test_client():
                            return True
                        else:
                            self.client = None
                            continue
                            
                except Exception as e:
                    print(f"  ⚠️ Méthode {method.__name__} échouée: {e}")
                    continue
            
            print("❌ Toutes les méthodes d'initialisation ont échoué")
            return False
            
        except Exception as e:
            print(f"❌ Erreur initialisation: {e}")
            return False
    
    def _init_via_config(self):
        """Méthode officielle : Configuration(user, password, url)"""
        try:
            from hda import Configuration, Client
            # FORCER l'URL correcte dans la configuration
            conf = Configuration(
                user=self.username, 
                password=self.password,
                url="https://wekeo.copernicus.eu/api/"  # CRITIQUE : sans '2' !
            )
            return Client(config=conf)
        except Exception as e:
            print(f"  ⚠️ _init_via_config: {e}")
            return None
    
    def _init_via_simple(self):
        """Méthode 2: Simple (utilise .netrc/.hdarc)"""
        try:
            return Client()
        except Exception as e:
            return None
    
    def _test_client(self):
        """Test rapide du client avec requête MINIMALE"""
        try:
            query = {
                "dataset_id": self.datasets['wind'],
                "startdate": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z"),
                "enddate": datetime.now().strftime("%Y-%m-%dT23:59:59.999Z"),
                "bbox": [10.0, 36.0, 10.5, 36.5],
                "itemsPerPage": 1  # Limiter à 1 résultat
            }
            matches = self.client.search(query)
            print(f"  🔍 Test client: {len(matches) if matches else 0} résultats")
            return matches is not None
        except Exception as e:
            print(f"  ⚠️ Test client échoué: {e}")
            return False
    
    def get_wind_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Récupère les données de vent avec cascade intelligente
        1. WEkEO → 2. Open-Meteo → 3. Modèle climatique
        """
        cache_key = self._get_cache_key('wind', lat, lon)
        
        # Vérifier cache (1 heure)
        cached = self._load_from_cache(cache_key)
        if cached:
            print(f"💾 Vent depuis cache: {cached.get('source', 'cache')}")
            return cached
        
        print(f"🌬️  Récupération vent pour ({lat:.3f}, {lon:.3f})")
        
        # 1. Essayer WEkEO
        wekeo_data = self._try_wekeo_wind(lat, lon)
        if wekeo_data:
            self._save_to_cache(cache_key, wekeo_data)
            return wekeo_data
        
        # 2. Essayer Open-Meteo (fallback fiable)
        om_data = self._try_openmeteo_wind(lat, lon)
        if om_data:
            self._save_to_cache(cache_key, om_data)
            return om_data
        
        # 3. Modèle climatique (dernier recours)
        model_data = self._get_climatic_wind(lat, lon)
        self._save_to_cache(cache_key, model_data)
        return model_data
    
    def _try_wekeo_wind(self, lat: float, lon: float) -> Optional[Dict]:
        """Tentative WEkEO avec gestion d'erreurs"""
        if not self.client:
            return None
        
        try:
            # Ajuster position pour mer
            adj_lat, adj_lon = self._adjust_for_sea(lat, lon)
            
            query = {
                "dataset_id": self.datasets['wind'],
                "startdate": (datetime.now() - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "enddate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.999Z"),
                "bbox": [adj_lon-0.1, adj_lat-0.1, adj_lon+0.1, adj_lat+0.1],  # BBOX réduite
                "itemsPerPage": 1  # UN seul résultat
            }
            
            print("  🔍 Requête WEkEO ERA5...")
            matches = self.client.search(query)
            
            if not matches:
                print("  ℹ️  Aucun résultat WEkEO")
                return None
            
            # Télécharger le premier fichier
            temp_dir = tempfile.mkdtemp(prefix="wekeo_")
            try:
                # Ne télécharger que le premier résultat
                if hasattr(matches, '__getitem__'):
                    matches[0].download(download_dir=temp_dir)
                else:
                    matches.download(download_dir=temp_dir)
                
                # Chercher fichier netCDF
                nc_files = [f for f in os.listdir(temp_dir) if f.endswith('.nc')]
                if not nc_files:
                    return None
                
                nc_file = os.path.join(temp_dir, nc_files[0])
                wind_data = self._extract_wind_nc(nc_file)
                
                if wind_data:
                    wind_data.update({
                        'source': 'WEkEO (ERA5)',
                        'quality': 'high',
                        'resolution': '0.25°'
                    })
                    print(f"  ✅ Vent WEkEO: {wind_data.get('wind_speed_kmh')} km/h")
                    return wind_data
                    
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    
        except Exception as e:
            print(f"  ⚠️  WEkEO erreur: {type(e).__name__}: {str(e)[:100]}")
        
        return None
    
    def _try_openmeteo_wind(self, lat: float, lon: float) -> Optional[Dict]:
        """Open-Meteo fallback (rapide et fiable)"""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'wind_speed_10m,wind_direction_10m',
                'timezone': 'Africa/Tunis'
            }
            
            print("  🌐 Requête Open-Meteo...")
            response = requests.get(url, params=params, timeout=3)
            
            if response.status_code == 200:
                data = response.json()['current']
                wind_data = {
                    'wind_speed_kmh': data['wind_speed_10m'],
                    'wind_direction_deg': data['wind_direction_10m'],
                    'wind_speed_ms': round(data['wind_speed_10m'] / 3.6, 1),
                    'source': 'Open-Meteo',
                    'quality': 'medium',
                    'resolution': '11km'
                }
                print(f"  ✅ Vent Open-Meteo: {data['wind_speed_10m']} km/h")
                return wind_data
                
        except Exception as e:
            print(f"  ⚠️  Open-Meteo erreur: {e}")
        
        return None
    
    def _get_climatic_wind(self, lat: float, lon: float) -> Dict:
        """Modèle climatique réaliste Tunisie"""
        now = datetime.now()
        hour = now.hour
        month = now.month
        
        # Base climatologique
        if month in [12, 1, 2]:  # Hiver
            base_speed, base_dir, variation = 15, 300, 5
        elif month in [6, 7, 8]:  # Été
            base_speed, base_dir, variation = 10, 90, 3
        else:  # Intersaison
            base_speed, base_dir, variation = 12, 180, 4
        
        # Variation diurne
        diurnal = 1.0 + 0.2 * math.sin((hour - 14) * math.pi / 12)
        
        # Variation position
        if lat > 37.0:  # Nord
            pos_factor, dir_adj = 1.1, 15
        elif lat > 36.0:  # Centre
            pos_factor, dir_adj = 1.0, 0
        else:  # Sud
            pos_factor, dir_adj = 0.9, -15
        
        # Calcul final
        wind_speed = base_speed * diurnal * pos_factor
        wind_speed += (hash(str(lat)+str(lon)+str(hour)) % variation) - variation/2
        
        wind_direction = (base_dir + dir_adj) % 360
        
        return {
            'wind_speed_kmh': max(5, min(40, round(wind_speed, 1))),
            'wind_direction_deg': int(wind_direction),
            'wind_speed_ms': round(wind_speed / 3.6, 1),
            'source': 'Modèle climatique Tunisie',
            'quality': 'low',
            'note': 'Données estimées basées sur climatologie'
        }
    
    def get_enhanced_data(self, lat: float, lon: float) -> Dict:
        """Données améliorées complètes"""
        result = {
            'wind': self.get_wind_data(lat, lon),
            'success': False,
            'sources': [],
            'timestamp': datetime.now().isoformat()
        }
        
        if result['wind']:
            result['sources'].append('wind')
            result['success'] = True
        
        return result
    
    # ===== FONCTIONS UTILITAIRES =====
    
    def _get_cache_key(self, data_type: str, lat: float, lon: float) -> str:
        """Génère une clé de cache"""
        hour_block = datetime.now().hour // 3
        key_str = f"{data_type}_{lat:.2f}_{lon:.2f}_{hour_block}"
        return hashlib.md5(key_str.encode()).hexdigest()[:10]
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Charge depuis cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                if time.time() - data.get('timestamp', 0) < 3600:  # 1 heure
                    return data.get('data')
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Sauvegarde en cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        try:
            cache_data = {
                'data': data,
                'timestamp': time.time(),
                'expires': time.time() + 3600
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except:
            pass
    
    def _adjust_for_sea(self, lat: float, lon: float) -> Tuple[float, float]:
        """Ajuste position pour être en mer"""
        adjusted_lon = lon + 0.15
        if 35.0 <= lat <= 35.5:
            adjusted_lat = lat + 0.1
        elif 35.5 < lat <= 36.5:
            adjusted_lat = lat + 0.08
        else:
            adjusted_lat = lat - 0.05
        return adjusted_lat, adjusted_lon
    
    def _extract_wind_nc(self, nc_file: str) -> Optional[Dict]:
        """Extrait vent depuis netCDF"""
        if not NETCDF_AVAILABLE:
            return None
        
        try:
            import netCDF4
            with netCDF4.Dataset(nc_file, 'r') as nc:
                # Chercher variables
                u_var = v_var = None
                for var_name in nc.variables:
                    var_lower = var_name.lower()
                    if 'u10' in var_lower or 'eastward' in var_lower:
                        u_var = nc.variables[var_name]
                    elif 'v10' in var_lower or 'northward' in var_lower:
                        v_var = nc.variables[var_name]
                
                if u_var is None or v_var is None:
                    return None
                
                # Extraire données
                u_data = u_var[:]
                v_data = v_var[:]
                
                # Prendre la première valeur
                if u_data.ndim == 3:
                    u_val = float(u_data[0, 0, 0])
                    v_val = float(v_data[0, 0, 0])
                elif u_data.ndim == 2:
                    u_val = float(u_data[0, 0])
                    v_val = float(v_data[0, 0])
                else:
                    return None
                
                # Calculer
                wind_speed_ms = math.sqrt(u_val**2 + v_val**2)
                wind_direction = (270 - math.degrees(math.atan2(v_val, u_val))) % 360
                
                return {
                    'wind_speed_ms': round(wind_speed_ms, 1),
                    'wind_speed_kmh': round(wind_speed_ms * 3.6, 1),
                    'wind_direction_deg': round(wind_direction, 0),
                    'u_component': round(u_val, 3),
                    'v_component': round(v_val, 3)
                }
                
        except Exception as e:
            print(f"⚠️ Extraction netCDF: {e}")
        
        return None

# ===== INSTANCE GLOBALE =====
wekeo_enhancer = WekeoEnhancedHandler()

# ===== FONCTIONS EXPOSÉES POUR COMPATIBILITÉ AVEC APP.PY =====
def get_wind_data(lat: float, lon: float) -> Optional[Dict]:
    """Wrapper pour app.py - retourne les données de vent"""
    return wekeo_enhancer.get_wind_data(lat, lon)

def test_connection() -> bool:
    """Teste la connexion WEkEO"""
    try:
        if wekeo_enhancer.client and wekeo_enhancer._test_client():
            print("✅ Connexion WEkEO opérationnelle")
            return True
        else:
            print("❌ Connexion WEkEO échouée")
            return False
    except Exception as e:
        print(f"⚠️ Erreur test connexion: {e}")
        return False

# ===== FONCTIONS DE COMPATIBILITÉ SUPPLÉMENTAIRES =====
def enhance_wind_data(lat: float, lon: float) -> Optional[Dict]:
    """Fonction compatible avec ancien code"""
    return wekeo_enhancer.get_wind_data(lat, lon)

def get_enhanced_fishing_data(lat: float, lon: float) -> Dict:
    """Fonction pour données complètes"""
    return wekeo_enhancer.get_enhanced_data(lat, lon)