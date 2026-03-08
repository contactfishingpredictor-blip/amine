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
                # Cache permanent pour GEBCO (données statiques)
                return cached['depth']
            except:
                pass
        
        if self.lats is None or self.lons is None or self.depths is None:
            return None
        
        # Trouver le point le plus proche
        lat_idx = np.argmin(np.abs(self.lats - lat))
        lon_idx = np.argmin(np.abs(self.lons - lon))
        
        # Récupérer la valeur GEBCO (négatif = mer, positif = terre)
        gebco_value = float(self.depths[lat_idx, lon_idx])
        
        # 🔴 CORRECTION CRITIQUE: Ne pas prendre abs() si c'est de la terre
        if gebco_value >= 0:
            # C'est de la terre ferme, pas de profondeur
            return None
        
        # C'est de la mer, profondeur = valeur absolue
        depth = abs(gebco_value)
        
        # Sauvegarde cache (sans expiration)
        with open(cache_file, 'w') as f:
            json.dump({
                'depth': depth,
                'timestamp': time.time(),
                'lat': lat,
                'lon': lon,
                'gebco_value': gebco_value
            }, f)
        
        return depth
    
    def get_depth_with_fallback(self, lat, lon):
        """
        🎯 PRIORITÉ ABSOLUE : TES SPOTS EXPERTS !
        → GEBCO est utilisé seulement en 2ème choix
        """
        
        # ===== 1️⃣ D'ABORD TES SPOTS (TU CONNAIS MIEUX QUE GEBCO !) =====
        spot_result = self._tunisia_expert(lat, lon)
        if spot_result['success'] and spot_result['confidence'] >= 0.9:
            return spot_result
        
        # ===== 2️⃣ ENSUITE GEBCO (si pas dans tes spots) =====
        try:
            depth = self.get_depth(lat, lon)
            if depth is not None and depth > 0:
                # Vérifier si la profondeur GEBCO est crédible
                if 0.5 <= depth <= 200:
                    return {
                        'success': True,
                        'depth': round(depth, 1),
                        'source': 'GEBCO 2025',
                        'accuracy': 'moyenne',
                        'confidence': 0.7
                    }
        except:
            pass
        
        # ===== 3️⃣ FALLBACK = Modèle Tunisie =====
        return self._tunisia_model(lat, lon)
    
    def _tunisia_expert(self, lat, lon):
        """
        🏆 CARTE EXPERT TUNISIE - SPOTS PERSONNELS
        Ces données sont PLUS FIABLES que GEBCO !
        """
        
        # === SPOTS EXPERTS - VERSION FINALE AVEC PRIORITÉ CORRECTE ===
        spots = [
            # [lat_min, lat_max, lon_min, lon_max, profondeur, nom]
            
            # ===== 1. PORTS DE PÊCHE (PRIORITÉ MAXIMALE - 2-5m) =====
            [36.88, 36.94, 10.26, 10.32, 4.0, "Marina Gammarth - Port de plaisance"],
            [36.83, 36.85, 11.07, 11.09, 4.0, "Kélibia - Port de pêche"],
            [37.17, 37.19, 10.19, 10.21, 3.5, "Ghar El Melh - Port"],
            [37.24, 37.26, 9.88, 9.90, 4.0, "Bizerte - Port de pêche"],
            [36.79, 36.81, 10.16, 10.18, 3.5, "Tunis - Port de plaisance"],
            [36.40, 36.42, 10.60, 10.62, 3.0, "Hammamet - Vieux port"],
            [35.80, 35.82, 10.62, 10.64, 4.0, "Sousse - Port de pêche"],
            [35.76, 35.78, 10.83, 10.85, 3.5, "Monastir - Port de pêche"],
            [35.48, 35.50, 11.06, 11.08, 4.0, "Mahdia - Port de pêche"],
            [34.70, 34.72, 10.75, 10.77, 4.0, "Sfax - Port de pêche"],
            [33.79, 33.81, 10.85, 10.87, 3.0, "Djerba - Houmt Souk port"],
            [33.48, 33.50, 11.12, 11.14, 4.0, "Zarzis - Port de pêche"],
            [36.94, 36.96, 8.75, 8.77, 5.0, "Tabarka - Port de pêche"],
            [33.88, 33.90, 10.10, 10.12, 4.0, "Gabès - Port de pêche"],
            
            # ===== 2. ZONES CÔTIÈRES / PLAGES =====
            [36.80, 36.82, 10.17, 10.19, 5.0, "Tunis - Plage Salammbô"],
            [36.40, 36.42, 10.60, 10.62, 3.0, "Hammamet - Plage"],
            [35.82, 35.84, 10.63, 10.65, 5.0, "Sousse - Plage Boujaafar"],
            [35.77, 35.79, 10.82, 10.84, 5.0, "Monastir - Plage"],
            [33.80, 33.82, 10.84, 10.86, 5.0, "Djerba - Plage Houmt Souk"],
            [36.90, 36.92, 10.30, 10.32, 4.0, "Gammarth - Plage"],
            [37.15, 37.17, 10.17, 10.19, 2.5, "Ghar El Melh - Lagune"],
            
            # ===== 3. PORTS DE COMMERCE =====
            [36.81, 36.83, 11.09, 11.11, 30, "Kélibia - Port de commerce"],
            [37.27, 37.29, 9.84, 9.86, 35, "Bizerte - Canal"],
            [36.79, 36.81, 10.17, 10.19, 25, "Tunis - Rade"],
            [35.81, 35.83, 10.63, 10.65, 12, "Sousse - Port de commerce"],
            [33.49, 33.51, 11.11, 11.13, 15, "Zarzis - Port de commerce"],
            
            # ===== 4. ZONES PROFONDES / LARGE =====
            [36.84, 36.86, 11.08, 11.10, 45, "Kélibia Nord - Canyon"],
            [36.86, 36.88, 11.05, 11.07, 35, "El Haouaria"],
            [37.26, 37.28, 9.86, 9.88, 50, "Bizerte - Large"],
            [36.80, 36.82, 10.20, 10.22, 30, "Tunis - Large"],
            [36.78, 36.80, 10.15, 10.17, 15, "Tunis - Côte"],
            [36.41, 36.43, 10.61, 10.63, 15, "Hammamet - Nord"],
            [36.39, 36.41, 10.59, 10.61, 12, "Hammamet - Centre"],
            [36.37, 36.39, 10.57, 10.59, 18, "Hammamet - Sud"],
            [35.77, 35.79, 10.82, 10.84, 10, "Monastir - Ribat"],
            [35.75, 35.77, 10.85, 10.87, 15, "Monastir - Large"],
            [35.49, 35.51, 11.05, 11.07, 25, "Mahdia - Cap"],
            [35.47, 35.49, 11.08, 11.10, 30, "Mahdia - Large"],
            [33.80, 33.82, 10.84, 10.86,  8, "Djerba - Houmt Souk"],
            [33.78, 33.80, 10.88, 10.90, 15, "Djerba - Large"],
            [33.72, 33.74, 10.74, 10.76,  6, "Djerba - Ajim"],
            [36.94, 36.96, 8.74, 8.76, 60, "Tabarka - Canyon"],
            [36.95, 36.97, 8.77, 8.79, 45, "Tabarka - Rochers"],
            [36.83, 36.85, 10.30, 10.32, 35, "Golfe de Tunis - Centre"],
            [36.82, 36.84, 10.25, 10.27, 30, "Golfe de Tunis - Sud"],
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
                    'confidence': 0.99
                }
        
        return {'success': False, 'confidence': 0}
    
    def _tunisia_model(self, lat, lon):
        """
        🌊 MODÈLE BATHYMÉTRIQUE TUNISIE
        Utilisé quand GEBCO et spots experts ne sont pas disponibles
        """
        
        # Liste des petits ports de pêche (fallback)
        petits_ports = [
            [36.88, 36.94, 10.26, 10.32, 4.0, "Marina Gammarth"],
            [36.83, 36.85, 11.07, 11.09, 4.0, "Kélibia port"],
            [37.15, 37.17, 10.17, 10.19, 2.5, "Ghar El Melh lagune"],
            [37.17, 37.19, 10.19, 10.21, 3.5, "Ghar El Melh port"],
            [37.24, 37.26, 9.88, 9.90, 4.0, "Bizerte pêche"],
            [36.79, 36.81, 10.16, 10.18, 3.5, "Tunis plaisance"],
            [36.40, 36.42, 10.60, 10.62, 3.0, "Hammamet vieux port"],
            [35.80, 35.82, 10.62, 10.64, 4.0, "Sousse pêche"],
            [35.76, 35.78, 10.83, 10.85, 3.5, "Monastir pêche"],
            [35.48, 35.50, 11.06, 11.08, 4.0, "Mahdia pêche"],
            [34.70, 34.72, 10.75, 10.77, 4.0, "Sfax pêche"],
            [33.79, 33.81, 10.85, 10.87, 3.0, "Djerba Houmt Souk"],
            [33.48, 33.50, 11.12, 11.14, 4.0, "Zarzis pêche"],
            [36.94, 36.96, 8.75, 8.77, 5.0, "Tabarka pêche"],
            [33.88, 33.90, 10.10, 10.12, 4.0, "Gabès pêche"],
        ]
        
        # Vérifier si on est dans un petit port
        for port in petits_ports:
            lat_min, lat_max, lon_min, lon_max, depth, name = port
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return {
                    'success': True,
                    'depth': depth,
                    'source': f'Port Tunisien - {name}',
                    'accuracy': 'bonne',
                    'confidence': 0.9
                }
        
        # Déterminer la zone géographique
        if lat > 37.0:
            base_depth, gradient = 50, 30
        elif lat > 36.5:
            base_depth, gradient = 35, 25
        elif lat > 36.0:
            base_depth, gradient = 25, 20
        elif lat > 35.0:
            base_depth, gradient = 20, 15
        elif lat > 34.0:
            base_depth, gradient = 15, 12
        else:
            base_depth, gradient = 12, 10
        
        # Distance approximative à la côte (degrés)
        dist_cote = self._estimate_distance_to_coast(lat, lon)
        
        # Calcul de la profondeur
        depth = base_depth + (dist_cote * gradient * 0.8)
        
        # Correction pour les zones très côtières
        if dist_cote < 0.02:  # Moins de 2km
            depth = max(2.0, min(depth, 8.0))
        elif dist_cote < 0.05:  # 2-5km
            depth = max(3.0, min(depth, 15.0))
        
        # Contraintes géologiques
        if lat > 37.0 and lon < 9.0:
            depth = min(depth, 200)
        elif lat > 36.8 and lon > 11.0:
            depth = min(depth, 150)
        elif lat < 34.0 and lon > 11.0:
            depth = min(depth, 40)
        else:
            depth = min(depth, 100)
        
        depth = max(2, round(depth, 1))
        
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
    
    def _estimate_distance_to_coast(self, lat, lon):
        """Estime la distance à la côte en degrés"""
        cotes = [
            (37.28, 9.87),   # Bizerte
            (36.80, 10.18),  # Tunis
            (36.40, 10.60),  # Hammamet
            (35.82, 10.64),  # Sousse
            (35.77, 10.83),  # Monastir
            (35.50, 11.06),  # Mahdia
            (34.73, 10.76),  # Sfax
            (33.87, 10.85),  # Djerba
            (33.50, 11.12),  # Zarzis
            (33.88, 10.10),  # Gabès
            (36.95, 8.75),   # Tabarka
            (37.16, 10.19),  # Ghar El Melh
            (36.85, 11.09),  # Kélibia
            (36.90, 10.29),  # Gammarth
        ]
        min_dist = min(((lat - clat)**2 + (lon - clon)**2)**0.5 for clat, clon in cotes)
        return min_dist
    
    def _is_coastal_zone(self, lat, lon):
        """Vérifie si le point est en zone côtière"""
        zones = [
            (36.7, 37.3, 9.8, 10.4),   # Bizerte-Tunis
            (36.3, 36.5, 10.5, 10.7),  # Hammamet
            (35.7, 35.9, 10.6, 10.9),  # Sousse-Monastir
            (35.4, 35.6, 11.0, 11.1),  # Mahdia
            (34.7, 34.8, 10.7, 10.8),  # Sfax
            (33.7, 33.9, 10.8, 11.0),  # Djerba
            (33.4, 33.6, 11.1, 11.2),  # Zarzis
            (36.88, 36.94, 10.26, 10.32),  # Gammarth
        ]
        for lat_min, lat_max, lon_min, lon_max in zones:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return True
        return False
    
    def get_spot_info(self, lat, lon):
        """Retourne toutes les infos sur un spot"""
        result = self.get_depth_with_fallback(lat, lon)
        
        if result['confidence'] >= 0.99:
            result['reliability'] = 'TRÈS FIABLE - Données expert'
        elif result['confidence'] >= 0.8:
            result['reliability'] = 'Fiable - Modèle Tunisie'
        else:
            result['reliability'] = 'Moyennement fiable - Données GEBCO'
        
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
        (36.908, 10.288, "Marina Gammarth"),
        (36.84, 11.08, "Kélibia port"),
        (37.18, 10.20, "Ghar El Melh"),
        (37.25, 9.89, "Bizerte pêche"),
        (36.80, 10.17, "Tunis plaisance"),
        (36.41, 10.61, "Hammamet vieux port"),
        (35.81, 10.63, "Sousse pêche"),
        (35.77, 10.84, "Monastir pêche"),
        (35.49, 11.07, "Mahdia pêche"),
        (34.71, 10.76, "Sfax pêche"),
        (33.80, 10.86, "Djerba port"),
        (33.49, 11.13, "Zarzis port"),
        (36.95, 8.76, "Tabarka port"),
        (33.89, 10.11, "Gabès port"),
    ]
    
    print("\n" + "="*70)
    print("🏝️  TEST BATHYMÉTRIE TUNISIE - VERSION FINALE")
    print("="*70)
    
    for lat, lon, nom in spots:
        result = gebco.get_spot_info(lat, lon)
        print(f"\n📍 {nom}: ({lat}, {lon})")
        print(f"   Profondeur: {result['depth']}m")
        print(f"   Source: {result['source']}")
        print(f"   Confiance: {result['confidence']*100:.0f}%")
        print(f"   Fiabilité: {result['reliability']}")
        print(f"   Zone: {result['zone']}")

if __name__ == "__main__":
    test_spots()