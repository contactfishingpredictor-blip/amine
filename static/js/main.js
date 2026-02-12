// main.js - Version complètement corrigée avec météo et animation du vent
console.log("🎣 Fishing Predictor Pro - Module principal initialisé");

// Variables globales
let currentWeatherData = null;
let isWeatherInitialized = false;

// Fonction principale pour charger les données météo
async function loadWeatherData() {
    console.log("🌤️ Chargement des données météo...");
    
    try {
        // Coordonnées par défaut (Tunis Marina)
        const lat = 36.8065;
        const lon = 10.1815;
        
        console.log(`📍 Position: ${lat}, ${lon}`);
        
        // Appeler l'API météo
        const response = await fetch(`/api/current_weather?lat=${lat}&lon=${lon}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("📊 Données météo reçues:", data);
        
        if (data.status === 'success') {
            currentWeatherData = data.weather;
            console.log("✅ Météo chargée avec succès");
            updateWeatherDisplay(currentWeatherData);
            
            // Mettre à jour l'animation du vent si elle est active
            if (typeof window.updateWindAnimation === 'function' && window.windAnimationActive) {
                window.updateWindAnimation();
            }
            
            return currentWeatherData;
        } else {
            throw new Error(data.message || 'Erreur inconnue de l\'API');
        }
    } catch (error) {
        console.error('❌ Erreur lors du chargement de la météo:', error);
        
        // Afficher une notification d'erreur
        showNotification('Impossible de charger la météo, données simulées utilisées', 'warning');
        
        // Utiliser des données simulées en cas d'erreur
        const fallbackWeather = generateFallbackWeather();
        updateWeatherDisplay(fallbackWeather);
        return fallbackWeather;
    }
}

// Mettre à jour l'affichage de la météo dans le DOM
function updateWeatherDisplay(weatherData) {
    console.log("🎨 Mise à jour de l'affichage météo:", weatherData);
    
    if (!weatherData) {
        console.error("❌ Aucune donnée météo à afficher");
        return;
    }
    
    // Mettre à jour les éléments du DOM
    const elementsToUpdate = {
        'temperature': `${weatherData.temperature?.toFixed(1) || '--'}°C`,
        'weather-condition': weatherData.condition_fr || weatherData.condition || '--',
        'wind-speed': `${weatherData.wind_speed?.toFixed(1) || '--'} km/h`,
        'weather-location-name': weatherData.location || 'Tunis Marina',
        'wind-direction': weatherData.wind_direction_name || '--',
        'weather-pressure': `${weatherData.pressure || '--'} hPa`,
        'wind-impact': weatherData.wind_fishing_impact || '--',
        'wind-fishing-tips': weatherData.wind_fishing_impact || '--',
        'weather-updated': new Date().toLocaleTimeString('fr-FR', {hour: '2-digit', minute: '2-digit'})
    };
    
    // Mettre à jour chaque élément
    Object.entries(elementsToUpdate).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            console.log(`   ✅ ${id}: ${value}`);
        } else {
            console.log(`   ⚠️  Élément ${id} non trouvé dans le DOM`);
        }
    });
    
    // Mettre à jour l'icône météo principale si présente
    const weatherMainIcon = document.getElementById('weather-main-icon');
    if (weatherMainIcon) {
        const weatherIcon = getWeatherIcon(weatherData.condition, weatherData.icon);
        weatherMainIcon.innerHTML = weatherIcon;
        console.log(`   ✅ Icône météo principale: ${weatherIcon}`);
    }
    
    // Mettre à jour l'icône de direction du vent (weather-icon)
    const windIconElement = document.getElementById('weather-icon');
    if (windIconElement) {
        windIconElement.textContent = weatherData.wind_direction_icon || '⬆️';
        console.log(`   ✅ Icône direction vent: ${weatherData.wind_direction_icon || '⬆️'}`);
    } else {
        console.log('   ⚠️ Élément weather-icon non trouvé');
    }
    
    // Mettre à jour les badges de sécurité du vent
    updateWindSafetyBadges(weatherData);
    
    // Mettre à jour la légende du vent si elle est visible
    if (typeof window.updateWindLegend === 'function') {
        window.updateWindLegend();
    }
    
    // Stocker en cache pour utilisation ultérieure
    window.weatherDataCache = weatherData;
    
    console.log("✅ Affichage météo mis à jour avec succès");
}

// Obtenir l'icône météo appropriée
function getWeatherIcon(condition, iconCode) {
    if (!condition) return '🌤️';
    
    const conditionLower = condition.toLowerCase();
    if (conditionLower.includes('clear') || conditionLower.includes('sunny')) return '☀️';
    if (conditionLower.includes('cloud')) return '⛅';
    if (conditionLower.includes('rain')) return '🌧️';
    if (conditionLower.includes('drizzle')) return '🌦️';
    if (conditionLower.includes('thunder') || conditionLower.includes('storm')) return '⛈️';
    if (conditionLower.includes('snow')) return '❄️';
    if (conditionLower.includes('fog') || conditionLower.includes('mist')) return '🌫️';
    
    return '🌤️';
}

// Mettre à jour les badges de sécurité du vent
function updateWindSafetyBadges(weatherData) {
    const windOffshoreAlert = document.getElementById('wind-offshore-alert');
    const windStrongAlert = document.getElementById('wind-strong-alert');
    
    if (windOffshoreAlert) {
        windOffshoreAlert.style.display = weatherData.wind_offshore ? 'block' : 'none';
        if (weatherData.wind_offshore) {
            console.log('   ⚠️ Alerte vent offshore activée');
        }
    }
    
    if (windStrongAlert) {
        windStrongAlert.style.display = (weatherData.wind_speed > 25) ? 'block' : 'none';
        if (weatherData.wind_speed > 25) {
            console.log('   💨 Alerte vent fort activée');
        }
    }
    
    // Mettre à jour le badge de sécurité
    const safetyBadge = document.getElementById('wind-safety-badge');
    if (safetyBadge) {
        if (weatherData.wind_offshore) {
            safetyBadge.textContent = 'Dangereux';
            safetyBadge.style.background = '#fee2e2';
            safetyBadge.style.color = '#991b1b';
        } else if (weatherData.wind_speed < 10) {
            safetyBadge.textContent = 'Sécuritaire';
            safetyBadge.style.background = '#d1fae5';
            safetyBadge.style.color = '#065f46';
        } else if (weatherData.wind_speed < 20) {
            safetyBadge.textContent = 'Modéré';
            safetyBadge.style.background = '#fef3c7';
            safetyBadge.style.color = '#92400e';
        } else {
            safetyBadge.textContent = 'Difficile';
            safetyBadge.style.background = '#fee2e2';
            safetyBadge.style.color = '#991b1b';
        }
        console.log(`   ✅ Badge sécurité: ${safetyBadge.textContent}`);
    }
    
    // Mettre à jour les conseils de pêche
    const fishingTips = document.getElementById('wind-fishing-tips');
    if (fishingTips) {
        if (weatherData.wind_offshore) {
            fishingTips.textContent = '⚠️ VENT DE TERRE - ÉVITEZ LA PÊCHE CÔTIÈRE. Risque d\'être emporté au large.';
        } else if (weatherData.wind_speed > 25) {
            fishingTips.textContent = 'Vent fort détecté. Conditions difficiles pour la pêche. Privilégiez la pêche au surfcasting.';
        } else if (weatherData.wind_speed > 15) {
            fishingTips.textContent = 'Vent modéré. Bonnes conditions pour la pêche, mais soyez prudent.';
        } else {
            fishingTips.textContent = 'Conditions optimales pour la pêche. Vent faible et favorable.';
        }
        console.log(`   ✅ Conseils pêche: ${fishingTips.textContent.substring(0, 50)}...`);
    }
}

// Générer des données météo de secours
function generateFallbackWeather() {
    const now = new Date();
    const hour = now.getHours();
    
    // Température basée sur l'heure
    const baseTemp = 20;
    const hourVariation = Math.sin(hour * Math.PI / 12) * 5;
    const temp = baseTemp + hourVariation;
    
    // Vent basé sur l'heure
    const wind = 10 + Math.sin(hour * Math.PI / 6) * 5;
    
    return {
        temperature: Math.round(temp),
        condition: 'Ensoleillé',
        condition_fr: 'Ensoleillé',
        wind_speed: Math.round(wind),
        wind_direction_name: 'Nord',
        wind_direction_icon: '⬆️',
        wind_fishing_impact: 'Conditions normales',
        location: 'Tunis Marina',
        pressure: 1015,
        humidity: 65,
        icon: '01d',
        source: 'modèle local',
        wind_offshore: false,
        wind_onshore: true
    };
}

// Rafraîchir la météo
function refreshWeather() {
    console.log("🔄 Rafraîchissement de la météo...");
    loadWeatherData();
    showNotification('Météo actualisée', 'info');
}

// Initialiser la météo
function initWeather() {
    if (isWeatherInitialized) {
        console.log("⚠️ Météo déjà initialisée");
        return;
    }
    
    console.log("🚀 Initialisation du module météo...");
    
    // Vérifier si on est sur une page qui nécessite la météo
    const hasWeatherElements = document.getElementById('temperature') || 
                               document.getElementById('weather-condition') ||
                               document.getElementById('wind-speed');
    
    if (isHomePage() || isPredictionsPage() || hasWeatherElements) {
        console.log("📄 Page détectée avec éléments météo");
        
        // Cacher le conteneur d'erreur au démarrage
        const errorEl = document.getElementById('weather-error');
        if (errorEl) errorEl.style.display = 'none';
        
        // Charger la météo immédiatement
        loadWeatherData();
        
        // Recharger la météo toutes les 5 minutes
        setInterval(loadWeatherData, 5 * 60 * 1000);
        
        isWeatherInitialized = true;
        console.log("✅ Module météo initialisé avec succès");
    } else {
        console.log("⚠️ Page sans éléments météo détectée");
    }
}

// Vérifier si on est sur la page d'accueil
function isHomePage() {
    const path = window.location.pathname;
    return path === '/' || path.includes('index') || path === '' || path.endsWith('/');
}

// Vérifier si on est sur la page des prévisions
function isPredictionsPage() {
    return window.location.pathname.includes('/predictions');
}

// Afficher une notification
function showNotification(message, type = 'info') {
    console.log(`📢 ${type.toUpperCase()}: ${message}`);
    
    // Créer une notification simple
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : 
                     type === 'error' ? '#ef4444' : 
                     type === 'warning' ? '#f59e0b' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
        max-width: 350px;
    `;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-circle' : 
                 type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon}" style="font-size: 1.2rem"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" style="margin-left:15px;background:none;border:none;color:white;cursor:pointer;font-size:1.2rem">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // Supprimer après 5 secondes
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
}

// Vérifier les éléments DOM météo
function checkWeatherElements() {
    console.log("🔍 Vérification des éléments météo...");
    
    const elements = [
        'temperature', 'weather-condition', 'wind-speed', 'weather-location-name',
        'weather-icon', 'wind-direction', 'weather-pressure', 'wind-impact',
        'wind-fishing-tips', 'weather-updated'
    ];
    
    elements.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            console.log(`   ✅ ${id}: présent`);
        } else {
            console.log(`   ❌ ${id}: absent`);
        }
    });
}

