# -*- coding: utf-8 -*-
"""
medir_volumen_diario_newsapi.py
---------------------------------
Sesion 7 - Correccion del sesgo de muestreo detectado en el corpus original.

Diagnostico (documentado en Bitacora BRAI):
  corpus_FIFA_WC.py (Sesion 4) pidio sortBy='relevancy' + una sola pagina
  de 100 resultados por query para las 4 semanas completas. Esto favorece
  sistematicamente a los articulos del evento mas grande (la final, 19-20
  jul) porque son los "mas relevantes" para las queries usadas, y desplaza
  del top-100 a articulos de dias de menor intensidad -- aunque esos
  articulos SI existen (confirmado empiricamente: verificar_dias_cero.py
  encontro 233, 282 y 164 resultados totales solo para el 27 de julio,
  un dia que en el corpus original aparecia con 0 articulos).

  Conclusion: el corpus de Sesion 4 es valido para clustering tematico
  (Sesion 6), donde queremos los articulos MAS relevantes/representativos.
  Pero NO es valido como fuente de conteo diario para series temporales,
  porque el mecanismo de muestreo esta correlacionado con la propia
  variable que se quiere medir (intensidad del evento).

Solucion:
  En vez de descargar articulos completos (redundante y caro en cuota),
  se consulta el campo 'totalResults' de NewsAPI dia por dia (from=to=
  mismo dia). totalResults refleja el universo COMPLETO de articulos que
  matchean la query ese dia, sin importar el orden de clasificacion --
  por lo tanto no arrastra el sesgo de relevancia. Es una medida de
  volumen, no un corpus de texto (para eso ya existe corpus_mundial2026_raw.json).

Cuota:
  4 queries x 28 dias = 112 peticiones, por encima del limite de 100/dia
  del tier gratuito. El script guarda progreso incremental en un JSON y
  puede pausarse/reanudarse: si se corta a mitad de camino (por rate
  limit u otra razon), la siguiente corrida retoma donde se quedo.

Requiere: newsapi_key.txt en esta misma carpeta (o variable NEWSAPI_KEY).

Uso:
    python medir_volumen_diario_newsapi.py
    (si se corta por limite de cuota, correr de nuevo al dia siguiente)
"""

import os
import json
import time
from datetime import datetime, timedelta

import requests

BASE_URL = "https://newsapi.org/v2/everything"

FECHA_INICIO = "2026-07-10"
FECHA_FIN = "2026-08-06"
PAUSA_ENTRE_PETICIONES = 1.5

# Mismas queries que corpus_FIFA_WC.py, para que el conteo diario sea
# comparable con el corpus original (no se cambian los terminos de busqueda,
# solo la forma de contarlos).
QUERIES = {
    "es_mundial2026": {"q": '"Mundial 2026"', "language": "es"},
    "es_seleccion_espanola": {"q": '"selección española" Mundial', "language": "es"},
    "en_worldcup2026": {"q": '"World Cup 2026"', "language": "en"},
    "en_fifa_worldcup": {"q": '"FIFA World Cup" 2026', "language": "en"},
}

RUTA_CHECKPOINT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "Load", "volumen_diario_newsapi.json")


def cargar_api_key():
    key = os.environ.get("NEWSAPI_KEY")
    if key:
        return key.strip()
    ruta_key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "newsapi_key.txt")
    if os.path.exists(ruta_key):
        with open(ruta_key, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def generar_rango_fechas(inicio, fin):
    d0 = datetime.strptime(inicio, "%Y-%m-%d")
    d1 = datetime.strptime(fin, "%Y-%m-%d")
    dias = []
    while d0 <= d1:
        dias.append(d0.strftime("%Y-%m-%d"))
        d0 += timedelta(days=1)
    return dias


def cargar_checkpoint():
    if os.path.exists(RUTA_CHECKPOINT):
        with open(RUTA_CHECKPOINT, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def guardar_checkpoint(resultados):
    os.makedirs(os.path.dirname(RUTA_CHECKPOINT), exist_ok=True)
    with open(RUTA_CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)


def main():
    api_key = cargar_api_key()
    if not api_key:
        print("ERROR: no se encontro newsapi_key.txt ni la variable NEWSAPI_KEY.")
        return

    dias = generar_rango_fechas(FECHA_INICIO, FECHA_FIN)
    resultados = cargar_checkpoint()

    peticiones_esta_corrida = 0

    for fecha in dias:
        if fecha not in resultados:
            resultados[fecha] = {}

        for nombre_query, params_base in QUERIES.items():
            if nombre_query in resultados[fecha]:
                continue  # ya se consulto en una corrida anterior

            params = {
                "apiKey": api_key,
                "q": params_base["q"],
                "language": params_base["language"],
                "from": fecha,
                "to": fecha,
                "pageSize": 1,  # no nos interesan los articulos, solo totalResults
            }

            resp = requests.get(BASE_URL, params=params, timeout=20)

            if resp.status_code == 200:
                total = resp.json().get("totalResults", 0)
                resultados[fecha][nombre_query] = total
                print(f"{fecha} | {nombre_query}: {total}")
            elif resp.status_code == 426:
                # No es limite de cuota: el plan gratuito solo permite buscar
                # articulos del ultimo mes contando desde HOY (ventana movil,
                # no desde la fecha de construccion del corpus original).
                # Este dia especifico quedo fuera de esa ventana -- se
                # documenta como tal y se SIGUE con los demas dias, no se
                # aborta la corrida completa.
                print(f"{fecha} | {nombre_query}: FUERA DE VENTANA DEL PLAN "
                      f"GRATUITO (HTTP 426) -- se documenta como no verificable, "
                      f"se continua con el resto.")
                resultados[fecha][nombre_query] = "fuera_de_ventana_plan_gratuito"
            elif resp.status_code == 429:
                # Este si es limite real de peticiones por dia -- ya no tiene
                # caso seguir intentando, hay que esperar y reanudar despues.
                print(f"\nLIMITE DE PETICIONES DIARIAS ALCANZADO en "
                      f"{fecha}/{nombre_query} (HTTP 429). Guardando progreso "
                      f"y deteniendo. Vuelve a correr el script manana para continuar.")
                guardar_checkpoint(resultados)
                return
            else:
                print(f"{fecha} | {nombre_query}: ERROR {resp.status_code} - "
                      f"{resp.text[:150]}")
                resultados[fecha][nombre_query] = None

            peticiones_esta_corrida += 1
            time.sleep(PAUSA_ENTRE_PETICIONES)

            # Guardado incremental por si se interrumpe manualmente
            if peticiones_esta_corrida % 10 == 0:
                guardar_checkpoint(resultados)

    guardar_checkpoint(resultados)
    print(f"\nCompleto. {peticiones_esta_corrida} peticiones nuevas esta corrida.")
    print(f"Resultado guardado en: {RUTA_CHECKPOINT}")


if __name__ == "__main__":
    main()