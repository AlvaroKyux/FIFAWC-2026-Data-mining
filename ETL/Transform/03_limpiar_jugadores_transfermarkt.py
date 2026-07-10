"""
Proyecto: Data Mining - FIFA WC2026
Entregable 3 - Limpieza y Transformación
Fuente: Transfermarkt — Filtrado y limpieza de plantillas

CONTEXTO: el extractor (02_transfermarkt_plantillas.py) corrió sin poder
encontrar clean/equipos_limpio.csv (problema de ruta relativa entre las
carpetas Extract/ y Transform/ del proyecto), por lo que el filtrado a
las 48 selecciones del Mundial 2026 NO se aplicó en ese momento. Como
resultado, se extrajeron 210 de 211 selecciones del ranking FIFA completo
(todo, no solo el Mundial). Esto NO se perdió: este script retoma esos
210 archivos JSON ya guardados y aplica el filtrado y la limpieza aquí,
sin necesidad de repetir el scraping.

Este script:
1. Lee TODOS los archivos JSON en raw/transfermarkt_plantillas/.
2. Filtra solo las 48 selecciones que están en el Mundial 2026 (cruce
   contra clean/equipos_limpio.csv de la Fase 1).
3. Aplana la estructura (jugadores anidados por selección) a una tabla
   plana de jugadores, con la selección como columna.
4. Aplica las transformaciones de limpieza:
   - Conversión de valor de mercado (texto "€12.00m") a número.
   - Separación de fecha de nacimiento y edad en columnas distintas.
   - Conversión de fecha a tipo datetime real.
5. Diagnostica duplicados y valores faltantes (para el TikTok 3).
6. Guarda el dataset limpio final.

IMPORTANTE SOBRE RUTAS: ajusta RAW_DIR y CLEAN_DIR abajo según donde
hayas corrido cada script. Si Fase 1 y Fase 2 quedaron en carpetas
distintas (Extract/ vs Transform/), usa rutas absolutas o copia los
archivos a una sola carpeta antes de continuar, para evitar el mismo
problema de ruta relativa que ya tuvimos.
"""

import json
import re
from pathlib import Path

import pandas as pd

RAW_PLANTILLAS_DIR = Path("raw/transfermarkt_plantillas")
RUTA_EQUIPOS_MUNDIAL = Path("clean/equipos_limpio.csv")  # de la Fase 1
CLEAN_DIR = Path("clean")
CLEAN_DIR.mkdir(exist_ok=True)


def cargar_plantillas_crudas() -> list[dict]:
    """Lee todos los JSON de plantillas ya extraídas (sin filtrar todavía)."""
    archivos = list(RAW_PLANTILLAS_DIR.glob("*.json"))
    plantillas = []
    for archivo in archivos:
        with open(archivo, encoding="utf-8") as f:
            plantillas.append(json.load(f))
    return plantillas


