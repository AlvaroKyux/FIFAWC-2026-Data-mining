"""
Proyecto: Data Mining - FIFA WC2026
Entregable 3 - Limpieza y Transformación
Fuente: Transfermarkt — Consolidación de estadísticas de carrera (leistungsdaten)

CONTEXTO: el proceso de extracción (05_extraer_leistungsdaten_selenium.py)
se detuvo deliberadamente tras procesar aproximadamente 991 de 1,248
jugadores (~79%), dado el tiempo extenso del proceso (varias horas con
Selenium). Esto se documenta como limitación reconocida en el Producto 2.
Gracias al diseño reanudable del extractor (un archivo JSON por jugador),
todo lo ya extraído está disponible y se consolida aquí sin pérdida.

Este script:
1. Lee TODOS los archivos JSON disponibles en raw/transfermarkt_leistungsdaten/.
2. Aplana la estructura anidada (jugador -> competiciones) a una tabla plana.
3. Limpia los valores: convierte texto a número, maneja "-" como ausencia
   real (no como dato faltante por error), convierte minutos "2,835'" a
   entero.
4. Cruza con el dataset de jugadores (Fase 3) para incorporar la posición,
   selección y club — necesario porque el significado de algunas columnas
   varía según la posición (ej. en un portero, "goles" en realidad
   corresponde a goles concedidos, no anotados).
5. Diagnostica cobertura: cuántos jugadores del total de 1,248 quedaron
   con datos, y cuántos no.
6. Guarda el dataset final limpio.
"""

import json
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path("raw/transfermarkt_leistungsdaten")
RUTA_JUGADORES = Path("clean/jugadores_mundial_limpio.csv")  # de la Fase 3
CLEAN_DIR = Path("clean")
CLEAN_DIR.mkdir(exist_ok=True)


def cargar_estadisticas_crudas() -> list[dict]:
    """Lee todos los JSON de estadísticas de carrera ya extraídos."""
    archivos = list(RAW_DIR.glob("*.json"))
    resultados = []
    for archivo in archivos:
        player_id = archivo.stem  # nombre del archivo sin extensión
        with open(archivo, encoding="utf-8") as f:
            data = json.load(f)
        data["player_id"] = player_id
        resultados.append(data)
    return resultados


def aplanar_a_tabla(estadisticas: list[dict]) -> pd.DataFrame:
    """Convierte la estructura anidada (jugador -> competiciones) a tabla plana."""
    filas = []
    for jugador in estadisticas:
        if not jugador["competiciones"]:
            # Jugador sin competiciones extraídas (fallo o timeout durante
            # la extracción). Se registra explícitamente como fila vacía
            # para que quede contabilizado en el diagnóstico de cobertura,
            # en vez de simplemente desaparecer del dataset sin dejar rastro.
            filas.append({
                "player_id": jugador["player_id"],
                "nombre": jugador["nombre"],
                "competicion_raw": None,
                "partidos_raw": None,
                "goles_raw": None,
                "asistencias_raw": None,
                "amarillas_raw": None,
                "rojas_raw": None,
                "minutos_raw": None,
                "extraccion_exitosa": False,
            })
            continue

        for comp in jugador["competiciones"]:
            filas.append({
                "player_id": jugador["player_id"],
                "nombre": jugador["nombre"],
                "competicion_raw": comp.get("competicion_raw"),
                "partidos_raw": comp.get("partidos"),
                "goles_raw": comp.get("goles"),
                "asistencias_raw": comp.get("asistencias"),
                "amarillas_raw": comp.get("amarillas"),
                "rojas_raw": comp.get("rojas"),
                "minutos_raw": comp.get("minutos_raw"),
                "extraccion_exitosa": True,
            })

    return pd.DataFrame(filas)


def limpiar_valor_numerico(valor) -> float | None:
    """
    Convierte valores de Transfermarkt a número real.
    '-' significa "no aplica / cero" (ej. un portero sin asistencias,
    o una competición en la que el jugador no participó) -> se convierte
    a 0, no a NaN, porque es un cero genuino, no un dato faltante.
    """
    if valor is None:
        return None
    if isinstance(valor, str):
        valor = valor.strip()
        if valor == "-" or valor == "":
            return 0.0
        valor_limpio = valor.replace(",", "").replace("'", "")
        try:
            return float(valor_limpio)
        except ValueError:
            return None
    return float(valor)


