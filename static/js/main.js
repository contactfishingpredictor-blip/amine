// main.js - Version complète avec fonctions de sélection de spot pour TOUTES les pages
console.log("🎣 Fishing Predictor Pro - Module principal initialisé");

// Variables globales
let currentWeatherData = null;
let isWeatherInitialized = false;
let isMobileDevice = false;
let currentLat = 36.8065;
let currentLon = 10.1815;
let map = null;
let currentMarker = null;

// Détection mobile
function detectMobileDevice() {
    isMobileDevice = (window.innerWidth <= 768) || 
                     ('ontouchstart' in window) || 
                     (navigator.maxTouchPoints > 0) ||
                     (navigator.msMaxTouchPoints > 0);
    console.log(`📱 Détection mobile: ${isMobileDevice ? 'OUI' : 'NON'}`);
    return isMobileDevice;
}

// ========== FONCTIONS DE CARTE ET SPOTS ==========

// Calcul de distance précis (Formule de Haversine)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371; // Rayon de la Terre en km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Sélection de spot (UNIVERSEL - utilisable sur toutes les pages)
async function selectSpot(event, lat, lon, name) {
    try {
        console.log('🎯 Sélection du spot :', name, lat, lon);
        
        // Sauvegarder la position utilisateur AVANT de la changer
        const userLat = currentLat;
        const userLon = currentLon;
        
        // Calcul précis de la distance
        const distanceKm = calculateDistance(userLat, userLon, lat, lon);
        
        // Mettre à jour la position courante
        currentLat = lat;
        currentLon = lon;
        
        // Sauvegarder dans localStorage pour persistance entre les pages
        localStorage.setItem('currentLat', lat);
        localStorage.setItem('currentLon', lon);
        localStorage.setItem('currentSpotName', name);
        localStorage.setItem('currentSpotDistance', distanceKm.toFixed(1));
        
        // Centrer la carte si elle existe
        if (map && typeof map.setView === 'function') {
            map.setView([lat, lon], 13);
        }
        
        // Mettre à jour l'affichage du spot si les éléments existent
        updateSpotDisplay(name, lat, lon, distanceKm);
        
        // Rafraîchir les données météo pour ce spot
        loadWeatherData(lat, lon);
        
        // Déclencher un événement personnalisé pour informer les autres scripts
        const spotSelectedEvent = new CustomEvent('spotSelected', {
            detail: { lat, lon, name, distance: distanceKm }
        });
        document.dispatchEvent(spotSelectedEvent);
        
        showNotification(`Spot sélectionné : ${name}`, 'success');
    } catch (error) {
        console.error('❌ Erreur selectSpot:', error);
        showNotification('Erreur lors de la sélection', 'error');
    }
}

