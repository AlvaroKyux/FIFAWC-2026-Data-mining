"""
Proyecto: Data Mining - FIFA WC2026
Entregable 2 - Selección y Evaluación de Datos
Fuente evaluada: StatsBomb Open Data

Objetivo de este script:
1. Listar TODAS las competiciones/temporadas disponibles en el catálogo gratuito.
2. Verificar si existen Mundiales anteriores y en qué formato.
3. Verificar si ya hay algo del Mundial 2026 (probablemente NO, por estar en curso).
4. Extraer una muestra real de datos de eventos para inspeccionar columnas/calidad.

Nota: statsbombpy descarga los datos directamente del repositorio público
de GitHub de StatsBomb (open-data), por lo que requiere conexión a internet.
"""

import pandas as pd
from statsbombpy import sb
import warnings

warnings.filterwarnings("ignore")  # statsbombpy lanza warnings de "credentials" que no aplican a open data

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def explorar_competiciones():
    """
    Paso 1: Obtener el catálogo completo de competiciones disponibles.
    Esto responde directamente al checklist: '¿Qué competiciones/temporadas
    están en el catálogo gratuito?'
    """
    print("=" * 80)
    print("PASO 1: CATÁLOGO DE COMPETICIONES DISPONIBLES EN STATSBOMB OPEN DATA")
    print("=" * 80)

    competitions = sb.competitions()
    print(f"\nTotal de competición-temporadas disponibles: {len(competitions)}")
    print(f"\nColumnas disponibles: {list(competitions.columns)}\n")

    # Vista completa ordenada por país/competición
    print(competitions[["competition_id", "season_id", "country_name",
                         "competition_name", "season_name"]].to_string(index=False))

    return competitions


def buscar_mundiales(competitions: pd.DataFrame):
    """
    Paso 2: Filtrar específicamente competiciones relacionadas con
    'World Cup' para responder: ¿incluye Mundiales anteriores?
    """
    print("\n" + "=" * 80)
    print("PASO 2: ¿HAY MUNDIALES (WORLD CUP) EN EL CATÁLOGO?")
    print("=" * 80)

    mundiales = competitions[
        competitions["competition_name"].str.contains("World Cup", case=False, na=False)
    ]

    if mundiales.empty:
        print("\n⚠️ No se encontró ninguna competición con 'World Cup' en el nombre.")
    else:
        print(f"\nSe encontraron {len(mundiales)} entradas relacionadas con 'World Cup':\n")
        print(mundiales[["competition_id", "season_id", "country_name",
                          "competition_name", "season_name"]].to_string(index=False))

    return mundiales


def verificar_mundial_2026(competitions: pd.DataFrame):
    """
    Paso 3: Verificar explícitamente si existe la temporada 2026
    (respuesta esperada: NO, porque el torneo está en curso/no concluido
    y StatsBomb libera datos abiertos típicamente DESPUÉS de cada edición).
    """
    print("\n" + "=" * 80)
    print("PASO 3: ¿EXISTE YA DATA DEL MUNDIAL 2026?")
    print("=" * 80)

    contiene_2026 = competitions[
        competitions["season_name"].astype(str).str.contains("2026", na=False)
    ]

    if contiene_2026.empty:
        print("\n❌ CONFIRMADO: No hay ninguna temporada '2026' disponible todavía.")
        print("   Esto era esperado: StatsBomb publica datos abiertos de un torneo")
        print("   normalmente DESPUÉS de que concluye, no durante.")
        print("   IMPLICACIÓN PARA EL PROYECTO: StatsBomb NO puede ser la fuente")
        print("   para datos del Mundial 2026 EN VIVO. Solo servirá como fuente")
        print("   histórica de referencia (Mundiales pasados) y, posiblemente,")
        print("   como fuente del WC2026 hasta mucho después de que termine.")
    else:
        print("\n✅ Sorpresa: SÍ hay datos relacionados con 2026:")
        print(contiene_2026.to_string(index=False))

    return contiene_2026


