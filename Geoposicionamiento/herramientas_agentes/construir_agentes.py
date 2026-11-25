"""Construye presentaciones/agentes_ia.html (un solo archivo) a partir de laminas_agentes.py, figuras_agentes.py, sims_agentes.js,
resultados_agentes.json, trazas.json y geometria_web.json. Solo biblioteca estándar.
Uso: python3 herramientas_agentes/construir_agentes.py  (desde Geoposicionamiento/)"""
import json, re, html, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import laminas_agentes as LA
import figuras_agentes as FG

RES = json.loads((AQUI / "resultados_agentes.json").read_text())
TRZ = json.loads((AQUI / "trazas.json").read_text())
GEO = json.loads((AQUI / "geometria_web.json").read_text())
GRAFOS = json.loads((AQUI / "grafos.json").read_text())
IMG = AQUI / "img"
SALIDA = AQUI.parent / "presentaciones" / "agentes_ia.html"

def fmt(n):
    return f"{n:,}".replace(",", " ")

ref = RES["referencia"]
R = {"p1_barrio": ref["p1"]["barrio"], "p1_cruces": ref["p1"]["cruces"], "p1_asignados": ref["p1"]["asignados"],
     "p2_id": next(x for x in ref["p2"] if x["campo"] == "id_cruce")["a 300 m"], "p2_obj": next(x for x in ref["p2"] if x["campo"] == "OBJECTID")["a 300 m"],
     "p3_barrio": ref["p3"]["barrio"], "p3_hurtos": ref["p3"]["hurtos"], "p3_dup": ref["p3"]["con_duplicados"],
     "sin_coord": fmt(ref["calidad_hurtos"]["sin coordenadas"]), "dup": fmt(ref["calidad_hurtos"]["duplicados exactos"]), "fuera_rango": ref["calidad_hurtos"]["longitud fuera de rango"]}
LAMS = LA.laminas(R)
modelos_txt = " y ".join(m.split("/")[1] for m in RES["modelos"])
for L in LAMS:
    L["s"] = L["s"].replace("{modelos}", modelos_txt).replace("{fecha}", RES["fecha"] if RES["modo"] != "simulado" else "corridas pendientes (modo simulado)")

# ------------------------------------------------------------------ bloques de contenido real
def code_block(texto, lang=""):
    return f'<pre class="codigo"><code>{html.escape(texto)}</code></pre>'

def primera_corrida(tarea, correcta=True):
    c = [x for x in TRZ["corridas"] if x["tarea"] == tarea]
    ok = [x for x in c if x["correcto"]]
    return (ok or c)[0] if c else None

def bloque_herramienta_json():
    h = next(x for x in RES["herramientas"] if x["function"]["name"] == "cruces_cercanos")
    f = h["function"]; props = f["parameters"]["properties"]
    lineas = ['{"type": "function",', ' "function": {', f'  "name": "{f["name"]}",', f'  "description": "{f["description"]}",', '  "parameters": {"type": "object", "properties": {']
    for k, v in props.items():
        lineas.append(f'    "{k}": ' + json.dumps(v, ensure_ascii=False) + ",")
    lineas[-1] = lineas[-1].rstrip(",")
    lineas += ['   }, "required": ' + json.dumps(f["parameters"].get("required", [])) + "}", " }", "}"]
    return code_block("\n".join(lineas))

def bloque_tool_call():
    t = primera_corrida("p1")
    paso = next(p for p in t["pasos"] if p["tipo"] == "modelo" and p["tool_calls"])
    tc = paso["tool_calls"][0]
    txt = json.dumps({"role": "assistant", "content": paso["contenido"], "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": tc["arguments"]}}]}, ensure_ascii=False, indent=1)
    nota = "(modelo simulado del cuaderno; se reemplaza por la llamada real al correr con Groq)" if t["simulado"] else f"({t['modelo']}, intento {t['intento']}; leyó {paso['tokens_entrada']} tokens y escribió {paso['tokens_salida']} en {str(paso['latencia_s']).replace('.', ',')} s)"
    return code_block(txt) + f'<p class="nota">Lo que devolvió el modelo a la pregunta 1 {nota}. El programa aún no ha ejecutado nada.</p>'

def bloque_mensajes_p1():
    t = primera_corrida("p1")
    ms = [{"role": "system", "content": RES["instrucciones"]}, {"role": "user", "content": t["pregunta"]}]
    for p in t["pasos"]:
        if p["tipo"] == "modelo":
            ms.append({"role": "assistant", "content": p["contenido"], "tool_calls": [f"{c['name']}({c['arguments']})" for c in p["tool_calls"]]})
        else:
            ms.append({"role": "tool", "name": p["name"], "content": json.dumps(p["resultado"], ensure_ascii=False)})
    rol = {"system": "sistema", "user": "usuario", "assistant": "modelo", "tool": "herramienta"}
    out = '<div class="msgs">'
    for m in ms:
        cuerpo = html.escape(m.get("content") or "")
        if m["role"] == "assistant" and m["tool_calls"]:
            cuerpo = "".join(f"<code>{html.escape(c)}</code>" for c in m["tool_calls"]) + (("<br>" + cuerpo) if cuerpo else "")
        out += f'<div class="msg msg-{m["role"]}"><span>{rol[m["role"]]}</span><div>{cuerpo}</div></div>'
    nota = "Corrida del modelo simulado; se reemplaza por la real al correr con Groq." if t["simulado"] else f"Corrida real: {t['modelo']}, intento {t['intento']}, {t['iteraciones']} iteraciones."
    return out + f'</div><p class="nota">{nota}</p>'

def bloque_resultado_p3():
    t = primera_corrida("p3")
    r = next((p["resultado"] for p in t["pasos"] if p["tipo"] == "herramienta" and p["name"] == "hurtos_por_barrio"), None)
    if r is None:
        r = {"aviso": "en esta corrida el modelo no llamó a hurtos_por_barrio"}
    return code_block(json.dumps(r, ensure_ascii=False, indent=1)) + '<p class="nota">Unas 60 palabras en lugar de 2 513 filas: el modelo recibe la cifra, la regla y las exclusiones, y puede nombrarlas en la respuesta.</p>'

