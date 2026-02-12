// map.js - Gestion de la carte interactive
console.log("map.js chargé");

let map = null;
let marker = null;
let currentLat = 36.8065;
let currentLon = 10.1815;

function initMap(containerId = 'map', center = [36.8065, 10.1815], zoom = 12) {
    try {
        map = L.map(containerId).setView(center, zoom);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        console.log("✅ Carte initialisée avec succès");
        
        // Vérifier si on doit aller à un favori
        const goToLocation = localStorage.getItem('go_to_location');
        if (goToLocation) {
            const location = JSON.parse(goToLocation);
            goToSpot(location.lat, location.lon, location.species);
            localStorage.removeItem('go_to_location');
        }
        
        return map;
        
    } catch (error) {
        console.error("❌ Erreur d'initialisation de la carte:", error);
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b">
                    <div style="text-align:center">
                        <i class="fas fa-exclamation-triangle" style="font-size:3rem;margin-bottom:1rem"></i>
                        <p>Impossible de charger la carte</p>
                        <p style="font-size:0.9rem">Vérifiez votre connexion internet</p>
                    </div>
                </div>
            `;
        }
        return null;
    }
}

function createMarker(lat, lon, popupContent = '', draggable = false) {
    if (marker && map) {
        map.removeLayer(marker);
    }
    
    marker = L.marker([lat, lon], {
        draggable: draggable
    }).addTo(map);
    
    if (popupContent) {
        marker.bindPopup(popupContent);
    }
    
    if (draggable) {
        marker.on('dragend', function(e) {
            currentLat = e.target.getLatLng().lat;
            currentLon = e.target.getLatLng().lng;
            onMarkerMoved(currentLat, currentLon);
        });
    }
    
    return marker;
}

function goToSpot(lat, lon, species = 'loup') {
    currentLat = lat;
    currentLon = lon;
    
    if (map) {
        map.setView([lat, lon], 13);
    }
    
    if (marker) {
        marker.setLatLng([lat, lon]);
    } else {
        createMarker(lat, lon, `Position: ${lat.toFixed(4)}, ${lon.toFixed(4)}`);
    }
    
    // Mettre à jour les prédictions si la fonction existe
    if (typeof updatePrediction === 'function') {
        updatePrediction();
    }
    
    return [lat, lon];
}

function getCurrentLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                
                goToSpot(lat, lon);
                
                if (typeof showNotification === 'function') {
                    showNotification('📍 Position actuelle chargée !', 'success');
                } else {
                    alert('📍 Position actuelle chargée !');
                }
            },
            function(error) {
                const message = error.code === 1 ? 
                    "Permission de géolocalisation refusée" :
                    "Impossible d'obtenir votre position";
                
                if (typeof showNotification === 'function') {
                    showNotification(message, 'error');
                } else {
                    alert(message);
                }
            }
        );
    } else {
        const message = "Géolocalisation non supportée par votre navigateur";
        if (typeof showNotification === 'function') {
            showNotification(message, 'error');
        } else {
            alert(message);
        }
    }
}

function onMarkerMoved(lat, lon) {
    console.log(`Marqueur déplacé: ${lat}, ${lon}`);
    currentLat = lat;
    currentLon = lon;
    
    // Déclencher les mises à jour nécessaires
    const event = new CustomEvent('markerMoved', {
        detail: { lat: lat, lon: lon }
    });
    document.dispatchEvent(event);
}

function addSpotToMap(lat, lon, name, score = 75, icon = '🐟') {
    if (!map) return null;
    
    const customIcon = L.divIcon({
        html: `<div style="background:#3b82f6;color:white;width:35px;height:35px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.3)">${icon}</div>`,
        className: 'custom-spot-marker',
        iconSize: [35, 35],
        iconAnchor: [17.5, 17.5]
    });
    
    const spotMarker = L.marker([lat, lon], { icon: customIcon }).addTo(map);
    
    spotMarker.bindPopup(`
        <div style="text-align:center;min-width:150px">
            <strong>${name}</strong><br>
            <small>Score: ${score}%</small><br>
            <button onclick="goToSpot(${lat}, ${lon})" 
                    style="margin-top:5px;padding:5px 10px;background:#3b82f6;color:white;border:none;border-radius:5px;cursor:pointer">
                Aller à ce spot
            </button>
        </div>
    `);
    
    return spotMarker;
}

// Exposer les fonctions globalement
window.initMap = initMap;
window.createMarker = createMarker;
window.goToSpot = goToSpot;
window.getCurrentLocation = getCurrentLocation;
window.addSpotToMap = addSpotToMap;