"""
cubo_olap_real.py
--------------------
Sesion 13 - Integracion Final (Semana 5)

Reemplaza el ejercicio de Cubos OLAP con datos SINTETICOS (redes sociales)
por un cubo real construido sobre los datos del proyecto: 1,248 jugadores
convocados al Mundial 2026, sus 48 selecciones, resultados reales del
torneo, y carga/rendimiento de club.

MODELO EN ESTRELLA:
  FACT_JUGADOR (grano: un jugador convocado)
    Medidas: valor_mercado_eur, partidos_temporada_actual,
             minutos_temporada_actual, goles_temporada_actual,
             asistencias_temporada_actual, rating_qatar2022_por90 (nullable)
  DIM_SELECCION: seleccion, grupo, ronda_alcanzada, ronda_orden,
                 pct_5_grandes_ligas, indice_rendimiento
  DIM_JUGADOR:   nombre, edad, categoria_posicion, posicion
  DIM_CLUB:      club_actual, liga (una de las 5 grandes, o "Otra liga")

Reutiliza: equipos_limpio.csv, jugadores_mundial_limpio.csv,
resultados_mundial2026.csv, pregunta1_datos.csv, leistungsdaten_parcial_
limpio.csv, y el mapeo de 96 clubes de pregunta1_correlacion.py.

LIMITACION heredada: rating_qatar2022_por90 solo existe para 104/1248
jugadores (los que tambien jugaron Qatar 2022). El resto queda como
celda vacia en esa medida especifica -- se documenta, no se rellena
con un valor inventado.
"""

import csv
from pathlib import Path
from collections import defaultdict

CARPETA_SCRIPT = Path(__file__).resolve().parent

# Mismo mapeo de las 5 grandes ligas usado en Pregunta 1 (club -> liga)
from pregunta1_correlacion import MAPEO_CLUBES

CLUB_A_LIGA = {}
LIGAS_POR_PREFIJO = {
    "Arsenal": "Premier League", "Aston Villa": "Premier League", "AFC Bournemouth": "Premier League",
    "Brentford": "Premier League", "Brighton & Hove Albion": "Premier League", "Burnley": "Premier League",
    "Chelsea": "Premier League", "Crystal Palace": "Premier League", "Everton": "Premier League",
    "Fulham": "Premier League", "Leeds United": "Premier League", "Liverpool": "Premier League",
    "Manchester City": "Premier League", "Manchester United": "Premier League",
    "Newcastle United": "Premier League", "Nottingham Forest": "Premier League",
    "Sunderland": "Premier League", "Tottenham Hotspur": "Premier League",
    "West Ham United": "Premier League", "Wolverhampton Wanderers": "Premier League",
}
# Reconstruir club -> liga a partir del mapeo club-de-liga -> club_actual de Pregunta 1
LIGAS_ORDEN = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
_rangos = {
    "Premier League": (0, 20), "La Liga": (20, 40), "Serie A": (40, 60),
    "Bundesliga": (60, 78), "Ligue 1": (78, 96),
}
_items = list(MAPEO_CLUBES.items())
for i, (club_liga, club_actual) in enumerate(_items):
    if club_actual is None:
        continue
    for liga, (ini, fin) in _rangos.items():
        if ini <= i < fin:
            CLUB_A_LIGA[club_actual] = liga
            break

CATEGORIA_POSICION = {
    "Goalkeeper": "Portero",
    "Centre-Back": "Defensa", "Left-Back": "Defensa", "Right-Back": "Defensa",
    "Defensive Midfield": "Medio", "Central Midfield": "Medio",
    "Attacking Midfield": "Medio", "Left Midfield": "Medio", "Right Midfield": "Medio",
    "Centre-Forward": "Ataque", "Left Winger": "Ataque", "Right Winger": "Ataque",
    "Second Striker": "Ataque",
}


