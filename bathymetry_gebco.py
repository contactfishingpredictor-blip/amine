# 📁 bathymetry_gebco.py
import os
import numpy as np
import netCDF4 as nc
import hashlib
import json
import time

class GebcoBathymetry:
    """Bathymétrie précise - GEBCO 2025 Tunisie + SPOTS EXPERTS PRIORITAIRES"""
    
    def __init__(self, file_path='data/gebco_tunisie.nc'):
        self.file_path = file_path
        self.cache_dir = 'data/bathymetry_cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lats = None
        self.lons = None
        self.depths = None
        self._load()
    
    def _load(self):
        """Charge le fichier NetCDF GEBCO"""
        try:
            if not os.path.exists(self.file_path):
                print(f"ℹ️ Fichier GEBCO non trouvé: {self.file_path}")
                print(f"   Utilisation du modèle Tunisie uniquement")
                return False
            
            print(f"📊 Chargement GEBCO: {self.file_path}")
            ds = nc.Dataset(self.file_path, 'r')
            
            self.lats = ds.variables['lat'][:]
            self.lons = ds.variables['lon'][:]
            self.depths = ds.variables['elevation'][:]
            
            ds.close()
            print(f"✅ GEBCO chargé: {len(self.lats)}x{len(self.lons)} points")
            return True
        except Exception as e:
            print(f"ℹ️ GEBCO non disponible: {e}")
            return False
    
    def get_depth(self, lat, lon):
        """Récupère la profondeur depuis GEBCO (avec cache)"""
        
        # Cache disque
        cache_key = hashlib.md5(f"{lat:.4f}_{lon:.4f}".encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                if time.time() - cached['timestamp'] < 86400 * 30:  # 30 jours
                    return cached['depth']
            except:
                pass
        
        if self.lats is None or self.lons is None or self.depths is None:
            return None
        
        # Trouver le point le plus proche
        lat_idx = np.argmin(np.abs(self.lats - lat))
        lon_idx = np.argmin(np.abs(self.lons - lon))
        
        # Profondeur = valeur absolue (négatif = mer)
        depth = abs(float(self.depths[lat_idx, lon_idx]))
        
        # Sauvegarde cache
        with open(cache_file, 'w') as f:
            json.dump({
                'depth': depth,
                'timestamp': time.time(),
                'lat': lat,
                'lon': lon
            }, f)
        
        return depth
    
    def get_depth_with_fallback(self, lat, lon):
        """
        🎯 PRIORITÉ ABSOLUE : TES SPOTS EXPERTS !
        → GEBCO est utilisé seulement en 2ème choix
        """
        
        # ===== 1️⃣ D'ABORD TES SPOTS (TU CONNAIS MIEUX QUE GEBCO !) =====
        spot_result = self._tunisia_expert(lat, lon)
        if spot_result['confidence'] >= 0.9:  # C'est TON spot ou zone expert
            return spot_result
        
        # ===== 2️⃣ ENSUITE GEBCO (si pas dans tes spots) =====
        try:
            depth = self.get_depth(lat, lon)
            if depth and depth > 0:
                # Vérifier si la profondeur GEBCO est crédible
                if 0.5 <= depth <= 200:  # Plage plausible pour Tunisie
                    return {
                        'success': True,
                        'depth': round(depth, 1),
                        'source': 'GEBCO 2025',
                        'accuracy': 'moyenne',
                        'confidence': 0.7  # Confiance réduite
                    }
        except:
            pass
        
        # ===== 3️⃣ FALLBACK = Modèle Tunisie =====
        return self._tunisia_model(lat, lon)
    
    def _tunisia_expert(self, lat, lon):
        """
        🏆 CARTE EXPERT TUNISIE - TES SPOTS PERSONNELS
        Ces données sont PLUS FIABLES que GEBCO !
        """
        
        # === TES SPOTS - AJOUTE LES TIENS ICI ===
        spots = [
            # [lat_min, lat_max, lon_min, lon_max, profondeur, nom]
            # --- CAP BON / KÉLIBIA ---
            [36.84, 36.86, 11.08, 11.10, 45, "Kélibia Nord - Canyon"],
            [36.81, 36.83, 11.09, 11.11, 30, "Kélibia Sud - Plateau"],
            [36.86, 36.88, 11.05, 11.07, 35, "El Haouaria"],
            
            # --- GHAR EL MELH ---
            [37.15, 37.17, 10.17, 10.19, 2.5, "Ghar El Melh - Lagune"],
            [37.17, 37.19, 10.19, 10.21, 8, "Ghar El Melh - Mer"],
            
            # --- BIZERTE ---
            [37.26, 37.28, 9.86, 9.88, 50, "Bizerte - Large"],
            [37.27, 37.29, 9.84, 9.86, 35, "Bizerte - Canal"],
            [37.24, 37.26, 9.88, 9.90, 15, "Bizerte - Baie"],
            
            # --- TUNIS ---
            [36.79, 36.81, 10.17, 10.19, 25, "Tunis - Rade"],
            [36.80, 36.82, 10.20, 10.22, 30, "Tunis - Large"],
            [36.78, 36.80, 10.15, 10.17, 15, "Tunis - Côte"],
            
            # --- HAMMAMET ---
            [36.41, 36.43, 10.61, 10.63, 15, "Hammamet - Nord"],
            [36.39, 36.41, 10.59, 10.61, 12, "Hammamet - Centre"],
            [36.37, 36.39, 10.57, 10.59, 18, "Hammamet - Sud"],
            
            # --- SOUSSE / MONASTIR ---
            [35.81, 35.83, 10.63, 10.65, 12, "Sousse - Port"],
            [35.77, 35.79, 10.82, 10.84, 10, "Monastir - Ribat"],
            [35.75, 35.77, 10.85, 10.87, 15, "Monastir - Large"],
            
            # --- MAHDIA ---
            [35.49, 35.51, 11.05, 11.07, 25, "Mahdia - Cap"],
            [35.47, 35.49, 11.08, 11.10, 30, "Mahdia - Large"],
            
            # --- DJERBA ---
            [33.80, 33.82, 10.84, 10.86, 8, "Djerba - Houmt Souk"],
            [33.78, 33.80, 10.88, 10.90, 15, "Djerba - Large"],
            [33.72, 33.74, 10.74, 10.76, 6, "Djerba - Ajim"],
            
            # --- ZARZIS ---
            [33.49, 33.51, 11.11, 11.13, 15, "Zarzis - Port"],
            [33.48, 33.50, 11.14, 11.16, 20, "Zarzis - Large"],
            
            # --- TABARKA ---
            [36.94, 36.96, 8.74, 8.76, 60, "Tabarka - Canyon"],
            [36.95, 36.97, 8.77, 8.79, 45, "Tabarka - Rochers"],
            
            # --- GOLFE DE TUNIS ---
            [36.83, 36.85, 10.30, 10.32, 35, "Golfe de Tunis - Centre"],
            [36.82, 36.84, 10.25, 10.27, 30, "Golfe de Tunis - Sud"],
            
            # --- ZONES SUPPLÉMENTAIRES ---
            [37.05, 37.07, 11.01, 11.03, 55, "Cap Bon - Extrême Nord"],
            [35.55, 35.57, 11.10, 11.12, 40, "Mahdia - Sud"],
            [34.72, 34.74, 10.74, 10.76, 12, "Sfax - Kerkennah"],
        ]
        
        for spot in spots:
            lat_min, lat_max, lon_min, lon_max, depth, name = spot
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return {
                    'success': True,
                    'depth': depth,
                    'source': f'Expert Tunisie - {name}',
                    'accuracy': 'excellente',
                    'confidence': 0.99  # Confiance MAXIMALE
                }
        
        # Pas dans les spots précis
        return {
            'success': False,
            'confidence': 0
        }
    
    def _tunisia_model(self, lat, lon):
        """
        🌊 MODÈLE BATHYMÉTRIQUE TUNISIE
        Utilisé quand GEBCO et spots experts ne sont pas disponibles
        """
        
        # Déterminer la zone géographique
        if lat > 37.0:  # Nord extrême (Bizerte, Tabarka)
            base_depth = 50
            gradient = 30
        elif lat > 36.5:  # Tunis, Cap Bon
            base_depth = 35
            gradient = 25
        elif lat > 36.0:  # Hammamet, Nabeul
            base_depth = 25
            gradient = 20
        elif lat > 35.0:  # Sahel (Sousse, Monastir, Mahdia)
            base_depth = 20
            gradient = 15
        elif lat > 34.0:  # Sfax
            base_depth = 15
            gradient = 12
        else:  # Sud (Djerba, Zarzis, Gabès)
            base_depth = 12
            gradient = 10
        
        # Distance approximative à la côte (degrés)
        dist_cote = min(
            abs(lon - 8.8) if lat > 36.8 else 999,  # Tabarka
            abs(lon - 9.87) if 37.2 < lat < 37.3 else 999,  # Bizerte
            abs(lon - 10.18) if 36.7 < lat < 36.9 else 999,  # Tunis
            abs(lon - 10.6) if 36.3 < lat < 36.5 else 999,  # Hammamet
            abs(lon - 10.64) if 35.7 < lat < 35.9 else 999,  # Sousse
            abs(lon - 10.83) if 35.7 < lat < 35.8 else 999,  # Monastir
            abs(lon - 11.06) if 35.4 < lat < 35.6 else 999,  # Mahdia
            abs(lon - 10.76) if 34.7 < lat < 34.8 else 999,  # Sfax
            abs(lon - 10.85) if 33.7 < lat < 33.9 else 999,  # Djerba
            abs(lon - 11.12) if 33.4 < lat < 33.6 else 999,  # Zarzis
        )
        
        # Calcul de la profondeur
        depth = base_depth + (dist_cote * gradient * 0.8)
        
        # Contraintes
        if lat > 37.0 and lon < 9.0:  # Canyon de Tabarka
            depth = min(depth, 200)
        elif lat > 36.8 and lon > 11.0:  # Cap Bon large
            depth = min(depth, 150)
        elif lat < 34.0 and lon > 11.0:  # Golfe de Gabès
            depth = min(depth, 40)
        else:
            depth = min(depth, 100)
        
        depth = max(2, round(depth, 1))  # Minimum 2m
        
        # Déterminer la source
        if self._is_coastal_zone(lat, lon):
            source = "Modèle côtier Tunisie"
            confiance = 0.8
        else:
            source = "Modèle bathymétrique Tunisie"
            confiance = 0.75
        
        return {
            'success': True,
            'depth': depth,
            'source': source,
            'accuracy': 'bonne',
            'confidence': confiance
        }
    
    def _is_coastal_zone(self, lat, lon):
        """Vérifie si le point est en zone côtière"""
        # Liste des zones côtières principales
        coastal_zones = [
            (36.7, 37.3, 9.8, 10.4),  # Bizerte-Tunis
            (36.3, 36.5, 10.5, 10.7),  # Hammamet
            (35.7, 35.9, 10.6, 10.9),  # Sousse-Monastir
            (35.4, 35.6, 11.0, 11.1),  # Mahdia
            (34.7, 34.8, 10.7, 10.8),  # Sfax
            (33.7, 33.9, 10.8, 11.0),  # Djerba
            (33.4, 33.6, 11.1, 11.2),  # Zarzis
        ]
        
        for lat_min, lat_max, lon_min, lon_max in coastal_zones:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return True
        return False
    
    def get_spot_info(self, lat, lon):
        """Retourne toutes les infos sur un spot"""
        result = self.get_depth_with_fallback(lat, lon)
        
        # Ajouter des infos supplémentaires
        if result['confidence'] >= 0.99:
            result['reliability'] = 'TRÈS FIABLE - Données expert'
        elif result['confidence'] >= 0.8:
            result['reliability'] = 'Fiable - Modèle Tunisie'
        else:
            result['reliability'] = 'Moyennement fiable - Données GEBCO'
        
        # Zone géographique
        if lat > 37.0:
            result['zone'] = 'Nord Tunisie'
        elif lat > 36.5:
            result['zone'] = 'Tunis / Cap Bon'
        elif lat > 36.0:
            result['zone'] = 'Hammamet / Nabeul'
        elif lat > 35.0:
            result['zone'] = 'Sahel'
        else:
            result['zone'] = 'Sud Tunisie'
        
        return result

# ===== INSTANCE GLOBALE =====
gebco = GebcoBathymetry()


# ===== FONCTION DE TEST =====
def test_spots():
    """Test rapide des principaux spots"""
    spots = [
        (36.85, 11.09, "Kélibia"),
        (37.16, 10.18, "Ghar El Melh"),
        (37.27, 9.87, "Bizerte"),
        (36.80, 10.18, "Tunis"),
        (36.40, 10.60, "Hammamet"),
        (35.82, 10.64, "Sousse"),
        (33.80, 10.85, "Djerba"),
    ]
    
    print("\n" + "="*60)
    print("🏝️  TEST BATHYMÉTRIE TUNISIE - SPOTS EXPERTS")
    print("="*60)
    
    for lat, lon, nom in spots:
        result = gebco.get_depth_with_fallback(lat, lon)
        print(f"\n📍 {nom}: ({lat}, {lon})")
        print(f"   Profondeur: {result['depth']}m")
        print(f"   Source: {result['source']}")
        print(f"   Confiance: {result['confidence']*100:.0f}%")
        print(f"   Précision: {result['accuracy']}")

if __name__ == "__main__":
    test_spots()