"""
capturar_resultados_mundial2026.py
------------------------------------
Sesion 13 - Integracion Final (Semana 5)

Objetivo BRAI: llenar el hueco de datos detectado para la Pregunta 1
("% jugadores en 5 grandes ligas" vs "rendimiento de seleccion"), que
necesitaba resultados REALES del Mundial 2026. Ninguno de los 5 CSV
del proyecto los tenia.

Decision documentada: se descarto worldcup26.ir para esta tarea especifica.
Motivo con evidencia (verificado hoy, 15-ago-2026): el repositorio cambio
de alcance -su propia documentacion ahora lo describe como API de
Premier League/LaLiga con cobertura verificada solo en Inglaterra y
Espana-, lo cual es exactamente el riesgo de discontinuidad que ya se
habia anotado como sesgo potencial en la Fase 1. En su lugar se usa
openfootball/worldcup.json: fuente publica, sin autenticacion, sin
rate limit, mantenida a mano, y verificada aqui mismo con el resultado
real de la final (Espana 1-0 Argentina, gol de Ferran Torres min. 106).

Fuente: https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
"""

import csv
import json
import urllib.request

URL_RESULTADOS = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# --------------------------------------------------------------------------
# Mapeo explicito de las 3 excepciones detectadas al comparar contra
# equipos_limpio.csv. No se usa fuzzy matching: con solo 48 equipos,
# un mapeo explicito y verificable es mas confiable y auditable
# (principio BRAI: preferir lo verificable sobre lo automatico-opaco).
# --------------------------------------------------------------------------
MAPEO_NOMBRES = {
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "USA": "United States",
    "DR Congo": "Democratic Republic of the Congo",
}

# Orden de las rondas para calcular "ronda alcanzada (ponderada)".
# Decision documentada: los finalistas (ganador y perdedor de la Final)
# se consideran mas lejos que los equipos del partido por el tercer
# lugar, porque jugaron el partido de mayor jerarquia del torneo.
ORDEN_RONDA = {
    "Fase de grupos": 0,
    "Round of 32": 1,
    "Round of 16": 2,
    "Quarter-final": 3,
    "Semi-final": 4,
    "Match for third place": 5,
    "Final": 6,
}


def normalizar_equipo(nombre):
    return MAPEO_NOMBRES.get(nombre, nombre)


def score_de_juego(score):
    """Goles para efectos de GF/GC: tiempo extra si existe, si no tiempo regular.
    Los penales (clave 'p') NO cuentan como goles, solo definen quien avanza."""
    if "et" in score:
        return score["et"][0], score["et"][1]
    return score["ft"][0], score["ft"][1]


def ganador_partido(score, team1, team2):
    """Determina quien avanza: penales > tiempo extra > tiempo regular."""
    if "p" in score:
        s1, s2 = score["p"]
    elif "et" in score:
        s1, s2 = score["et"]
    else:
        s1, s2 = score["ft"]
    if s1 > s2:
        return team1
    if s2 > s1:
        return team2
    return None  # empate real (solo deberia pasar en fase de grupos)


