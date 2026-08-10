#!/usr/bin/env python3
"""
generar_dataset.py
-------------------
Generador de datos sinteticos para el Data Warehouse "Interacciones en Redes
Sociales sobre equipos de futbol - 2023".

Produce el esquema en estrella descrito en la practica:
    DIM_TIEMPO.csv
    DIM_PAIS.csv
    DIM_CIUDAD.csv
    DIM_RED.csv
    DIM_EQUIPO.csv
    FACT_INTERACCIONES.csv

Uso:
    python generar_dataset.py --seed 4587 --registros 3000
"""

import argparse
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta

# --------------------------------------------------------------------------
# 1. Argumentos de linea de comandos
# --------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Generador de Data Warehouse sintetico")
parser.add_argument("--seed", type=int, default=4587, help="Semilla del generador aleatorio")
parser.add_argument("--registros", type=int, default=3000, help="Numero de registros en la tabla de hechos")
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
parser.add_argument("--out", type=str, default=str(SCRIPT_DIR / "datos_csv"), help="Carpeta de salida de los CSV")
args = parser.parse_args()

rng = np.random.default_rng(args.seed)
os.makedirs(args.out, exist_ok=True)

FECHA_GENERACION = date.today().isoformat()

# --------------------------------------------------------------------------
# 2. DIM_PAIS  (continente, region, pais)
# --------------------------------------------------------------------------
paises_data = [
    # continente, region, pais
    ("America", "Norteamerica", "Mexico"),
    ("America", "Norteamerica", "Estados Unidos"),
    ("America", "Norteamerica", "Canada"),
    ("America", "Sudamerica", "Argentina"),
    ("America", "Sudamerica", "Brasil"),
    ("America", "Sudamerica", "Uruguay"),
    ("Europa", "Europa Occidental", "Espana"),
    ("Europa", "Europa Occidental", "Francia"),
    ("Europa", "Europa Occidental", "Inglaterra"),
    ("Europa", "Europa Occidental", "Alemania"),
    ("Europa", "Europa del Sur", "Italia"),
    ("Europa", "Europa del Sur", "Portugal"),
    ("Africa", "Norte de Africa", "Marruecos"),
    ("Asia", "Asia Oriental", "Japon"),
    ("Asia", "Asia Occidental", "Arabia Saudita"),
]
dim_pais = pd.DataFrame(paises_data, columns=["continente", "region", "pais"])
dim_pais.insert(0, "id_pais", range(1, len(dim_pais) + 1))
dim_pais.to_csv(f"{args.out}/DIM_PAIS.csv", index=False)

# --------------------------------------------------------------------------
# 3. DIM_CIUDAD (depende de DIM_PAIS)
# --------------------------------------------------------------------------
ciudades_por_pais = {
    "Mexico": ["Ciudad de Mexico", "Guadalajara", "Monterrey"],
    "Estados Unidos": ["Nueva York", "Los Angeles", "Miami"],
    "Canada": ["Toronto", "Vancouver"],
    "Argentina": ["Buenos Aires", "Cordoba"],
    "Brasil": ["Sao Paulo", "Rio de Janeiro"],
    "Uruguay": ["Montevideo"],
    "Espana": ["Madrid", "Barcelona", "Sevilla"],
    "Francia": ["Paris", "Marsella"],
    "Inglaterra": ["Londres", "Manchester"],
    "Alemania": ["Berlin", "Munich"],
    "Italia": ["Roma", "Milan"],
    "Portugal": ["Lisboa", "Oporto"],
    "Marruecos": ["Casablanca", "Rabat"],
    "Japon": ["Tokio", "Osaka"],
    "Arabia Saudita": ["Riad", "Jeda"],
}
filas_ciudad = []
for _, row in dim_pais.iterrows():
    for ciudad in ciudades_por_pais.get(row["pais"], []):
        filas_ciudad.append((row["id_pais"], row["pais"], ciudad))
dim_ciudad = pd.DataFrame(filas_ciudad, columns=["id_pais", "pais", "ciudad"])
dim_ciudad.insert(0, "id_ciudad", range(1, len(dim_ciudad) + 1))
dim_ciudad.to_csv(f"{args.out}/DIM_CIUDAD.csv", index=False)

