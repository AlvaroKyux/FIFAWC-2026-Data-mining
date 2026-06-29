"""
Proyecto: Data Mining - FIFA WC2026
Entregable 2 - Selección y Evaluación de Datos
Fuente evaluada: worldcup26.ir

HALLAZGO CRÍTICO VERIFICADO (investigación previa a este script):
worldcup26.ir NO es una fuente oficial de FIFA. Es un proyecto personal
de código abierto (github.com/rezarahiminia/worldcup2026), mantenido por
un solo desarrollador independiente. Esto tiene implicaciones directas:

1. RIESGO DE CONTINUIDAD: al depender del mantenimiento de una sola
   persona (no una organización), existe riesgo real de que el servicio
   cambie de estructura, presente downtime, o deje de mantenerse durante
   las 5 semanas del proyecto. Esto NO aplica igual a StatsBomb (mantenida
   por una empresa) ni a Transfermarkt (plataforma comercial establecida).

2. COBERTURA LIMITADA: solo expone equipos, grupos, partidos, estadios,
   marcadores y clasificaciones de los 48 equipos. NO tiene estadísticas
   avanzadas de jugador (sin xG, sin eventos de juego detallados). Es
   decir: sirve para contexto general del torneo (resultados, calendario),
   NO como fuente de rendimiento individual para las Preguntas 2 y 3.

3. REQUIERE AUTENTICACIÓN: a diferencia de lo que sugería el reporte
   inicial ("completamente gratuita, sin uso restringido"), esta API
   requiere un token JWT (Bearer token) válido por 84 días, tras lo cual
   hay que volver a autenticarse. No es anónima ni de acceso totalmente
   libre como StatsBomb Open Data.

DECISIÓN ADOPTADA: mantener worldcup26.ir en el proyecto, pero como
FUENTE COMPLEMENTARIA/DE RESPALDO para datos básicos del torneo en vivo
(calendario, resultados, marcadores), nunca como fuente única o crítica
para ninguna de las 3 preguntas de investigación. Esto se documenta
explícitamente en la sección de "Limitaciones" del Producto 2.

Objetivo de este script:
1. Verificar que el servicio está activo y responde.
2. Confirmar el flujo de autenticación (login -> token).
3. Extraer una muestra de equipos y calendario para validar estructura
   real de los datos devueltos.
4. Documentar el comportamiento ante fallos (qué pasa si el servicio
   no responde, para poder programar el equipo con manejo de errores
   adecuado desde el inicio).
"""

import requests

BASE_URL = "https://worldcup26.ir"

# IMPORTANTE: estos son datos de ejemplo. Revisar la documentación real
# en https://worldcup26.ir/api-docs/ para el flujo de login correcto
# (probablemente un endpoint POST /login o similar que devuelva el token).
# Este script asume que el equipo ya generó un token y lo coloca aquí.
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjZhNDFlYmZiZmU1YWQxNjA0ODA2ZDExOSIsImlhdCI6MTc4MjcwNTIyMywiZXhwIjoxNzg5OTYyODIzfQ.uD2W1TimKpqWRmXu0-0cx6yDkE9yXMxUV7Qx3XfbGtk"  # Reemplazar con tu JWT real una vez generado


def verificar_disponibilidad():
    """
    Paso 1: Verificar que el servicio responde, SIN autenticación,
    para confirmar que el sitio está activo en este momento.
    """
    print("=" * 80)
    print("PASO 1: VERIFICACIÓN DE DISPONIBILIDAD DEL SERVICIO")
    print("=" * 80)

    try:
        resp = requests.get(f"{BASE_URL}/get/teams", timeout=10)
        print(f"\nCódigo de respuesta: {resp.status_code}")

        if resp.status_code == 401:
            print("✅ El servicio está activo (responde), pero requiere")
            print("   autenticación (401 Unauthorized), como se documentó.")
        elif resp.status_code == 200:
            print("✅ El servicio respondió sin requerir autenticación")
            print("   para este endpoint específico.")
            print(f"Muestra de respuesta: {resp.text[:300]}")
        else:
            print(f"⚠️ Respuesta inesperada: {resp.status_code}")
            print(f"Cuerpo: {resp.text[:300]}")

        return resp
    except requests.exceptions.RequestException as e:
        print(f"\n❌ EL SERVICIO NO RESPONDIÓ: {e}")
        print("   Esto sería evidencia directa del riesgo de continuidad")
        print("   documentado (mantenimiento por un solo desarrollador).")
        return None


