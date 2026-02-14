#!/usr/bin/env python3
"""
Script de test pour vérifier les scores d'activité de Fishing Predictor Pro
Utilisation : python test_scores.py [latitude] [longitude] [espèce]
Exemple : python test_scores.py 36.8065 10.1815 loup
"""

import requests
import sys
import json
from datetime import datetime
import statistics

def test_forecast_scores(lat=36.8065, lon=10.1815, species='loup'):
    """Teste les scores de l'API forecast_10days"""
    
    print("="*60)
    print("🎣 TEST DES SCORES D'ACTIVITÉ - FISHING PREDICTOR PRO")
    print("="*60)
    print(f"📍 Position: {lat}, {lon}")
    print(f"🐟 Espèce: {species}")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*60)
    
    # URL de l'API
    url = f"http://127.0.0.1:5000/api/forecast_10days?lat={lat}&lon={lon}&species={species}"
    
    try:
        # Appel à l'API
        print("📡 Appel à l'API...")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Erreur HTTP: {response.status_code}")
            print(response.text[:200])
            return False
        
        data = response.json()
        
        if data.get('status') != 'success':
            print(f"❌ Erreur API: {data.get('message', 'unknown')}")
            return False
        
        forecast = data.get('forecast', [])
        
        if not forecast:
            print("❌ Aucune prévision reçue")
            return False
        
        # Analyse des scores
        print(f"\n📊 Analyse des {len(forecast)} jours de prévision:")
        print(f"📌 Source des données: {data.get('source', 'unknown')}")
        print(f"📌 Note: {data.get('note', '')}")
        print("-"*60)
        
        scores = []
        for day in forecast:
            scores.append(day['score'])
            date = datetime.strptime(day['date'], '%Y-%m-%d').strftime('%d/%m')
            weather = day.get('weather', {})
            wind = weather.get('wind_speed', '?')
            temp = weather.get('temp_avg', weather.get('temperature', '?'))
            
            # Émoticône selon le score
            if day['score'] >= 80:
                emoji = "✅ EXCELLENT"
            elif day['score'] >= 60:
                emoji = "🟡 BON"
            elif day['score'] >= 40:
                emoji = "⚠️ MOYEN"
            else:
                emoji = "❌ FAIBLE"
            
            print(f"Jour {day['day']:2d} | {date} | Score: {day['score']:3d}% | {emoji} | Vent: {wind} km/h | Temp: {temp}°C")
        
        print("-"*60)
        
        # Statistiques
        print(f"\n📈 STATISTIQUES:")
        print(f"   Score minimum: {min(scores)}%")
        print(f"   Score maximum: {max(scores)}%")
        print(f"   Score moyen: {statistics.mean(scores):.1f}%")
        print(f"   Écart-type: {statistics.stdev(scores) if len(scores) > 1 else 0:.1f}")
        
        # Vérification de la cohérence
        print(f"\n🔍 VÉRIFICATION DE COHÉRENCE:")
        
        # 1. Scores entre 0 et 100 ?
        if all(0 <= s <= 100 for s in scores):
            print("   ✅ Tous les scores sont entre 0 et 100")
        else:
            print("   ❌ Des scores sont hors limite 0-100 !")
            outliers = [s for s in scores if s < 0 or s > 100]
            print(f"      Scores anormaux: {outliers}")
        
        # 2. Variation réaliste ?
        score_range = max(scores) - min(scores)
        if 10 <= score_range <= 60:
            print(f"   ✅ Variation de score réaliste: {score_range} points")
        elif score_range < 10:
            print(f"   ⚠️ Variation trop faible: {score_range} points (peut-être trop stable)")
        else:
            print(f"   ⚠️ Variation très forte: {score_range} points (peut-être trop instable)")
        
        # 3. Distribution
        excellent = sum(1 for s in scores if s >= 80)
        bon = sum(1 for s in scores if 60 <= s < 80)
        moyen = sum(1 for s in scores if 40 <= s < 60)
        faible = sum(1 for s in scores if s < 40)
        
        print(f"\n📊 DISTRIBUTION:")
        print(f"   ✅ Excellent (80-100%): {excellent} jours")
        print(f"   🟡 Bon (60-79%): {bon} jours")
        print(f"   ⚠️ Moyen (40-59%): {moyen} jours")
        print(f"   ❌ Faible (0-39%): {faible} jours")
        
        # 4. Lien avec le vent (logique basique)
        print(f"\n🌬️  CORRÉLATION VENT/SCORE:")
        correlations = []
        for day in forecast[:5]:  # 5 premiers jours
            wind = day.get('weather', {}).get('wind_speed', 0)
            score = day['score']
            if wind > 30 and score > 70:
                correlations.append(("⚠️", f"Vent fort ({wind} km/h) mais bon score ({score}%)"))
            elif wind < 10 and score < 40:
                correlations.append(("⚠️", f"Vent faible ({wind} km/h) mais mauvais score ({score}%)"))
        
        if correlations:
            for icon, msg in correlations:
                print(f"   {icon} {msg}")
        else:
            print("   ✅ Pas d'incohérence majeure vent/score détectée")
        
        # 5. Test de plusieurs espèces
        if species == 'loup':
            print(f"\n🔄 TEST COMPARATIF ESPÈCES (position fixe):")
            test_species_comparison(lat, lon)
        
        print("="*60)
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Erreur de connexion: Le serveur Flask est-il en cours d'exécution sur http://127.0.0.1:5000 ?")
        return False
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def test_species_comparison(lat=36.8065, lon=10.1815):
    """Teste les scores pour différentes espèces au même endroit"""
    species_list = ['loup', 'daurade', 'thon']
    results = {}
    
    for species in species_list:
        url = f"http://127.0.0.1:5000/api/forecast_10days?lat={lat}&lon={lon}&species={species}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                forecast = data.get('forecast', [])
                if forecast:
                    avg_score = statistics.mean([d['score'] for d in forecast])
                    results[species] = avg_score
        except:
            pass
    
    if results:
        for species, avg in results.items():
            print(f"   {species.capitalize():8s}: {avg:.1f}%")
        
        # Vérification que les scores sont différents (logique)
        if len(set(results.values())) == 1:
            print("   ⚠️ Toutes les espèces ont le même score - problème probable !")
        else:
            print("   ✅ Les scores varient selon l'espèce (normal)")

