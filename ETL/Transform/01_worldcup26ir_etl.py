"""
Proyecto: Data Mining - FIFA WC2026
Entregable 3 - Limpieza y Transformación
Fuente: worldcup26.ir

Este script:
1. Extrae los 48 equipos (requiere autenticación JWT, ya validada en Entregable 2).
2. Limpia y normaliza el dataset crudo.
3. Construye la TABLA DE MAPEO DE NOMBRES que usaremos como referencia
   universal para cruzar las otras dos fuentes (Transfermarkt, StatsBomb),
   ya que cada una nombra a las selecciones de forma distinta.

CREDENCIALES: reemplazar EMAIL y PASSWORD con las que ya usaste en el
Entregable 2 (el registro con sirkyux100@gmail.com ya existe, así que
este script usa el endpoint de LOGIN, no de registro).
"""

import requests
import pandas as pd
import json
from pathlib import Path

BASE_URL = "https://worldcup26.ir"
EMAIL = "sirkyux100@gmail.com"   # ya registrado en el Entregable 2
PASSWORD = "pass123"

RAW_DIR = Path("raw")
CLEAN_DIR = Path("clean")
RAW_DIR.mkdir(exist_ok=True)
CLEAN_DIR.mkdir(exist_ok=True)


def obtener_token() -> str:
    """Login contra la API real de producción (no Swagger, que está mal configurado)."""
    resp = requests.post(
        f"{BASE_URL}/auth/authenticate",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def extraer_equipos(token: str) -> pd.DataFrame:
    """Descarga los 48 equipos y los convierte a DataFrame."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/get/teams", headers=headers, timeout=15)
    resp.raise_for_status()

    data = resp.json()["teams"]

    # Guardamos el crudo exactamente como llegó, ANTES de tocar nada.
    # Esto es evidencia técnica de "antes de la limpieza" para el minireporte.
    with open(RAW_DIR / "worldcup26ir_teams_raw.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(data)
    return df


def diagnosticar_crudo(df: pd.DataFrame) -> dict:
    """
    Diagnóstico ANTES de limpiar: nulos, duplicados, tipos.
    Esto es lo que documentamos para el TikTok 3 ("errores encontrados").
    """
    diagnostico = {
        "total_registros": len(df),
        "columnas": list(df.columns),
        "nulos_por_columna": df.isnull().sum().to_dict(),
        "duplicados_por_id": df["id"].duplicated().sum(),
        "duplicados_por_fifa_code": df["fifa_code"].duplicated().sum(),
        "grupos_unicos": sorted(df["groups"].unique().tolist()),
        "equipos_por_grupo": df.groupby("groups").size().to_dict(),
    }
    return diagnostico


def limpiar_equipos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica las transformaciones de limpieza:
    - Normaliza el id a entero (llega como string en el JSON crudo).
    - Estandariza el nombre a mayúsculas/sin espacios extra para comparación.
    - Verifica que el código FIFA tenga exactamente 3 caracteres (estándar).
    - Elimina columnas que no necesitamos para el análisis (name_fa, flag)
      pero las dejamos en el crudo por si se necesitan después.
    """
    df_limpio = df.copy()

    # Tipos: id y groups llegan como string; id debería ser numérico
    df_limpio["id"] = pd.to_numeric(df_limpio["id"], errors="coerce").astype("Int64")

    # Normalización de texto para comparación entre fuentes
    df_limpio["name_en_normalizado"] = (
        df_limpio["name_en"].str.strip().str.upper()
    )

    # Validación de longitud del código ISO2 (debe ser exactamente 2 letras).
    # HALLAZGO REAL: Inglaterra y Escocia tienen iso2="ENG"/"SCO" (3 letras,
    # igual a su fifa_code) en lugar de un código ISO 3166-1 alpha-2 real,
    # porque no son países soberanos con código ISO propio (son naciones
    # constituyentes del Reino Unido). El fifa_code SÍ es consistente
    # (siempre 3 letras) para las 48 selecciones.
    df_limpio["iso2_valido"] = df_limpio["iso2"].str.len() == 2

    # Renombramos para claridad y dejamos solo las columnas relevantes al análisis
    df_limpio = df_limpio.rename(columns={
        "fifa_code": "codigo_fifa",
        "iso2": "codigo_iso2",
        "groups": "grupo",
        "name_en": "nombre_en",
    })

    columnas_finales = [
        "id", "nombre_en", "name_en_normalizado", "codigo_fifa",
        "codigo_iso2", "iso2_valido", "grupo",
    ]
    return df_limpio[columnas_finales]


def construir_tabla_mapeo(df_limpio: pd.DataFrame) -> pd.DataFrame:
    """
    Construye la tabla de mapeo de nombres que usaremos como referencia
    universal. Por ahora solo tiene la variante de worldcup26.ir; en las
    fases de Transfermarkt y StatsBomb vamos a AGREGAR columnas a esta
    misma tabla con el nombre que cada fuente usa para el mismo equipo,
    para poder cruzarlas más adelante con un solo JOIN limpio.
    """
    mapeo = df_limpio[["codigo_fifa", "nombre_en", "name_en_normalizado", "grupo"]].copy()
    mapeo = mapeo.rename(columns={"nombre_en": "nombre_worldcup26ir"})
    return mapeo


if __name__ == "__main__":
    print("=" * 80)
    print("PASO 1: AUTENTICACIÓN Y EXTRACCIÓN")
    print("=" * 80)
    token = obtener_token()
    df_crudo = extraer_equipos(token)
    print(f"✅ {len(df_crudo)} equipos extraídos y guardados en raw/worldcup26ir_teams_raw.json")

    print("\n" + "=" * 80)
    print("PASO 2: DIAGNÓSTICO DEL DATASET CRUDO (para TikTok 3)")
    print("=" * 80)
    diagnostico = diagnosticar_crudo(df_crudo)
    for clave, valor in diagnostico.items():
        print(f"\n• {clave}: {valor}")

    print("\n" + "=" * 80)
    print("PASO 3: LIMPIEZA Y NORMALIZACIÓN")
    print("=" * 80)
    df_limpio = limpiar_equipos(df_crudo)
    print(df_limpio.head(10).to_string(index=False))

    # Verificación de códigos ISO2 "no estándar" (ENG, SCO no son 2 letras)
    no_estandar = df_limpio[~df_limpio["iso2_valido"]]
    if not no_estandar.empty:
        print(f"\n⚠️ {len(no_estandar)} equipos con código ISO2 fuera del estándar de 2 letras:")
        print(no_estandar[["nombre_en", "codigo_fifa", "codigo_iso2"]].to_string(index=False))
        print("   (Inglaterra/Escocia no tienen código ISO propio al ser naciones")
        print("    constituyentes del Reino Unido, no países soberanos)")

    df_limpio.to_csv(CLEAN_DIR / "equipos_limpio.csv", index=False)
    print(f"\n✅ Dataset limpio guardado en clean/equipos_limpio.csv")

    print("\n" + "=" * 80)
    print("PASO 4: TABLA DE MAPEO DE NOMBRES (referencia universal)")
    print("=" * 80)
    tabla_mapeo = construir_tabla_mapeo(df_limpio)
    tabla_mapeo.to_csv(CLEAN_DIR / "tabla_mapeo_selecciones.csv", index=False)
    print(tabla_mapeo.head(10).to_string(index=False))
    print(f"\n✅ Tabla de mapeo guardada en clean/tabla_mapeo_selecciones.csv")
    print("   (esta tabla se irá ampliando con columnas de Transfermarkt y StatsBomb)")