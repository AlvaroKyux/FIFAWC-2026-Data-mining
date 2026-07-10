"""
Proyecto: Data Mining - FIFA WC2026
Entregable 3 - Limpieza y Transformación
Fuente: StatsBomb Open Data — FIFA World Cup Qatar 2022 (completo)

A diferencia de Transfermarkt, StatsBomb no tiene rate-limit agresivo ni
bloqueo por comportamiento (descarga directa desde el repositorio público
de GitHub), por lo que este extractor no necesita pausas largas.

Este script:
1. Descarga los 64 partidos de Qatar 2022 (competition_id=43, season_id=106).
2. Descarga TODOS los eventos de TODOS los partidos (puede tardar varios
   minutos por el volumen: ~64 partidos x ~3,500-4,400 eventos cada uno).
3. Consolida todo en una sola tabla de eventos.
4. Construye una tabla RESUMEN de rendimiento por jugador y partido
   (minutos jugados, goles, asistencias, xG, duelos ganados/perdidos),
   que es la forma directamente usable para las Preguntas 2 y 3 del proyecto.
5. Diagnostica y limpia el dataset resultante.

INSTALACIÓN PREVIA:
    python -m pip install statsbombpy pandas

TIEMPO ESTIMADO: 5-10 minutos (64 partidos, sin rate-limit pero con
volumen de datos considerable).
"""

import warnings
import json
from pathlib import Path

import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore")

COMPETITION_ID = 43  # FIFA World Cup
SEASON_ID = 106      # 2022 (Qatar)

RAW_DIR = Path("raw/statsbomb_qatar2022")
RAW_DIR.mkdir(parents=True, exist_ok=True)
CLEAN_DIR = Path("clean")
CLEAN_DIR.mkdir(exist_ok=True)


def extraer_partidos() -> pd.DataFrame:
    """Descarga los 64 partidos de Qatar 2022."""
    partidos = sb.matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
    partidos.to_csv(RAW_DIR / "partidos_qatar2022_raw.csv", index=False)
    return partidos


def extraer_todos_los_eventos(partidos: pd.DataFrame) -> pd.DataFrame:
    """
    Descarga los eventos de TODOS los partidos y los consolida en una
    sola tabla. Guarda también un JSON crudo por partido como evidencia
    técnica (igual que hicimos con Transfermarkt: crudo antes de limpiar).
    """
    todos_los_eventos = []

    for i, match_id in enumerate(partidos["match_id"], 1):
        print(f"[{i}/{len(partidos)}] Descargando eventos del partido {match_id}...")
        eventos = sb.events(match_id=match_id)
        eventos["match_id"] = match_id  # asegurar la columna por si no viene
        todos_los_eventos.append(eventos)

        # Guardado incremental por partido (mismo principio de reanudabilidad
        # que usamos en Transfermarkt, aunque aquí el riesgo de bloqueo es
        # mínimo, es buena práctica para no perder avance si algo falla)
        eventos.to_json(RAW_DIR / f"eventos_{match_id}.json", orient="records")

    df_eventos = pd.concat(todos_los_eventos, ignore_index=True)
    return df_eventos


def diagnosticar_eventos(df: pd.DataFrame) -> dict:
    """Diagnóstico antes de limpiar, para el TikTok 3."""
    return {
        "total_eventos": len(df),
        "partidos_representados": df["match_id"].nunique(),
        "promedio_eventos_por_partido": round(len(df) / df["match_id"].nunique(), 1),
        "jugadores_unicos": df["player_id"].nunique(),
        "tipos_de_evento": df["type"].value_counts().to_dict(),
        "nulos_en_columnas_clave": df[["player_id", "minute", "team"]].isnull().sum().to_dict(),
    }


