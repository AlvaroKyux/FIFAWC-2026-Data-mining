# -*- coding: utf-8 -*-
"""
construir_corpus_mundial2026.py
---------------------------------
Construccion del CORPUS REAL de Sesion 4 (Recuperacion de Informacion),
tras la evaluacion de fuentes documentada:
  - GDELT: descartado (0 resultados ES + throttling que impidio diagnostico)
  - NewsAPI: ACEPTADO como fuente unica, ambos idiomas confirmados (200 OK,
    resultados relevantes y bien fechados en pruebas del 07/08/2026)

Alcance (regla del proyecto: filtrado agresivo de volumen):
  - Bilingue ES + EN unicamente.
  - Solo noticias del Mundial 2026 / temporada regular actual (no historico).
  - Tier gratuito de NewsAPI limita naturalmente a ~100 articulos reales
    por query aunque 'totalResults' reporte miles -> esto ya actua como
    filtro de volumen, no hace falta imponer un limite adicional agresivo.
  - Se usan MUY pocas queries (4 en total) para mantenernos muy por debajo
    del limite de 100 peticiones/dia del plan gratuito.

Campos guardados por articulo: titulo, descripcion, contenido (truncado a
~200 caracteres por el tier gratuito -- NO es el articulo completo, lo cual
es intencional: evita problemas de derechos de autor por reproduccion
extensa y es consistente con el alcance de "corpus para mineria de texto",
no "archivo de articulos completos").

Requiere: pip install requests --break-system-packages

Uso:
    1. Asegurate de tener newsapi_key.txt en esta misma carpeta (o la
       variable de entorno NEWSAPI_KEY configurada).
    2. python construir_corpus_mundial2026.py
"""

import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta

BASE_URL = "https://newsapi.org/v2/everything"


def cargar_api_key():
    key = os.environ.get("NEWSAPI_KEY")
    if key:
        return key.strip()
    ruta_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsapi_key.txt")
    if os.path.exists(ruta_key):
        with open(ruta_key, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


API_KEY = cargar_api_key()

DIAS_ATRAS = 28  # dentro del limite de ~1 mes del tier gratuito
FECHA_FIN = datetime.now(timezone.utc)
FECHA_INICIO = FECHA_FIN - timedelta(days=DIAS_ATRAS)

PAUSA_ENTRE_PETICIONES = 1.5  # NewsAPI es mucho mas permisivo que GDELT
PAGE_SIZE = 100  # maximo del tier gratuito

# Queries deliberadamente pocas y especificas -- alineadas a tu regla de
# "filtrado agresivo": preferimos pocas queries de alta relevancia en vez
# de muchas queries genericas que inflarian el corpus con ruido.
QUERIES_CORPUS = [
    {"nombre": "es_mundial2026", "q": '"Mundial 2026"', "language": "es"},
    {"nombre": "es_seleccion_espanola", "q": '"selección española" Mundial', "language": "es"},
    {"nombre": "en_worldcup2026", "q": '"World Cup 2026"', "language": "en"},
    {"nombre": "en_fifa_worldcup", "q": '"FIFA World Cup" 2026', "language": "en"},
]


def descargar_query(nombre: str, q: str, language: str) -> list:
    params = {
        "apiKey": API_KEY,
        "q": q,
        "language": language,
        "from": FECHA_INICIO.strftime("%Y-%m-%d"),
        "to": FECHA_FIN.strftime("%Y-%m-%d"),
        "sortBy": "relevancy",
        "pageSize": PAGE_SIZE,
        "page": 1,
    }

    print(f"\n{'='*70}")
    print(f"DESCARGANDO: {nombre} (idioma={language})")
    print(f"Query: {q}")
    print(f"{'='*70}")

    resp = requests.get(BASE_URL, params=params, timeout=20)
    if resp.status_code != 200:
        print(f"ERROR HTTP {resp.status_code}: {resp.text[:300]}")
        return []

    data = resp.json()
    articulos_crudos = data.get("articles", [])
    print(f"Total reportado por API: {data.get('totalResults', 0)}")
    print(f"Articulos descargados esta pagina: {len(articulos_crudos)}")

    corpus_parcial = []
    for art in articulos_crudos:
        corpus_parcial.append({
            "query_origen": nombre,
            "idioma": language,
            "titulo": art.get("title"),
            "descripcion": art.get("description"),
            "contenido_truncado": art.get("content"),  # truncado por tier gratuito
            "fuente": art.get("source", {}).get("name"),
            "autor": art.get("author"),
            "url": art.get("url"),
            "url_imagen": art.get("urlToImage"),
            "fecha_publicacion": art.get("publishedAt"),
        })

    return corpus_parcial


def main():
    if not API_KEY:
        print("ERROR: no se encontro la API key (newsapi_key.txt o variable de entorno).")
        return

    print("CONSTRUCCION DEL CORPUS - MUNDIAL 2026 (ES + EN)")
    print(f"Fecha de ejecucion: {datetime.now(timezone.utc).isoformat()}")
    print(f"Rango de fechas: {FECHA_INICIO.date()} a {FECHA_FIN.date()}")

    corpus_completo = []
    for i, query in enumerate(QUERIES_CORPUS):
        articulos = descargar_query(query["nombre"], query["q"], query["language"])
        corpus_completo.extend(articulos)
        if i < len(QUERIES_CORPUS) - 1:
            time.sleep(PAUSA_ENTRE_PETICIONES)

    # Deduplicacion por URL (queries distintas pueden traer el mismo articulo)
    vistos = set()
    corpus_deduplicado = []
    for art in corpus_completo:
        url = art.get("url")
        if url and url not in vistos:
            vistos.add(url)
            corpus_deduplicado.append(art)

    print(f"\n{'='*70}")
    print("RESUMEN DE CONSTRUCCION DEL CORPUS")
    print(f"{'='*70}")
    print(f"Articulos totales descargados (con duplicados): {len(corpus_completo)}")
    print(f"Articulos unicos tras deduplicacion por URL: {len(corpus_deduplicado)}")

    por_idioma = {}
    for art in corpus_deduplicado:
        idioma = art["idioma"]
        por_idioma[idioma] = por_idioma.get(idioma, 0) + 1
    print(f"Distribucion por idioma: {por_idioma}")

    resultado = {
        "metadata": {
            "proyecto": "FIFA WC2026 - Grupo 09_02",
            "sesion": "Sesion 4 - Recuperacion de Informacion",
            "fuente": "NewsAPI (newsapi.org), tier Developer (gratuito)",
            "fecha_construccion": datetime.now(timezone.utc).isoformat(),
            "rango_fechas": f"{FECHA_INICIO.date()} a {FECHA_FIN.date()}",
            "idiomas": ["es", "en"],
            "queries_usadas": [q["nombre"] for q in QUERIES_CORPUS],
            "total_articulos_unicos": len(corpus_deduplicado),
            "distribucion_por_idioma": por_idioma,
            "nota_limitacion": "El campo 'contenido_truncado' esta limitado a ~200 "
                                "caracteres por el tier gratuito de NewsAPI, no es el "
                                "articulo completo. El corpus se basa en titulo + "
                                "descripcion + fragmento corto.",
        },
        "corpus": corpus_deduplicado,
    }

    ruta_salida = "corpus_mundial2026_raw.json"
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\nCorpus guardado en: {ruta_salida}")


if __name__ == "__main__":
    main()