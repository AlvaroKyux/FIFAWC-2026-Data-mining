"""
Inspecciona el archivo debug_pagina_completa.html ya guardado por la
prueba anterior, para encontrar la clase EXACTA de la tabla real
(ya confirmamos que existe 1 ocurrencia de '<table' en ese archivo).
"""

from bs4 import BeautifulSoup

with open("debug_pagina_completa.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

tablas = soup.find_all("table")
print(f"Total de tablas encontradas: {len(tablas)}\n")

for i, tabla in enumerate(tablas):
    print(f"--- Tabla {i} ---")
    print(f"  class: {tabla.get('class')}")
    print(f"  id: {tabla.get('id')}")
    filas = tabla.find_all("tr")
    print(f"  filas: {len(filas)}")

    encabezados = tabla.find("thead")
    if encabezados:
        cols = [th.get_text(strip=True) for th in encabezados.find_all("th")]
        print(f"  columnas: {cols}")

    if filas:
        print(f"  primera fila (texto completo): {filas[0].get_text(' | ', strip=True)}")
    print()