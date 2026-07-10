"""
VALIDACIÓN RÁPIDA - PASO INTERMEDIO antes de correr el extractor completo.

Hace UNA SOLA petición (a la confederación de Europa) para confirmar que
la lógica de extracción de país/country_id/href funciona correctamente
con la estructura HTML real, antes de comprometernos a las 4 peticiones
de confederación + 48 de selección + 48 de plantilla.

Si esto funciona y los nombres/hrefs se ven correctos, entonces sí
lanzamos 02_transfermarkt_plantillas.py completo.
"""

import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.transfermarkt.co.uk"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

print("Esperando 6 segundos antes de la petición de prueba...")
time.sleep(6)

resp = requests.get(f"{BASE_URL}/wettbewerbe/europa", headers=HEADERS, timeout=20)
print(f"Código de respuesta: {resp.status_code}\n")

if resp.status_code != 200:
    print("❌ No se pudo continuar la validación, revisar bloqueo de red.")
    exit()

soup = BeautifulSoup(resp.text, "lxml")
filas = soup.select("table.items tbody tr.odd, table.items tbody tr.even")
print(f"Filas encontradas en la tabla: {len(filas)}\n")

paises = []
for fila in filas:
    celdas = fila.find_all("td")
    if len(celdas) < 2:
        continue

    img_bandera = celdas[1].find("img")
    nombre_pais = img_bandera.get("title") if img_bandera else None

    primera_celda = celdas[0]
    sub_tabla = primera_celda.find("table")
    country_id = None
    if sub_tabla:
        tds_sub_tabla = sub_tabla.find_all("td")
        if len(tds_sub_tabla) >= 2:
            link_id = tds_sub_tabla[1].find("a")
            if link_id:
                href_id = link_id.get("href", "")
                posible_id = href_id.rstrip("/").split("/")[-1]
                if posible_id.isdigit():
                    country_id = posible_id

    paises.append({"nombre": nombre_pais, "country_id": country_id})

print("=== PRIMEROS 10 PAÍSES ENCONTRADOS ===")
for p in paises[:10]:
    print(p)

print(f"\n=== DIAGNÓSTICO ===")
print(f"Total filas procesadas: {len(paises)}")
print(f"Nombres vacíos: {sum(1 for p in paises if not p['nombre'])}")
print(f"country_id vacíos: {sum(1 for p in paises if not p['country_id'])}")