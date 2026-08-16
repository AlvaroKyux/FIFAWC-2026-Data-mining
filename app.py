# -*- coding: utf-8 -*-
"""
app.py
--------
Sesion 14 - Dashboard y Visualizacion.

Dashboard Streamlit que consolida los hallazgos de las 5 semanas del
proyecto FIFA-WC-2026, Grupo 09_02. Corre 100% local (requiere el modelo
de embeddings de Hugging Face para el buscador semantico, misma
limitacion ya documentada desde Sesion 12).

Diseno de rutas (aprendido de los fallos del orquestador en Sesion 13):
este archivo debe vivir en la RAIZ del proyecto, junto a
pipeline_completo.py. No asume que los datos estan co-ubicados con el
script -- lee directamente de las rutas reales de Load/Transform
confirmadas contra el arbol de carpetas real del proyecto.

Uso:
    pip install -r requirements_dashboard.txt --break-system-packages
    python -m streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RAIZ = Path(__file__).resolve().parent

# ============================================================================
# RUTAS -- confirmadas contra el arbol real de carpetas (Sesion 13)
# ============================================================================
RUTA_CORPUS_RAW = RAIZ / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_raw.json"
RUTA_CORPUS_PRE = RAIZ / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_preprocesado.json"
RUTA_CLUSTERS = RAIZ / "ETL" / "CORPUS" / "ETL" / "Load" / "clusters_tematicos_embeddings.json"
RUTA_PRONOSTICOS = RAIZ / "ETL" / "CORPUS" / "ETL" / "Load" / "pronosticos_comparacion.csv"
RUTA_ANOMALIAS = RAIZ / "ETL" / "CORPUS" / "ETL" / "Load" / "anomalias_detectadas.csv"

RUTA_FACT_JUGADOR = RAIZ / "EXTRA" / "ETL" / "Extract" / "FACT_JUGADOR.csv"
RUTA_PREGUNTA1 = RAIZ / "EXTRA" / "ETL" / "Extract" / "pregunta1_datos.csv"
RUTA_PREGUNTA2 = RAIZ / "EXTRA" / "ETL" / "Extract" / "pregunta2_datos.csv"
RUTA_PREGUNTA3 = RAIZ / "EXTRA" / "ETL" / "Extract" / "pregunta3_datos.csv"
RUTA_CUBO_PIVOT = RAIZ / "EXTRA" / "ETL" / "Extract" / "cubo_pivot_liga_posicion.csv"
RUTA_RESULTADOS_2026 = RAIZ / "EXTRA" / "ETL" / "Extract" / "resultados_mundial2026.csv"


st.set_page_config(page_title="FIFA-WC-2026 · Grupo 09_02", layout="wide")


# ============================================================================
# CARGA DE DATOS (cacheada)
# ============================================================================

@st.cache_data
def cargar_json(ruta):
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_csv(ruta):
    if not ruta.exists():
        return None
    return pd.read_csv(ruta)


@st.cache_data
def cargar_corpus_raw():
    data = cargar_json(RUTA_CORPUS_RAW)
    if data is None:
        return None
    return data.get("corpus", []) if isinstance(data, dict) else data


@st.cache_data
def cargar_corpus_preprocesado():
    data = cargar_json(RUTA_CORPUS_PRE)
    if data is None:
        return None
    return data.get("corpus_preprocesado", []) if isinstance(data, dict) else data


@st.cache_data
def cargar_clustering():
    data = cargar_json(RUTA_CLUSTERS)
    if data is None:
        return None
    return data.get("clustering_combinado") if isinstance(data, dict) else None


def obtener_tokens_bm25(articulo):
    """El nombre exacto del campo lematizado no estaba confirmado al
    escribir esto, asi que se prueban varios candidatos antes de caer
    en texto_limpio.split() como respaldo seguro."""
    for campo in ("lemas", "lemmas", "texto_lematizado", "tokens"):
        val = articulo.get(campo)
        if val:
            if isinstance(val, list):
                return [str(x).lower() for x in val]
            return str(val).lower().split()
    return str(articulo.get("texto_limpio", "")).lower().split()


@st.cache_data
def construir_indice_bm25(_corpus_preprocesado):
    from rank_bm25 import BM25Okapi
    tokens_por_doc = [obtener_tokens_bm25(a) for a in _corpus_preprocesado]
    return BM25Okapi(tokens_por_doc)


@st.cache_resource
def cargar_modelo_embeddings():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def archivo_faltante(ruta, nombre):
    st.warning(
        f"No se encontro **{nombre}** en `{ruta}`. "
        f"Esta seccion se omite -- correr el script correspondiente primero."
    )


# ============================================================================
# TABS
# ============================================================================

st.title("FIFA-WC-2026 · Grupo 09_02")
st.caption("Escucha digital y analitica del Mundial 2026 mediante IA y Mineria de Datos")

tab1, tab2, tab3 = st.tabs([
    "📰 Mineria de Texto", "⚽ Rendimiento Real", "🧭 Metodologia BRAI"
])

# ----------------------------------------------------------------------------
# TAB 1 -- MINERIA DE TEXTO
# ----------------------------------------------------------------------------
with tab1:
    corpus_raw = cargar_corpus_raw()
    if not corpus_raw:
        archivo_faltante(RUTA_CORPUS_RAW, "corpus_mundial2026_raw.json")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Articulos totales", len(corpus_raw))
        n_es = sum(1 for a in corpus_raw if a.get("idioma") == "es")
        n_en = sum(1 for a in corpus_raw if a.get("idioma") == "en")
        col2.metric("Espanol", n_es)
        col3.metric("Ingles", n_en)

    st.divider()
    st.subheader("Clusters tematicos (Sesion 6)")
    cc = cargar_clustering()
    if cc is None:
        archivo_faltante(RUTA_CLUSTERS, "clusters_tematicos_embeddings.json (clustering_combinado)")
    else:
        asignaciones = cc.get("asignacion_cluster_por_articulo", [])
        conteo = pd.Series([a["cluster"] for a in asignaciones]).value_counts().sort_index()
        df_clusters = pd.DataFrame({"cluster": conteo.index.astype(str), "articulos": conteo.values})
        fig = px.bar(
            df_clusters, x="cluster", y="articulos",
            title=f"Articulos por cluster (k={cc.get('k_usado')}, "
                  f"pureza de idioma promedio={cc.get('pureza_idioma_promedio', 0):.2f})",
        )
        st.plotly_chart(fig, use_container_width=True)

        temas = cc.get("temas_por_cluster", {})
        if temas:
            st.markdown("**Terminos mas frecuentes por cluster**")
            cols_temas = st.columns(len(temas))
            for col, (cluster_id, terminos) in zip(cols_temas, sorted(temas.items())):
                with col:
                    st.markdown(f"Cluster {cluster_id}")
                    for t in terminos[:6]:
                        st.write(f"- {t['termino']} ({t['frecuencia']})")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Modelos de pronostico (Sesion 8)")
        df_pron = cargar_csv(RUTA_PRONOSTICOS)
        if df_pron is None:
            archivo_faltante(RUTA_PRONOSTICOS, "pronosticos_comparacion.csv")
        else:
            st.dataframe(df_pron, use_container_width=True)
    with col_b:
        st.subheader("Anomalias detectadas (Sesion 9)")
        df_anom = cargar_csv(RUTA_ANOMALIAS)
        if df_anom is None:
            archivo_faltante(RUTA_ANOMALIAS, "anomalias_detectadas.csv")
        else:
            st.dataframe(df_anom, use_container_width=True)

    st.divider()
    st.subheader("Buscador interactivo: BM25 vs Semantico (Sesion 11-12)")
    st.caption(
        "La primera busqueda tarda mas porque descarga/carga el modelo de "
        "embeddings (~1-2 min). Las siguientes son instantaneas gracias al cache."
    )
    corpus_pre = cargar_corpus_preprocesado()
    if not corpus_pre:
        archivo_faltante(RUTA_CORPUS_PRE, "corpus_mundial2026_preprocesado.json (corpus_preprocesado)")
    else:
        # El preprocesado no trae 'titulo' (solo url, idioma, fuente, texto_limpio),
        # asi que se arma un mapa url -> titulo a partir del corpus crudo, que si lo tiene.
        mapa_titulos = {a.get("url"): a.get("titulo", "(sin titulo)") for a in (corpus_raw or [])}

        consulta = st.text_input("Escribe una consulta (ej. 'controversia arbitral', 'España campeón')")
        if consulta:
            with st.spinner("Buscando..."):
                bm25 = construir_indice_bm25(corpus_pre)
                tokens = consulta.lower().split()
                scores_bm25 = bm25.get_scores(tokens)
                top5_bm25_idx = sorted(range(len(scores_bm25)), key=lambda i: -scores_bm25[i])[:5]

                modelo = cargar_modelo_embeddings()
                textos = [a.get("texto_limpio", "") for a in corpus_pre]
                emb_corpus = modelo.encode(textos)
                emb_consulta = modelo.encode([consulta])[0]
                import numpy as np
                sims = emb_corpus @ emb_consulta / (
                    np.linalg.norm(emb_corpus, axis=1) * np.linalg.norm(emb_consulta) + 1e-9
                )
                top5_sem_idx = sorted(range(len(sims)), key=lambda i: -sims[i])[:5]

            col_bm25, col_sem = st.columns(2)
            with col_bm25:
                st.markdown("**BM25 (lexico)**")
                for i in top5_bm25_idx:
                    titulo = mapa_titulos.get(corpus_pre[i].get("url"), "(sin titulo)")
                    st.write(f"- {titulo} (score={scores_bm25[i]:.2f})")
            with col_sem:
                st.markdown("**Semantico (embeddings)**")
                for i in top5_sem_idx:
                    titulo = mapa_titulos.get(corpus_pre[i].get("url"), "(sin titulo)")
                    st.write(f"- {titulo} (sim={sims[i]:.3f})")

# ----------------------------------------------------------------------------
# TAB 2 -- RENDIMIENTO REAL (cubo OLAP, Sesion 13)
# ----------------------------------------------------------------------------
with tab2:
    df_fact = cargar_csv(RUTA_FACT_JUGADOR)
    if df_fact is None:
        archivo_faltante(RUTA_FACT_JUGADOR, "FACT_JUGADOR.csv (correr cubo_olap_real.py primero)")
    else:
        st.subheader("Filtros (equivalente a Slice / Dice)")
        col_f1, col_f2, col_f3 = st.columns(3)
        selecciones = ["Todas"] + sorted(df_fact["seleccion"].dropna().unique().tolist())
        ligas = ["Todas"] + sorted(df_fact["liga"].dropna().unique().tolist())
        categorias = ["Todas"] + sorted(df_fact["categoria_posicion"].dropna().unique().tolist())

        f_seleccion = col_f1.selectbox("Seleccion", selecciones)
        f_liga = col_f2.selectbox("Liga", ligas)
        f_categoria = col_f3.selectbox("Categoria de posicion", categorias)

        df_filtrado = df_fact.copy()
        if f_seleccion != "Todas":
            df_filtrado = df_filtrado[df_filtrado["seleccion"] == f_seleccion]
        if f_liga != "Todas":
            df_filtrado = df_filtrado[df_filtrado["liga"] == f_liga]
        if f_categoria != "Todas":
            df_filtrado = df_filtrado[df_filtrado["categoria_posicion"] == f_categoria]

        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("Jugadores (filtro actual)", len(df_filtrado))
        col_k2.metric("Valor de mercado total", f"€{df_filtrado['valor_mercado_eur'].sum():,.0f}")
        col_k3.metric("Edad promedio", f"{df_filtrado['edad'].mean():.1f}" if len(df_filtrado) else "-")

        st.dataframe(
            df_filtrado[["nombre", "seleccion", "posicion", "club_actual", "liga", "valor_mercado_eur"]]
            .sort_values("valor_mercado_eur", ascending=False),
            use_container_width=True, height=300,
        )

        st.divider()
        col_roll, col_pivot = st.columns(2)
        with col_roll:
            st.subheader("Roll-up: valor de mercado por Grupo")
            df_grupo = df_fact.groupby("grupo", dropna=True)["valor_mercado_eur"].sum().reset_index()
            fig_grupo = px.bar(df_grupo.sort_values("grupo"), x="grupo", y="valor_mercado_eur")
            st.plotly_chart(fig_grupo, use_container_width=True)

        with col_pivot:
            st.subheader("Pivot: Liga x Categoria de posicion")
            df_pivot = cargar_csv(RUTA_CUBO_PIVOT)
            if df_pivot is not None:
                df_pivot_idx = df_pivot.set_index("liga")
                fig_heat = px.imshow(
                    df_pivot_idx, text_auto=True, aspect="auto",
                    labels=dict(x="Categoria", y="Liga", color="Jugadores"),
                )
                st.plotly_chart(fig_heat, use_container_width=True)

        st.divider()
        st.subheader("Pregunta 1: % en 5 grandes ligas vs Rendimiento")
        df_p1 = cargar_csv(RUTA_PREGUNTA1)
        if df_p1 is None:
            archivo_faltante(RUTA_PREGUNTA1, "pregunta1_datos.csv")
        else:
            r = df_p1["pct_5_grandes_ligas"].corr(df_p1["indice_rendimiento"])
            st.metric("Correlacion de Pearson", f"r = {r:.3f}")
            try:
                import statsmodels.api  # noqa: F401
                trendline = "ols"
            except ImportError:
                trendline = None
                st.caption(
                    "Instala `statsmodels` para ver la linea de tendencia "
                    "(`pip install statsmodels --break-system-packages`)."
                )
            fig_p1 = px.scatter(
                df_p1, x="pct_5_grandes_ligas", y="indice_rendimiento",
                hover_name="seleccion", trendline=trendline,
                labels={"pct_5_grandes_ligas": "% convocados en 5 grandes ligas",
                        "indice_rendimiento": "Indice de rendimiento"},
            )
            st.plotly_chart(fig_p1, use_container_width=True)

# ----------------------------------------------------------------------------
# TAB 3 -- METODOLOGIA BRAI
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Linea de tiempo de decisiones BRAI documentadas")
    decisiones = [
        ("Sesion 4", "GDELT rechazado", "Rate limiting persistente + 0 resultados en espanol, confirmado con multiples corridas."),
        ("Sesion 5", "spaCy _sm mantenido", "Errores de lematizacion conocidos aceptados como trade-off documentado, no corregidos silenciosamente."),
        ("Sesion 6", "TF-IDF rechazado para clustering", "Silhouette ~0 por snippets cortos con alto solapamiento lexico; embeddings semanticos lo resolvieron."),
        ("Sesion 8", "Modelos complejos rechazados", "Prophet y red neuronal (MLP) perdieron contra Moving Average simple (MAE 1.54 vs 3.14 y 7.77)."),
        ("Sesion 10", "FBref reconfirmado inaccesible", "robots.txt tambien devolvio 403, reforzando el bloqueo tecnico ya documentado en Sesion 2."),
        ("Sesion 11", "TF-IDF SI sirve para indexacion", "Se probo de nuevo en su propio contexto en vez de asumir que el fallo de clustering se repetiria; 8/10 acuerdo con BM25."),
        ("Sesion 13", "worldcup26.ir descartado para resultados 2026", "El repositorio cambio de alcance (ahora cubre Premier League/LaLiga de clubes); se uso openfootball/worldcup.json en su lugar, verificado con el resultado real de la final."),
        ("Sesion 13", "Bug de mapeo de clubes corregido", "20/88 clubes mal escritos a mano (faltaba 'FC', acentos); corregido con verificacion automatica, r cambio de 0.684 a 0.770."),
        ("Sesion 13", "Pipeline no reproducible (mayor problema tecnico)", "Rutas inconsistentes entre scripts de distintas sesiones + cuota de NewsAPI + bug de ruta en construir_indice.py; resuelto con un orquestador que copia insumos y valida salidas antes de promoverlas."),
    ]
    df_decisiones = pd.DataFrame(decisiones, columns=["Sesion", "Decision", "Evidencia"])
    st.dataframe(df_decisiones, use_container_width=True, height=380)

    st.divider()
    st.subheader("Cobertura de datos (limitaciones documentadas)")
    st.markdown("""
    - **Rendimiento en Mundial:** solo disponible para Qatar 2022 via StatsBomb
      (verificado el 15-ago-2026: el Mundial 2026 aun no tiene temporada
      publicada en el catalogo abierto).
    - **Pregunta 2/3:** usan la temporada de club **actual** (2025-26) como
      proxy de carga/rendimiento, no la temporada previa a Qatar 2022 --
      desfase de ~4 anios, documentado explicitamente en los scripts.
    - **leistungsdaten:** cobertura de 80.9% (1,010/1,248 jugadores) por
      fallos de extraccion ya documentados en la Fase 5.
    """)