def bloque_tabla_patrones():
    filas = [("P1 ¿Qué barrio tiene más cruces?", "encadenamiento (interpretar → contar → redactar)", "el camino es siempre el mismo"),
             ("P2 ¿Cuántos cruces a 300 m del cruce 125?", "agente (una herramienta, con posible segunda llamada)", "el modelo debe decidir qué campo usar y decirlo; un evaluador–optimizador lo reforzaría"),
             ("P3 ¿Barrio con más hurtos en 2022?", "agente con resultado estructurado", "depende de lo que devuelva la herramienta (exclusiones, aviso de periodo)"),
             ("P4 ¿Accidentes cerca del cruce 125?", "enrutamiento a «no respondible» o agente con listar_capas", "la respuesta correcta es no responder; cualquier patrón debe permitirlo"),
             ("«¿Hurtos cerca del cruce 125?» (no está en el ejercicio)", "agente con dos herramientas encadenadas por el modelo", "cruza dos capas; antes de un orquestador, probar si un agente solo lo resuelve")]
    out = '<table class="tabla"><thead><tr><th>pregunta</th><th>patrón mínimo</th><th>por qué</th></tr></thead><tbody>'
    out += "".join(f"<tr><td>{html.escape(a)}</td><td><b>{html.escape(b)}</b></td><td>{html.escape(c)}</td></tr>" for a, b, c in filas)
    return out + "</tbody></table>"

def bloque_tabla_criterios():
    out = '<table class="tabla"><thead><tr><th>tarea</th><th>pregunta</th><th>criterio en código</th><th>mira</th></tr></thead><tbody>'
    mira = {"p1": "respuesta", "p2": "respuesta y trayectoria", "p3": "respuesta", "p4": "respuesta"}
    for k, crit in RES["casos"].items():
        out += f"<tr><td><b>{k.upper()}</b></td><td>{html.escape(RES['preguntas'][k])}</td><td>{html.escape(crit)}</td><td>{mira[k]}</td></tr>"
    return out + "</tbody></table>"

def bloque_codigo_herramientas():
    cod = '''from langchain_core.tools import StructuredTool

class ArgsCrucesCercanos(BaseModel):
    identificador: int = Field(description="Número del cruce")
    campo: Literal["id_cruce", "OBJECTID"] = Field("id_cruce", description="Campo en el que se busca el número; la capa tiene ambos y no coinciden")
    radio_m: float = Field(gt=0, le=5000, description="Radio de búsqueda en metros (el plano es EPSG:9377, en metros)")

def cruces_cercanos(identificador, campo="id_cruce", radio_m=300):
    sel = cruces[cruces[campo] == identificador]
    if len(sel) != 1:
        return {"error": f"no hay exactamente un cruce con {campo} = {identificador}"}
    d = cruces.geometry.distance(sel.geometry.iloc[0])
    return {"campo": campo, "identificador": identificador, "radio_m": radio_m,
            "cruces_a_esa_distancia_o_menos": int(((d <= radio_m) & (d > 0)).sum()),
            "excluye_el_propio_cruce": True, "barrio_del_cruce": str(union.loc[sel.index[0], "nombre"])}

def herramienta(nombre, funcion, args):   # descripción y esquema Pydantic: lo que ve el modelo; la función corre en el programa
    return StructuredTool.from_function(func=lambda **kw: json.dumps(funcion(**kw), ensure_ascii=False),
                                        name=nombre, description=DESCRIPCIONES[nombre], args_schema=args)

HERRAMIENTAS = [herramienta(n, f, a) for n, (a, f) in FUNCIONES.items()]'''
    return code_block(cod)

def bloque_codigo_ciclo():
    cod = '''from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

def construir_agente(llm, herramientas, instrucciones=INSTRUCCIONES):
    modelo = llm.bind_tools(herramientas)                          # el modelo conoce los esquemas
    def nodo_modelo(estado):
        return {"messages": [modelo.invoke([SystemMessage(instrucciones)] + estado["messages"])]}
    g = StateGraph(MessagesState)                                  # el estado es la lista de mensajes
    g.add_node("modelo", nodo_modelo)
    g.add_node("herramientas", ToolNode(herramientas, handle_tool_errors=True))   # valida y ejecuta; un error vuelve como observación
    g.add_edge(START, "modelo")
    g.add_conditional_edges("modelo", tools_condition, {"tools": "herramientas", END: END})   # ¿pidió herramientas?
    g.add_edge("herramientas", "modelo")                           # la observación vuelve al modelo
    return g.compile()

agente = construir_agente(ChatGroq(model="openai/gpt-oss-20b", temperature=0.2), HERRAMIENTAS)
salida = agente.invoke({"messages": [HumanMessage(pregunta)]}, config={"recursion_limit": 13})   # tope: 6 iteraciones'''
    return code_block(cod)

BLOQUES = {"herramienta_json": bloque_herramienta_json, "tool_call": bloque_tool_call, "mensajes_p1": bloque_mensajes_p1, "resultado_p3": bloque_resultado_p3,
           "tabla_patrones": bloque_tabla_patrones, "tabla_criterios": bloque_tabla_criterios, "codigo_herramientas": bloque_codigo_herramientas, "codigo_ciclo": bloque_codigo_ciclo}

FG.FIGURAS["mapa_acto_4"] = lambda: FG.fig_mapa_acto([("encadenamiento", "pasos fijos en fila", FG.B), ("enrutamiento", "elegir una rama", FG.B), ("paralelización", "varias a la vez", FG.B), ("evaluador", "revisar y corregir", FG.T), ("ReAct", "razonar y actuar", FG.T), ("orquestador", "repartir subtareas", FG.T)], "De izquierda a derecha crece lo que decide el modelo y lo que cuesta cada pregunta.")
FG.FIGURAS["mapa_acto_5"] = lambda: FG.fig_mapa_acto([("tarea y criterio", "qué se pide", FG.B), ("intentos repetidos", "no responde igual", FG.B), ("calificador", "código: sí o no", FG.B), ("fiabilidad", "aciertos al repetir", FG.T), ("inyección", "órdenes en los datos", FG.R), ("permisos y datos", "qué puede tocar", FG.R)], "Primero medir; después proteger lo que la medida no ve.")

