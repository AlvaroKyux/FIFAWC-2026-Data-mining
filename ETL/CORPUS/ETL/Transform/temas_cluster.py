# -*- coding: utf-8 -*-
"""
clustering_tematico.py
------------------------
Sesion 6: Similaridad y Embeddings.

Toma el corpus preprocesado de Sesion 5 (corpus_mundial2026_preprocesado.json,
con lemas ya limpios) y aplica:
  1. Vectorizacion TF-IDF (unigrama + bigrama, para capturar frases como
     "balon de oro" o "world cup").
  2. Seleccion de k (numero de clusters) por maximizacion de silhouette
     score, en vez de fijar k a mano -- decision justificable con metrica,
     no arbitraria.
  3. K-Means clustering.
  4. Reduccion dimensional para visualizacion: PCA (rapido, determinista)
     y t-SNE (mejor separacion visual de clusters no lineales).
  5. Extraccion de terminos representativos por cluster (mayor peso TF-IDF
     promedio dentro del cluster) para nombrar los "temas".

DECISION METODOLOGICA CLAVE (diagnostico empirico, no supuesto a priori):

El corpus es bilingue ES/EN. El vocabulario en espanol y en ingles casi no
se superpone (salvo nombres propios: "Messi", "Mbappe", "2026"). Esto
significa que un TF-IDF sobre el corpus COMBINADO puede terminar
clusterizando por IDIOMA en vez de por TEMA, que no es lo que buscamos
(el entregable pide "temas", no "idiomas").

Este script:
  (a) Corre primero el clustering sobre el corpus COMBINADO.
  (b) Mide la "pureza de idioma" de los clusters resultantes: que fraccion
      de cada cluster pertenece al idioma mayoritario de ese cluster,
      promediado sobre todos los clusters.
  (c) Si la pureza es muy alta (>85%), es evidencia de que el combinado
      esta clusterizando por idioma, no por tema -> se descarta el enfoque
      combinado y se reporta el clustering POR IDIOMA POR SEPARADO como
      resultado final (es el que efectivamente aisla temas).
  (d) Si la pureza es baja/moderada, se mantiene el combinado como valido.

Requiere:
    pip install scikit-learn matplotlib --break-system-packages

Uso:
    python clustering_tematico.py
"""

import json
import sys
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend sin ventana, para guardar PNG directo
import matplotlib.pyplot as plt

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

RUTA_CORPUS_PREPROCESADO = "corpus_mundial2026_preprocesado.json"
RUTA_SALIDA_JSON = "clusters_tematicos.json"

UMBRAL_PUREZA_IDIOMA = 0.85  # por encima de esto, se asume clustering-por-idioma
K_TEMAS_FINAL = 3  # fijo, alineado al entregable "3 temas principales"
K_MAX_DIAGNOSTICO = 8  # rango de busqueda libre, solo para el diagnostico/evidencia

# Terminos de "ruido editorial" detectados empiricamente al correr el pipeline
# sin restriccion sobre el corpus real (k=8 libre produjo clusters que NO eran
# temas: creditos de imagen, agencias de noticias, etiquetas de navegacion del
# sitio tipo "Preview"/"Reaction"). Se filtran antes de vectorizar porque
# aparecen con frecuencia suficiente para formar su propio "cluster" sin
# aportar significado tematico.
BOILERPLATE = {
    "es": {"autor", "imagen", "imágenes", "fuente", "getty", "crédito",
           "foto", "fotografía", "agencia"},
    "en": {"getty", "images", "image", "photo", "photos", "ap", "reuters",
           "afp", "credit", "preview", "reaction", "highlight", "highlights"},
}


