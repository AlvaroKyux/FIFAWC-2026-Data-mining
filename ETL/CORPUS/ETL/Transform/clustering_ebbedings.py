# -*- coding: utf-8 -*-
"""
clustering_embeddings.py
--------------------------
Sesion 6 (v2): Similaridad y Embeddings, con EMBEDDINGS SEMANTICOS en vez
de TF-IDF puro.

CONTEXTO DE LA DECISION (documentar en minireporte):
Se probo primero TF-IDF (clustering_tematico.py), con dos configuraciones
distintas de hiperparametros (max_df=0.9 y max_df=0.45 + sublinear_tf).
Ambas corridas sobre el corpus real (330 articulos) dieron silhouette
scores casi nulos (ES: ~0.007-0.011, EN: ~0.03-0.05), evidencia de que el
problema no era de ajuste fino sino estructural: TF-IDF depende de
solapamiento LEXICO EXACTO, y los snippets de NewsAPI (tier gratuito,
~200 caracteres de contenido) son demasiado cortos para que ese
solapamiento sea confiable entre articulos del mismo sub-tema.

Se escala a embeddings semanticos (sentence-transformers, modelo
multilingue 'paraphrase-multilingual-MiniLM-L12-v2') porque capturan
SIGNIFICADO en vez de coincidencia de palabras -- dos frases sobre
"pausas de hidratacion por calor" y "temperaturas extremas en los
partidos" quedan cerca en el espacio vectorial aunque compartan pocas
palabras exactas. Al ser multilingue, tambien permite volver a probar
si el corpus COMBINADO (ES+EN) puede clusterizar por tema real esta vez,
en vez de solo por idioma (con TF-IDF eso no era posible).

Requiere:
    pip install sentence-transformers scikit-learn matplotlib --break-system-packages

Uso:
    python clustering_embeddings.py

Nota: la primera corrida descarga el modelo (~470 MB) desde HuggingFace,
puede tardar unos minutos segun tu conexion. Corridas siguientes son
rapidas porque el modelo queda cacheado localmente.
"""

import json
import sys
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

RUTA_CORPUS_PREPROCESADO = "corpus_mundial2026_preprocesado.json"
RUTA_SALIDA_JSON = "clusters_tematicos_embeddings.json"

UMBRAL_PUREZA_IDIOMA = 0.85
K_TEMAS_FINAL = 3
K_MAX_DIAGNOSTICO = 8
NOMBRE_MODELO = "paraphrase-multilingual-MiniLM-L12-v2"

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
        sys.exit(1)
    return [d for d in data.get("corpus_preprocesado", []) if d.get("texto_limpio")]


def cargar_modelo_embeddings():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: falta sentence-transformers. Instala con:")
        print("  pip install sentence-transformers --break-system-packages")
        sys.exit(1)
    print(f"Cargando modelo de embeddings: {NOMBRE_MODELO} "
          f"(primera vez puede tardar varios minutos, se descarga ~470MB)...")
    return SentenceTransformer(NOMBRE_MODELO)


def seleccionar_mejor_k(embeddings, k_min=2, k_max=8):
    n_docs = embeddings.shape[0]
    k_max = min(k_max, n_docs - 1)
    if k_max < k_min:
        return k_min, []
    historial = []
    mejor_k, mejor_score = k_min, -1
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        etiquetas = km.fit_predict(embeddings)
        if len(set(etiquetas)) < 2:
            continue
        score = silhouette_score(embeddings, etiquetas)
        historial.append({"k": k, "silhouette": round(float(score), 4), "inercia": round(float(km.inertia_), 2)})
        if score > mejor_score:
            mejor_k, mejor_score = k, score
    return mejor_k, historial


def medir_pureza_idioma(etiquetas, idiomas):
    por_cluster = defaultdict(list)
    for etiqueta, idioma in zip(etiquetas, idiomas):
        por_cluster[etiqueta].append(idioma)
    purezas, detalle = [], {}
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


