"""
Proyecto: Data Mining - FIFA WC2026
Entregable 3 - Limpieza y Transformación
Fuente: Transfermarkt — Plantillas de las 48 selecciones nacionales

HALLAZGO YA DOCUMENTADO (Entregable 2): Transfermarkt aplica un bloqueo
dinámico por comportamiento. Una petición aislada funciona (200), pero
varias peticiones rápidas seguidas disparan 403, incluso en la MISMA URL
que antes funcionó. La solución verificada es usar pausas de al menos
5 segundos entre peticiones.

DISEÑO DE ESTE SCRIPT (decisiones explícitas, no improvisadas):
1. Recorre la jerarquía: confederaciones -> países -> selección nacional
   -> plantilla de jugadores. Esto es necesario porque Transfermarkt no
   tiene una lista plana de "selecciones nacionales"; hay que descubrir
   la URL de cada selección navegando desde su país.
2. GUARDADO INCREMENTAL: cada selección se guarda en su propio archivo
   JSON apenas se descarga, en lugar de acumular todo en memoria y
   guardar al final. Esto es deliberado: si el proceso se interrumpe
   (por bloqueo, corte de luz, etc.) a la mitad de las 48 selecciones,
   no perdemos lo ya avanzado.
3. REANUDABLE: si vuelves a correr el script, salta las selecciones que
   ya tienen su archivo JSON guardado, en lugar de re-descargarlas.
4. PAUSA CONFIGURABLE: por defecto 6 segundos (margen sobre los 5s ya
   verificados como suficientes), ajustable si el bloqueo reaparece.

TIEMPO ESTIMADO: 48 selecciones x ~2 peticiones cada una (país -> selección
-> plantilla) x 6s de pausa ≈ 10-15 minutos para esta etapa. NO incluye
las estadísticas de carrera por jugador (eso es la Fase 3, mucho más larga).

INSTALACIÓN PREVIA:
    python -m pip install requests beautifulsoup4 lxml pandas
"""

import time
import json
import re
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


def peticion_segura(url: str, etiqueta: str = "") -> requests.Response | None:
    """Petición GET con pausa previa y manejo de errores no destructivo."""
    print(f"  -> {etiqueta or url}")
    time.sleep(PAUSA_SEGUNDOS)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 403:
            print(f"     ⚠️ 403 recibido. Si esto se repite en TODAS las")
            print(f"        peticiones siguientes, detener el script y")
            print(f"        aumentar PAUSA_SEGUNDOS o esperar antes de reintentar.")
            return None
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        print(f"     ❌ Error de red: {e}")
        return None


# Lista de confederaciones, igual a la que ya verificamos en el Entregable 2
CONFEDERACIONES = [
    "/wettbewerbe/europa",
    "/wettbewerbe/amerika",
    "/wettbewerbe/afrika",
    "/wettbewerbe/asien",
]