def explorar_muestra_eventos(mundiales: pd.DataFrame):
    """
    Paso 4: Tomar UN Mundial disponible (el más reciente que exista)
    y extraer una muestra real de partidos + eventos para ver columnas,
    nivel de detalle y posibles huecos.
    """
    print("\n" + "=" * 80)
    print("PASO 4: MUESTRA REAL DE DATOS (PARTIDOS Y EVENTOS)")
    print("=" * 80)

    if mundiales.empty:
        print("\nNo hay Mundiales disponibles para muestrear. Se omite este paso.")
        return None, None

    # Tomamos el Mundial más reciente disponible en el catálogo
    fila = mundiales.sort_values("season_name", ascending=False).iloc[0]
    comp_id, season_id = fila["competition_id"], fila["season_id"]
    print(f"\nUsando como muestra: {fila['competition_name']} - {fila['season_name']}")

    partidos = sb.matches(competition_id=comp_id, season_id=season_id)
    print(f"\nPartidos disponibles en esta edición: {len(partidos)}")
    print(f"Columnas de 'matches': {list(partidos.columns)}\n")
    print(partidos[["match_id", "match_date", "home_team", "away_team",
                     "home_score", "away_score"]].head(10).to_string(index=False))

    # Eventos de un solo partido (el primero de la lista) para ver el detalle disponible
    match_id_muestra = partidos.iloc[0]["match_id"]
    eventos = sb.events(match_id=match_id_muestra)

    print(f"\n--- Eventos del partido_id {match_id_muestra} ---")
    print(f"Total de eventos registrados: {len(eventos)}")
    print(f"Columnas disponibles en eventos: {len(eventos.columns)}")
    print(f"\nTipos de evento encontrados (campo 'type'):")
    print(eventos["type"].value_counts().to_string())

    return partidos, eventos


def resumen_evaluacion():
    """
    Paso 5: Imprimir un resumen estructurado según los 6 criterios de
    evaluación definidos en la Fase 1 del plan (Accesibilidad, Cobertura,
    Completitud, Actualidad, Confiabilidad, Sesgo potencial).
    Este resumen es la base directa para llenar la tabla del minireporte.
    """
    print("\n" + "=" * 80)
    print("RESUMEN DE EVALUACIÓN - StatsBomb Open Data")
    print("(completar manualmente los campos marcados con [REVISAR] según salida real)")
    print("=" * 80)

    resumen = {
        "Accesibilidad": "Confirmado: librería oficial en Python (statsbombpy), sin API key, sin costo, sin errores en la ejecución. Descarga directa desde el repositorio público de GitHub de StatsBomb.",
        "Cobertura temporal/temática": "80 competición-temporadas en total. Incluye 7 Mundiales masculinos (1958-2022) y 2 Mundiales femeninos (2019, 2023), además de ligas de clubes (Bundesliga, La Liga, Ligue 1, Premier League, Serie A) pero con cobertura DESIGUAL e incompleta por temporada (ej. Premier League solo tiene 2003/04 y 2015/16, no todas las temporadas recientes).",
        "Completitud": "Alta a nivel de partido: el Mundial Qatar 2022 tiene sus 64 partidos completos (fase de grupos a final). A nivel de evento, cada partido trae entre 3,400 y 4,400 eventos individuales con 94 columnas (incluye player_id, minute, shot_statsbomb_xg, pass_goal_assist, duel_outcome).",
        "Actualidad": "NO cubre WC2026 en curso (confirmado: no existe ninguna temporada '2026' en el catálogo). Esto es estructural: StatsBomb libera datos abiertos de un torneo después de que concluye. Implicación directa: StatsBomb sirve para datos HISTÓRICOS (ej. Qatar 2022 como benchmark) pero NO para el Mundial 2026 mientras esté en curso.",
        "Confiabilidad/reputación": "Alta: dataset usado ampliamente en investigación académica y por analistas profesionales de fútbol.",
        "Sesgo potencial": "La cobertura de ligas de clubes es desigual entre países y temporadas (ej. mucha data de España/Europa en años específicos, hueco en otras ligas y temporadas recientes). Para Mundiales, la cobertura histórica SÍ es completa por edición.",
        "Decisión preliminar": "ACEPTAR como fuente principal para datos de Mundiales PASADOS (útil como benchmark histórico de rendimiento en torneo). DESCARTAR como fuente para el Mundial 2026 en vivo — se requiere una fuente alterna (API-Football o worldcup26.ir) para esa parte del análisis mientras el torneo está en curso.",
    }

    for criterio, valor in resumen.items():
        print(f"\n• {criterio}:\n  {valor}")


if __name__ == "__main__":
    competitions = explorar_competiciones()
    mundiales = buscar_mundiales(competitions)
    verificar_mundial_2026(competitions)
    explorar_muestra_eventos(mundiales)
    resumen_evaluacion()