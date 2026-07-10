"""
Inspecciona el formulario/control de filtro de temporada completo
(class='auflistung'), incluyendo el botón "Show" y cualquier elemento
<form> asociado, para entender qué interacción hace falta antes de que
la tabla de estadísticas reales se cargue.
"""

from bs4 import BeautifulSoup

with open("debug_pagina_completa.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

tabla_filtro = soup.find("table", class_="auflistung")
print("=== HTML COMPLETO DE LA TABLA DE FILTRO ===")
print(tabla_filtro.prettify() if tabla_filtro else "No encontrada")

print("\n" + "=" * 80)
print("BÚSQUEDA DE <form> EN TODA LA PÁGINA")
print("=" * 80)
formularios = soup.find_all("form")
print(f"Total de formularios: {len(formularios)}")
for i, form in enumerate(formularios):
    print(f"\n--- Form {i} ---")
    print(f"  action: {form.get('action')}")
    print(f"  method: {form.get('method')}")
    print(f"  id: {form.get('id')}")
    print(f"  class: {form.get('class')}")

print("\n" + "=" * 80)
print("BÚSQUEDA DE ELEMENTOS CON id O class QUE CONTENGAN 'season' O 'saison'")
print("=" * 80)
elementos = soup.find_all(attrs={"id": lambda x: x and ("season" in x.lower() or "saison" in x.lower())})
elementos += soup.find_all(attrs={"class": lambda x: x and any("season" in c.lower() or "saison" in c.lower() for c in x)})
for el in elementos[:15]:
    print(f"  <{el.name}> id={el.get('id')} class={el.get('class')}")

print("\n" + "=" * 80)
print("BÚSQUEDA DE DIVS CONTENEDORES PRINCIPALES (donde debería ir la tabla real)")
print("=" * 80)
contenedor_principal = soup.find("div", class_=lambda c: c and "large-8" in c)
if contenedor_principal:
    print("Encontrado div.large-8 (contenedor de contenido principal típico de Transfermarkt)")
    print(f"Longitud de su contenido HTML: {len(str(contenedor_principal))} caracteres")
    print(f"Primeros 800 caracteres:")
    print(str(contenedor_principal)[:800])
else:
    print("No se encontró un contenedor large-8")