"""
Inspecciona debug_innerhtml_js.html (capturado vía JavaScript execute_script,
NO vía Selenium .text) para entender la estructura real del contenido y
por qué el método .text de Selenium no lo detectaba como texto visible.
"""

from bs4 import BeautifulSoup

with open("debug_innerhtml_js.html", encoding="utf-8") as f:
    html = f.read()

print(f"Longitud total: {len(html)} caracteres\n")

soup = BeautifulSoup(html, "lxml")

print("=== TODO EL TEXTO PLANO (sin importar visibilidad) ===")
print(soup.get_text(" | ", strip=True)[:3000])

print("\n\n=== BÚSQUEDA DE ESTILOS 'display:none' O 'visibility:hidden' ===")
elementos_ocultos = soup.find_all(style=lambda s: s and ("display:none" in s.replace(" ", "") or "visibility:hidden" in s.replace(" ", "")))
print(f"Elementos con estilo de ocultamiento inline: {len(elementos_ocultos)}")

print("\n=== ESTRUCTURA DE LAS PRIMERAS FILAS REALES (grid-row) ===")
filas = soup.find_all("div", class_="grid-row")
print(f"Total de div.grid-row en este fragmento: {len(filas)}")
for i, fila in enumerate(filas[:8]):
    print(f"\n--- Fila {i} ---")
    print(f"  class completa: {fila.get('class')}")
    celdas = fila.find_all("div", class_=lambda c: c and "tm-grid__cell" in c)
    for j, celda in enumerate(celdas):
        texto = celda.get_text(strip=True)
        print(f"    celda[{j}] class={celda.get('class')} texto='{texto}'")