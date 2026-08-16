"""
pregunta3_rendimiento_club_vs_mundial.py
--------------------------------------------
Sesion 13 - Integracion Final (Semana 5)

Pregunta 3: el rendimiento de un jugador en su club durante la temporada
regular, predice su rendimiento en el Mundial?

Variable independiente: rendimiento en club = (goles + asistencias) por
cada 90 minutos, en la temporada de club ACTUAL (2025-26).
Variable dependiente: mismo rating_por_90 usado en Pregunta 2, calculado
sobre los datos de Qatar 2022 (StatsBomb).

MISMA LIMITACION que Pregunta 2 (no se repite en detalle, ver ese script):
desfase de ~4 anios entre la temporada de club usada y el Mundial medido.
Se reutiliza el mismo subconjunto de 104 jugadores presentes en ambos
datasets, por la misma razon de disponibilidad de datos.

Diferencia real con Pregunta 2: alli se media VOLUMEN (partidos, minutos
= carga). Aqui se mide TASA DE PRODUCCION (goles+asistencias por 90 =
calidad ofensiva), que es una pregunta de investigacion distinta aunque
comparta la fuente de datos.

CORRECCION APLICADA (error propio, detectado y corregido antes de
entregar): la primera version de este script incluia porteros en la
metrica de "goles+asistencias por 90", lo que disparo valores absurdos
(ej. Jordan Pickford con 1.58 goles+asistencias por 90). La causa es la
misma que el equipo ya habia documentado en la Fase 5: para un portero,
la columna "goles" de leistungsdaten representa goles RECIBIDOS, no
anotados. Se excluyen porteros de esta metrica ofensiva especifica.
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
        a["minutos_aprox"] += int(r["minuto_ultimo_evento"])
        a["partidos"] += 1

    filas = []
    porteros_excluidos = 0
    for j in sorted(comunes):
        a = agregado_sb[j]
        ld_row = ld_totales[j]

        # Excluir porteros: "goles" en leistungsdaten es goles RECIBIDOS
        # para esta posicion, no anotados (documentado desde la Fase 5).
        # Incluirlos en una metrica de "rendimiento ofensivo" seria un
        # error de interpretacion, no una limitacion menor.
        if ld_row["posicion"] == "Goalkeeper":
            porteros_excluidos += 1
            continue

        minutos_qatar = a["minutos_aprox"] if a["minutos_aprox"] > 0 else 1
        puntos_qatar = a["goles"] * 4 + a["asistencias"] * 3 + a["duelos"] * 0.5 + a["pases"] * 0.02
        rating_mundial_por90 = puntos_qatar / minutos_qatar * 90

        minutos_club = float(ld_row["minutos"]) or 1.0
        goles_club = float(ld_row["goles"])
        asist_club = float(ld_row["asistencias"])
        rendimiento_club_por90 = (goles_club + asist_club) / minutos_club * 90

        filas.append({
            "jugador": j,
            "seleccion": ld_row["seleccion"],
            "posicion": ld_row["posicion"],
            "club_actual": ld_row["club_actual"],
            "goles_club_actual": goles_club,
            "asistencias_club_actual": asist_club,
            "minutos_club_actual": minutos_club,
            "rendimiento_club_ga_por90": round(rendimiento_club_por90, 3),
            "rating_mundial_por90_qatar2022": round(rating_mundial_por90, 3),
        })

    print(f"Porteros excluidos de la metrica ofensiva: {porteros_excluidos}")
    print(f"Jugadores de campo analizados: {len(filas)}")
    print()

    columnas = list(filas[0].keys())
    ruta_salida = CARPETA_SCRIPT / "pregunta3_datos.csv"
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)

    x = [f["rendimiento_club_ga_por90"] for f in filas]
    y = [f["rating_mundial_por90_qatar2022"] for f in filas]
    r = pearson(x, y)

    # Segmentacion por posicion: la hipotesis de "rendimiento en club predice
    # rendimiento en Mundial" es mas plausible en delanteros/mediocampistas
    # ofensivos que en defensas/porteros, donde goles+asistencias no capturan
    # bien el rol. Se reporta tambien la correlacion solo en esas posiciones,
    # en vez de asumir que la metrica aplica igual a todos los roles.
    posiciones_ofensivas = {"Centre-Forward", "Left Winger", "Right Winger",
                             "Attacking Midfield", "Second Striker"}
    filas_of = [f for f in filas if f["posicion"] in posiciones_ofensivas]
    if len(filas_of) >= 5:
        x_of = [f["rendimiento_club_ga_por90"] for f in filas_of]
        y_of = [f["rating_mundial_por90_qatar2022"] for f in filas_of]
        r_of = pearson(x_of, y_of)
    else:
        r_of = float("nan")

    print(f"Correlacion general (n={len(filas)}): r = {r:.3f}")
    print(f"Correlacion solo posiciones ofensivas (n={len(filas_of)}): r = {r_of:.3f}")
    print()

    filas.sort(key=lambda f: -f["rendimiento_club_ga_por90"])
    print("Top 5 por rendimiento ofensivo en club (goles+asistencias por 90):")
    for f in filas[:5]:
        print(f"  {f['jugador']:<25} club={f['rendimiento_club_ga_por90']:>5.2f}  "
              f"mundial(Qatar22)={f['rating_mundial_por90_qatar2022']:>6.2f}  ({f['posicion']})")

    print()
    print(f"Archivo generado: {ruta_salida}")
    print()
    print("RECORDATORIO: misma limitacion temporal que Pregunta 2 (temporada de")
    print("club actual vs Mundial 2022 historico). Documentar en el minireporte.")


if __name__ == "__main__":
    main()
