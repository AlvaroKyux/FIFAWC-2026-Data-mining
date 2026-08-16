# -*- coding: utf-8 -*-
"""
construir_series_temporales.py
--------------------------------
Sesion 7 - Construccion de Series Temporales.

Decision de fuente de datos (documentada en Bitacora BRAI):
  El temario original asume series basadas en resultados deportivos, pero
  el Mundial 2026 ya concluyo (final el 19 de julio de 2026), por lo que
  worldcup26.ir y StatsBomb (Qatar 2022) son fotografias estaticas, no
  series que evolucionen en el tiempo.

  En su lugar se usa el campo 'fecha_publicacion' del corpus de NewsAPI
  (Sesion 4), que si es una serie real: volumen de cobertura mediatica
  dia a dia. Se cruza ademas con la asignacion de cluster tematico de la
  Sesion 6 (embeddings) para obtener series por tema, no solo agregadas,
  manteniendo continuidad con el trabajo previo del proyecto.

Entradas:
  - corpus_mundial2026_raw.json      (Sesion 4: fecha_publicacion, url, idioma)
  - clusters_tematicos_embeddings.json (Sesion 6: cluster por url)

Salida:
  - series_diarias.csv  (una fila por dia, incluyendo dias en cero)
  - serie_volumen_diario.png (visualizacion con evento de referencia marcado)

Uso:
    python construir_series_temporales.py
"""

import json
import os
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_CORPUS = os.path.join(CARPETA_ACTUAL, "..", "corpus_mundial2026_raw.json")
RUTA_CLUSTERS = os.path.join(CARPETA_ACTUAL, "..", "clusters_tematicos_embeddings.json")
RUTA_SALIDA_CSV = os.path.join(CARPETA_ACTUAL, "..", "Load", "series_diarias.csv")
RUTA_SALIDA_PNG = os.path.join(CARPETA_ACTUAL, "..", "Load", "serie_volumen_diario.png")

# Fecha real de la final del Mundial 2026 (Espana 1-0 Argentina, tiempo extra,
# MetLife Stadium). Se usa como evento de referencia para interpretar picos,
# no como un dato inventado -- es un hecho verificable externamente.
FECHA_FINAL_MUNDIAL = "2026-07-19"


def cargar_corpus(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    articulos = data["corpus"]
    filas = []
    for art in articulos:
        fecha_pub = art.get("fecha_publicacion")
        if not fecha_pub:
            continue
        fecha = fecha_pub[:10]  # YYYY-MM-DD, se descarta la hora
        filas.append({
            "url": art.get("url"),
            "idioma": art.get("idioma"),
            "fecha": fecha,
        })
    return pd.DataFrame(filas)


def cargar_clusters(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        data = json.load(f)
    asignaciones = data["clustering_combinado"]["asignacion_cluster_por_articulo"]
    df = pd.DataFrame(asignaciones)
    # Nos quedamos solo con url y cluster; el idioma ya viene del corpus.
    return df[["url", "cluster"]]


def construir_serie_diaria(df_corpus, df_clusters):
    # Cruce por url. Regla BRAI: verificar cobertura del cruce antes de
    # confiar en el resultado (no asumir que el join es perfecto).
    df = df_corpus.merge(df_clusters, on="url", how="left")

    n_sin_cluster = df["cluster"].isna().sum()
    if n_sin_cluster > 0:
        print(f"AVISO: {n_sin_cluster} de {len(df)} articulos no tienen "
              f"cluster asignado (no hicieron match por url). Se cuentan "
              f"en el total pero no en las columnas por cluster.")

    # Rango completo de fechas, incluyendo dias sin ningun articulo.
    fecha_min = df["fecha"].min()
    fecha_max = df["fecha"].max()
    rango_fechas = pd.date_range(fecha_min, fecha_max, freq="D").strftime("%Y-%m-%d")

    resumen = pd.DataFrame({"fecha": rango_fechas})

    # Total por dia
    total_dia = df.groupby("fecha").size().rename("total_articulos")
    resumen = resumen.merge(total_dia, on="fecha", how="left")

    # Por idioma
    for idioma in ["es", "en"]:
        col = df[df["idioma"] == idioma].groupby("fecha").size().rename(idioma)
        resumen = resumen.merge(col, on="fecha", how="left")

    # Por cluster tematico (0, 1, 2 segun Sesion 6)
    for cluster_id in sorted(df["cluster"].dropna().unique()):
        nombre_col = f"cluster_{int(cluster_id)}"
        col = (df[df["cluster"] == cluster_id]
               .groupby("fecha").size().rename(nombre_col))
        resumen = resumen.merge(col, on="fecha", how="left")

    resumen = resumen.fillna(0)
    cols_numericas = [c for c in resumen.columns if c != "fecha"]
    resumen[cols_numericas] = resumen[cols_numericas].astype(int)

    return resumen


def graficar_serie(resumen, ruta_salida):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(resumen["fecha"], resumen["total_articulos"],
            marker="o", markersize=3, linewidth=1.3, color="#1f4e8c")

    if FECHA_FINAL_MUNDIAL in resumen["fecha"].values:
        idx_final = resumen.index[resumen["fecha"] == FECHA_FINAL_MUNDIAL][0]
        ax.axvline(idx_final, color="crimson", linestyle="--", linewidth=1,
                    label=f"Final del Mundial ({FECHA_FINAL_MUNDIAL})")

    ax.set_title("Volumen diario de articulos - Corpus Mundial 2026 (NewsAPI)")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Articulos publicados")
    ax.set_xticks(range(0, len(resumen), 2))
    ax.set_xticklabels(resumen["fecha"][::2], rotation=45, ha="right", fontsize=8)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(ruta_salida, dpi=150)
    print(f"Grafico guardado en: {ruta_salida}")


def main():
    df_corpus = cargar_corpus(RUTA_CORPUS)
    df_clusters = cargar_clusters(RUTA_CLUSTERS)

    print(f"Articulos cargados del corpus: {len(df_corpus)}")
    print(f"Articulos con cluster asignado: {len(df_clusters)}")

    resumen = construir_serie_diaria(df_corpus, df_clusters)

    dias_en_cero = resumen[resumen["total_articulos"] == 0]["fecha"].tolist()
    print(f"\nDias sin ningun articulo (pendiente verificar si es hueco real "
          f"o artefacto de recoleccion, ver nota BRAI): {dias_en_cero}")

    os.makedirs(os.path.dirname(RUTA_SALIDA_CSV), exist_ok=True)
    resumen.to_csv(RUTA_SALIDA_CSV, index=False, encoding="utf-8")
    print(f"\nSerie diaria guardada en: {RUTA_SALIDA_CSV}")
    print(resumen.to_string(index=False))

    graficar_serie(resumen, RUTA_SALIDA_PNG)


if __name__ == "__main__":
    main()