def cargar_corpus():
    try:
        with open(RUTA_CORPUS_PREPROCESADO, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: no se encontro {RUTA_CORPUS_PREPROCESADO}.")
        print("Corre primero preprocesar_corpus.py (Sesion 5).")
        sys.exit(1)
    return data.get("corpus_preprocesado", [])


def seleccionar_mejor_k(matriz_tfidf, k_min=2, k_max=8):
    """Elige k maximizando silhouette score. Devuelve (mejor_k, historial)."""
    n_docs = matriz_tfidf.shape[0]
    k_max = min(k_max, n_docs - 1)
    if k_max < k_min:
        return k_min, []

    historial = []
    mejor_k, mejor_score = k_min, -1
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        etiquetas = km.fit_predict(matriz_tfidf)
        if len(set(etiquetas)) < 2:
            continue
        score = silhouette_score(matriz_tfidf, etiquetas)
        historial.append({"k": k, "silhouette": round(float(score), 4), "inercia": round(float(km.inertia_), 2)})
        if score > mejor_score:
            mejor_k, mejor_score = k, score

    return mejor_k, historial


def extraer_terminos_por_cluster(vectorizer, matriz_tfidf, etiquetas, n_terminos=10):
    """Top N terminos por promedio de peso TF-IDF dentro de cada cluster."""
    vocabulario = np.array(vectorizer.get_feature_names_out())
    temas = {}
    for cluster_id in sorted(set(etiquetas)):
        indices_cluster = np.where(etiquetas == cluster_id)[0]
        promedio = np.asarray(matriz_tfidf[indices_cluster].mean(axis=0)).ravel()
        top_idx = promedio.argsort()[::-1][:n_terminos]
        temas[int(cluster_id)] = [
            {"termino": vocabulario[i], "peso_promedio": round(float(promedio[i]), 4)}
            for i in top_idx
        ]
    return temas


def medir_pureza_idioma(etiquetas, idiomas):
    """Promedio, sobre todos los clusters, de la fraccion del idioma mayoritario."""
    por_cluster = defaultdict(list)
    for etiqueta, idioma in zip(etiquetas, idiomas):
        por_cluster[etiqueta].append(idioma)

    purezas = []
    detalle = {}
    for cluster_id, lista_idiomas in por_cluster.items():
        conteo = Counter(lista_idiomas)
        total = sum(conteo.values())
        idioma_mayoritario, cantidad = conteo.most_common(1)[0]
        pureza = cantidad / total
        purezas.append(pureza)
        detalle[int(cluster_id)] = {
            "idioma_mayoritario": idioma_mayoritario,
            "pureza": round(pureza, 3),
            "distribucion": dict(conteo),
        }

    return float(np.mean(purezas)), detalle


def graficar_pca(matriz_tfidf, etiquetas, titulo, ruta_salida):
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(matriz_tfidf.toarray())

    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=etiquetas, cmap="tab10", alpha=0.7)
    plt.title(f"PCA - {titulo}")
    plt.xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% var.)")
    plt.ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% var.)")
    plt.legend(*scatter.legend_elements(), title="Cluster")
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=120)
    plt.close()


def graficar_tsne(matriz_tfidf, etiquetas, titulo, ruta_salida):
    n_docs = matriz_tfidf.shape[0]
    perplexity = min(30, max(5, n_docs // 4))
    tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity, init="pca")
    coords = tsne.fit_transform(matriz_tfidf.toarray())

    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=etiquetas, cmap="tab10", alpha=0.7)
    plt.title(f"t-SNE - {titulo}")
    plt.legend(*scatter.legend_elements(), title="Cluster")
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=120)
    plt.close()


