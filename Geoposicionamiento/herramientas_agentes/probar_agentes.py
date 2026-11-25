"""Prueba la presentación en Chromium sin cabeza: errores de consola, simulaciones vacías, ajuste a cuatro tamaños,
términos usados antes de definirse y controles sin efecto. Uso: python3 herramientas_agentes/probar_agentes.py [capturas]"""
import json, re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
HTML = (AQUI.parent / "presentaciones" / "agentes_ia.html").resolve()
CAPT = AQUI / "capturas"
TAMANOS = [(1280, 720), (1366, 768), (1440, 900), (1920, 1080)]

def main(capturas=False):
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        errores = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pg.goto(HTML.as_uri()); pg.wait_for_timeout(800)
        n = pg.evaluate("document.querySelectorAll('.lam').length")
        print("láminas:", n)
        # 1. cada lámina: sin errores, sims con contenido, tamaños
        desbordan = {t: [] for t in TAMANOS}
        vacias = []
        textos = []
        for i in range(n):
            pg.evaluate(f"location.hash='#lamina-{i+1}'"); pg.wait_for_timeout(250)
            info = pg.evaluate("""() => { const s=document.querySelector('.lam.on'); return {t: s.querySelector('h2,h1')?.textContent, txt: s.innerText, sims: [...s.querySelectorAll('[data-sim]')].map(e=>[e.dataset.sim, e.innerText.length, e.querySelectorAll('canvas,svg,table,.barra,.msg,.estado').length])} }""")
            textos.append((i + 1, info["t"], info["txt"]))
            for s, ln, k in info["sims"]:
                if ln < 20 and k == 0: vacias.append((i + 1, s))
            for (w, h) in TAMANOS:
                pg.set_viewport_size({"width": w, "height": h}); pg.wait_for_timeout(120)
                z = pg.evaluate("[document.documentElement.scrollHeight, innerHeight, getComputedStyle(document.documentElement).getPropertyValue('--deck-zoom')]")
                if z[0] > z[1] + 2: desbordan[(w, h)].append((i + 1, z[0] - z[1], z[2]))
            pg.set_viewport_size({"width": 1280, "height": 720})
            if capturas:
                CAPT.mkdir(exist_ok=True); pg.wait_for_timeout(150); pg.screenshot(path=str(CAPT / f"l{i+1:02d}.png"))
        print("errores de consola:", len(errores)); [print("  ", e[:200]) for e in errores[:10]]
        print("simulaciones vacías:", vacias)
        for t, l in desbordan.items(): print(f"desbordan a {t[0]}×{t[1]}:", l)
        # 2. términos: primera lámina donde se usa vs primera donde se define (negrita «Término —» o glosario)
        defs = pg.evaluate("""() => [...document.querySelectorAll('.lam')].map((s,i)=>[...s.querySelectorAll('.defs p strong, .problema strong, .gl-cuerpo strong, h2')].map(e=>e.textContent.replace(/\\s*[—–-]\\s*$/,'').trim()).map(t=>[i+1,t]))""")
        defs = [x for grupo in defs for x in grupo]
        terminos = ["token", "contexto", "parámetro", "transformer", "autoatención", "inferencia", "temperatura", "alucinación", "herramienta", "llamada a herramienta", "esquema", "validación", "observación", "iteración",
                    "flujo de trabajo", "agente", "modelo aumentado", "memoria", "recuperación", "rag", "mcp", "ingeniería de contexto", "ventana de contexto", "encadenamiento", "enrutamiento", "paralelización", "react", "orquestador",
                    "tarea", "intento", "calificador", "pass@k", "trayectoria", "inyección", "guardrail", "agregado", "línea base", "unión espacial", "duplicado", "pydantic", "json", "traza", "latencia", "tokens de entrada"]
        avisos = []
        for term in terminos:
            pat = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
            primera_def = next((i for i, t in defs if pat.search(t)), None)
            primer_uso = next((i for i, t, txt in textos if pat.search(txt) and not (t or "").startswith(("Mapa del", "De la pregunta", "El ejercicio"))), None)
            if primer_uso is not None and (primera_def is None or primera_def > primer_uso):
                avisos.append((term, primer_uso, primera_def))
        print("términos usados antes de definirse (término, lámina de uso, lámina de definición):", avisos)
        if "rapido" in sys.argv:
            print("(modo rápido: sin auditoría de controles)"); b.close(); return
        # 3. controles con efecto: mover cada deslizador, cambiar cada select, escribir en cada input de texto, pulsar botones
        sin_efecto = []
        for i in range(n):
            pg.goto(HTML.as_uri() + f"#lamina-{i+1}"); pg.reload(); pg.wait_for_timeout(300)
            ctrls = pg.evaluate("""() => [...document.querySelectorAll('.lam.on .mini input, .lam.on .mini select, .lam.on .mini button, .lam.on .visual input')].map((e,k)=>{e.dataset.k=k;return [k,e.tagName,e.type||'',e.id||e.textContent.trim().slice(0,30)]})""")
            for k, tag, tipo, nombre in ctrls:
                pg.reload(); pg.wait_for_timeout(250); pg.evaluate("[...document.querySelectorAll('.lam.on .mini input, .lam.on .mini select, .lam.on .mini button, .lam.on .visual input')].forEach((e,k)=>e.dataset.k=k)")
                antes = pg.evaluate("document.querySelector('.lam.on').innerText + [...document.querySelectorAll('.lam.on canvas')].map(c=>c.toDataURL().length).join()")
                sel = f".lam.on [data-k='{k}']"
                if tag == "INPUT" and tipo == "range":
                    pg.evaluate(f"(()=>{{const e=document.querySelector(\"{sel}\");e.value=(+e.max+ +e.min)/2===+e.value?e.max:(+e.max+ +e.min)/2;e.dispatchEvent(new Event('input',{{bubbles:true}}))}})()")
                elif tag == "INPUT":
                    pg.evaluate(f"(()=>{{const e=document.querySelector(\"{sel}\");e.value=e.value+' barrio';e.dispatchEvent(new Event('input',{{bubbles:true}}))}})()")
                elif tag == "SELECT":
                    pg.evaluate(f"(()=>{{const e=document.querySelector(\"{sel}\");e.selectedIndex=(e.selectedIndex+1)%e.options.length;e.dispatchEvent(new Event('change',{{bubbles:true}}))}})()")
                else:
                    pg.evaluate(f"document.querySelector(\"{sel}\").click()")
                pg.wait_for_timeout(80)
                pg.on("pageerror", lambda e: None)
                despues = pg.evaluate("document.querySelector('.lam.on').innerText + [...document.querySelectorAll('.lam.on canvas')].map(c=>c.toDataURL().length).join()")
                if antes == despues: sin_efecto.append((i + 1, tag, nombre))
        print("controles sin efecto:", sin_efecto)
        # 4. modo lectura
        pg.evaluate("document.getElementById('deckMode').click()"); pg.wait_for_timeout(600)
        print("modo lectura: láminas visibles =", pg.evaluate("[...document.querySelectorAll('.lam')].filter(s=>s.offsetHeight>0).length"), "errores =", len(errores))
        b.close()
    (AQUI / "informe_prueba.json").write_text(json.dumps({"laminas": n, "errores": errores, "vacias": vacias, "desbordan": {f"{a}x{b}": v for (a, b), v in desbordan.items()}, "terminos": avisos, "sin_efecto": sin_efecto}, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main("capturas" in sys.argv)