def limpiar_tabla(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica limpieza de tipos a toda la tabla."""
    df_limpio = df.copy()

    for columna_raw, columna_limpia in [
        ("partidos_raw", "partidos"),
        ("goles_raw", "goles"),
        ("asistencias_raw", "asistencias"),
        ("amarillas_raw", "amarillas"),
        ("rojas_raw", "rojas"),
        ("minutos_raw", "minutos"),
    ]:
        df_limpio[columna_limpia] = df_limpio[columna_raw].apply(limpiar_valor_numerico)

    # Bandera explícita para filas de TOTAL, útiles para evitar doble
    # conteo si en el análisis posterior se suman partidos por jugador
    df_limpio["es_total"] = df_limpio["competicion_raw"] == "TOTAL"

    columnas_finales = [
        "player_id", "nombre", "competicion_raw", "es_total",
        "partidos", "goles", "asistencias", "amarillas", "rojas",
        "minutos", "extraccion_exitosa",
    ]
    return df_limpio[columnas_finales]


def cruzar_con_jugadores(df_stats: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza con el dataset de jugadores de la Fase 3 para incorporar
    posición, selección y club. Necesario porque el significado de
    'goles'/'asistencias' varía según si el jugador es portero o no.
    """
    if not RUTA_JUGADORES.exists():
        print(f"⚠️ No se encontró {RUTA_JUGADORES}. Se omite el cruce con")
        print("   posición/selección. Verifica la ruta antes de usar el")
        print("   dataset final para análisis por posición.")
        return df_stats

    jugadores = pd.read_csv(RUTA_JUGADORES)
    jugadores["player_id"] = jugadores["player_id"].astype(str)
    df_stats["player_id"] = df_stats["player_id"].astype(str)

    return df_stats.merge(
        jugadores[["player_id", "seleccion", "posicion", "club_actual"]],
        on="player_id",
        how="left",
    )


def diagnosticar_cobertura(df_final: pd.DataFrame) -> dict:
    """Diagnóstico de cobertura: cuántos de los 1,248 jugadores tienen datos."""
    total_jugadores_objetivo = 1248
    if RUTA_JUGADORES.exists():
        total_jugadores_objetivo = len(pd.read_csv(RUTA_JUGADORES))

    jugadores_con_datos = df_final[df_final["extraccion_exitosa"]]["player_id"].nunique()
    jugadores_sin_datos = df_final[~df_final["extraccion_exitosa"]]["player_id"].nunique()
    jugadores_procesados_total = df_final["player_id"].nunique()

    return {
        "total_jugadores_objetivo_(1248)": total_jugadores_objetivo,
        "jugadores_procesados_en_esta_corrida": jugadores_procesados_total,
        "jugadores_con_datos_extraidos_exitosamente": jugadores_con_datos,
        "jugadores_sin_datos_(timeout_o_error)": jugadores_sin_datos,
        "porcentaje_cobertura_total": round(
            jugadores_con_datos / total_jugadores_objetivo * 100, 1
        ),
        "filas_totales_competicion_jugador": len(df_final),
    }


if __name__ == "__main__":
    print("=" * 80)
    print("PASO 1: CARGA DE ARCHIVOS JSON DISPONIBLES")
    print("=" * 80)
    estadisticas_crudas = cargar_estadisticas_crudas()
    print(f"\n✅ {len(estadisticas_crudas)} archivos de jugador cargados")
    print("   (este número refleja hasta dónde llegó el proceso antes de")
    print("   detenerse deliberadamente).")

    print("\n" + "=" * 80)
    print("PASO 2: APLANADO A TABLA")
    print("=" * 80)
    df_crudo = aplanar_a_tabla(estadisticas_crudas)
    print(f"\n✅ {len(df_crudo)} filas (competición x jugador) generadas.")

    df_crudo.to_csv(RAW_DIR.parent / "leistungsdaten_crudo_parcial.csv", index=False)
    print(f"   Guardado en raw/leistungsdaten_crudo_parcial.csv (evidencia técnica)")

    print("\n" + "=" * 80)
    print("PASO 3: LIMPIEZA DE VALORES")
    print("=" * 80)
    df_limpio = limpiar_tabla(df_crudo)
    print(f"\n✅ Limpieza aplicada: '-' convertido a 0, minutos sin comas/apóstrofes.")
    print(df_limpio.head(10).to_string(index=False))

    print("\n" + "=" * 80)
    print("PASO 4: CRUCE CON DATASET DE JUGADORES (posición, selección, club)")
    print("=" * 80)
    df_final = cruzar_con_jugadores(df_limpio)
    print(f"\n✅ Cruce completado. Columnas finales: {list(df_final.columns)}")

    print("\n" + "=" * 80)
    print("PASO 5: DIAGNÓSTICO DE COBERTURA (para minireporte y limitaciones)")
    print("=" * 80)
    diagnostico = diagnosticar_cobertura(df_final)
    for clave, valor in diagnostico.items():
        print(f"\n• {clave}: {valor}")

    df_final.to_csv(CLEAN_DIR / "leistungsdaten_parcial_limpio.csv", index=False)
    print(f"\n✅ Dataset final guardado en clean/leistungsdaten_parcial_limpio.csv")
    print("\n⚠️ RECORDATORIO PARA EL MINIREPORTE: este dataset es PARCIAL")
    print("   (aprox. 79% de cobertura). Documentar como limitación reconocida")
    print("   en la sección correspondiente del Producto 2.")