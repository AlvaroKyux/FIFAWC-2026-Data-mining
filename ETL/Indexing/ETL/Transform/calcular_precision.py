# -*- coding: utf-8 -*-
"""
calcular_precision.py
------------------------
Sesion 12 - Recuperacion de Informacion (segunda parte).

Corre esto DESPUES de llenar manualmente la columna 'relevante' en
resultados_busqueda_comparados.csv (generado por buscador_ir.py).

Calcula Precision@5 por consulta y promedio general, para BM25 y para
el buscador semantico, y genera la grafica comparativa.

Uso:
    python calcular_precision.py
"""

import os

import pandas as pd
import matplotlib.pyplot as plt

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_ENTRADA = os.path.join(CARPETA_ACTUAL, "resultados_busqueda_comparados.csv")
RUTA_SALIDA_CSV = os.path.join(CARPETA_ACTUAL, "precision_por_consulta.csv")
RUTA_SALIDA_PNG = os.path.join(CARPETA_ACTUAL, "precision_comparacion.png")


def main():
    df = pd.read_csv(RUTA_ENTRADA)

    if df["relevante"].isna().any() or (df["relevante"] == "").any():
        print("ERROR: la columna 'relevante' todavia tiene celdas vacias.")
        print("Llenen TODAS las filas con 1 o 0 antes de correr este script.")
        return

    df["relevante"] = df["relevante"].astype(int)

    # Precision@5 = relevantes encontrados / 5, por consulta y motor
    precision = (
        df.groupby(["consulta", "motor"])["relevante"]
        .agg(relevantes_encontrados="sum", precision_at_5=lambda x: x.sum() / len(x))
        .reset_index()
    )
    precision.to_csv(RUTA_SALIDA_CSV, index=False, encoding="utf-8-sig")

    print("Precision@5 por consulta:")
    print(precision.to_string(index=False))

    resumen = df.groupby("motor")["relevante"].mean().reset_index()
    resumen.columns = ["motor", "precision_at_5_promedio"]
    print("\nPromedio general:")
    print(resumen.to_string(index=False))

    # Grafica comparativa
    pivote = precision.pivot(index="consulta", columns="motor", values="precision_at_5")
    fig, ax = plt.subplots(figsize=(10, 6))
    pivote.plot(kind="barh", ax=ax)
    ax.set_xlabel("Precision@5")
    ax.set_title("Precision@5 por consulta: BM25 vs Buscador Semantico")
    ax.legend(title="Motor")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RUTA_SALIDA_PNG, dpi=150)
    print(f"\nGrafica guardada en: {RUTA_SALIDA_PNG}")


if __name__ == "__main__":
    main()
