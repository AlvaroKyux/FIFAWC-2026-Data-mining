"""
test_gdelt_fuente_v4_final.py
------------------------------
Prueba MINIMA de una sola peticion, para no seguir agotando el limite de
tasa de GDELT. Objetivo unico: verificar si el 0 de resultados en espanol
se debia a falta de acentos/tildes en las queries anteriores (v1-v3 usaban
"campeon", "Mundial 2026" sin caracteres especiales codificados correctamente).

IMPORTANTE: correr esto SOLO despues de esperar al menos 10-15 minutos
desde la ultima ejecucion, para dar tiempo a que el throttling de GDELT
se libere. No correr en loop ni repetir varias veces seguidas.

Requiere: pip install requests --break-system-packages
"""

import requests
import json
from datetime import datetime, timezone, timedelta

BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

DIAS_ATRAS = 30
FECHA_FIN = datetime.now(timezone.utc)
FECHA_INICIO = FECHA_FIN - timedelta(days=DIAS_ATRAS)
FORMATO_GDELT = "%Y%m%d%H%M%S"

# Query con tildes reales (UTF-8), dejando que requests haga el URL-encoding
# correctamente via el parametro 'params' (no concatenacion manual de string).
QUERY = '"selección española" sourcelang:spa'

params = {
    "query": QUERY,
    "mode": "artlist",
    "format": "json",
    "maxrecords": 30,
    "startdatetime": FECHA_INICIO.strftime(FORMATO_GDELT),
    "enddatetime": FECHA_FIN.strftime(FORMATO_GDELT),
    "sort": "hybridrel",
}

print(f"Query: {QUERY}")
print(f"Rango: {FECHA_INICIO.date()} a {FECHA_FIN.date()}")
print("Ejecutando UNA sola peticion...")

resp = requests.get(BASE_URL, params=params, timeout=20)
print(f"Status code: {resp.status_code}")
print(f"URL real enviada: {resp.url}")

if resp.status_code == 200:
    data = resp.json()
    articulos = data.get("articles", [])
    print(f"\nArticulos devueltos: {len(articulos)}")
    for art in articulos[:10]:
        print(f"  {art.get('domain')} | {art.get('language')} | {art.get('title')}")

    with open("gdelt_prueba_final.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\nGuardado en: gdelt_prueba_final.json")
else:
    print(f"Error: {resp.text[:400]}")