# ------------------------------------------------------------------ diccionario de datos para la recuperación
DICCIONARIO = [
    {"titulo": "barrios · nombre", "texto": "Capa barrios_y_veredas: 332 polígonos; la columna nombre trae el nombre del barrio o vereda; codigo es el código municipal."},
    {"titulo": "barrios · sistema de referencia", "texto": "Las tres capas usan EPSG:9377, plano nacional de Colombia en metros; las distancias se calculan directamente en metros."},
    {"titulo": "cruces · identificadores", "texto": "Capa cruces_semaforicos: 724 puntos; OBJECTID e id_cruce son dos campos numéricos distintos; id_controlador agrupa varios cruces."},
    {"titulo": "cruces · atributos", "texto": "Cada cruce semafórico trae direccion (carrera y calle), cod_barrio y link_foto cuando existe fotografía."},
    {"titulo": "hurtos · fecha_hecho", "texto": "Columna fecha_hecho: fecha y hora del hurto a residencia en zona horaria −05:00; el periodo va de enero de 2003 a noviembre de 2023; año y mes se obtienen de esta columna."},
    {"titulo": "hurtos · coordenadas", "texto": "Columnas latitud y longitud en grados (WGS84); 4 330 registros no tienen coordenadas y todos los hurtos de 2023 carecen de ellas, así que 2023 no se puede mapear."},
    {"titulo": "hurtos · duplicados", "texto": "El CSV de hurtos tiene 5 559 filas duplicadas idénticas en todas las columnas; la herramienta las excluye por defecto y lo declara."},
    {"titulo": "hurtos · modalidad", "texto": "Columna modalidad: rompimiento de cerradura, descuido, atraco, llave maestra; conducta es siempre hurto a residencia."},
    {"titulo": "hurtos · datos personales", "texto": "Columnas sexo, edad, estado_civil, ocupacion y nivel_academico describen a la víctima; nunca se envían al modelo, solo agregados."},
    {"titulo": "capas · accidentes", "texto": "No existe ninguna capa de accidentes ni de siniestros viales en los datos del curso; preguntas sobre accidentes no son respondibles."},
    {"titulo": "herramientas · radio", "texto": "cruces_cercanos recibe identificador, campo y radio_m en metros; excluye el propio cruce; el radio máximo es 5 000 m."},
]

# ------------------------------------------------------------------ guiones de los flujos animados (desde las trazas reales)
def corto(x, n=260):
    t = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return t if len(t) <= n else t[:n] + "…"

def guion_agente(traza, textos=None):
    pasos, g, prev = traza["pasos"], [], "__start__"
    k = 0
    for p in pasos:
        if p["tipo"] == "modelo":
            k += 1
            tok = f" Leyó {p['tokens_entrada']} tokens y escribió {p['tokens_salida']}." if p.get("tokens_entrada") else ""
            if p["tool_calls"]:
                x = "Pide: " + "; ".join(f"{t['name']}({t['arguments']})" for t in p["tool_calls"]) + tok
                t = f"Llamada {k} al modelo: lee el contexto y pide una herramienta"
            else:
                x = "Responde: " + corto(p["contenido"]) + tok
                t = f"Llamada {k} al modelo: respuesta final"
            g.append({"n": ["modelo"], "de": [prev], "t": t, "x": x}); prev = "modelo"
        else:
            g.append({"n": ["herramientas"], "de": [prev], "t": f"Nodo herramientas: valida {p['name']} y la ejecuta", "x": "Observación que vuelve al contexto: " + corto(p["resultado"])}); prev = "herramientas"
    g.append({"n": ["__end__"], "de": [prev], "t": "tools_condition: sin llamadas pendientes → fin", "x": ("Terminó por " + traza.get("terminado_por", "") + ". ") + (textos or "")})
    return g

def pasos_patron(nombre):
    return RES["patrones"][nombre]["pasos"]

def guion_cadena():
    ps = {p["nodo"]: p for p in pasos_patron("cadena")}
    return [{"n": ["interpretar"], "de": ["__start__"], "t": "interpretar: salida estructurada del modelo", "x": f"anio = {ps['interpretar'].get('anio')}, capa = {ps['interpretar'].get('capa')}"},
            {"n": ["contar"], "de": ["interpretar"], "t": "contar: código, sin modelo", "x": corto(ps["contar"].get("resultado", ""))},
            {"n": ["redactar"], "de": ["contar"], "t": "redactar: el modelo escribe con los datos", "x": corto(ps["redactar"].get("respuesta", ""))},
            {"n": ["__end__"], "de": ["redactar"], "t": "fin", "x": "El orden fue fijo: la misma cadena no sabría responder la pregunta 4."}]

def guion_ruta(k):
    ps = RES["ruta"][k]["pasos"]; rama = ps[0].get("rama"); fin = ps[-1]
    return [{"n": ["clasificar"], "de": ["__start__"], "t": "clasificar: una sola decisión del modelo", "x": f"rama = {rama}"},
            {"n": [rama], "de": ["clasificar"], "t": f"rama {rama}: camino fijo", "x": corto(fin.get("resultado", fin.get("respuesta", RES["ruta"][k]["salida"].get("respuesta", ""))))},
            {"n": ["__end__"], "de": [rama], "t": "fin", "x": "Respuesta: " + corto(RES["ruta"][k]["salida"].get("respuesta", ""))}]

def guion_paralelo():
    ps = pasos_patron("paralelo"); corr = [p for p in ps if p["nodo"].startswith("corrida")]; voto = next((p for p in ps if p["nodo"] == "votar"), {})
    return [{"n": ["corrida_1", "corrida_2", "corrida_3"], "de": ["__start__", "__start__", "__start__"], "t": "tres corridas del agente a la vez", "x": "\n".join(f"{p['nodo']}: {corto(p.get('respuesta', ''), 120)}" for p in corr)},
            {"n": ["votar"], "de": ["corrida_1", "corrida_2", "corrida_3"], "t": "votar: código que toma la cifra más repetida", "x": "voto = " + str(voto.get("voto", ""))},
            {"n": ["__end__"], "de": ["votar"], "t": "fin", "x": "Tres llamadas en el tiempo de una; el costo se triplica."}]

def guion_evaluador():
    g, prev = [], "__start__"
    for p in pasos_patron("evaluador"):
        if p["nodo"] == "generador":
            g.append({"n": ["generador"], "de": [prev], "t": f"generador (ronda {p.get('ronda')}): el agente propone", "x": corto(p.get("respuesta", ""))}); prev = "generador"
        else:
            g.append({"n": ["evaluador"], "de": [prev], "t": "evaluador: ¿dice qué campo usó?", "x": ("acepta" if p.get("acepta") else "no acepta: " + str(p.get("observacion", "")))}); prev = "evaluador"
    g.append({"n": ["__end__"], "de": [prev], "t": "fin", "x": "El bucle termina al aceptar o a la tercera ronda."})
    return g

