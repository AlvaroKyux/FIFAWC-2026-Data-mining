"""
DIAGNÓSTICO - inspecciona la estructura HTML real de la página de
ranking FIFA de Transfermarkt (statistik/weltrangliste), que parece
contener el listado completo de selecciones nacionales en una sola
página, evitando la navegación confederación -> país -> selección
que ya falló por desactualización del código de referencia.

Guarda esta página primero desde tu navegador como
transfermarkt_ranking_fifa.html en la misma carpeta que ya usamos
(ETL/Extract), y ajusta la ruta abajo si es necesario.
"""

from bs4 import BeautifulSoup

RUTA_HTML = r"C:\Users\SirKy\OneDrive\Documents\PROYECTOS\FIFA-WC-2026\ETL\Extract\transfermarkt_ranking_fifa.html"

with open(RUTA_HTML, encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

# Buscamos TODAS las tablas con class "items" (el patrón típico de Transfermarkt)
tablas = soup.find_all("table", class_="items")
print(f"Tablas con class='items' encontradas: {len(tablas)}\n")

for i, tabla in enumerate(tablas):
    filas = tabla.select("tbody > tr")
    print(f"--- Tabla {i}: {len(filas)} filas ---")
    if filas:
        # Mostramos la primera fila completa de cada tabla para identificar
        # cuál es la que contiene selecciones nacionales
        print(filas[0].prettify()[:1500])
        print("...\n")

print("\n" + "=" * 80)
print("BÚSQUEDA DE LINKS A SELECCIONES NACIONALES (/startseite/verein/)")
print("=" * 80)
links_seleccion = soup.find_all("a", href=lambda h: h and "/startseite/verein/" in h)
print(f"Total de links a páginas de selección/club encontrados: {len(links_seleccion)}\n")
print("Primeros 10:")
for link in links_seleccion[:10]:
    print(f"  texto='{link.get_text(strip=True)}'  href={link.get('href')}  title={link.get('title')}") 