# -*- coding: utf-8 -*-
"""
verificar_dias_cero.py
------------------------
Sesion 7 - Verificacion puntual de los dias sin articulos detectados en
construir_series_temporales.py (2026-07-27 y 2026-08-02).

Objetivo (regla BRAI): distinguir si el hueco es un HECHO REAL (no hubo
cobertura del Mundial esos dias) o un ARTEFACTO DE RECOLECCION (las 4
queries originales de la Sesion 4 no capturaron todo lo que existia).

Se consulta NewsAPI acotando 'from' y 'to' a cada fecha individual, con
las mismas 4 queries usadas en la construccion del corpus original, para
que la comparacion sea justa (no se agregan queries nuevas que cambiarian
las reglas del experimento).

Requiere: newsapi_key.txt en esta misma carpeta (o variable de entorno
NEWSAPI_KEY), igual que corpus_FIFA_WC.py.

Uso:
    python verificar_dias_cero.py
"""

import os
import time
import json
import requests

BASE_URL = "https://newsapi.org/v2/everything"

DIAS_A_VERIFICAR = ["2026-07-27", "2026-08-02"]

# Mismas queries que se usaron para construir el corpus original (Sesion 4),
# para que la verificacion sea comparable y no introduzca un sesgo nuevo.
QUERIES = {
    "es_mundial2026": {"q": "mundial 2026", "language": "es"},
    "es_seleccion_espanola": {"q": "seleccion espanola mundial", "language": "es"},
    "en_worldcup2026": {"q": "world cup 2026", "language": "en"},
    "en_fifa_worldcup": {"q": "FIFA world cup", "language": "en"},
}


def cargar_api_key():
    key = os.environ.get("NEWSAPI_KEY")
    if key:
        return key.strip()
    ruta_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsapi_key.txt")
    if os.path.exists(ruta_key):
        with open(ruta_key, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def main():
    api_key = cargar_api_key()
    if not api_key:
        print("ERROR: no se encontro newsapi_key.txt ni la variable NEWSAPI_KEY.")
        return

    resultados = {}

    for fecha in DIAS_A_VERIFICAR:
        print(f"\n{'='*60}\nVerificando {fecha}\n{'='*60}")
        resultados[fecha] = {}

        for nombre_query, params_base in QUERIES.items():
            params = {
                "q": params_base["q"],
                "language": params_base["language"],
                "from": fecha,
                "to": fecha,
                "sortBy": "publishedAt",
                "pageSize": 100,
                "apiKey": api_key,
            }
            resp = requests.get(BASE_URL, params=params)

            if resp.status_code == 200:
                data = resp.json()
                total = data.get("totalResults", 0)
                n_traidos = len(data.get("articles", []))
                print(f"  {nombre_query}: totalResults={total}, "
                      f"articulos_traidos={n_traidos}")
                resultados[fecha][nombre_query] = {
                    "status": 200,
                    "totalResults": total,
                    "articulos_traidos": n_traidos,
                }
            else:
                print(f"  {nombre_query}: ERROR {resp.status_code} - {resp.text[:200]}")
                resultados[fecha][nombre_query] = {
                    "status": resp.status_code,
                    "error": resp.text[:200],
                }

            time.sleep(1.5)  # misma pausa que corpus_FIFA_WC.py

    ruta_salida = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "Load", "verificacion_dias_cero.json")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n\nResultado guardado en: {ruta_salida}")



if __name__ == "__main__":
    main()