def filtrar_a_mundial(plantillas: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Filtra las plantillas crudas a solo las 48 selecciones del Mundial 2026,
    cruzando por nombre normalizado contra equipos_limpio.csv.
    Devuelve (plantillas_filtradas, nombres_no_encontrados).
    """
    if not RUTA_EQUIPOS_MUNDIAL.exists():
        raise FileNotFoundError(
            f"No se encontró {RUTA_EQUIPOS_MUNDIAL}. Verifica que estás "
            f"corriendo este script desde una carpeta donde también esté "
            f"disponible el resultado de la Fase 1 (01_worldcup26ir_etl.py)."
        )

    equipos_mundial = pd.read_csv(RUTA_EQUIPOS_MUNDIAL)
    nombres_mundial = set(equipos_mundial["name_en_normalizado"])

    filtradas = []
    nombres_encontrados = set()

    for plantilla in plantillas:
        nombre_normalizado = plantilla["pais"].strip().upper()
        if nombre_normalizado in nombres_mundial:
            filtradas.append(plantilla)
            nombres_encontrados.add(nombre_normalizado)

    no_encontrados = sorted(nombres_mundial - nombres_encontrados)
    return filtradas, no_encontrados


def aplanar_a_tabla_jugadores(plantillas: list[dict]) -> pd.DataFrame:
    """Convierte la estructura anidada (selección -> jugadores) a una tabla plana."""
    filas = []
    for plantilla in plantillas:
        for jugador in plantilla["jugadores"]:
            fila = {"seleccion": plantilla["pais"], **jugador}
            filas.append(fila)
    return pd.DataFrame(filas)


def diagnosticar_crudo(df: pd.DataFrame) -> dict:
    """Diagnóstico antes de limpiar, para el TikTok 3."""
    return {
        "total_jugadores": len(df),
        "selecciones_representadas": df["seleccion"].nunique(),
        "nulos_por_columna": df.isnull().sum().to_dict(),
        "duplicados_por_player_id": df["player_id"].duplicated().sum(),
        "jugadores_sin_player_id": df["player_id"].isnull().sum(),
        "promedio_jugadores_por_seleccion": round(
            len(df) / df["seleccion"].nunique(), 1
        ) if df["seleccion"].nunique() else 0,
    }


def limpiar_valor_mercado(valor_raw) -> float | None:
    """
    Convierte '€12.00m' -> 12000000.0, '€500k' o '€500Th.' -> 500000.0.
    Devuelve None si no se puede parsear (ej. '-' para jugadores sin valor).
    """
    if not isinstance(valor_raw, str):
        return None

    valor_raw = valor_raw.strip()
    match = re.search(r"€?([\d.]+)\s*(m|k|Th\.?|bn)?", valor_raw, re.IGNORECASE)
    if not match:
        return None

    numero_str, unidad = match.groups()
    try:
        numero = float(numero_str)
    except ValueError:
        return None

    unidad = (unidad or "").lower()
    if unidad in ("m",):
        return numero * 1_000_000
    elif unidad in ("k", "th", "th."):
        return numero * 1_000
    elif unidad in ("bn",):
        return numero * 1_000_000_000
    else:
        return numero  # sin unidad reconocida, se asume valor base


def separar_fecha_edad(fecha_edad_raw) -> tuple[str | None, int | None]:
    """
    Separa 'DD/MM/YYYY (edad)' en (fecha_str, edad_int).
    """
    if not isinstance(fecha_edad_raw, str):
        return None, None

    match = re.match(r"(\d{2}/\d{2}/\d{4})\s*\((\d+)\)", fecha_edad_raw.strip())
    if not match:
        return fecha_edad_raw, None

    fecha_str, edad_str = match.groups()
    return fecha_str, int(edad_str)


def limpiar_tabla_jugadores(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica todas las transformaciones de limpieza."""
    df_limpio = df.copy()

    # Separar fecha de nacimiento y edad en columnas independientes
    fechas_edades = df_limpio["fecha_nacimiento_edad_raw"].apply(separar_fecha_edad)
    df_limpio["fecha_nacimiento_str"] = fechas_edades.apply(lambda x: x[0])
    df_limpio["edad"] = fechas_edades.apply(lambda x: x[1])

    # Convertir fecha de nacimiento a datetime real (formato DD/MM/YYYY)
    df_limpio["fecha_nacimiento"] = pd.to_datetime(
        df_limpio["fecha_nacimiento_str"], format="%d/%m/%Y", errors="coerce"
    )

    # Convertir valor de mercado a número
    df_limpio["valor_mercado_eur"] = df_limpio["valor_mercado_raw"].apply(limpiar_valor_mercado)

    # Normalizar nombre de selección (para cruzar con la tabla de mapeo universal)
    df_limpio["seleccion_normalizada"] = df_limpio["seleccion"].str.strip().str.upper()

    # Eliminar duplicados por player_id (si el mismo jugador apareciera dos veces)
    duplicados_antes = df_limpio["player_id"].duplicated().sum()
    df_limpio = df_limpio.drop_duplicates(subset="player_id", keep="first")

    columnas_finales = [
        "seleccion", "seleccion_normalizada", "player_id", "nombre",
        "posicion", "fecha_nacimiento", "edad", "club_actual",
        "valor_mercado_eur", "href_perfil",
    ]
    return df_limpio[columnas_finales], duplicados_antes


if __name__ == "__main__":
    print("=" * 80)
    print("PASO 1: CARGA DE PLANTILLAS CRUDAS")
    print("=" * 80)
    plantillas_crudas = cargar_plantillas_crudas()
    print(f"\n✅ {len(plantillas_crudas)} archivos de selección cargados.")

    print("\n" + "=" * 80)
    print("PASO 2: FILTRADO A LAS 48 SELECCIONES DEL MUNDIAL 2026")
    print("=" * 80)
    plantillas_mundial, no_encontrados = filtrar_a_mundial(plantillas_crudas)
    print(f"\n✅ {len(plantillas_mundial)} selecciones del Mundial encontradas en los datos crudos.")
    if no_encontrados:
        print(f"\n⚠️ {len(no_encontrados)} selecciones del Mundial NO se encontraron")
        print(f"   entre los archivos extraídos (puede requerir re-extracción puntual):")
        print(f"   {no_encontrados}")

    print("\n" + "=" * 80)
    print("PASO 3: APLANADO A TABLA DE JUGADORES")
    print("=" * 80)
    df_crudo = aplanar_a_tabla_jugadores(plantillas_mundial)
    print(f"\n✅ Tabla aplanada: {len(df_crudo)} jugadores en total.")

    # Guardamos el crudo aplanado (pre-limpieza) como evidencia técnica
    df_crudo.to_csv(RAW_PLANTILLAS_DIR.parent / "jugadores_mundial_crudo.csv", index=False)

    print("\n" + "=" * 80)
    print("PASO 4: DIAGNÓSTICO DEL DATASET CRUDO (para TikTok 3)")
    print("=" * 80)
    diagnostico = diagnosticar_crudo(df_crudo)
    for clave, valor in diagnostico.items():
        print(f"\n• {clave}: {valor}")

    print("\n" + "=" * 80)
    print("PASO 5: LIMPIEZA Y TRANSFORMACIÓN")
    print("=" * 80)
    df_limpio, duplicados_eliminados = limpiar_tabla_jugadores(df_crudo)
    print(f"\nDuplicados por player_id eliminados: {duplicados_eliminados}")
    print(f"Jugadores en dataset final: {len(df_limpio)}")
    print("\n--- Muestra ---")
    print(df_limpio.head(10).to_string(index=False))

    print("\n--- Verificación de valores de mercado parseados ---")
    print(f"Valores nulos tras conversión: {df_limpio['valor_mercado_eur'].isnull().sum()}")
    print(f"Rango: €{df_limpio['valor_mercado_eur'].min():,.0f} - €{df_limpio['valor_mercado_eur'].max():,.0f}")

    print("\n--- Verificación de fechas de nacimiento ---")
    print(f"Fechas nulas tras conversión: {df_limpio['fecha_nacimiento'].isnull().sum()}")
    print(f"Rango de edades: {df_limpio['edad'].min()} - {df_limpio['edad'].max()}")

    df_limpio.to_csv(CLEAN_DIR / "jugadores_mundial_limpio.csv", index=False)
    print(f"\n✅ Dataset limpio guardado en clean/jugadores_mundial_limpio.csv")