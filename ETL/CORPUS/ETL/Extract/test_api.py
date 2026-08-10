"""
test_newsapi_fuente.py
-----------------------
Verificacion de NewsAPI (newsapi.org) como fuente complementaria para
cobertura en ESPAÑOL del corpus de Sesion 4, tras evidencia de que GDELT
no es confiable para este idioma en el tiempo disponible del proyecto.

Se prueba tambien ingles como punto de comparacion directo contra los
resultados ya confirmados de GDELT (50/50 con "World Cup 2026").

IMPORTANTE - Limites del tier gratuito (Developer):
- 100 peticiones/dia.
- Solo articulos de hasta ~1 mes de antiguedad (coincide con tu alcance:
  Mundial 2026 / temporada regular actual, no historico).
- No apto para uso comercial/produccion, si para desarrollo y proyectos
  academicos como este.

Requiere: pip install requests --break-system-packages

Uso:
    1. Reemplazar API_KEY abajo con tu key de https://newsapi.org
    2. python test_newsapi_fuente.py
"""

import os
import requests
import json
import time
from datetime import datetime, timezone, timedelta

# La key se lee, en este orden de prioridad:
# 1. Variable de entorno NEWSAPI_KEY (si ya la configuraste asi)
# 2. Archivo local "newsapi_key.txt" en la MISMA carpeta que este script
#    (crea ese archivo tu mismo, en tu editor, con la key como unico
#    contenido -- NUNCA escribas la key en la terminal ni la pegues
#    en un chat; este metodo evita ambas cosas)
#
# IMPORTANTE: agrega "newsapi_key.txt" a tu .gitignore para que nunca
# se suba a GitHub por accidente.
def cargar_api_key():
    key = os.environ.get("NEWSAPI_KEY")
    if key:
        return key.strip()

    ruta_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsapi_key.txt")
    if os.path.exists(ruta_key):
        with open(ruta_key, "r", encoding="utf-8") as f:
            return f.read().strip()

    return None

API_KEY = cargar_api_key()
BASE_URL = "https://newsapi.org/v2/everything"

DIAS_ATRAS = 28  # NewsAPI free tier limita a ~1 mes; nos quedamos dentro del margen
FECHA_FIN = datetime.now(timezone.utc)
FECHA_INICIO = FECHA_FIN - timedelta(days=DIAS_ATRAS)

RESULTADOS_POR_QUERY = 20  # bajo a proposito, prueba inicial (no consumir cuota diaria)
PAUSA_ENTRE_PETICIONES = 2  # NewsAPI es mucho menos estricto que GDELT, pero mantenemos pausa preventiva

QUERIES_PRUEBA = [
    {
        "nombre": "ES - Mundial 2026",
        "params_extra": {"q": '"Mundial 2026"', "language": "es"},
    },
    {
        "nombre": "ES - selección española Mundial",
        "params_extra": {"q": "selección Mundial", "language": "es"},
    },
    {
        "nombre": "EN - World Cup 2026 (comparacion directa con GDELT)",
        "params_extra": {"q": '"World Cup 2026"', "language": "en"},
    },
]


def probar_query(nombre: str, params_extra: dict) -> dict:
    params = {
        "apiKey": API_KEY,
        "from": FECHA_INICIO.strftime("%Y-%m-%d"),
        "to": FECHA_FIN.strftime("%Y-%m-%d"),
        "sortBy": "relevancy",
        "pageSize": RESULTADOS_POR_QUERY,
        **params_extra,
    }

    print(f"\n{'='*70}")
    print(f"PRUEBA: {nombre}")
    print(f"Params: {params_extra}")
    print(f"{'='*70}")

    try:
        resp = requests.get(BASE_URL, params=params, timeout=20)
        print(f"Status code: {resp.status_code}")

        data = resp.json()

        if resp.status_code != 200:
            print(f"ERROR: {data.get('message', 'sin mensaje')}")
            return {"nombre": nombre, "exito": False, "error": data.get("message")}

        total_resultados = data.get("totalResults", 0)
        articulos = data.get("articles", [])
        print(f"Total resultados (reportado por API): {total_resultados}")
        print(f"Articulos devueltos en esta pagina: {len(articulos)}")

        if articulos:
            print("\nMuestra de titulos (primeros 5):")
            for art in articulos[:5]:
                titulo = art.get("title", "SIN TITULO")
                fuente = art.get("source", {}).get("name", "SIN FUENTE")
                fecha = art.get("publishedAt", "SIN FECHA")
                idioma_detectado = "N/A (NewsAPI no devuelve idioma detectado por articulo)"
                print(f"  [{fecha}] ({fuente}) {titulo}")

        return {
            "nombre": nombre,
            "exito": True,
            "total_resultados_api": total_resultados,
            "articulos_pagina": len(articulos),
            "muestra": articulos[:5],
        }

    except requests.exceptions.RequestException as e:
        print(f"ERROR de conexion: {e}")
        return {"nombre": nombre, "exito": False, "error": str(e)}
    except json.JSONDecodeError:
        print(f"ERROR: respuesta no es JSON valido. Texto: {resp.text[:300]}")
        return {"nombre": nombre, "exito": False, "error": "JSON invalido"}


def main():
    if not API_KEY:
        print("ERROR: no se encontro la API key.")
        print("Opcion A (recomendada): crea un archivo 'newsapi_key.txt' en esta")
        print("misma carpeta, con tu key como unico contenido (sin comillas).")
        print("Opcion B: variable de entorno, en PowerShell:")
        print('  $env:NEWSAPI_KEY = "tu_key_aqui"')
        print("  (en cmd.exe seria: set NEWSAPI_KEY=tu_key_aqui , sin comillas)")
        return

    print("VERIFICACION DE NEWSAPI COMO FUENTE COMPLEMENTARIA (ESPAÑOL)")
    print(f"Fecha de ejecucion: {datetime.now(timezone.utc).isoformat()}")
    print(f"Rango de fechas: {FECHA_INICIO.date()} a {FECHA_FIN.date()}")

    resultados = []
    for i, prueba in enumerate(QUERIES_PRUEBA):
        resultado = probar_query(prueba["nombre"], prueba["params_extra"])
        resultados.append(resultado)
        if i < len(QUERIES_PRUEBA) - 1:
            time.sleep(PAUSA_ENTRE_PETICIONES)

    print(f"\n\n{'='*70}")
    print("RESUMEN FINAL")
    print(f"{'='*70}")
    for r in resultados:
        if r["exito"]:
            print(f"[OK]    {r['nombre']}: {r['total_resultados_api']} resultados totales "
                  f"({r['articulos_pagina']} en esta pagina)")
        else:
            print(f"[FALLO] {r['nombre']}: {r.get('error', 'error desconocido')}")

    with open("newsapi_prueba_resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
    print("\nResultados completos guardados en: newsapi_prueba_resultados.json")


if __name__ == "__main__":
    main()