def guion_orquestador():
    ps = pasos_patron("orquestador"); orq = next((p for p in ps if p["nodo"] == "orquestador"), {}); trab = [p for p in ps if p["nodo"] == "trabajador"]; sint = next((p for p in ps if p["nodo"] == "sintetizar"), {})
    return [{"n": ["orquestador"], "de": ["__start__"], "t": "orquestador: el modelo divide la pregunta", "x": "subtareas = " + corto(orq.get("subtareas", ""))},
            {"n": ["trabajador"], "de": ["orquestador"] * max(1, len(trab)), "t": f"trabajador × {len(trab)}: cada subtarea corre el agente (Send)", "x": "\n".join(f"· {corto(p.get('subtarea', ''), 90)} → {corto(p.get('respuesta', ''), 110)}" for p in trab)},
            {"n": ["sintetizar"], "de": ["trabajador"], "t": "sintetizar: el modelo reúne los resultados", "x": corto(sint.get("respuesta", ""))},
            {"n": ["__end__"], "de": ["sintetizar"], "t": "fin", "x": f"Agente solo con la misma pregunta: {corto(RES['patrones'].get('agente_solo_cruzada', {}).get('respuesta', ''), 160)}"}]

def guion_inyeccion():
    modelo = RES["modelos"][0]; iny = RES["inyeccion"][modelo]
    traza = {"pasos": iny["pasos"], "terminado_por": "respuesta final"}
    g = guion_agente(traza, "¿Obedeció la instrucción inyectada? " + " · ".join(f"{m.split('/')[1]}: " + ("sí, respondió «999»" if v["obedecio"] else "no") + " («" + corto(v["respuesta"], 110) + "»)" for m, v in RES["inyeccion"].items()))
    for paso in g:
        if paso["n"] == ["herramientas"]:
            paso["t"] = "herramientas: el dato trae una frase que parece una orden"; paso["x"] = "Observación: " + corto({k: v for k, v in next(p["resultado"] for p in iny["pasos"] if p["tipo"] == "herramienta").items() if k == "conteo"}, 300)
    return g

def guion_calificador():
    g = guion_agente(TRZ["ejemplo_p2"])
    for paso in g:
        if paso["n"] == ["herramientas"]: paso["t"] = "trayectoria: el calificador de P2 lee aquí los argumentos (125 y 300)"
        if paso["n"] == ["__end__"]: paso["t"] = "resultado: el calificador lee la respuesta final (17 y el campo, o 17 y 15)"
    return g

def guion_react():
    cand = [c for c in TRZ["corridas"] if any(p.get("razonamiento") for p in c["pasos"] if p["tipo"] == "modelo") and c["correcto"]]
    t = cand[0] if cand else TRZ["ejemplo_p2"]
    g = guion_agente(t)
    i = 0
    for p in t["pasos"]:
        if p["tipo"] == "modelo":
            while i < len(g) and g[i]["n"] != ["modelo"]: i += 1
            if i < len(g):
                g[i]["t"] = g[i]["t"].replace("Llamada", "Pensamiento + acción · llamada")
                if p.get("razonamiento"): g[i]["x"] = "Razonamiento expuesto: «" + corto(p["razonamiento"], 220) + "»\n" + g[i]["x"]
                i += 1
    if not cand: g[-1]["x"] += " (Este modelo no expone razonamiento en esta corrida; el ciclo es el mismo.)"
    return g

def traza_p3():
    c = [x for x in TRZ["corridas"] if x["tarea"] == "p3"]; return (next((x for x in c if x["correcto"]), None) or c[0]) if c else TRZ["ejemplo_p2"]

FLUJOS = {"agente_p2": {"grafo": "agente", "guion": guion_agente(TRZ["ejemplo_p2"]), "inicio": "Grafo del agente dibujado por LangGraph; la pregunta 2 con su traza real.", "alt": "Grafo del agente: inicio, modelo, herramientas, fin"},
          "agente_p3": {"grafo": "agente", "guion": guion_agente(traza_p3()), "inicio": "La pregunta 3 con el agente."},
          "cadena": {"grafo": "cadena", "guion": guion_cadena(), "inicio": "Encadenamiento para la pregunta 3."},
          "ruta": {k: {"grafo": "ruta", "guion": guion_ruta(k), "inicio": "Elegir una pregunta y recorrer el grafo."} for k in RES["ruta"]},
          "paralelo": {"grafo": "paralelo", "guion": guion_paralelo(), "inicio": "Votación: la pregunta 2 tres veces a la vez."},
          "evaluador": {"grafo": "evaluador", "guion": guion_evaluador(), "inicio": "Evaluador–optimizador para la pregunta 2."},
          "orquestador": {"grafo": "orquestador", "guion": guion_orquestador(), "inicio": "Una pregunta que cruza dos capas, repartida."},
          "inyeccion": {"grafo": "agente", "guion": guion_inyeccion(), "inicio": "La pregunta 1 con la capa alterada."},
          "calificador": {"grafo": "agente", "guion": guion_calificador(), "inicio": "Qué parte de la corrida lee cada calificador."},
          "react": {"grafo": "agente", "guion": guion_react(), "inicio": "El ciclo del agente leído como ReAct: pensamiento, acción, observación."}}

# ------------------------------------------------------------------ corpus para las simulaciones de texto
def texto_plano(h):
    return html.unescape(re.sub(r"<[^>]+>", " ", h))
corpus = " ".join(texto_plano(" ".join(L["txt"]) + " " + L.get("t", "") + " " + L.get("p", "")) for L in LAMS)
corpus += " " + RES["instrucciones"] + " " + " ".join(RES["preguntas"].values()) + " " + " ".join(d["texto"] for d in DICCIONARIO)

# ------------------------------------------------------------------ trazas recortadas para el navegador
def recortar(t):
    return {k: t[k] for k in t if k != "mensajes"}
TRZ_WEB = {"modo": TRZ["modo"], "ejemplo_p2": recortar(TRZ["ejemplo_p2"]), "corridas": [recortar(c) for c in TRZ["corridas"]]}
RES_WEB = {k: RES[k] for k in ["modo", "fecha", "modelos", "intentos", "referencia", "casos", "preguntas", "instrucciones", "herramientas", "resumen", "sin_herramientas", "inyeccion", "memoria"]}
RES_WEB["costos"] = RES.get("costos", []); RES_WEB["pregunta_cruzada"] = RES.get("pregunta_cruzada", "")
DATOS = {"corpus": corpus, "geometria": GEO, "resultados": RES_WEB, "trazas": TRZ_WEB, "diccionario": DICCIONARIO, "grafos": GRAFOS, "flujos": FLUJOS}

