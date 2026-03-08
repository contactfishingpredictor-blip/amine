// main.js - Version FINALE avec analyse scientifique des plages horaires (SANS SCORES)
console.log("🎣 Fishing Predictor Pro - Module principal initialisé");

// ===== VARIABLES GLOBALES =====
let currentWeatherData = null;
let isWeatherInitialized = false;
let isMobileDevice = false;
let currentLat = 36.8065;
let currentLon = 10.1815;
let map = null;
let currentMarker = null;
let selectedSpotMarker = null;
let modalContentCache = null;

// ===== VARIABLES DE SYNCHRONISATION =====
window.lastChartData = null;
window.lastSpotData = null;
let modalOpen = false;
let favorites = [];

// ===== GESTION DU CACHE CLIENT =====
const CACHE_DURATION = 3 * 60 * 60 * 1000;

// ===== GESTION DE L'ESPÈCE =====
let currentSpecies = 'loup';
console.log('🐟 Espèce par défaut: loup');
const savedSpecies = localStorage.getItem('fishingLastSpecies');
if (savedSpecies) currentSpecies = savedSpecies;

// ===== FONCTIONS UTILITAIRES GLOBALES =====
function formatHourToTime(hourStr) {
    if (!hourStr) return '--:--';
    if (hourStr.includes('h')) {
        const parts = hourStr.split('h');
        const hour = parts[0].padStart(2, '0');
        const minute = parts[1] ? parts[1].padStart(2, '0') : '00';
        return `${hour}:${minute}`;
    }
    return hourStr;
}

function formatTime(minutes) {
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h${mins}` : `${hours}h`;
}

// ============================================
// VERSION SCIENTIFIQUE DES PLAGES OPTIMALES - SANS SCORES
// ============================================
function extractOptimalRanges(scores, hours, percentile = 70) {
    if (!scores || !hours || scores.length === 0 || hours.length === 0) return [];
    
    const sortedScores = [...scores].sort((a, b) => a - b);
    const threshold = sortedScores[Math.floor(scores.length * (percentile / 100))];
    
    let ranges = [];
    let currentRange = null;
    
    for (let i = 0; i < scores.length; i++) {
        if (scores[i] >= threshold) {
            if (!currentRange) {
                currentRange = { start: hours[i], end: hours[i], scores: [scores[i]] };
            } else {
                currentRange.end = hours[i];
                currentRange.scores.push(scores[i]);
            }
        } else {
            if (currentRange) {
                currentRange.avgScore = Math.round(currentRange.scores.reduce((a, b) => a + b, 0) / currentRange.scores.length);
                ranges.push(currentRange);
                currentRange = null;
            }
        }
    }
    if (currentRange) {
        currentRange.avgScore = Math.round(currentRange.scores.reduce((a, b) => a + b, 0) / currentRange.scores.length);
        ranges.push(currentRange);
    }
    return ranges;
}

function displayOptimalRanges(ranges) {
    const container = document.getElementById('optimal-ranges-list');
    if (!container) return;
    
    // Récupérer les facteurs scientifiques actuels
    const moonPhase = document.getElementById('moon-phase')?.textContent || '';
    const pressure = parseFloat(document.getElementById('pressure')?.textContent) || 1015;
    const pressureTrend = document.getElementById('pressure-trend-icon')?.textContent || '➡️';
    const currentHour = new Date().getHours();
    
    if (!ranges || ranges.length === 0) {
        const bestHour = document.getElementById('best-period')?.textContent || '--h';
        
        // Calculer la qualité sans afficher de score
        let qualityIcon = '🎯';
        let qualityText = '';
        let borderColor = '#3b82f6';
        const bestHourNum = parseInt(bestHour);
        
        // Déterminer la qualité basée sur les facteurs
        if (bestHourNum >= 4 && bestHourNum <= 7) {
            qualityIcon = '🌅';
            qualityText = 'Aube - Moment idéal';
            borderColor = '#10b981';
        } else if (bestHourNum >= 17 && bestHourNum <= 20) {
            qualityIcon = '🌆';
            qualityText = 'Crépuscule - Excellent';
            borderColor = '#10b981';
        } else if (bestHourNum >= 21 || bestHourNum <= 4) {
            if (moonPhase.includes('Pleine Lune')) {
                qualityIcon = '🌕';
                qualityText = 'Pleine Lune - Très bon';
                borderColor = '#3b82f6';
            } else if (moonPhase.includes('Nouvelle Lune')) {
                qualityIcon = '🌑';
                qualityText = 'Nouvelle Lune - Bon';
                borderColor = '#3b82f6';
            } else {
                qualityIcon = '🌙';
                qualityText = 'Nuit - Potentiel';
                borderColor = '#f59e0b';
            }
        } else if (bestHourNum >= 11 && bestHourNum <= 14) {
            qualityIcon = '☀️';
            qualityText = 'Midi - Activité réduite';
            borderColor = '#ef4444';
        } else {
            qualityIcon = '⏰';
            qualityText = 'Conditions standard';
            borderColor = '#94a3b8';
        }
        
        // Ajouter info pression
        if (pressureTrend === '📉' && pressure < 1020) {
            qualityText += ' · Pression en baisse ✅';
        } else if (pressureTrend === '📈' && pressure > 1020) {
            qualityText += ' · Pression en hausse ⚠️';
        }
        
        const tooltipText = qualityText;
        
        container.innerHTML = `
            <div class="optimal-range-item" style="border-left-color: ${borderColor};" title="${tooltipText}">
                <div class="optimal-range-time">
                    <span class="optimal-range-icon">${qualityIcon}</span>
                    <span style="color:white; font-weight:600;">${formatHourToTime(bestHour)}</span>
                    <span style="color:#94a3b8; font-size:0.9rem; margin-left:0.5rem;">${qualityText.split('·')[0]}</span>
                </div>
                <div class="optimal-range-badge" style="background: ${borderColor}; font-size:0.8rem; padding:0.2rem 0.8rem;">
                    Recommandé
                </div>
            </div>
        `;
        return;
    }
    
    let html = '';
    ranges.forEach((range) => {
        const startTime = formatHourToTime(range.start);
        const endTime = formatHourToTime(range.end);
        const startHour = parseInt(range.start);
        const endHour = parseInt(range.end);
        
        // Calculer la qualité sans afficher de score
        let qualityIcon = '🎣';
        let qualityText = '';
        let borderColor = '#3b82f6';
        
        // 1. Facteur crépusculaire
        if ((startHour >= 4 && endHour <= 7) || (startHour >= 17 && endHour <= 20)) {
            qualityIcon = '🌅';
            qualityText = 'Crépuscule';
            borderColor = '#10b981';
        }
        
        // 2. Facteur nuit et lune
        else if (startHour >= 21 || endHour <= 4) {
            if (moonPhase.includes('Pleine Lune')) {
                qualityIcon = '🌕';
                qualityText = 'Pleine Lune';
                borderColor = '#3b82f6';
            } else if (moonPhase.includes('Nouvelle Lune')) {
                qualityIcon = '🌑';
                qualityText = 'Nouvelle Lune';
                borderColor = '#3b82f6';
            } else if (moonPhase.includes('Gibbeuse')) {
                qualityIcon = '🌔';
                qualityText = 'Lune gibbeuse';
                borderColor = '#f59e0b';
            } else {
                qualityIcon = '🌙';
                qualityText = 'Nuit';
                borderColor = '#94a3b8';
            }
        }
        
        // 3. Facteur heure
        else if (startHour >= 5 && startHour <= 7) {
            qualityIcon = '⏰';
            qualityText = 'Aube';
            borderColor = '#10b981';
        } else if (startHour >= 11 && startHour <= 14) {
            qualityIcon = '☀️';
            qualityText = 'Midi';
            borderColor = '#ef4444';
        } else if (startHour >= 17 && startHour <= 19) {
            qualityIcon = '🌆';
            qualityText = 'Crépuscule';
            borderColor = '#10b981';
        } else {
            qualityIcon = '⏳';
            qualityText = 'Journée';
            borderColor = '#94a3b8';
        }
        
        // Ajouter info pression si pertinente
        let pressureInfo = '';
        if (pressureTrend === '📉' && pressure < 1020) {
            pressureInfo = ' · Pression en baisse';
        } else if (pressureTrend === '📈' && pressure > 1020) {
            pressureInfo = ' · Pression en hausse';
        }
        
        const tooltipText = `${qualityText}${pressureInfo}`;
        
        html += `
            <div class="optimal-range-item" style="border-left-color: ${borderColor};" title="${tooltipText}">
                <div class="optimal-range-time">
                    <span class="optimal-range-icon">${qualityIcon}</span>
                    <span style="color:white; font-weight:600;">${startTime}</span>
                    <span style="color:#94a3b8;">→</span>
                    <span style="color:white; font-weight:600;">${endTime}</span>
                </div>
                <div class="optimal-range-badge" style="background: ${borderColor}; font-size:0.75rem; padding:0.2rem 0.6rem;">
                    ${qualityText}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateFishCountFromScore(score) {
    const fishCount = document.getElementById('current-fish-count');
    if (!fishCount) return;
    const scoreNum = parseInt(score);
    const now = new Date();
    const hour = now.getHours();
    const month = now.getMonth() + 1;
    
    let seasonalFactor = 1.0;
    if (month >= 4 && month <= 6) seasonalFactor = 1.3;
    else if (month >= 9 && month <= 11) seasonalFactor = 1.2;
    else if (month >= 12 || month <= 2) seasonalFactor = 0.7;
    
    let hourlyFactor = 1.0;
    if (hour >= 5 && hour <= 8) hourlyFactor = 1.4;
    else if (hour >= 17 && hour <= 20) hourlyFactor = 1.5;
    else if (hour >= 10 && hour <= 15) hourlyFactor = 0.8;
    else if (hour >= 22 || hour <= 4) hourlyFactor = 0.6;
    
    const depth = parseFloat(document.getElementById('mini-depth')?.textContent) || 10;
    let depthFactor = depth > 20 ? 1.2 : depth < 5 ? 0.7 : 1.0;
    
    const waterTemp = parseFloat(document.getElementById('water-temp')?.textContent) || 18;
    let tempFactor = 1.0;
    if (waterTemp >= 18 && waterTemp <= 22) tempFactor = 1.3;
    else if (waterTemp >= 15 && waterTemp <= 25) tempFactor = 1.1;
    else if (waterTemp < 10 || waterTemp > 28) tempFactor = 0.5;
    
    const windSpeed = parseFloat(document.getElementById('wind-speed')?.textContent) || 10;
    let windFactor = 1.0;
    if (windSpeed < 10) windFactor = 0.9;
    else if (windSpeed >= 10 && windSpeed <= 20) windFactor = 1.2;
    else if (windSpeed > 20 && windSpeed <= 30) windFactor = 0.8;
    else if (windSpeed > 30) windFactor = 0.4;
    
    const moonPhase = document.getElementById('moon-phase')?.textContent || '';
    let moonFactor = 1.0;
    if (moonPhase.includes('Nouvelle Lune')) moonFactor = 1.3;
    else if (moonPhase.includes('Pleine Lune')) moonFactor = 1.2;
    else if (moonPhase.includes('Gibbeuse')) moonFactor = 1.1;
    
    const pressure = parseFloat(document.getElementById('pressure')?.textContent) || 1015;
    const pressureTrend = document.getElementById('pressure-trend-icon')?.textContent || '➡️';
    let pressureFactor = 1.0;
    if (pressure < 1000) pressureFactor = 1.3;
    else if (pressure >= 1000 && pressure <= 1015) pressureFactor = 1.2;
    else if (pressure > 1025) pressureFactor = 0.6;
    if (pressureTrend === '📉') pressureFactor *= 1.2;
    else if (pressureTrend === '📈') pressureFactor *= 0.7;
    
    const totalFactor = Math.pow(seasonalFactor * hourlyFactor * depthFactor * tempFactor * windFactor * moonFactor * pressureFactor, 1/7);
    let baseFish = 50 + (scoreNum - 50) * 3;
    let estimated = Math.round(baseFish * totalFactor);
    
    if (scoreNum >= 95) estimated = Math.round(estimated * 1.3);
    else if (scoreNum >= 90) estimated = Math.round(estimated * 1.2);
    else if (scoreNum >= 85) estimated = Math.round(estimated * 1.1);
    else if (scoreNum <= 40) estimated = Math.round(estimated * 0.6);
    else if (scoreNum <= 30) estimated = Math.round(estimated * 0.4);
    
    estimated = Math.min(350, Math.max(20, Math.round(estimated * (1 + (Math.random() * 0.06 - 0.03)))));
    fishCount.textContent = estimated;
    
    if (estimated >= 250) fishCount.style.color = '#10b981';
    else if (estimated >= 150) fishCount.style.color = '#3b82f6';
    else if (estimated >= 80) fishCount.style.color = '#f59e0b';
    else fishCount.style.color = '#ef4444';
}

// ===== SOLUTION ANTI-CACHE =====
(function setupNoCache() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        if (typeof url === 'string' && url.includes('/api/') && !url.includes('_=')) {
            const separator = url.includes('?') ? '&' : '?';
            url = `${url}${separator}_=${Date.now()}`;
        }
        return originalFetch.call(this, url, options);
    };
    console.log('✅ Anti-cache system activated');
})();

