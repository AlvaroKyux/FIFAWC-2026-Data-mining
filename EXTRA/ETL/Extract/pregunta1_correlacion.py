"""
pregunta1_correlacion.py
--------------------------
Sesion 13 - Integracion Final (Semana 5)

Cierra la Pregunta 1: correlacion entre % de convocados en las 5 grandes
ligas (Premier League, La Liga, Serie A, Bundesliga, Ligue 1) y el
rendimiento de la seleccion en el Mundial 2026.

Fuente de las plantillas 2025-26: Wikipedia (verificado 15-ago-2026), no
memoria del modelo -- las plantillas cambian cada temporada por ascensos
y descensos, asi que no se pueden asumir de conocimiento general.

Metodologia de cruce de nombres: emparejamiento explicito club-por-club
(96 clubes), no fuzzy matching automatico. Con solo 96 clubes un mapeo
verificado a mano es mas confiable y auditable que un matching automatico
que podria emparejar mal en silencio (ej. "Inter" -> "Inter Miami CF").
8 de los 96 clubes de las 5 grandes ligas no tienen ningun jugador
convocado al Mundial 2026 en este dataset (Getafe, Lazio, Lecce,
Heidenheim, FC Koln, FC Metz, Stade Brestois, Deportivo Alaves):
verificado por busqueda directa, no es un error de nombre.
"""

import csv
from pathlib import Path
from collections import defaultdict

CARPETA_SCRIPT = Path(__file__).resolve().parent

# Mapeo club de la liga -> nombre exacto en club_actual del CSV del proyecto.
# None = el club no tiene ningun convocado al Mundial 2026 (verificado).
MAPEO_CLUBES = {
    # Premier League (coincidencia directa, sin alias)
    "Arsenal": "Arsenal FC", "Aston Villa": "Aston Villa", "Bournemouth": "AFC Bournemouth",
    "Brentford": "Brentford FC", "Brighton & Hove Albion": "Brighton & Hove Albion",
    "Burnley": "Burnley FC", "Chelsea": "Chelsea FC", "Crystal Palace": "Crystal Palace",
    "Everton": "Everton FC", "Fulham": "Fulham FC", "Leeds United": "Leeds United",
    "Liverpool": "Liverpool FC", "Manchester City": "Manchester City",
    "Manchester United": "Manchester United", "Newcastle United": "Newcastle United",
    "Nottingham Forest": "Nottingham Forest", "Sunderland": "Sunderland AFC",
    "Tottenham Hotspur": "Tottenham Hotspur", "West Ham United": "West Ham United",
    "Wolverhampton Wanderers": "Wolverhampton Wanderers",
    # La Liga
    "FC Barcelona": "FC Barcelona", "Real Madrid": "Real Madrid",
    "Atletico de Madrid": "Atlético de Madrid", "Athletic Club": "Athletic Bilbao",
    "Villarreal": "Villarreal CF", "Real Betis": "Real Betis Balompié",
    "Celta de Vigo": "Celta de Vigo", "Rayo Vallecano": "Rayo Vallecano",
    "Osasuna": "CA Osasuna", "RCD Mallorca": "RCD Mallorca",
    "Real Sociedad": "Real Sociedad", "Valencia": "Valencia CF",
    "Getafe": None, "RCD Espanyol": "RCD Espanyol Barcelona",
    "Deportivo Alaves": None, "Girona": "Girona FC", "Sevilla": "Sevilla FC",
    "Levante": "Levante UD", "Elche": "Elche CF", "Real Oviedo": "Real Oviedo",
    # Serie A
    "Atalanta": "Atalanta BC", "Bologna": "Bologna FC 1909", "Cagliari": "Cagliari Calcio",
    "Como": "Como 1907", "Cremonese": "US Cremonese", "Fiorentina": "ACF Fiorentina",
    "Genoa": "Genoa CFC", "Hellas Verona": "Hellas Verona", "Inter": "Inter Milan",
    "Juventus": "Juventus FC", "Lazio": None, "Lecce": None, "AC Milan": "AC Milan",
    "Napoli": "SSC Napoli", "Parma": "Parma Calcio 1913", "Pisa": "Pisa Sporting Club",
    "AS Roma": "AS Roma", "Sassuolo": "US Sassuolo", "Torino": "Torino FC",
    "Udinese": "Udinese Calcio",
    # Bundesliga
    "FC Augsburg": "FC Augsburg", "Union Berlin": "1.FC Union Berlin",
    "Werder Bremen": "SV Werder Bremen", "Borussia Dortmund": "Borussia Dortmund",
    "Eintracht Frankfurt": "Eintracht Frankfurt", "SC Freiburg": "SC Freiburg",
    "Hamburger SV": "Hamburger SV", "Heidenheim": None,
    "TSG Hoffenheim": "TSG 1899 Hoffenheim", "FC Koln": None,
    "RB Leipzig": "RB Leipzig", "Bayer Leverkusen": "Bayer 04 Leverkusen",
    "Mainz 05": "1.FSV Mainz 05", "Borussia Monchengladbach": "Borussia Mönchengladbach",
    "Bayern Munich": "Bayern Munich", "FC St. Pauli": "FC St. Pauli",
    "VfB Stuttgart": "VfB Stuttgart", "VfL Wolfsburg": "VfL Wolfsburg",
    # Ligue 1
    "Angers": "Angers SCO", "AJ Auxerre": "AJ Auxerre", "Stade Brestois": None,
    "Le Havre AC": "Le Havre AC", "RC Lens": "RC Lens", "LOSC Lille": "LOSC Lille",
    "FC Lorient": "FC Lorient", "Olympique Lyonnais": "Olympique Lyon",
    "Olympique Marseille": "Olympique Marseille", "AS Monaco": "AS Monaco",
    "OGC Nice": "OGC Nice", "Paris FC": "Paris FC",
    "Paris Saint-Germain": "Paris Saint-Germain", "Stade Rennais": "Stade Rennais FC",
    "RC Strasbourg": "RC Strasbourg Alsace", "Toulouse FC": "FC Toulouse",
    "FC Metz": None, "FC Nantes": "FC Nantes",
}