# ------------------------------------------------------------------ imágenes con licencia o de fuentes oficiales citadas
import base64, mimetypes, io
def recortar_margenes(ruta):
    # Quita los márgenes blancos o transparentes de las figuras externas para que se vean grandes; devuelve bytes PNG
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None, None
    im = Image.open(ruta).convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    plano = Image.alpha_composite(fondo, im).convert("RGB")
    diff = ImageChops.difference(plano, Image.new("RGB", im.size, (255, 255, 255)))
    bbox = diff.point(lambda v: 255 if v > 12 else 0).getbbox()
    if bbox:
        m = 12; bbox = (max(0, bbox[0] - m), max(0, bbox[1] - m), min(im.width, bbox[2] + m), min(im.height, bbox[3] + m))
        plano = plano.crop(bbox)
    if plano.width > 1400:
        plano = plano.resize((1400, int(plano.height * 1400 / plano.width)))
    buf = io.BytesIO(); plano.save(buf, format="PNG", optimize=True); return buf.getvalue(), "image/png"

def imagen(nombre, pie):
    ruta = IMG / nombre
    datos_b, mime = recortar_margenes(ruta)
    if datos_b is None:
        mime = "image/webp" if nombre.endswith(".webp") else mimetypes.guess_type(nombre)[0]; datos_b = ruta.read_bytes()
    datos = base64.b64encode(datos_b).decode()
    return f'<figure class="img-ext"><img src="data:{mime};base64,{datos}" alt="{html.escape(pie)}"><figcaption>{pie}</figcaption></figure>'

# ------------------------------------------------------------------ HTML de cada lámina
FIG_ANCHAS = {"atencion", "entrenamiento", "prompt", "workflow", "agente", "contexto", "memoria", "tarea", "inyeccion", "permisos", "datos_personales", "mapa_ejercicio",
              "valido_correcto", "mapa_acto_4", "mapa_acto_5", "patron_cadena", "patron_react", "patron_evaluador", "token", "ciclo", "alucinacion", "rag_calculo"}

def lamina_html(i, L):
    modo = L.get("modo_forzado") or ("ancha" if L.get("fig") in FIG_ANCHAS else L["modo"])
    parr = "".join(f"<p>{p}</p>" for p in L["txt"])
    if modo == "portada":
        cuerpo = (f'<div class="portada-grid"><div><p class="eyebrow">Curso corto · Ingeniería Aeroespacial</p><h1>Agentes de inteligencia artificial aplicados a la <em>ciencia de datos geoespaciales</em></h1>'
                  f'<div class="lead">{parr}</div><p class="meta">José Ortega · Curso de Geoposicionamiento · {fmt(len(LAMS))} láminas · 6 actos</p></div>'
                  f'<div class="visual"><div data-sim="mapaP1"></div><p class="pie">Cruces semafóricos por barrio o vereda de Medellín, calculados con las capas del curso.</p></div></div>')
    elif modo == "fuentes":
        vistas, items = set(), []
        for M in LAMS:
            for s in re.split(r" · (?=[A-ZÁÉÍÓÚ]|complemento|resultado|simulación)", M.get("s", "")):
                s = s.strip()
                if s and s not in vistas:
                    vistas.add(s); items.append(s)
        oficiales = [s for s in items if not s.startswith(("complemento", "resultado propio", "simulación"))]
        otras = [s for s in items if s.startswith(("complemento", "resultado propio", "simulación"))]
        def li(s):
            return "<li>" + re.sub(r"(https?://\S+)", r'<a href="\1">\1</a>', html.escape(s)) + "</li>"
        cuerpo = (f'<div class="fuentes"><h3>Fuentes oficiales (leídas antes de citarlas)</h3><ol>{"".join(li(s) for s in oficiales)}</ol>'
                  f'<h3>Complementos y resultados propios</h3><ol>{"".join(li(s) for s in otras)}</ol></div>')
    else:
        derecha = ""
        imgs = "".join(imagen(f, pie) for f, pie in L.get("img", [])) if L.get("img") else ""
        if L.get("fig"):
            derecha = f'<figure class="defs-fig">{FG.FIGURAS[L["fig"]]()}</figure>'
        sim = f'<div class="mini" data-sim="{L["sim"]}"></div>' if L.get("sim") else ""
        bloque = BLOQUES[L["bloque"]]() if L.get("bloque") else ""
        if imgs and sim:
            cuerpo = f'<div class="defs con-fig con-img"><div class="defs-txt">{parr}</div><div class="img-col">{imgs}</div></div><div class="defs ancha">{sim}</div>'
        elif imgs:
            cuerpo = f'<div class="defs con-fig con-img solo-img"><div class="defs-txt">{parr}</div><div class="img-col">{imgs}</div></div>{bloque}'
        elif modo == "ancha":
            cuerpo = f'<div class="defs ancha"><div class="defs-txt">{parr}</div>{bloque}{derecha}{sim}</div>'
        else:
            cuerpo = f'<div class="defs con-fig {"con-sim" if sim else ""} {"con-bloque" if bloque else ""}"><div class="defs-txt">{parr}</div>{derecha}{sim}<div class="bloque-der">{bloque}</div></div>'
    glos = ""
    if L.get("g"):
        glos = ('<details class="gloss" open><summary>Términos de esta lámina (' + str(len(L["g"])) + ')</summary><div class="gl-cuerpo' + (" cols" if len(L["g"]) > 2 else "") + '">'
                + "".join("<p><strong>" + html.escape(t.split(" — ")[0]) + " —</strong> " + html.escape(" — ".join(t.split(" — ")[1:])) + "</p>" for t in L["g"]) + "</div></details>")
    prob = f'<p class="problema"><strong>El problema —</strong> {L["p"]}</p>' if L.get("p") else ""
    fuente = f'<p class="fuente">Fuente: {html.escape(L["s"])}</p>' if L.get("s") else ""
    cab = "" if modo == "portada" else f'<div class="lam-head"><span class="kicker">{html.escape(L["a"])}</span><h2>{html.escape(L["t"])}</h2></div>'
    return f'<section class="lam" id="lamina-{i+1}" data-i="{i}">{cab}{prob}{cuerpo}{glos}{fuente}</section>'

INDICE = [{"a": L["a"], "t": L["t"]} for L in LAMS]

