"""
pregunta2_carga_rendimiento.py
---------------------------------
Sesion 13 - Integracion Final (Semana 5)

Pregunta 2: la cantidad de minutos/partidos jugados por un jugador en la
temporada de clubes, afecta su rendimiento individual en el Mundial?

LIMITACION METODOLOGICA DOCUMENTADA (no oculta):
leistungsdaten_parcial_limpio.csv refleja la temporada de club ACTUAL
(2025-26, la que precede al Mundial 2026). statsbomb_rendimiento_jugador_
partido.csv es de Qatar 2022, el unico Mundial con datos abiertos
disponibles (ver Fase 4 / Sesion verificacion de fuentes). Estos dos
periodos estan separados por ~4 anios.

Esto significa que este script NO prueba "carga previa a Qatar 2022 vs
rendimiento en Qatar 2022" (no tenemos la carga de 2021-22 de estos
jugadores). Prueba una version mas debil y honesta: "carga de club ACTUAL
de un jugador vs su rendimiento HISTORICO en un Mundial que si jugo".
Es la mejor evidencia empirica disponible con las fuentes que el proyecto
ya valido, pero el resultado debe leerse como una aproximacion, no como
una prueba directa de la hipotesis de fatiga formulada en Sesion 1.

Muestra: 104 jugadores que aparecen en AMBOS datasets (jugaron Qatar 2022
Y siguen convocados al Mundial 2026), de 1010 jugadores con fila TOTAL en
leistungsdaten y 681 jugadores unicos en statsbomb.
"""

import csv
from pathlib import Path
from collections import defaultdict

CARPETA_SCRIPT = Path(__file__).resolve().parent


def pearson(xs, ys):
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return float("nan")
    return cov / (var_x ** 0.5 * var_y ** 0.5)


def main():
    with open(CARPETA_SCRIPT / "leistungsdaten_parcial_limpio.csv", encoding="utf-8-sig") as f:
        ld = list(csv.DictReader(f))
    ld_totales = {r["nombre"]: r for r in ld if r["es_total"] == "True"}

    with open(CARPETA_SCRIPT / "statsbomb_rendimiento_jugador_partido.csv", encoding="utf-8-sig") as f:
        sb = list(csv.DictReader(f))

    comunes = set(ld_totales) & set(r["player"] for r in sb)
    print(f"Jugadores en ambos datasets: {len(comunes)}")

    # Agregar rendimiento en Qatar 2022 por jugador (across todos sus partidos)
    agregado_sb = defaultdict(lambda: {"goles": 0, "asistencias": 0, "duelos": 0,
                                        "pases": 0, "minutos_aprox": 0, "partidos": 0})
    for r in sb:
        j = r["player"]
        if j not in comunes:
            continue
        a = agregado_sb[j]
        a["goles"] += int(r["goles"])
        a["asistencias"] += int(r["asistencias"])
        a["duelos"] += int(r["duelos"])
        a["pases"] += int(r["pases"])
        # StatsBomb no da "minutos jugados" directo en este resumen; se usa
        # el minuto del ultimo evento registrado por partido como proxy
        # (aproximacion documentada, no un dato exacto de minutos).
        a["minutos_aprox"] += int(r["minuto_ultimo_evento"])
        a["partidos"] += 1

    filas = []
    for j in sorted(comunes):
        a = agregado_sb[j]
        ld_row = ld_totales[j]
        minutos_qatar = a["minutos_aprox"] if a["minutos_aprox"] > 0 else 1

        # Rating de rendimiento en Qatar 2022, normalizado por 90 minutos.
        # Pesos: gol=4, asistencia=3, duelo=0.5, pase=0.02 (participacion
        # general de juego). No hay "pases clave" en este resumen de
        # StatsBomb, se usa "pases" totales como proxy mas amplio -
        # limitacion documentada, no un reemplazo exacto de la metrica
        # original definida en Sesion 1.
        puntos = a["goles"] * 4 + a["asistencias"] * 3 + a["duelos"] * 0.5 + a["pases"] * 0.02
        rating_90 = puntos / minutos_qatar * 90

        carga_partidos = float(ld_row["partidos"])
        carga_minutos = float(ld_row["minutos"])

        filas.append({
            "jugador": j,
            "seleccion": ld_row["seleccion"],
            "posicion": ld_row["posicion"],
            "club_actual": ld_row["club_actual"],
            "carga_partidos_temporada_actual": carga_partidos,
            "carga_minutos_temporada_actual": carga_minutos,
            "partidos_qatar2022": a["partidos"],
            "goles_qatar2022": a["goles"],
            "asistencias_qatar2022": a["asistencias"],
            "rating_por_90_qatar2022": round(rating_90, 3),
        })

    columnas = list(filas[0].keys())
    ruta_salida = CARPETA_SCRIPT / "pregunta2_datos.csv"
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)

    # Correlaciones: carga (partidos, minutos) vs rating en Qatar 2022
    carga_p = [f["carga_partidos_temporada_actual"] for f in filas]
    carga_m = [f["carga_minutos_temporada_actual"] for f in filas]
    rating = [f["rating_por_90_qatar2022"] for f in filas]

    r_partidos = pearson(carga_p, rating)
    r_minutos = pearson(carga_m, rating)

    print(f"Correlacion carga de PARTIDOS (temporada actual) vs rating Qatar 2022: r = {r_partidos:.3f}")
    print(f"Correlacion carga de MINUTOS  (temporada actual) vs rating Qatar 2022: r = {r_minutos:.3f}")
    print()

    filas.sort(key=lambda f: -f["rating_por_90_qatar2022"])
    print("Top 5 por rating en Qatar 2022:")
    for f in filas[:5]:
        print(f"  {f['jugador']:<25} rating={f['rating_por_90_qatar2022']:>6.2f}  "
              f"carga_actual={f['carga_partidos_temporada_actual']:>4.0f} partidos / "
              f"{f['carga_minutos_temporada_actual']:>5.0f} min")

    print()
    print(f"Archivo generado: {ruta_salida}")
    print()
    print("RECORDATORIO: esta correlacion compara la carga de la temporada 2025-26")
    print("(actual) contra el rendimiento historico en Qatar 2022, no la carga previa")
    print("a ese torneo. Es una aproximacion, documentar como tal en el minireporte.")


if __name__ == "__main__":
    main()
