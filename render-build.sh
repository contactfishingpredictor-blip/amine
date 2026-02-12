#!/bin/bash
set -e

echo "🐍 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build terminé !"