def extraer_terminos_representativos(documentos, etiquetas, n_terminos=8):
    """Como los embeddings no dan 'vocabulario' directo, se usan los lemas
    (ya limpios de Sesion 5) para nombrar cada cluster por frecuencia,
    excluyendo boilerplate y terminos ubicuos del corpus completo (doc freq > 45%)."""
    idioma_dominante = documentos[0]["idioma"] if len(set(d["idioma"] for d in documentos)) == 1 else "es"
    stop_bp = BOILERPLATE.get(idioma_dominante, set())

    doc_freq_global = Counter()
    for d in documentos:
        for termino in set(d["lemas"]):
            doc_freq_global[termino] += 1
    n_docs = len(documentos)
    terminos_ubicuos = {t for t, c in doc_freq_global.items() if c / n_docs > 0.45}

    temas = {}
    por_cluster_docs = defaultdict(list)
    for i, etiqueta in enumerate(etiquetas):
        por_cluster_docs[int(etiqueta)].append(i)

    for cluster_id, indices in por_cluster_docs.items():
        contador = Counter()
        for i in indices:
            for lema in documentos[i]["lemas"]:
                if lema in stop_bp or lema in terminos_ubicuos or len(lema) < 3:
                    continue
                contador[lema] += 1
        top = contador.most_common(n_terminos)
        temas[cluster_id] = [{"termino": t, "frecuencia": c} for t, c in top]

    return temas


def ejemplos_cercanos_al_centroide(embeddings, etiquetas, km, documentos, n_ejemplos=3):
    """Para cada cluster, los N articulos mas cercanos al centroide (contexto cualitativo)."""
    ejemplos = {}
    for cluster_id in sorted(set(etiquetas)):
        indices_cluster = np.where(etiquetas == cluster_id)[0]
        centroide = km.cluster_centers_[cluster_id]
        distancias = np.linalg.norm(embeddings[indices_cluster] - centroide, axis=1)
        orden = indices_cluster[np.argsort(distancias)][:n_ejemplos]
        ejemplos[int(cluster_id)] = [
            {"titulo": documentos[i].get("texto_limpio", "")[:120], "url": documentos[i].get("url")}
            for i in orden
        ]
    return ejemplos


def graficar(coords, etiquetas, titulo, metodo, ruta_salida):
    plt.figure(figsize=(8, 6))
    scatter = plt.scatter(coords[:, 0], coords[:, 1], c=etiquetas, cmap="tab10", alpha=0.7)
    plt.title(f"{metodo} - {titulo} (embeddings semanticos)")
    plt.legend(*scatter.legend_elements(), title="Cluster")
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=120)
    plt.close()


