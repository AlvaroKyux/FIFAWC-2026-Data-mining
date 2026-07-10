"""
PRUEBA DECISIVA - hace la petición exacta que usará el extractor real
(con la librería `requests`, no el navegador) y guarda la respuesta
cruda en disco para inspección directa.

Esto elimina la ambigüedad de "Guardar como HTML" o "Ver código fuente"
del navegador, que pueden comportarse distinto a una petición programática
simple. Si la tabla aparece AQUÍ, el extractor va a funcionar. Si no
aparece aquí tampoco, confirmamos que se necesita otro enfoque (navegador
automatizado, similar a lo que tuvimos que hacer con FBref).
"""

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

URL = "https://www.transfermarkt.co.uk/emiliano-martinez/leistungsdaten/spieler/111873"

resp = requests.get(URL, headers=HEADERS, timeout=20)
print(f"Código de respuesta: {resp.status_code}")
print(f"Longitud de la respuesta: {len(resp.text)} caracteres")
print(f"Ocurrencias de '<table': {resp.text.count('<table')}")
print(f"Ocurrencias de 'class=\"items\"': {resp.text.count('class=\"items\"')}")

# Guardamos la respuesta cruda exacta que ve Python, para inspección directa
with open("respuesta_requests_leistungsdaten.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print("\n✅ Respuesta guardada en 'respuesta_requests_leistungsdaten.html'")
print("   Ábrela en el navegador o en VS Code para inspeccionarla directamente.")