CLUBES_5_GRANDES = {v for v in MAPEO_CLUBES.values() if v is not None}


def main():
    with open(CARPETA_SCRIPT / "jugadores_mundial_limpio.csv", encoding="utf-8-sig") as f:
        jugadores = list(csv.DictReader(f))

    with open(CARPETA_SCRIPT / "resultados_mundial2026.csv", encoding="utf-8") as f:
        resultados = {r["name_en_normalizado"]: r for r in csv.DictReader(f)}

    total_por_seleccion = defaultdict(int)
    en_5_grandes_por_seleccion = defaultdict(int)

    for j in jugadores:
        sel = j["seleccion_normalizada"]
        total_por_seleccion[sel] += 1
        if j["club_actual"] in CLUBES_5_GRANDES:
            en_5_grandes_por_seleccion[sel] += 1

    filas = []
    for sel, total in total_por_seleccion.items():
        en5 = en_5_grandes_por_seleccion[sel]
        pct = round(100 * en5 / total, 2) if total else 0.0
        r = resultados.get(sel)
        if r is None:
            print(f"AVISO: {sel} no encontrada en resultados_mundial2026.csv")
            continue
        filas.append({
            "seleccion": sel,
            "convocados_totales": total,
            "convocados_5_grandes_ligas": en5,
            "pct_5_grandes_ligas": pct,
            "ronda_alcanzada": r["ronda_alcanzada"],
            "ronda_orden": int(r["ronda_orden"]),
            "gf_total": int(r["gf_total"]),
            "gc_total": int(r["gc_total"]),
            "puntos_grupo": int(r["puntos_grupo"]),
        })

    # Indice de rendimiento tal como se definio en Sesion 1:
    # ronda alcanzada (ponderada) + goles a favor - goles en contra + puntos en fase de grupos
    for f in filas:
        f["indice_rendimiento"] = (
            f["ronda_orden"] + f["gf_total"] - f["gc_total"] + f["puntos_grupo"]
        )

    filas.sort(key=lambda f: -f["pct_5_grandes_ligas"])

    columnas = ["seleccion", "convocados_totales", "convocados_5_grandes_ligas",
                "pct_5_grandes_ligas", "ronda_alcanzada", "indice_rendimiento"]
    with open(CARPETA_SCRIPT / "pregunta1_datos.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        for fila in filas:
            writer.writerow({k: fila[k] for k in columnas})

    # Correlacion de Pearson (sin dependencias externas)
    n = len(filas)
    xs = [f["pct_5_grandes_ligas"] for f in filas]
    ys = [f["indice_rendimiento"] for f in filas]
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    r_pearson = cov / (var_x ** 0.5 * var_y ** 0.5)

    print(f"Selecciones procesadas: {n} (esperado: 48)")
    print(f"Correlacion de Pearson (%% 5 grandes ligas vs indice de rendimiento): r = {r_pearson:.3f}")
    print()
    print("Top 5 por %% de convocados en 5 grandes ligas:")
    for f in filas[:5]:
        print(f"  {f['seleccion']:<20} {f['pct_5_grandes_ligas']:>6.1f}%  "
              f"indice={f['indice_rendimiento']:>4}  ({f['ronda_alcanzada']})")
    print()
    print("Bottom 5 por %% de convocados en 5 grandes ligas:")
    for f in filas[-5:]:
        print(f"  {f['seleccion']:<20} {f['pct_5_grandes_ligas']:>6.1f}%  "
              f"indice={f['indice_rendimiento']:>4}  ({f['ronda_alcanzada']})")

    print()
    print(f"Archivo generado: {CARPETA_SCRIPT / 'pregunta1_datos.csv'}")


if __name__ == "__main__":
    main()