// Détection mobile
function detectMobileDevice() {
    isMobileDevice = (window.innerWidth <= 768) || ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
    return isMobileDevice;
}

// ===== FONCTIONS DE GESTION DES FAVORIS =====
async function loadFavorites() {
    try {
        const response = await fetch('/api/favorites');
        const data = await response.json();
        if (data.status === 'success') {
            favorites = data.favorites || [];
            console.log('⭐ Favoris chargés:', favorites.length);
        }
    } catch (error) {
        console.error('Erreur chargement favoris:', error);
    }
}

async function saveFavorite(spot) {
    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: spot.name,
                lat: spot.lat,
                lon: spot.lon,
                type: 'custom',
                description: spot.description || 'Spot favori'
            })
        });
        const data = await response.json();
        if (data.status === 'success') {
            showNotification('⭐ Spot ajouté aux favoris', 'success');
            await loadFavorites();
            return true;
        }
    } catch (error) {
        console.error('Erreur sauvegarde favori:', error);
        showNotification('❌ Erreur lors de la sauvegarde', 'error');
    }
    return false;
}

async function deleteFavorite(spotId) {
    try {
        const response = await fetch(`/api/favorites?id=${spotId}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            showNotification('⭐ Spot retiré des favoris', 'info');
            await loadFavorites();
            return true;
        }
    } catch (error) {
        console.error('Erreur suppression favori:', error);
        showNotification('❌ Erreur lors de la suppression', 'error');
    }
    return false;
}

function isSpotFavorite(lat, lon) {
    return favorites.some(f => Math.abs(f.lat - lat) < 0.0001 && Math.abs(f.lon - lon) < 0.0001);
}

function getFavoriteId(lat, lon) {
    const favorite = favorites.find(f => Math.abs(f.lat - lat) < 0.0001 && Math.abs(f.lon - lon) < 0.0001);
    return favorite ? favorite.id : null;
}

// ===== FONCTIONS DE CARTE =====
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function createSelectedSpotMarker(lat, lon, name, isFavorite = false) {
    const color = isFavorite ? '#f59e0b' : '#ef4444';
    const pulseColor = isFavorite ? 'rgba(245,158,11,0.8)' : 'rgba(239,68,68,0.8)';
    
    const markerHtml = `
        <div style="position: relative; width: 60px; height: 60px;">
            <div style="position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); 
                 background: ${color}; width: 24px; height: 24px; border-radius: 50%; 
                 border: 3px solid white; box-shadow: 0 0 20px ${pulseColor}; 
                 animation: pulse-selected 1.5s infinite;"></div>
            <div style="position: absolute; bottom: 30px; left: 50%; transform: translateX(-50%); 
                 background: ${color}; color: white; padding: 4px 8px; border-radius: 16px; 
                 font-size: 11px; font-weight: bold; white-space: nowrap; 
                 box-shadow: 0 2px 10px rgba(0,0,0,0.3);">
                <i class="fas fa-${isFavorite ? 'star' : 'map-pin'}" style="margin-right: 3px;"></i>${name}
            </div>
        </div>
    `;
    
    return L.divIcon({ 
        html: markerHtml, 
        className: 'selected-spot-marker', 
        iconSize: [60, 60],
        iconAnchor: [30, 48], // Centre du cercle (24px de diamètre, centré à 30,48)
        popupAnchor: [0, -48] 
    });
}

function createTunisianSpotMarker(spot) {
    const colors = { 'port': '#3b82f6', 'plage': '#10b981', 'rocheux': '#f59e0b', 'custom': '#8b5cf6' };
    const color = colors[spot.type] || '#6b7280';
    
    const markerHtml = `<div style="background: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>`;
    
    return L.divIcon({ 
        html: markerHtml, 
        className: 'tunisian-spot-marker', 
        iconSize: [18, 18],
        iconAnchor: [9, 9] // Centre exact du cercle
    });
}

async function calculateDistanceToSpot(lat, lon) {
    try {
        const response = await fetch(`/api/distance_calculation?lat1=${currentLat}&lon1=${currentLon}&lat2=${lat}&lon2=${lon}`);
        const data = await response.json();
        if (data.status === 'success') {
            const distanceKm = parseFloat(data.distance_km);
            const travelTimeMinutes = data.travel_time_minutes || Math.round((distanceKm / 50) * 60);
            const spotDistanceEl = document.getElementById('spot-distance');
            if (spotDistanceEl) {
                spotDistanceEl.style.display = 'block';
                if (distanceKm < 0.1) {
                    spotDistanceEl.innerHTML = `<span style="color:#94a3b8">📍 Vous êtes ici</span>`;
                } else {
                    spotDistanceEl.innerHTML = `📍 ${distanceKm.toFixed(1)} km <span style="font-size:.8rem; color:#94a3b8">(${formatTime(travelTimeMinutes)})</span>`;
                }
            }
        }
    } catch(error) {
        console.error('Erreur calcul distance:', error);
    }
}

function updateSpotDisplay(name, lat, lon, distanceKm, isFavorite = false) {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (isNaN(latNum) || isNaN(lonNum)) return;
    const spotInfo = document.getElementById('spot-info');
    if (spotInfo) {
        const starIcon = isFavorite ? '⭐' : '☆';
        const favoriteColor = isFavorite ? '#f59e0b' : '#94a3b8';
        spotInfo.innerHTML = `
            <div style="display:flex; flex-direction:column; background: linear-gradient(135deg, #1e293b, #0f172a); padding: 1rem; border-radius: 12px; border-left: 4px solid ${isFavorite ? '#f59e0b' : '#ef4444'};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <h3 style="margin:0; color:${isFavorite ? '#f59e0b' : '#ef4444'}; display: flex; align-items: center; gap: 8px;">
                        <i class="fas fa-${isFavorite ? 'star' : 'map-marker-alt'}"></i> ${escapeHTML(name)}
                    </h3>
                    <button onclick="window.toggleFavorite(${latNum}, ${lonNum}, '${name}')" 
                        style="background:transparent; border:none; color:${favoriteColor}; font-size:1.5rem; cursor:pointer; padding:0.5rem;" 
                        title="${isFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}">
                        ${starIcon}
                    </button>
                </div>
                <div style="color:#94a3b8; font-size:.9rem; display:flex; gap:1rem;">
                    <span><i class="fas fa-globe"></i> ${latNum.toFixed(4)}, ${lonNum.toFixed(4)}</span>
                    <span><i class="fas fa-route"></i> ${distanceKm.toFixed(1)} km</span>
                </div>
            </div>
        `;
    }
    const selectedSpotName = document.getElementById('selected-spot-name');
    if (selectedSpotName) {
        selectedSpotName.textContent = name;
        selectedSpotName.style.color = isFavorite ? '#f59e0b' : '#ef4444';
        selectedSpotName.style.fontWeight = 'bold';
    }
}

function escapeHTML(str) {
    return String(str).replace(/[&<>"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' })[c] || c);
}

function restoreLastSpot() {
    const savedLat = localStorage.getItem('currentLat');
    const savedLon = localStorage.getItem('currentLon');
    const savedName = localStorage.getItem('currentSpotName');
    const savedDistance = localStorage.getItem('currentSpotDistance');
    if (savedLat && savedLon && savedName) {
        const latNum = parseFloat(savedLat);
        const lonNum = parseFloat(savedLon);
        if (!isNaN(latNum) && !isNaN(lonNum)) {
            currentLat = latNum;
            currentLon = lonNum;
            const isFav = isSpotFavorite(latNum, lonNum);
            updateSpotDisplay(savedName, latNum, lonNum, parseFloat(savedDistance || 0), isFav);
            if (window.map) {
                window.map.setView([latNum, lonNum], 13, { animate: true, duration: 1 });
                if (selectedSpotMarker) window.map.removeLayer(selectedSpotMarker);
                selectedSpotMarker = L.marker([latNum, lonNum], { 
                    icon: createSelectedSpotMarker(latNum, lonNum, savedName, isFav),
                    zIndexOffset: 1000 
                }).addTo(window.map);
                console.log('📍 Spot restauré:', savedName);
            }
        }
    }
}

window.toggleFavorite = async function(lat, lon, name) {
    const isFav = isSpotFavorite(lat, lon);
    if (isFav) {
        const favId = getFavoriteId(lat, lon);
        if (favId) await deleteFavorite(favId);
    } else {
        await saveFavorite({ lat, lon, name });
    }
    const distanceKm = calculateDistance(currentLat, currentLon, lat, lon);
    const isNowFav = isSpotFavorite(lat, lon);
    updateSpotDisplay(name, lat, lon, distanceKm, isNowFav);
    if (selectedSpotMarker && window.map) {
        window.map.removeLayer(selectedSpotMarker);
        selectedSpotMarker = L.marker([lat, lon], { 
            icon: createSelectedSpotMarker(lat, lon, name, isNowFav),
            zIndexOffset: 1000 
        }).addTo(window.map);
    }
};

// ===== FONCTIONS MÉTÉO =====
async function loadWeatherData(lat = currentLat, lon = currentLon) {
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (isNaN(latNum) || isNaN(lonNum)) return generateFallbackWeather();
    try {
        const response = await fetch(`/api/current_weather?lat=${latNum}&lon=${lonNum}`);
        const data = await response.json();
        if (data.status === 'success') {
            currentWeatherData = data.weather;
            updateWeatherDisplay(currentWeatherData);
            return currentWeatherData;
        }
    } catch (error) {
        console.error('Erreur météo:', error);
        return generateFallbackWeather();
    }
}

function updateWeatherDisplay(weatherData) {
    if (!weatherData) return;
    const elements = {
        'temperature': `${weatherData.temperature?.toFixed(1) || '--'}°C`,
        'weather-condition': weatherData.condition_fr || weatherData.condition || '--',
        'wind-speed': `${weatherData.wind_speed?.toFixed(1) || '--'} km/h`,
        'wind-direction': weatherData.wind_direction_name || '--',
        'weather-pressure': `${weatherData.pressure || '--'} hPa`
    };
    Object.entries(elements).forEach(([id, value]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    });
}

function generateFallbackWeather() {
    return { temperature: 22, condition: 'Ensoleillé', condition_fr: 'Ensoleillé', wind_speed: 12, wind_direction_name: 'Nord', pressure: 1015 };
}

function initWeather() {
    if (isWeatherInitialized) return;
    if (document.getElementById('temperature')) {
        loadWeatherData();
        setInterval(() => loadWeatherData(), 5 * 60 * 1000);
        isWeatherInitialized = true;
    }
}

// ===== FONCTION PRINCIPALE DE SÉLECTION DE SPOT (CORRIGÉE) =====
async function selectSpot(lat, lon, name) {
    console.log(`🎯 Sélection du spot : ${name}`);
    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);
    if (isNaN(latNum) || isNaN(lonNum)) { showNotification('Coordonnées invalides', 'error'); return; }
    
    if (!window.map) {
        console.log('⏳ Carte pas prête, tentative dans 500ms...');
        setTimeout(() => selectSpot(lat, lon, name), 500);
        return;
    }
    
    const userLat = currentLat;
    const userLon = currentLon;
    const distanceKm = calculateDistance(userLat, userLon, latNum, lonNum);
    
    currentLat = latNum;
    currentLon = lonNum;
    
    localStorage.setItem('currentLat', latNum.toString());
    localStorage.setItem('currentLon', lonNum.toString());
    localStorage.setItem('currentSpotName', name);
    localStorage.setItem('currentSpotDistance', distanceKm.toFixed(1));
    
    const isFav = isSpotFavorite(latNum, lonNum);
    window.lastSpotData = { name, lat: latNum, lon: lonNum, distance: distanceKm, isFavorite: isFav };
    
    window.map.setView([latNum, lonNum], 13, { animate: true, duration: 0.5 });
    
    if (selectedSpotMarker) window.map.removeLayer(selectedSpotMarker);
    selectedSpotMarker = L.marker([latNum, lonNum], { 
        icon: createSelectedSpotMarker(latNum, lonNum, name, isFav),
        zIndexOffset: 1000 
    }).addTo(window.map);
    console.log('📍 Marqueur créé pour', name);
    
    selectedSpotMarker.bindPopup(`
        <div style="text-align: center; min-width: 200px;">
            <h3 style="color: ${isFav ? '#f59e0b' : '#ef4444'};">${isFav ? '⭐' : '📍'} ${escapeHTML(name)}</h3>
            <p style="color: #64748b;">${latNum.toFixed(4)}, ${lonNum.toFixed(4)}</p>
            <p style="color: #94a3b8;">Distance: ${distanceKm.toFixed(1)} km</p>
            <button onclick="window.toggleFavorite(${latNum}, ${lonNum}, '${escapeHTML(name)}')" 
                    style="background: ${isFav ? '#f59e0b' : '#3b82f6'}; color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; margin-top: 10px; width: 100%;">
                <i class="fas fa-star"></i> ${isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'}
            </button>
        </div>
    `).openPopup();
    
    updateSpotDisplay(name, latNum, lonNum, distanceKm, isFav);
    await calculateDistanceToSpot(latNum, lonNum);
    
    // Mettre à jour le spot sélectionné dans FishingDashboard pour la sauvegarde
    if (window.FishingDashboard) {
        // Appeler la méthode selectSpot du dashboard pour synchroniser selectedSpot
        window.FishingDashboard.selectSpot(latNum, lonNum, name);
        
        await Promise.all([
            window.FishingDashboard.loadWeatherDataInternal?.(latNum, lonNum),
            window.FishingDashboard.updatePredictionInternal?.(latNum, lonNum),
            window.FishingDashboard.updateScientificDataInternal?.(latNum, lonNum),
            window.FishingDashboard.load24hForecastInternal?.(latNum, lonNum)
        ]);
        showNotification(`✅ Spot "${name}" sélectionné`, 'success');
        if (window.innerWidth <= 768) setTimeout(() => showMobileDetailsModal(), 800);
        return;
    }
    await loadWeatherData(latNum, lonNum);
    showNotification(`✅ Spot "${name}" sélectionné`, 'success');
    if (window.innerWidth <= 768) setTimeout(() => showMobileDetailsModal(), 800);
}

// ===== NOTIFICATIONS =====
function showNotification(message, type = 'info') {
    document.querySelectorAll('.notification').forEach(n => n.remove());
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    const icons = { 'success': 'check-circle', 'error': 'exclamation-circle', 'warning': 'exclamation-triangle', 'info': 'info-circle' };
    notification.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i><span>${escapeHTML(message)}</span><button onclick="this.parentElement.remove()">×</button>`;
    document.body.appendChild(notification);
    setTimeout(() => notification.classList.add('show'), 10);
    setTimeout(() => { notification.classList.remove('show'); setTimeout(() => notification.remove(), 300); }, 3000);
}

// ===== MODALE MOBILE =====
function initMobileInterface() {
    if (window.innerWidth > 768) return;
    if (!document.getElementById('map')) return;
    const rightColumn = document.querySelector('.right-column');
    if (rightColumn && !modalContentCache) modalContentCache = rightColumn.innerHTML;
}

async function showMobileDetailsModal() {
    console.log('📱 OUVERTURE MODALE');
    const modal = document.getElementById('mobileDetailsModal');
    const content = document.getElementById('modal-content-container');
    if (!modal || !content) return;
    if (modalOpen) { console.log('📱 Modale déjà ouverte'); return; }
    modalOpen = true;
    const spotName = document.getElementById('selected-spot-name')?.textContent || 'Spot non sélectionné';
    const userLat = window.FishingDashboard?.userLat || 36.8065;
    const userLon = window.FishingDashboard?.userLon || 10.1815;
    const currentSpecies = window.FishingDashboard?.currentSpecies || 'loup';
    document.getElementById('modal-spot-name').textContent = spotName;
    content.innerHTML = `<div style="display:flex; justify-content:center; align-items:center; height:70vh; flex-direction:column;">
        <div style="width:50px; height:50px; border:4px solid #334155; border-top:4px solid #3b82f6; border-radius:50%; animation:spin 1s linear infinite; margin-bottom:1rem;"></div>
        <p style="color:#94a3b8;">Analyse en cours...</p>
    </div>`;
    modal.style.display = 'block';
    modal.classList.remove('closing');
    document.body.style.overflow = 'hidden';
    
    const score = document.getElementById('prediction-score')?.textContent || '--%';
    const fishCount = document.getElementById('current-fish-count')?.textContent || '--';
    const waterTemp = document.getElementById('water-temp')?.textContent || '--°C';
    const oxygen = document.getElementById('oxygen-level')?.textContent || '-- mg/L';
    const phytoplankton = document.getElementById('phytoplankton')?.textContent || '--';
    const waveHeight = document.getElementById('wave-height')?.textContent || '-- m';
    const moonPhase = document.getElementById('moon-phase')?.textContent || '--';
    const bestPeriod = document.getElementById('best-period')?.textContent || '--h';
    const windSpeed = document.getElementById('wind-speed')?.textContent || '--';
    const windDir = document.getElementById('wind-direction')?.textContent || 'Direction';
    const temperature = document.getElementById('temperature')?.textContent || '--°C';
    const pressure = document.getElementById('pressure')?.textContent || '-- hPa';
    const weatherCondition = document.getElementById('weather-condition')?.textContent || '--';
    const checkOffshore = document.getElementById('check-offshore')?.textContent || '❌';
    const envScore = document.getElementById('mini-env-score')?.textContent || '--%';
    const behScore = document.getElementById('mini-beh-score')?.textContent || '--%';
    const depth = document.getElementById('mini-depth')?.textContent || '-- m';
    const seabed = document.getElementById('mini-seabed')?.textContent || '--';
    const scoreValue = parseInt(score) || 0;
    let scoreColor = '#ef4444', scoreText = 'Mauvais';
    if (scoreValue >= 80) { scoreColor = '#10b981'; scoreText = 'Excellent'; }
    else if (scoreValue >= 65) { scoreColor = '#3b82f6'; scoreText = 'Bon'; }
    else if (scoreValue >= 50) { scoreColor = '#f59e0b'; scoreText = 'Moyen'; }
    
    let chartLabels = [], chartScores = [], trendArrow = '➡️', trend = 'Stable', bestTime = bestPeriod, optimalRanges = [];
    if (window.lastChartData) {
        chartLabels = window.lastChartData.hours;
        chartScores = window.lastChartData.scores;
        bestTime = window.lastChartData.best_hour || bestTime;
        if (window.lastChartData.trend === 'rising') { trendArrow = '↗️'; trend = 'Hausse'; }
        else if (window.lastChartData.trend === 'falling') { trendArrow = '↘️'; trend = 'Baisse'; }
        optimalRanges = extractOptimalRanges(window.lastChartData.scores, window.lastChartData.hours, 70);
    } else {
        try {
            const response = await fetch(`/api/24h_forecast?lat=${userLat}&lon=${userLon}&species=${currentSpecies}&_=${Date.now()}`);
            const data = await response.json();
            if (data.status === 'success') {
                chartLabels = data.hours;
                chartScores = data.scores;
                bestTime = data.best_hour || bestTime;
                if (data.trend === 'rising') { trendArrow = '↗️'; trend = 'Hausse'; }
                else if (data.trend === 'falling') { trendArrow = '↘️'; trend = 'Baisse'; }
                optimalRanges = extractOptimalRanges(data.scores, data.hours, 70);
            }
        } catch (e) {
            chartLabels = Array.from({length:24}, (_,i) => i.toString().padStart(2,'0')+'h');
            chartScores = chartLabels.map(() => Math.floor(50 + Math.random() * 30));
            optimalRanges = extractOptimalRanges(chartScores, chartLabels, 70);
        }
    }
    
    // Plages optimales HTML - Version sans scores
    let rangesHtml = '<div style="margin:1rem 0;">';
    const pressureTrend = document.getElementById('pressure-trend-icon')?.textContent || '➡️';
    const pressureValue = parseFloat(document.getElementById('pressure')?.textContent) || 1015;
    
    if (optimalRanges.length === 0) {
        const fallbackTime = formatHourToTime(bestTime);
        const fallbackHour = parseInt(bestTime);
        
        // Déterminer la qualité sans score
        let qualityIcon = '🎯';
        let qualityText = 'Recommandé';
        let borderColor = '#3b82f6';
        
        if (fallbackHour >= 4 && fallbackHour <= 7) {
            qualityIcon = '🌅';
            qualityText = 'Aube';
            borderColor = '#10b981';
        } else if (fallbackHour >= 17 && fallbackHour <= 20) {
            qualityIcon = '🌆';
            qualityText = 'Crépuscule';
            borderColor = '#10b981';
        } else if (fallbackHour >= 21 || fallbackHour <= 4) {
            if (moonPhase.includes('Pleine Lune')) {
                qualityIcon = '🌕';
                qualityText = 'Pleine Lune';
                borderColor = '#3b82f6';
            } else {
                qualityIcon = '🌙';
                qualityText = 'Nuit';
                borderColor = '#f59e0b';
            }
        }
        
        // Ajouter info pression
        if (pressureTrend === '📉' && pressureValue < 1020) {
            qualityText += ' ✓';
        }
        
        rangesHtml += `
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem; padding:0.5rem; background:#1e293b; border-radius:8px; border-left:4px solid ${borderColor};">
                <div style="display:flex; align-items:center; gap:0.75rem;">
                    <span style="font-size:1.3rem;">${qualityIcon}</span>
                    <span style="color:white; font-weight:600;">${fallbackTime}</span>
                </div>
                <div style="background: ${borderColor}; padding:0.25rem 0.75rem; border-radius:20px; color:white; font-weight:600; font-size:0.9rem;">
                    ${qualityText}
                </div>
            </div>
        `;
    } else {
        optimalRanges.forEach(range => {
            const startTime = formatHourToTime(range.start);
            const endTime = formatHourToTime(range.end);
            const startHour = parseInt(range.start);
            
            // Déterminer la qualité sans score
            let qualityIcon = '🎣';
            let qualityText = 'Recommandé';
            let borderColor = '#3b82f6';
            
            if (startHour >= 4 && startHour <= 7) {
                qualityIcon = '🌅';
                qualityText = 'Aube';
                borderColor = '#10b981';
            } else if (startHour >= 17 && startHour <= 20) {
                qualityIcon = '🌆';
                qualityText = 'Crépuscule';
                borderColor = '#10b981';
            } else if (startHour >= 21 || startHour <= 4) {
                if (moonPhase.includes('Pleine Lune')) {
                    qualityIcon = '🌕';
                    qualityText = 'Pleine Lune';
                    borderColor = '#3b82f6';
                } else if (moonPhase.includes('Nouvelle Lune')) {
                    qualityIcon = '🌑';
                    qualityText = 'Nouvelle Lune';
                    borderColor = '#3b82f6';
                } else {
                    qualityIcon = '🌙';
                    qualityText = 'Nuit';
                    borderColor = '#f59e0b';
                }
            } else if (startHour >= 11 && startHour <= 14) {
                qualityIcon = '☀️';
                qualityText = 'Midi';
                borderColor = '#ef4444';
            }
            
            // Ajouter info pression
            if (pressureTrend === '📉' && pressureValue < 1020) {
                qualityText += ' ✓';
            }
            
            rangesHtml += `
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.5rem; padding:0.5rem; background:#1e293b; border-radius:8px; border-left:4px solid ${borderColor};">
                    <div style="display:flex; align-items:center; gap:0.75rem;">
                        <span style="font-size:1.3rem;">${qualityIcon}</span>
                        <div>
                            <span style="color:white; font-weight:600;">${startTime}</span>
                            <span style="color:#94a3b8; margin:0 0.25rem;">→</span>
                            <span style="color:white; font-weight:600;">${endTime}</span>
                        </div>
                    </div>
                    <div style="background: ${borderColor}; padding:0.25rem 0.75rem; border-radius:20px; color:white; font-weight:600; font-size:0.9rem;">
                        ${qualityText}
                    </div>
                </div>
            `;
        });
    }
    rangesHtml += '</div>';
    
    const speciesNames = {'loup':'Loup','daurade':'Dorade','pageot':'Pageot','thon':'Thon','sar':'Sar','mulet':'Mulet','marbré':'Marbré','rouget':'Rouget','sériole':'Sériole','bonite':'Bonite','corbeau':'Corbeau','espadon':'Espadon','mérou':'Mérou','merlan':'Merlan','merlu':'Merlu','orphie':'Orphie'};
    let speciesOptions = '';
    for (const [key, name] of Object.entries(speciesNames)) {
        speciesOptions += `<option value="${key}" ${key === currentSpecies ? 'selected' : ''}>${name}</option>`;
    }
    
    let html = `
        <div style="background: linear-gradient(135deg, #1e293b, #0f172a); border-radius: 20px; padding: 1.5rem; margin-bottom: 1.5rem; border: 2px solid ${scoreColor};">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div><div style="color:#94a3b8;">Score de pêche</div><div style="font-size:3.5rem; font-weight:900; color:${scoreColor};">${score}</div><div style="color:${scoreColor};">${scoreText}</div></div>
                <div style="text-align:right;"><div style="color:#94a3b8;">Poissons actifs</div><div style="font-size:2.5rem; font-weight:700;">${fishCount}</div><div style="color:#94a3b8;">estimés</div></div>
            </div>
        </div>
        <div style="background:#1e293b; border-radius:16px; padding:1rem; margin-bottom:1.5rem;">
            <select id="modal-species-selector" style="width:100%; padding:0.75rem; background:#0f172a; color:white; border:1px solid #3b82f6; border-radius:12px;" onchange="window.FishingDashboard.changeSpecies(this.value)">${speciesOptions}</select>
        </div>
        <div style="background:#1e293b; border-radius:16px; padding:1.2rem; margin-bottom:1.5rem;">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                <div style="background:#0f172a; border-radius:12px; padding:0.8rem; text-align:center;"><div style="font-size:1.3rem;">💨 ${windSpeed}</div><div style="color:#94a3b8;">${windDir}</div></div>
                <div style="background:#0f172a; border-radius:12px; padding:0.8rem; text-align:center;"><div style="font-size:1.3rem;">🌡️ ${temperature}</div><div style="color:#94a3b8;">Air</div></div>
                <div style="background:#0f172a; border-radius:12px; padding:0.8rem; text-align:center;"><div style="font-size:1.3rem;">💧 ${pressure}</div><div style="color:#94a3b8;">Pression</div></div>
                <div style="background:#0f172a; border-radius:12px; padding:0.8rem; text-align:center;"><div style="font-size:1.3rem;">${checkOffshore}</div><div style="color:#94a3b8;">Offshore</div></div>
            </div>
        </div>
        <div style="background:#1e293b; border-radius:16px; padding:1.2rem; margin-bottom:1.5rem;">
            <div style="display:grid; grid-template-columns:repeat(3,1fr); gap:0.8rem;">
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>🌡️ ${waterTemp}</div><div style="color:#94a3b8;">Eau</div></div>
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>💧 ${oxygen}</div><div style="color:#94a3b8;">Oxygène</div></div>
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>🌿 ${phytoplankton}</div><div style="color:#94a3b8;">Phyto.</div></div>
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>🌊 ${waveHeight}</div><div style="color:#94a3b8;">Vagues</div></div>
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>🌙 ${moonPhase}</div><div style="color:#94a3b8;">Lune</div></div>
                <div style="background:#0f172a; border-radius:10px; padding:0.6rem; text-align:center;"><div>🎣 ${bestPeriod}</div><div style="color:#94a3b8;">Meilleur</div></div>
            </div>
        </div>
        <div style="background:#1e293b; border-radius:16px; padding:1.2rem;">
            <div style="height:200px;"><canvas id="modal-activity-chart"></canvas></div>
            <div style="margin-top:1rem;">${rangesHtml}</div>
        </div>
    `;
    content.innerHTML = html;
    setTimeout(() => {
        const canvas = document.getElementById('modal-activity-chart');
        if (!canvas) return;
        if (window.modalChart) window.modalChart.destroy();
        window.modalChart = new Chart(canvas, {
            type: 'line',
            data: { labels: window.lastChartData?.hours || chartLabels, datasets: [{ data: window.lastChartData?.scores || chartScores, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 3, fill: true, tension: 0.4, pointRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
        });
    }, 100);
}

function closeMobileDetailsModal() {
    const modal = document.getElementById('mobileDetailsModal');
    if (!modal || !modalOpen) return;
    modal.classList.add('closing');
    document.body.style.overflow = '';
    setTimeout(() => {
        modal.style.display = 'none';
        modal.classList.remove('closing');
        modalOpen = false;
    }, 300);
}

// ===== FONCTIONS DE CHARGEMENT OPTIMISÉ =====
async function loadPredictionOptimized(lat, lon, species) {
    console.log('📊 Chargement optimisé...');
    try {
        const quickRes = await fetch(`/api/quick_score?lat=${lat}&lon=${lon}&species=${species}&_=${Date.now()}`);
        const quickData = await quickRes.json();
        if (quickData.status === 'success') {
            const scoreEl = document.getElementById('prediction-score');
            const lastUpdateEl = document.getElementById('last-update');
            
            if (scoreEl) scoreEl.textContent = quickData.score + '%';
            if (lastUpdateEl) lastUpdateEl.innerHTML = `🔄 ${new Date(quickData.last_update).toLocaleTimeString()} (cache)`;
            
            setTimeout(() => updatePreciseScore(lat, lon, species), 100);
        }
    } catch (error) { console.error('Erreur:', error); }
}

async function updatePreciseScore(lat, lon, species) {
    try {
        const preciseRes = await fetch(`/api/tunisian_prediction?lat=${lat}&lon=${lon}&species=${species}&_=${Date.now()}`);
        const preciseData = await preciseRes.json();
        if (preciseData.status === 'success') {
            const scoreEl = document.getElementById('prediction-score');
            const lastUpdateEl = document.getElementById('last-update');
            
            if (scoreEl) scoreEl.textContent = preciseData.scores.final + '%';
            if (lastUpdateEl) lastUpdateEl.innerHTML = `🔄 ${new Date().toLocaleTimeString()}`;
        }
    } catch (error) { console.error('Erreur mise à jour:', error); }
}

function scheduleUpdates(lat, lon, species) {
    setInterval(() => updatePreciseScore(lat, lon, species), 3 * 60 * 60 * 1000);
}

// ===== FONCTIONS SPÉCIFIQUES =====
function checkOffshoreWind(isOffshore) {
    const alertDiv = document.getElementById('wind-offshore-alert');
    const dangerDiv = document.getElementById('offshore-danger');
    const checkOffshore = document.getElementById('check-offshore');
    if (isOffshore === true) {
        if (alertDiv) alertDiv.style.display = 'block';
        if (dangerDiv) dangerDiv.style.display = 'block';
        if (checkOffshore) { checkOffshore.innerHTML = '⚠️'; checkOffshore.style.color = '#ef4444'; }
    } else {
        if (alertDiv) alertDiv.style.display = 'none';
        if (dangerDiv) dangerDiv.style.display = 'none';
        if (checkOffshore) { checkOffshore.innerHTML = '✅'; checkOffshore.style.color = '#10b981'; }
    }
}

function updateDetailedAnalysis(data) {
    if (!data) return;
    const miniEnv = document.getElementById('mini-env-score');
    const miniBeh = document.getElementById('mini-beh-score');
    const miniDepth = document.getElementById('mini-depth');
    const miniSeabed = document.getElementById('mini-seabed');
    if (miniEnv && data.scores) miniEnv.textContent = (data.scores.environmental || 0) + '%';
    if (miniBeh && data.scores) miniBeh.textContent = (data.scores.behavioral || 0) + '%';
    if (miniDepth && data.bathymetry) miniDepth.textContent = (data.bathymetry.depth || '--') + ' m';
    if (miniSeabed && data.bathymetry) miniSeabed.textContent = data.bathymetry.seabed_description || '--';
    const detailEnv = document.getElementById('detail-environmental');
    const detailBeh = document.getElementById('detail-behavioral');
    const detailDepth = document.getElementById('detail-depth');
    const detailSeabed = document.getElementById('detail-seabed');
    const detailWaveHeight = document.getElementById('detail-wave-height');
    const detailCurrent = document.getElementById('detail-current');
    const detailCurrentImpact = document.getElementById('detail-current-impact');
    if (detailEnv && data.scores) detailEnv.textContent = (data.scores.environmental || 0) + '%';
    if (detailBeh && data.scores) detailBeh.textContent = (data.scores.behavioral || 0) + '%';
    if (detailDepth && data.bathymetry) detailDepth.textContent = (data.bathymetry.depth || '--') + ' m';
    if (detailSeabed && data.bathymetry) detailSeabed.textContent = data.bathymetry.seabed_description || '--';
    if (detailWaveHeight && data.weather) detailWaveHeight.textContent = (data.weather.wave_height || '--') + ' m';
    if (detailCurrent && data.scientific_factors?.tidal_current) detailCurrent.textContent = (data.scientific_factors.tidal_current.speed_mps || '--') + ' m/s';
    if (detailCurrentImpact && data.scientific_factors?.tidal_current) detailCurrentImpact.textContent = data.scientific_factors.tidal_current.fishing_impact || '--';
}

async function loadPressureData() {
    try {
        const isPredictionsPage = window.location.pathname.includes('predictions') || 
                                  document.querySelector('.predictions-hero') !== null;
        
        if (isPredictionsPage) {
            return;
        }
        
        const pressureCanvas = document.getElementById('pressure-chart');
        const pressureCurrent = document.getElementById('pressure-current');
        const pressureTrend = document.getElementById('pressure-trend-icon');
        const pressureMessage = document.getElementById('pressure-message');
        
        if (!pressureCurrent && !pressureTrend && !pressureMessage) {
            return;
        }
        
        const response = await fetch(`/api/pressure_24h?lat=${currentLat}&lon=${currentLon}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            if (pressureCurrent) pressureCurrent.textContent = data.current + ' hPa';
            if (pressureTrend) pressureTrend.textContent = data.trend_icon;
            if (pressureMessage) pressureMessage.textContent = data.message;
            
            if (pressureCanvas && pressureCanvas.tagName === 'CANVAS') {
                try {
                    const ctx = pressureCanvas.getContext('2d');
                    if (ctx) {
                        if (window.pressureChart) window.pressureChart.destroy();
                        window.pressureChart = new Chart(ctx, {
                            type: 'line',
                            data: { 
                                labels: data.hours, 
                                datasets: [{ 
                                    data: data.pressures, 
                                    borderColor: data.trend_color, 
                                    borderWidth: 2, 
                                    pointRadius: 0,
                                    tension: 0.4
                                }] 
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false, 
                                plugins: { legend: { display: false } },
                                scales: {
                                    x: { display: false },
                                    y: { display: false }
                                }
                            }
                        });
                    }
                } catch (chartError) {
                    console.warn('⚠️ Erreur création graphique pression:', chartError);
                }
            }
        }
    } catch (error) { 
        if (window.location.pathname.includes('predictions')) {
            return;
        }
        console.warn('⚠️ Erreur pression (non bloquante):', error.message); 
    }
}

// ===== FISHING DASHBOARD OBJECT =====
if (typeof window.FishingDashboard === 'undefined') {
    window.FishingDashboard = (function() {
        let map = null;
        let userLat = 36.8065;
        let userLon = 10.1815;
        let currentMarker = null;
        let selectedSpot = null; // Variable pour le spot sélectionné (utilisée par saveCurrentSpot)
        let activityChart = null;
        let currentSpecies = 'loup';
        let currentWindDirection = 0;
        let currentWindSpeed = 10;
        let windAnimationActive = false;
        let windCanvas = null;
        let windCtx = null;
        let windParticles = [];
        let windAnimationFrame = null;
        let customSpots = [];
        
        const speciesNames = {'loup':'Loup','daurade':'Dorade','pageot':'Pageot','thon':'Thon','sar':'Sar','mulet':'Mulet','marbré':'Marbré','rouget':'Rouget','sériole':'Sériole','bonite':'Bonite','corbeau':'Corbeau','espadon':'Espadon','mérou':'Mérou','merlan':'Merlan','merlu':'Merlu','orphie':'Orphie'};
        const TUNISIAN_SPOTS = [
            {name:"Tunis Marina",lat:36.8065,lon:10.1815,type:"port"},
            {name:"Cap Bon",lat:36.8475,lon:11.0940,type:"rocheux"},
            {name:"Sousse",lat:35.8254,lon:10.6360,type:"port"},
            {name:"Hammamet",lat:36.4000,lon:10.6000,type:"plage"},
            {name:"Bizerte",lat:37.2747,lon:9.8739,type:"port"}
        ];
        
        function initWindAnimation() {
            windCanvas = document.getElementById('wind-animation-canvas');
            if(!windCanvas) return;
            windCtx = windCanvas.getContext('2d');
            if(!windCtx) return;
            function resizeCanvas() {
                const mapDiv = document.getElementById('map');
                if(mapDiv && windCanvas && mapDiv.clientHeight > 0) {
                    windCanvas.width = mapDiv.clientWidth;
                    windCanvas.height = mapDiv.clientHeight;
                    initWindParticles();
                }
            }
            setTimeout(resizeCanvas, 500);
            window.addEventListener('resize', resizeCanvas);
        }
        
        function initWindParticles() {
            if(!windCanvas) return;
            const count = Math.min(80, Math.floor(windCanvas.width * windCanvas.height / 2000));
            windParticles = [];
            for(let i=0; i<count; i++) {
                windParticles.push({
                    x: Math.random() * windCanvas.width,
                    y: Math.random() * windCanvas.height,
                    size: Math.random()*2+1,
                    speed: (Math.random()*1.5+0.5) * (currentWindSpeed/15||1),
                    opacity: Math.random()*0.4+0.2
                });
            }
        }
        
        function animateWind() {
            if(!windAnimationActive || !windCtx || !windCanvas) return;
            windCtx.clearRect(0,0,windCanvas.width,windCanvas.height);
            let windAngle = ((currentWindDirection+90) * Math.PI/180);
            windParticles.forEach(p => {
                p.x += Math.cos(windAngle)*p.speed;
                p.y += Math.sin(windAngle)*p.speed;
                p.x += Math.cos(windAngle)*(p.speed * currentWindSpeed/20);
                p.y += Math.sin(windAngle)*(p.speed * currentWindSpeed/20);
                if(p.x > windCanvas.width+10) p.x = -10;
                if(p.x < -10) p.x = windCanvas.width+10;
                if(p.y > windCanvas.height+10) p.y = -10;
                if(p.y < -10) p.y = windCanvas.height+10;
                windCtx.save();
                windCtx.translate(p.x,p.y);
                windCtx.rotate(windAngle);
                windCtx.beginPath();
                windCtx.moveTo(0,0);
                windCtx.lineTo(-8,-2);
                windCtx.lineTo(-8,2);
                windCtx.closePath();
                windCtx.fillStyle = `rgba(59,130,246,${p.opacity*0.8})`;
                windCtx.fill();
                windCtx.beginPath();
                windCtx.arc(0,0,p.size,0,Math.PI*2);
                windCtx.fillStyle = `rgba(59,130,246,${p.opacity})`;
                windCtx.fill();
                windCtx.restore();
            });
            windAnimationFrame = requestAnimationFrame(animateWind);
        }
        
        function checkStrongWind(windSpeed) {
            const strongWindThreshold = 30;
            const veryStrongWindThreshold = 45;
            let strongWindAlert = document.getElementById('strong-wind-alert');
            if(!strongWindAlert) {
                strongWindAlert = document.createElement('div');
                strongWindAlert.id = 'strong-wind-alert';
                strongWindAlert.style.cssText = 'display:none;margin-top:1rem;padding:1rem;color:white;border-radius:8px;text-align:center;animation:pulse 1.5s infinite';
                const offshoreAlert = document.getElementById('wind-offshore-alert');
                if(offshoreAlert && offshoreAlert.parentNode) offshoreAlert.parentNode.insertBefore(strongWindAlert, offshoreAlert.nextSibling);
            }
            if(windSpeed >= veryStrongWindThreshold) {
                strongWindAlert.style.display = 'block';
                strongWindAlert.innerHTML = '<i class="fas fa-exclamation-triangle"></i> <strong>VENT TRÈS FORT - DANGER</strong><br>Pêche déconseillée';
                strongWindAlert.style.background = '#dc2626';
            } else if(windSpeed >= strongWindThreshold) {
                strongWindAlert.style.display = 'block';
                strongWindAlert.innerHTML = '<i class="fas fa-exclamation-triangle"></i> <strong>VENT FORT</strong><br>Conditions difficiles';
                strongWindAlert.style.background = '#f59e0b';
            } else if(strongWindAlert) strongWindAlert.style.display = 'none';
        }
        
        function calculateWaveHeight(windSpeedKmh) {
            if (!windSpeedKmh) return 0.2;
            if (windSpeedKmh < 10) return 0.2;
            else if (windSpeedKmh < 20) return 0.2 + (windSpeedKmh-10)*0.04;
            else if (windSpeedKmh < 30) return 0.6 + (windSpeedKmh-20)*0.06;
            else if (windSpeedKmh < 40) return 1.2 + (windSpeedKmh-30)*0.08;
            else if (windSpeedKmh < 50) return 2.0 + (windSpeedKmh-40)*0.10;
            else if (windSpeedKmh < 60) return 3.0 + (windSpeedKmh-50)*0.12;
            else return 4.2 + (windSpeedKmh-60)*0.15;
        }
        
        function updateWaveHeight(value) {
            let waveValue = typeof value === 'number' ? value.toFixed(1) : value;
            const waveEl = document.getElementById('wave-height');
            const checkWaves = document.getElementById('check-waves');
            const detailWave = document.getElementById('detail-wave-height');
            
            if (waveEl) waveEl.textContent = waveValue + ' m';
            if (checkWaves) checkWaves.textContent = waveValue + ' m';
            if (detailWave) detailWave.textContent = waveValue + ' m';
        }
        
        function updateUserPosition(lat, lon) {
            userLat = lat; userLon = lon;
            if (currentMarker) currentMarker.setLatLng([lat, lon]);
            if (map) map.setView([lat, lon], map.getZoom());
            if (selectedSpot) calculateDistanceToSpot(selectedSpot.lat, selectedSpot.lon);
            loadWeatherDataInternal();
            updatePredictionInternal();
            updateScientificDataInternal();
            load24hForecastInternal();
        }
        
        function addSpotToMap(spot, isCustom = false) {
            if(!spot || !spot.lat || !spot.lon || !map) {
                console.warn('⚠️ Impossible d\'ajouter le marqueur', spot);
                return;
            }
            let iconColor = {port:'#3b82f6',plage:'#10b981',rocheux:'#f59e0b',custom:'#8b5cf6'}[spot.type] || '#6b7280';
            
            const iconSize = isCustom ? 18 : 16;
            const iconAnchor = isCustom ? 9 : 8;
            
            const icon = L.divIcon({
                html: `<div style="background:${iconColor};width:${iconSize-4}px;height:${iconSize-4}px;border-radius:50%;border:2px solid white;box-shadow:0 0 10px rgba(0,0,0,0.5);${isCustom?'animation:pulse 1.5s infinite':''}"></div>`,
                className: 'spot-icon',
                iconSize: [iconSize, iconSize],
                iconAnchor: [iconAnchor, iconAnchor]
            });
            
            const marker = L.marker([spot.lat, spot.lon], {icon}).addTo(map);
            marker.spotData = { name: spot.name, lat: spot.lat, lon: spot.lon, type: spot.type, description: spot.description, id: spot.id };
            marker.on('click', function() { window.selectSpot(this.spotData.lat, this.spotData.lon, this.spotData.name); });
            
            const isFav = isSpotFavorite(spot.lat, spot.lon);
            const favButton = isCustom ? `<button onclick="window.toggleFavorite(${spot.lat},${spot.lon},'${escapeHTML(spot.name)}')" style="background:${isFav?'#f59e0b':'#3b82f6'}; color:white; border:none; padding:8px 16px; border-radius:20px; cursor:pointer; margin-top:5px; width:100%;"><i class="fas fa-star"></i> ${isFav?'Retirer':'Ajouter'}</button>` : '';
            const deleteButton = isCustom ? `<button onclick="if(confirm('Supprimer ?')) window.FishingDashboard.deleteCustomSpot(${spot.lat},${spot.lon},'${escapeHTML(spot.name)}')" style="background:#ef4444; color:white; border:none; padding:8px 16px; border-radius:20px; cursor:pointer; margin-top:5px; width:100%;"><i class="fas fa-trash"></i> Supprimer</button>` : '';
            
            const popupDiv = document.createElement('div');
            popupDiv.style.minWidth = '220px'; popupDiv.style.textAlign = 'center';
            popupDiv.innerHTML = `<h3 style="color:#1e40af;">${escapeHTML(spot.name)}</h3><span style="background:${iconColor}; color:white; padding:2px 8px; border-radius:12px; font-size:12px;">${isCustom?'Favori':spot.type}</span><p>${escapeHTML(spot.description||'')}</p><p>${spot.lat.toFixed(4)}, ${spot.lon.toFixed(4)}</p>${favButton}${deleteButton}`;
            marker.bindPopup(popupDiv);
            marker.spotType = spot.type;
            marker.isCustom = isCustom;
        }
        
        function loadCustomSpots() {
            try {
                const saved = localStorage.getItem('fishingPredictorCustomSpots');
                if(saved) { customSpots = JSON.parse(saved); customSpots.forEach(s => addSpotToMap(s, true)); }
            } catch(e) { console.error('Erreur chargement spots:', e); customSpots = []; }
        }
        
        function saveCustomSpots() {
            localStorage.setItem('fishingPredictorCustomSpots', JSON.stringify(customSpots));
        }
        
        async function loadWeatherDataInternal(lat = null, lon = null) {
            const targetLat = lat !== null ? lat : userLat;
            const targetLon = lon !== null ? lon : userLon;
            try {
                const response = await fetch(`/api/current_weather?lat=${targetLat}&lon=${targetLon}`);
                const data = await response.json();
                if (data.status === 'success') {
                    const weather = data.weather;
                    currentWindDirection = weather.wind_direction || 0;
                    currentWindSpeed = weather.wind_speed || 10;
                    
                    const tempEl = document.getElementById('temperature');
                    const windSpeedEl = document.getElementById('wind-speed');
                    const windDirEl = document.getElementById('wind-direction');
                    const pressureEl = document.getElementById('pressure');
                    const conditionEl = document.getElementById('weather-condition');
                    const cloudEl = document.getElementById('cloud-cover');
                    
                    if (tempEl) tempEl.textContent = `${weather.temperature?.toFixed(1) || '--'}°C`;
                    if (windSpeedEl) windSpeedEl.textContent = `${weather.wind_speed?.toFixed(1) || '--'} km/h`;
                    if (windDirEl) windDirEl.textContent = weather.wind_direction_name || '--';
                    if (pressureEl) pressureEl.textContent = `${weather.pressure?.toFixed(0) || '--'} hPa`;
                    if (conditionEl) conditionEl.textContent = weather.condition_fr || '--';
                    if (cloudEl) cloudEl.textContent = `Nuages: ${weather.clouds || '--'}%`;
                    
                    if (weather.wave_height) updateWaveHeight(weather.wave_height);
                    checkOffshoreWind(weather.wind_offshore);
                    checkStrongWind(weather.wind_speed || 0);
                    if(windAnimationActive) initWindParticles();
                }
            } catch (error) { console.error('Erreur météo:', error); }
            updatePredictionInternal(lat, lon);
            loadPressureData();
        }
        
        function updateAdvice(currentScore, bestScore, bestHour) {
            const adviceContainer = document.getElementById('advice-container');
            if (!adviceContainer) return;
            const diff = currentScore - bestScore;
            const absDiff = Math.abs(diff);
            let message, bgColor, icon;
            if (currentScore >= bestScore) { icon='🔥'; message=`PÊCHEZ MAINTENANT ! (${currentScore}% vs ${bestScore}%)`; bgColor='linear-gradient(135deg,#10b981,#059669)'; }
            else if (bestScore - currentScore < 5) { icon='👍'; message=`Bon maintenant, mieux à ${bestHour} (+${absDiff}%)`; bgColor='linear-gradient(135deg,#f59e0b,#d97706)'; }
            else { icon='⏳'; message=`Attendez ${bestHour} (+${absDiff}% meilleur)`; bgColor='linear-gradient(135deg,#3b82f6,#2563eb)'; }
            adviceContainer.innerHTML = `<div style="background:${bgColor};color:white;padding:15px 20px;border-radius:12px;font-weight:bold;text-align:center;">${icon} ${message}<br><span style="font-size:0.9rem;">${currentScore}% maintenant · ${bestScore}% à ${bestHour}</span></div>`;
        }
        
        function getScoreColor(score) {
            if (score >= 85) return '#10b981';
            if (score >= 75) return '#3b82f6';
            if (score >= 65) return '#f59e0b';
            if (score >= 50) return '#f97316';
            return '#ef4444';
        }
        
        function getAdviceForTest() { return document.getElementById('test-advice')?.getAttribute('data-advice') || null; }
        
        function estimateWaveHeight(score) {
            if (score >= 85) return 0.5;
            if (score >= 75) return 1.0;
            if (score >= 65) return 1.5;
            if (score >= 55) return 2.0;
            return 2.5;
        }
        
        async function updatePredictionInternal(lat = null, lon = null) {
            const targetLat = lat !== null ? lat : userLat;
            const targetLon = lon !== null ? lon : userLon;
            try {
                const forecastResponse = await fetch(`/api/24h_forecast?lat=${targetLat}&lon=${targetLon}&species=${currentSpecies}`);
                const forecastData = await forecastResponse.json();
                if (forecastData.status === 'success') {
                    const currentHour = new Date().getHours();
                    let currentIndex = 0;
                    for (let i=0; i<forecastData.hours.length; i++) {
                        if (forecastData.hours[i] === currentHour+'h') { currentIndex = i; break; }
                    }
                    const currentScore = forecastData.scores[currentIndex];
                    let bestScore = 0, bestHour = '';
                    for (let i=0; i<forecastData.scores.length; i++) {
                        if (forecastData.scores[i] > bestScore) { bestScore = forecastData.scores[i]; bestHour = forecastData.hours[i]; }
                    }
                    updateFishCountFromScore(currentScore);
                    updateAdvice(currentScore, bestScore, bestHour);
                    
                    // Amélioration du meilleur moment avec facteurs scientifiques
                    const bestHourNum = parseInt(bestHour);
                    let quality = '';
                    let qualityColor = '';
                    
                    if (bestHourNum >= 5 && bestHourNum <= 7) {
                        quality = '🌅 Aube - Excellent !';
                        qualityColor = '#10b981';
                    } else if (bestHourNum >= 17 && bestHourNum <= 19) {
                        quality = '🌆 Crépuscule - Optimal !';
                        qualityColor = '#10b981';
                    } else if (bestHourNum >= 21 || bestHourNum <= 4) {
                        const moonPhase = document.getElementById('moon-phase')?.textContent || '';
                        if (moonPhase.includes('Pleine Lune')) {
                            quality = '🌕 Pleine Lune - Très bon';
                            qualityColor = '#3b82f6';
                        } else {
                            quality = '🌙 Nuit - Potentiel';
                            qualityColor = '#f59e0b';
                        }
                    } else if (bestHourNum >= 11 && bestHourNum <= 14) {
                        quality = '☀️ Midi - Activité réduite';
                        qualityColor = '#ef4444';
                    } else {
                        quality = '📊 Conditions standard';
                        qualityColor = '#94a3b8';
                    }
                    
                    const pressureTrend = document.getElementById('pressure-trend-icon')?.textContent || '➡️';
                    const pressure = parseFloat(document.getElementById('pressure')?.textContent) || 1015;
                    
                    if (pressureTrend === '📉' && pressure < 1020) {
                        quality += ' · Pression en baisse ✅';
                    } else if (pressureTrend === '📈' && pressure > 1020) {
                        quality += ' · Pression en hausse ⚠️';
                    }
                    
                    document.getElementById('window-quality').textContent = quality;
                    document.getElementById('window-quality').style.color = qualityColor;
                    
                    const detailedResponse = await fetch(`/api/tunisian_prediction?lat=${targetLat}&lon=${targetLon}&species=${currentSpecies}&_=${Date.now()}`);
                    const detailedData = await detailedResponse.json();
                    if (detailedData.status === 'success') {
                        detailedData.weather = detailedData.weather || {};
                        detailedData.weather.wave_height = estimateWaveHeight(currentScore);
                        updateDetailedAnalysis(detailedData);
                    }
                    
                    const predScore = document.getElementById('prediction-score');
                    const headerScore = document.getElementById('header-prediction-score');
                    const checkScore = document.getElementById('check-score');
                    const predText = document.getElementById('prediction-text');
                    const headerText = document.getElementById('header-prediction-text');
                    
                    if (predScore) predScore.textContent = currentScore + '%';
                    if (headerScore) headerScore.textContent = currentScore + '%';
                    if (checkScore) checkScore.textContent = currentScore + '%';
                    
                    let text = '';
                    if (currentScore >= 85) text = 'Excellent ! Conditions optimales';
                    else if (currentScore >= 70) text = 'Bonnes conditions';
                    else if (currentScore >= 50) text = 'Conditions moyennes';
                    else text = 'Conditions difficiles';
                    
                    if (predText) predText.textContent = text;
                    if (headerText) headerText.textContent = text;
                }
            } catch(error) { console.error('Erreur prédiction:', error); }
        }
        
        async function updateScientificDataInternal(lat = null, lon = null) {
            const targetLat = lat !== null ? lat : userLat;
            const targetLon = lon !== null ? lon : userLon;
            try {
                const response = await fetch(`/api/scientific_factors?lat=${targetLat}&lon=${targetLon}&species=${currentSpecies}`);
                const data = await response.json();
                if (data.status === 'success') {
                    const factors = data.factors;
                    
                    const waterTemp = document.getElementById('water-temp');
                    const oxygenLevel = document.getElementById('oxygen-level');
                    const phytoplankton = document.getElementById('phytoplankton');
                    
                    if (waterTemp) waterTemp.textContent = factors.water_temperature?.value ? `${factors.water_temperature.value}°C` : '--°C';
                    if (oxygenLevel) oxygenLevel.textContent = factors.dissolved_oxygen?.value ? `${factors.dissolved_oxygen.value} mg/L` : '-- mg/L';
                    if (phytoplankton) phytoplankton.textContent = factors.chlorophyll_a?.value ? `${factors.chlorophyll_a.value} mg/m³` : '--';
                }
            } catch(error) {
                const waterTemp = document.getElementById('water-temp');
                const oxygenLevel = document.getElementById('oxygen-level');
                const phytoplankton = document.getElementById('phytoplankton');
                
                if (waterTemp) waterTemp.textContent = '22°C';
                if (oxygenLevel) oxygenLevel.textContent = '7.2 mg/L';
                if (phytoplankton) phytoplankton.textContent = 'Moyenne';
            }
            try {
                const moonResponse = await fetch('/api/moon_phase');
                const moonData = await moonResponse.json();
                const moonPhase = document.getElementById('moon-phase');
                if (moonPhase) moonPhase.textContent = moonData.moon_phase || '--';
            } catch(e) { 
                const moonPhase = document.getElementById('moon-phase');
                if (moonPhase) moonPhase.textContent = '--'; 
            }
        }
        
        function changeSpecies(species) {
            console.log(`🔄 Changement d'espèce: ${species}`);
            currentSpecies = species;
            localStorage.setItem('fishingLastSpecies', species);
            const selector = document.getElementById('species-selector');
            if (selector) selector.value = species;
            load24hForecastInternal(userLat, userLon);
            updatePredictionInternal(userLat, userLon);
            updateScientificDataInternal(userLat, userLon);
            showNotification(`Espèce: ${speciesNames[species] || species}`, 'info');
        }
        
        // ===== VERSION CORRIGÉE DU GRAPHIQUE (AVEC ÉCHELLE DYNAMIQUE) =====
        async function load24hForecastInternal(lat = null, lon = null) {
            const targetLat = lat !== null ? lat : userLat;
            const targetLon = lon !== null ? lon : userLon;
            try {
                const response = await fetch(`/api/24h_forecast?lat=${targetLat}&lon=${targetLon}&species=${currentSpecies}&_=${Date.now()}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    window.lastChartData = {
                        hours: data.hours,
                        scores: data.scores,
                        best_hour: data.best_hour,
                        best_score: data.best_score,
                        trend: data.trend
                    };
                    
                    const container = document.querySelector('.chart-container');
                    if (!container) return;
                    
                    container.innerHTML = '<canvas id="activity-chart" style="width:100%; height:200px;"></canvas>';
                    
                    setTimeout(() => {
                        const canvas = document.getElementById('activity-chart');
                        if (!canvas) return;
                        
                        if (activityChart) activityChart.destroy();
                        
                        const ctx = canvas.getContext('2d');
                        const gradient = ctx.createLinearGradient(0, 0, 0, 200);
                        gradient.addColorStop(0, 'rgba(59,130,246,0.3)');
                        gradient.addColorStop(1, 'rgba(59,130,246,0.05)');
                        
                        activityChart = new Chart(canvas, {
                            type: 'line',
                            data: { 
                                labels: data.hours, 
                                datasets: [{ 
                                    data: data.scores, 
                                    borderColor: '#3b82f6', 
                                    backgroundColor: gradient,
                                    borderWidth: 3, 
                                    fill: true, 
                                    tension: 0.4, 
                                    pointRadius: 4,
                                    pointHoverRadius: 8,
                                    pointBackgroundColor: '#ffffff',
                                    pointBorderColor: '#3b82f6',
                                    pointBorderWidth: 2,
                                    pointHoverBackgroundColor: '#3b82f6',
                                    pointHoverBorderColor: '#ffffff'
                                }] 
                            },
                            options: { 
                                responsive: true, 
                                maintainAspectRatio: false,
                                interaction: {
                                    mode: 'index',
                                    intersect: false,
                                },
                                plugins: { 
                                    legend: { display: false },
                                    tooltip: {
                                        enabled: true,
                                        backgroundColor: '#1e293b',
                                        titleColor: '#f8fafc',
                                        bodyColor: '#94a3b8',
                                        borderColor: '#3b82f6',
                                        borderWidth: 2,
                                        padding: 12,
                                        displayColors: false,
                                        callbacks: {
                                            label: (context) => {
                                                return `Score: ${context.raw}%`;
                                            },
                                            title: (tooltipItems) => {
                                                const hour = tooltipItems[0].label;
                                                return `Prévision à ${hour}`;
                                            }
                                        }
                                    }
                                }, 
                                scales: { 
                                    x: { 
                                        grid: { color: 'rgba(255,255,255,0.1)' }, 
                                        ticks: { color: '#94a3b8' } 
                                    }, 
                                    y: { 
                                        beginAtZero: false,
                                        min: Math.min(...data.scores) - 5,
                                        max: Math.max(...data.scores) + 5,
                                        grid: { color: 'rgba(255,255,255,0.1)' }, 
                                        ticks: { 
                                            color: '#94a3b8', 
                                            stepSize: 10,
                                            callback: (value) => value + '%'
                                        } 
                                    } 
                                }
                            }
                        });
                        
                        console.log('✅ Graphique chargé avec échelle dynamique');
                    }, 100);
                    
                    // Utiliser la version scientifique pour afficher les plages optimales (SANS SCORES)
                    const optimalRanges = extractOptimalRanges(data.scores, data.hours, 70);
                    displayOptimalRanges(optimalRanges);
                    
                    if (data.best_hour) document.getElementById('best-period').textContent = data.best_hour;
                    if (data.best_time) document.getElementById('next-window-start').textContent = data.best_time;
                    
                    if (data.trend) {
                        let trendText = '', trendIcon = '';
                        if (data.trend === 'rising') { trendText = 'Hausse'; trendIcon = '↗️'; }
                        else if (data.trend === 'falling') { trendText = 'Baisse'; trendIcon = '↘️'; }
                        else { trendText = 'Stable'; trendIcon = '➡️'; }
                        
                        document.getElementById('current-trend').textContent = trendText;
                        document.getElementById('trend-arrow').textContent = trendIcon;
                    }
                }
            } catch (error) { 
                console.error('❌ Erreur chargement graphique:', error); 
            }
        }
        
        function startValidityCountdown(minutes = 30) {
            let timeLeft = minutes * 60;
            setInterval(() => {
                timeLeft--;
                const mins = Math.floor(timeLeft/60);
                const secs = timeLeft%60;
                const countdown = document.getElementById('countdown');
                if(countdown) {
                    countdown.textContent = `${mins.toString().padStart(2,'0')}:${secs.toString().padStart(2,'0')}`;
                    if(timeLeft <= 300) countdown.style.color = '#ef4444';
                }
                if(timeLeft <= 0) {
                    loadWeatherDataInternal();
                    updatePredictionInternal();
                    updateScientificDataInternal();
                    load24hForecastInternal();
                    startValidityCountdown(30);
                }
            }, 1000);
        }
        
        function initMap() {
            setTimeout(() => {
                if (window.fishingMap) { 
                    map = window.fishingMap; 
                    window.map = window.fishingMap;
                    return; 
                }
                
                const mapDiv = document.getElementById('map');
                if (!mapDiv) {
                    console.error('❌ Élément map non trouvé');
                    return;
                }
                
                console.log('📍 Initialisation carte avec:', userLat, userLon);
                
                try {
                    window.fishingMap = L.map('map').setView([userLat, userLon], 10);
                    window.map = window.fishingMap;
                    map = window.fishingMap;
                    
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
                        attribution: '© OpenStreetMap' 
                    }).addTo(map);
                    
                    if (!document.getElementById('advice-container')) {
                        const adviceContainer = document.createElement('div');
                        adviceContainer.id = 'advice-container';
                        const rightColumn = document.querySelector('.right-column');
                        if (rightColumn) rightColumn.prepend(adviceContainer);
                    }
                    
                    if (!document.getElementById('test-advice')) {
                        const testEl = document.createElement('div');
                        testEl.id = 'test-advice';
                        testEl.style.display = 'none';
                        document.body.appendChild(testEl);
                    }
                    
                    setTimeout(() => {
                        TUNISIAN_SPOTS.forEach(s => addSpotToMap(s, false));
                        loadCustomSpots();
                        
                        currentMarker = L.marker([userLat, userLon], {
                            icon: L.divIcon({ 
                                html: '<div style="background:#3b82f6;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 0 10px rgba(59,130,246,0.7);"></div>', 
                                className: 'user-location-icon', 
                                iconSize: [22,22],
                                iconAnchor: [11, 11]
                            })
                        }).addTo(map).bindPopup('Votre position');
                        
                        console.log('✅ Marqueurs ajoutés avec succès');
                    }, 100);
                    
                    map.on('click', function(e) {
                        const lat = e.latlng.lat;
                        const lon = e.latlng.lng;
                        const spotName = `Spot ${lat.toFixed(2)}, ${lon.toFixed(2)}`;
                        localStorage.setItem('currentSpotName', spotName);
                        localStorage.setItem('currentLat', lat);
                        localStorage.setItem('currentLon', lon);
                        window.selectSpot(lat, lon, spotName);
                    });
                    
                    initWindAnimation();
                    loadWeatherDataInternal();
                    updateScientificDataInternal();
                    load24hForecastInternal();
                    startValidityCountdown(30);
                    
                    const now = new Date();
                    const checkHour = document.getElementById('check-hour');
                    if (checkHour) checkHour.textContent = `${now.getHours()}h`;
                    
                    setInterval(() => {
                        if(document.visibilityState === 'visible') {
                            loadWeatherDataInternal();
                            updatePredictionInternal();
                            updateScientificDataInternal();
                            load24hForecastInternal();
                        }
                    }, 5*60000);
                    
                    loadPressureData();
                    setInterval(loadPressureData, 5*60000);
                    loadFavorites();
                    setTimeout(restoreLastSpot, 1000);
                    
                    setTimeout(() => {
                        if (window.map) {
                            window.map.invalidateSize();
                            console.log('📍 Carte redimensionnée');
                        }
                    }, 500);
                    
                    console.log('✅ Carte initialisée avec succès');
                } catch (e) {
                    console.error('❌ Erreur initialisation carte:', e);
                }
            }, 100);
        }
        
        function toggleWindAnimation(e) {
            windAnimationActive = !windAnimationActive;
            const canvas = document.getElementById('wind-animation-canvas');
            const btn = e?.currentTarget || document.getElementById('windToggleBtn');
            if(windAnimationActive) {
                canvas.style.display = 'block';
                if(btn) { btn.innerHTML = '<i class="fas fa-wind"></i> Masquer vent'; btn.classList.add('btn-primary'); btn.classList.remove('btn-secondary'); }
                initWindParticles();
                animateWind();
            } else {
                canvas.style.display = 'none';
                if(btn) { btn.innerHTML = '<i class="fas fa-wind"></i> Afficher vent'; btn.classList.add('btn-secondary'); btn.classList.remove('btn-primary'); }
                if(windAnimationFrame) cancelAnimationFrame(windAnimationFrame);
            }
        }
        
        function toggleSpotType(type) {
            const isChecked = event?.target?.checked || false;
            if(map) map.eachLayer(layer => { if(layer.spotType === type) layer.setOpacity(isChecked?1:0); });
        }
        
        // Méthode pour sélectionner un spot (synchronisée avec la fonction globale)
        function selectSpot(lat, lon, name) {
            selectedSpot = { lat, lon, name };
            document.getElementById('selected-spot-name').textContent = name;
            return Promise.resolve();
        }
        
        function calculateDistanceToSpot(lat, lon) {
            return window.calculateDistanceToSpot(lat, lon);
        }
        
        function deleteCustomSpot(lat, lon, name) {
            if(confirm(`Supprimer "${name}" ?`)) {
                customSpots = customSpots.filter(spot => !(Math.abs(spot.lat - lat) < 0.0001 && Math.abs(spot.lon - lon) < 0.0001));
                saveCustomSpots();
                reloadMap();
                showNotification(`Spot "${name}" supprimé`, 'success');
            }
        }
        
        function clearCustomSpots() {
            if(confirm("Supprimer TOUS les spots ?")) {
                customSpots = [];
                saveCustomSpots();
                reloadMap();
                showNotification('Tous les spots supprimés', 'info');
            }
        }
        
        function reloadMap() {
            if(!map) return;
            const center = map.getCenter();
            const zoom = map.getZoom();
            map.eachLayer(layer => { if(layer instanceof L.Marker && layer !== currentMarker) map.removeLayer(layer); });
            TUNISIAN_SPOTS.forEach(s => addSpotToMap(s, false));
            customSpots.forEach(s => addSpotToMap(s, true));
            favorites.forEach(s => {
                if(s.lat && s.lon && !customSpots.find(c => Math.abs(c.lat - s.lat) < 0.0001)) {
                    addSpotToMap({ name: s.name, lat: s.lat, lon: s.lon, type:'custom', description: s.description || 'Favori', id: s.id }, true);
                }
            });
            map.setView(center, zoom);
        }
        
        function getCurrentLocation() {
            if(navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    pos => { updateUserPosition(pos.coords.latitude, pos.coords.longitude); showNotification('Position mise à jour', 'success'); },
                    err => { showNotification('Impossible d\'obtenir la position', 'error'); }
                );
            } else showNotification('Géolocalisation non supportée', 'error');
        }
        
        function saveCurrentSpot() {
            if(selectedSpot) {
                const name = prompt("Nom du spot :", `Spot ${selectedSpot.lat.toFixed(4)},${selectedSpot.lon.toFixed(4)}`);
                if(name) {
                    const newSpot = { name, lat: selectedSpot.lat, lon: selectedSpot.lon, type:"custom", depth:"?", description:"Spot sauvegardé" };
                    customSpots.push(newSpot);
                    saveCustomSpots();
                    addSpotToMap(newSpot, true);
                    if (confirm("Ajouter aux favoris ?")) saveFavorite(newSpot);
                    showNotification(`Spot "${name}" sauvegardé`, 'success');
                }
            } else showNotification("Sélectionnez d'abord un spot", 'error');
        }
        
        function calculatePreparationTime() { showNotification('⏱️ Préparation: 45 min • Départ dans 10 min', 'info'); }
        function quickCheck() { this.checkGoNowDecision(); showNotification('Vérification effectuée', 'info'); if('vibrate' in navigator) navigator.vibrate(100); }
        
        async function checkGoNowDecision() {
            try {
                const r = await fetch(`/api/quick_check?lat=${userLat}&lon=${userLon}&species=${currentSpecies}`);
                const d = await r.json();
                if(d.status === 'success') {
                    const banner = document.getElementById('instant-decision-banner');
                    if(banner) banner.innerHTML = `<div style="background:${d.color};color:white;padding:1rem;border-radius:8px;display:flex;align-items:center;gap:1rem"><i class="fas fa-${d.decision==='danger'?'skull-crossbones':d.decision==='excellent'?'check-circle':'thumbs-up'}"></i><div>${d.message}</div><button onclick="this.parentElement.remove()">×</button></div>`;
                }
            } catch(e) {}
        }
        
        function toggleDetailedAnalysis() {
            const mini = document.getElementById('detailed-analysis-mini');
            const full = document.getElementById('detailed-analysis-full');
            const btn = event?.currentTarget;
            if (!mini || !full) return;
            if (mini.style.display === 'none') {
                mini.style.display = 'grid';
                full.style.display = 'none';
                if (btn) btn.innerHTML = '<i class="fas fa-chevron-down"></i> Voir';
            } else {
                mini.style.display = 'none';
                full.style.display = 'block';
                if (btn) btn.innerHTML = '<i class="fas fa-chevron-up"></i> Réduire';
                if (window.lastDetailedData) updateDetailedAnalysis(window.lastDetailedData);
            }
        }
        
        function getCurrentWindInfo() { return { speed: currentWindSpeed, direction: currentWindDirection, animationActive: windAnimationActive }; }
        function refreshWeather() { loadWeatherDataInternal(); }
        function refreshPrediction() { updatePredictionInternal(); }
        function refreshScientific() { updateScientificDataInternal(); }
        function addWindAnimation() { if(!windAnimationActive) toggleWindAnimation(); }
        function removeWindAnimation() { if(windAnimationActive) toggleWindAnimation(); }
        function updateWindAnimation() { if(windAnimationActive) initWindParticles(); }
        
        return {
            userLat, userLon, activityChart, currentSpecies, speciesNames,
            initMap, changeSpecies, selectSpot, loadWeatherDataInternal, updatePredictionInternal,
            updateScientificDataInternal, load24hForecastInternal, showNotification, calculateDistanceToSpot,
            deleteCustomSpot, clearCustomSpots, reloadMap, saveCurrentSpot,
            toggleWindAnimation, toggleSpotType, getCurrentLocation, calculatePreparationTime,
            quickCheck, checkGoNowDecision, toggleDetailedAnalysis, getCurrentWindInfo,
            refreshWeather, refreshPrediction, refreshScientific, addWindAnimation, removeWindAnimation,
            updateWindAnimation, getAdviceForTest
        };
    })();
}

// ===== AJOUT DE LA FONCTION MANQUANTE toggleWindLayer =====
window.toggleWindLayer = function() {
    if (window.FishingDashboard && window.FishingDashboard.toggleWindAnimation) {
        window.FishingDashboard.toggleWindAnimation();
    } else if (window.WindAnimation && window.WindAnimation.toggleLayer) {
        window.WindAnimation.toggleLayer();
    } else {
        console.warn('⚠️ Fonction toggleWindAnimation non disponible');
    }
};

// ===== INITIALISATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log("📄 Initialisation de l'application");
    detectMobileDevice();
    initWeather();
    
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse-selected { 0% { transform: scale(1); } 50% { transform: scale(1.2); } 100% { transform: scale(1); } }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .notification { position: fixed; top: 20px; right: 20px; padding: 15px; border-radius: 8px; color: white; z-index: 10000; transform: translateX(120%); transition: transform 0.3s ease; max-width: 300px; display: flex; align-items: center; gap: 10px; }
        .notification.show { transform: translateX(0); }
        .notification.success { background: #10b981; }
        .notification.error { background: #ef4444; }
        .notification.info { background: #3b82f6; }
        .notification button { background: transparent; border: none; color: white; font-size: 1.2rem; cursor: pointer; margin-left: auto; }
        .mobile-details-button { display: none; width: 100%; margin-top: 1rem; padding: 1rem; background: linear-gradient(90deg, #3b82f6, #2563eb); color: white; border: none; border-radius: 12px; font-weight: 600; cursor: pointer; align-items: center; justify-content: center; gap: 0.5rem; box-shadow: 0 4px 12px rgba(59,130,246,0.3); }
        @media (max-width: 768px) { .mobile-details-button { display: flex; } }
    `;
    document.head.appendChild(style);
    
    setTimeout(() => {
        const leftColumn = document.querySelector('.left-column');
        if (leftColumn && !document.querySelector('.mobile-details-button')) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-primary mobile-details-button';
            btn.innerHTML = '<i class="fas fa-info-circle"></i> Voir tous les détails';
            btn.onclick = showMobileDetailsModal;
            leftColumn.appendChild(btn);
            console.log('📱 Bouton mobile ajouté');
        }
    }, 1000);
    
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMobileDetailsModal(); });
    
    const checkDashboard = setInterval(() => {
        if (window.FishingDashboard) {
            clearInterval(checkDashboard);
            if (!window.fishingMap) window.FishingDashboard.initMap();
            setTimeout(() => {
                window.FishingDashboard.load24hForecastInternal(window.FishingDashboard.userLat, window.FishingDashboard.userLon);
                loadPressureData();
            }, 500);
            const selector = document.getElementById('species-selector');
            if (selector) selector.value = currentSpecies;
        }
    }, 100);
    
    setTimeout(() => {
        initMobileInterface();
        if (window.FishingDashboard) {
            loadPredictionOptimized(currentLat, currentLon, currentSpecies);
            scheduleUpdates(currentLat, currentLon, currentSpecies);
        }
    }, 1000);
    
    setInterval(() => { if (window.FishingDashboard) window.FishingDashboard.updateScientificDataInternal(); }, 60000);
});

console.log("✅ Module main.js chargé - Version finale avec analyse scientifique des plages horaires (SANS SCORES)");