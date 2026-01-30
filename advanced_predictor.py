import math, random
from datetime import datetime, timedelta

class ScientificFishingPredictor:
    def __init__(self):
        # Profils des espèces améliorés avec plus de données
        self.species_profiles = {
            "loup": {
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
                "wave_tolerance": "high"
            },
            "daurade": {
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
                "wave_tolerance": "medium"
            },
            "pageot": {
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
                "wave_tolerance": "high"
            },
            "thon": {
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
                "wave_tolerance": "high"
            },
            "sar": {
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
                "wave_tolerance": "medium"
            }
        }
        
        # Constantes scientifiques pour les nouveaux facteurs
        self.SEAWATER_DENSITY = 1025  # kg/m³ (Méditerranée)
        self.SALINITY_MEDITERRANEAN = 38.0  # g/L
        self.ATMOSPHERIC_PRESSURE_SEA = 1013.25  # hPa
        
        print("✅ Prédicteur scientifique initialisé - 3 nouveaux facteurs scientifiques")

    # ===== NOUVELLES MÉTHODES SCIENTIFIQUES =====
    
    def calculate_dissolved_oxygen(self, water_temp: float, salinity: float = 38.0, 
                                  pressure: float = 1013.25) -> float:
        """Calcule l'oxygène dissous (mg/L) selon formule scientifique"""
        # Formule de Weiss (1970) pour l'eau de mer
        T_kelvin = water_temp + 273.15
        T_ratio = T_kelvin / 100
        
        # Calcul saturation pour eau douce
        ln_DO_fresh = (-173.4292 + 249.6339/T_ratio + 
                       143.3483 * math.log(T_ratio) - 
                       21.8492 * T_ratio)
        DO_sat_fresh = math.exp(ln_DO_fresh)
        
        # Correction pour salinité
        salinity_factor = salinity * (-0.033096 + 0.014259*T_ratio - 0.001700*T_ratio**2)
        
        # Saturation à pression atmosphérique standard
        DO_sat_sea = DO_sat_fresh * math.exp(salinity_factor)
        
        # Correction pour pression (loi de Henry)
        pressure_correction = pressure / 1013.25
        DO_sat = DO_sat_sea * pressure_correction
        
        # Ajustement pour eaux tunisiennes (légèrement plus faible)
        tunisia_factor = 0.95  # Les eaux tunisiennes sont légèrement moins oxygénées
        DO_sat_tunisia = DO_sat * tunisia_factor
        
        return round(DO_sat_tunisia, 2)

    def estimate_chlorophyll(self, month: int, lat: float, lon: float) -> float:
        """Estime la chlorophylle-a (mg/m³) basée sur saison et position"""
        # Données saisonnières pour Méditerranée tunisienne
        seasonal_chlorophyll = {
            1: 0.3, 2: 0.4, 3: 0.8, 4: 1.5, 5: 2.2, 6: 1.8,
            7: 1.2, 8: 0.9, 9: 0.7, 10: 0.5, 11: 0.4, 12: 0.3
        }
        
        base_chl = seasonal_chlorophyll.get(month, 1.0)
        
        # Ajustement selon latitude (plus de productivité au nord)
        lat_factor = 1.0 + (lat - 36.0) * 0.05
        
        # Ajustement côtier vs offshore
        coastal_factor = 1.5 if self._is_coastal_tunisia(lat, lon) else 1.0
        
        estimated_chl = base_chl * lat_factor * coastal_factor
        return round(max(0.1, min(5.0, estimated_chl)), 2)

    def _is_coastal_tunisia(self, lat: float, lon: float) -> bool:
        """Détermine si la position est côtière en Tunisie"""
        coastal_zones = [
            (36.0, 10.0, 37.5, 11.5),  # Golfe de Tunis
            (35.5, 10.5, 36.5, 11.5),  # Sousse/Monastir
            (34.5, 10.0, 35.5, 11.0),  # Sfax
            (33.0, 10.5, 34.0, 11.5),  # Djerba/Zarzis
            (36.7, 8.5, 37.0, 9.5),    # Tabarka
            (35.0, 11.0, 35.5, 11.5)   # Mahdia
        ]
        
        for min_lat, min_lon, max_lat, max_lon in coastal_zones:
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return True
        return False

    def calculate_tidal_current(self, lat: float, lon: float, 
                              datetime_obj: datetime) -> dict:
        """Calcule les courants de marée pour la Tunisie"""
        # Calcul phase de marée
        lunar_cycle = 29.53
        days_since_new = (datetime_obj - datetime(datetime_obj.year, 1, 11)).days % lunar_cycle
        tide_phase = days_since_new / lunar_cycle
        
        # Hauteur de marée estimée (Méditerranée = marées faibles)
        tide_height = 0.3 + 0.2 * math.sin(tide_phase * 2 * math.pi)
        
        # Vitesse du courant (m/s) - adapté à la Tunisie
        current_speed = 0.05 + 0.15 * abs(math.sin(tide_phase * 4 * math.pi))
        
        # Direction du courant basée sur la géographie tunisienne
        if lat > 37.0:  # Nord (Bizerte, Tabarka)
            direction = "SO-NE" if tide_phase < 0.5 else "NE-SO"
        elif lat > 36.0:  # Golfe de Tunis
            direction = "O-E" if tide_phase < 0.25 else "E-O" if tide_phase < 0.5 else "SO-NE" if tide_phase < 0.75 else "NE-SO"
        elif lat > 35.0:  # Centre (Sousse, Monastir)
            direction = "NO-SE" if tide_phase < 0.5 else "SE-NO"
        else:  # Sud (Sfax, Djerba)
            direction = "N-S" if tide_phase < 0.5 else "S-N"
        
        # Déterminer si le courant est favorable pour la pêche
        current_for_fishing = "favorable" if 0.1 <= current_speed <= 0.3 else "trop faible" if current_speed < 0.1 else "trop fort"
        
        return {
            'speed_mps': round(current_speed, 2),
            'speed_knots': round(current_speed * 1.944, 2),
            'direction': direction,
            'tide_height': round(tide_height, 2),
            'tide_phase': 'montante' if tide_phase < 0.25 or tide_phase > 0.75 else 'descendante',
            'fishing_impact': current_for_fishing
        }

    def calculate_weather_factor(self, weather_data: dict, species: str) -> float:
        """Calcule un facteur météo pour la pêche (0-1) avec nouveaux facteurs"""
        profile = self.species_profiles.get(species, self.species_profiles["loup"])
        
        # Facteur température
        temp_opt = self._mean(profile["temp_optimal"])
        temp_diff = abs(weather_data['temperature'] - temp_opt)
        temp_score = max(0, 1 - temp_diff / profile["temp_tolerance"])
        
        # Facteur vent
        wind_tolerance = profile.get("wind_tolerance", "medium")
        wind_max = {"low": 15, "medium": 25, "high": 40}[wind_tolerance]
        wind_score = max(0, 1 - weather_data['wind_speed'] / wind_max)
        
        # Facteur vague
        wave_tolerance = profile.get("wave_tolerance", "medium")
        wave_max = {"low": 0.5, "medium": 1.0, "high": 2.0}[wave_tolerance]
        wave_score = max(0, 1 - weather_data.get('wave_height', 0.5) / wave_max)
        
        # Facteur pression
        pressure_diff = abs(weather_data['pressure'] - 1015)
        pressure_score = max(0, 1 - pressure_diff / 30)
        
        # NOUVEAU : Facteur oxygène dissous
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
        
        # Pondération améliorée avec oxygène
        if species in ["loup", "pageot"]:
            weights = {'temp': 0.3, 'wind': 0.2, 'wave': 0.15, 'pressure': 0.15, 'oxygen': 0.2}
        elif species in ["daurade", "sar"]:
            weights = {'temp': 0.25, 'wind': 0.15, 'wave': 0.25, 'pressure': 0.15, 'oxygen': 0.2}
        else:  # thon et autres
            weights = {'temp': 0.25, 'wind': 0.2, 'wave': 0.2, 'pressure': 0.15, 'oxygen': 0.2}
        
        weather_factor = (
            temp_score * weights['temp'] +
            wind_score * weights['wind'] +
            wave_score * weights['wave'] +
            pressure_score * weights['pressure'] +
            oxygen_score * weights.get('oxygen', 0)
        )
        
        return min(1.0, max(0.0, weather_factor))

    def calculate_environmental_score(self, weather_data: dict, species: str, 
                                    lat: float = None, lon: float = None) -> float:
        """Score environnemental incluant les 3 nouveaux facteurs"""
        profile = self.species_profiles.get(species, self.species_profiles["loup"])
        
        # Calculer les 3 nouveaux facteurs
        water_temp = weather_data.get('water_temperature', weather_data.get('temperature', 20))
        
        # 1. Oxygène dissous
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
        
        # 2. Chlorophylle
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
        
        # 3. Courant
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
        temp_diff = abs(weather_data['temperature'] - temp_opt)
        temp_score = max(0, 1 - temp_diff / profile["temp_tolerance"])
        
        wind_score = max(0, 1 - weather_data['wind_speed'] / 40)
        
        pressure_diff = abs(weather_data['pressure'] - 1015)
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
        
        # Nouvelle pondération avec les 3 facteurs scientifiques
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
        else:  # thon et pélagiques
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
        
        # Ajustement saisonnier
        current_month = datetime.now().month
        spawning_season = profile.get("spawning_season", [])
        if spawning_season and spawning_season[0] <= current_month <= spawning_season[1]:
            environmental_score *= 0.8
        
        return min(1.0, max(0.0, environmental_score))

    def predict_daily_activity(self, lat: float, lon: float, date: datetime, species: str, weather_data: dict) -> dict:
        """Prédiction améliorée avec les 3 nouveaux facteurs"""
        # Calcul des nouveaux facteurs
        water_temp = weather_data.get('water_temperature', weather_data['temperature'])
        oxygen_level = self.calculate_dissolved_oxygen(
            water_temp,
            weather_data.get('salinity', self.SALINITY_MEDITERRANEAN),
            weather_data.get('pressure', 1013)
        )
        
        month = date.month
        chlorophyll_level = self.estimate_chlorophyll(month, lat, lon)
        
        current_data = self.calculate_tidal_current(lat, lon, date)
        
        # Mettre à jour weather_data avec les nouveaux facteurs
        enhanced_weather = weather_data.copy()
        enhanced_weather.update({
            'oxygen': oxygen_level,
            'chlorophyll': chlorophyll_level,
            'current_speed': current_data['speed_mps'],
            'water_temperature': water_temp
        })
        
        env_score = self.calculate_environmental_score(enhanced_weather, species, lat, lon)
        behavior_score = self.calculate_behavioral_score(date, species)
        regional_factor = self._calculate_regional_factor(lat, lon, species, date.month)
        weather_factor = self.calculate_weather_factor(enhanced_weather, species)
        
        # Pondération améliorée
        activity_score = (
            env_score * 0.40 +  # Augmenté pour inclure les nouveaux facteurs
            behavior_score * 0.20 +
            regional_factor * 0.15 +
            weather_factor * 0.25
        )
        
        best_hours = self.calculate_best_hours(date, species, activity_score, enhanced_weather)
        
        if activity_score > 0.75:
            opportunity = "EXCELLENTE"
            color = "#10b981"
        elif activity_score > 0.65:
            opportunity = "TRÈS BONNE"
            color = "#22c55e"
        elif activity_score > 0.55:
            opportunity = "BONNE"
            color = "#f59e0b"
        elif activity_score > 0.45:
            opportunity = "MOYENNE"
            color = "#3b82f6"
        else:
            opportunity = "FAIBLE"
            color = "#ef4444"
        
        limitations = []
        favorable_factors = []
        
        # Limitations basées sur les nouveaux facteurs
        if enhanced_weather.get('oxygen', 6.0) < 4.0:
            limitations.append(f"Oxygène dissous faible ({enhanced_weather['oxygen']} mg/L)")
        elif enhanced_weather.get('oxygen', 6.0) > 7.5:
            favorable_factors.append(f"Oxygène dissous optimal ({enhanced_weather['oxygen']} mg/L)")
        
        if enhanced_weather.get('chlorophyll', 1.5) < 0.5:
            limitations.append("Faible productivité (chlorophylle basse)")
        elif enhanced_weather.get('chlorophyll', 1.5) > 2.5:
            favorable_factors.append("Forte productivité primaire")
        
        if enhanced_weather.get('current_speed', 0.2) < 0.1:
            limitations.append("Courant trop faible pour activer la nourriture")
        elif enhanced_weather.get('current_speed', 0.2) > 0.5:
            limitations.append("Courant trop fort pour pêcher confortablement")
        else:
            favorable_factors.append(f"Courant favorable ({enhanced_weather['current_speed']} m/s)")
        
        # Limitations traditionnelles
        if enhanced_weather['wind_speed'] > 30:
            limitations.append("Vent trop fort pour pêche côtière")
        elif enhanced_weather['wind_speed'] < 10:
            favorable_factors.append("Vent faible - conditions idéales")
        
        if enhanced_weather.get('wave_height', 0.5) > 1.5:
            limitations.append("Mer trop agitée")
        elif enhanced_weather.get('wave_height', 0.5) < 0.5:
            favorable_factors.append("Mer calme - excellente visibilité")
        
        if abs(enhanced_weather['temperature'] - self._mean(self.species_profiles[species]["temp_optimal"])) > 8:
            limitations.append("Température non optimale")
        else:
            favorable_factors.append("Température favorable")
        
        if abs(enhanced_weather['pressure'] - 1015) < 10:
            favorable_factors.append("Pression stable - activité normale")
        
        return {
            'fishing_opportunity': opportunity,
            'activity_score': round(activity_score, 3),
            'environmental_score': round(env_score, 3),
            'behavioral_score': round(behavior_score, 3),
            'regional_factor': round(regional_factor, 3),
            'weather_factor': round(weather_factor, 3),
            'color': color,
            'confidence': round(0.65 + activity_score * 0.35, 2),  # Augmenté
            'best_fishing_hours': best_hours,
            'limitations': limitations[:3],
            'favorable_factors': favorable_factors[:3],
            'species': species,
            'date': date.strftime("%Y-%m-%d"),
            'recommended_techniques': self._get_recommended_techniques(species, enhanced_weather),
            'bathymetry': self.get_bathymetry_data(lat, lon),
            'weather_summary': self._get_weather_summary(enhanced_weather),
            # NOUVEAUX : Données scientifiques
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

    # ===== MÉTHODES EXISTANTES (MODIFIÉES POUR L'INTÉGRATION) =====
    
    def _get_weather_summary(self, weather_data: dict) -> str:
        """Génère un résumé météo incluant les nouveaux facteurs"""
        temp = weather_data['temperature']
        wind = weather_data['wind_speed']
        pressure = weather_data['pressure']
        oxygen = weather_data.get('oxygen', 6.0)
        chlorophyll = weather_data.get('chlorophyll', 1.5)
        
        summary = []
        
        if 15 <= temp <= 25:
            summary.append("Température idéale")
        elif temp < 10:
            summary.append("Température basse")
        elif temp > 30:
            summary.append("Température élevée")
        
        if wind < 10:
            summary.append("Vent faible")
        elif wind > 25:
            summary.append("Vent fort")
        
        if pressure < 1000:
            summary.append("Pression basse")
        elif pressure > 1030:
            summary.append("Pression haute")
        
        if oxygen > 7.0:
            summary.append("Eau bien oxygénée")
        elif oxygen < 4.0:
            summary.append("Oxygène faible")
        
        if chlorophyll > 2.0:
            summary.append("Eau productive")
        
        return ", ".join(summary) if summary else "Conditions normales"

    def calculate_behavioral_score(self, date: datetime, species: str, moon_phase: float = None) -> float:
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
        
        if moon_phase is None:
            lunar_cycle = 29.53
            days_since_new_moon = (date - datetime(date.year, 1, 11)).days % lunar_cycle
            moon_phase = days_since_new_moon / lunar_cycle
        
        moon_sensitivity = profile.get("moon_sensitivity", "moderate")
        if moon_sensitivity == "high":
            moon_score = 0.4 + 0.6 * abs(math.sin(moon_phase * math.pi))
        elif moon_sensitivity == "moderate":
            moon_score = 0.6 + 0.4 * abs(math.sin(moon_phase * math.pi))
        else:
            # REMPLACÉ : plus d'aléatoire, formule déterministe
            moon_score = 0.7 + 0.3 * math.sin(moon_phase * math.pi * 2)
        
        tide_cycle = 12.4
        tide_phase = (hour % tide_cycle) / tide_cycle
        tide_score = 0.7 + 0.3 * abs(math.sin(tide_phase * 2 * math.pi))
        
        feeding_intensity = profile.get("feeding_intensity", [0.6, 0.8])
        base_feeding = (feeding_intensity[0] + feeding_intensity[1]) / 2
        
        return diel_score * 0.4 + moon_score * 0.3 + tide_score * 0.2 + base_feeding * 0.1

    # ===== MÉTHODES UTILITAIRES =====
    
    def _mean(self, arr):
        if not arr:
            return 0
        if isinstance(arr[0], (list, tuple)):
            return (arr[0] + arr[1]) / 2
        return sum(arr) / len(arr)
    
    def _calculate_regional_factor(self, lat: float, lon: float, species: str, month: int) -> float:
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
        
        return min(1.0, max(0.0, factor))
    
    def get_bathymetry_data(self, lat: float, lon: float) -> dict:
        # Méthode existante inchangée
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
            distance = abs(lat - known_lat) + abs(lon - known_lon)
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
                if lon > 10.5 and lat < 36.5:
                    seabed_type = "grass"
                else:
                    seabed_type = "mixed"
            elif depth < 25:
                seabed_type = "rock"
            else:
                seabed_type = "mud"
        
        seabed_descriptions = {
            "sand": "Sable fin",
            "rock": "Rochers",
            "grass": "Herbier",
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

    def calculate_best_hours(self, date: datetime, species: str, activity_score: float, weather_data: dict) -> list:
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
        
        # Ajustement selon la météo ET les nouveaux facteurs
        weather_adjustment = 1.0
        if weather_data['wind_speed'] > 20:
            weather_adjustment *= 0.8
        if weather_data.get('wave_height', 0.5) > 1.2:
            weather_adjustment *= 0.7
        if abs(weather_data['pressure'] - 1015) < 10:
            weather_adjustment *= 1.1
        
        # Ajustement selon oxygène
        oxygen = weather_data.get('oxygen', 6.0)
        if oxygen > 7.0:
            weather_adjustment *= 1.1
        elif oxygen < 4.0:
            weather_adjustment *= 0.8
        
        # Ajustement selon chlorophylle (productivité)
        chlorophyll = weather_data.get('chlorophyll', 1.5)
        if 1.0 <= chlorophyll <= 3.0:
            weather_adjustment *= 1.05
        
        adjusted_hours = []
        for hour, base_score in base_hours:
            # Moins d'aléatoire, plus déterministe
            deterministic_variation = 0.95 + (hour % 3) * 0.025
            hour_factor = 1.0 - abs(hour - 12) / 24 * 0.3
            adjusted_score = base_score * weather_adjustment * hour_factor * deterministic_variation
            adjusted_score = min(0.95, max(0.3, adjusted_score))
            
            if adjusted_score > 0.8:
                level = "EXCELLENT"
                color = "#10b981"
            elif adjusted_score > 0.7:
                level = "BON"
                color = "#22c55e"
            elif adjusted_score > 0.6:
                level = "MOYEN"
                color = "#f59e0b"
            else:
                level = "FAIBLE"
                color = "#ef4444"
            
            adjusted_hours.append({
                'hour': hour,
                'score': round(adjusted_score, 3),
                'level': level,
                'color': color,
                'description': f"{hour}h-{hour+2}h"
            })
        
        adjusted_hours.sort(key=lambda x: x['score'], reverse=True)
        return adjusted_hours[:5]

    def _get_recommended_techniques(self, species: str, weather_data: dict) -> list:
        techniques = {
            "loup": ["surfcasting", "pêche à soutenir", "pêche au leurre", "pêche au vif"],
            "daurade": ["pêche au flotteur", "pêche à soutenir", "pêche à l'anglaise", "pêche fine"],
            "pageot": ["pêche à soutenir", "pêche au leurre", "pêche à la dandine"],
            "thon": ["pêche à la traîne", "pêche à la dérive", "pêche au vif"],
            "sar": ["pêche à soutenir", "pêche au flotteur", "pêche au leurre"]
        }
        
        base_techniques = techniques.get(species, ["pêche à soutenir", "surfcasting"])
        
        # Ajustement selon la météo ET les nouveaux facteurs
        if weather_data['wind_speed'] > 20:
            base_techniques = [t for t in base_techniques if t not in ["pêche au flotteur", "pêche fine"]]
        
        if weather_data.get('wave_height', 0.5) > 1.0:
            if "surfcasting" not in base_techniques:
                base_techniques.append("surfcasting")
        
        # Ajustement selon courant
        current_speed = weather_data.get('current_speed', 0.2)
        if current_speed > 0.3:
            if "pêche à la dérive" not in base_techniques:
                base_techniques.append("pêche à la dérive")
        
        return base_techniques[:3]

    # Les autres méthodes existantes restent similaires...

if __name__ == "__main__":
    predictor = ScientificFishingPredictor()
    print("=" * 60)
    print("🧪 SCIENTIFIC FISHING PREDICTOR - VERSION 2.1")
    print("=" * 60)
    print("✅ 3 nouveaux facteurs scientifiques intégrés")
    print("✅ Oxygène dissous calculé scientifiquement")
    print("✅ Chlorophylle estimée saisonnièrement")
    print("✅ Courants de marée calculés")
    print("=" * 60)
    
    # Test des nouveaux facteurs
    test_lat, test_lon = 36.8, 10.1
    test_temp = 22.5
    
    print("\n🔬 TEST DES NOUVEAUX FACTEURS:")
    print(f"📍 Position: {test_lat}, {test_lon}")
    
    # Test oxygène dissous
    oxygen = predictor.calculate_dissolved_oxygen(test_temp, 38.0, 1013)
    print(f"💨 Oxygène dissous: {oxygen} mg/L")
    
    # Test chlorophylle
    month = datetime.now().month
    chlorophyll = predictor.estimate_chlorophyll(month, test_lat, test_lon)
    print(f"🌿 Chlorophylle estimée: {chlorophyll} mg/m³")
    
    # Test courants
    current = predictor.calculate_tidal_current(test_lat, test_lon, datetime.now())
    print(f"🌊 Courant de marée: {current['speed_mps']} m/s ({current['direction']})")
    
    print("=" * 60)