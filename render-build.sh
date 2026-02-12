#!/bin/bash  
set -e  
  
echo "?? DêPLOIEMENT FISHING PREDICTOR PRO"  
echo "?? Python version:"  
python --version  
  
echo "?? Installation des dÇpendances..."  
pip install --upgrade pip  
pip install -r requirements.txt  
  
echo "? BUILD TERMINê AVEC SUCC‘S !"  
