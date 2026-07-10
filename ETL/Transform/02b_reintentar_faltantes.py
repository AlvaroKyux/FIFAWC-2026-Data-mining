"""
Reintento puntual para las selecciones que fallaron en la corrida completa:
Bosnia and Herzegovina, Czech Republic, Turkey.

En vez de repetir las 210 peticiones del descubrimiento completo, usamos
directamente los hrefs ya conocidos de Transfermarkt para estas 3
selecciones (confirmados manualmente), y solo reintentamos la extracción
de su plantilla.

Requiere las mismas funciones del script 02 (extraer_plantilla,
guardar_plantilla, peticion_segura). Este script las reimplementa de
forma mínima para no depender de imports relativos complicados.
"""

import time
import re
import json
from pathlib import Path

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
PAUSA_SEGUNDOS = 6
RAW_DIR = Path("raw/transfermarkt_plantillas")
RAW_DIR.mkdir(parents=True, exist_ok=True)

# hrefs CONFIRMADOS mediante búsqueda (no asumidos a partir de un patrón
# de idioma alemán, que resultó incorrecto en el primer intento)
SELECCIONES_FALTANTES = [
    {"nombre": "Bosnia and Herzegovina", "href": "/bosnien-herzegowina/startseite/verein/3446"},
    {"nombre": "Czech Republic", "href": "/tschechien/startseite/verein/3445"},
    {"nombre": "Turkey", "href": "/turkiye/startseite/verein/3381"},
]


def peticion_segura(url: str, etiqueta: str = ""):
    print(f"  -> {etiqueta or url}")
    time.sleep(PAUSA_SEGUNDOS)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            print(f"     ⚠️ Código de respuesta: {resp.status_code}")
            return None
        return resp
    except requests.exceptions.RequestException as e:
        print(f"     ❌ Error de red: {e}")
        return None


def extraer_plantilla(href_seleccion: str, nombre_pais: str):
    resp = peticion_segura(f"{BASE_URL}{href_seleccion}", f"Plantilla: {nombre_pais}")
    if resp is None:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    jugadores = []
    tabla = soup.find("table", class_="items")
    if not tabla:
        print(f"     ⚠️ No se encontró tabla de plantilla para {nombre_pais}")
        return None

    filas = tabla.select("tbody > tr")
    for fila in filas:
        celdas = fila.find_all("td")
        if len(celdas) < 6:
            continue

        link_jugador = fila.find("td", class_="hauptlink") or fila.find("a", href=re.compile(r"/profil/spieler/"))
        nombre_jugador, href_jugador, player_id = None, None, None
        if link_jugador:
            enlace = link_jugador.find("a") if link_jugador.name == "td" else link_jugador
            if enlace:
                nombre_jugador = enlace.text.strip()
                href_jugador = enlace.get("href")
                match_id = re.search(r"/spieler/(\d+)", href_jugador or "")
                player_id = match_id.group(1) if match_id else None

        posicion_el = fila.find("td", class_="hauptlink")
        posicion = None
        if posicion_el:
            tabla_interna = posicion_el.find_parent("table")
            if tabla_interna:
                filas_internas = tabla_interna.find_all("tr")
                if len(filas_internas) >= 2:
                    celda_posicion = filas_internas[1].find("td")
                    if celda_posicion:
                        posicion = celda_posicion.get_text(strip=True)

        club_actual = None
        for img in fila.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if "wappen" in src:
                club_actual = img.get("title")
                break

        celdas_texto = [c.text.strip() for c in celdas]
        fecha_edad = next((c for c in celdas_texto if re.search(r"\(\d+\)", c)), None)
        valor_mercado = celdas_texto[-1] if celdas_texto else None

        jugadores.append({
            "player_id": player_id,
            "nombre": nombre_jugador,
            "href_perfil": href_jugador,
            "posicion": posicion,
            "fecha_nacimiento_edad_raw": fecha_edad,
            "club_actual": club_actual,
            "valor_mercado_raw": valor_mercado,
        })

    return {"pais": nombre_pais, "href_seleccion": href_seleccion, "jugadores": jugadores}


if __name__ == "__main__":
    print("=" * 80)
    print("REINTENTO DE SELECCIONES FALTANTES")
    print("=" * 80)

    for i, seleccion in enumerate(SELECCIONES_FALTANTES, 1):
        nombre = seleccion["nombre"]
        print(f"\n[{i}/{len(SELECCIONES_FALTANTES)}] Procesando: {nombre}")

        plantilla = extraer_plantilla(seleccion["href"], nombre)
        if plantilla is None:
            print(f"   ❌ Falló de nuevo. Verificar el href manualmente:")
            print(f"      {BASE_URL}{seleccion['href']}")
            continue

        archivo = RAW_DIR / f"{nombre.replace(' ', '_')}.json"
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(plantilla, f, ensure_ascii=False, indent=2)

        print(f"   ✅ {len(plantilla['jugadores'])} jugadores guardados en {archivo.name}")

    print("\n" + "=" * 80)
    print("Reintento completado. Vuelve a correr 03_limpiar_jugadores_transfermarkt.py")
    print("=" * 80)