# Herramientas de «Agentes de inteligencia artificial aplicados a la ciencia de datos geoespaciales»

Todo se ejecuta desde `Geoposicionamiento/` con el `.venv` del repositorio.

## Cadena completa (cuatro pasos)

1. **Clave de Groq** (una vez): copiar `.pruebas.ejemplo` como `.pruebas` en `Geoposicionamiento/` y poner la clave (`GROQ_API_KEY=gsk_...`). `.pruebas` está en `.gitignore`: nunca entra al repositorio; la clave tampoco aparece en el cuaderno ni en sus salidas. Conviene crearla en console.groq.com con fecha de vencimiento y revocarla al terminar. Sin clave, el cuaderno corre con el modelo simulado y lo rotula así en todas las salidas.
2. **Ejecutar el cuaderno** (escribe `herramientas_agentes/resultados_agentes.json`, `trazas.json` y `grafos.json`; necesita `langgraph`, `langchain-core`, `langchain-groq`, `groq`, `pydantic` en el `.venv`):
   `../.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 agentes_geoespaciales.ipynb`
   Con Groq: 4 tareas × 2 modelos × 5 intentos + corridas de inyección y memoria ≈ 50 llamadas por modelo, unos 10 minutos con la cuota gratuita.
3. **Construir la presentación** (solo biblioteca estándar): `python3 herramientas_agentes/construir_agentes.py` → `presentaciones/agentes_ia.html`.
4. **Probar** (Chromium sin cabeza; `pip install playwright && playwright install chromium`): `python3 herramientas_agentes/probar_agentes.py capturas` → errores de consola, simulaciones vacías, desbordes en 1280×720 / 1366×768 / 1440×900 / 1920×1080, términos usados antes de definirse y controles sin efecto. Informe en `informe_prueba.json`, capturas en `capturas/`.

## Archivos

| Archivo | Qué es |
|---|---|
| `crear_notebook.py` | Genera `agentes_geoespaciales.ipynb` sin salidas (fuente única del cuaderno). |
| `verificar_datos.py` → `verificacion_datos.json` | Inspección inicial de las capas y cifras de referencia (sesión del 25‑nov‑2026). |
| `laminas_agentes.py` | Contenido de las 56 láminas: acto, título = término, «El problema —», párrafos, figura, imagen externa (`img`) o simulación, términos, fuente. |
| `img/` | Figuras externas incrustadas con atribución: Google ML Crash Course (CC BY 4.0), Anthropic «Building effective agents», OpenAI «A practical guide to building agents», modelcontextprotocol.io (decisión del docente, 25-nov-2026: figuras de las fuentes oficiales citadas, con su pie). El constructor recorta los márgenes blancos al incrustarlas. |
| `grafos.json` | Los grafos de LangGraph (`get_graph().to_json()` y Mermaid) del agente y de los cinco patrones; la presentación los dibuja y anima con las trazas reales (`flujos` en `sims_agentes.js`). |
| `figuras_agentes.py` | Esquemas propios en SVG (paleta de la página). |
| `sims_agentes.js` | Simulaciones del navegador: flujos animados sobre los grafos de LangGraph, BPE y trigramas entrenados con el texto de la presentación, validación contra el esquema real, mapas con los 724 cruces y los 332 polígonos simplificados, trazas, TF‑IDF, enrutador, pass@k, tablas del cuaderno. |
| `geometria_web.json` | Cruces (coordenadas EPSG:9377 relativas al origen) y barrios simplificados a 25 m para el navegador. |
| `construir_agentes.py` | Ensambla el HTML (CSS, navegación por láminas, índice, modo lectura, ajuste a pantalla). |
| `probar_agentes.py` | Auditoría automática (ver paso 4). |
| `resultados_agentes.json`, `trazas.json`, `memoria_agente.json` | Salidas del cuaderno; la presentación toma de aquí todas sus cifras y trazas. |

## Reglas que sigue el material

Una lámina, un concepto; título = término; «El problema —» abre; definición solo con palabras ya definidas; figura o simulación que calcula de verdad; «En el ejercicio —» con la cifra real; fuente oficial con sección al pie; «Términos de esta lámina» en las que lo necesitan; redacción impersonal; un solo ejercicio en toda la presentación. Las cifras de las láminas nunca se escriben a mano: salen de `resultados_agentes.json`.