def ejecutar_pipeline(documentos, etiqueta_run, generar_tsne=True, k_fijo=None, k_max_busqueda=8):
    """documentos: lista de dicts con 'lemas' (list[str]) e 'idioma'.

    Si k_fijo se especifica, se usa ese k directamente (no se busca).
    Si no, se busca el mejor k por silhouette en [2, k_max_busqueda].
    """
    idioma_dominante = documentos[0]["idioma"] if len(set(d["idioma"] for d in documentos)) == 1 else None
    stop_boilerplate = BOILERPLATE.get(idioma_dominante, set())

    textos = []
    for d in documentos:
        lemas_filtrados = [l for l in d["lemas"] if l not in stop_boilerplate]
        textos.append(" ".join(lemas_filtrados))
    idiomas = [d["idioma"] for d in documentos]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2 if len(documentos) > 20 else 1,
        max_df=0.45,  # excluye terminos "ubicuos del tema central" (ej. "españa",
                       # "selección") que aparecen en gran parte del corpus y
                       # ahogan el clustering de SUB-temas. Bajado de 0.9 tras
                       # evidencia real de que 0.9 dejaba pasar terminos con
                       # >50% de frecuencia documental, produciendo silhouette
                       # scores casi nulos (~0.01) y clusters sin diferenciacion.
        sublinear_tf=True,  # amortigua saltos de frecuencia (log(1+tf) en vez
                             # de tf lineal), reduce el peso de palabras que se
                             # repiten muchas veces DENTRO de un mismo articulo.
    )
    matriz = vectorizer.fit_transform(textos)

    # Diagnostico: terminos mas frecuentes ANTES del filtro max_df, para
    # documentar en el minireporte cuales palabras "ubicuas del tema central"
    # se estan excluyendo deliberadamente.
    vectorizer_diagnostico = TfidfVectorizer(ngram_range=(1, 1))
    try:
        matriz_diag = vectorizer_diagnostico.fit_transform(textos)
        doc_freq = np.asarray((matriz_diag > 0).sum(axis=0)).ravel()
        vocab_diag = np.array(vectorizer_diagnostico.get_feature_names_out())
        proporcion_doc_freq = doc_freq / len(documentos)
        idx_dominantes = np.where(proporcion_doc_freq > 0.45)[0]
        terminos_excluidos = sorted(
            zip(vocab_diag[idx_dominantes], proporcion_doc_freq[idx_dominantes]),
            key=lambda x: -x[1]
        )[:15]
    except ValueError:
        terminos_excluidos = []

    if k_fijo is not None:
        mejor_k = min(k_fijo, matriz.shape[0] - 1)
        _, historial_k = seleccionar_mejor_k(matriz, k_min=2, k_max=k_max_busqueda)
    else:
        mejor_k, historial_k = seleccionar_mejor_k(matriz, k_min=2, k_max=k_max_busqueda)

    km = KMeans(n_clusters=mejor_k, random_state=42, n_init=10)
    etiquetas_cluster = km.fit_predict(matriz)

    temas = extraer_terminos_por_cluster(vectorizer, matriz, etiquetas_cluster)
    pureza_prom, pureza_detalle = medir_pureza_idioma(etiquetas_cluster, idiomas)

    ruta_pca = f"pca_{etiqueta_run}.png"
    graficar_pca(matriz, etiquetas_cluster, etiqueta_run, ruta_pca)

    ruta_tsne = None
    if generar_tsne and len(documentos) >= 10:
        ruta_tsne = f"tsne_{etiqueta_run}.png"
        graficar_tsne(matriz, etiquetas_cluster, etiqueta_run, ruta_tsne)

    return {
        "num_documentos": len(documentos),
        "k_seleccionado": mejor_k,
        "historial_seleccion_k": historial_k,
        "terminos_dominantes_excluidos_max_df": [
            {"termino": t, "proporcion_documentos": round(float(p), 3)} for t, p in terminos_excluidos
        ],
        "pureza_idioma_promedio": round(pureza_prom, 3),
        "pureza_por_cluster": pureza_detalle,
        "temas_por_cluster": temas,
        "grafico_pca": ruta_pca,
        "grafico_tsne": ruta_tsne,
        "asignacion_cluster_por_articulo": [
            {"url": documentos[i].get("url"), "idioma": idiomas[i], "cluster": int(etiquetas_cluster[i])}
            for i in range(len(documentos))
        ],
    }


