from wekeo_handler import get_wind_data, test_connection

print("Test connexion WEkEO:", test_connection())
lat, lon = 36.8065, 10.1815
print(f"Données vent pour ({lat}, {lon}):")
print(get_wind_data(lat, lon))