# -*- coding: utf-8 -*-
"""
construir_indice.py
----------------------
Sesion 11 - Indexacion.

Punto BRAI central de esta sesion: en la Sesion 6, TF-IDF fallo para
CLUSTERING (silhouette casi cero) por snippets cortos (~200 caracteres)
con alto solapamiento lexico. Eso no implica automaticamente que TF-IDF
o BM25 fallen para INDEXACION -- son tareas distintas (clustering separa
documentos entre si; indexacion solo discrimina contra una consulta
puntual). Este script prueba esa hipotesis con evidencia, no la asume.

Entrada:
  - corpus_mundial2026_preprocesado.json (Sesion 5: 330 articulos, 10,518 lemas)

Salida:
  - indice_invertido.json   (termino -> lista de doc_id con frecuencia)
  - resultados_tfidf.csv    (ranking TF-IDF por consulta)
  - resultados_bm25.csv     (ranking BM25 por consulta)
  - comparacion_tfidf_bm25.csv (tabla comparativa lado a lado)

Uso:
    pip install scikit-learn rank_bm25 pandas --break-system-packages
    python construir_indice.py
"""

import json
import os
from collections import defaultdict

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from rank_bm25 import BM25Okapi

CARPETA_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_CORPUS = os.path.join(CARPETA_ACTUAL, "..", "corpus_mundial2026_preprocesado.json")
RUTA_SALIDA_INDICE = os.path.join(CARPETA_ACTUAL, "..", "Load", "indice_invertido.json")
RUTA_SALIDA_TFIDF = os.path.join(CARPETA_ACTUAL, "..", "Load", "resultados_tfidf.csv")
RUTA_SALIDA_BM25 = os.path.join(CARPETA_ACTUAL, "..", "Load", "resultados_bm25.csv")
RUTA_SALIDA_COMPARACION = os.path.join(CARPETA_ACTUAL, "..", "Load", "comparacion_tfidf_bm25.csv")

# --------------------------------------------------------------------------
# Consultas de prueba: mezcla deliberada de tipos, en espanol e ingles, para
# poder ver en la Sesion 12 en que tipo de consulta gana cada tecnica.
# --------------------------------------------------------------------------
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


def cargar_corpus():
    with open(RUTA_CORPUS, encoding="utf-8") as f:
        data = json.load(f)
    return data["corpus_preprocesado"]


def construir_indice_invertido(corpus):
    """termino -> {doc_id: frecuencia}"""
    indice = defaultdict(dict)
    for doc_id, art in enumerate(corpus):
        conteo = defaultdict(int)
        for lema in art["lemas"]:
            conteo[lema] += 1
        for lema, freq in conteo.items():
            indice[lema][doc_id] = freq
    return indice


