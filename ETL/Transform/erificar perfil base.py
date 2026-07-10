"""
VERIFICACIÓN - confirma qué datos de "rendimiento" (no solo biografía)
están disponibles en la página de PERFIL BASE (profil/spieler/<id>),
que ya sabemos es estática (no requiere JavaScript), como alternativa
a 'leistungsdaten' que sí lo requiere.
"""

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

URL = "https://www.transfermarkt.co.uk/emiliano-martinez/profil/spieler/111873"

resp = requests.get(URL, headers=HEADERS, timeout=20)
print(f"Código de respuesta: {resp.status_code}")
print(f"Ocurrencias de '<table': {resp.text.count('<table')}")

soup = BeautifulSoup(resp.text, "lxml")

# Buscamos específicamente el bloque de "Caps/Goals" que vimos en pantalla
print("\n--- BÚSQUEDA DE 'Caps' / 'International' EN EL HTML ---")
for texto_buscar in ["Caps", "International", "caps", "Current international"]:
    elementos = soup.find_all(string=lambda t: t and texto_buscar in t)
    print(f"  '{texto_buscar}': {len(elementos)} coincidencias")
    for el in elementos[:3]:
        print(f"     contexto: '{el.strip()[:80]}'")

print("\n--- TODAS LAS CLASES 'li' EN EL HEADER DE DATOS (data-header) ---")
header = soup.find("div", class_=lambda c: c and "data-header" in c)
if header:
    for li in header.find_all("li")[:20]:
        print(f"  {li.get_text(strip=True)[:100]}")
else:
    print("  No se encontró el contenedor data-header.")

# Búsqueda directa: encontrar el elemento que contiene "Caps/Goals:" y
# extraer el VALOR numérico que lo acompaña (no solo confirmar el texto)
print("\n--- VALOR REAL DE 'Caps/Goals' ---")
elemento_caps = soup.find(string=lambda t: t and "Caps/Goals" in t)
if elemento_caps:
    padre = elemento_caps.find_parent()
    print(f"Tag del elemento que contiene el texto: <{padre.name}> class={padre.get('class')}")
    print(f"Texto completo del padre: '{padre.get_text(strip=True)}'")

    # El valor suele estar en un elemento hermano o en el siguiente <span>
    contenedor = padre.find_parent("li") or padre.find_parent("div")
    if contenedor:
        print(f"\nContenedor más amplio (li o div padre):")
        print(f"  Texto completo: '{contenedor.get_text(strip=True)}'")
        print(f"  HTML crudo (primeros 500 caracteres):")
        print(f"  {str(contenedor)[:500]}")