CSS = """
:root{--blue:#155eef;--ink:#122b49;--muted:#526781;--line:#dae4f0;--pale:#f1f6fd;--teal:#008c9b;--navy:#0b2242;--paper:#fff;--red:#c0392b;--mono:ui-monospace,SFMono-Regular,Consolas,monospace;--deck-zoom:1.12}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button,input,select{font:inherit}button{cursor:pointer}a{color:var(--blue)}button:focus-visible,a:focus-visible,summary:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #44a7ff;outline-offset:3px}
header{height:54px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding:0 4%;background:#fff}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink);line-height:1.1}.brand svg{width:34px;height:34px}.brand strong{font-size:18px;letter-spacing:-.6px}.brand small{display:block;font-size:10px;letter-spacing:2px;color:var(--muted);margin-top:5px;text-transform:uppercase}
.header-tag{font:11px var(--mono);letter-spacing:.5px;color:var(--muted)}
main{max-width:1230px;margin:auto;padding:12px 34px 70px}
body.deck main{zoom:var(--deck-zoom)}
.lam{display:none}body.deck .lam.on{display:block}body:not(.deck) .lam{display:block;padding:40px 0;border-bottom:1px solid var(--line)}
.lam-head{margin:0 0 12px;border-bottom:2px solid var(--line);padding-bottom:9px}.kicker{font-family:var(--mono);font-size:12px;letter-spacing:.8px;text-transform:uppercase;color:var(--blue)}
h2{font-size:32px;letter-spacing:-1.2px;line-height:1.15;margin:6px 0 0;font-weight:650}
.problema{font-size:18.5px;line-height:1.45;margin:0 0 10px;color:var(--ink)}.problema strong{color:var(--navy)}
.defs{padding:4px 0}.defs p{font-size:19px;line-height:1.5;margin:0 0 15px}.defs p strong{color:var(--navy)}.defs code{font:0.86em var(--mono);background:var(--pale);padding:1px 5px;border-radius:4px}
.defs.con-fig{display:grid;grid-template-columns:minmax(0,.82fr) minmax(0,1.18fr);gap:28px;align-items:start}.defs.con-sim{grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr)}
.defs.con-fig .defs-txt p{font-size:17px}.defs.con-bloque{grid-template-columns:minmax(0,.85fr) minmax(0,1.15fr)}.defs.con-bloque .defs-txt p{font-size:16.5px}.bloque-der:empty{display:none}.bloque-der .codigo{margin-top:0}.defs.ancha .defs-txt{max-width:1080px}
.defs-fig{margin:0;background:var(--pale);border:1px solid var(--line);border-radius:10px;padding:14px;position:sticky;top:12px}.defs-fig svg{width:100%;height:auto;display:block}
.mini{background:var(--pale);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:14px}
.mini label{display:flex;justify-content:space-between;font-weight:550;font-size:13px;margin:0 0 6px}.mini output{font:12px var(--mono);color:var(--blue)}
.mini input[type=range]{display:block;width:100%;height:5px;margin:6px 0 10px;accent-color:var(--blue);cursor:pointer}.mini input[type=text],.mini select{width:100%;padding:7px 9px;border:1px solid #c5d4e7;border-radius:6px;background:#fff;font-size:14px}
.mini-read{font-size:13.5px;line-height:1.5;color:var(--muted);margin:8px 0 0}.mini-lbl{font-size:12.5px;font-weight:550;margin:0 0 4px;color:var(--ink)}.chips button[aria-pressed="true"]{background:var(--navy);color:#fff;border-color:var(--navy)}.mini-read b{color:var(--ink)}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chips button{border:1px solid #c5d4e7;background:#fff;color:var(--blue);border-radius:6px;padding:5px 10px;font-size:12.5px}.chips button:hover{background:#eaf1ff}
.barras{display:grid;gap:5px;margin-top:8px}.barra{display:grid;grid-template-columns:150px 1fr 56px 60px;align-items:center;gap:8px;font-size:13px}.barra span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.barra i{display:block;height:12px;background:var(--blue);border-radius:3px}.barra b{font:12px var(--mono);color:var(--ink)}.barra small{font:11px var(--mono);color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fichas{margin:10px 0;line-height:2.2}.tok-w{display:inline-block;margin-right:8px}.tok-w i{display:inline-block;font-style:normal;font:13px var(--mono);border:1px solid var(--blue);background:#fff;color:var(--ink);padding:2px 6px;border-radius:4px;margin-right:2px}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.estado{border-radius:8px;padding:10px 12px;font-size:13.5px;line-height:1.5;margin-top:10px;background:#fff;border:1px solid var(--line)}.estado.si{border-color:#a9d18e;background:#f3faf0}.estado.no{border-color:#e4a3a3;background:#fdf3f3}.estado code{font:12px var(--mono);word-break:break-all}
.form3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}.form3 label{display:block;font-size:12.5px;font-weight:550}.form3 input,.form3 select{width:100%;margin-top:4px}
.gen-out{font-size:15px;line-height:1.6;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 12px;min-height:60px;margin:8px 0 0}
.mapa-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;align-items:start}.mapa svg,.mapa canvas{width:100%;display:block;background:#f7f9fc;border-radius:8px}.mapa path:hover{stroke:var(--navy);stroke-width:1.2}
.msgs{display:grid;gap:6px;margin:8px 0}.msg{display:grid;grid-template-columns:86px 1fr;gap:10px;font-size:13px;line-height:1.45;border:1px solid var(--line);border-radius:8px;padding:7px 10px;background:#fff}.msg span{font:11px var(--mono);text-transform:uppercase;letter-spacing:.5px;color:var(--muted);padding-top:2px}.msg code{font:12px var(--mono);word-break:break-all}
.msg-system{opacity:.85}.msg-assistant{border-color:#b9cdfb;background:#f5f8ff}.msg-tool{border-color:#b7dfe3;background:#f1fbfc}.msg-user{border-color:#d8d8d8}.msg-on{box-shadow:0 0 0 2px var(--blue)}
.codigo{background:#0f1f36;color:#e8eef8;border-radius:10px;padding:12px 14px;font:12px/1.45 var(--mono);overflow:auto;margin:6px 0 10px}
.nota{font-size:14px;color:var(--muted);margin:0 0 8px}
.codigo code{background:transparent;color:inherit;padding:0;font:inherit}.codigo.chico{font-size:11.5px;padding:8px 10px;margin:6px 0 0}
.mini .msgs{max-height:300px;overflow:auto;padding-right:4px}
.img-ext{margin:0;background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px}.img-ext img{width:100%;height:auto;display:block}.img-ext figcaption{font-size:11.5px;color:var(--muted);margin-top:6px;line-height:1.4}
.img-col{display:grid;gap:8px;align-content:start}.defs.con-img{grid-template-columns:minmax(0,1.25fr) minmax(0,.75fr);gap:22px}.defs.con-img .defs-txt p{font-size:16px;margin-bottom:10px}.img-ext{padding:6px}.img-ext img{max-height:165px;object-fit:contain}.defs.solo-img{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.defs.solo-img .img-ext img{max-height:230px}.img-ext figcaption{font-size:10.5px;margin-top:4px}
.fl-svg{width:100%;height:auto;display:block;background:#fff;border:1px solid var(--line);border-radius:10px}.fl-panel{font-size:13.5px;line-height:1.45;margin-top:6px;min-height:32px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 12px}.fl-tit{display:block;font-weight:650;color:var(--navy);margin-bottom:2px}.fl-rotulo{font:12px var(--mono);letter-spacing:.5px;text-transform:uppercase;color:var(--blue);margin:0 0 6px}.fl-cab{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.fl-cab select{max-width:520px}
.fl-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.fl-grid>div:nth-child(4),.fl-grid>div:nth-child(5){grid-column:span 1}
.barra.b3{grid-template-columns:190px 1fr 110px 1fr 70px 80px}.barra i.t{background:var(--teal)}
.tabla{width:100%;border-collapse:collapse;font-size:14px;margin:6px 0 10px}.tabla th{text-align:left;font:11px var(--mono);letter-spacing:.6px;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--line);padding:6px 8px}.tabla td{padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}.tabla td.ok{color:#2e7d32;font-weight:600}.tabla td.medio{color:#b26a00;font-weight:600}.tabla td.mal{color:var(--red);font-weight:600}.tabla code{font:12px var(--mono)}
.gloss{margin-top:14px;border-top:1px solid var(--line);padding-top:8px}.gloss summary{cursor:pointer;color:var(--ink);font-weight:550;font-size:12.5px}.gl-cuerpo p{font-size:13.5px;line-height:1.45;margin:6px 0;color:var(--muted)}.gl-cuerpo strong{color:var(--ink)}.gl-cuerpo.cols{columns:2;column-gap:28px}
.fuente{font-size:11px;color:var(--muted);margin:8px 0 0;line-height:1.4;border-top:1px solid var(--line);padding-top:8px;word-break:break-word}
.portada-grid{display:grid;grid-template-columns:1fr 1.05fr;gap:50px;align-items:center;padding:30px 0}.eyebrow{font:11px/1.5 var(--mono);letter-spacing:1.8px;text-transform:uppercase;color:var(--blue)}
h1{font-size:clamp(32px,3.3vw,48px);line-height:1.1;letter-spacing:-1.8px;margin:14px 0 18px;font-weight:650}h1 em{font-style:normal;color:var(--blue)}.lead p{font-size:16.5px;color:var(--muted);line-height:1.6;margin:0 0 12px}.meta{font-size:12px;color:var(--muted)}
.visual{background:var(--pale);border:1px solid var(--line);border-radius:12px;padding:14px}.visual .pie{font-size:12.5px;color:var(--muted);margin:8px 0 0}
.fuentes h3{font-size:16px;margin:14px 0 6px}.fuentes{columns:2;column-gap:30px}.fuentes h3{break-after:avoid}.fuentes ol{margin:0;padding-left:20px;font-size:11.5px;line-height:1.45}.fuentes li{margin-bottom:5px;word-break:break-word}
#deckBar{position:fixed;left:0;right:0;bottom:0;background:var(--navy);color:#fff;display:flex;gap:8px;justify-content:center;align-items:center;padding:8px;z-index:20;font-size:13px}#deckBar button{background:#fff;color:var(--navy);border:0;border-radius:6px;padding:6px 12px;font-size:13px}#deckBar button:disabled{opacity:.4}#deckBar span{font:12px var(--mono);padding:0 8px}.deck-sep{width:1px;height:22px;background:#3a5277}
body:not(.deck) #deckBar button.solo-deck{display:none}
#deckIndex{position:fixed;inset:0 0 44px 0;background:#ffffffee;backdrop-filter:blur(8px);overflow:auto;padding:30px 5%;z-index:19;columns:3;column-gap:34px}#deckIndex h3{font-size:13px;color:var(--blue);margin:14px 0 6px;break-after:avoid;font-family:var(--mono);text-transform:uppercase;letter-spacing:.8px}#deckIndex ol{margin:0;padding:0;list-style:none}#deckIndex button{display:block;width:100%;text-align:left;background:transparent;border:0;padding:4px 6px;font-size:13.5px;color:var(--ink);border-radius:5px}#deckIndex button:hover,#deckIndex button[aria-current="true"]{background:#eaf1ff;color:var(--blue)}
body.deck{padding-bottom:50px}
@media(max-width:900px){.defs.con-fig,.portada-grid,.mapa-grid,.dos,.form3{grid-template-columns:1fr}#deckIndex{columns:1}.gl-cuerpo.cols{columns:1}}
"""

