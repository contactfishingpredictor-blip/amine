"""
Service d'envoi d'emails Gmail optimisé pour Render
Version Render-compatible avec support ports 465/587
"""

import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)

class GmailSender:
    """Service d'envoi d'emails Gmail optimisé pour Render"""
    
    def __init__(self):
        self.gmail_user = config.GMAIL_USER
        self.gmail_password = config.GMAIL_APP_PASSWORD
        self.email_from = config.EMAIL_FROM
        self.email_from_name = config.EMAIL_FROM_NAME
        
    def send_email(self, to_email, subject, html_content, text_content=None):
        """
        Envoie un email via Gmail - Version optimisée Render
        Essaie d'abord le port 465 (SSL), puis 587 (TLS) comme fallback
        """
        # Vérifier configuration
        if not self.gmail_user or not self.gmail_password:
            logger.error("❌ Configuration Gmail manquante")
            return False
        
        try:
            # Créer le message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = to_email
            
            # Ajouter contenu texte si fourni
            if text_content:
                msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            
            # Ajouter contenu HTML
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 🔥 STRATÉGIE POUR RENDER:
            # 1. Essayer d'abord le port 465 (SSL) - le plus compatible
            # 2. Si échec, essayer le port 587 (TLS)
            # 3. Si les deux échouent, Render bloque probablement SMTP
            
            # Tentative 1: Port 465 avec SSL
            try:
                logger.info(f"📤 Tentative envoi à {to_email} via port 465 (SSL)...")
                server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30)
                server.login(self.gmail_user, self.gmail_password)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"✅ Email envoyé à {to_email} (port 465 SSL)")
                self._log_email(to_email, subject, "success_465")
                return True
                
            except Exception as ssl_error:
                logger.warning(f"⚠️ Port 465 échoué, tentative port 587: {ssl_error}")
                
                # Tentative 2: Port 587 avec TLS
                try:
                    logger.info(f"📤 Tentative envoi à {to_email} via port 587 (TLS)...")
                    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=30)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.gmail_user, self.gmail_password)
                    server.send_message(msg)
                    server.quit()
                    
                    logger.info(f"✅ Email envoyé à {to_email} (port 587 TLS)")
                    self._log_email(to_email, subject, "success_587")
                    return True
                    
                except Exception as tls_error:
                    logger.error(f"❌ Les deux ports ont échoué: {tls_error}")
                    self._log_email(to_email, subject, f"failed_both: {str(tls_error)[:100]}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Erreur générale envoi email: {e}")
            self._log_email(to_email, subject, f"error: {str(e)[:100]}")
            return False
    
    def test_connection(self):
        """Teste la connexion Gmail - Version Render"""
        if not self.gmail_user or not self.gmail_password:
            logger.error("Configuration Gmail manquante")
            return False
        
        # Tester port 465 d'abord
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
            server.login(self.gmail_user, self.gmail_password)
            server.quit()
            logger.info("✅ Test connexion Gmail OK (port 465 SSL)")
            return True
        except Exception as ssl_error:
            logger.warning(f"Port 465 échoué: {ssl_error}")
        
        # Tester port 587 comme fallback
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.gmail_user, self.gmail_password)
            server.quit()
            logger.info("✅ Test connexion Gmail OK (port 587 TLS)")
            return True
        except Exception as tls_error:
            logger.error(f"Tous les ports ont échoué: {tls_error}")
            return False
    
    def send_test_email(self, to_email=None):
        """Envoie un email de test"""
        target_email = to_email or self.gmail_user
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test Email - Fishing Predictor Pro</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success {{ color: #10b981; font-weight: bold; }}
                .info {{ background: #dbeafe; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎣 Fishing Predictor Pro</h1>
                <h2>Test d'envoi d'email</h2>
            </div>
            <div class="content">
                <p class="success">✅ Test réussi !</p>
                <p>Cet email confirme que votre configuration Gmail fonctionne correctement sur Render.</p>
                
                <div class="info">
                    <p><strong>Détails:</strong></p>
                    <p>📧 De: {self.email_from}</p>
                    <p>📧 À: {target_email}</p>
                    <p>🕐 Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    <p>🌐 Environnement: Production (Render)</p>
                </div>
                
                <p>Le système d'alertes de pêche est maintenant opérationnel !</p>
                <p>Vous recevrez des alertes lorsque les conditions de pêche seront optimales.</p>
                
                <p><em>L'équipe Fishing Predictor Pro</em></p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Test d'envoi d'email - Fishing Predictor Pro
        
        ✅ Test réussi !
        
        Cet email confirme que votre configuration Gmail fonctionne correctement sur Render.
        
        Détails:
        - De: {self.email_from}
        - À: {target_email}
        - Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        - Environnement: Production (Render)
        
        Le système d'alertes de pêche est maintenant opérationnel !
        
        L'équipe Fishing Predictor Pro
        """
        
        return self.send_email(
            to_email=target_email,
            subject="🎣 TEST - Configuration Gmail OK - Fishing Predictor Pro",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_confirmation_email(self, email, confirmation_id):
        """Envoie un email de confirmation d'abonnement"""
        timestamp = datetime.now().strftime('%d/%m/%Y à %H:%M')
        
        html_content = f"""
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
                <p>Bonjour,</p>
                
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
                <p>© 2024 Fishing Predictor Pro - Tous droits réservés</p>
                <p><small>Vous recevez cet email car vous vous êtes abonné aux alertes sur notre site.</small></p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
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
        © 2026 Fishing Predictor Pro
        """
        
        return self.send_email(
            to_email=email,
            subject="🎣 Confirmation d'abonnement aux alertes - Fishing Predictor Pro",
            html_content=html_content,
            text_content=text_content
        )
    
    def _log_email(self, to_email, subject, status):
        """Sauvegarde les logs d'emails"""
        try:
            logs_file = config.EMAIL_LOGS_FILE
            os.makedirs(os.path.dirname(logs_file), exist_ok=True)
            
            logs = []
            if os.path.exists(logs_file):
                with open(logs_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            
            log_entry = {
                'to': to_email,
                'subject': subject,
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'gmail_user': self.gmail_user,
                'server': 'Gmail SMTP (Render)'
            }
            
            logs.append(log_entry)
            
            # Garder seulement les 100 derniers logs
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(logs_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Erreur lors du log email: {e}")

# Instance globale
gmail_sender = GmailSender()


# Fonctions de compatibilité (pour app.py existant)
def send_confirmation_email_gmail(email, confirmation_id):
    """Fonction wrapper pour compatibilité avec app.py existant"""
    return gmail_sender.send_confirmation_email(email, confirmation_id)

def test_gmail_configuration():
    """Test de configuration pour Render"""
    return gmail_sender.test_connection()