# Sesión 10 — Web Mining: Checklist de Confiabilidad y Ética de Fuentes

## Decisión metodológica (BRAI)

En lugar de generar minería web nueva desde cero, se formaliza y audita el
scraping ya realizado en la Sesión 2 (Fase de selección de datos) sobre
Transfermarkt, FBref y worldcup26.ir, agregando el único punto que faltó
resolver entonces: la verificación explícita de `robots.txt`.

## Intento de verificación desde el entorno de Claude

Antes de entregarles el script para correr localmente, se intentó verificar
los 3 `robots.txt` directamente desde las herramientas de Claude. Resultado,
documentado con transparencia (regla BRAI de reportar limitaciones):

| Fuente | Resultado del intento | Causa |
|---|---|---|
| Transfermarkt | `SITE_BLOCKED` | Bloqueo del proveedor de herramientas de Claude sobre ese dominio, no del sitio en sí |
| FBref | Rechazado | Política de la herramienta: solo permite fetch de URLs ya vistas en una búsqueda previa |
| worldcup26.ir | Confirmado que existe `/robots.txt` (vía README del repo oficial en GitHub), pero no se pudo leer el contenido | Misma restricción de herramienta |

**Conclusión:** la verificación real requiere una máquina con acceso de red
sin restricciones — exactamente el mismo patrón que ya usaron en la Sesión 7
con `verificar_dias_cero.py` (Claude no puede correrlo, el equipo sí). Por
eso el script `verificar_robots_txt.py` está diseñado para correr en VS Code,
no en este entorno.

## Checklist de ética de scraping (resultados reales, corrido 16/ago/2026)

| Criterio | Transfermarkt | FBref | worldcup26.ir |
|---|---|---|---|
| ¿`robots.txt` permite las rutas usadas? | ✅ **PERMITIDO** — ambas rutas probadas (`/wettbewerbe/europa`, `/argentinien/startseite/verein/3437`) autorizadas para `*` | ⚠️ **NO VERIFICABLE** — el propio `robots.txt` respondió HTTP 403 | ✅ **PERMITIDO** — ambas rutas de API probadas autorizadas para `*` |
| ¿Se identificó el proyecto en el User-Agent? | ✅ Sí (headers de navegador + script propio) | ⚠️ Parcial (soccerdata usa navegador automatizado, no un UA descriptivo) | ✅ Sí (uso de API oficial documentada, con registro de usuario) |
| ¿Se respetó un ritmo de peticiones razonable? | ✅ Sí (pausas de 5s tras detectar bloqueo dinámico) | N/A (rechazado por bloqueo estructural antes de escalar) | ✅ Sí (bajo volumen, 48 equipos en pocas llamadas) |
| ¿Se accedió solo a datos públicos, sin login de terceros? | ✅ Sí | ✅ Sí (intento) | ⚠️ Requiere registro propio del equipo (correo/contraseña del proyecto) |
| ¿Se extrajeron datos personales sensibles? | ❌ No (solo datos deportivos públicos) | ❌ No | ❌ No |

## Hallazgo BRAI de esta sesión

**El propio `robots.txt` de FBref devolvió HTTP 403**, no solo las páginas de
datos que ya sabían bloqueadas desde la Sesión 2. Esto es evidencia adicional
(no solo teórica) de que el bloqueo de FBref es un filtro de "fingerprint" de
conexión a nivel de red — activo incluso antes de que el servidor evalúe qué
recurso se está pidiendo, ni siquiera un archivo de texto plano diseñado para
ser públicamente legible por cualquier robot. Refuerza la decisión ya tomada
en Sesión 2 de descartar FBref por bloqueo estructural, y añade evidencia de
que no es un problema de qué ruta se pide, sino de quién la pide.

**Conclusión ética final:** de las 3 fuentes, 2 (Transfermarkt y worldcup26.ir)
tienen scraping/consumo de API **explícitamente permitido** por robots.txt en
las rutas exactas que usaron. FBref queda como **no verificable por bloqueo
total**, consistente con — y reforzando — la decisión de rechazo ya tomada
con evidencia en la Sesión 2. No hay ninguna violación confirmada de
robots.txt en las fuentes que sí se usaron en el proyecto final.

## Entregables de la Sesión 10

- Video TikTok 10: *"¿Qué fuentes son confiables y cuáles no?"* — guion:
  resumen de las 4 fuentes ya evaluadas en Sesión 2 + el hallazgo nuevo de
  robots.txt (una vez que corran el script).
- Este checklist (completado).
- Evidencia técnica: `verificar_robots_txt.py` + los `robots_*.txt`
  descargados como copia local (el script los guarda automáticamente).
