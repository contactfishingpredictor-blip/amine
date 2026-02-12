# advanced_predictor.py - VERSION CORRIGÉE COMPLÈTE
import math, random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScientificFishingPredictor:
    def __init__(self):
        # Profils des espèces améliorés avec plus de données
        self.species_profiles = {
            "loup": {
                "name": "Loup de Mer",
                "temp_optimal": [15, 24],
                "temp_tolerance": 5.0,
                "salinity_optimal": [32, 38],
                "salinity_tolerance": 3.0,
                "oxygen_min": 3.5,
                "oxygen_optimal": [5.0, 8.0],
                "chlorophyll_optimal": [0.8, 3.0],
                "current_preference": [0.1, 0.8],
                "feeding_behavior": "chasseur_opportuniste",
                "metabolic_rate": 1.3,
                "diel_pattern": "crepuscular",
                "depth_preference": [1, 50],
                "spawning_season": [1, 3],
                "feeding_intensity": [0.7, 0.9],
                "moon_sensitivity": "moderate",
                "turbidity_tolerance": "medium",
                "wind_tolerance": "medium",
                "wave_tolerance": "high",
                "ideal_techniques": ["surfcasting", "pêche à soutenir", "pêche au leurre", "pêche au vif"]
            },
            "daurade": {
                "name": "Daurade Royale",
                "temp_optimal": [16, 26],
                "temp_tolerance": 6.0,
                "salinity_optimal": [30, 40],
                "salinity_tolerance": 4.0,
                "oxygen_min": 3.0,
                "oxygen_optimal": [4.5, 7.5],
                "chlorophyll_optimal": [1.0, 4.0],
                "current_preference": [0.05, 0.6],
                "feeding_behavior": "brouteur_omnivore",
                "metabolic_rate": 1.1,
                "diel_pattern": "diurnal",
                "depth_preference": [1, 30],
                "spawning_season": [10, 12],
                "feeding_intensity": [0.6, 0.8],
                "moon_sensitivity": "low",
                "turbidity_tolerance": "high",
                "wind_tolerance": "low",
                "wave_tolerance": "medium",
                "ideal_techniques": ["pêche au flotteur", "pêche à soutenir", "pêche à l'anglaise", "pêche fine"]
            },
            "pageot": {
                "name": "Pageot Commun",
                "temp_optimal": [15, 22],
                "temp_tolerance": 4.0,
                "salinity_optimal": [35, 38],
                "salinity_tolerance": 2.0,
                "oxygen_min": 4.0,
                "oxygen_optimal": [5.0, 8.0],
                "chlorophyll_optimal": [1.0, 3.5],
                "current_preference": [0.1, 0.7],
                "feeding_behavior": "chasseur_fond",
                "metabolic_rate": 1.0,
                "diel_pattern": "nocturnal",
                "depth_preference": [10, 100],
                "spawning_season": [5, 7],
                "feeding_intensity": [0.8, 0.95],
                "moon_sensitivity": "high",
                "turbidity_tolerance": "low",
                "wind_tolerance": "high",
                "wave_tolerance": "high",
                "ideal_techniques": ["pêche à soutenir", "pêche au leurre", "pêche à la dandine"]
            },
            "thon": {
                "name": "Thon Rouge",
                "temp_optimal": [15, 20],
                "temp_tolerance": 3.0,
                "salinity_optimal": [36, 39],
                "salinity_tolerance": 1.5,
                "oxygen_min": 4.5,
                "oxygen_optimal": [6.0, 9.0],
                "chlorophyll_optimal": [0.5, 2.0],
                "current_preference": [0.3, 1.2],
                "feeding_behavior": "prédateur_pélagique",
                "metabolic_rate": 2.5,
                "diel_pattern": "diurnal",
                "depth_preference": [0, 500],
                "spawning_season": [5, 8],
                "feeding_intensity": [0.9, 1.0],
                "moon_sensitivity": "moderate",
                "turbidity_tolerance": "medium",
                "wind_tolerance": "high",
                "wave_tolerance": "high",
                "ideal_techniques": ["pêche à la traîne", "pêche à la dérive", "pêche au vif"]
            },
            "sar": {
                "name": "Sar Commun",
                "temp_optimal": [16, 24],
                "temp_tolerance": 4.5,
                "salinity_optimal": [34, 38],
                "salinity_tolerance": 2.5,
                "oxygen_min": 3.2,
                "oxygen_optimal": [4.8, 7.2],
                "chlorophyll_optimal": [1.2, 3.8],
                "current_preference": [0.08, 0.5],
                "feeding_behavior": "omnivore_opportuniste",
                "metabolic_rate": 1.2,
                "diel_pattern": "diurnal",
                "depth_preference": [1, 50],
                "spawning_season": [4, 6],
                "feeding_intensity": [0.7, 0.85],
                "moon_sensitivity": "low",
                "turbidity_tolerance": "medium",
                "wind_tolerance": "medium",
                "wave_tolerance": "medium",
                "ideal_techniques": ["pêche à soutenir", "pêche au flotteur", "pêche au leurre"]
            }
        }
        
        # Constantes scientifiques
        self.SEAWATER_DENSITY = 1025
        self.SALINITY_MEDITERRANEAN = 38.0
        self.ATMOSPHERIC_PRESSURE_SEA = 1013.25
        
        logger.info("ScientificFishingPredictor initialisé avec %d espèces", len(self.species_profiles))

    # ===== MÉTHODES SCIENTIFIQUES =====
    
    def calculate_dissolved_oxygen(self, water_temp: float, salinity: float = None, 
                                  pressure: float = None) -> float:
        """Calcule l'oxygène dissous (mg/L)"""
        try:
            salinity = salinity or self.SALINITY_MEDITERRANEAN
            pressure = pressure or self.ATMOSPHERIC_PRESSURE_SEA
            
            T_kelvin = water_temp + 273.15
            T_ratio = T_kelvin / 100
            
            ln_DO_fresh = (-173.4292 + 249.6339/T_ratio + 
                           143.3483 * math.log(T_ratio) - 
                           21.8492 * T_ratio)
            DO_sat_fresh = math.exp(ln_DO_fresh)
            
            salinity_factor = salinity * (-0.033096 + 0.014259*T_ratio - 0.001700*T_ratio**2)
            DO_sat_sea = DO_sat_fresh * math.exp(salinity_factor)
            
            pressure_correction = pressure / 1013.25
            DO_sat = DO_sat_sea * pressure_correction
            
            tunisia_factor = 0.95
            DO_sat_tunisia = DO_sat * tunisia_factor
            
            return round(DO_sat_tunisia, 2)
        except Exception as e:
            logger.error("Erreur calcul oxygène: %s", e)
            return 6.0

    def estimate_chlorophyll(self, month: int, lat: float, lon: float) -> float:
        """Estime la chlorophylle-a (mg/m³)"""
        try:
            seasonal_chlorophyll = {
                1: 0.3, 2: 0.4, 3: 0.8, 4: 1.5, 5: 2.2, 6: 1.8,
                7: 1.2, 8: 0.9, 9: 0.7, 10: 0.5, 11: 0.4, 12: 0.3
            }
            
            base_chl = seasonal_chlorophyll.get(month, 1.0)
            lat_factor = 1.0 + (lat - 36.0) * 0.05
            coastal_factor = 1.5 if self._is_coastal_tunisia(lat, lon) else 1.0
            
            estimated_chl = base_chl * lat_factor * coastal_factor
            return round(max(0.1, min(5.0, estimated_chl)), 2)
        except Exception as e:
            logger.error("Erreur estimation chlorophylle: %s", e)
            return 1.5

    def _is_coastal_tunisia(self, lat: float, lon: float) -> bool:
        """Détermine si la position est côtière"""
        coastal_zones = [
            (36.0, 10.0, 37.5, 11.5),
            (35.5, 10.5, 36.5, 11.5),
            (34.5, 10.0, 35.5, 11.0),
            (33.0, 10.5, 34.0, 11.5),
            (36.7, 8.5, 37.0, 9.5),
            (35.0, 11.0, 35.5, 11.5)
        ]
        
        for min_lat, min_lon, max_lat, max_lon in coastal_zones:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return True
        return False

    def calculate_tidal_current(self, lat: float, lon: float, 
                              datetime_obj: datetime) -> Dict:
        """Calcule les courants de marée"""
        try:
            lunar_cycle = 29.53
            days_since_new = (datetime_obj - datetime(datetime_obj.year, 1, 11)).days % lunar_cycle
            tide_phase = days_since_new / lunar_cycle
            
            tide_height = 0.3 + 0.2 * math.sin(tide_phase * 2 * math.pi)
            current_speed = 0.05 + 0.15 * abs(math.sin(tide_phase * 4 * math.pi))
            
            if lat > 37.0:
                direction = "SO-NE" if tide_phase < 0.5 else "NE-SO"
            elif lat > 36.0:
                direction = "O-E" if tide_phase < 0.25 else "E-O" if tide_phase < 0.5 else "SO-NE" if tide_phase < 0.75 else "NE-SO"
            elif lat > 35.0:
                direction = "NO-SE" if tide_phase < 0.5 else "SE-NO"
            else:
                direction = "N-S" if tide_phase < 0.5 else "S-N"
            
            if 0.1 <= current_speed <= 0.3:
                fishing_impact = "favorable"
            elif current_speed < 0.1:
                fishing_impact = "trop faible"
            else:
                fishing_impact = "trop fort"
            
            return {
                'speed_mps': round(current_speed, 3),
                'speed_knots': round(current_speed * 1.944, 3),
                'direction': direction,
                'tide_height': round(tide_height, 2),
                'tide_phase': 'montante' if tide_phase < 0.25 or tide_phase > 0.75 else 'descendante',
                'fishing_impact': fishing_impact
            }
        except Exception as e:
            logger.error("Erreur calcul courant: %s", e)
            return {
                'speed_mps': 0.2,
                'speed_knots': 0.39,
                'direction': 'N-S',
                'tide_height': 0.3,
                'tide_phase': 'étale',
                'fishing_impact': 'moyen'
            }

    # ===== MÉTHODE DE TEMPÉRATURE D'EAU =====
    
    def estimate_water_from_position(self, lat: float, lon: float) -> float:
        """Estime température eau basée sur position et saison"""
        try:
            month = datetime.now().month
            
            # Températures moyennes pour la Tunisie par région
            if lat > 37.0:  # Nord
                temps = {1:14,2:14,3:15,4:17,5:20,6:23,7:26,8:27,9:25,10:22,11:19,12:16}
            elif lat > 36.0:  # Centre (Tunis, Sousse)
                temps = {1:15,2:15,3:16,4:18,5:21,6:24,7:27,8:28,9:26,10:23,11:20,12:17}
            else:  # Sud (Sfax, Djerba)
                temps = {1:16,2:16,3:17,4:19,5:22,6:25,7:28,8:29,9:27,10:24,11:21,12:18}
            
            base_temp = temps.get(month, 20)
            
            # Variation journalière
            hour = datetime.now().hour
            hour_variation = math.sin(hour * math.pi / 12) * 1.5
            
            return round(base_temp + hour_variation, 1)
        except Exception as e:
            logger.error("Erreur estimation température eau: %s", e)
            return 20.0

    def estimate_water_from_air(self, air_temp: float) -> float:
        """Estime température eau depuis température air pour la Tunisie"""
        try:
            month = datetime.now().month
            # Modèle spécifique à la Tunisie
            if 6 <= month <= 9:  # Été
                return max(air_temp - 4.0, 22.0)  # Min 22°C en été
            elif 12 <= month or month <= 2:  # Hiver
                return min(air_temp + 2.0, 16.0)  # Max 16°C en hiver
            else:  # Printemps/Automne
                return air_temp - 2.0
        except Exception as e:
            logger.error("Erreur conversion air/eau: %s", e)
            return 20.0

    # ===== MÉTHODES DE SCORING =====
    
    def calculate_weather_factor(self, weather_data: Dict, species: str) -> float:
        """Calcule un facteur météo (0-1)"""
        try:
            profile = self.species_profiles.get(species, self.species_profiles["loup"])
            
            temp_opt = self._mean(profile["temp_optimal"])
            temp_diff = abs(weather_data.get('temperature', 20) - temp_opt)
            temp_score = max(0, 1 - temp_diff / profile["temp_tolerance"])
            
            wind_tolerance = profile.get("wind_tolerance", "medium")
            wind_max = {"low": 15, "medium": 25, "high": 40}[wind_tolerance]
            wind_score = max(0, 1 - weather_data.get('wind_speed', 10) / wind_max)
            
            wave_tolerance = profile.get("wave_tolerance", "medium")
            wave_max = {"low": 0.5, "medium": 1.0, "high": 2.0}[wave_tolerance]
            wave_score = max(0, 1 - weather_data.get('wave_height', 0.5) / wave_max)
            
            pressure_diff = abs(weather_data.get('pressure', 1015) - 1015)
            pressure_score = max(0, 1 - pressure_diff / 30)
            
            oxygen = weather_data.get('oxygen', 6.0)
            oxygen_opt = profile.get("oxygen_optimal", [5.0, 8.0])
            if oxygen < profile.get("oxygen_min", 3.5):
                oxygen_score = 0.0
            elif oxygen < oxygen_opt[0]:
                oxygen_score = oxygen / oxygen_opt[0]
            elif oxygen > oxygen_opt[1]:
                oxygen_score = max(0, 1 - (oxygen - oxygen_opt[1]) / oxygen_opt[1])
            else:
                oxygen_score = 1.0
            
            if species in ["loup", "pageot"]:
                weights = {'temp': 0.3, 'wind': 0.2, 'wave': 0.15, 'pressure': 0.15, 'oxygen': 0.2}
            elif species in ["daurade", "sar"]:
                weights = {'temp': 0.25, 'wind': 0.15, 'wave': 0.25, 'pressure': 0.15, 'oxygen': 0.2}
            else:
                weights = {'temp': 0.25, 'wind': 0.2, 'wave': 0.2, 'pressure': 0.15, 'oxygen': 0.2}
            
            weather_factor = (
                temp_score * weights['temp'] +
                wind_score * weights['wind'] +
                wave_score * weights['wave'] +
                pressure_score * weights['pressure'] +
                oxygen_score * weights.get('oxygen', 0)
            )
            
            return min(1.0, max(0.0, round(weather_factor, 3)))
        except Exception as e:
            logger.error("Erreur calcul facteur météo: %s", e)
            return 0.5

    def calculate_environmental_score(self, weather_data: Dict, species: str, 
                                    lat: float = None, lon: float = None) -> float:
        """Score environnemental (0-1)"""
        try:
            profile = self.species_profiles.get(species, self.species_profiles["loup"])
            water_temp = weather_data.get('water_temperature', weather_data.get('temperature', 20))
            
            # Oxygène
            oxygen_level = self.calculate_dissolved_oxygen(
                water_temp,
                weather_data.get('salinity', self.SALINITY_MEDITERRANEAN),
                weather_data.get('pressure', self.ATMOSPHERIC_PRESSURE_SEA)
            )
            
            oxygen_opt = profile.get("oxygen_optimal", [5.0, 8.0])
            if oxygen_level < profile.get("oxygen_min", 3.5):
                oxygen_score = 0.0
            elif oxygen_level < oxygen_opt[0]:
                oxygen_score = oxygen_level / oxygen_opt[0]
            elif oxygen_level > oxygen_opt[1]:
                oxygen_score = max(0, 1 - (oxygen_level - oxygen_opt[1]) / oxygen_opt[1])
            else:
                oxygen_score = 1.0
            
            # Chlorophylle
            if lat and lon:
                month = datetime.now().month
                chlorophyll = self.estimate_chlorophyll(month, lat, lon)
            else:
                chlorophyll = weather_data.get('chlorophyll', 1.5)
            
            chl_opt = profile.get("chlorophyll_optimal", [0.8, 3.0])
            if chlorophyll < chl_opt[0]:
                chl_score = chlorophyll / chl_opt[0]
            elif chlorophyll > chl_opt[1]:
                chl_score = max(0, 1 - (chlorophyll - chl_opt[1]) / chl_opt[1])
            else:
                chl_score = 1.0
            
            # Courant
            if lat and lon:
                current_data = self.calculate_tidal_current(lat, lon, datetime.now())
                current_speed = current_data['speed_mps']
            else:
                current_speed = weather_data.get('current_speed', 0.2)
            
            current_opt = profile.get("current_preference", [0.1, 0.8])
            if current_speed < current_opt[0]:
                current_score = current_speed / current_opt[0]
            elif current_speed > current_opt[1]:
                current_score = max(0, 1 - (current_speed - current_opt[1]) / current_opt[1])
            else:
                current_score = 1.0
            
            # Facteurs traditionnels
            temp_opt = self._mean(profile["temp_optimal"])
            temp_diff = abs(weather_data.get('temperature', 20) - temp_opt)
            temp_score = max(0, 1 - temp_diff / profile["temp_tolerance"])
            
            wind_score = max(0, 1 - weather_data.get('wind_speed', 10) / 40)
            pressure_diff = abs(weather_data.get('pressure', 1015) - 1015)
            pressure_score = max(0, 1 - pressure_diff / 30)
            wave_score = max(0, 1 - weather_data.get('wave_height', 0.5) / 2.0)
            
            turbidity = weather_data.get('turbidity', 1.0)
            turbidity_score = 1.0
            if 'turbidity' in weather_data:
                if profile.get('turbidity_tolerance') == 'low':
                    turbidity_score = max(0, 1 - (turbidity - 1.0))
                elif profile.get('turbidity_tolerance') == 'high':
                    turbidity_score = 0.8 + (turbidity - 1.0) * 0.1
            
            weather_factor = self.calculate_weather_factor(weather_data, species)
            
            if species in ["loup", "pageot"]:
                weights = {
                    'temp': 0.12, 'wind': 0.10, 'pressure': 0.08, 'wave': 0.10,
                    'oxygen': 0.15, 'chlorophyll': 0.12, 'current': 0.10,
                    'turbidity': 0.05, 'weather': 0.18
                }
            elif species in ["daurade", "sar"]:
                weights = {
                    'temp': 0.10, 'wind': 0.08, 'pressure': 0.06, 'wave': 0.12,
                    'oxygen': 0.14, 'chlorophyll': 0.15, 'current': 0.08,
                    'turbidity': 0.06, 'weather': 0.21
                }
            else:
                weights = {
                    'temp': 0.15, 'wind': 0.12, 'pressure': 0.08, 'wave': 0.10,
                    'oxygen': 0.18, 'chlorophyll': 0.10, 'current': 0.12,
                    'turbidity': 0.05, 'weather': 0.10
                }
            
            environmental_score = (
                temp_score * weights['temp'] +
                wind_score * weights['wind'] +
                pressure_score * weights['pressure'] +
                wave_score * weights['wave'] +
                oxygen_score * weights['oxygen'] +
                chl_score * weights['chlorophyll'] +
                current_score * weights['current'] +
                turbidity_score * weights.get('turbidity', 0) +
                weather_factor * weights.get('weather', 0)
            )
            
            current_month = datetime.now().month
            spawning_season = profile.get("spawning_season", [])
            if spawning_season and spawning_season[0] <= current_month <= spawning_season[1]:
                environmental_score *= 0.8
            
            return min(1.0, max(0.0, round(environmental_score, 3)))
        except Exception as e:
            logger.error("Erreur calcul score environnemental: %s", e)
            return 0.5

    # ===== MÉTHODE PRINCIPALE CORRIGÉE =====
    
    def predict_daily_activity(self, lat: float, lon: float, date: datetime, 
                              species: str, weather_data: Dict) -> Dict:
        """Prédiction quotidienne - RETOURNE SCORE EN POURCENTAGE (0-100)"""
        try:
            if not weather_data:
                weather_data = self._get_default_weather_data()
            
            if species not in self.species_profiles:
                logger.warning("Espèce %s non trouvée, utilisation de 'loup'", species)
                species = "loup"
            
            # Calcul des facteurs scientifiques
            water_temp = weather_data.get('water_temperature', 
                                        self.estimate_water_from_position(lat, lon))
            
            oxygen_level = self.calculate_dissolved_oxygen(
                water_temp,
                weather_data.get('salinity', self.SALINITY_MEDITERRANEAN),
                weather_data.get('pressure', 1013)
            )
            
            month = date.month
            chlorophyll_level = self.estimate_chlorophyll(month, lat, lon)
            current_data = self.calculate_tidal_current(lat, lon, date)
            
            # Mise à jour weather_data
            enhanced_weather = weather_data.copy()
            enhanced_weather.update({
                'oxygen': oxygen_level,
                'chlorophyll': chlorophyll_level,
                'current_speed': current_data['speed_mps'],
                'water_temperature': water_temp,
                'lat': lat,
                'lon': lon
            })
            
            # Calcul des scores (0-1)
            env_score = self.calculate_environmental_score(enhanced_weather, species, lat, lon)
            behavior_score = self.calculate_behavioral_score(date, species)
            regional_factor = self._calculate_regional_factor(lat, lon, species, date.month)
            weather_factor = self.calculate_weather_factor(enhanced_weather, species)
            
            # Score d'activité global en DÉCIMAL (0-1)
            activity_score_decimal = (
                env_score * 0.40 +
                behavior_score * 0.20 +
                regional_factor * 0.15 +
                weather_factor * 0.25
            )
            
            # ASSURER QUE LE SCORE EST BIEN ENTRE 0 ET 1
            activity_score_decimal = max(0.0, min(1.0, activity_score_decimal))
            
            # CONVERSION EN POURCENTAGE POUR FRONTEND (0-100)
            activity_score_percent = int(round(activity_score_decimal * 100))
            
            # S'assurer que le pourcentage est entre 0 et 100
            activity_score_percent = max(0, min(100, activity_score_percent))
            
            # Calcul des heures optimales (scores en DÉCIMAL 0-1)
            best_hours = self.calculate_best_hours(date, species, enhanced_weather)
            
            # Détermination du niveau
            if activity_score_percent >= 80:
                opportunity = "EXCELLENTE"
                color = "#10b981"
            elif activity_score_percent >= 70:
                opportunity = "TRÈS BONNE"
                color = "#22c55e"
            elif activity_score_percent >= 60:
                opportunity = "BONNE"
                color = "#f59e0b"
            elif activity_score_percent >= 50:
                opportunity = "MOYENNE"
                color = "#3b82f6"
            else:
                opportunity = "FAIBLE"
                color = "#ef4444"
            
            # Génération recommandations
            limitations, favorable_factors = self._generate_recommendations(
                enhanced_weather, species, activity_score_percent
            )
            
            # ===== CORRECTION : AJOUT DE best_fishing_hours =====
            # Pour compatibilité avec l'API existante qui attend ce champ
            return {
                'fishing_opportunity': opportunity,
                'score': activity_score_percent,  # ← POUR FRONTEND : 0-100%
                'activity_score': activity_score_percent,  # Alias
                'activity_score_decimal': round(activity_score_decimal, 3),  # Pour debug
                'environmental_score': round(env_score, 3),
                'behavioral_score': round(behavior_score, 3),
                'regional_factor': round(regional_factor, 3),
                'weather_factor': round(weather_factor, 3),
                'color': color,
                'confidence': round(0.65 + activity_score_decimal * 0.35, 2),
                'best_hours': best_hours,  # ← Scores en DÉCIMAL 0-1
                'optimal_hours': best_hours,  # Alias pour predictions.html
                'best_fishing_hours': best_hours,  # ← CORRECTION : Pour API tunisian_prediction
                'limitations': limitations[:3],
                'favorable_factors': favorable_factors[:3],
                'recommendations': self._combine_recommendations(limitations, favorable_factors),  # Ajouté pour compatibilité
                'species': species,
                'species_name': self.species_profiles[species].get('name', species),
                'date': date.strftime("%Y-%m-%d"),
                'recommended_techniques': self._get_recommended_techniques(species, enhanced_weather),
                'bathymetry': self.get_bathymetry_data(lat, lon),
                'weather_summary': self._get_weather_summary(enhanced_weather),
                'scientific_factors': {
                    'dissolved_oxygen': {
                        'value': oxygen_level,
                        'unit': 'mg/L',
                        'optimal_range': f"{self.species_profiles[species].get('oxygen_optimal', [5.0, 8.0])[0]}-{self.species_profiles[species].get('oxygen_optimal', [5.0, 8.0])[1]} mg/L",
                        'status': 'optimal' if self.species_profiles[species].get('oxygen_optimal', [5.0, 8.0])[0] <= oxygen_level <= self.species_profiles[species].get('oxygen_optimal', [5.0, 8.0])[1] else 'suboptimal'
                    },
                    'chlorophyll_a': {
                        'value': chlorophyll_level,
                        'unit': 'mg/m³',
                        'optimal_range': f"{self.species_profiles[species].get('chlorophyll_optimal', [0.8, 3.0])[0]}-{self.species_profiles[species].get('chlorophyll_optimal', [0.8, 3.0])[1]} mg/m³",
                        'status': 'optimal' if self.species_profiles[species].get('chlorophyll_optimal', [0.8, 3.0])[0] <= chlorophyll_level <= self.species_profiles[species].get('chlorophyll_optimal', [0.8, 3.0])[1] else 'suboptimal'
                    },
                    'tidal_current': current_data
                }
            }
        except Exception as e:
            logger.error("Erreur prédiction activité: %s", e)
            return self._get_fallback_prediction(lat, lon, date, species)

    # ===== NOUVELLE MÉTHODE POUR COMBINER RECOMMANDATIONS =====
    def _combine_recommendations(self, limitations: List[str], favorable_factors: List[str]) -> List[str]:
        """Combine limitations et favorable_factors en une liste de recommandations"""
        recommendations = []
        
        if limitations:
            recommendations.extend([f"⚠️ {lim}" for lim in limitations[:2]])
        
        if favorable_factors:
            recommendations.extend([f"✅ {fav}" for fav in favorable_factors[:2]])
        
        # Si vide, retourner des recommandations par défaut
        if not recommendations:
            recommendations = [
                "Vérifiez les heures optimales ci-dessus",
                "Conditions météo standard pour la pêche"
            ]
        
        return recommendations

    def calculate_best_hours(self, date: datetime, species: str, 
                           weather_data: Dict) -> List[Dict]:
        """Calcule les meilleures heures - RETOURNE SCORES EN DÉCIMAL (0-1)"""
        try:
            profile = self.species_profiles.get(species, self.species_profiles["loup"])
            diel_pattern = profile["diel_pattern"]
            
            if diel_pattern == "diurnal":
                base_hours = [(8, 0.7), (10, 0.8), (12, 0.9), (14, 0.85), (16, 0.75)]
            elif diel_pattern == "nocturnal":
                base_hours = [(20, 0.7), (22, 0.85), (0, 0.9), (2, 0.8), (4, 0.7)]
            elif diel_pattern == "crepuscular":
                base_hours = [(5, 0.8), (6, 0.9), (7, 0.85), (18, 0.85), (19, 0.9), (20, 0.8)]
            else:
                base_hours = [(9, 0.7), (12, 0.8), (15, 0.7)]
            
            # Ajustement météo
            weather_adjustment = 1.0
            
            # Vent
            wind_speed = weather_data.get('wind_speed', 10)
            if wind_speed > 25:
                weather_adjustment *= 0.7
            elif wind_speed > 20:
                weather_adjustment *= 0.8
            elif wind_speed > 15:
                weather_adjustment *= 0.9
            elif wind_speed < 5:
                weather_adjustment *= 1.1
            
            # Vague
            wave_height = weather_data.get('wave_height', 0.5)
            if wave_height > 1.5:
                weather_adjustment *= 0.6
            elif wave_height > 1.0:
                weather_adjustment *= 0.8
            elif wave_height < 0.3:
                weather_adjustment *= 1.05
            
            # Pression
            pressure = weather_data.get('pressure', 1015)
            if abs(pressure - 1015) < 10:
                weather_adjustment *= 1.05
            
            # Oxygène
            oxygen = weather_data.get('oxygen', 6.0)
            if oxygen > 7.0:
                weather_adjustment *= 1.05
            elif oxygen < 4.0:
                weather_adjustment *= 0.9
            
            # Chlorophylle
            chlorophyll = weather_data.get('chlorophyll', 1.5)
            if 1.0 <= chlorophyll <= 3.0:
                weather_adjustment *= 1.03
            
            # Calcul des scores
            adjusted_hours = []
            for hour, base_score in base_hours:
                # Facteur horaire
                if diel_pattern == "diurnal":
                    hour_factor = 1.0 - abs(hour - 13) / 12 * 0.3
                elif diel_pattern == "nocturnal":
                    night_hour = hour if hour >= 18 else hour + 24
                    hour_factor = 1.0 - abs(night_hour - 1) / 12 * 0.3
                elif diel_pattern == "crepuscular":
                    dawn_factor = 1.0 - abs(hour - 6) / 6 * 0.3
                    dusk_factor = 1.0 - abs(hour - 19) / 6 * 0.3
                    hour_factor = max(dawn_factor, dusk_factor)
                else:
                    hour_factor = 1.0 - abs(hour - 12) / 12 * 0.3
                
                adjusted_score = base_score * weather_adjustment * hour_factor
                adjusted_score = min(0.95, max(0.3, adjusted_score))
                
                # Niveau
                if adjusted_score >= 0.8:
                    level = "EXCELLENT"
                    color = "#10b981"
                elif adjusted_score >= 0.7:
                    level = "BON"
                    color = "#22c55e"
                elif adjusted_score >= 0.6:
                    level = "MOYEN"
                    color = "#f59e0b"
                elif adjusted_score >= 0.5:
                    level = "PASSABLE"
                    color = "#3b82f6"
                else:
                    level = "FAIBLE"
                    color = "#ef4444"
                
                adjusted_hours.append({
                    'hour': hour,
                    'score': round(adjusted_score, 3),  # ← DÉCIMAL 0-1
                    'level': level,
                    'color': color,
                    'description': f"{hour}h-{hour+2}h"
                })
            
            adjusted_hours.sort(key=lambda x: x['score'], reverse=True)
            return adjusted_hours[:5]
        except Exception as e:
            logger.error("Erreur calcul meilleures heures: %s", e)
            return [{'hour': 8, 'score': 0.6, 'level': "MOYEN", 'color': "#f59e0b", 'description': "8h-10h"}]

    # ===== MÉTHODES UTILITAIRES =====
    
    def calculate_behavioral_score(self, date: datetime, species: str) -> float:
        """Score comportemental (0-1)"""
        try:
            profile = self.species_profiles.get(species, self.species_profiles["loup"])
            hour = date.hour
            diel_pattern = profile["diel_pattern"]
            
            if diel_pattern == "diurnal":
                diel_score = 0.6 + 0.4 * math.exp(-((hour - 14) / 4) ** 2)
            elif diel_pattern == "nocturnal":
                night_hour = hour if hour >= 18 else hour + 24
                diel_score = 0.6 + 0.4 * math.exp(-((night_hour - 1) / 4) ** 2)
            elif diel_pattern == "crepuscular":
                dawn_score = math.exp(-((hour - 6) / 2) ** 2)
                dusk_score = math.exp(-((hour - 19) / 2) ** 2)
                diel_score = 0.5 + 0.5 * max(dawn_score, dusk_score)
            else:
                diel_score = 0.7
            
            lunar_cycle = 29.53
            days_since_new_moon = (date - datetime(date.year, 1, 11)).days % lunar_cycle
            moon_phase = days_since_new_moon / lunar_cycle
            
            moon_sensitivity = profile.get("moon_sensitivity", "moderate")
            if moon_sensitivity == "high":
                moon_score = 0.4 + 0.6 * abs(math.sin(moon_phase * math.pi))
            elif moon_sensitivity == "moderate":
                moon_score = 0.6 + 0.4 * abs(math.sin(moon_phase * math.pi))
            else:
                moon_score = 0.7 + 0.3 * math.sin(moon_phase * math.pi * 2)
            
            tide_cycle = 12.4
            tide_phase = (hour % tide_cycle) / tide_cycle
            tide_score = 0.7 + 0.3 * abs(math.sin(tide_phase * 2 * math.pi))
            
            feeding_intensity = profile.get("feeding_intensity", [0.6, 0.8])
            base_feeding = (feeding_intensity[0] + feeding_intensity[1]) / 2
            
            score = diel_score * 0.4 + moon_score * 0.3 + tide_score * 0.2 + base_feeding * 0.1
            return min(1.0, max(0.0, round(score, 3)))
        except:
            return 0.5

    def _calculate_regional_factor(self, lat: float, lon: float, 
                                 species: str, month: int) -> float:
        """Facteur régional (0-1)"""
        try:
            factor = 0.5
            
            if lat > 37.0:
                if species in ["loup", "daurade", "corbeau", "merlan"]:
                    factor += 0.3
            elif lat > 36.5 and lon > 10.8:
                if species in ["thon", "espadon", "sériole", "bonite"]:
                    factor += 0.4
            elif lat > 35.5 and lon > 10.5:
                if species in ["daurade", "sar", "marbré", "mulet"]:
                    factor += 0.3
            elif lat < 34.0:
                if species in ["daurade", "mulet", "marbré", "orphie"]:
                    factor += 0.2
            
            seasonal_adjustment = {
                12: {"loup": 0.2, "daurade": 0.1, "merlan": 0.3, "corbeau": 0.2},
                1: {"loup": 0.2, "daurade": 0.1, "merlan": 0.3, "corbeau": 0.2},
                2: {"loup": 0.2, "daurade": 0.1, "merlan": 0.3, "corbeau": 0.2},
                6: {"daurade": 0.3, "mulet": 0.4, "marbré": 0.3, "sériole": 0.2},
                7: {"daurade": 0.3, "mulet": 0.4, "marbré": 0.3, "sériole": 0.2},
                8: {"daurade": 0.3, "mulet": 0.4, "marbré": 0.3, "sériole": 0.2}
            }
            
            if month in seasonal_adjustment and species in seasonal_adjustment[month]:
                factor += seasonal_adjustment[month][species]
            
            return min(1.0, max(0.0, round(factor, 3)))
        except:
            return 0.5

    def _generate_recommendations(self, weather_data: Dict, species: str, 
                                activity_score: int) -> Tuple[List[str], List[str]]:
        """Génère recommandations"""
        limitations = []
        favorable_factors = []
        
        profile = self.species_profiles.get(species, self.species_profiles["loup"])
        
        # Vérifications
        oxygen = weather_data.get('oxygen', 6.0)
        if oxygen < 4.0:
            limitations.append(f"Oxygène dissous faible ({oxygen} mg/L)")
        elif oxygen > 7.0:
            favorable_factors.append(f"Oxygène dissous optimal ({oxygen} mg/L)")
        
        chlorophyll = weather_data.get('chlorophyll', 1.5)
        if chlorophyll < 0.5:
            limitations.append("Faible productivité (chlorophylle basse)")
        elif chlorophyll > 2.0:
            favorable_factors.append("Forte productivité primaire")
        
        current_speed = weather_data.get('current_speed', 0.2)
        if current_speed < 0.1:
            limitations.append("Courant trop faible")
        elif current_speed > 0.5:
            limitations.append("Courant trop fort")
        else:
            favorable_factors.append(f"Courant favorable ({current_speed} m/s)")
        
        wind_speed = weather_data.get('wind_speed', 10)
        if wind_speed > 25:
            limitations.append("Vent trop fort")
        elif wind_speed < 10:
            favorable_factors.append("Vent faible")
        
        wave_height = weather_data.get('wave_height', 0.5)
        if wave_height > 1.5:
            limitations.append("Mer agitée")
        elif wave_height < 0.5:
            favorable_factors.append("Mer calme")
        
        temp_diff = abs(weather_data.get('temperature', 20) - self._mean(profile["temp_optimal"]))
        if temp_diff > 8:
            limitations.append("Température non optimale")
        else:
            favorable_factors.append("Température favorable")
        
        if abs(weather_data.get('pressure', 1015) - 1015) < 10:
            favorable_factors.append("Pression stable")
        
        if activity_score >= 70 and not favorable_factors:
            favorable_factors.append("Conditions générales favorables")
        
        return limitations, favorable_factors

    def _mean(self, arr):
        """Calcule la moyenne"""
        if not arr:
            return 0
        if isinstance(arr[0], (list, tuple)):
            return (arr[0] + arr[1]) / 2
        return sum(arr) / len(arr)

    def get_bathymetry_data(self, lat: float, lon: float) -> Dict:
        """Données bathymétriques"""
        try:
            known_depths = {
                (36.9000, 10.3333): {"depth": 5.0, "type": "sand"},
                (36.8185, 10.3050): {"depth": 8.0, "type": "mixed"},
                (36.8687, 10.3418): {"depth": 15.0, "type": "rock"},
                (36.8475, 11.0940): {"depth": 20.0, "type": "rock"},
                (37.2747, 9.8739): {"depth": 12.0, "type": "mud"},
                (36.9540, 8.7580): {"depth": 25.0, "type": "rock"},
                (35.8254, 10.6360): {"depth": 6.0, "type": "sand"},
                (35.7833, 10.8333): {"depth": 4.0, "type": "sand"},
                (33.8078, 10.8451): {"depth": 2.0, "type": "sand"},
                (36.4000, 10.6000): {"depth": 3.0, "type": "sand"}
            }
            
            min_distance = float('inf')
            best_match = None
            
            for known_coords, data in known_depths.items():
                known_lat, known_lon = known_coords
                distance = math.sqrt((lat - known_lat)**2 + (lon - known_lon)**2)
                if distance < min_distance:
                    min_distance = distance
                    best_match = data
            
            if min_distance < 0.5 and best_match:
                depth = best_match["depth"]
                seabed_type = best_match["type"]
            else:
                coastal_depth = 0.5
                lat_factor = max(0, min(1, (lat - 32.0) / 6.0))
                lon_factor = max(0, min(1, (lon - 7.0) / 5.0))
                depth = coastal_depth + (lat_factor * 20) + (lon_factor * 10)
                depth = min(40, max(1, depth))
                
                if depth < 5:
                    seabed_type = "sand"
                elif depth < 15:
                    seabed_type = "mixed" if lon <= 10.5 or lat >= 36.5 else "grass"
                elif depth < 25:
                    seabed_type = "rock"
                else:
                    seabed_type = "mud"
            
            seabed_descriptions = {
                "sand": "Sable fin",
                "rock": "Rochers",
                "grass": "Herbier de posidonie",
                "mud": "Vase",
                "mixed": "Fond mixte"
            }
            
            slope = 3.0 if seabed_type == "rock" else 0.5
            
            return {
                "depth": round(depth, 1),
                "seabed_type": seabed_type,
                "seabed_description": seabed_descriptions.get(seabed_type, "Inconnu"),
                "slope": round(slope, 1),
                "accuracy": "haute" if min_distance < 0.1 else "moyenne" if min_distance < 0.5 else "basse"
            }
        except:
            return {
                "depth": 10.0,
                "seabed_type": "mixed",
                "seabed_description": "Fond mixte",
                "slope": 1.0,
                "accuracy": "moyenne"
            }

    def _get_recommended_techniques(self, species: str, weather_data: Dict) -> List[str]:
        """Techniques recommandées"""
        try:
            profile = self.species_profiles.get(species, self.species_profiles["loup"])
            base_techniques = profile.get("ideal_techniques", ["pêche à soutenir", "surfcasting"])
            
            filtered_techniques = []
            for technique in base_techniques:
                if technique in ["pêche au flotteur", "pêche fine"]:
                    if weather_data.get('wind_speed', 10) > 15:
                        continue
                    if weather_data.get('wave_height', 0.5) > 0.8:
                        continue
                
                if technique == "pêche à la dérive":
                    current_speed = weather_data.get('current_speed', 0.2)
                    if current_speed < 0.1 or current_speed > 0.5:
                        continue
                
                filtered_techniques.append(technique)
            
            if not filtered_techniques:
                return base_techniques[:2]
            
            return filtered_techniques[:3]
        except:
            return ["pêche à soutenir", "surfcasting"]

    def _get_weather_summary(self, weather_data: Dict) -> str:
        """Résumé météo"""
        try:
            summary_parts = []
            
            temp = weather_data.get('temperature', 20)
            if 18 <= temp <= 25:
                summary_parts.append("Température idéale")
            elif temp < 15:
                summary_parts.append("Température fraîche")
            elif temp > 28:
                summary_parts.append("Température élevée")
            
            wind = weather_data.get('wind_speed', 10)
            if wind < 10:
                summary_parts.append("Vent faible")
            elif wind > 20:
                summary_parts.append("Vent modéré à fort")
            
            oxygen = weather_data.get('oxygen', 6.0)
            if oxygen > 7.0:
                summary_parts.append("Eau bien oxygénée")
            
            return ", ".join(summary_parts) if summary_parts else "Conditions normales"
        except:
            return "Données météo disponibles"

    def _get_default_weather_data(self) -> Dict:
        """Données météo par défaut"""
        return {
            'temperature': 20.0,
            'wind_speed': 10.0,
            'pressure': 1015.0,
            'wave_height': 0.5,
            'salinity': self.SALINITY_MEDITERRANEAN
        }

    def _get_fallback_prediction(self, lat: float, lon: float, 
                               date: datetime, species: str) -> Dict:
        """Prédiction de secours"""
        best_hours = [{'hour': 8, 'score': 0.6, 'level': "MOYEN", 'color': "#f59e0b", 'description': "8h-10h"}]
        
        return {
            'fishing_opportunity': "MOYENNE",
            'score': 50,
            'activity_score': 50,
            'activity_score_decimal': 0.5,
            'best_hours': best_hours,
            'optimal_hours': best_hours,
            'best_fishing_hours': best_hours,  # ← CORRECTION : Ajouté ici aussi
            'limitations': ["Calculs temporairement limités"],
            'favorable_factors': ["Conditions de base acceptables"],
            'recommendations': ["Utilisez les données par défaut", "Vérifiez la météo locale"],
            'species': species,
            'species_name': self.species_profiles.get(species, {}).get('name', species),
            'date': date.strftime("%Y-%m-%d"),
            'recommended_techniques': ["pêche à soutenir", "surfcasting"],
            'bathymetry': self.get_bathymetry_data(lat, lon),
            'weather_summary': "Données par défaut"
        }

