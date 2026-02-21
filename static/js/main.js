// main.js - Version corrigée avec synchronisation parfaite du score et anti-cache
console.log("🎣 Fishing Predictor Pro - Module principal initialisé");

// Variables globales
let currentWeatherData = null;
let isWeatherInitialized = false;
let isMobileDevice = false;
let currentLat = 36.8065;
let currentLon = 10.1815;
let map = null;
let currentMarker = null;

// ===== SOLUTION ANTI-CACHE DÉFINITIVE =====
(function setupNoCache() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options) {
        if (typeof url === 'string' && url.includes('/api/')) {
            // Éviter de dupliquer le paramètre
            if (!url.includes('_=') && !url.includes('refresh=') && !url.includes('nocache=')) {
                const separator = url.includes('?') ? '&' : '?';
                url = `${url}${separator}_=${Date.now()}`;
            }
        }
        return originalFetch.call(this, url, options);
    };
    
    console.log('✅ Anti-cache system activated - Tous les appels API sont frais');
})();

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

// Mettre à jour l'affichage du spot
function updateSpotDisplay(name, lat, lon, distanceKm) {
    // S'assurer que lat et lon sont des nombres
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    
    if (isNaN(latNum) || isNaN(lonNum)) {
        console.error('❌ updateSpotDisplay: coordonnées invalides', { name, lat, lon });
        return;
    }
    
    // Mettre à jour spot-info si présent
    const spotInfo = document.getElementById('spot-info');
    if (spotInfo) {
        spotInfo.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div>
                    <h3 style="margin:0;color:#3b82f6">${escapeHTML(name)}</h3>
                    <div style="color:#94a3b8;font-size:.9rem;margin-top:.25rem">
                        ${latNum.toFixed(4)}, ${lonNum.toFixed(4)}
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
    if (selectedSpotCoords) selectedSpotCoords.textContent = `${latNum.toFixed(4)}, ${lonNum.toFixed(4)}`;
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
        const latNum = parseFloat(savedLat);
        const lonNum = parseFloat(savedLon);
        
        if (!isNaN(latNum) && !isNaN(lonNum)) {
            currentLat = latNum;
            currentLon = lonNum;
            
            if (savedName) {
                updateSpotDisplay(savedName, latNum, lonNum, parseFloat(savedDistance || 0));
                console.log(`🔄 Spot restauré: ${savedName} (${latNum}, ${lonNum})`);
            }
        } else {
            console.warn('⚠️ Coordonnées invalides dans localStorage');
        }
    }
}

// ========== FONCTIONS MÉTÉO ==========