def main():
    with open(CARPETA_SCRIPT / "resultados_mundial2026.csv", encoding="utf-8") as f:
        resultados = {r["name_en_normalizado"]: r for r in csv.DictReader(f)}

    with open(CARPETA_SCRIPT / "pregunta1_datos.csv", encoding="utf-8") as f:
        p1 = {r["seleccion"]: r for r in csv.DictReader(f)}

    with open(CARPETA_SCRIPT / "jugadores_mundial_limpio.csv", encoding="utf-8-sig") as f:
        jugadores = list(csv.DictReader(f))

    with open(CARPETA_SCRIPT / "leistungsdaten_parcial_limpio.csv", encoding="utf-8-sig") as f:
        ld_totales = {r["nombre"]: r for r in csv.DictReader(f) if r["es_total"] == "True"}

    ratings_qatar = {}
    ruta_p2 = CARPETA_SCRIPT / "pregunta2_datos.csv"
    if ruta_p2.exists():
        with open(ruta_p2, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ratings_qatar[r["jugador"]] = float(r["rating_por_90_qatar2022"])

    fact = []
    for j in jugadores:
        sel = j["seleccion_normalizada"]
        r_res = resultados.get(sel)
        r_p1 = p1.get(sel)
        ld = ld_totales.get(j["nombre"])

        fila = {
            "player_id": j["player_id"],
            "nombre": j["nombre"],
            "edad": int(j["edad"]) if j["edad"] else None,
            "posicion": j["posicion"],
            "categoria_posicion": CATEGORIA_POSICION.get(j["posicion"], "Sin clasificar"),
            "club_actual": j["club_actual"],
            "liga": CLUB_A_LIGA.get(j["club_actual"], "Otra liga"),
            "valor_mercado_eur": float(j["valor_mercado_eur"]) if j["valor_mercado_eur"] else 0.0,
            "seleccion": sel,
            "grupo": r_res["grupo"] if r_res else None,
            "ronda_alcanzada": r_res["ronda_alcanzada"] if r_res else None,
            "ronda_orden": int(r_res["ronda_orden"]) if r_res else None,
            "pct_5_grandes_ligas_seleccion": float(r_p1["pct_5_grandes_ligas"]) if r_p1 else None,
            "partidos_temporada_actual": float(ld["partidos"]) if ld else None,
            "minutos_temporada_actual": float(ld["minutos"]) if ld else None,
            "rating_qatar2022_por90": ratings_qatar.get(j["nombre"]),
        }
        fact.append(fila)

    columnas = list(fact[0].keys())
    with open(CARPETA_SCRIPT / "FACT_JUGADOR.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(fact)

    print(f"FACT_JUGADOR construida: {len(fact)} filas (esperado: 1248)")
    con_carga = sum(1 for f in fact if f["partidos_temporada_actual"] is not None)
    con_qatar = sum(1 for f in fact if f["rating_qatar2022_por90"] is not None)
    print(f"  Con datos de carga de temporada actual: {con_carga}/1248 (~80.9% esperado por Fase 5)")
    print(f"  Con rating de Qatar 2022: {con_qatar}/1248 (104 esperados)")
    print()

    # ======================================================================
    # OPERACION 1: ROLL-UP
    # Subir de nivel Seleccion -> Grupo: valor de mercado total por grupo
    # ======================================================================
    print("=" * 70)
    print("ROLL-UP: Valor de mercado total, de Seleccion agregado a Grupo")
    print("=" * 70)
    valor_por_grupo = defaultdict(float)
    for f in fact:
        if f["grupo"]:
            valor_por_grupo[f["grupo"]] += f["valor_mercado_eur"]
    for grupo in sorted(valor_por_grupo):
        print(f"  Grupo {grupo}: EUR {valor_por_grupo[grupo]:>15,.0f}")
    print()

    # ======================================================================
    # OPERACION 2: DRILL-DOWN
    # Bajar de Categoria de posicion -> Posicion especifica (global)
    # ======================================================================
    print("=" * 70)
    print("DRILL-DOWN: de Categoria de posicion a Posicion especifica (Ataque)")
    print("=" * 70)
    valor_por_posicion = defaultdict(lambda: [0.0, 0])
    for f in fact:
        if f["categoria_posicion"] == "Ataque":
            valor_por_posicion[f["posicion"]][0] += f["valor_mercado_eur"]
            valor_por_posicion[f["posicion"]][1] += 1
    for pos, (total, n) in sorted(valor_por_posicion.items(), key=lambda x: -x[1][0]):
        print(f"  {pos:<20} EUR {total:>15,.0f}  (n={n}, promedio EUR {total/n:>12,.0f})")
    print()

    # ======================================================================
    # OPERACION 3: SLICE
    # Fijar Seleccion = Spain, ver todos sus jugadores
    # ======================================================================
    print("=" * 70)
    print("SLICE: Jugadores de Espana (campeon), ordenados por valor de mercado")
    print("=" * 70)
    espana = sorted([f for f in fact if f["seleccion"] == "SPAIN"],
                     key=lambda f: -f["valor_mercado_eur"])
    for f in espana[:8]:
        print(f"  {f['nombre']:<25} {f['posicion']:<20} EUR {f['valor_mercado_eur']:>12,.0f}  ({f['club_actual']})")
    print(f"  ... total convocados: {len(espana)}")
    print()

    # ======================================================================
    # OPERACION 4: DICE
    # Filtrar por Seleccion = France AND Liga = Premier League
    # ======================================================================
    print("=" * 70)
    print("DICE: Convocados de Francia que juegan en la Premier League")
    print("=" * 70)
    dice = [f for f in fact if f["seleccion"] == "FRANCE" and f["liga"] == "Premier League"]
    for f in dice:
        print(f"  {f['nombre']:<25} {f['posicion']:<20} {f['club_actual']}")
    print(f"  Total: {len(dice)} jugadores")
    print()

    # ======================================================================
    # OPERACION 5: PIVOT
    # Liga (filas) x Categoria de posicion (columnas) = conteo de jugadores
    # ======================================================================
    print("=" * 70)
    print("PIVOT: Liga x Categoria de posicion (conteo de convocados)")
    print("=" * 70)
    ligas_todas = LIGAS_ORDEN + ["Otra liga"]
    categorias = ["Portero", "Defensa", "Medio", "Ataque"]
    tabla = {liga: {c: 0 for c in categorias} for liga in ligas_todas}
    for f in fact:
        liga = f["liga"]
        cat = f["categoria_posicion"]
        if liga in tabla and cat in categorias:
            tabla[liga][cat] += 1

    header = f"  {'Liga':<16}" + "".join(f"{c:>10}" for c in categorias)
    print(header)
    for liga in ligas_todas:
        fila_txt = f"  {liga:<16}" + "".join(f"{tabla[liga][c]:>10}" for c in categorias)
        print(fila_txt)

    with open(CARPETA_SCRIPT / "cubo_pivot_liga_posicion.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["liga"] + categorias)
        for liga in ligas_todas:
            writer.writerow([liga] + [tabla[liga][c] for c in categorias])

    print()
    print("Archivos generados: FACT_JUGADOR.csv, cubo_pivot_liga_posicion.csv")


if __name__ == "__main__":
    main()