# --------------------------------------------------------------------------
# 4. DIM_RED  (tipo, red_social)
# --------------------------------------------------------------------------
redes_data = [
    ("Microblogging", "Twitter"),
    ("Imagen y video corto", "Instagram"),
    ("Video largo", "YouTube"),
    ("Red social generalista", "Facebook"),
    ("Video corto", "TikTok"),
]
dim_red = pd.DataFrame(redes_data, columns=["tipo", "red_social"])
dim_red.insert(0, "id_red", range(1, len(dim_red) + 1))
dim_red.to_csv(f"{args.out}/DIM_RED.csv", index=False)

# --------------------------------------------------------------------------
# 5. DIM_EQUIPO (liga, pais, equipo)
# --------------------------------------------------------------------------
equipos_data = [
    ("Liga MX", "Mexico", "Club America"),
    ("Liga MX", "Mexico", "Chivas Guadalajara"),
    ("Liga MX", "Mexico", "Cruz Azul"),
    ("La Liga", "Espana", "Real Madrid"),
    ("La Liga", "Espana", "FC Barcelona"),
    ("La Liga", "Espana", "Atletico Madrid"),
    ("Premier League", "Inglaterra", "Manchester City"),
    ("Premier League", "Inglaterra", "Liverpool"),
    ("Premier League", "Inglaterra", "Arsenal"),
    ("Serie A", "Italia", "Juventus"),
    ("Serie A", "Italia", "AC Milan"),
    ("Bundesliga", "Alemania", "Bayern Munich"),
    ("Bundesliga", "Alemania", "Borussia Dortmund"),
    ("Ligue 1", "Francia", "Paris Saint-Germain"),
    ("Liga Argentina", "Argentina", "Boca Juniors"),
    ("Liga Argentina", "Argentina", "River Plate"),
    ("Brasileirao", "Brasil", "Flamengo"),
    ("Brasileirao", "Brasil", "Palmeiras"),
    ("Primeira Liga", "Portugal", "Benfica"),
    ("Saudi Pro League", "Arabia Saudita", "Al Nassr"),
]
dim_equipo = pd.DataFrame(equipos_data, columns=["liga", "pais", "equipo"])
dim_equipo.insert(0, "id_equipo", range(1, len(dim_equipo) + 1))
dim_equipo.to_csv(f"{args.out}/DIM_EQUIPO.csv", index=False)

# --------------------------------------------------------------------------
# 6. DIM_TIEMPO (todo el ano 2023, con jerarquia Anio -> Trimestre -> Mes)
# --------------------------------------------------------------------------
inicio = date(2023, 1, 1)
fin = date(2023, 12, 31)
dias = pd.date_range(inicio, fin, freq="D")

dias_semana_es = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]

dim_tiempo = pd.DataFrame({
    "fecha": dias.date,
})
dim_tiempo["anio"] = dias.year
dim_tiempo["trimestre"] = "T" + dias.quarter.astype(str)
dim_tiempo["mes"] = dias.month
dim_tiempo["nombre_mes"] = dias.month_name()
dim_tiempo["dia_semana"] = [dias_semana_es[d] for d in dias.weekday]
dim_tiempo.insert(0, "id_tiempo", range(1, len(dim_tiempo) + 1))
dim_tiempo.to_csv(f"{args.out}/DIM_TIEMPO.csv", index=False)

# --------------------------------------------------------------------------
# 7. FACT_INTERACCIONES
# --------------------------------------------------------------------------
N = args.registros

sentimientos = ["Positivo", "Negativo", "Neutro"]
sentimiento_probs = [0.45, 0.25, 0.30]

hashtags = [
    "#Mundial2026", "#VamosSeleccion", "#FutbolTotal", "#GoleoElEquipo",
    "#DiaDePartido", "#FanaticoDelFutbol", "#RumboAlMundial", "#Campeones",
]

# Damos mas peso a paises/equipos con mayor base de aficionados (Mexico,
# Espana, Argentina, Brasil e Inglaterra) para simular un mercado real,
# en vez de una distribucion uniforme (evita un dataset "de juguete").
pesos_pais = np.ones(len(dim_pais))
paises_top = ["Mexico", "Espana", "Argentina", "Brasil", "Inglaterra"]
for i, p in enumerate(dim_pais["pais"]):
    if p in paises_top:
        pesos_pais[i] = 3.0
pesos_pais = pesos_pais / pesos_pais.sum()

id_pais_muestra = rng.choice(dim_pais["id_pais"], size=N, p=pesos_pais)