def test_multiple_positions():
    """Teste les scores sur plusieurs spots connus"""
    print("\n📍 TEST SUR DIFFÉRENTS SPOTS:")
    
    spots = [
        {"name": "Tunis Marina", "lat": 36.8065, "lon": 10.1815},
        {"name": "Cap Bon", "lat": 36.8475, "lon": 11.0940},
        {"name": "Bizerte", "lat": 37.2747, "lon": 9.8739},
        {"name": "Sousse", "lat": 35.8254, "lon": 10.6360},
        {"name": "Large (mer ouverte)", "lat": 37.5000, "lon": 11.5000},
    ]
    
    for spot in spots:
        url = f"http://127.0.0.1:5000/api/forecast_10days?lat={spot['lat']}&lon={spot['lon']}&species=loup"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                forecast = data.get('forecast', [])
                if forecast:
                    avg_score = statistics.mean([d['score'] for d in forecast[:3]])  # 3 premiers jours
                    source = data.get('source', 'unknown')
                    print(f"   {spot['name']:15s}: {avg_score:.1f}% (source: {source})")
        except:
            print(f"   {spot['name']:15s}: ❌ Erreur")

if __name__ == "__main__":
    # Récupération des arguments
    lat = 36.8065
    lon = 10.1815
    species = 'loup'
    
    if len(sys.argv) > 1:
        try:
            lat = float(sys.argv[1])
        except:
            print(f"❌ Latitude invalide: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        try:
            lon = float(sys.argv[2])
        except:
            print(f"❌ Longitude invalide: {sys.argv[2]}")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        species = sys.argv[3]
    
    # Exécution des tests
    success = test_forecast_scores(lat, lon, species)
    
    if success:
        # Tests supplémentaires
        test_multiple_positions()
    
    print("\n" + "="*60)