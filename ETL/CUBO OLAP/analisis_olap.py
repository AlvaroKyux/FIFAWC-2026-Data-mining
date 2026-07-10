#!/usr/bin/env python3
"""
analisis_olap.py
-----------------
Explota el Data Warehouse generado por generar_dataset.py aplicando
operaciones OLAP (Roll-up, Drill-down, Slice, Dice, Pivot) mediante pandas,
ya que no se dispone de un motor MOLAP (Mondrian/SSAS) en este entorno.
Cada consulta pandas es funcionalmente equivalente a la consulta MDX
mostrada en el documento.
"""
import pandas as pd

DATA = "../data"

dim_tiempo = pd.read_csv(f"{DATA}/DIM_TIEMPO.csv")
dim_pais = pd.read_csv(f"{DATA}/DIM_PAIS.csv")
dim_ciudad = pd.read_csv(f"{DATA}/DIM_CIUDAD.csv")
dim_red = pd.read_csv(f"{DATA}/DIM_RED.csv")
dim_equipo = pd.read_csv(f"{DATA}/DIM_EQUIPO.csv")
fact = pd.read_csv(f"{DATA}/FACT_INTERACCIONES.csv")

# Vista desnormalizada completa (equivalente al cubo materializado)
cubo = (fact
        .merge(dim_tiempo, on="id_tiempo")
        .merge(dim_pais, on="id_pais")
        .merge(dim_ciudad[["id_ciudad", "ciudad"]], on="id_ciudad")
        .merge(dim_red, on="id_red")
        .merge(dim_equipo[["id_equipo", "liga", "equipo"]], on="id_equipo"))

def linea():
    print("-" * 70)

print("=" * 70)
print("4. EXPLORACION DEL DATA WAREHOUSE")
print("=" * 70)
print(f"Total de interacciones : {fact['interacciones'].sum():,}")
print(f"Promedio por registro  : {fact['interacciones'].mean():.2f}")
print(f"Maximo de interacciones: {fact['interacciones'].max():,}")
print(f"Minimo de interacciones: {fact['interacciones'].min():,}")
print(f"Sentimiento mas comun  : {fact['sentimiento'].mode()[0]} "
      f"({(fact['sentimiento'].value_counts(normalize=True).iloc[0]*100):.1f}%)")
red_top = cubo.groupby('red_social')['interacciones'].sum().idxmax()
print(f"Red con mas interacciones: {red_top}")

linea()
print("7.1 ROLL-UP: Total interacciones por Trimestre (2023)")
linea()
rollup = cubo.groupby("trimestre")["interacciones"].sum().reindex(["T1","T2","T3","T4"])
print(rollup)

linea()
print("7.2 DRILL-DOWN: Total interacciones por Red Social dentro de 'Microblogging/Imagen y video corto'")
linea()
drill = cubo[cubo["tipo"].isin(["Microblogging"])].groupby("red_social")["interacciones"].sum()
print(drill)
drill_full = cubo.groupby(["tipo","red_social"])["interacciones"].sum()
print("\n(Todas las redes por tipo, para referencia completa):")
print(drill_full)

linea()
print("7.3 SLICE: Total interacciones por Equipo -- Pais = Espana")
linea()
slice_ = cubo[cubo["pais"] == "Espana"].groupby("equipo")["interacciones"].sum().sort_values(ascending=False)
print(slice_)

linea()
print("7.4 DICE: Total interacciones por Equipo -- Pais = Mexico AND Trimestre = T4")
linea()
dice_ = cubo[(cubo["pais"] == "Mexico") & (cubo["trimestre"] == "T4")].groupby("equipo")["interacciones"].sum().sort_values(ascending=False)
print(dice_)

linea()
print("7.5 PIVOT: Pais x Red Social (Total interacciones), paises seleccionados")
linea()
pivot = cubo[cubo["pais"].isin(["Espana","Mexico","Argentina"])].pivot_table(
    index="pais", columns="red_social", values="interacciones", aggfunc="sum", fill_value=0)
print(pivot)

linea()
print("8. CONSULTAS DE NEGOCIO")
linea()

print("\nP1. Equipo con mayor interaccion total:")
p1 = cubo.groupby("equipo")["interacciones"].sum().sort_values(ascending=False)
print(p1.head(5))

print("\nP2. Pais con mas publicaciones (conteo de registros):")
p2 = cubo.groupby("pais").size().sort_values(ascending=False)
print(p2.head(5))

print("\nP3. Red social con mayor numero de interacciones:")
p3 = cubo.groupby("red_social")["interacciones"].sum().sort_values(ascending=False)
print(p3)

print("\nP4. Dia de la semana con mayor actividad (conteo de publicaciones):")
p4 = cubo.groupby("dia_semana").size().sort_values(ascending=False)
print(p4)

print("\nP5. Sentimiento predominante:")
p5 = cubo["sentimiento"].value_counts()
print(p5)

print("\nP6. Combinacion Pais-RedSocial con mayor interaccion:")
p6 = cubo.groupby(["pais","red_social"])["interacciones"].sum().sort_values(ascending=False)
print(p6.head(5))

print("\nP7. Hashtag mas utilizado (conteo de publicaciones):")
p7 = cubo["hashtag"].value_counts()
print(p7)

print("\nP8. Ciudad con mas publicaciones:")
p8 = cubo.groupby("ciudad").size().sort_values(ascending=False)
print(p8.head(5))
