# -*- coding: utf-8 -*-
"""
deteccion_anomalias.py
-------------------------
Sesion 9 - Deteccion de Anomalias.

Punto de partida (continuidad con Sesion 7): ya se sabe que el 27 de
julio es una anomalia de CAPTURA (0 articulos en el corpus pese a 237
articulos reales existentes, confirmado con NewsAPI). La pregunta que
responde este script es distinta: ¿la deteccion de anomalias estadistica
estandar, aplicada solo sobre la serie que tenemos (sin la verificacion
externa de la Sesion 7), habria encontrado ese problema por si sola?

Se aplican dos tecnicas:
  1. Z-score univariado sobre total_articulos -- para confirmar que el
     pico del 19-20 de julio es una anomalia estadistica real (evento
     verificable: final del Mundial).
  2. Isolation Forest multivariado -- usando ademas idioma, dia de la
     semana y mezcla de clusters tematicos, para ver si detecta algo que
     el Z-score univariado no vea.

Entrada: series_diarias.csv (Sesion 7)
Salida:
  - anomalias_detectadas.csv
  - anomalias_detectadas.png

Uso:
    python deteccion_anomalias.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest

RUTA_SERIE = "series_diarias.csv"
COL_OBJETIVO = "total_articulos"

FECHA_FINAL_MUNDIAL = "2026-07-19"
FECHA_ANOMALIA_CAPTURA_CONOCIDA = "2026-07-27"  # ya diagnosticada en Sesion 7


def cargar_serie():
    df = pd.read_csv(RUTA_SERIE, parse_dates=["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    df["dia_semana"] = df["fecha"].dt.dayofweek  # 0=lunes ... 6=domingo
    return df


def calcular_zscore(df, col=COL_OBJETIVO, umbral=2.0):
    media = df[col].mean()
    std = df[col].std()
    df["zscore"] = (df[col] - media) / std
    df["anomalia_zscore"] = df["zscore"].abs() > umbral
    print(f"Z-score sobre '{col}': media={media:.2f}, std={std:.2f}, "
          f"umbral=|z|>{umbral}")
    return df


def calcular_isolation_forest(df, contaminacion=0.15):
    features = df[["total_articulos", "es", "en", "dia_semana",
                    "cluster_0", "cluster_1", "cluster_2"]].copy()

    modelo = IsolationForest(contamination=contaminacion, random_state=42)
    pred = modelo.fit_predict(features)  # -1 = anomalia, 1 = normal
    df["anomalia_isolation_forest"] = pred == -1
    df["score_isolation_forest"] = modelo.decision_function(features)
    return df


def main():
    df = cargar_serie()
    df = calcular_zscore(df)
    df = calcular_isolation_forest(df)

    print("\n" + "="*70)
    print("DIAS MARCADOS COMO ANOMALIA POR Z-SCORE (|z| > 2.0)")
    print("="*70)
    anomalias_z = df[df["anomalia_zscore"]]
    print(anomalias_z[["fecha", COL_OBJETIVO, "zscore"]].to_string(index=False))

    print("\n" + "="*70)
    print("DIAS MARCADOS COMO ANOMALIA POR ISOLATION FOREST")
    print("="*70)
    anomalias_if = df[df["anomalia_isolation_forest"]]
    print(anomalias_if[["fecha", COL_OBJETIVO, "score_isolation_forest"]].to_string(index=False))

    # Verificacion cruzada con la anomalia de captura ya conocida (27-jul)
    fila_27 = df[df["fecha"] == FECHA_ANOMALIA_CAPTURA_CONOCIDA].iloc[0]
    print("\n" + "="*70)
    print(f"VERIFICACION CRUZADA: {FECHA_ANOMALIA_CAPTURA_CONOCIDA} "
          f"(anomalia de captura ya confirmada en Sesion 7)")
    print("="*70)
    print(f"  Z-score ese dia: {fila_27['zscore']:.2f} "
          f"-> {'DETECTADA' if fila_27['anomalia_zscore'] else 'NO DETECTADA'} por Z-score")
    print(f"  Isolation Forest ese dia: "
          f"{'DETECTADA' if fila_27['anomalia_isolation_forest'] else 'NO DETECTADA'} "
          f"por Isolation Forest")
    if not fila_27["anomalia_zscore"] and not fila_27["anomalia_isolation_forest"]:
        print("\n  CONCLUSION: ninguna de las dos tecnicas estadisticas detecto el "
              "27 de julio como anomalia. Esto confirma que la deteccion de "
              "anomalias aplicada UNICAMENTE sobre la serie recolectada tiene un "
              "punto ciego: un dia con captura fallida se ve identico, "
              "estadisticamente, a un dia real de baja actividad dentro de la "
              "cola de decaimiento. Solo se detecto gracias a la verificacion "
              "cruzada con una fuente externa (NewsAPI totalResults) en la "
              "Sesion 7, no por el analisis estadistico de la serie en si.")

    df.to_csv("anomalias_detectadas.csv", index=False)

    # Grafico
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df["fecha"], df[COL_OBJETIVO], color="black", linewidth=1.2,
            marker="o", markersize=3, label="Volumen diario")

    z_pts = df[df["anomalia_zscore"]]
    ax.scatter(z_pts["fecha"], z_pts[COL_OBJETIVO], color="crimson", s=120,
               marker="^", zorder=5, label="Anomalia (Z-score)")

    if_pts = df[df["anomalia_isolation_forest"]]
    ax.scatter(if_pts["fecha"], if_pts[COL_OBJETIVO], color="darkorange", s=200,
               marker="o", facecolors="none", linewidths=2, zorder=4,
               label="Anomalia (Isolation Forest)")

    fila_27_fecha = pd.to_datetime(FECHA_ANOMALIA_CAPTURA_CONOCIDA)
    ax.scatter([fila_27_fecha], [0], color="blue", s=250, marker="x",
               linewidths=3, zorder=6, label="27-jul: anomalia de captura\n(no detectada por metodos estadisticos)")

    ax.set_title("Deteccion de anomalias sobre el volumen diario de cobertura")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Articulos publicados")
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.3)
    plt.xticks(rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig("anomalias_detectadas.png", dpi=150)
    print("\nGrafico guardado en: anomalias_detectadas.png")


if __name__ == "__main__":
    main()