"""
Handler WEkEO invisible - Améliore les données en arrière-plan
Sans interface utilisateur visible
"""
import numpy as np
import netCDF4
from datetime import datetime, timedelta
from hda import Client, Configuration
import tempfile
import os
import shutil
from typing import Optional, Dict
import hashlib
import json
import time

class WekeoBackgroundEnhancer:
    """Amélioration silencieuse des données en arrière-plan"""
    
    def __init__(self):
        self.username = os.getenv('WEKEO_USER', 'aminech')
        self.password = os.getenv('WEKEO_PASSWORD', 'Nour2024')
        self.client = None
        self.cache_dir = os.path.join(os.path.dirname(__file__), 'data', 'wekeo_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self._silent_init()
    
    def _silent_init(self):
        """Initialisation silencieuse sans logs visibles"""
        try:
            conf = Configuration(user=self.username, password=self.password, timeout=20)
            self.client = Client(config=conf)
            return True
        except Exception:
            self.client = None
            return False
    
    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Génère une clé de cache"""
        key_str = f"wind_{lat:.3f}_{lon:.3f}_{datetime.utcnow().strftime('%Y%m%d%H')}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Charge depuis le cache silencieusement"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                # Vérifier expiration (1 heure)
                if time.time() - data.get('timestamp', 0) < 3600:
                    return data.get('data')
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict):
        """Sauvegarde dans le cache"""
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        cache_data = {
            'data': data,
            'timestamp': time.time()
        }
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except:
            pass
    
    def enhance_wind_data(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Améliore silencieusement les données de vent
        Retourne None si échec (l'utilisateur ne voit rien)
        """
        if not self.client:
            return None
        
        cache_key = self._get_cache_key(lat, lon)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached
        
        try:
            # Chercher des données offshore (moins de NaN)
            offshore_lat, offshore_lon = self._get_offshore_position(lat, lon)
            
            # Dataset de vent fonctionnel
            dataset_id = "EO:MO:DAT:WIND_GLO_PHY_L4_NRT_012_004:cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H_202207"
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=6)
            
            query = {
                "dataset_id": dataset_id,
                "bbox": [offshore_lon-0.15, offshore_lat-0.15, offshore_lon+0.15, offshore_lat+0.15],
                "startdate": start_time.strftime("%Y-%m-%dT00:00:00.000Z"),
                "enddate": end_time.strftime("%Y-%m-%dT23:59:59.999Z"),
                "itemsPerPage": 1
            }
            
            matches = self.client.search(query)
            if not matches:
                return None
            
            temp_dir = tempfile.mkdtemp(prefix="wekeo_")
            matches.download(download_dir=temp_dir)
            
            nc_files = [f for f in os.listdir(temp_dir) if f.endswith('.nc')]
            if not nc_files:
                shutil.rmtree(temp_dir)
                return None
            
            nc_file = os.path.join(temp_dir, nc_files[0])
            wind_data = self._extract_and_clean_data(nc_file, offshore_lat, offshore_lon)
            
            shutil.rmtree(temp_dir)
            
            if wind_data and wind_data.get('wind_speed_ms'):
                self._save_to_cache(cache_key, wind_data)
                return wind_data
            
        except Exception:
            # Silence complet - pas de logs
            pass
        
        return None
    
    def _get_offshore_position(self, lat: float, lon: float) -> tuple:
        """Déplace légèrement vers le large pour éviter les NaN côtiers"""
        # Pour la Tunisie : déplacer vers l'Est/Nord-Est (vers la mer)
        if 35.0 <= lat <= 37.5 and 8.0 <= lon <= 11.0:
            offshore_lat = lat + 0.08  # Un peu au nord
            offshore_lon = lon + 0.12  # Un peu à l'est
            return (offshore_lat, offshore_lon)
        return (lat, lon)
    
    def _extract_and_clean_data(self, nc_file_path: str, lat: float, lon: float) -> Optional[Dict]:
        """Extrait et nettoie les données"""
        try:
            with netCDF4.Dataset(nc_file_path, 'r') as nc:
                if 'eastward_wind' not in nc.variables:
                    return None
                
                lats = nc.variables['latitude'][:]
                lons = nc.variables['longitude'][:]
                
                lat_idx = np.abs(lats - lat).argmin()
                lon_idx = np.abs(lons - lon).argmin()
                
                u_wind = nc.variables['eastward_wind']
                v_wind = nc.variables['northward_wind']
                
                if u_wind.ndim != 3:
                    return None
                
                # Prendre plusieurs échantillons temporels
                time_samples = min(6, u_wind.shape[0])
                u_values = []
                v_values = []
                
                for t in range(-time_samples, 0):
                    try:
                        u_val = float(u_wind[t, lat_idx, lon_idx])
                        v_val = float(v_wind[t, lat_idx, lon_idx])
                        
                        # Filtrer les NaN
                        if not np.isnan(u_val) and not np.isnan(v_val):
                            u_values.append(u_val)
                            v_values.append(v_val)
                    except:
                        continue
                
                if not u_values:
                    return None
                
                # Moyenne des valeurs valides
                u_mean = np.mean(u_values)
                v_mean = np.mean(v_values)
                
                wind_speed = np.sqrt(u_mean**2 + v_mean**2)
                wind_direction = (270 - np.degrees(np.arctan2(v_mean, u_mean))) % 360
                
                return {
                    'wind_speed_ms': float(wind_speed),
                    'wind_speed_kmh': float(wind_speed * 3.6),
                    'wind_direction_deg': float(wind_direction),
                    'samples_count': len(u_values),
                    'source': 'satellite',
                    'extracted_at': datetime.now().isoformat()
                }
                
        except Exception:
            return None

# Instance globale (silencieuse)
wekeo_enhancer = WekeoBackgroundEnhancer()