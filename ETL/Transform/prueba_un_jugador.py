"""
PRUEBA CON UN SOLO JUGADOR antes de lanzar la corrida completa de 1,248.

Imprime la tabla completa fila por fila con TODOS los textos de celda
(no solo los índices que asumimos), para poder verificar/corregir el
mapeo de columnas antes de comprometer 3-4 horas de extracción.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

opciones = Options()
opciones.add_argument("--headless=new")
opciones.add_argument("--disable-gpu")
opciones.add_argument("--no-sandbox")
opciones.add_argument("--window-size=1920,1080")
opciones.add_argument(
    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

driver = webdriver.Chrome(options=opciones)

try:
    url = "https://www.transfermarkt.co.uk/emiliano-martinez/leistungsdaten/spieler/111873"
    print(f"Cargando: {url}")
    driver.get(url)

    print(f"Título de la página cargada: '{driver.title}'")
    print(f"URL actual (tras posibles redirecciones): {driver.current_url}")

    # HALLAZGO CONFIRMADO: Transfermarkt muestra un modal de consentimiento
    # de cookies/privacidad ("Welcome! How would you like to use
    # Transfermarkt?") que bloquea la inicialización completa de la página
    # hasta que se acepta. Hay que cerrarlo ANTES de esperar la tabla.
    try:
        boton_aceptar = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        boton_aceptar.click()
        print("✅ Modal de cookies cerrado (clic en 'Accept & continue').")
        time.sleep(1)
    except Exception:
        print("ℹ️ No apareció modal de cookies (o ya estaba cerrado). Continuando...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tm-player-performance-table-new"))
        )
        print("✅ Componente tm-player-performance-table-new detectado.\n")
    except Exception as e:
        print(f"\n⚠️ TIMEOUT esperando el componente. Diagnosticando...")
        driver.save_screenshot("debug_screenshot.png")
        with open("debug_pagina_completa.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        raise SystemExit(1)

    # Espera adicional más generosa: el componente puede existir en el DOM
    # antes de que su contenido de texto termine de poblarse (hallazgo de
    # la corrida anterior: 80 filas detectadas pero todas con celdas vacías).
    print("Esperando contenido real dentro del componente (hasta 10s)...")
    contenido_poblado = False
    for intento in range(20):
        componente = driver.find_element(By.CSS_SELECTOR, "tm-player-performance-table-new")
        texto_actual = componente.text.strip()
        if texto_actual and "Premier League" in texto_actual or len(texto_actual) > 100:
            contenido_poblado = True
            print(f"   Contenido detectado tras {intento * 0.5:.1f}s de espera.")
            break
        time.sleep(0.5)

    if not contenido_poblado:
        print("⚠️ El contenido no se pobló tras 10s de espera adicional.")

        # Diagnóstico de Shadow DOM: verificar si el componente encapsula
        # su contenido en un shadow root nativo, lo cual explicaría por
        # qué .text y find_elements normales no encuentran nada útil.
        print("\n--- DIAGNÓSTICO DE SHADOW DOM ---")
        tiene_shadow_root = driver.execute_script(
            "return arguments[0].shadowRoot !== null", componente
        )
        print(f"¿El componente tiene shadowRoot?: {tiene_shadow_root}")

        if tiene_shadow_root:
            html_shadow = driver.execute_script(
                "return arguments[0].shadowRoot.innerHTML", componente
            )
            print(f"Longitud del HTML dentro del shadow root: {len(html_shadow)} caracteres")
            with open("debug_shadow_dom.html", "w", encoding="utf-8") as f:
                f.write(html_shadow)
            print("📄 Contenido del shadow root guardado en 'debug_shadow_dom.html'")
        else:
            # Si no es shadow DOM, probamos leer el innerHTML normal vía JS
            html_normal = driver.execute_script(
                "return arguments[0].innerHTML", componente
            )
            print(f"Longitud del innerHTML normal (vía JS): {len(html_normal)} caracteres")
            with open("debug_innerhtml_js.html", "w", encoding="utf-8") as f:
                f.write(html_normal)
            print("📄 innerHTML guardado en 'debug_innerhtml_js.html'")

        driver.save_screenshot("debug_componente.png")
        print("📸 Screenshot de página completa guardado en 'debug_componente.png'")
        raise SystemExit(1)

    print(f"\n=== TEXTO COMPLETO DEL COMPONENTE ===")
    componente = driver.find_element(By.CSS_SELECTOR, "tm-player-performance-table-new")
    print(componente.text)

    print(f"\n=== FILAS DENTRO DEL COMPONENTE ESPECÍFICAMENTE (no toda la página) ===")
    filas_grid = componente.find_elements(By.CSS_SELECTOR, "div.grid-row")
    print(f"Total de filas dentro del componente: {len(filas_grid)}\n")

    for i, fila in enumerate(filas_grid):
        celdas = fila.find_elements(By.CSS_SELECTOR, "div.tm-grid__cell")
        textos = [c.text.strip() for c in celdas]
        if any(textos):  # solo mostramos filas que sí tienen contenido
            print(f"--- Fila {i} ({len(celdas)} celdas) ---")
            print(f"  {textos}")
            print()

finally:
    driver.quit()