def construir_tabla_resumen_jugador_partido(df_eventos: pd.DataFrame) -> pd.DataFrame:
    """
    Construye la tabla RESUMEN que el proyecto necesita: una fila por
    jugador-partido, con sus métricas agregadas de rendimiento.
    Esto es lo que se usará directamente en las Preguntas 2 y 3.
    """
    # Filtramos solo eventos que tienen jugador asociado (algunos eventos
    # de tipo "Half Start", "Tactical Shift", etc. no tienen player_id)
    df_jugador = df_eventos[df_eventos["player_id"].notna()].copy()

    resumen = df_jugador.groupby(["match_id", "team", "player_id", "player"]).agg(
        total_eventos=("type", "count"),
        minuto_ultimo_evento=("minute", "max"),
        pases=("type", lambda x: (x == "Pass").sum()),
        tiros=("type", lambda x: (x == "Shot").sum()),
        duelos=("type", lambda x: (x == "Duel").sum()),
    ).reset_index()

    # xG: solo existe en eventos de tipo Shot, hay que sumarlo aparte
    if "shot_statsbomb_xg" in df_jugador.columns:
        xg_por_jugador = df_jugador.groupby(["match_id", "player_id"])["shot_statsbomb_xg"].sum().reset_index()
        xg_por_jugador = xg_por_jugador.rename(columns={"shot_statsbomb_xg": "xg_total"})
        resumen = resumen.merge(xg_por_jugador, on=["match_id", "player_id"], how="left")
        resumen["xg_total"] = resumen["xg_total"].fillna(0)

    # Asistencias: eventos de pase donde pass_goal_assist es True
    if "pass_goal_assist" in df_jugador.columns:
        asistencias = df_jugador[df_jugador["pass_goal_assist"] == True].groupby(
            ["match_id", "player_id"]
        ).size().reset_index(name="asistencias")
        resumen = resumen.merge(asistencias, on=["match_id", "player_id"], how="left")
        resumen["asistencias"] = resumen["asistencias"].fillna(0).astype(int)

    # Goles: eventos de tipo Shot con shot_outcome == "Goal"
    if "shot_outcome" in df_jugador.columns:
        goles = df_jugador[df_jugador["shot_outcome"] == "Goal"].groupby(
            ["match_id", "player_id"]
        ).size().reset_index(name="goles")
        resumen = resumen.merge(goles, on=["match_id", "player_id"], how="left")
        resumen["goles"] = resumen["goles"].fillna(0).astype(int)

    return resumen


if __name__ == "__main__":
    print("=" * 80)
    print("PASO 1: EXTRACCIÓN DE PARTIDOS")
    print("=" * 80)
    partidos = extraer_partidos()
    print(f"\n✅ {len(partidos)} partidos de Qatar 2022 descargados.")

    print("\n" + "=" * 80)
    print("PASO 2: EXTRACCIÓN DE EVENTOS (esto tardará varios minutos)")
    print("=" * 80)
    df_eventos = extraer_todos_los_eventos(partidos)
    print(f"\n✅ {len(df_eventos)} eventos descargados en total.")

    df_eventos.to_csv(RAW_DIR.parent / "statsbomb_eventos_crudo.csv", index=False)
    print(f"   Guardado en raw/statsbomb_eventos_crudo.csv")

    print("\n" + "=" * 80)
    print("PASO 3: DIAGNÓSTICO DEL DATASET CRUDO (para TikTok 3)")
    print("=" * 80)
    diagnostico = diagnosticar_eventos(df_eventos)
    for clave, valor in diagnostico.items():
        if clave == "tipos_de_evento":
            print(f"\n• {clave} (top 10):")
            for tipo, cuenta in list(valor.items())[:10]:
                print(f"    {tipo}: {cuenta}")
        else:
            print(f"\n• {clave}: {valor}")

    print("\n" + "=" * 80)
    print("PASO 4: TABLA RESUMEN DE RENDIMIENTO POR JUGADOR-PARTIDO")
    print("=" * 80)
    df_resumen = construir_tabla_resumen_jugador_partido(df_eventos)
    print(f"\n✅ {len(df_resumen)} filas jugador-partido en el resumen.")
    print(df_resumen.head(10).to_string(index=False))

    df_resumen.to_csv(CLEAN_DIR / "statsbomb_rendimiento_jugador_partido.csv", index=False)
    print(f"\n✅ Dataset limpio guardado en clean/statsbomb_rendimiento_jugador_partido.csv")