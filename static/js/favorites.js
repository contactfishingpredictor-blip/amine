// favorites.js - Gestion des favoris optimisée mobile
// CORRIGÉ : Suppression de la double déclaration de isMobileDevice
console.log("⭐ favorites.js chargé - Module de gestion des favoris");

// Variables globales
if (typeof window.favoritesCache === 'undefined') {
    window.favoritesCache = [];
}

// PAS de déclaration locale de isMobileDevice - on utilise window.isMobileDevice

// Fonction pour sauvegarder un favori
async function saveToFavorites(name, lat, lon, species, score, notes = '') {
    console.log(`💾 Sauvegarde favori: ${name} (${lat}, ${lon})`);
    
    // Si des notes ne sont pas fournies, essayer de récupérer les conditions météo
    if (!notes && window.weatherDataCache) {
        const weather = window.weatherDataCache;
        notes = `Météo: ${weather.condition_fr || weather.condition}, ${weather.temperature?.toFixed(1) || 'N/A'}°C, Vent: ${weather.wind_speed?.toFixed(1) || 'N/A'} km/h`;
    } else if (!notes) {
        notes = "Ajouté depuis la carte";
    }
    
    // Demander à l'utilisateur pour les notes - version mobile friendly
    const userNotes = prompt("Notes (optionnel):", notes || "");
    if (userNotes === null) {
        showNotification('Ajout annulé', 'info');
        return { success: false, cancelled: true };
    }
    
    const favoriteData = {
        name: name || `Spot (${lat.toFixed(4)}, ${lon.toFixed(4)})`,
        lat: lat,
        lon: lon,
        species: species || 'loup',
        score: score || 75,
        notes: userNotes || notes || '',
        date: new Date().toISOString()
    };
    
    console.log("📤 Données à envoyer:", favoriteData);
    
    try {
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(favoriteData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("📥 Réponse serveur:", data);
        
        if (data.status === 'success') {
            showNotification('⭐ Spot ajouté aux favoris !', 'success');
            
            // Mettre à jour le cache
            await refreshFavoritesCache();
            
            return { success: true, id: data.id };
        } else {
            throw new Error(data.message || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('❌ Erreur lors de la sauvegarde:', error);
        showNotification('Erreur: ' + error.message, 'error');
        return { success: false, error: error.message };
    }
}

// Fonction pour supprimer un favori
async function deleteFavorite(favoriteId) {
    if (!favoriteId) {
        showNotification("ID du favori manquant", "error");
        return false;
    }
    
    // Version mobile-friendly de confirm
    if (!await confirmDialog('Voulez-vous vraiment supprimer ce favori ?')) {
        return false;
    }
    
    console.log(`🗑️ Suppression du favori: ${favoriteId}`);
    
    try {
        const response = await fetch(`/api/favorites?id=${favoriteId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("📥 Réponse suppression:", data);
        
        if (data.status === 'success') {
            showNotification('🗑️ Favori supprimé !', 'success');
            
            // Mettre à jour le cache
            window.favoritesCache = window.favoritesCache.filter(f => f.id !== favoriteId);
            
            return true;
        } else {
            throw new Error(data.message || 'Erreur inconnue');
        }
    } catch (error) {
        console.error('❌ Erreur suppression:', error);
        showNotification('Erreur: ' + error.message, 'error');
        return false;
    }
}

// Confirm dialog adapté mobile - utilise window.isMobileDevice
async function confirmDialog(message) {
    // Utiliser la variable globale de main.js
    const isMobile = window.isMobileDevice || false;
    
    if (isMobile) {
        // Sur mobile, utiliser la boîte de dialogue native
        return confirm(message);
    } else {
        return confirm(message);
    }
}

// Fonction pour charger les favoris
async function loadFavorites() {
    console.log("📥 Chargement des favoris...");
    
    try {
        const response = await fetch('/api/favorites');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("📊 Données reçues:", data);
        
        if (data.status === 'success') {
            window.favoritesCache = data.favorites || [];
            return window.favoritesCache;
        } else {
            throw new Error(data.message || 'Erreur serveur');
        }
    } catch (error) {
        console.error('❌ Erreur chargement favoris:', error);
        showNotification('Erreur de chargement: ' + error.message, 'error');
        return [];
    }
}

// Fonction pour rafraîchir le cache
async function refreshFavoritesCache() {
    console.log("🔄 Rafraîchissement du cache...");
    window.favoritesCache = await loadFavorites();
    return window.favoritesCache;
}

// Fonction pour mettre à jour un favori
async function updateFavorite(favoriteId, updates) {
    console.log(`✏️ Mise à jour du favori: ${favoriteId}`);
    
    try {
        // Charger tous les favoris
        const favorites = await loadFavorites();
        const favoriteIndex = favorites.findIndex(f => f.id === favoriteId);
        
        if (favoriteIndex === -1) {
            showNotification('Favori non trouvé', 'error');
            return false;
        }
        
        // Mettre à jour le favori
        const updatedFavorite = { ...favorites[favoriteIndex], ...updates };
        
        // Pour simplifier, on va supprimer et recréer
        await deleteFavorite(favoriteId);
        
        const response = await fetch('/api/favorites', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(updatedFavorite)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('✅ Favori mis à jour !', 'success');
            await refreshFavoritesCache();
            return true;
        } else {
            throw new Error(data.message || 'Erreur mise à jour');
        }
    } catch (error) {
        console.error('❌ Erreur mise à jour favori:', error);
        showNotification('Erreur lors de la mise à jour', 'error');
        return false;
    }
}

// Fonction pour obtenir le nom de l'espèce
function getSpeciesName(key) {
    const speciesNames = {
        'loup': 'Loup de Mer',
        'daurade': 'Daurade Royale',
        'pageot': 'Pageot Commun',
        'thon': 'Thon Rouge',
        'maquereau': 'Maquereau',
        'sériole': 'Sériole',
        'marbré': 'Marbré',
        'mulet': 'Mulet',
        'rouget': 'Rouget',
        'sar': 'Sar',
        'corbeau': 'Corbeau',
        'espadon': 'Espadon',
        'lichet': 'Lichet',
        'bonite': 'Bonite',
        'mérou': 'Mérou',
        'merlan': 'Merlan',
        'merlu': 'Merlu',
        'orphie': 'Orphie'
    };
    return speciesNames[key] || key;
}

// Fonction pour formater la date
function formatDate(dateString) {
    if (!dateString) return "Date inconnue";
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// Fonction pour afficher une notification
function showNotification(message, type = 'info') {
    console.log(`📢 ${type.toUpperCase()}: ${message}`);
    
    // Vérifier si showNotification existe déjà dans main.js
    if (typeof window.showNotification === 'function' && window.showNotification !== showNotification) {
        window.showNotification(message, type);
        return;
    }
    
    // Supprimer les notifications existantes
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notif => notif.remove());
    
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
    
    // Supprimer après 3 secondes
    setTimeout(() => {
        if (notification.parentElement) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }
    }, 3000);
}

// Fonction pour exporter les favoris
function exportFavorites() {
    loadFavorites().then(favorites => {
        if (favorites.length === 0) {
            showNotification('Aucun favori à exporter', 'warning');
            return;
        }
        
        const dataStr = JSON.stringify(favorites, null, 2);
        const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        
        const exportFileDefaultName = `favoris-peche-${new Date().toISOString().slice(0,10)}.json`;
        
        const linkElement = document.createElement('a');
        linkElement.setAttribute('href', dataUri);
        linkElement.setAttribute('download', exportFileDefaultName);
        linkElement.click();
        
        showNotification(`✅ ${favorites.length} favoris exportés`, 'success');
    });
}

// Fonction pour importer des favoris
async function importFavorites() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        
        reader.onload = async (e) => {
            try {
                const importedFavorites = JSON.parse(e.target.result);
                
                if (!Array.isArray(importedFavorites)) {
                    showNotification('Format de fichier invalide', 'error');
                    return;
                }
                
                let importedCount = 0;
                
                for (const fav of importedFavorites) {
                    // Vérifier les champs requis
                    if (fav.lat && fav.lon && fav.name) {
                        const favoriteData = {
                            name: fav.name,
                            lat: fav.lat,
                            lon: fav.lon,
                            species: fav.species || 'loup',
                            score: fav.score || 75,
                            notes: fav.notes || '',
                            date: fav.date || new Date().toISOString()
                        };
                        
                        const response = await fetch('/api/favorites', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(favoriteData)
                        });
                        
                        if (response.ok) {
                            importedCount++;
                        }
                    }
                }
                
                showNotification(`✅ ${importedCount} favoris importés`, 'success');
                await refreshFavoritesCache();
                
                // Rafraîchir la liste si on est sur la page des favoris
                if (window.location.pathname.includes('/favorites') && typeof window.loadFavoritesPage === 'function') {
                    window.loadFavoritesPage();
                }
            } catch (error) {
                console.error('Erreur import:', error);
                showNotification('Erreur lors de l\'import', 'error');
            }
        };
        
        reader.readAsText(file);
    };
    
    input.click();
}

// Fonction pour ajouter le spot actuel aux favoris
async function addCurrentSpotToFavorites() {
    console.log("📍 Ajout du spot actuel aux favoris...");
    
    try {
        // Récupérer les coordonnées actuelles
        let lat, lon;
        
        // Essayer de récupérer depuis la carte Leaflet
        if (window.currentMap && window.currentMap.getCenter) {
            const center = window.currentMap.getCenter();
            lat = center.lat;
            lon = center.lng;
            console.log(`📍 Coordonnées depuis la carte: ${lat}, ${lon}`);
        }
        // Essayer de récupérer depuis localStorage
        else if (localStorage.getItem('currentLat') && localStorage.getItem('currentLon')) {
            lat = parseFloat(localStorage.getItem('currentLat'));
            lon = parseFloat(localStorage.getItem('currentLon'));
            console.log(`📍 Coordonnées depuis localStorage: ${lat}, ${lon}`);
        }
        // Sinon, utiliser les coordonnées par défaut
        else {
            lat = 36.8065;
            lon = 10.1815;
            console.log(`📍 Coordonnées par défaut: ${lat}, ${lon}`);
        }
        
        // Récupérer l'espèce sélectionnée
        let species = 'loup';
        const speciesSelect = document.querySelector('#species-selector, select[name="species"], [data-species]');
        if (speciesSelect) {
            species = speciesSelect.value || speciesSelect.getAttribute('data-species') || 'loup';
        }
        
        // Récupérer le score actuel
        let score = 75;
        const scoreElement = document.querySelector('.final-score, .score-value, [data-score]');
        if (scoreElement) {
            const scoreText = scoreElement.textContent || scoreElement.innerText || scoreElement.getAttribute('data-score');
            const match = scoreText.toString().match(/(\d+)%/);
            if (match) {
                score = parseInt(match[1]);
            }
        }
        
        // Nom par défaut
        const defaultName = `Spot ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        const name = prompt("Nom du spot :", defaultName);
        
        if (name) {
            const result = await saveToFavorites(name, lat, lon, species, score);
            return result;
        } else {
            showNotification("Ajout annulé", "info");
            return { success: false, cancelled: true };
        }
    } catch (error) {
        console.error("❌ Erreur lors de l'ajout du spot:", error);
        showNotification("Erreur: " + error.message, "error");
        return { success: false, error: error.message };
    }
}

// Fonction pour tester l'ajout
async function testAddFavorite() {
    console.log("🧪 Test d'ajout de favori...");
    
    const testData = {
        name: "Spot de test " + new Date().toLocaleTimeString(),
        lat: 36.8 + (Math.random() * 0.1),
        lon: 10.1 + (Math.random() * 0.1),
        species: "loup",
        score: 70 + Math.floor(Math.random() * 30),
        notes: "Créé depuis le bouton test"
    };
    
    const result = await saveToFavorites(
        testData.name,
        testData.lat,
        testData.lon,
        testData.species,
        testData.score,
        testData.notes
    );
    
    return result;
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log("✅ Module favorites.js initialisé");
    
    // PAS de détection mobile ici - on utilise celle de main.js
});

// Exposer les fonctions globalement
window.saveToFavorites = saveToFavorites;
window.deleteFavorite = deleteFavorite;
window.loadFavorites = loadFavorites;
window.updateFavorite = updateFavorite;
window.exportFavorites = exportFavorites;
window.importFavorites = importFavorites;
window.showNotification = showNotification;
window.getSpeciesName = getSpeciesName;
window.formatDate = formatDate;
window.addCurrentSpotToFavorites = addCurrentSpotToFavorites;
window.testAddFavorite = testAddFavorite;

console.log("✅ Module favorites.js chargé - Version optimisée mobile");