def ejecutar_pipeline(documentos, embeddings, etiqueta_run, k_fijo=None):
    mejor_k_libre, historial_k = seleccionar_mejor_k(embeddings, k_min=2, k_max=K_MAX_DIAGNOSTICO)
    k_final = k_fijo if k_fijo is not None else mejor_k_libre
    k_final = min(k_final, embeddings.shape[0] - 1)

    km = KMeans(n_clusters=k_final, random_state=42, n_init=10)
    etiquetas_cluster = km.fit_predict(embeddings)

    idiomas = [d["idioma"] for d in documentos]
    pureza_prom, pureza_detalle = medir_pureza_idioma(etiquetas_cluster, idiomas)

    temas = extraer_terminos_representativos(documentos, etiquetas_cluster)
    ejemplos = ejemplos_cercanos_al_centroide(embeddings, etiquetas_cluster, km, documentos)

    pca = PCA(n_components=2, random_state=42)
    coords_pca = pca.fit_transform(embeddings)
    graficar(coords_pca, etiquetas_cluster, etiqueta_run, "PCA", f"pca_emb_{etiqueta_run}.png")

    if len(documentos) >= 10:
        perplexity = min(30, max(5, len(documentos) // 4))
        tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity, init="pca")
        coords_tsne = tsne.fit_transform(embeddings)
        graficar(coords_tsne, etiquetas_cluster, etiqueta_run, "t-SNE", f"tsne_emb_{etiqueta_run}.png")

    return {
        "num_documentos": len(documentos),
        "k_usado": k_final,
        "historial_seleccion_k_libre": historial_k,
        "pureza_idioma_promedio": round(pureza_prom, 3),
        "pureza_por_cluster": pureza_detalle,
        "temas_por_cluster": temas,
        "ejemplos_por_cluster": ejemplos,
        "asignacion_cluster_por_articulo": [
            {"url": documentos[i].get("url"), "idioma": idiomas[i], "cluster": int(etiquetas_cluster[i])}
            for i in range(len(documentos))
        ],
    }


def main():
    print("SESION 6 v2 - EMBEDDINGS SEMANTICOS (sentence-transformers) + K-Means + PCA/t-SNE")
    corpus = cargar_corpus()
    print(f"Documentos disponibles: {len(corpus)}")

    modelo = cargar_modelo_embeddings()
    textos = [d["texto_limpio"] for d in corpus]
    print("Generando embeddings (esto puede tardar 1-2 minutos)...")
    embeddings = modelo.encode(textos, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings)

    print(f"\n{'='*70}")
    print("PASO 1: Clustering COMBINADO (ES+EN) con embeddings multilingues")
    print(f"{'='*70}")
    resultado_combinado = ejecutar_pipeline(corpus, embeddings, "combinado", k_fijo=K_TEMAS_FINAL)
    print(f"Pureza de idioma promedio: {resultado_combinado['pureza_idioma_promedio']:.1%}")
    print(f"Historial silhouette libre: {resultado_combinado['historial_seleccion_k_libre']}")

    usar_combinado = resultado_combinado["pureza_idioma_promedio"] < UMBRAL_PUREZA_IDIOMA
    if usar_combinado:
        print(f"\n>> Pureza < {UMBRAL_PUREZA_IDIOMA:.0%}: los embeddings multilingues SI logran "
              f"agrupar por TEMA cruzando idiomas. Se usa el combinado como resultado final.")
        for cid, terminos in resultado_combinado["temas_por_cluster"].items():
            top = ", ".join(t["termino"] for t in terminos[:6])
            print(f"  Cluster {cid}: {top}")
    else:
        print(f"\n>> Pureza >= {UMBRAL_PUREZA_IDIOMA:.0%}: incluso con embeddings semanticos, "
              f"persiste separacion por idioma. Se mantiene el enfoque por idioma separado.")

    resultados_por_idioma = {}
    print(f"\n{'='*70}")
    print("PASO 2: Clustering por idioma por separado (respaldo/comparacion)")
    print(f"{'='*70}")
    for idioma in ["es", "en"]:
        indices_idioma = [i for i, d in enumerate(corpus) if d["idioma"] == idioma]
        if len(indices_idioma) < 5:
            continue
        docs_idioma = [corpus[i] for i in indices_idioma]
        emb_idioma = embeddings[indices_idioma]
        print(f"\n  Idioma: {idioma} ({len(docs_idioma)} documentos)")
        resultado = ejecutar_pipeline(docs_idioma, emb_idioma, idioma, k_fijo=K_TEMAS_FINAL)
        resultados_por_idioma[idioma] = resultado
        for cid, terminos in resultado["temas_por_cluster"].items():
            top = ", ".join(t["termino"] for t in terminos[:6])
            n_docs_cluster = sum(1 for a in resultado["asignacion_cluster_por_articulo"] if a["cluster"] == cid)
            print(f"    Cluster {cid} ({n_docs_cluster} articulos): {top}")

    salida = {
        "metadata": {
            "proyecto": "FIFA WC2026 - Grupo 09_02",
            "sesion": "Sesion 6 v2 - Similaridad y Embeddings (semanticos)",
            "modelo_embeddings": NOMBRE_MODELO,
            "decision": "Se escalo de TF-IDF a embeddings semanticos multilingues tras "
                        "evidencia de silhouette casi nulo (~0.01-0.05) en dos configuraciones "
                        "distintas de TF-IDF, diagnosticado como limitacion estructural de "
                        "solapamiento lexico con snippets cortos (~200 caracteres, tier "
                        "gratuito de NewsAPI).",
            "usar_combinado_final": usar_combinado,
        },
        "clustering_combinado": resultado_combinado,
        "clustering_por_idioma": resultados_por_idioma,
    }

    with open(RUTA_SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {RUTA_SALIDA_JSON}")


if __name__ == "__main__":
    main()