"""
Inspecciona el contenido COMPLETO del Web Component
<tm-player-performance-table-new>, donde confirmamos que vive la tabla
real de estadísticas (225,392 caracteres de HTML), para encontrar la
estructura real de filas de datos (probablemente NO es <table class="items">
sino una estructura basada en divs, típica de componentes Svelte).
"""

from bs4 import BeautifulSoup

with open("debug_pagina_completa.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "lxml")

componente = soup.find("tm-player-performance-table-new")
print(f"Componente encontrado: {componente is not None}")

if componente:
    print(f"\nAtributos del componente: {componente.attrs}")

    # Buscamos cualquier tabla DENTRO de este componente específicamente
    tablas_internas = componente.find_all("table")
    print(f"\nTablas <table> dentro del componente: {len(tablas_internas)}")
    for t in tablas_internas:
        print(f"  class={t.get('class')}")

    # Si no hay tablas, busca estructuras de filas basadas en divs (patrón Svelte)
    print(f"\n--- BÚSQUEDA DE FILAS BASADAS EN DIV (patrón típico Svelte) ---")
    posibles_filas = componente.find_all("div", class_=lambda c: c and ("row" in " ".join(c).lower() or "tr" in " ".join(c).lower()))
    print(f"Divs con 'row' o 'tr' en su clase: {len(posibles_filas)}")

    # Mostramos las clases únicas de TODOS los divs dentro del componente,
    # para identificar el patrón real sin adivinar nombres
    print(f"\n--- TODAS LAS CLASES ÚNICAS DE <div> DENTRO DEL COMPONENTE ---")
    clases_unicas = set()
    for div in componente.find_all("div"):
        clases = div.get("class")
        if clases:
            clases_unicas.add(" ".join(clases))
    for c in sorted(clases_unicas):
        print(f"  '{c}'")

    print(f"\n--- TEXTO PLANO COMPLETO DEL COMPONENTE (primeros 3000 caracteres) ---")
    print(componente.get_text(" | ", strip=True)[:3000])