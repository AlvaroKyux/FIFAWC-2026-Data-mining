# -*- coding: utf-8 -*-
"""
verificar_robots_txt.py
--------------------------
Sesion 10 - Web Mining.

Decision documentada (BRAI): en vez de generar scraping nuevo desde cero,
se formaliza la evaluacion etica del scraping YA REALIZADO en la Sesion 2
(Fase de seleccion de datos), sobre Transfermarkt, FBref y worldcup26.ir.
En su momento se resolvieron los bloqueos tecnicos (403, rate-limiting,
Cloudflare) pero nunca se verifico explicitamente si esas fuentes
PERMITIAN el scraping segun su propio robots.txt -- ese es el hueco que
cierra este script.

Intento previo desde el entorno de Claude (documentado, no oculto):
  Se intento verificar los 3 robots.txt directamente desde el sandbox de
  Claude usando web_fetch/web_search. Resultado:
    - transfermarkt.com/robots.txt  -> SITE_BLOCKED (bloqueo del propio
      proveedor de herramientas de Claude, no del sitio).
    - fbref.com/robots.txt          -> rechazado por politica de la
      herramienta (URL no vista previamente en busqueda).
    - worldcup26.ir/robots.txt      -> se confirmo por el README del
      repositorio oficial (GitHub: rezarahiminia/worldcup2026) que existe
      un endpoint /robots.txt y /sitemap.xml, pero no se pudo leer el
      contenido real desde el sandbox.
  Conclusion: la verificacion real solo se puede hacer desde una maquina
  con acceso de red sin restricciones -- por eso este script esta
  disenado para correr LOCALMENTE (VS Code), igual que
  verificar_dias_cero.py en la Sesion 7.

Que hace este script:
  1. Descarga robots.txt de cada fuente.
  2. Extrae las reglas Disallow/Allow para el user-agent '*' (el que
     aplica por defecto a un script sin identificarse como bot conocido).
  3. Contrasta esas reglas contra las RUTAS REALES que se scrapearon en
     la Sesion 2 (documentadas abajo, tomadas literalmente del reporte
     de "Verificacion de fuentes").
  4. Imprime un veredicto por fuente: PERMITIDO / EN ZONA GRIS / VIOLADO.

Uso:
    pip install requests --break-system-packages
    python verificar_robots_txt.py
"""

import requests
from urllib.robotparser import RobotFileParser

# --------------------------------------------------------------------------
# Rutas reales que se scrapearon en la Sesion 2 (tomadas del reporte de
# "Verificacion de fuentes" ya entregado). Si el robots.txt bloquea
# cualquiera de estas rutas para '*', hay que documentarlo como hallazgo,
# no ignorarlo.
# --------------------------------------------------------------------------
FUENTES = {
    "Transfermarkt": {
        "robots_url": "https://www.transfermarkt.co.uk/robots.txt",
        "user_agent_probado": "requests/python (identificado como proyecto academico)",
        "rutas_scrapeadas": [
            "/wettbewerbe/europa",                 # jerarquia de confederaciones
            "/argentinien/startseite/verein/3437",  # ejemplo: pagina de seleccion (Argentina)
        ],
    },
    "FBref": {
        "robots_url": "https://fbref.com/robots.txt",
        "user_agent_probado": "soccerdata (navegador Chrome automatizado)",
        "rutas_scrapeadas": [
            "/en/comps/",       # listado de competiciones
            "/en/schedule/",    # read_schedule() de soccerdata
        ],
    },
    "worldcup26.ir": {
        "robots_url": "https://worldcup26.ir/robots.txt",
        "user_agent_probado": "PowerShell Invoke-RestMethod (API REST, no HTML scraping)",
        "rutas_scrapeadas": [
            "/api/auth/authenticate",
            "/api/teams",
        ],
    },
}


def obtener_robots_txt(url, timeout=10):
    """Descarga el contenido crudo de un robots.txt. Devuelve None si falla."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "FIFA-WC-2026-Grupo0902-Academico/1.0"},
        )
        if resp.status_code == 200:
            return resp.text
        print(f"  [!] {url} respondio con status {resp.status_code}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [!] Error al descargar {url}: {e}")
        return None


def evaluar_fuente(nombre, info):
    print(f"\n{'=' * 70}")
    print(f"FUENTE: {nombre}")
    print(f"{'=' * 70}")
    print(f"User-agent usado en la Sesion 2: {info['user_agent_probado']}")

    contenido = obtener_robots_txt(info["robots_url"])
    if contenido is None:
        print("  -> No se pudo verificar (fuente inaccesible o bloqueada). "
              "Documentar como LIMITACION, no asumir que esta permitido.")
        return {
            "fuente": nombre,
            "verificable": False,
            "veredicto": "NO VERIFICABLE",
        }

    # Guardar copia local del robots.txt como evidencia
    nombre_archivo = f"robots_{nombre.lower().replace('.', '_')}.txt"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"  Copia guardada en: {nombre_archivo}")

    parser = RobotFileParser()
    parser.parse(contenido.splitlines())

    resultados_rutas = {}
    for ruta in info["rutas_scrapeadas"]:
        permitido = parser.can_fetch("*", ruta)
        resultados_rutas[ruta] = permitido
        estado = "PERMITIDO" if permitido else "BLOQUEADO por robots.txt"
        print(f"  Ruta '{ruta}': {estado}")

    todas_permitidas = all(resultados_rutas.values())
    veredicto = "PERMITIDO" if todas_permitidas else "VIOLA robots.txt EN AL MENOS 1 RUTA"

    print(f"  VEREDICTO: {veredicto}")
    return {
        "fuente": nombre,
        "verificable": True,
        "rutas": resultados_rutas,
        "veredicto": veredicto,
    }


def main():
    print("Verificacion de robots.txt - Sesion 10 (Web Mining)")
    print("Contrastando reglas del sitio contra las rutas scrapeadas en Sesion 2\n")

    resultados = []
    for nombre, info in FUENTES.items():
        resultados.append(evaluar_fuente(nombre, info))

    print(f"\n{'=' * 70}")
    print("RESUMEN FINAL")
    print(f"{'=' * 70}")
    for r in resultados:
        print(f"  {r['fuente']:<20} -> {r['veredicto']}")

    print("\nNota BRAI: si una fuente aparece como 'VIOLA robots.txt', esto NO "
          "significa que haya sido ilegal (robots.txt es una convencion "
          "voluntaria, no una ley), pero SI debe documentarse como una "
          "limitacion etica reconocida en el minireporte, tal como se "
          "documentaron los rechazos de FBref por bloqueo tecnico.")


if __name__ == "__main__":
    main()