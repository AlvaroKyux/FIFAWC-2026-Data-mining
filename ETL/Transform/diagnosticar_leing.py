"""
DIAGNÓSTICO - inspecciona la estructura HTML real de la página de
"datos de rendimiento" (leistungsdaten) de un jugador en Transfermarkt,
antes de construir el extractor completo para los 1,248 jugadores.

Guarda la página de Emiliano Martínez como
transfermarkt_leistungsdaten_muestra.html en ETL/Extract y ajusta la
ruta abajo si es necesario.
"""

from bs4 import BeautifulSoup

RUTA_HTML = r"C:\Users\SirKy\OneDrive\Documents\PROYECTOS\FIFA-WC-2026\ETL\Extract\transfermarkt_leistungsdaten_muestra.html"

with open(RUTA_HTML, encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

tablas = soup.find_all("table", class_="items")
print(f"Tablas con class='items' encontradas: {len(tablas)}\n")

for i, tabla in enumerate(tablas):
    filas = tabla.select("tbody > tr")
    print(f"--- Tabla {i}: {len(filas)} filas ---")

    # Mostramos los encabezados de columna de cada tabla, para identificar
    # cuál es la de "rendimiento por competición"
    encabezados = tabla.find("thead")
    if encabezados:
        cols = [th.get_text(strip=True) for th in encabezados.find_all("th")]
        print(f"   Columnas: {cols}")

    if filas:
        print(f"\n   Primera fila completa:")
        print(filas[0].prettify()[:2000])
    print()

print("\n" + "=" * 80)
print("BÚSQUEDA DE CUALQUIER TABLA (sin filtrar por class)")
print("=" * 80)
todas_tablas = soup.find_all("table")
print(f"Total de elementos <table> en la página: {len(todas_tablas)}")
for i, t in enumerate(todas_tablas):
    clases = t.get("class", [])
    filas_t = t.find_all("tr")
    print(f"  Tabla {i}: class={clases}, filas={len(filas_t)}")