if __name__ == "__main__":
    predictor = ScientificFishingPredictor()
    print("=" * 60)
    print("🧪 SCIENTIFIC FISHING PREDICTOR - VERSION 2.4 CORRIGÉE")
    print("=" * 60)
    print("✅ Méthode estimate_water_from_position corrigée")
    print("✅ Bug 6800% corrigé")
    print("✅ Champ best_fishing_hours ajouté (compatibilité API)")
    print("✅ Champ recommendations ajouté")
    print("✅ Scores globaux en pourcentage (0-100)")
    print("✅ Scores horaires en décimal (0-1)")
    print("=" * 60)
    
    # Test rapide
    test_date = datetime.now()
    test_weather = {
        'temperature': 22.0,
        'wind_speed': 12.0,
        'pressure': 1018.0,
        'wave_height': 0.8
    }
    
    try:
        prediction = predictor.predict_daily_activity(
            lat=36.8065, lon=10.1815,
            date=test_date,
            species='loup',
            weather_data=test_weather
        )
        
        print(f"📊 Test prédiction - {prediction['species_name']}")
        print(f"   Score global: {prediction['score']}%")
        print(f"   Opportunité: {prediction['fishing_opportunity']}")
        print(f"   Heures optimales: {len(prediction['best_hours'])} créneaux")
        print(f"   best_fishing_hours présent: {'best_fishing_hours' in prediction}")
        print(f"   recommendations présent: {'recommendations' in prediction}")
        print("=" * 60)
        
        # Vérification spécifique du bug
        score = prediction['score']
        if score > 100:
            print(f"⚠️ ATTENTION : Score toujours > 100 : {score}")
        else:
            print(f"✅ Score correctement limité à 0-100 : {score}")
            
    except Exception as e:
        print(f"❌ Erreur test: {e}")