// Mettre à jour l'affichage du spot
function updateSpotDisplay(name, lat, lon, distanceKm) {
    // Mettre à jour spot-info si présent
    const spotInfo = document.getElementById('spot-info');
    if (spotInfo) {
        spotInfo.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <h3 style="margin:0;color:#3b82f6">${escapeHTML(name)}</h3>
                    <div style="color:#94a3b8;font-size:.9rem;margin-top:.25rem">
                        ${lat.toFixed(4)}, ${lon.toFixed(4)}
                    </div>
                </div>
                <div style="background:#1e293b;padding:0.5rem 1rem;border-radius:20px;text-align:center">
                    <div style="color:#94a3b8;font-size:.8rem">Distance</div>
                    <div style="font-weight:700;font-size:1.3rem;color:#f8fafc">${distanceKm.toFixed(1)} km</div>
                </div>
            </div>
        `;
    }
    
    // Mettre à jour distance-info si présent
    const distanceInfo = document.getElementById('distance-info');
    if (distanceInfo) {
        distanceInfo.innerHTML = `
            <div style="display:flex;align-items:center;gap:.75rem;color:white;padding:.75rem 1rem;background:#0f172a;border-radius:8px;border-left:4px solid #3b82f6">
                <i class="fas fa-ship" style="color:#3b82f6;font-size:1.2rem"></i>
                <div>
                    <span style="font-weight:600">${distanceKm.toFixed(1)} km</span>
                    <span style="color:#94a3b8;margin-left:0.5rem">du spot sélectionné</span>
                </div>
            </div>
        `;
    }
    
    // Mettre à jour d'autres éléments potentiels
    const selectedSpotName = document.getElementById('selected-spot-name');
    if (selectedSpotName) selectedSpotName.textContent = name;
    
    const selectedSpotCoords = document.getElementById('selected-spot-coords');
    if (selectedSpotCoords) selectedSpotCoords.textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
}

// Échapper le HTML pour éviter les injections XSS
function escapeHTML(str) {
    return String(str).replace(/[&<>"]/g, c => ({ 
        '&':'&amp;', 
        '<':'&lt;', 
        '>':'&gt;', 
        '"':'&quot;' 
    })[c] || c);
}

// Restaurer le dernier spot sélectionné depuis localStorage
function restoreLastSpot() {
    const savedLat = localStorage.getItem('currentLat');
    const savedLon = localStorage.getItem('currentLon');
    const savedName = localStorage.getItem('currentSpotName');
    const savedDistance = localStorage.getItem('currentSpotDistance');
    
    if (savedLat && savedLon) {
        currentLat = parseFloat(savedLat);
        currentLon = parseFloat(savedLon);
        
        if (savedName) {
            updateSpotDisplay(savedName, currentLat, currentLon, parseFloat(savedDistance || 0));
            console.log(`🔄 Spot restauré: ${savedName} (${currentLat}, ${currentLon})`);
        }
    }
}

// ========== FONCTIONS MÉTÉO ==========

// Charger les données météo pour une position donnée
async function loadWeatherData(lat = currentLat, lon = currentLon) {
    console.log(`🌤️ Chargement des données météo pour ${lat}, ${lon}...`);
    
    try {
        const response = await fetch(`/api/current_weather?lat=${lat}&lon=${lon}`);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
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
        showNotification('Impossible de charger la météo, données simulées utilisées', 'warning');
        
        const fallbackWeather = generateFallbackWeather();
        updateWeatherDisplay(fallbackWeather);
        return fallbackWeather;
    }
}

// Mettre à jour l'affichage de la météo
function updateWeatherDisplay(weatherData) {
    if (!weatherData) return;
    
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
    
    Object.entries(elementsToUpdate).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
    
    const windIconElement = document.getElementById('weather-icon');
    if (windIconElement) {
        windIconElement.textContent = weatherData.wind_direction_icon || '⬆️';
    }
    
    updateWindSafetyBadges(weatherData);
    window.weatherDataCache = weatherData;
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
    const hour = new Date().getHours();
    const temp = 20 + Math.sin(hour * Math.PI / 12) * 5;
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
        wind_offshore: false,
        wind_onshore: true
    };
}

// Initialiser la météo
function initWeather() {
    if (isWeatherInitialized) return;
    
    const hasWeatherElements = document.getElementById('temperature') || 
                               document.getElementById('weather-condition') ||
                               document.getElementById('wind-speed');
    
    if (hasWeatherElements) {
        loadWeatherData();
        setInterval(() => loadWeatherData(), 5 * 60 * 1000);
        isWeatherInitialized = true;
    }
}

// ========== NOTIFICATIONS ==========

function showNotification(message, type = 'info') {
    // Supprimer les notifications existantes
    document.querySelectorAll('.notification').forEach(notif => notif.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    
    notification.innerHTML = `
        <i class="fas fa-${icons[type] || 'info-circle'}" style="font-size: 1.2rem"></i>
        <span style="flex:1">${message}</span>
        <button class="close-notification" onclick="this.parentElement.remove()">×</button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 10);
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ========== ANIMATION VENT ==========

window.toggleWindAnimation = function() {
    console.log("💨 Toggle animation du vent");
    if (typeof window.toggleWindLayer === 'function') {
        window.toggleWindLayer();
    } else {
        showNotification('Animation du vent disponible sur la page principale', 'info');
    }
};

// ========== BACK TO TOP ==========

function initBackToTop() {
    if (document.getElementById('back-to-top')) return;
    
    const btn = document.createElement('div');
    btn.id = 'back-to-top';
    btn.className = 'back-to-top';
    btn.innerHTML = '<i class="fas fa-arrow-up"></i>';
    btn.style.display = 'none';
    
    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    
    document.body.appendChild(btn);
    
    window.addEventListener('scroll', () => {
        btn.style.display = window.scrollY > 300 ? 'flex' : 'none';
    });
}

// ========== INITIALISATION ==========

document.addEventListener('DOMContentLoaded', function() {
    console.log("📄 DOM chargé - Initialisation de l'application");
    
    detectMobileDevice();
    initBackToTop();
    restoreLastSpot();
    initWeather();
    
    // Écouter les clics sur les boutons de sélection de spot
    document.addEventListener('click', function(e) {
        const selectSpotBtn = e.target.closest('[data-select-spot]');
        if (selectSpotBtn) {
            const lat = parseFloat(selectSpotBtn.dataset.lat);
            const lon = parseFloat(selectSpotBtn.dataset.lon);
            const name = selectSpotBtn.dataset.name || 'Spot';
            selectSpot(e, lat, lon, name);
        }
    });
    
    console.log("✅ Application initialisée - Fonctions de spot disponibles sur toutes les pages");
});

// ========== EXPOSITION GLOBALE ==========

window.selectSpot = selectSpot;
window.calculateDistance = calculateDistance;
window.loadWeatherData = loadWeatherData;
window.updateWeatherDisplay = updateWeatherDisplay;
window.initWeather = initWeather;
window.showNotification = showNotification;
window.toggleWindAnimation = toggleWindAnimation;
window.escapeHTML = escapeHTML;
window.currentLat = currentLat;
window.currentLon = currentLon;
window.isMobileDevice = isMobileDevice; // ✅ AJOUT : exposition de la variable globale

console.log("✅ Module main.js chargé - Fonctions de sélection de spot disponibles GLOBALEMENT");