def descubrir_selecciones_via_ranking() -> list[dict]:
    """
    CONFIRMADO con HTML real Y con inspección de DevTools (Network tab):
    la página /statistik/weltrangliste pagina su tabla vía AJAX/jQuery,
    SIN cambiar la URL visible en el navegador. La petición real que
    carga cada página es:

        https://www.transfermarkt.co.uk/statistik/weltrangliste?ajax=yw1&page=N

    Esto fue verificado inspeccionando la pestaña Network del navegador
    al hacer clic en el botón de paginación "3": apareció una petición
    XHR con exactamente esa URL (Request Method: GET, Status: 200 OK).

    Cada página trae 25 filas. El ranking FIFA completo tiene ~211
    selecciones (9 páginas según la paginación visible en el sitio).
    Recorremos páginas hasta encontrar las 48 selecciones del Mundial 2026
    o hasta agotar las páginas disponibles.
    """
    todas = []
    pagina = 1
    paginas_sin_filas_nuevas = 0

    while True:
        url = f"{BASE_URL}/statistik/weltrangliste?ajax=yw1&page={pagina}"
        resp = peticion_segura(url, f"Ranking FIFA, página {pagina}")
        if resp is None:
            break

        soup = BeautifulSoup(resp.text, "lxml")
        tabla = soup.find("table", class_="items")
        if not tabla:
            print(f"   ⚠️ No se encontró tabla en la página {pagina}, deteniendo paginación.")
            break

        filas = tabla.select("tbody > tr")
        if not filas:
            print(f"   ℹ️ Página {pagina} sin filas, asumiendo fin del ranking.")
            break

        nuevas_en_esta_pagina = 0
        for fila in filas:
            link = fila.find("a", href=lambda h: h and "/startseite/verein/" in h)
            if not link:
                continue
            nombre = link.get("title")
            href = link.get("href")
            if nombre and href:
                todas.append({"nombre": nombre, "href": href})
                nuevas_en_esta_pagina += 1

        print(f"      -> {nuevas_en_esta_pagina} entradas en esta página (antes de deduplicar)")

        pagina += 1
        if pagina > 12:  # margen de seguridad sobre las ~9 páginas observadas
            print("   ℹ️ Límite de seguridad de páginas alcanzado.")
            break

    # Deduplicar por href (cada selección aparece 2 veces: bandera + texto)
    vistos = set()
    unicas = []
    for s in todas:
        if s["href"] not in vistos:
            vistos.add(s["href"])
            unicas.append(s)

    return unicas


def filtrar_selecciones_mundial(todas_las_selecciones: list[dict]) -> list[dict]:
    """
    Cruza el listado completo del ranking FIFA contra las 48 selecciones
    del Mundial 2026 (ya extraídas en la Fase 1, worldcup26.ir), usando
    el nombre normalizado para hacer el match.
    """
    import pandas as pd

    ruta_equipos = Path("clean/equipos_limpio.csv")
    if not ruta_equipos.exists():
        print("⚠️ No se encontró clean/equipos_limpio.csv (Fase 1).")
        print("   Corre primero 01_worldcup26ir_etl.py, o el filtrado")
        print("   se omitirá y se usarán TODAS las selecciones encontradas.")
        return todas_las_selecciones

    equipos_mundial = pd.read_csv(ruta_equipos)
    nombres_mundial = set(equipos_mundial["name_en_normalizado"])

    seleccionadas = []
    no_encontradas = set(nombres_mundial)

    for s in todas_las_selecciones:
        nombre_normalizado = s["nombre"].strip().upper()
        if nombre_normalizado in nombres_mundial:
            seleccionadas.append(s)
            no_encontradas.discard(nombre_normalizado)

    if no_encontradas:
        print(f"\n⚠️ {len(no_encontradas)} selecciones del Mundial NO encontradas")
        print(f"   en el ranking de Transfermarkt (probable diferencia de nombre):")
        print(f"   {sorted(no_encontradas)}")
        print("   Estas requerirán mapeo manual en la tabla de mapeo de nombres.")

    return seleccionadas


