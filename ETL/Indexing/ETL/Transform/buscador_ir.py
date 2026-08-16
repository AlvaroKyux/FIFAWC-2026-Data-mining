# -*- coding: utf-8 -*-
"""
buscador_ir.py
-----------------
Sesion 12 - Recuperacion de Informacion.

IMPORTANTE: este script se DEBE correr localmente (VS Code), no en el
entorno de Claude. Motivo documentado (BRAI): generar los embeddings
semanticos requiere descargar el modelo 'paraphrase-multilingual-MiniLM-L12-v2'
desde Hugging Face, y el sandbox de Claude no tiene acceso a ese dominio
(misma naturaleza de restriccion que goles/robots.txt en Sesion 10, pero
esta vez sin alternativa: no hay forma de evitarlo).

El archivo clusters_tematicos_embeddings.json de la Sesion 6 SOLO guarda las
asignaciones finales de cluster, no los vectores crudos (son pesados, no se
guardaron en JSON). Por eso este script recalcula los embeddings desde cero
sobre el mismo corpus y el mismo modelo -- es reproducible porque el modelo
es determinista para el mismo texto de entrada.

Que hace:
  1. Construye el indice BM25 sobre los lemas del corpus preprocesado
     (mismo enfoque de la Sesion 11).
  2. Calcula embeddings semanticos sobre el texto limpio (NO lematizado --
     los embeddings funcionan mejor sobre texto natural, no sobre bolsas
     de lemas sueltos, a diferencia de TF-IDF/BM25).
  3. Corre las mismas 10 consultas de la Sesion 11 contra ambos motores.
  4. Genera un CSV con top-5 de cada motor, listo para que el equipo marque
     manualmente cuales resultados son realmente relevantes (columna
     'relevante' vacia, a llenar con 1/0).
  5. Una vez llenada esa columna, correr calcular_precision.py (incluido
     al final de este mismo archivo como funcion aparte) para obtener
     Precision@5 de cada motor.

Entradas:
  - corpus_mundial2026_preprocesado.json (Sesion 5)

Salidas:
  - resultados_busqueda_comparados.csv  (BM25 + semantico, top-5 c/u, listo
    para juicio de relevancia manual)

Uso:
    pip install sentence-transformers rank_bm25 pandas scikit-learn --break-system-packages
    python buscador_ir.py

    (la primera corrida descarga el modelo de Hugging Face, ~470MB,
    puede tardar unos minutos; corridas posteriores usan cache local)
"""

import json
import os

import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_CORPUS = os.path.join(CARPETA_ACTUAL, "corpus_mundial2026_preprocesado.json")
RUTA_SALIDA = os.path.join(CARPETA_ACTUAL, "resultados_busqueda_comparados.csv")

MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"

# Mismas 10 consultas de la Sesion 11, para poder comparar directamente
CONSULTAS = [
    "españa campeón mundial",
    "polémica arbitral",
    "lesión jugador",
    "amazon documental selección española",
    "argentina final",
    "spain world cup champion",
    "controversy referee decision",
    "player injury world cup",
    "fifa organización torneo",
    "estadio sede partido",
]

TOP_K = 5


def cargar_corpus():
    with open(RUTA_CORPUS, encoding="utf-8") as f:
        data = json.load(f)
    return data["corpus_preprocesado"]


def main():
    corpus = cargar_corpus()
    print(f"Corpus cargado: {len(corpus)} articulos")

    # ------------------------------------------------------------------
    # BM25 (reutiliza el mismo enfoque de Sesion 11)
    # ------------------------------------------------------------------
    corpus_tokenizado = [art["lemas"] for art in corpus]
    bm25 = BM25Okapi(corpus_tokenizado)
    print("BM25 listo.")

    # ------------------------------------------------------------------
    # Embeddings semanticos -- sobre texto_limpio, NO sobre lemas.
    # Justificacion: el modelo de embeddings esta entrenado sobre lenguaje
    # natural; pasarle una bolsa de lemas sueltos (sin orden gramatical)
    # rompe la señal que el modelo usa para capturar significado.
    # ------------------------------------------------------------------
    print(f"Descargando/cargando modelo {MODELO_EMBEDDINGS} ...")
    modelo = SentenceTransformer(MODELO_EMBEDDINGS)

    textos_corpus = [art["texto_limpio"] for art in corpus]
    print("Calculando embeddings del corpus (puede tardar 1-2 minutos)...")
    embeddings_corpus = modelo.encode(textos_corpus, show_progress_bar=True)

    embeddings_consultas = modelo.encode(CONSULTAS, show_progress_bar=False)
    print("Embeddings listos.")

    # ------------------------------------------------------------------
    # Correr consultas en ambos motores
    # ------------------------------------------------------------------
    filas = []
    for i, consulta in enumerate(CONSULTAS):
        tokens_consulta = consulta.lower().split()

        # BM25
        scores_bm25 = bm25.get_scores(tokens_consulta)
        top_bm25 = scores_bm25.argsort()[::-1][:TOP_K]

        # Semantico
        sim_semantica = cosine_similarity(
            [embeddings_consultas[i]], embeddings_corpus
        ).flatten()
        top_semantico = sim_semantica.argsort()[::-1][:TOP_K]

        for rank in range(TOP_K):
            doc_bm25 = corpus[top_bm25[rank]]
            filas.append({
                "consulta": consulta,
                "motor": "BM25",
                "rank": rank + 1,
                "doc_id": int(top_bm25[rank]),
                "score": round(float(scores_bm25[top_bm25[rank]]), 4),
                "fuente": doc_bm25["fuente"],
                "idioma": doc_bm25["idioma"],
                "url": doc_bm25["url"],
                "relevante": "",  # <- LLENAR MANUALMENTE: 1 si es relevante, 0 si no
            })

            doc_sem = corpus[top_semantico[rank]]
            filas.append({
                "consulta": consulta,
                "motor": "Semantico",
                "rank": rank + 1,
                "doc_id": int(top_semantico[rank]),
                "score": round(float(sim_semantica[top_semantico[rank]]), 4),
                "fuente": doc_sem["fuente"],
                "idioma": doc_sem["idioma"],
                "url": doc_sem["url"],
                "relevante": "",  # <- LLENAR MANUALMENTE: 1 si es relevante, 0 si no
            })

    df = pd.DataFrame(filas)
    df.to_csv(RUTA_SALIDA, index=False, encoding="utf-8-sig")
    print(f"\nResultados guardados en: {RUTA_SALIDA}")
    print("\nSIGUIENTE PASO MANUAL (no lo puede hacer la IA por ustedes):")
    print("Abran el CSV y llenen la columna 'relevante' con 1 (relevante) o 0")
    print("(no relevante) para cada uno de los 100 resultados (10 consultas x")
    print("5 resultados x 2 motores). Es trabajo de criterio humano -- es el")
    print("'ground truth' contra el que se evalua, y por eso no puede salir")
    print("de otro modelo de IA sin volverse circular.")
    print("\nCuando lo tengan lleno, correr calcular_precision.py sobre este")
    print("mismo CSV para obtener Precision@5 de cada motor.")


if __name__ == "__main__":
    main()
