# -*- coding: utf-8 -*-
"""
pipeline_completo.py
-----------------------
Sesion 13 - Integracion Final (Semana 5).

Orquestador unico del proyecto FIFA-WC-2026, Grupo 09_02. Este es el
"Producto 1: Sistema funcional" -- une los dos pipelines independientes
construidos a lo largo del curso (mineria de texto y datos estructurados
de jugadores/equipos) en un solo sistema ejecutable, en vez de 15 scripts
sueltos que solo tienen sentido si uno sabe el orden correcto.

COMO USAR ESTE SCRIPT:
  1. Ajusta la seccion CONFIGURACION de abajo con las rutas REALES de tu
     proyecto (las de aqui son mi mejor estimado a partir del historial
     de sesiones, pero varios scripts los renombraste despues de
     recibirlos, asi que hay que confirmarlas).
  2. Corre primero con --preflight (o sin argumentos, lo hace por
     defecto) para verificar que todo existe ANTES de ejecutar nada.
  3. Corre con --run para ejecutar la cadena completa.
  4. Corre con --run --solo NOMBRE_ETAPA para ejecutar una sola etapa.

DECISION DE DISENO (documentada, no un descuido): varias etapas de este
pipeline NO pueden correr en un entorno sin acceso de red completo
(descarga del modelo de embeddings desde Hugging Face, verificacion de
robots.txt) -- esto ya fue documentado como hallazgo BRAI en Sesiones
10 y 12, no es una limitacion nueva de este orquestador. Esas etapas se
marcan explicitamente como "requiere_red_completa" y el script las
señala en vez de fingir que corren igual que las demas.

Uso:
    python pipeline_completo.py --preflight
    python pipeline_completo.py --run
    python pipeline_completo.py --run --solo corpus
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

CARPETA_SCRIPT = Path(__file__).resolve().parent

# ============================================================================
# CONFIGURACION -- AJUSTAR ESTAS RUTAS A TU ESTRUCTURA REAL ANTES DE CORRER
# ============================================================================
# Cada etapa define:
#   script:            ruta al .py, relativa a la carpeta de este orquestador
#                       (o ruta absoluta si prefieres ser explicito)
#   entradas:           archivos que DEBEN existir antes de correr la etapa
#   salidas:            archivos que la etapa debe producir al terminar
#   requiere_red_completa: True si el script necesita acceso a internet sin
#                       restricciones (Hugging Face, verificacion en vivo de
#                       robots.txt) -- ya documentado en Sesiones 10 y 12
#   opcional:           True si el pipeline puede seguir aunque esta etapa
#                       falle o no este disponible (ej. graficas)

RAIZ_PROYECTO = CARPETA_SCRIPT  # ajustar si este script no vive en la raiz

# Rutas corregidas el 15-ago-2026 contra el listado real de carpetas
# (tu estructura usa ETL\<SECCION>\ETL\<Extract|Transform|Load>\, con la
# carpeta ETL duplicada dentro de cada seccion -- no es un error mio, es
# como quedo armado el proyecto realmente).
ETAPAS = [
    {
        "nombre": "corpus",
        "descripcion": "Sesion 4 - Construccion del corpus (NewsAPI)",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Extract" / "corpus_FIFA_WC.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Extract" / "newsapi_key.txt"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_raw.json"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "preprocesamiento",
        "descripcion": "Sesion 5 - Preprocesamiento y lematizacion (spaCy)",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Transform" / "preprocesar_corpus.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_raw.json"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_preprocesado.json"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "clustering",
        "descripcion": "Sesion 6 - Clustering tematico (embeddings)",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Transform" / "temas_cluster.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_preprocesado.json"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "clusters_tematicos_embeddings.json"],
        "requiere_red_completa": True,  # descarga del modelo la primera vez
        "opcional": False,
    },
    {
        # OJO: construir_series_temporales.py y series_diarias.csv NO
        # aparecen en el listado real de carpetas que me compartiste.
        # Dejo esta ruta como mejor estimado (mismo patron que el resto
        # de CORPUS), pero es MUY probable que este mal -- confirmalo,
        # o dime donde quedo realmente ese script de Sesion 7.
        "nombre": "series_temporales",
        "descripcion": "Sesion 7 - Series temporales diarias (RUTA SIN CONFIRMAR)",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Transform" / "construir_series_temporales.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "corpus_mundial2026_raw.json"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "series_diarias.csv"],
        "requiere_red_completa": False,
        "opcional": True,  # opcional hasta confirmar la ruta real
    },
    {
        "nombre": "pronostico",
        "descripcion": "Sesion 8 - Modelos de pronostico",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Transform" / "pronostico_modelos.py",
        "entradas": [],  # no se pudo confirmar su entrada real (ver nota de series_temporales)
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "pronosticos_comparacion.csv"],
        "requiere_red_completa": False,
        "opcional": True,
    },
    {
        "nombre": "anomalias",
        "descripcion": "Sesion 9 - Deteccion de anomalias",
        "script": RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Transform" / "deteccion_anomalias.py",
        "entradas": [],
        "salidas": [RAIZ_PROYECTO / "ETL" / "CORPUS" / "ETL" / "Load" / "anomalias_detectadas.csv"],
        "requiere_red_completa": False,
        "opcional": True,
    },
    {
        "nombre": "robots_txt",
        "descripcion": "Sesion 10 - Auditoria etica de scraping (robots.txt)",
        "script": RAIZ_PROYECTO / "ETL" / "WEBMINING" / "ETL" / "Transform" / "verificar_robots.py",
        "entradas": [],
        "salidas": [
            RAIZ_PROYECTO / "ETL" / "WEBMINING" / "ETL" / "Load" / "robots_transfermarkt.txt",
            RAIZ_PROYECTO / "ETL" / "WEBMINING" / "ETL" / "Load" / "robots_worldcup26_ir.txt",
        ],
        "requiere_red_completa": True,
        "opcional": True,
    },
    {
        "nombre": "indexacion",
        "descripcion": "Sesion 11 - Indice invertido (TF-IDF vs BM25)",
        "script": RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "construir_indice.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "corpus_mundial2026_preprocesado.json"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Load" / "indice_invertido.json"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "buscador",
        "descripcion": "Sesion 12 - Buscador BM25 vs semantico",
        "script": RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "buscador_ir.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "corpus_mundial2026_preprocesado.json"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "resultados_busqueda_comparados.csv"],
        "requiere_red_completa": True,  # descarga del modelo de embeddings
        "opcional": False,
    },
    {
        "nombre": "precision_busqueda",
        "descripcion": "Sesion 12 - Precision@5 (requiere juicio de relevancia ya llenado)",
        "script": RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "calcular_precision.py",
        "entradas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Transform" / "resultados_busqueda_comparados.csv"],
        "salidas": [RAIZ_PROYECTO / "ETL" / "Indexing" / "ETL" / "Load" / "precision_FINAL.csv"],
        "requiere_red_completa": False,
        "opcional": True,
    },
    {
        "nombre": "resultados_2026",
        "descripcion": "Sesion 13 - Captura de resultados reales del Mundial 2026",
        "script": RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "capturar_resultados_mundial2026.py",
        "entradas": [RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "equipos_limpio.csv"],
        "salidas": [RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "resultados_mundial2026.csv"],
        "requiere_red_completa": False,  # solo necesita raw.githubusercontent.com
        "opcional": False,
    },
    {
        "nombre": "pregunta1",
        "descripcion": "Sesion 13 - Pregunta 1 (5 grandes ligas vs rendimiento)",
        "script": RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta1_correlacion.py",
        "entradas": [
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "jugadores_mundial_limpio.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "resultados_mundial2026.csv",
        ],
        "salidas": [RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta1_datos.csv"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "pregunta2",
        "descripcion": "Sesion 13 - Pregunta 2 (carga de partidos vs rendimiento)",
        "script": RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta2_carga_rendimiento.py",
        "entradas": [
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "leistungsdaten_parcial_limpio.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "statsbomb_rendimiento_jugador_partido.csv",
        ],
        "salidas": [RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta2_datos.csv"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "pregunta3",
        "descripcion": "Sesion 13 - Pregunta 3 (rendimiento club vs Mundial)",
        "script": RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta3_rendimiento_club_vs_mundial.py",
        "entradas": [
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "leistungsdaten_parcial_limpio.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "statsbomb_rendimiento_jugador_partido.csv",
        ],
        "salidas": [RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta3_datos.csv"],
        "requiere_red_completa": False,
        "opcional": False,
    },
    {
        "nombre": "cubo_olap",
        "descripcion": "Sesion 13 - Cubo OLAP real (5 operaciones)",
        "script": RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "cubo_olap_real.py",
        "entradas": [
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "resultados_mundial2026.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "pregunta1_datos.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "jugadores_mundial_limpio.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "leistungsdaten_parcial_limpio.csv",
        ],
        "salidas": [
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "FACT_JUGADOR.csv",
            RAIZ_PROYECTO / "EXTRA" / "ETL" / "Extract" / "cubo_pivot_liga_posicion.csv",
        ],
        "requiere_red_completa": False,
        "opcional": False,
    },
]

PYTHON_EXE = sys.executable  # usa el mismo interprete con el que se corre este orquestador


# ============================================================================
# LOGICA DEL ORQUESTADOR (no deberia necesitar cambios)
# ============================================================================

def preflight():
    """Verifica que cada script exista y que las entradas de cada etapa
    esten disponibles ANTES de ejecutar nada. No corre ningun script."""
    print("=" * 78)
    print("PREFLIGHT: verificando que todo exista antes de correr el pipeline")
    print("=" * 78)
    todo_ok = True
    for etapa in ETAPAS:
        problemas = []
        if not etapa["script"].exists():
            problemas.append(f"NO EXISTE el script: {etapa['script']}")
        for entrada in etapa["entradas"]:
            if not entrada.exists():
                problemas.append(f"falta entrada requerida: {entrada}")

        estado = "OK" if not problemas else "FALTA CONFIGURAR"
        marca_red = " [requiere red completa]" if etapa["requiere_red_completa"] else ""
        marca_opc = " [opcional]" if etapa["opcional"] else ""
        print(f"\n[{estado}] {etapa['nombre']} - {etapa['descripcion']}{marca_red}{marca_opc}")
        for p in problemas:
            print(f"    -> {p}")
            if not etapa["opcional"]:
                todo_ok = False

    print()
    print("=" * 78)
    if todo_ok:
        print("Preflight OK: todas las rutas obligatorias existen. Listo para --run.")
    else:
        print("Preflight con problemas: ajusta las rutas en la seccion CONFIGURACION")
        print("de este mismo archivo (o mueve/renombra tus scripts) antes de --run.")
        print("Las etapas marcadas [opcional] no bloquean el pipeline si faltan.")
    print("=" * 78)
    return todo_ok


def validar_corpus_no_vacio(ruta_json):
    """Evita el peor escenario posible: que un corpus vacio (por rate
    limit de NewsAPI u otro fallo silencioso) sobrescriba el corpus real
    de 330 articulos ya validado en Sesion 4. Si el archivo recien
    generado tiene 0 articulos, se rechaza la promocion."""
    import json
    try:
        with open(ruta_json, encoding="utf-8") as f:
            data = json.load(f)
        n = len(data) if isinstance(data, list) else len(data.get("articulos", data))
        return n > 0, n
    except Exception as e:
        return False, f"error leyendo el archivo: {e}"


# Validadores especificos por etapa: si una etapa tiene un validador y
# no pasa, la salida NO se promueve a su ubicacion canonica (para no
# pisar un resultado bueno con uno vacio o corrupto).
VALIDADORES = {
    "corpus": validar_corpus_no_vacio,
}

# Copias extra de insumos que algunos scripts necesitan por bugs de ruta
# conocidos (documentados, no corregidos en el script original para no
# tocar el trabajo ya entregado). Formato: nombre_etapa -> lista de
# carpetas adicionales donde tambien copiar cada entrada.
COPIAS_EXTRA_ENTRADAS = {
    # construir_indice.py busca el corpus preprocesado un nivel arriba
    # de su propia carpeta (bug real, "..\corpus_mundial2026_preprocesado.json"
    # en vez de la ruta directa). Se deja una copia extra ahi tambien.
    "indexacion": [lambda etapa: etapa["script"].parent.parent],
}


def preparar_entradas(etapa):
    """La mayoria de los scripts de este proyecto asumen que sus archivos
    de entrada estan FISICAMENTE junto a ellos (mismo patron que ya
    conoces de sesiones anteriores: 'corpus file not found errors
    required placing files alongside scripts'). En vez de asumir que
    cada script sabe navegar a Load/Transform, este orquestador copia
    las entradas configuradas a la carpeta del script antes de correrlo."""
    carpeta_destino = etapa["script"].parent
    for entrada in etapa["entradas"]:
        if not entrada.exists():
            continue
        destino = carpeta_destino / entrada.name
        if destino.resolve() != entrada.resolve():
            import shutil
            shutil.copy2(entrada, destino)
            print(f"  [copiado] {entrada.name} -> {carpeta_destino}")

    for carpeta_fn in COPIAS_EXTRA_ENTRADAS.get(etapa["nombre"], []):
        carpeta_extra = carpeta_fn(etapa)
        for entrada in etapa["entradas"]:
            if not entrada.exists():
                continue
            destino = carpeta_extra / entrada.name
            if destino.resolve() != entrada.resolve():
                import shutil
                shutil.copy2(entrada, destino)
                print(f"  [copiado - workaround de ruta] {entrada.name} -> {carpeta_extra}")


def promover_salidas(etapa):
    """Despues de correr un script, busca sus salidas EN LA CARPETA DEL
    SCRIPT (donde realmente las escribe, segun el mismo patron de
    co-ubicacion) y las copia a la ruta canonica configurada en
    ETAPAS, para que la siguiente etapa las encuentre ahi. Si la etapa
    tiene un validador y el archivo no lo pasa, NO se promueve -- se
    reporta como fallo en vez de arriesgar sobrescribir un resultado
    bueno con uno vacio o corrupto."""
    import shutil
    carpeta_script = etapa["script"].parent
    validador = VALIDADORES.get(etapa["nombre"])

    for salida_canonica in etapa["salidas"]:
        candidato = carpeta_script / salida_canonica.name
        if not candidato.exists():
            continue  # puede que el script ya haya escrito directo en la ruta canonica

        if validador:
            ok, detalle = validador(candidato)
            if not ok:
                print(f"  [BLOQUEADO] {candidato.name} no paso la validacion ({detalle}).")
                print(f"    NO se sobrescribe {salida_canonica} -- se conserva el archivo existente.")
                return False

        if candidato.resolve() != salida_canonica.resolve():
            salida_canonica.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidato, salida_canonica)
            print(f"  [promovido] {candidato.name} -> {salida_canonica}")
    return True


def ejecutar_etapa(etapa):
    print("\n" + "=" * 78)
    print(f"ETAPA: {etapa['nombre']} - {etapa['descripcion']}")
    print("=" * 78)

    if not etapa["script"].exists():
        print(f"  SALTADA: no se encontro el script {etapa['script']}")
        return "saltada"

    if etapa["requiere_red_completa"]:
        print("  Nota: esta etapa requiere acceso de red sin restricciones")
        print("  (documentado desde Sesiones 10/12). Si falla por conexion,")
        print("  no es un error del pipeline, es la limitacion ya conocida.")

    preparar_entradas(etapa)

    inicio = time.time()
    resultado = subprocess.run(
        [PYTHON_EXE, str(etapa["script"])],
        cwd=str(etapa["script"].parent),
        capture_output=True,
        text=True,
    )
    duracion = time.time() - inicio

    print(resultado.stdout)
    if resultado.stderr:
        print("--- STDERR ---")
        print(resultado.stderr)

    if resultado.returncode != 0:
        print(f"  FALLO (codigo {resultado.returncode}) en {duracion:.1f}s")
        return "fallo" if not etapa["opcional"] else "fallo_opcional"

    promovido_ok = promover_salidas(etapa)
    if not promovido_ok:
        return "fallo" if not etapa["opcional"] else "fallo_opcional"

    faltantes = [s for s in etapa["salidas"] if not s.exists()]
    if faltantes:
        print(f"  ADVERTENCIA: el script corrio sin error pero no genero:")
        for f in faltantes:
            print(f"    - {f}")
        return "salidas_incompletas"

    print(f"  OK ({duracion:.1f}s)")
    return "ok"


def run(solo=None):
    etapas_a_correr = [e for e in ETAPAS if solo is None or e["nombre"] == solo]
    if solo and not etapas_a_correr:
        print(f"No existe una etapa llamada '{solo}'. Etapas disponibles:")
        for e in ETAPAS:
            print(f"  - {e['nombre']}")
        return

    resumen = {}
    inicio_total = time.time()
    for etapa in etapas_a_correr:
        resumen[etapa["nombre"]] = ejecutar_etapa(etapa)
    duracion_total = time.time() - inicio_total

    print("\n" + "=" * 78)
    print(f"RESUMEN DEL PIPELINE ({duracion_total:.1f}s total)")
    print("=" * 78)
    for nombre, estado in resumen.items():
        print(f"  {nombre:<20} {estado}")

    fallidas = [n for n, e in resumen.items() if e == "fallo"]
    if fallidas:
        print(f"\n{len(fallidas)} etapa(s) obligatoria(s) fallaron: {fallidas}")
        print("Revisa el detalle arriba antes de considerar el sistema funcional.")
    else:
        print("\nTodas las etapas obligatorias corrieron sin error.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestador del pipeline FIFA-WC-2026")
    parser.add_argument("--preflight", action="store_true", help="Solo verificar, no ejecutar")
    parser.add_argument("--run", action="store_true", help="Ejecutar el pipeline")
    parser.add_argument("--solo", type=str, default=None, help="Ejecutar solo esta etapa")
    args = parser.parse_args()

    if args.run:
        ok = preflight()
        if not ok and args.solo is None:
            print("\nHay problemas de configuracion. Corrigelos o usa --solo para")
            print("ejecutar una etapa especifica que si este lista.")
        else:
            run(solo=args.solo)
    else:
        preflight()