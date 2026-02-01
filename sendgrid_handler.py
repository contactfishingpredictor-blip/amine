"""
Handler pour l'envoi d'emails via SendGrid - VERSION CORRIGÉE
"""
import os
import json
import hashlib
from datetime import datetime
import requests
from typing import Dict, Any, Optional

from config import config

class SendGridHandler:
    """Gestionnaire SendGrid pour l'envoi d'emails - VERSION FONCTIONNELLE"""
    
    def __init__(self):
        self.api_key = config.SENDGRID_API_KEY
        
        # CRITIQUE : Toujours utiliser un expéditeur vérifié (votre Gmail)
        # 'alerts@fishingpredictor.pro' n'est PAS vérifié dans SendGrid
        self.from_email = 'contactfishingpredictor@gmail.com'  # FORCÉ À GMAIL
        self.from_name = config.EMAIL_FROM_NAME or 'Fishing Predictor Pro'
        
        print(f"🔧 SendGrid configuré avec expéditeur: {self.from_email}")
        
        # Vérification de la clé
        if not self.is_configured():
            print("⚠️ ATTENTION: Clé SendGrid invalide ou manquante")
    
    def is_configured(self) -> bool:
        """Vérifie si SendGrid est configuré avec une clé valide"""
        return bool(self.api_key and self.api_key.startswith('SG.'))
    
    def send_email(self, to_email: str, subject: str, html_content: str, 
                  text_content: str = None) -> Dict[str, Any]:
        """
        Envoie un email via SendGrid API - VERSION SIMPLIFIÉE ET FONCTIONNELLE
        """
        try:
            if not self.is_configured():
                print("❌ SendGrid non configuré")
                return {
                    'success': False,
                    'error': 'SendGrid non configuré',
                    'simulated': False
                }
            
            print(f"📧 Préparation email SendGrid pour: {to_email}")
            
            # URL SendGrid
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Construire le payload SIMPLIFIÉ
            payload = {
                "personalizations": [{
                    "to": [{
                        "email": to_email,
                        "name": to_email.split('@')[0]
                    }]
                }],
                "from": {
                    "email": self.from_email,  # TOUJOURS contactfishingpredictor@gmail.com
                    "name": self.from_name
                },
                "subject": subject,
                "content": [
                    {
                        "type": "text/html",
                        "value": html_content
                    }
                ]
            }
            
            # Ajouter texte brut si fourni
            if text_content:
                payload["content"].insert(0, {
                    "type": "text/plain",
                    "value": text_content
                })
            
            # Envoyer la requête avec timeout court
            print(f"🚀 Envoi SendGrid à: {to_email}")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            
            # Analyser la réponse
            if response.status_code in [200, 202]:
                print(f"✅ SendGrid SUCCÈS: Email envoyé à {to_email}")
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'message': 'Email envoyé avec succès',
                    'provider': 'SendGrid'
                }
            else:
                # Erreur SendGrid
                error_msg = f"Erreur SendGrid ({response.status_code})"
                try:
                    error_data = response.json()
                    if 'errors' in error_data:
                        error_msg += f": {error_data['errors'][0].get('message', 'Unknown')}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'provider': 'SendGrid'
                }
                
        except requests.exceptions.Timeout:
            print("❌ Timeout SendGrid")
            return {
                'success': False,
                'error': 'Timeout - Serveur SendGrid non accessible',
                'simulated': False
            }
        except Exception as e:
            print(f"❌ Exception SendGrid: {type(e).__name__}: {str(e)[:100]}")
            return {
                'success': False,
                'error': str(e),
                'simulated': False
            }
    
    def send_confirmation_email(self, email: str, confirmation_id: str) -> Dict[str, Any]:
        """Envoie un email de confirmation d'abonnement - VERSION CORRIGÉE"""
        try:
            print(f"🎣 Préparation confirmation pour: {email}")
            
            timestamp = datetime.now().strftime('%d/%m/%Y à %H:%M')
            
            # Contenu HTML de l'email
            html_content = self._generate_confirmation_html(email, confirmation_id, timestamp)
            
            # Version texte simple
            text_content = self._generate_confirmation_text(email, confirmation_id, timestamp)
            
            # Envoyer l'email via SendGrid
            result = self.send_email(
                to_email=email,
                subject="🎣 Confirmation d'abonnement - Fishing Predictor Pro",
                html_content=html_content,
                text_content=text_content
            )
            
            # Sauvegarder le log
            self._save_email_log(
                email, 'confirmation', confirmation_id, 
                result.get('success', False), 
                result.get('status_code', 0),
                result.get('error', '')
            )
            
            return result
            
        except Exception as e:
            print(f"❌ Erreur préparation email: {e}")
            return {
                'success': False, 
                'error': str(e),
                'simulated': False
            }
    
    def _generate_confirmation_html(self, email: str, confirmation_id: str, 
                                   timestamp: str) -> str:
        """Génère le contenu HTML de l'email de confirmation"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Confirmation d'abonnement - Fishing Predictor Pro</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 10px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 0.9em; }}
                .confirmation-id {{ background: #e0f2fe; padding: 15px; border-radius: 5px; font-family: monospace; font-weight: bold; text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎣 Fishing Predictor Pro</h1>
                <h2>Confirmation d'abonnement</h2>
            </div>
            <div class="content">
                <p>Bonjour pêcheur,</p>
                
                <p>Merci de vous être abonné aux alertes de pêche de <strong>Fishing Predictor Pro</strong> !</p>
                
                <p><strong>✅ Votre abonnement a été confirmé avec succès.</strong></p>
                
                <div class="confirmation-id">
                    ID de confirmation : {confirmation_id}<br>
                    Date : {timestamp}
                </div>
                
                <p>Vous recevrez désormais des alertes par email lorsque :</p>
                <ul>
                    <li>🎯 Les conditions de pêche seront excellentes (score ≥ 85%)</li>
                    <li>🌸 Les saisons de pêche changent</li>
                    <li>📅 Des événements de pêche spéciaux sont prévus</li>
                </ul>
                
                <p style="text-align: center;">
                    <a href="https://fishing-activity.onrender.com" class="button">Consulter les prédictions</a>
                </p>
                
                <p><strong>Pour gérer vos préférences ou vous désabonner :</strong><br>
                Visitez la page <a href="https://fishing-activity.onrender.com/alerts">Alertes Intelligentes</a> ou cliquez sur le lien de désabonnement présent dans chaque email.</p>
                
                <p>Bonne pêche ! 🐟</p>
                
                <p><em>L'équipe Fishing Predictor Pro</em></p>
            </div>
            <div class="footer">
                <p>Cet email a été envoyé à {email}</p>
                <p>© {datetime.now().year} Fishing Predictor Pro - Tous droits réservés</p>
                <p><small>Vous recevez cet email car vous vous êtes abonné aux alertes sur notre site.</small></p>
            </div>
        </body>
        </html>
        """
    
    def _generate_confirmation_text(self, email: str, confirmation_id: str, 
                                   timestamp: str) -> str:
        """Génère le contenu texte de l'email de confirmation"""
        return f"""
        Confirmation d'abonnement - Fishing Predictor Pro
        
        Bonjour,
        
        Merci de vous être abonné aux alertes de pêche de Fishing Predictor Pro !
        
        ✅ Votre abonnement a été confirmé avec succès.
        
        ID de confirmation : {confirmation_id}
        Date : {timestamp}
        
        Vous recevrez désormais des alertes par email lorsque les conditions de pêche seront excellentes.
        
        Pour gérer vos préférences ou vous désabonner :
        Visitez https://fishing-activity.onrender.com/alerts ou cliquez sur le lien de désabonnement présent dans chaque email.
        
        Bonne pêche !
        
        L'équipe Fishing Predictor Pro
        
        ---
        Cet email a été envoyé à {email}
        © {datetime.now().year} Fishing Predictor Pro
        """
    
    def _save_email_log(self, email: str, email_type: str, confirmation_id: str, 
                       sent: bool, status_code: int = 0, error: str = ''):
        """Sauvegarde les logs d'emails envoyés"""
        try:
            log_file = config.EMAIL_LOGS_FILE
            os.makedirs(config.DATA_DIR, exist_ok=True)
            
            logs = []
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
            
            log_entry = {
                'to': email,
                'type': email_type,
                'confirmation_id': confirmation_id,
                'sent': sent,
                'status_code': status_code,
                'error': error[:200] if error else '',
                'timestamp': datetime.now().isoformat(),
                'provider': 'SendGrid',
                'from_email': self.from_email
            }
            
            logs.append(log_entry)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            status = '✅ Envoyé' if sent else f'❌ Échec ({status_code})'
            print(f"📋 Log email sauvegardé: {email} - {status}")
            
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde log email: {e}")

# Instance globale
sendgrid_handler = SendGridHandler()

# Test rapide
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TEST SENDGRID HANDLER")
    print("="*60)
    
    print(f"Clé API: {'✅' if sendgrid_handler.is_configured() else '❌'}")
    print(f"Expéditeur: {sendgrid_handler.from_email}")
    
    if sendgrid_handler.is_configured():
        print("\n🔍 Test de connexion SendGrid...")
        test_result = sendgrid_handler.send_email(
            to_email="test@example.com",
            subject="Test SendGrid",
            html_content="<h1>Test</h1><p>Ceci est un test.</p>"
        )
        print(f"Résultat: {test_result}")
