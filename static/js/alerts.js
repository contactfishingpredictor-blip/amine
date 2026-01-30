// alerts.js - Gestion des alertes améliorée

let alertInterval = null;
let alertCheckEnabled = true;

// Fonction pour s'abonner aux alertes
async function subscribeToAlerts(email, preferences = {}) {
    if (!email || !email.includes('@')) {
        showNotification('Veuillez entrer une adresse email valide', 'error');
        return false;
    }
    
    const alertPreferences = {
        email: email,
        subscribed: true,
        subscribedAt: new Date().toISOString(),
        preferences: {
            excellentConditions: document.getElementById('alert-excellent')?.checked ?? true,
            seasonalReminders: document.getElementById('alert-seasonal')?.checked ?? true,
            weeklyTips: document.getElementById('alert-weekly')?.checked ?? false,
            favoriteSpots: document.getElementById('alert-favorites')?.checked ?? true,
            ...preferences
        }
    };
    
    try {
        // Sauvegarder localement
        localStorage.setItem('alert_subscription', JSON.stringify(alertPreferences));
        
        // Simuler un envoi au serveur (dans une vraie app, vous auriez un vrai endpoint)
        console.log('Abonnement sauvegardé:', alertPreferences);
        
        showNotification('✅ Abonnement aux alertes activé !', 'success');
        
        // Démarrer la vérification périodique
        startAlertChecking();
        
        return true;
    } catch (error) {
        console.error('Erreur abonnement:', error);
        showNotification('Erreur lors de l\'abonnement', 'error');
        return false;
    }
}

// Démarrer la vérification des alertes
function startAlertChecking() {
    if (alertInterval) {
        clearInterval(alertInterval);
    }
    
    // Vérifier toutes les 10 minutes en production (ici toutes les 30 secondes pour les tests)
    alertInterval = setInterval(checkForAlerts, 10 * 60 * 1000);
    
    // Vérifier immédiatement
    checkForAlerts();
}

// Arrêter la vérification des alertes
function stopAlertChecking() {
    if (alertInterval) {
        clearInterval(alertInterval);
        alertInterval = null;
    }
}

// Vérifier les nouvelles alertes
async function checkForAlerts() {
    if (!alertCheckEnabled) return;
    
    const subscription = getAlertPreferences();
    
    if (!subscription || !subscription.subscribed) {
        return;
    }
    
    try {
        // Vérifier les conditions actuelles pour l'emplacement par défaut
        const data = await fetchApiData('tunisian_prediction', {
            lat: 36.8065, // Position par défaut (Tunis)
            lon: 10.1815,
            species: 'loup',
            stable: true
        });
        
        if (data && data.scores?.final >= 85) {
            // Conditions excellentes détectées
            const alertData = {
                type: 'excellent_conditions',
                location: data.location.name,
                score: data.scores.final,
                timestamp: new Date().toISOString(),
                details: data
            };
            
            showAlertNotification(alertData);
            saveAlertToHistory(alertData);
        }
        
        // Vérifier les changements de saison (une fois par jour)
        const lastSeasonCheck = localStorage.getItem('last_season_check');
        const today = new Date().toDateString();
        
        if (!lastSeasonCheck || lastSeasonCheck !== today) {
            await checkSeasonalAlerts();
            localStorage.setItem('last_season_check', today);
        }
        
    } catch (error) {
        console.error('Erreur vérification alertes:', error);
    }
}

// Vérifier les alertes saisonnières
async function checkSeasonalAlerts() {
    const subscription = getAlertPreferences();
    
    if (!subscription?.preferences?.seasonalReminders) {
        return;
    }
    
    try {
        const seasonData = await fetchApiData('species_by_season');
        
        if (seasonData) {
            const alertData = {
                type: 'seasonal_change',
                season: seasonData.current_season,
                recommended_species: seasonData.recommended_species,
                timestamp: new Date().toISOString()
            };
            
            showSeasonalAlert(alertData);
            saveAlertToHistory(alertData);
        }
    } catch (error) {
        console.error('Erreur vérification saison:', error);
    }
}

// Afficher une notification d'alerte
function showAlertNotification(alertData) {
    if (!('Notification' in window)) {
        console.log('Notifications système non supportées');
        return;
    }
    
    // Demander la permission si nécessaire
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    if (Notification.permission === 'granted') {
        createSystemNotification(alertData);
    }
    
    // Notification interne à l'application
    createAppNotification(alertData);
}

// Afficher une alerte saisonnière
function showSeasonalAlert(alertData) {
    const notification = {
        id: Date.now(),
        title: '🌸 Changement de Saison',
        message: `Nouvelle saison: ${alertData.season}. Découvrez les espèces recommandées !`,
        type: 'seasonal',
        timestamp: new Date().toISOString(),
        read: false,
        data: alertData
    };
    
    saveAlertToHistory(notification);
    createAppNotification(notification);
}