// Charger les données météo pour une position donnée
async function loadWeatherData(lat = currentLat, lon = currentLon) {
    // Conversion et validation des coordonnées
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    
    if (isNaN(latNum) || isNaN(lonNum)) {
        console.error('❌ loadWeatherData: coordonnées invalides', { lat, lon });
        showNotification('Coordonnées météo invalides', 'error');
        return generateFallbackWeather();
    }
    
    console.log(`🌤️ Chargement des données météo pour ${latNum}, ${lonNum}...`);
    
    try {
        const response = await fetch(`/api/current_weather?lat=${latNum}&lon=${lonNum}`);
        
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

// ========== FONCTION PRINCIPALE DE SÉLECTION DE SPOT ==========

/**
 * Fonction universelle de sélection de spot
 * Délègue à FishingDashboard si disponible, sinon fait un fallback manuel
 */
async function selectSpot(lat, lon, name) {
    console.log(`🎯 Sélection du spot : ${name} ${lat} ${lon}`);
    
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    
    if (isNaN(latNum) || isNaN(lonNum)) {
        console.error('❌ Coordonnées invalides:', { lat, lon, name });
        showNotification('Coordonnées du spot invalides', 'error');
        return;
    }
    
    // Sauvegarder la position utilisateur AVANT de la changer
    const userLat = currentLat;
    const userLon = currentLon;
    
    // Calcul précis de la distance
    const distanceKm = calculateDistance(userLat, userLon, latNum, lonNum);
    
    // Mettre à jour la position courante
    currentLat = latNum;
    currentLon = lonNum;
    
    // Sauvegarder dans localStorage pour persistance entre les pages
    localStorage.setItem('currentLat', latNum.toString());
    localStorage.setItem('currentLon', lonNum.toString());
    localStorage.setItem('currentSpotName', name);
    localStorage.setItem('currentSpotDistance', distanceKm.toFixed(1));
    
    // Centrer la carte si elle existe
    if (map && typeof map.setView === 'function') {
        map.setView([latNum, lonNum], 13);
    }
    
    // Mettre à jour l'affichage du spot
    updateSpotDisplay(name, latNum, lonNum, distanceKm);
    
    // --- PRIORITÉ 1: Utiliser FishingDashboard si disponible ---
    if (window.FishingDashboard && typeof window.FishingDashboard.selectSpot === 'function') {
        console.log('✅ Délégation à FishingDashboard.selectSpot');
        
        // Mettre à jour les variables internes de FishingDashboard
        if (typeof FishingDashboard.updateUserPosition === 'function') {
            FishingDashboard.updateUserPosition(latNum, lonNum);
        }
        
        // Appeler la méthode de sélection
        await FishingDashboard.selectSpot(latNum, lonNum, name);
        
        // Forcer le rechargement des données
        await Promise.all([
            FishingDashboard.loadWeatherDataInternal?.(latNum, lonNum),
            FishingDashboard.updatePredictionInternal?.(latNum, lonNum),
            FishingDashboard.updateScientificDataInternal?.(latNum, lonNum),
            FishingDashboard.load24hForecastInternal?.(latNum, lonNum)
        ]);
        
        console.log(`✅ Spot "${name}" entièrement chargé via FishingDashboard`);
        showNotification(`Spot sélectionné : ${name}`, 'success');
        
        // Déclencher l'événement personnalisé
        const spotSelectedEvent = new CustomEvent('spotSelected', {
            detail: { lat: latNum, lon: lonNum, name, distance: distanceKm }
        });
        document.dispatchEvent(spotSelectedEvent);
        
        return;
    }
    
    // --- PRIORITÉ 2: Fallback manuel ---
    console.log('⚠️ FishingDashboard non disponible, fallback manuel...');
    
    // Charger la météo
    console.log(`🔄 Chargement des données météo pour ${name}...`);
    await loadWeatherData(latNum, lonNum);
    
    // Charger la prédiction
    try {
        const response = await fetch(`/api/tunisian_prediction?lat=${latNum}&lon=${lonNum}&species=loup`);
        const data = await response.json();
        
        if (data.status === 'success') {
            const score = data.scores?.final || 0;
            
            // Mettre à jour tous les éléments de score
            const scoreElements = [
                'prediction-score',
                'header-prediction-score',
                'check-score'
            ];
            
            scoreElements.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = score + '%';
            });
            
            // Mettre à jour les sous-scores
            if (data.scores) {
                document.getElementById('mini-env-score') && (document.getElementById('mini-env-score').textContent = data.scores.environmental + '%');
                document.getElementById('mini-beh-score') && (document.getElementById('mini-beh-score').textContent = data.scores.behavioral + '%');
            }
            
            console.log(`✅ Score mis à jour: ${score}%`);
        }
    } catch (error) {
        console.error('❌ Erreur chargement prédiction:', error);
    }
    
    // Forcer la mise à jour du graphique 24h si disponible
    if (typeof window.forcePredictionUpdate === 'function') {
        await window.forcePredictionUpdate(latNum, lonNum);
    }
    
    console.log(`✅ Spot "${name}" chargé (fallback)`);
    showNotification(`Spot sélectionné : ${name}`, 'success');
    
    // Déclencher l'événement
    const spotSelectedEvent = new CustomEvent('spotSelected', {
        detail: { lat: latNum, lon: lonNum, name, distance: distanceKm }
    });
    document.dispatchEvent(spotSelectedEvent);
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

// ========== FONCTION D'URGENCE POUR LA PAGE INDEX ==========

window.forcePredictionUpdate = async function(lat, lon) {
    console.log('🔄 Force prediction update for', lat, lon);
    
    if (window.FishingDashboard) {
        if (typeof FishingDashboard.updatePredictionInternal === 'function') {
            await FishingDashboard.updatePredictionInternal(lat, lon);
        }
        if (typeof FishingDashboard.updateScientificDataInternal === 'function') {
            await FishingDashboard.updateScientificDataInternal(lat, lon);
        }
        if (typeof FishingDashboard.load24hForecastInternal === 'function') {
            await FishingDashboard.load24hForecastInternal(lat, lon);
        }
        console.log('✅ Mise à jour FishingDashboard effectuée');
    }
};

// ========== SYNCHRONISATION FORCÉE AVEC FISHINGDASHBOARD ==========
// Cette fonction force la synchronisation entre main.js et FishingDashboard
window.forceSyncWithFishingDashboard = function(lat, lon, name, distance) {
    if (!window.FishingDashboard) return false;
    
    console.log('🔄 Synchronisation forcée avec FishingDashboard...');
    
    // Méthode 1: Utiliser updateUserPosition si disponible
    if (typeof FishingDashboard.updateUserPosition === 'function') {
        FishingDashboard.updateUserPosition(lat, lon);
    }
    
    // Méthode 2: Mise à jour manuelle des variables
    FishingDashboard.userLat = lat;
    FishingDashboard.userLon = lon;
    FishingDashboard.selectedSpot = { 
        lat: lat, 
        lon: lon, 
        name: name,
        distance: distance 
    };
    
    // Méthode 3: Forcer le rechargement des données
    if (typeof FishingDashboard.loadWeatherDataInternal === 'function') {
        FishingDashboard.loadWeatherDataInternal(lat, lon);
    }
    if (typeof FishingDashboard.updatePredictionInternal === 'function') {
        FishingDashboard.updatePredictionInternal(lat, lon);
    }
    if (typeof FishingDashboard.updateScientificDataInternal === 'function') {
        FishingDashboard.updateScientificDataInternal(lat, lon);
    }
    if (typeof FishingDashboard.load24hForecastInternal === 'function') {
        FishingDashboard.load24hForecastInternal(lat, lon);
    }
    
    // Méthode 4: Centrer la carte
    if (FishingDashboard.map && typeof FishingDashboard.map.setView === 'function') {
        FishingDashboard.map.setView([lat, lon], 13);
    }
    
    console.log(`✅ FishingDashboard synchronisé: (${FishingDashboard.userLat}, ${FishingDashboard.userLon})`);
    return true;
};

// ========== CORRECTION DÉFINITIVE POUR LA SYNCHRONISATION ==========
(function fixSpotSelection() {
    console.log('🔧 Application de la correction définitive selectSpot...');
    
    // Sauvegarder l'ancienne fonction
    const originalSelectSpot = window.selectSpot;
    
    // Nouvelle fonction qui inclut la synchronisation
    window.selectSpot = async function(lat, lon, name) {
        await originalSelectSpot(lat, lon, name);
        
        // Forcer la synchronisation avec FishingDashboard
        const latNum = parseFloat(lat);
        const lonNum = parseFloat(lon);
        const distanceKm = calculateDistance(currentLat, currentLon, latNum, lonNum);
        
        window.forceSyncWithFishingDashboard(latNum, lonNum, name, distanceKm);
        
        // Forcer la mise à jour des variables globales
        window.currentLat = latNum;
        window.currentLon = lonNum;
    };
    
    console.log('✅ Correction définitive appliquée!');
    console.log('📝 Nouvelle fonction selectSpot avec synchronisation forcée');
})();

// ========== INITIALISATION ==========

document.addEventListener('DOMContentLoaded', function() {
    console.log("📄 DOM chargé - Initialisation de l'application");
    
    detectMobileDevice();
    initBackToTop();
    restoreLastSpot();
    initWeather();
    
    // Synchroniser avec localStorage au chargement
    const savedLat = localStorage.getItem('currentLat');
    const savedLon = localStorage.getItem('currentLon');
    const savedName = localStorage.getItem('currentSpotName');
    
    if (savedLat && savedLon && savedName) {
        window.currentLat = parseFloat(savedLat);
        window.currentLon = parseFloat(savedLon);
        
        // Forcer la synchronisation avec FishingDashboard
        setTimeout(() => {
            window.forceSyncWithFishingDashboard(
                window.currentLat, 
                window.currentLon, 
                savedName,
                localStorage.getItem('currentSpotDistance') || 0
            );
        }, 1000);
    }
    
    // Écouter les clics sur les boutons de sélection de spot
    document.addEventListener('click', function(e) {
        const selectSpotBtn = e.target.closest('[data-select-spot]');
        if (selectSpotBtn) {
            const lat = parseFloat(selectSpotBtn.dataset.lat);
            const lon = parseFloat(selectSpotBtn.dataset.lon);
            const name = selectSpotBtn.dataset.name || 'Spot';
            selectSpot(lat, lon, name);
        }
    });
    
    console.log("✅ Application initialisée - Fonctions de spot disponibles sur toutes les pages");
});

// ========== INTERVALLE DE SYNCHRONISATION ==========
// Vérifier et synchroniser toutes les 30 secondes
setInterval(function() {
    const savedLat = localStorage.getItem('currentLat');
    const savedLon = localStorage.getItem('currentLon');
    
    if (savedLat && savedLon && window.FishingDashboard) {
        const savedLatNum = parseFloat(savedLat);
        const savedLonNum = parseFloat(savedLon);
        
        // Si les variables sont désynchronisées, forcer la mise à jour
        if (window.FishingDashboard.userLat !== savedLatNum || 
            window.FishingDashboard.userLon !== savedLonNum) {
            
            console.log('🔄 Désynchronisation détectée, correction automatique...');
            window.forceSyncWithFishingDashboard(
                savedLatNum, 
                savedLonNum, 
                localStorage.getItem('currentSpotName') || 'Spot',
                localStorage.getItem('currentSpotDistance') || 0
            );
        }
    }
}, 30000);

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
window.isMobileDevice = isMobileDevice;
window.forceSyncWithFishingDashboard = forceSyncWithFishingDashboard;

console.log("✅ Module main.js chargé - Fonctions de sélection de spot disponibles GLOBALEMENT");