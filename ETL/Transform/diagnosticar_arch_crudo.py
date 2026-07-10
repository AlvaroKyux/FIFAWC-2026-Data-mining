"""
DIAGNÓSTICO BÁSICO - verifica qué hay realmente en el archivo HTML
guardado, antes de seguir asumiendo que el problema es de selectores.
"""

from pathlib import Path

RUTA_HTML = r"C:\Users\SirKy\OneDrive\Documents\PROYECTOS\FIFA-WC-2026\ETL\Extract\transfermarkt_leistungsdaten_muestra.html"

ruta = Path(RUTA_HTML)
print(f"¿Existe el archivo?: {ruta.exists()}")
print(f"Tamaño del archivo: {ruta.stat().st_size if ruta.exists() else 'N/A'} bytes")

with open(RUTA_HTML, encoding="utf-8", errors="replace") as f:
    contenido = f.read()

print(f"\nLongitud del contenido leído: {len(contenido)} caracteres")
print(f"\n--- PRIMEROS 1000 CARACTERES ---")
print(contenido[:1000])
print(f"\n--- ÚLTIMOS 500 CARACTERES ---")
print(contenido[-500:])

# Búsquedas de palabras clave que nos digan qué tipo de página es
print(f"\n--- DIAGNÓSTICO DE CONTENIDO ---")
print(f"Contiene 'Emiliano': {'Emiliano' in contenido}")
print(f"Contiene 'table': {'table' in contenido.lower()}")
print(f"Contiene 'cookie': {'cookie' in contenido.lower()}")
print(f"Contiene '404' o 'not found': {'404' in contenido or 'not found' in contenido.lower()}")
print(f"Contiene 'captcha' o 'blocked' o 'forbidden': {any(p in contenido.lower() for p in ['captcha', 'blocked', 'forbidden'])}")
print(f"Contiene '<script': {'<script' in contenido.lower()}")

# Diagnóstico adicional: ¿la tabla está envuelta en comentarios HTML?
# (patrón visto antes en sitios similares, ej. FBref)
import re

print(f"\n--- BÚSQUEDA DE TABLAS DENTRO DE COMENTARIOS HTML ---")
comentarios = re.findall(r"<!--(.*?)-->", contenido, re.DOTALL)
print(f"Total de comentarios HTML encontrados: {len(comentarios)}")
comentarios_con_tabla = [c for c in comentarios if "<table" in c]
print(f"Comentarios que contienen '<table': {len(comentarios_con_tabla)}")

# Diagnóstico adicional: ¿dónde aparece "Emiliano" exactamente?
print(f"\n--- CONTEXTO ALREDEDOR DE 'Emiliano' ---")
idx = contenido.find("Emiliano")
if idx != -1:
    print(contenido[max(0, idx - 200):idx + 200])

# Diagnóstico adicional: ¿cuántas veces aparece "<table" literal vs solo la palabra "table"?
print(f"\n--- CONTEO DE '<table' literal en el HTML (no solo la palabra) ---")
print(f"Ocurrencias de '<table': {contenido.count('<table')}")
print(f"Ocurrencias de '</table>': {contenido.count('</table>')}")