def extraer_plantilla(href_seleccion: str, nombre_pais: str) -> dict | None:
    """
    Extrae la plantilla completa de una selección: jugador, posición,
    fecha de nacimiento, club actual (vía atributo title/alt del escudo,
    no texto plano), y valor de mercado.
    """
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

        # Nombre y link de perfil del jugador (necesario para la Fase 3:
        # estadísticas de carrera por jugador)
        link_jugador = fila.find("td", class_="hauptlink") or fila.find("a", href=re.compile(r"/profil/spieler/"))
        nombre_jugador = None
        href_jugador = None
        player_id = None
        if link_jugador:
            enlace = link_jugador.find("a") if link_jugador.name == "td" else link_jugador
            if enlace:
                nombre_jugador = enlace.text.strip()
                href_jugador = enlace.get("href")
                match_id = re.search(r"/spieler/(\d+)", href_jugador or "")
                player_id = match_id.group(1) if match_id else None

        # Posición: viene en la SEGUNDA fila de la tabla interna
        # (table.inline-table) que también contiene el nombre del jugador.
        # CONFIRMADO con HTML real (Argentina, Entregable 3): no existe un
        # td.posrela; la posición está en un <td> sin clase, fila 2 de la
        # tabla interna que arranca con el nombre.
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

        # Club actual: CONFIRMADO con HTML real que hay DOS <img> por fila
        # (foto del jugador + escudo del club), sin clase "tiny_wappen"
        # como se asumió inicialmente. Se distinguen por la URL: el escudo
        # viene de una ruta que contiene "wappen"; la foto del jugador
        # viene de "portrait". Filtramos explícitamente por eso.
        club_actual = None
        for img in fila.find_all("img"):
            src = img.get("src", "") or img.get("data-src", "")
            if "wappen" in src:
                club_actual = img.get("title")
                break

        # Fecha de nacimiento / edad: viene en una celda tipo "Sep 2, 1992 (33)"
        celdas_texto = [c.text.strip() for c in celdas]
        fecha_edad = next((c for c in celdas_texto if re.search(r"\(\d+\)", c)), None)

        # Valor de mercado: última celda, formato "€12.00m"
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

    return {
        "pais": nombre_pais,
        "href_seleccion": href_seleccion,
        "jugadores": jugadores,
    }


def ya_descargado(nombre_pais: str) -> bool:
    """Verifica si ya existe el archivo de esta selección (para reanudar)."""
    archivo = RAW_DIR / f"{nombre_pais.replace(' ', '_').replace('/', '-')}.json"
    return archivo.exists()


def guardar_plantilla(nombre_pais: str, data: dict) -> None:
    archivo = RAW_DIR / f"{nombre_pais.replace(' ', '_').replace('/', '-')}.json"
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print("=" * 80)
    print("PASO 1: DESCUBRIMIENTO DE SELECCIONES VÍA RANKING FIFA")
    print("=" * 80)
    todas_selecciones = descubrir_selecciones_via_ranking()
    print(f"\n✅ {len(todas_selecciones)} selecciones encontradas en el ranking FIFA.")

    # Guardamos el listado completo como checkpoint, por si hay que retomar
    # o auditar manualmente qué se descubrió.
    with open(RAW_DIR.parent / "todas_selecciones_ranking.json", "w", encoding="utf-8") as f:
        json.dump(todas_selecciones, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("PASO 2: FILTRADO A LAS 48 SELECCIONES DEL MUNDIAL 2026")
    print("=" * 80)
    selecciones = filtrar_selecciones_mundial(todas_selecciones)
    print(f"\n✅ {len(selecciones)} selecciones del Mundial 2026 identificadas para extracción.")

    with open(RAW_DIR.parent / "selecciones_mundial_a_extraer.json", "w", encoding="utf-8") as f:
        json.dump(selecciones, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 80)
    print("PASO 3: EXTRACCIÓN DE PLANTILLAS (reanudable)")
    print("=" * 80)

    exitosas = 0
    fallidas = []

    for i, seleccion in enumerate(selecciones, 1):
        nombre = seleccion["nombre"]

        if ya_descargado(nombre):
            print(f"[{i}/{len(selecciones)}] {nombre}: ya descargado, se omite.")
            continue

        print(f"\n[{i}/{len(selecciones)}] Procesando: {nombre}")

        plantilla = extraer_plantilla(seleccion["href"], nombre)
        if plantilla is None:
            fallidas.append(nombre)
            continue

        guardar_plantilla(nombre, plantilla)
        exitosas += 1
        print(f"   ✅ {len(plantilla['jugadores'])} jugadores guardados.")

    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Plantillas extraídas exitosamente: {exitosas}")
    print(f"Fallidas: {len(fallidas)}")
    if fallidas:
        print(f"Lista de fallidas: {fallidas}")
    print(f"\nArchivos guardados en: {RAW_DIR}/")