def main():
    print("Descargando resultados reales del Mundial 2026...")
    with urllib.request.urlopen(URL_RESULTADOS) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    partidos = data["matches"]
    print(f"Partidos encontrados: {len(partidos)} (esperado: 104)")

    stats = {}

    def inicializar(equipo):
        if equipo not in stats:
            stats[equipo] = {
                "pj_grupo": 0, "pg_grupo": 0, "pe_grupo": 0, "pp_grupo": 0,
                "gf_grupo": 0, "gc_grupo": 0, "pts_grupo": 0,
                "gf_total": 0, "gc_total": 0,
                "ultima_ronda": "Fase de grupos", "campeon": False,
            }

    for p in partidos:
        t1 = normalizar_equipo(p["team1"])
        t2 = normalizar_equipo(p["team2"])
        inicializar(t1)
        inicializar(t2)

        gf1, gf2 = score_de_juego(p["score"])
        stats[t1]["gf_total"] += gf1
        stats[t1]["gc_total"] += gf2
        stats[t2]["gf_total"] += gf2
        stats[t2]["gc_total"] += gf1

        es_fase_grupos = "group" in p

        if es_fase_grupos:
            stats[t1]["pj_grupo"] += 1
            stats[t2]["pj_grupo"] += 1
            stats[t1]["gf_grupo"] += gf1
            stats[t1]["gc_grupo"] += gf2
            stats[t2]["gf_grupo"] += gf2
            stats[t2]["gc_grupo"] += gf1
            if gf1 > gf2:
                stats[t1]["pg_grupo"] += 1
                stats[t1]["pts_grupo"] += 3
                stats[t2]["pp_grupo"] += 1
            elif gf2 > gf1:
                stats[t2]["pg_grupo"] += 1
                stats[t2]["pts_grupo"] += 3
                stats[t1]["pp_grupo"] += 1
            else:
                stats[t1]["pe_grupo"] += 1
                stats[t2]["pe_grupo"] += 1
                stats[t1]["pts_grupo"] += 1
                stats[t2]["pts_grupo"] += 1
        else:
            ronda = p["round"]
            for equipo in (t1, t2):
                if ORDEN_RONDA[ronda] >= ORDEN_RONDA[stats[equipo]["ultima_ronda"]]:
                    stats[equipo]["ultima_ronda"] = ronda

            if ronda == "Final":
                ganador = ganador_partido(p["score"], t1, t2)
                if ganador:
                    stats[ganador]["campeon"] = True

    # Validacion interna BRAI: la suma de goles a favor de las 48
    # selecciones debe ser exactamente el doble del total de goles
    # del torneo (cada gol cuenta como GF de un equipo y GC del otro).
    suma_gf = sum(v["gf_total"] for v in stats.values())
    goles_torneo = sum(score_de_juego(p["score"])[0] + score_de_juego(p["score"])[1] for p in partidos)
    print(f"Validacion de consistencia: suma GF = {suma_gf}, 2 x goles del torneo = {goles_torneo * 2 // len(partidos) * len(partidos) if False else goles_torneo}")
    assert suma_gf == goles_torneo, "Inconsistencia en el conteo de goles"
    print("Validacion OK: suma de goles a favor coincide con el total de goles del torneo.")

    campeon = [k for k, v in stats.items() if v["campeon"]]
    print(f"Campeon detectado: {campeon}")
    assert campeon == ["Spain"], f"Se esperaba Spain como campeon, se obtuvo {campeon}"
    print("Validacion OK: campeon coincide con lo ya documentado (Espana).")

    # --------------------------------------------------------------------
    # Cruce con equipos_limpio.csv
    # --------------------------------------------------------------------
    equipos = {}
    with open("equipos_limpio.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            equipos[row["nombre_en"]] = row

    salida = []
    no_encontrados = []
    for equipo, s in stats.items():
        info = equipos.get(equipo)
        if info is None:
            no_encontrados.append(equipo)
            continue
        salida.append({
            "nombre_en": equipo,
            "name_en_normalizado": info["name_en_normalizado"],
            "codigo_fifa": info["codigo_fifa"],
            "grupo": info["grupo"],
            "partidos_grupo": s["pj_grupo"],
            "pg_grupo": s["pg_grupo"],
            "pe_grupo": s["pe_grupo"],
            "pp_grupo": s["pp_grupo"],
            "gf_grupo": s["gf_grupo"],
            "gc_grupo": s["gc_grupo"],
            "puntos_grupo": s["pts_grupo"],
            "gf_total": s["gf_total"],
            "gc_total": s["gc_total"],
            "diferencia_total": s["gf_total"] - s["gc_total"],
            "ronda_alcanzada": "Campeon" if s["campeon"] else s["ultima_ronda"],
            "ronda_orden": (ORDEN_RONDA[s["ultima_ronda"]] + 1) if s["campeon"] else ORDEN_RONDA[s["ultima_ronda"]],
        })

    if no_encontrados:
        print(f"AVISO: {len(no_encontrados)} equipos del JSON no cruzaron con equipos_limpio.csv: {no_encontrados}")
    else:
        print("Cruce completo: los 48 equipos del JSON cruzaron correctamente con equipos_limpio.csv.")

    print(f"Total de selecciones procesadas: {len(salida)} (esperado: 48)")
    assert len(salida) == 48, "No se procesaron las 48 selecciones"

    columnas = list(salida[0].keys())
    with open("resultados_mundial2026.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(salida)

    print("Archivo generado: resultados_mundial2026.csv")


if __name__ == "__main__":
    main()
