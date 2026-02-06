"""
Service d'envoi d'emails Gmail pour Fishing Predictor Pro
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from config import config

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GmailSender:
    """Gestionnaire d'emails Gmail"""
    
    def __init__(self):
        self.config = config.GMAIL_CONFIG
        self.sender = config.GMAIL_USER
        
    def send_email(self, to_email, subject, html_content, text_content=None):
        """
        Envoi d'email via Gmail SMTP
        
        Args:
            to_email: Destinataire
            subject: Sujet
            html_content: Contenu HTML
            text_content: Contenu texte (optionnel)
            
        Returns:
            bool: True si réussi, False sinon
        """
        # Vérifier la configuration
        if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
            logger.error("❌ Configuration Gmail manquante")
            return False
        
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{config.EMAIL_FROM_NAME} <{config.GMAIL_USER}>"
        msg['To'] = to_email
        
        # Ajouter contenu texte si fourni
        if text_content:
            part1 = MIMEText(text_content, 'plain')
            msg.attach(part1)
        
        # Ajouter contenu HTML
        part2 = MIMEText(html_content, 'html')
        msg.attach(part2)
        
        try:
            logger.info(f"📤 Tentative d'envoi à {to_email}")
            
            # Connexion SMTP
            server = smtplib.SMTP(
                self.config['smtp_server'], 
                self.config['smtp_port'],
                timeout=self.config['timeout']
            )
            
            server.ehlo()
            server.starttls()  # Chiffrement TLS
            server.ehlo()
            
            # Authentification
            server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
            
            # Envoi
            server.sendmail(config.GMAIL_USER, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Email envoyé avec succès à {to_email}")
            self._log_email(to_email, subject, "success")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Erreur d'authentification Gmail: {e}")
            logger.error("🔧 Vérifie ton App Password (16 caractères sans espaces)")
            self._log_email(to_email, subject, f"auth_error: {str(e)}")
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"❌ Erreur SMTP: {e}")
            self._log_email(to_email, subject, f"smtp_error: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erreur inattendue: {e}")
            self._log_email(to_email, subject, f"unexpected_error: {str(e)}")
            return False
    
    def test_connection(self):
        """Test de connexion Gmail"""
        try:
            logger.info("🔍 Test de connexion Gmail...")
            server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
            server.quit()
            logger.info("✅ Connexion Gmail OK")
            return True
        except Exception as e:
            logger.error(f"❌ Test connexion échoué: {e}")
            return False
    
    def send_test_email(self, to_email=None):
        """Envoie un email de test"""
        test_email = to_email or config.GMAIL_USER
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success {{ color: #4CAF50; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎣 Fishing Predictor Pro</h1>
                    <p>Test d'envoi d'email</p>
                </div>
                <div class="content">
                    <h2>✅ Test Réussi !</h2>
                    <p>Votre configuration Gmail fonctionne correctement.</p>
                    <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>De:</strong> {config.GMAIL_USER}</p>
                    <p><strong>À:</strong> {test_email}</p>
                    <p class="success">Le système d'envoi d'emails est opérationnel !</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(
            to_email=test_email,
            subject="🎣 Test Gmail Fishing Predictor Pro",
            html_content=html,
            text_content=f"Test Gmail Fishing Predictor Pro\nDate: {datetime.now()}\nDe: {config.GMAIL_USER}\nÀ: {test_email}"
        )
    
    def _log_email(self, to_email, subject, status):
        """Log l'envoi d'email"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'to': to_email,
                'subject': subject,
                'status': status,
                'sender': config.GMAIL_USER
            }
            
            # Sauvegarder dans le fichier de logs
            import json
            import os
            
            logs_file = config.EMAIL_LOGS_FILE
            os.makedirs(os.path.dirname(logs_file), exist_ok=True)
            
            logs = []
            if os.path.exists(logs_file):
                with open(logs_file, 'r') as f:
                    try:
                        logs = json.load(f)
                    except:
                        logs = []
            
            logs.append(log_entry)
            
            # Garder seulement les 100 derniers logs
            if len(logs) > 100:
                logs = logs[-100:]
            
            with open(logs_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            logger.error(f"Erreur lors du log: {e}")

# Instance globale
gmail_sender = GmailSender()