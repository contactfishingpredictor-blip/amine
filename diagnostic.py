# diagnostic.py (version corrigée)
#!/usr/bin/env python3
"""
Script de diagnostic Gmail pour Fishing Predictor Pro
"""
import os
import sys
import json

print("🔍 DIAGNOSTIC GMAIL FISHING PREDICTOR PRO")
print("="*50)

# 1. Vérifier les variables d'environnement
print("\n1. 📋 VARIABLES D'ENVIRONNEMENT:")
env_vars = ['GMAIL_USER', 'GMAIL_APP_PASSWORD', 'EMAIL_FROM']
for var in env_vars:
    value = os.getenv(var, 'NON DÉFINI')
    if value and value != 'NON DÉFINI':
        if var == 'GMAIL_APP_PASSWORD':
            masked = value[:4] + '*' * (len(value)-8) + value[-4:] if len(value) > 8 else '***'
            print(f"   {var}: ✅ {masked} ({len(value)} caractères)")
        else:
            print(f"   {var}: ✅ {value}")
    else:
        print(f"   {var}: ❌ {value}")

# 2. Vérifier le fichier .env (avec UTF-8)
print("\n2. 📁 FICHIER .env:")
env_files = ['.env', '.env.local', '.env.dev']
found = False
for env_file in env_files:
    if os.path.exists(env_file):
        try:
            # Essayer UTF-8 d'abord
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"   ✅ Trouvé: {env_file} (UTF-8)")
        except UnicodeDecodeError:
            try:
                # Essayer latin-1
                with open(env_file, 'r', encoding='latin-1') as f:
                    content = f.read()
                print(f"   ⚠️ Trouvé: {env_file} (latin-1) - RECOMMANDE: Convertir en UTF-8")
            except:
                print(f"   ❌ Trouvé: {env_file} (encodage inconnu)")
        
        found = True
        
        # Vérifier si Gmail est configuré
        if 'GMAIL_APP_PASSWORD' in content:
            print(f"   🔑 App Password présent dans {env_file}")
        
        # Afficher les lignes Gmail
        for line in content.split('\n'):
            if 'GMAIL' in line or 'EMAIL' in line:
                print(f"   📝 {line.strip()}")
        break

if not found:
    print("   ❌ Aucun fichier .env trouvé!")

# 3. Importer et vérifier la configuration
print("\n3. ⚙️ CONFIGURATION APPLICATION:")
try:
    from config import config
    
    print(f"   App: {config.APP_NAME} v{config.APP_VERSION}")
    print(f"   GMAIL_USER: {config.GMAIL_USER or '❌ Non défini'}")
    
    if config.GMAIL_APP_PASSWORD:
        length = len(config.GMAIL_APP_PASSWORD)
        if ' ' in config.GMAIL_APP_PASSWORD:
            print(f"   GMAIL_APP_PASSWORD: ❌ CONTIENT DES ESPACES! ({length} caractères)")
            print(f"      CORRECTION: '{config.GMAIL_APP_PASSWORD.replace(' ', '')}'")
        elif length == 16:
            print(f"   GMAIL_APP_PASSWORD: ✅ {length} caractères (OK)")
        else:
            print(f"   GMAIL_APP_PASSWORD: ❌ {length} caractères (ATTENDU: 16)")
    else:
        print(f"   GMAIL_APP_PASSWORD: ❌ Non défini")
    
    # Vérifier la configuration
    config_status = config.check_gmail_config()
    print(f"   Status: {'✅ PRÊT' if config_status['gmail_ready'] else '❌ NON PRÊT'}")
    
except ImportError as e:
    print(f"   ❌ Erreur d'import: {e}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")

# 4. Tester la connexion SMTP
print("\n4. 🔌 TEST CONNEXION SMTP:")
try:
    import smtplib
    import socket
    
    # Test de connexion réseau
    socket.setdefaulttimeout(10)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('smtp.gmail.com', 587))
    
    if result == 0:
        print("   ✅ Port 587 accessible")
    else:
        print("   ❌ Port 587 bloqué ou inaccessible")
    
    sock.close()
    
except Exception as e:
    print(f"   ❌ Erreur test réseau: {e}")

print("\n" + "="*50)
print("🎯 INSTRUCTIONS POUR GÉNÉRER APP PASSWORD:")
print("1. Allez sur: https://myaccount.google.com/security")
print("2. Activez 'Vérification en 2 étapes'")
print("3. Cliquez sur 'Mots de passe d'application'")
print("4. Nommez-le 'Fishing Predictor'")
print("5. Copiez les 16 caractères SANS ESPACES")
print("6. Collez dans GMAIL_APP_PASSWORD dans .env")
print("="*50)

# 5. Vérifier la longueur du mot de passe
try:
    if 'config' in locals() and config.GMAIL_APP_PASSWORD:
        pw = config.GMAIL_APP_PASSWORD
        if ' ' in pw:
            print("\n⚠️  ATTENTION: Votre App Password contient des ESPACES!")
            print("   Corrigez-le en supprimant les espaces:")
            print(f"   AVANT: '{pw}'")
            print(f"   APRÈS: '{pw.replace(' ', '')}'")
        elif len(pw) < 16:
            print(f"\n⚠️  ATTENTION: Seulement {len(pw)} caractères (16 requis)")
except:
    pass

print("\n✅ Diagnostic terminé.")