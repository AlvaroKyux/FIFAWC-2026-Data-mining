# -*- coding: utf-8 -*-
"""
preprocesar_corpus.py
-----------------------
Sesion 5: Preprocesamiento de Texto.

Toma el corpus real construido en Sesion 4 (corpus_mundial2026_raw.json,
via NewsAPI, 330 articulos ES/EN) y aplica el pipeline de limpieza y
normalizacion para dejarlo listo para Sesion 6 (similaridad/embeddings).

DECISIONES METODOLOGICAS (documentar en el minireporte de Sesion 5):

1. spaCy en vez de NLTK.
   Justificacion: NLTK tiene tokenizacion y lematizacion mas debil para
   espanol (su stemmer Snowball no lematiza, solo recorta sufijos de forma
   agresiva). spaCy trae modelos entrenados especificos por idioma
   (es_core_news_sm, en_core_web_sm) con lematizacion real basada en
   diccionario + POS tagging, que es mas precisa para un corpus bilingue
   como el nuestro.

2. Lematizacion en vez de stemming.
   Justificacion: Sesion 6 usara TF-IDF/embeddings para clustering
   tematico. El stemming (ej. "jugadores" -> "jugador", pero tambien
   "jugando" -> "jug") puede fusionar palabras con significado distinto
   o dejar raices no-palabras, lo que degrada la calidad semantica de los
   vectores. La lematizacion conserva la forma canonica real de la
   palabra ("jugadores" -> "jugador", "jugando" -> "jugar"), preservando
   mejor el significado para el analisis de similaridad.

3. Filtrado de tokens.
   Se conservan solo tokens alfabeticos (se descartan numeros sueltos,
   puntuacion, simbolos), con longitud minima de 3 caracteres, que no
   sean stopwords (lista propia de spaCy por idioma, ampliada con
   terminos deportivos genericos de bajo valor tematico).

4. Limpieza previa a la tokenizacion.
   Se elimina el marcador de truncamiento propio de NewsAPI tier gratuito
   (ej. "... [+1234 chars]"), URLs sueltas, y se normalizan espacios.
   Esto es necesario porque ese marcador NO es texto real del articulo,
   es un artefacto de la API, y si no se limpia contamina el corpus con
   un patron falso muy frecuente.

Requiere (instalar UNA vez, en tu maquina local):
    pip install spacy --break-system-packages
    python -m spacy download es_core_news_sm
    python -m spacy download en_core_web_sm

Uso:
    python preprocesar_corpus.py
"""

import json
import re
import sys

try:
    import spacy
except ImportError:
    print("ERROR: falta spacy. Instala con:")
    print("  pip install spacy --break-system-packages")
    print("  python -m spacy download es_core_news_sm")
    print("  python -m spacy download en_core_web_sm")
    sys.exit(1)

RUTA_CORPUS_CRUDO = "corpus_mundial2026_raw.json"
RUTA_CORPUS_PREPROCESADO = "corpus_mundial2026_preprocesado.json"

# ---------------------------------------------------------------------
# Carga de modelos spaCy (uno por idioma). Se cargan sin componentes de
# NER/parser que no se necesitan para este paso, para que corra mas
# rapido sobre 330 articulos.
# ---------------------------------------------------------------------
def cargar_modelos():
    try:
        nlp_es = spacy.load("es_core_news_sm", disable=["ner", "parser"])
    except OSError:
        print("ERROR: falta el modelo es_core_news_sm. Instala con:")
        print("  python -m spacy download es_core_news_sm")
        sys.exit(1)
    try:
        nlp_en = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    except OSError:
        print("ERROR: falta el modelo en_core_web_sm. Instala con:")
        print("  python -m spacy download en_core_web_sm")
        sys.exit(1)
    return {"es": nlp_es, "en": nlp_en}


# Terminos deportivos genericos de bajo valor tematico para ESTE corpus
# especifico (aparecen en casi todos los articulos, no diferencian temas).
STOPWORDS_EXTRA = {
    "es": {"mundial", "copa", "fifa", "partido", "seleccion", "futbol",
           "equipo", "jugador", "gol", "minuto", "final"},
    "en": {"world", "cup", "fifa", "match", "team", "player", "goal",
           "minute", "final", "soccer", "football"},
}

PATRON_TRUNCAMIENTO_NEWSAPI = re.compile(r"\[\+\d+\s*chars\]")
PATRON_URL = re.compile(r"https?://\S+")
PATRON_ESPACIOS = re.compile(r"\s+")


def limpiar_texto_crudo(texto: str) -> str:
    """Limpieza previa a tokenizacion: quita artefactos de la API y URLs."""
    if not texto:
        return ""
    texto = PATRON_TRUNCAMIENTO_NEWSAPI.sub(" ", texto)
    texto = PATRON_URL.sub(" ", texto)
    texto = PATRON_ESPACIOS.sub(" ", texto).strip()
    return texto


