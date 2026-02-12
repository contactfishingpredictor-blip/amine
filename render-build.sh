#!/bin/bash
set -e

echo "🚀 DÉBUT DU BUILD RENDER"
echo "🐍 Version Python:"
python --version

echo "📦 Installation des dépendances SCIENTIFIQUES en premier..."
pip install --upgrade pip
pip install numpy==1.24.3
pip install scipy==1.10.1
pip install pandas==2.0.3

echo "📦 Installation des dépendances GÉOSPATIALES..."
pip install xarray==2023.7.0
pip install netCDF4==1.6.5
pip install cftime==1.6.3

echo "📦 Installation du RESTE sans résolution stricte..."
pip install --no-deps -r requirements.txt

echo "📦 Installation des dépendances MANQUANTES (forcées)..."
pip install Flask==3.1.2
pip install gunicorn==20.1.0
pip install geopy==2.4.1
pip install requests==2.32.3
pip install python-dotenv==1.0.1
pip install secure-smtplib==0.1.1
pip install email-validator==2.1.2

echo "✅ BUILD TERMINÉ AVEC SUCCÈS !"