# Ciudad coherente con el pais elegido (evita inconsistencias FK)
id_ciudad_muestra = np.empty(N, dtype=int)
ciudad_por_pais_idx = {pid: dim_ciudad[dim_ciudad["id_pais"] == pid]["id_ciudad"].values
                       for pid in dim_pais["id_pais"]}
for i, pid in enumerate(id_pais_muestra):
    opciones = ciudad_por_pais_idx[pid]
    id_ciudad_muestra[i] = rng.choice(opciones)

# Equipo con mayor probabilidad si coincide el pais del aficionado (sesgo realista)
id_equipo_muestra = np.empty(N, dtype=int)
equipo_por_pais_idx = {pid: dim_equipo.merge(dim_pais, on="pais")[
    dim_equipo.merge(dim_pais, on="pais")["id_pais"] == pid]["id_equipo"].values
    for pid in dim_pais["id_pais"]}
todos_los_equipos = dim_equipo["id_equipo"].values
for i, pid in enumerate(id_pais_muestra):
    locales = equipo_por_pais_idx.get(pid, np.array([]))
    if len(locales) > 0 and rng.random() < 0.6:
        id_equipo_muestra[i] = rng.choice(locales)
    else:
        id_equipo_muestra[i] = rng.choice(todos_los_equipos)

# Red social: TikTok/Instagram/Twitter mas usadas que YouTube/Facebook
pesos_red = np.array([0.28, 0.26, 0.12, 0.12, 0.22])  # Twitter, Insta, YouTube, FB, TikTok
id_red_muestra = rng.choice(dim_red["id_red"], size=N, p=pesos_red)

# Tiempo: mas actividad en fin de semana (dias de partido) -> sesgo por dia_semana
pesos_dia = dim_tiempo["dia_semana"].map({
    "Lunes": 0.10, "Martes": 0.08, "Miercoles": 0.10, "Jueves": 0.10,
    "Viernes": 0.14, "Sabado": 0.24, "Domingo": 0.24,
}).values
pesos_dia = pesos_dia / pesos_dia.sum()
id_tiempo_muestra = rng.choice(dim_tiempo["id_tiempo"], size=N, p=pesos_dia)

sentimiento_muestra = rng.choice(sentimientos, size=N, p=sentimiento_probs)
hashtag_muestra = rng.choice(hashtags, size=N, p=[0.22, 0.16, 0.14, 0.12, 0.10, 0.10, 0.09, 0.07])

# Medidas numericas (distribuciones asimetricas tipo redes sociales: lognormal)
interacciones = rng.lognormal(mean=5.2, sigma=1.1, size=N).astype(int) + 1
alcance = (interacciones * rng.uniform(8, 15, size=N)).astype(int)
compartidos = (interacciones * rng.uniform(0.05, 0.25, size=N)).astype(int)
respuestas = (interacciones * rng.uniform(0.02, 0.18, size=N)).astype(int)

fact = pd.DataFrame({
    "id_tiempo": id_tiempo_muestra,
    "id_pais": id_pais_muestra,
    "id_ciudad": id_ciudad_muestra,
    "id_red": id_red_muestra,
    "id_equipo": id_equipo_muestra,
    "sentimiento": sentimiento_muestra,
    "hashtag": hashtag_muestra,
    "interacciones": interacciones,
    "alcance": alcance,
    "compartidos": compartidos,
    "respuestas": respuestas,
})
fact.insert(0, "id_fact", range(1, len(fact) + 1))
fact["ratio_compartidos"] = (fact["compartidos"] / fact["interacciones"]).round(4)

fact.to_csv(f"{args.out}/FACT_INTERACCIONES.csv", index=False)

# --------------------------------------------------------------------------
# 8. Resumen de ejecucion
# --------------------------------------------------------------------------
print("=" * 60)
print("GENERACION DE DATA WAREHOUSE SINTETICO COMPLETADA")
print("=" * 60)
print(f"Semilla utilizada        : {args.seed}")
print(f"Registros solicitados    : {args.registros}")
print(f"Fecha de generacion      : {FECHA_GENERACION}")
print(f"Carpeta de salida        : {os.path.abspath(args.out)}")
print("-" * 60)
for nombre, df in [
    ("DIM_TIEMPO", dim_tiempo), ("DIM_PAIS", dim_pais),
    ("DIM_CIUDAD", dim_ciudad), ("DIM_RED", dim_red),
    ("DIM_EQUIPO", dim_equipo), ("FACT_INTERACCIONES", fact),
]:
    print(f"  {nombre:<22} {len(df):>6} registros")
print("=" * 60)