// Fonction pour tester l'API météo manuellement
window.testWeatherAPI = async function() {
    console.log("🧪 Test manuel de l'API météo...");
    
    try {
        const response = await fetch('/api/current_weather?lat=36.8065&lon=10.1815&refresh=true');
        const data = await response.json();
        console.log("📊 Résultat du test:", data);
        
        if (data.status === 'success') {
            showNotification(`✅ Météo chargée! ${data.weather.temperature}°C, ${data.weather.condition_fr}`, 'success');
            return data.weather;
        } else {
            showNotification('❌ Erreur: ' + (data.message || 'Inconnue'), 'error');
            return null;
        }
    } catch (error) {
        console.error('❌ Erreur test:', error);
        showNotification('❌ Erreur de connexion: ' + error.message, 'error');
        return null;
    }
};

// Fonction pour activer/désactiver l'animation du vent
window.toggleWindAnimation = function() {
    console.log("💨 Toggle animation du vent");
    if (typeof window.toggleWindLayer === 'function') {
        window.toggleWindLayer();
    } else {
        showNotification('Animation du vent non disponible sur cette page', 'warning');
    }
};

// Fonction pour vérifier si l'animation du vent est disponible
function checkWindAnimationAvailability() {
    console.log("🔧 Vérification disponibilité animation vent...");
    
    const functions = [
        'toggleWindLayer',
        'addWindAnimation',
        'removeWindAnimation',
        'updateWindAnimation'
    ];
    
    functions.forEach(func => {
        if (typeof window[func] === 'function') {
            console.log(`   ✅ ${func}(): disponible`);
        } else {
            console.log(`   ❌ ${func}(): non disponible`);
        }
    });
}

// Back to top button
document.addEventListener('DOMContentLoaded', function() {
    console.log("📄 DOM chargé - Initialisation de l'application");
    
    // Back to top button
    const backToTop = document.createElement('div');
    backToTop.id = 'back-to-top';
    backToTop.className = 'back-to-top';
    backToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTop.style.display = 'none';
    
    backToTop.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    
    document.body.appendChild(backToTop);
    
    window.addEventListener('scroll', function() {
        backToTop.style.display = window.scrollY > 300 ? 'flex' : 'none';
    });
    
    // Initialiser la météo après un court délai
    setTimeout(() => {
        initWeather();
        checkWeatherElements();
        checkWindAnimationAvailability();
    }, 1000);
    
    console.log("✅ Application initialisée");
});

// Exposer les fonctions globalement
window.loadWeatherData = loadWeatherData;
window.updateWeatherDisplay = updateWeatherDisplay;
window.initWeather = initWeather;
window.showNotification = showNotification;
window.testWeatherAPI = testWeatherAPI;
window.refreshWeather = refreshWeather;
window.toggleWindAnimation = toggleWindAnimation;
window.checkWeatherElements = checkWeatherElements;

console.log("✅ Module main.js chargé avec fonctions météo et animation du vent complètes");