def preprocesar_articulo(articulo: dict, modelos: dict) -> dict:
    idioma = articulo.get("idioma", "es")
    nlp = modelos.get(idioma, modelos["es"])
    stopwords_extra = STOPWORDS_EXTRA.get(idioma, set())

    partes = [
        articulo.get("titulo") or "",
        articulo.get("descripcion") or "",
        articulo.get("contenido_truncado") or "",
    ]
    texto_crudo = " ".join(p for p in partes if p)
    texto_limpio = limpiar_texto_crudo(texto_crudo)

    doc = nlp(texto_limpio)

    lemas = []
    for token in doc:
        if not token.is_alpha:
            continue
        if len(token.text) < 3:
            continue
        if token.is_stop:
            continue
        lema = token.lemma_.lower().strip()
        if not lema or lema in stopwords_extra:
            continue
        lemas.append(lema)

    return {
        "url": articulo.get("url"),
        "idioma": idioma,
        "fuente": articulo.get("fuente"),
        "fecha_publicacion": articulo.get("fecha_publicacion"),
        "texto_limpio": texto_limpio,
        "num_tokens_originales": len(doc),
        "num_lemas_finales": len(lemas),
        "lemas": lemas,
    }


def main():
    print("PREPROCESAMIENTO DE TEXTO - SESION 5")
    print("Cargando modelos spaCy (es_core_news_sm, en_core_web_sm)...")
    modelos = cargar_modelos()

    print(f"Cargando corpus crudo desde: {RUTA_CORPUS_CRUDO}")
    try:
        with open(RUTA_CORPUS_CRUDO, "r", encoding="utf-8") as f:
            data_cruda = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: no se encontro {RUTA_CORPUS_CRUDO} en esta carpeta.")
        print("Corre primero construir_corpus_mundial2026.py (Sesion 4).")
        sys.exit(1)

    corpus_crudo = data_cruda.get("corpus", [])
    print(f"Articulos a procesar: {len(corpus_crudo)}")

    corpus_preprocesado = []
    for i, articulo in enumerate(corpus_crudo, 1):
        resultado = preprocesar_articulo(articulo, modelos)
        corpus_preprocesado.append(resultado)
        if i % 50 == 0:
            print(f"  Procesados {i}/{len(corpus_crudo)}...")

    # ------------------------------------------------------------------
    # Validacion de calidad: muestreo manual antes/despues (Actividad
    # de Cierre de Sesion 5, segun el plan del profesor).
    # ------------------------------------------------------------------
    print(f"\n{'='*70}")
    print("MUESTREO DE VALIDACION (antes / despues) - 3 ejemplos")
    print(f"{'='*70}")
    for ejemplo in corpus_preprocesado[:3]:
        print(f"\n--- Fuente: {ejemplo['fuente']} ({ejemplo['idioma']}) ---")
        print(f"ANTES  : {ejemplo['texto_limpio'][:200]}...")
        print(f"DESPUES: {ejemplo['lemas'][:20]}")
        print(f"Tokens originales: {ejemplo['num_tokens_originales']} -> "
              f"Lemas finales: {ejemplo['num_lemas_finales']}")

    # ------------------------------------------------------------------
    # Estadisticas agregadas
    # ------------------------------------------------------------------
    total_lemas = sum(a["num_lemas_finales"] for a in corpus_preprocesado)
    por_idioma = {}
    for a in corpus_preprocesado:
        por_idioma[a["idioma"]] = por_idioma.get(a["idioma"], 0) + 1

    print(f"\n{'='*70}")
    print("RESUMEN DE PREPROCESAMIENTO")
    print(f"{'='*70}")
    print(f"Articulos procesados: {len(corpus_preprocesado)}")
    print(f"Distribucion por idioma: {por_idioma}")
    print(f"Total de lemas (tokens finales) en todo el corpus: {total_lemas}")
    print(f"Promedio de lemas por articulo: {total_lemas / len(corpus_preprocesado):.1f}")

    resultado_final = {
        "metadata": {
            "proyecto": "FIFA WC2026 - Grupo 09_02",
            "sesion": "Sesion 5 - Preprocesamiento de Texto",
            "pipeline": "spaCy (es_core_news_sm, en_core_web_sm): tokenizacion, "
                        "eliminacion de stopwords (spaCy + lista propia de terminos "
                        "deportivos genericos), lematizacion.",
            "justificacion_lematizacion_vs_stemming": (
                "Se prefirio lematizacion sobre stemming porque Sesion 6 usa "
                "TF-IDF/embeddings para clustering tematico, donde preservar la "
                "forma canonica real de la palabra da vectores semanticamente "
                "mas limpios que un recorte de sufijos."
            ),
            "total_articulos": len(corpus_preprocesado),
            "distribucion_por_idioma": por_idioma,
            "total_lemas": total_lemas,
        },
        "corpus_preprocesado": corpus_preprocesado,
    }

    with open(RUTA_CORPUS_PREPROCESADO, "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado en: {RUTA_CORPUS_PREPROCESADO}")


if __name__ == "__main__":
    main()