def main():
    os.makedirs(os.path.join(CARPETA_ACTUAL, "..", "Load"), exist_ok=True)
    corpus = cargar_corpus()
    print(f"Corpus cargado: {len(corpus)} articulos")

    # ------------------------------------------------------------------
    # 1. Indice invertido
    # ------------------------------------------------------------------
    indice = construir_indice_invertido(corpus)
    print(f"Indice invertido construido: {len(indice)} terminos unicos")

    # Guardar una version resumida (top 20 terminos mas frecuentes en doc-count,
    # el indice completo puede pesar mucho para JSON legible)
    terminos_por_docfreq = sorted(
        indice.items(), key=lambda kv: len(kv[1]), reverse=True
    )
    resumen_indice = {
        "total_terminos": len(indice),
        "total_documentos": len(corpus),
        "top_20_terminos_mas_frecuentes": [
            {"termino": t, "num_documentos": len(docs), "frecuencia_total": sum(docs.values())}
            for t, docs in terminos_por_docfreq[:20]
        ],
        "indice_completo": {t: docs for t, docs in indice.items()},
    }
    with open(RUTA_SALIDA_INDICE, "w", encoding="utf-8") as f:
        json.dump(resumen_indice, f, ensure_ascii=False, indent=2)
    print(f"Indice guardado en: {RUTA_SALIDA_INDICE}")

    # ------------------------------------------------------------------
    # 2. TF-IDF
    # ------------------------------------------------------------------
    documentos_texto = [" ".join(art["lemas"]) for art in corpus]
    vectorizer = TfidfVectorizer()
    matriz_tfidf = vectorizer.fit_transform(documentos_texto)
    print(f"Matriz TF-IDF: {matriz_tfidf.shape[0]} docs x {matriz_tfidf.shape[1]} terminos")

    # ------------------------------------------------------------------
    # 3. BM25
    # ------------------------------------------------------------------
    corpus_tokenizado = [art["lemas"] for art in corpus]
    bm25 = BM25Okapi(corpus_tokenizado)
    print("Indice BM25 construido (k1=1.5, b=0.75, valores por defecto de rank_bm25)")

    # ------------------------------------------------------------------
    # 4. Correr consultas y comparar
    # ------------------------------------------------------------------
    filas_tfidf = []
    filas_bm25 = []
    filas_comparacion = []

    for consulta in CONSULTAS:
        tokens_consulta = consulta.lower().split()

        # --- TF-IDF: transformar la consulta al mismo espacio vectorial ---
        vector_consulta = vectorizer.transform([" ".join(tokens_consulta)])
        similitudes = cosine_similarity(vector_consulta, matriz_tfidf).flatten()
        top5_tfidf = similitudes.argsort()[::-1][:5]

        # --- BM25 ---
        scores_bm25 = bm25.get_scores(tokens_consulta)
        top5_bm25 = scores_bm25.argsort()[::-1][:5]

        for rank, doc_id in enumerate(top5_tfidf, start=1):
            art = corpus[doc_id]
            filas_tfidf.append({
                "consulta": consulta,
                "rank": rank,
                "doc_id": doc_id,
                "score": round(float(similitudes[doc_id]), 4),
                "fuente": art["fuente"],
                "idioma": art["idioma"],
                "url": art["url"],
            })

        for rank, doc_id in enumerate(top5_bm25, start=1):
            art = corpus[doc_id]
            filas_bm25.append({
                "consulta": consulta,
                "rank": rank,
                "doc_id": doc_id,
                "score": round(float(scores_bm25[doc_id]), 4),
                "fuente": art["fuente"],
                "idioma": art["idioma"],
                "url": art["url"],
            })

        # Comparacion lado a lado (top-3) + overlap de resultados
        top3_tfidf_set = set(top5_tfidf[:3].tolist())
        top3_bm25_set = set(top5_bm25[:3].tolist())
        overlap = len(top3_tfidf_set & top3_bm25_set)
        filas_comparacion.append({
            "consulta": consulta,
            "top1_tfidf": corpus[top5_tfidf[0]]["fuente"] if similitudes[top5_tfidf[0]] > 0 else "(sin match)",
            "top1_tfidf_score": round(float(similitudes[top5_tfidf[0]]), 4),
            "top1_bm25": corpus[top5_bm25[0]]["fuente"] if scores_bm25[top5_bm25[0]] > 0 else "(sin match)",
            "top1_bm25_score": round(float(scores_bm25[top5_bm25[0]]), 4),
            "overlap_top3": overlap,
            "coinciden_top1": bool(top5_tfidf[0] == top5_bm25[0]),
        })

    pd.DataFrame(filas_tfidf).to_csv(RUTA_SALIDA_TFIDF, index=False, encoding="utf-8-sig")
    pd.DataFrame(filas_bm25).to_csv(RUTA_SALIDA_BM25, index=False, encoding="utf-8-sig")
    df_comparacion = pd.DataFrame(filas_comparacion)
    df_comparacion.to_csv(RUTA_SALIDA_COMPARACION, index=False, encoding="utf-8-sig")

    print(f"\nResultados guardados:")
    print(f"  {RUTA_SALIDA_TFIDF}")
    print(f"  {RUTA_SALIDA_BM25}")
    print(f"  {RUTA_SALIDA_COMPARACION}")

    print(f"\n{'=' * 70}")
    print("RESUMEN DE COMPARACION")
    print(f"{'=' * 70}")
    print(df_comparacion.to_string(index=False))

    coincidencias = df_comparacion["coinciden_top1"].sum()
    overlap_promedio = df_comparacion["overlap_top3"].mean()
    print(f"\nTop-1 coincide entre TF-IDF y BM25 en {coincidencias}/{len(CONSULTAS)} consultas")
    print(f"Overlap promedio en top-3: {overlap_promedio:.1f} de 3 documentos")


if __name__ == "__main__":
    main()
