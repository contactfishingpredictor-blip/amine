// main.js - Version optimisée mobile avec détection et performance
console.log("🎣 Fishing Predictor Pro - Module principal initialisé");

// Variables globales
let currentWeatherData = null;
let isWeatherInitialized = false;
let isMobileDevice = false;

// Détection mobile
function detectMobileDevice() {
    isMobileDevice = (window.innerWidth <= 768) || 
                     ('ontouchstart' in window) || 
                     (navigator.maxTouchPoints > 0) ||
                     (navigator.msMaxTouchPoints > 0);
    
    console.log(`📱 Détection mobile: ${isMobileDevice ? 'OUI' : 'NON'}`);
    return isMobileDevice;
}

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
            console.log(`   ✅ ${id}: ${value.substring(0, 30)}...`);
        }
    });
    
    // Mettre à jour l'icône de direction du vent
    const windIconElement = document.getElementById('weather-icon');
    if (windIconElement) {
        windIconElement.textContent = weatherData.wind_direction_icon || '⬆️';
    }
    
    // Mettre à jour les badges de sécurité du vent
    updateWindSafetyBadges(weatherData);
    
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
    const offshoreDanger = document.getElementById('offshore-danger');
    
    if (windOffshoreAlert) {
        windOffshoreAlert.style.display = weatherData.wind_offshore ? 'block' : 'none';
    }
    
    if (offshoreDanger) {
        offshoreDanger.style.display = weatherData.wind_offshore ? 'block' : 'none';
    }
    
    // Mettre à jour les conseils de pêche
    const fishingTips = document.getElementById('wind-fishing-tips');
    if (fishingTips) {
        if (weatherData.wind_offshore) {
            fishingTips.textContent = '⚠️ VENT OFFSHORE - DANGER DE NOYADE. NE PÊCHEZ PAS.';
        } else if (weatherData.wind_speed > 30) {
            fishingTips.textContent = 'VENT TRÈS FORT - Pêche déconseillée, risque de sécurité élevé.';
        } else if (weatherData.wind_speed > 20) {
            fishingTips.textContent = 'Vent fort - Conditions difficiles, prudence recommandée.';
        } else {
            fishingTips.textContent = weatherData.wind_fishing_impact || 'Conditions normales pour la pêche.';
        }
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
        
        // Recharger la météo toutes les 10 minutes (moins fréquent sur mobile)
        const refreshInterval = isMobileDevice ? 10 * 60 * 1000 : 5 * 60 * 1000;
        setInterval(loadWeatherData, refreshInterval);
        
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
    
    // Supprimer les notifications existantes
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notif => notif.remove());
    
    // Créer une notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    const icon = icons[type] || 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon}" style="font-size: 1.2rem"></i>
        <span style="flex:1">${message}</span>
        <button class="close-notification" onclick="this.parentElement.remove()">×</button>
    `;
    
    document.body.appendChild(notification);
    
    // Animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Supprimer après 5 secondes
    setTimeout(() => {
        if (notification.parentElement) {
            notification.classList.remove('show');
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
            console.log(`   ⚠️ ${id}: absent`);
        }
    });
}

// Fonction pour tester l'API météo
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

// Fonction pour activer/désactiver l'animation du vent (désactivée sur mobile par défaut)
window.toggleWindAnimation = function() {
    if (isMobileDevice) {
        showNotification('Animation du vent désactivée sur mobile pour économiser la batterie', 'info');
        return;
    }
    
    console.log("💨 Toggle animation du vent");
    if (typeof window.toggleWindLayer === 'function') {
        window.toggleWindLayer();
    } else {
        showNotification('Animation du vent non disponible sur cette page', 'warning');
    }
};

// Back to top button
function initBackToTop() {
    const backToTop = document.getElementById('back-to-top');
    if (!backToTop) {
        const btn = document.createElement('div');
        btn.id = 'back-to-top';
        btn.className = 'back-to-top';
        btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
        btn.style.display = 'none';
        
        btn.addEventListener('click', function() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        
        document.body.appendChild(btn);
        
        window.addEventListener('scroll', function() {
            btn.style.display = window.scrollY > 300 ? 'flex' : 'none';
        });
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log("📄 DOM chargé - Initialisation de l'application");
    
    // Détecter mobile
    detectMobileDevice();
    
    // Initialiser back to top
    initBackToTop();
    
    // Initialiser la météo après un court délai
    setTimeout(() => {
        initWeather();
        checkWeatherElements();
    }, 1000);
    
    // Adapter les popups Leaflet pour mobile
    if (isMobileDevice) {
        setTimeout(() => {
            document.querySelectorAll('.leaflet-popup-close-button').forEach(btn => {
                btn.style.width = '36px';
                btn.style.height = '36px';
                btn.style.fontSize = '22px';
                btn.style.lineHeight = '36px';
            });
        }, 2000);
    }
    
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
window.detectMobileDevice = detectMobileDevice;
window.isMobileDevice = false; // Sera mis à jour

console.log("✅ Module main.js chargé - Version optimisée mobile");