def main():
    print("SESION 6 - SIMILARIDAD Y EMBEDDINGS (TF-IDF + K-Means + PCA/t-SNE)")
    corpus = cargar_corpus()
    corpus = [d for d in corpus if d.get("lemas")]  # descarta articulos sin lemas
    print(f"Documentos disponibles (con lemas): {len(corpus)}")

    # ------------------------------------------------------------------
    # PASO 1: diagnostico sobre corpus COMBINADO (ES+EN)
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("PASO 1: Clustering sobre corpus COMBINADO (diagnostico)")
    print(f"{'='*70}")
    resultado_combinado = ejecutar_pipeline(corpus, "combinado", generar_tsne=True)
    print(f"k seleccionado: {resultado_combinado['k_seleccionado']}")
    print(f"Pureza de idioma promedio: {resultado_combinado['pureza_idioma_promedio']:.1%}")

    usar_combinado = resultado_combinado["pureza_idioma_promedio"] < UMBRAL_PUREZA_IDIOMA

    if usar_combinado:
        print(f"\n>> DECISION: pureza < {UMBRAL_PUREZA_IDIOMA:.0%} -> el combinado SI mezcla "
              f"idiomas dentro de los clusters, es una senal de que esta agrupando por TEMA "
              f"y no por idioma. Se usa como resultado final.")
    else:
        print(f"\n>> DECISION: pureza >= {UMBRAL_PUREZA_IDIOMA:.0%} -> el combinado esta "
              f"clusterizando por IDIOMA, no por tema (confirma la hipotesis inicial). "
              f"Se descarta el combinado como resultado final y se corre clustering "
              f"POR IDIOMA POR SEPARADO.")

    # ------------------------------------------------------------------
    # PASO 2: clustering por idioma por separado (siempre se corre, para
    # tener el resultado listo sin importar el diagnostico del paso 1)
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("PASO 2: Clustering POR IDIOMA POR SEPARADO")
    print(f"{'='*70}")

    resultados_por_idioma = {}
    for idioma in ["es", "en"]:
        docs_idioma = [d for d in corpus if d["idioma"] == idioma]
        if len(docs_idioma) < 5:
            print(f"  [{idioma}] Muy pocos documentos ({len(docs_idioma)}), se omite.")
            continue
        print(f"\n  Procesando idioma: {idioma} ({len(docs_idioma)} documentos)")
        resultado = ejecutar_pipeline(
            docs_idioma, idioma, generar_tsne=True,
            k_fijo=K_TEMAS_FINAL, k_max_busqueda=K_MAX_DIAGNOSTICO,
        )
        resultados_por_idioma[idioma] = resultado
        print(f"  k usado (fijo, alineado al entregable): {resultado['k_seleccionado']}")
        print(f"  Historial de busqueda libre (evidencia, no usado como final): "
              f"{resultado['historial_seleccion_k']}")
        if resultado["terminos_dominantes_excluidos_max_df"]:
            excluidos_str = ", ".join(
                f"{t['termino']}({t['proporcion_documentos']:.0%})"
                for t in resultado["terminos_dominantes_excluidos_max_df"][:8]
            )
            print(f"  Terminos ubicuos excluidos por max_df: {excluidos_str}")
        for cluster_id, terminos in resultado["temas_por_cluster"].items():
            top5 = ", ".join(t["termino"] for t in terminos[:5])
            n_docs_cluster = sum(1 for a in resultado["asignacion_cluster_por_articulo"] if a["cluster"] == cluster_id)
            print(f"    Cluster {cluster_id} ({n_docs_cluster} articulos): {top5}")

    # ------------------------------------------------------------------
    # Guardar resultado final
    # ------------------------------------------------------------------
    salida = {
        "metadata": {
            "proyecto": "FIFA WC2026 - Grupo 09_02",
            "sesion": "Sesion 6 - Similaridad y Embeddings",
            "metodologia": "TF-IDF (uni+bigrama) + K-Means + PCA/t-SNE para visualizacion.",
            "decision_k_final": {
                "k_usado_produccion": K_TEMAS_FINAL,
                "justificacion": "Se corrio primero busqueda libre de k (maximizando "
                                  "silhouette score, sin restriccion, hasta k=8). Esto "
                                  "produjo clusters que NO eran temas reales sino ruido "
                                  "editorial (creditos de imagen, etiquetas de navegacion "
                                  "del sitio como 'Preview'/'Reaction'), evidencia de "
                                  "sobre-fragmentacion. Se fijo k=3 para la corrida final, "
                                  "alineado al entregable pedido (3 temas principales), "
                                  "y se filtraron los terminos de boilerplate identificados.",
            },
            "boilerplate_filtrado": {k: sorted(v) for k, v in BOILERPLATE.items()},
            "decision_bilinguismo": {
                "diagnostico": "Se midio la pureza de idioma de los clusters del corpus "
                                "combinado ES+EN para detectar si el clustering separaba "
                                "por idioma en vez de por tema.",
                "pureza_idioma_combinado": resultado_combinado["pureza_idioma_promedio"],
                "umbral_usado": UMBRAL_PUREZA_IDIOMA,
                "resultado_final_recomendado": "por_idioma_separado" if not usar_combinado else "combinado",
            },
        },
        "clustering_combinado_diagnostico": resultado_combinado,
        "clustering_por_idioma": resultados_por_idioma,
    }

    with open(RUTA_SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"Guardado: {RUTA_SALIDA_JSON}")
    print(f"Graficos PNG generados en la carpeta actual (pca_*.png, tsne_*.png)")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()