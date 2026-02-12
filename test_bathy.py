# test_bathy.py
from bathymetry_gebco import gebco

# Test tes spots
spots = [
    (36.85, 11.09, "Kélibia"),
    (37.16, 10.18, "Ghar El Melh"),
    (36.80, 10.18, "Tunis"),
    (37.27, 9.87, "Bizerte"),
    (36.40, 10.60, "Hammamet"),
    (35.82, 10.64, "Sousse"),
    (33.80, 10.85, "Djerba"),
]

print("\n" + "="*60)
print("🏝️  TEST BATHYMÉTRIE TUNISIE")
print("="*60)

for lat, lon, nom in spots:
    result = gebco.get_depth_with_fallback(lat, lon)
    print(f"\n📍 {nom}: ({lat}, {lon})")
    print(f"   Profondeur: {result['depth']}m")
    print(f"   Source: {result['source']}")
    print(f"   Confiance: {result['confidence']*100}%")