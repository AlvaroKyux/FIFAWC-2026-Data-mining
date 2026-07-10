"""
VALIDACIÓN RÁPIDA - correr este script PRIMERO, antes del extractor completo.

Usa el archivo HTML que ya guardaste en el Entregable 2
(transfermarkt_seleccion_muestra.html, la página de Argentina) para
confirmar que la lógica de parseo (BeautifulSoup) extrae correctamente
jugador, posición, club actual y valor de mercado, ANTES de lanzar el
extractor completo de las 48 selecciones.

Ajusta la ruta abajo si el archivo está en otra carpeta.
"""

import re
from bs4 import BeautifulSoup

RUTA_HTML = r"C:\Users\SirKy\OneDrive\Documents\PROYECTOS\FIFA-WC-2026\ETL\Extract\transfermarkt_seleccion_muestra.html" # ajustar si es necesario

with open(RUTA_HTML, encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

tabla = soup.find("table", class_="items")
if not tabla:
    print("❌ No se encontró ninguna tabla con class='items'. Revisar estructura del HTML.")
    exit()

filas = tabla.select("tbody > tr")
print(f"Filas encontradas en la tabla: {len(filas)}\n")

jugadores = []
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
        "posicion": posicion,
        "fecha_edad": fecha_edad,
        "club_actual": club_actual,
        "valor_mercado": valor_mercado,
    })

print(f"Jugadores parseados correctamente: {len(jugadores)}\n")
print("=== MUESTRA DE LOS PRIMEROS 5 ===")
for j in jugadores[:5]:
    print(j)

# Diagnóstico de campos vacíos (para saber si algún selector falló)
print("\n=== DIAGNÓSTICO DE CAMPOS VACÍOS ===")
for campo in ["player_id", "nombre", "posicion", "club_actual", "valor_mercado"]:
    vacios = sum(1 for j in jugadores if not j[campo])
    print(f"  {campo}: {vacios} vacíos de {len(jugadores)}")