// Créer une notification système
function createSystemNotification(alertData) {
    let title, body;
    
    switch (alertData.type) {
        case 'excellent_conditions':
            title = '🎣 Conditions de Pêche Excellentes !';
            body = `Score de ${alertData.score}% à ${alertData.location}`;
            break;
        case 'seasonal_change':
            title = '🌸 Nouvelle Saison de Pêche';
            body = `La saison ${alertData.season} a commencé !`;
            break;
        default:
            title = 'Fishing Predictor Pro';
            body = 'Nouvelle alerte disponible';
    }
    
    const notification = new Notification(title, {
        body: body,
        icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🐟</text></svg>',
        tag: 'fishing-alert',
        requireInteraction: true
    });
    
    notification.onclick = function() {
        window.focus();
        this.close();
        
        // Rediriger vers la page appropriée
        if (alertData.type === 'excellent_conditions') {
            window.location.href = '/';
        } else if (alertData.type === 'seasonal_change') {
            window.location.href = '/species_selector';
        }
    };
}

// Créer une notification dans l'application
function createAppNotification(alert) {
    const notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        // Créer le conteneur s'il n'existe pas
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            max-width: 350px;
        `;
        document.body.appendChild(container);
    }
    
    const notificationId = 'alert-' + Date.now();
    let icon, bgColor;
    
    switch (alert.type || alert.data?.type) {
        case 'excellent_conditions':
            icon = '🎣';
            bgColor = '#10b981';
            break;
        case 'seasonal_change':
            icon = '🌸';
            bgColor = '#f59e0b';
            break;
        default:
            icon = '🔔';
            bgColor = '#3b82f6';
    }
    
    const notificationElement = document.createElement('div');
    notificationElement.id = notificationId;
    notificationElement.style.cssText = `
        background: white;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        border-left: 4px solid ${bgColor};
        animation: slideInRight 0.3s ease;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        cursor: pointer;
        transition: transform 0.2s;
    `;
    
    notificationElement.innerHTML = `
        <div style="font-size: 24px;">${icon}</div>
        <div style="flex: 1;">
            <div style="font-weight: 600; margin-bottom: 5px; color: #1e293b;">${alert.title}</div>
            <div style="color: #64748b; font-size: 14px;">${alert.message}</div>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                ${new Date(alert.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
            </div>
        </div>
        <button onclick="document.getElementById('${notificationId}').remove()" 
                style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 18px;">
            ×
        </button>
    `;
    
    notificationElement.onclick = function() {
        this.remove();
        // Marquer comme lu dans l'historique
        markAlertAsRead(alert.id || Date.now());
    };
    
    notificationContainer.appendChild(notificationElement);
    
    // Supprimer automatiquement après 10 secondes
    setTimeout(() => {
        if (document.getElementById(notificationId)) {
            notificationElement.remove();
        }
    }, 10000);
}

// Sauvegarder une alerte dans l'historique
function saveAlertToHistory(alert) {
    const alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    
    const alertEntry = {
        id: Date.now(),
        ...alert,
        read: false,
        timestamp: new Date().toISOString()
    };
    
    // Limiter à 100 alertes maximum
    if (alerts.length >= 100) {
        alerts.shift();
    }
    
    alerts.push(alertEntry);
    localStorage.setItem('fishing_alerts', JSON.stringify(alerts));
    
    updateAlertBadge(alerts.length);
}

// Mettre à jour le badge de notification
function updateAlertBadge(count) {
    let badge = document.getElementById('alert-badge');
    
    if (!badge) {
        badge = document.createElement('span');
        badge.id = 'alert-badge';
        badge.style.cssText = `
            position: absolute;
            top: -5px;
            right: -5px;
            background: #ef4444;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        const alertLink = document.querySelector('a[href="/alerts"]');
        if (alertLink) {
            alertLink.style.position = 'relative';
            alertLink.appendChild(badge);
        }
    }
    
    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

// Marquer une alerte comme lue
function markAlertAsRead(alertId) {
    const alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    const alert = alerts.find(a => a.id === alertId);
    
    if (alert) {
        alert.read = true;
        localStorage.setItem('fishing_alerts', JSON.stringify(alerts));
        
        // Mettre à jour le badge
        const unreadCount = alerts.filter(a => !a.read).length;
        updateAlertBadge(unreadCount);
    }
}

// Marquer toutes les alertes comme lues
function markAllAlertsAsRead() {
    const alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    alerts.forEach(alert => alert.read = true);
    localStorage.setItem('fishing_alerts', JSON.stringify(alerts));
    updateAlertBadge(0);
}

// Obtenir les préférences d'alertes
function getAlertPreferences() {
    return JSON.parse(localStorage.getItem('alert_subscription') || '{}');
}

// Se désabonner des alertes
function unsubscribeAlerts() {
    const preferences = getAlertPreferences();
    preferences.subscribed = false;
    localStorage.setItem('alert_subscription', JSON.stringify(preferences));
    
    stopAlertChecking();
    showNotification('Désabonnement effectué', 'info');
}

// Charger l'historique des alertes
function loadAlertHistory() {
    const alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    const container = document.getElementById('alerts-history');
    
    if (!container) return;
    
    if (alerts.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-bell-slash"></i>
                <h3>Aucune alerte</h3>
                <p>Vous n'avez pas encore reçu d'alertes.</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="alerts-list">';
    
    alerts.slice().reverse().forEach(alert => {
        const date = new Date(alert.timestamp);
        const timeString = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
        const dateString = date.toLocaleDateString('fr-FR');
        
        let icon, color;
        
        switch (alert.type || alert.data?.type) {
            case 'excellent_conditions':
                icon = '🎣';
                color = '#10b981';
                break;
            case 'seasonal_change':
                icon = '🌸';
                color = '#f59e0b';
                break;
            default:
                icon = '🔔';
                color = '#3b82f6';
        }
        
        html += `
            <div class="alert-item ${alert.read ? 'read' : 'unread'}" data-id="${alert.id}">
                <div class="alert-icon" style="background: ${color}">${icon}</div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title || 'Nouvelle alerte'}</div>
                    <div class="alert-message">${alert.message || ''}</div>
                    <div class="alert-meta">
                        <span class="alert-time">${timeString}</span>
                        <span class="alert-date">${dateString}</span>
                    </div>
                </div>
                <div class="alert-actions">
                    ${!alert.read ? `
                        <button class="btn-mark-read" onclick="markAlertAsRead(${alert.id})" 
                                title="Marquer comme lu">
                            <i class="fas fa-check"></i>
                        </button>
                    ` : ''}
                    <button class="btn-delete-alert" onclick="deleteAlert(${alert.id})" 
                            title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
    
    // Mettre à jour le badge
    const unreadCount = alerts.filter(a => !a.read).length;
    updateAlertBadge(unreadCount);
}

// Supprimer une alerte
function deleteAlert(alertId) {
    let alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    alerts = alerts.filter(alert => alert.id !== alertId);
    localStorage.setItem('fishing_alerts', JSON.stringify(alerts));
    loadAlertHistory();
}

// Fonction utilitaire pour les appels API
async function fetchApiData(endpoint, params = {}) {
    try {
        const queryString = new URLSearchParams(params).toString();
        const url = `/api/${endpoint}${queryString ? '?' + queryString : ''}`;
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Erreur API ${endpoint}:`, error);
        return null;
    }
}

// Initialiser le système d'alertes au chargement
document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si l'utilisateur est abonné
    const subscription = getAlertPreferences();
    
    if (subscription && subscription.subscribed) {
        startAlertChecking();
    }
    
    // Charger l'historique si sur la page des alertes
    if (window.location.pathname.includes('alerts')) {
        loadAlertHistory();
    }
    
    // Mettre à jour le badge initial
    const alerts = JSON.parse(localStorage.getItem('fishing_alerts') || '[]');
    const unreadCount = alerts.filter(a => !a.read).length;
    updateAlertBadge(unreadCount);
});

// Styles CSS pour les notifications
const alertStyles = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .alerts-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-height: 500px;
        overflow-y: auto;
        padding: 10px;
    }
    
    .alert-item {
        background: white;
        border-radius: 10px;
        padding: 15px;
        display: flex;
        align-items: center;
        gap: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        transition: all 0.3s;
    }
    
    .alert-item.unread {
        background: #f0f9ff;
        border-left-color: #3b82f6;
    }
    
    .alert-item.read {
        opacity: 0.7;
    }
    
    .alert-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.15);
    }
    
    .alert-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: white;
    }
    
    .alert-content {
        flex: 1;
    }
    
    .alert-title {
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 5px;
    }
    
    .alert-message {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 5px;
    }
    
    .alert-meta {
        display: flex;
        gap: 15px;
        font-size: 12px;
        color: #94a3b8;
    }
    
    .alert-actions {
        display: flex;
        gap: 5px;
    }
    
    .btn-mark-read, .btn-delete-alert {
        background: none;
        border: none;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: #64748b;
        transition: all 0.3s;
    }
    
    .btn-mark-read:hover {
        background: #d1fae5;
        color: #065f46;
    }
    
    .btn-delete-alert:hover {
        background: #fee2e2;
        color: #dc2626;
    }
`;

// Injecter les styles
const styleSheet = document.createElement("style");
styleSheet.textContent = alertStyles;
document.head.appendChild(styleSheet);

// Exposer les fonctions globalement
window.subscribeToAlerts = subscribeToAlerts;
window.unsubscribeAlerts = unsubscribeAlerts;
window.markAllAlertsAsRead = markAllAlertsAsRead;
window.loadAlertHistory = loadAlertHistory;
window.deleteAlert = deleteAlert;
window.markAlertAsRead = markAlertAsRead;