def probar_con_token(token: str):
    """
    Paso 2: Probar el endpoint de equipos con un token JWT válido.
    Llamar esta función manualmente una vez que tengas un token real.
    """
    print("\n" + "=" * 80)
    print("PASO 2: PRUEBA CON AUTENTICACIÓN")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(f"{BASE_URL}/get/teams", headers=headers, timeout=10)
        print(f"\nCódigo de respuesta: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"Total de equipos recibidos: {len(data) if isinstance(data, list) else 'N/A'}")
            print(f"Muestra del primer registro: {data[0] if isinstance(data, list) and data else data}")
        else:
            print(f"Cuerpo de la respuesta: {resp.text[:300]}")

        return resp
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error en la petición autenticada: {e}")
        return None


def resumen_evaluacion():
    print("\n" + "=" * 80)
    print("RESUMEN DE EVALUACIÓN - worldcup26.ir")
    print("=" * 80)

    resumen = {
        "Accesibilidad": "NO requiere scraping (es una API REST real con JSON), pero SÍ requiere autenticación vía token JWT (válido 84 días). Es más accesible técnicamente que FBref/Transfermarkt, pero menos abierta que StatsBomb (que no requiere ningún login).",
        "Cobertura temporal/temática": "Cubre los 48 equipos, calendario, marcadores en vivo y clasificaciones del Mundial 2026 EN CURSO — esto es justo lo que StatsBomb NO puede ofrecer (dato en vivo). Sin embargo, NO tiene estadísticas avanzadas de jugador (sin xG, sin eventos detallados de partido).",
        "Completitud": "[A COMPLETAR TRAS EJECUTAR EL SCRIPT: verificar si /get/teams y /get/games devuelven datos completos para los 48 equipos sin huecos]",
        "Actualidad": "Excelente para datos en vivo del torneo en curso — esto la hace complementaria perfecta a StatsBomb (que es histórica) y no competidora con ella.",
        "Confiabilidad/reputación": "BAJA-MEDIA: es un proyecto personal de un solo desarrollador independiente (NO es FIFA oficial, a pesar del nombre del dominio). Riesgo real de discontinuidad o cambios sin aviso durante las 5 semanas del proyecto.",
        "Sesgo potencial": "No aplica un sesgo de cobertura por liga/país (cubre los 48 equipos por igual), pero sí existe riesgo de errores de captura de datos al ser un proyecto no oficial sin el respaldo de validación de una organización grande.",
        "Decisión preliminar": "ACEPTAR como fuente COMPLEMENTARIA/DE RESPALDO únicamente para datos básicos del torneo en vivo (calendario, resultados, marcadores). NO usar como fuente única ni crítica para ninguna de las 3 preguntas de investigación del proyecto, dado el riesgo de continuidad documentado. Mantener StatsBomb/API-Football como respaldo si worldcup26.ir falla a mitad del proyecto.",
    }

    for criterio, valor in resumen.items():
        print(f"\n• {criterio}:\n  {valor}")


if __name__ == "__main__":
    verificar_disponibilidad()

    if TOKEN:
        probar_con_token(TOKEN)
    else:
        print("\n⚠️ No se proporcionó TOKEN. Para completar el Paso 2:")
        print("   1. Revisar https://worldcup26.ir/api-docs/ para el endpoint de login")
        print("   2. Generar un token JWT")
        print("   3. Asignarlo a la variable TOKEN al inicio de este script")
        print("   4. Volver a ejecutar")

    resumen_evaluacion()