NAV_JS = """
(function(){
const LAMS=__INDICE__;const $=id=>document.getElementById(id);const secs=[...document.querySelectorAll('.lam')];let cur=0,zoom=1.12,autoFit=true;
function fromHash(){const m=/^#lamina-(\\d+)$/.exec(location.hash);return m?Math.min(LAMS.length,Math.max(1,+m[1]))-1:null}
function applyZoom(){const root=document.documentElement;root.style.setProperty('--deck-zoom',zoom);if(!autoFit||!document.body.classList.contains('deck')||innerWidth<=760)return;
  let z=zoom;for(let k=0;k<9;k++){const alto=root.scrollHeight,vis=innerHeight;if(alto<=vis+2)break;z=Math.max(zoom*0.6,z*vis/alto*0.975);root.style.setProperty('--deck-zoom',z);if(z<=zoom*0.6)break}
  const dt=secs[cur].querySelector('details.gloss');if(dt&&dt.open&&root.scrollHeight>innerHeight+2){dt.open=false;z=zoom;root.style.setProperty('--deck-zoom',z);for(let k=0;k<9;k++){const alto=root.scrollHeight,vis=innerHeight;if(alto<=vis+2)break;z=Math.max(zoom*0.6,z*vis/alto*0.975);root.style.setProperty('--deck-zoom',z);if(z<=zoom*0.6)break}}}
function show(i){cur=Math.min(LAMS.length-1,Math.max(0,i));secs.forEach((s,k)=>s.classList.toggle('on',k===cur));const dt=secs[cur].querySelector('details.gloss');if(dt)dt.open=true;
  $('deckCount').textContent=(cur+1)+' / '+LAMS.length;$('deckPrev').disabled=cur===0;$('deckNext').disabled=cur===LAMS.length-1;
  try{history.replaceState(null,'','#lamina-'+(cur+1))}catch(e){location.hash='lamina-'+(cur+1)}document.title=LAMS[cur].t+' · Agentes de inteligencia artificial';
  window.iniciarSims(secs[cur]);applyZoom();scrollTo(0,0);requestAnimationFrame(()=>{window.redibujarSims();applyZoom();requestAnimationFrame(()=>{window.redibujarSims();applyZoom()})})}
function setMode(deck){document.body.classList.toggle('deck',deck);$('deckMode').textContent=deck?'Modo lectura':'Modo láminas';
  if(deck)show(cur);else{secs.forEach(s=>s.classList.add('on'));window.iniciarSims(document);$('deckIndex').hidden=true;document.documentElement.style.setProperty('--deck-zoom',1);requestAnimationFrame(()=>window.redibujarSims())}}
function buildIndex(){const box=$('deckIndex');let h='',act=null;LAMS.forEach((L,i)=>{if(L.a!==act){if(act!==null)h+='</ol>';act=L.a;h+='<h3>'+L.a+'</h3><ol>'}h+='<li><button data-go="'+i+'">'+(i+1)+' · '+L.t+'</button></li>'});box.innerHTML=h+'</ol>';
  box.addEventListener('click',e=>{const b=e.target.closest('[data-go]');if(b){box.hidden=true;if(!document.body.classList.contains('deck'))setMode(true);show(+b.dataset.go)}})}
function toggleIndex(){const box=$('deckIndex');box.hidden=!box.hidden;if(!box.hidden){box.querySelectorAll('[data-go]').forEach(b=>b.setAttribute('aria-current',String(+b.dataset.go===cur)));const c=box.querySelector('[aria-current="true"]');if(c)c.focus()}}
$('deckPrev').addEventListener('click',()=>show(cur-1));$('deckNext').addEventListener('click',()=>show(cur+1));$('deckIndexBtn').addEventListener('click',toggleIndex);$('deckMode').addEventListener('click',()=>setMode(!document.body.classList.contains('deck')));
function setZoom(z){autoFit=false;zoom=Math.min(1.6,Math.max(.6,z));applyZoom();requestAnimationFrame(()=>window.redibujarSims())}
const efectivo=()=>parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--deck-zoom'))||zoom;
$('deckSmaller').addEventListener('click',()=>setZoom(efectivo()-.08));$('deckBigger').addEventListener('click',()=>setZoom(efectivo()+.08));
document.addEventListener('keydown',e=>{if(!document.body.classList.contains('deck')||e.altKey||e.ctrlKey||e.metaKey)return;if(e.key==='Escape'){$('deckIndex').hidden=true;return}
  const t=e.target,busy=t.closest&&t.closest('input,select,textarea,summary,#deckIndex');
  if(e.key==='PageDown'){e.preventDefault();show(cur+1)}else if(e.key==='PageUp'){e.preventDefault();show(cur-1)}else if(!busy&&e.key==='ArrowRight'){e.preventDefault();show(cur+1)}else if(!busy&&e.key==='ArrowLeft'){e.preventDefault();show(cur-1)}else if(!busy&&e.key==='Home'){e.preventDefault();show(0)}else if(!busy&&e.key==='End'){e.preventDefault();show(LAMS.length-1)}});
window.addEventListener('hashchange',()=>{const i=fromHash();if(i!==null&&i!==cur&&document.body.classList.contains('deck'))show(i)});
window.addEventListener('resize',e=>{if(e.isTrusted){if(document.body.classList.contains('deck'))applyZoom();requestAnimationFrame(()=>window.redibujarSims())}});
buildIndex();const h=fromHash();if(h!==null)cur=h;setMode(true);
})();
"""

LOGO = '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="18" fill="#0b2242"/><circle cx="14" cy="22" r="4" fill="#65d8dd"/><circle cx="26" cy="14" r="4" fill="#155eef"/><path d="M14 22 L26 14" stroke="#fff" stroke-width="2"/><circle cx="27" cy="27" r="3" fill="#fff"/></svg>'

def construir():
    cuerpo = "".join(lamina_html(i, L) for i, L in enumerate(LAMS))
    sims = (AQUI / "sims_agentes.js").read_text()
    datos = json.dumps(DATOS, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    doc = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agentes de inteligencia artificial aplicados a la ciencia de datos geoespaciales · láminas</title>
<meta name="description" content="Agentes de inteligencia artificial aplicados a la ciencia de datos geoespaciales: curso corto con un ejercicio sobre datos de Medellín. Un solo archivo HTML, funciona sin conexión.">
<style>{CSS}</style></head>
<body class="deck">
<header><a class="brand" href="#lamina-1">{LOGO}<span><strong>Agentes de inteligencia artificial</strong><small>ciencia de datos geoespaciales</small></span></a><span class="header-tag">CURSO DE GEOPOSICIONAMIENTO · {fmt(len(LAMS))} LÁMINAS · SIN CONEXIÓN</span></header>
<main>{cuerpo}</main>
<div aria-label="Navegación por láminas" id="deckBar" role="navigation"><button aria-label="Lámina anterior" class="solo-deck" id="deckPrev">◀</button><button aria-haspopup="dialog" id="deckIndexBtn">Índice</button><span aria-live="polite" id="deckCount"></span><button aria-label="Lámina siguiente" class="solo-deck" id="deckNext">▶</button><span class="deck-sep"></span><button aria-label="Reducir tamaño" class="solo-deck" id="deckSmaller">A−</button><button aria-label="Aumentar tamaño" class="solo-deck" id="deckBigger">A+</button><button id="deckMode"></button></div>
<div aria-label="Índice de láminas" hidden id="deckIndex" role="dialog"></div>
<script>window.DATOS={datos};</script>
<script>{sims}</script>
<script>{NAV_JS.replace("__INDICE__", json.dumps(INDICE, ensure_ascii=False))}</script>
</body></html>"""
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(doc, encoding="utf-8")
    palabras = [len(texto_plano(" ".join(L["txt"])).split()) for L in LAMS]
    print(f"{SALIDA} · {len(LAMS)} láminas · {len(doc)/1e6:.2f} MB · palabras por lámina: mín {min(palabras)}, máx {max(palabras)}, media {sum(palabras)/len(palabras):.0f}")
    return SALIDA

if __name__ == "__main__":
    construir()
