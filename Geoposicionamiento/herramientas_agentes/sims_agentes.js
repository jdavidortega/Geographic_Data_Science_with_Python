/* Simulaciones de la presentación «Agentes de inteligencia artificial aplicados a la ciencia de datos geoespaciales». Todas calculan con los datos incrustados (DATOS): nada es ilustrativo. */
(function(){
const $=(id)=>document.getElementById(id);
const num=(x,n)=>Number(x).toFixed(n).replace('.',',');
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const SIMS={};window.SIMS=SIMS;
const D=window.DATOS;

/* ---------- corpus y modelos de texto (reales, entrenados aquí) ---------- */
const palabras=t=>t.toLowerCase().replace(/[«»"“”()\[\]{}]/g,' ').match(/[a-záéíóúüñ]+|\d+|[.,;:¿?¡!]/g)||[];
const CORPUS=palabras(D.corpus);
const N_CORPUS=CORPUS.length;

/* BPE: fusiones aprendidas del corpus, en orden */
let BPE=null;
function entrenarBPE(maxFus){
  const vocab=new Map();
  for(const w of CORPUS){if(!/^[a-záéíóúüñ]+$/.test(w))continue;const k=w.split('').join(' ')+' </w>';vocab.set(k,(vocab.get(k)||0)+1)}
  let items=[...vocab.entries()].map(([k,c])=>[k.split(' '),c]);
  const fusiones=[];
  for(let f=0;f<maxFus;f++){
    const pares=new Map();
    for(const [s,c] of items)for(let i=0;i<s.length-1;i++){const p=s[i]+'\u0001'+s[i+1];pares.set(p,(pares.get(p)||0)+c)}
    let mejor=null,mc=0;for(const [p,c] of pares)if(c>mc){mc=c;mejor=p}
    if(!mejor||mc<2)break;
    const [a,b]=mejor.split('\u0001');fusiones.push([a,b,mc]);
    items=items.map(([s,c])=>{const o=[];for(let i=0;i<s.length;i++){if(i<s.length-1&&s[i]===a&&s[i+1]===b){o.push(a+b);i++}else o.push(s[i])}return[o,c]});
  }
  return fusiones;
}
function aplicarBPE(palabra,fusiones,k){
  let s=palabra.toLowerCase().split('').concat(['</w>']);
  for(let f=0;f<Math.min(k,fusiones.length);f++){const [a,b]=fusiones[f];const o=[];for(let i=0;i<s.length;i++){if(i<s.length-1&&s[i]===a&&s[i+1]===b){o.push(a+b);i++}else o.push(s[i])}s=o}
  return s.map(t=>t.replace('</w>',''));
}
SIMS.bpe=function(el){
  if(!BPE)BPE=entrenarBPE(400);
  const NIV=[['solo letras',0],['pequeño',40],['mediano',150],['grande',400]];let k=150;
  el.innerHTML='<p class="mini-lbl">Tamaño del vocabulario del tokenizador</p><div class="chips" id="bpeN">'+NIV.map(([n,v])=>'<button data-k="'+v+'"'+(v===k?' aria-pressed="true"':'')+'>'+n+'</button>').join('')+'</div>'+
    '<label for="bpeT" style="margin-top:10px">Texto que se parte en tokens</label><input id="bpeT" type="text" value="cruces semafóricos por barrio y vereda" maxlength="80">'+
    '<div id="bpeR" class="fichas" aria-live="polite"></div><p class="mini-read" id="bpeF"></p>';
  const draw=()=>{el.querySelectorAll('#bpeN button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.k===k)));
    const ws=($('bpeT').value.match(/[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+/g)||[]).slice(0,10);let total=0,enteras=0;
    $('bpeR').innerHTML=ws.map(w=>{const t=aplicarBPE(w,BPE,k);total+=t.length;if(t.length===1)enteras++;return '<span class="tok-w">'+t.map(x=>'<i>'+esc(x)+'</i>').join('')+'</span>'}).join(' ');
    const nombreNiv=(NIV.find(x=>x[1]===k)||NIV[0])[0];
    let expl=k===0?'Con el vocabulario mínimo cada letra es un token: la frase se vuelve muy larga y ninguna pieza significa nada por sí sola.':
      k>=400?'Con un vocabulario grande las palabras frecuentes de este texto quedan enteras y solo las raras se parten.':
      'Con un vocabulario '+nombreNiv+' las palabras más frecuentes del texto ya son un solo token y las demás se parten en trozos.';
    $('bpeF').innerHTML=(ws.length?'<b>'+total+' tokens</b> para '+ws.length+' palabras; '+enteras+(enteras===1?' palabra quedó entera':' palabras quedaron enteras')+'. ':'')+expl+
      ' Los trozos no son sílabas ni palabras: los decide la frecuencia de cada pareja de letras en el texto de entrenamiento (aquí, el de esta presentación; un modelo comercial usa otro texto y otros cortes).'};
  el.querySelectorAll('#bpeN button').forEach(b=>b.addEventListener('click',()=>{k=+b.dataset.k;draw()}));$('bpeT').addEventListener('input',draw);draw();return draw};

/* Trigramas: cuentas reales sobre el corpus con retroceso a bigramas y unigramas */
let TRI=null;
function entrenarTri(){
  const u=new Map(),b=new Map(),t=new Map();
  for(let i=0;i<CORPUS.length;i++){const w=CORPUS[i];u.set(w,(u.get(w)||0)+1);
    if(i>0){const k=CORPUS[i-1];if(!b.has(k))b.set(k,new Map());const m=b.get(k);m.set(w,(m.get(w)||0)+1)}
    if(i>1){const k=CORPUS[i-2]+' '+CORPUS[i-1];if(!t.has(k))t.set(k,new Map());const m=t.get(k);m.set(w,(m.get(w)||0)+1)}}
  return{u,b,t};
}
function distribucion(contexto){
  if(!TRI)TRI=entrenarTri();
  const c=palabras(contexto);let m=null,orden='';
  if(c.length>=2&&TRI.t.has(c[c.length-2]+' '+c[c.length-1])){m=TRI.t.get(c[c.length-2]+' '+c[c.length-1]);orden='se buscaron en el texto todas las veces que aparecen juntas «'+c[c.length-2]+' '+c[c.length-1]+'» y se contó qué palabra sigue'}
  else if(c.length>=1&&TRI.b.has(c[c.length-1])){m=TRI.b.get(c[c.length-1]);orden='esas dos palabras nunca aparecen juntas en el texto; se cuenta qué sigue solo a «'+c[c.length-1]+'»'}
  else{m=TRI.u;orden='ninguna de esas palabras aparece en el texto; solo queda la frecuencia general de cada palabra'}
  const tot=[...m.values()].reduce((a,x)=>a+x,0);
  const lista=[...m.entries()].map(([w,n])=>[w,n/tot,n]).sort((a,b)=>b[1]-a[1]);
  return{lista,tot,orden};
}
function barras(id,lista,n){
  const top=lista.slice(0,n),mx=top.length?top[0][1]:1;
  $(id).innerHTML=top.map(([w,p,c])=>'<div class="barra"><span>'+esc(w)+'</span><i style="width:'+Math.max(2,p/mx*100)+'%"></i><b>'+num(p*100,1)+' %</b><small>'+c+'</small></div>').join('')||'<p>Sin datos.</p>';
}
SIMS.trigrama=function(el){
  el.innerHTML='<label for="triT">Inicio de la frase</label><input id="triT" type="text" value="el modelo de" maxlength="60">'+
    '<p class="mini-read" id="triO"></p><div id="triB" class="barras"></div>';
  const draw=()=>{const {lista,tot,orden}=distribucion($('triT').value);$('triO').innerHTML='Cómo se calculó: '+esc(orden)+' ('+tot+' casos). Barra = probabilidad de cada palabra siguiente; el número pequeño, cuántas veces se contó.';barras('triB',lista,8)};
  $('triT').addEventListener('input',draw);draw();return draw};

SIMS.contexto=function(el){
  el.innerHTML='<div class="dos"><div><label for="ctxA">Contexto A</label><input id="ctxA" type="text" value="la pregunta es" maxlength="60"><div id="ctxBa" class="barras"></div></div>'+
    '<div><label for="ctxB">Contexto B</label><input id="ctxB" type="text" value="la respuesta es" maxlength="60"><div id="ctxBb" class="barras"></div></div></div><p class="mini-read" id="ctxO"></p>';
  const draw=()=>{const a=distribucion($('ctxA').value),b=distribucion($('ctxB').value);barras('ctxBa',a.lista,6);barras('ctxBb',b.lista,6);
    const ta=a.lista[0]?a.lista[0][0]:'—',tb=b.lista[0]?b.lista[0][0]:'—';
    $('ctxO').innerHTML='Mismo modelo, mismos parámetros: con A el token más probable es «'+esc(ta)+'»; con B, «'+esc(tb)+'». Solo cambió el contexto. Barra = probabilidad; número pequeño = veces contadas en el texto.'};
  $('ctxA').addEventListener('input',draw);$('ctxB').addEventListener('input',draw);draw();return draw};

function rng(seed){let s=seed>>>0||1;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296}}
SIMS.generar=function(el){
  el.innerHTML='<label for="genT">Temperatura <output id="genO"></output></label><input id="genT" type="range" min="0" max="1.5" step="0.1" value="0">'+
    '<div class="chips"><button id="genR">Generar de nuevo</button></div><p class="mini-read" id="genS"></p><p class="gen-out" id="genX" aria-live="polite"></p>';
  let semilla=7;
  const gen=()=>{const T=+$('genT').value;$('genO').textContent=num(T,1);const r=rng(semilla);let ctx='el agente';const out=['el','agente'];
    for(let i=0;i<30;i++){const {lista}=distribucion(ctx);if(!lista.length)break;let w;
      if(T===0)w=lista[0][0];else{const ps=lista.map(([_,p])=>Math.pow(p,1/T)),z=ps.reduce((a,x)=>a+x,0);let u=r()*z,k=0;while(k<ps.length-1&&u>ps[k]){u-=ps[k];k++}w=lista[k][0]}
      out.push(w);ctx=out.slice(-2).join(' ')}
    $('genX').textContent=out.join(' ').replace(/ ([.,;:?!])/g,'$1');
    $('genS').textContent=(T===0?'Temperatura 0: en cada paso se toma la palabra más probable; al generar de nuevo sale exactamente el mismo texto.':T<=0.5?'Temperatura '+num(T,1)+': casi siempre la palabra más probable, a veces otra; el texto cambia poco entre corridas.':'Temperatura '+num(T,1)+': las palabras menos probables salen con frecuencia; cada corrida da un texto distinto y, con valores altos, sin sentido.')+' (Texto generado por el modelo de trigramas entrenado con esta presentación.)'};
  $('genT').addEventListener('input',gen);$('genR').addEventListener('click',()=>{semilla=(semilla*31+7)%1000+1;gen()});gen();return gen};

/* Entrenamiento frente a inferencia: la huella de los parámetros no cambia al generar */
function huella(){if(!TRI)TRI=entrenarTri();let h=2166136261;for(const [k,m] of TRI.b){for(const [w,c] of m){const t=k+'>'+w+':'+c;for(let i=0;i<t.length;i++){h^=t.charCodeAt(i);h=Math.imul(h,16777619)}}}return (h>>>0).toString(16).padStart(8,'0')}
SIMS.entrenamiento=function(el){
  if(!TRI)TRI=entrenarTri();const nParam=[...TRI.b.values()].reduce((a,m)=>a+m.size,0);const H0=huella();
  el.innerHTML='<div class="dos"><div class="estado"><b>Entrenamiento (una sola vez)</b><br>Texto de entrenamiento: '+N_CORPUS.toLocaleString('es-CO')+' palabras (esta presentación).<br>Parámetros ajustados: <b>'+nParam.toLocaleString('es-CO')+'</b> cuentas de «palabra → siguiente».<br>Huella de los parámetros: <code id="enH0">'+H0+'</code></div>'+
    '<div class="estado si"><b>Inferencia (cada pregunta)</b><br><label for="enT">Inicio</label><input id="enT" type="text" value="el agente" maxlength="40"><div class="chips"><button id="enB">Generar 12 palabras</button></div><p class="gen-out" id="enX"></p>Huella de los parámetros después de generar: <code id="enH1">'+H0+'</code> <span id="enI"></span></div></div><p class="mini-read" id="enN"></p>';
  let n=0;
  const gen=()=>{let ctx=$('enT').value;const out=palabras(ctx);for(let i=0;i<12;i++){const {lista}=distribucion(out.slice(-2).join(' '));if(!lista.length)break;out.push(lista[0][0])}
    $('enX').textContent=out.join(' ').replace(/ ([.,;:?!])/g,'$1');n++;const h=huella();$('enH1').textContent=h;$('enI').textContent=h===H0?'— idéntica':'— cambió';
    $('enN').textContent='Se han hecho '+n+(n===1?' pregunta':' preguntas')+' y los parámetros son los mismos: la inferencia solo lee el modelo. Lo que el modelo «sabe» sobre esta conversación está en el contexto, no en los parámetros. (Modelo de trigramas de esta presentación; un modelo grande funciona igual con una red neuronal.)'};
  $('enB').addEventListener('click',gen);gen();return null};

/* ---------- geometría y herramientas reales en el navegador ---------- */
const G=D.geometria;
const porId=new Map(G.cruces.map(c=>[c.i,c])),porObj=new Map(G.cruces.map(c=>[c.o,c]));
function crucesCercanos(campo,id,radio){const c=(campo==='id_cruce'?porId:porObj).get(id);if(!c)return null;let n=0;for(const p of G.cruces){const d=Math.hypot(p.x-c.x,p.y-c.y);if(d<=radio&&d>0)n++}return{n,c}}

function validarContraEsquema(esq,obj){
  const err=[];for(const r of (esq.required||[]))if(!(r in obj)||obj[r]===''||obj[r]===undefined)err.push(r+': falta (es obligatorio)');
  for(const [k,v] of Object.entries(obj)){const p=esq.properties[k];if(!p){err.push(k+': no está en el esquema');continue}if(v===''||v===undefined)continue;
    if(p.type==='integer'){if(!/^-?\d+$/.test(String(v)))err.push(k+': debe ser un entero, no «'+v+'»')}
    else if(p.type==='number'){if(isNaN(Number(v))||String(v).trim()==='')err.push(k+': debe ser un número, no «'+v+'»')}
    if(p.enum&&!p.enum.includes(v))err.push(k+': debe ser uno de '+p.enum.join(', '));
    const x=Number(v);if(!isNaN(x)){if(p.exclusiveMinimum!==undefined&&x<=p.exclusiveMinimum)err.push(k+': debe ser mayor que '+p.exclusiveMinimum);if(p.minimum!==undefined&&x<p.minimum)err.push(k+': debe ser al menos '+p.minimum);if(p.maximum!==undefined&&x>p.maximum)err.push(k+': debe ser como mucho '+p.maximum)}}
  return err;
}
SIMS.validar=function(el){
  const esq=D.resultados.herramientas.find(h=>h.function.name==='cruces_cercanos').function.parameters;
  el.innerHTML='<p class="mini-lbl">Argumentos que el modelo podría escribir para cruces_cercanos; se validan contra el esquema real antes de ejecutar</p><div class="form3"><label>identificador <input id="vaI" type="text" value="125"></label><label>campo <select id="vaC"><option>id_cruce</option><option>OBJECTID</option></select></label><label>radio_m <input id="vaR" type="text" value="300"></label></div>'+
    '<div class="chips"><button data-r="trescientos">radio «trescientos»</button><button data-r="-5">radio −5</button><button data-r="9000">radio 9 000</button><button data-r="300" data-i="125">125 y 300</button><button data-i="99999">cruce 99999</button></div><div id="vaO" class="estado" aria-live="polite"></div>';
  const draw=()=>{const obj={identificador:$('vaI').value,campo:$('vaC').value,radio_m:$('vaR').value};const err=validarContraEsquema(esq,obj);const o=$('vaO');
    if(err.length){o.className='estado no';o.innerHTML='<b>Rechazada por el esquema.</b> Lo que recibe el modelo como observación:<br><code>{"error_de_validacion": '+esc(JSON.stringify(err))+'}</code>';return}
    const r=crucesCercanos(obj.campo,+obj.identificador,+obj.radio_m);
    if(!r){o.className='estado no';o.innerHTML='<b>Válida, pero la función no encuentra el cruce.</b> Observación: <code>{"error": "no hay exactamente un cruce con '+esc(obj.campo)+' = '+esc(obj.identificador)+'"}</code>';return}
    o.className='estado si';o.innerHTML='<b>Válida y ejecutada.</b> Observación: <code>{"campo": "'+esc(obj.campo)+'", "identificador": '+esc(obj.identificador)+', "radio_m": '+esc(obj.radio_m)+', "cruces_a_esa_distancia_o_menos": '+r.n+', "barrio_del_cruce": "'+esc(r.c.b||'fuera de los polígonos')+'"}</code>'};
  for(const id of['vaI','vaR'])$(id).addEventListener('input',draw);$('vaC').addEventListener('change',draw);
  el.querySelectorAll('[data-r],[data-i]').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.r!==undefined)$('vaR').value=b.dataset.r;if(b.dataset.i!==undefined)$('vaI').value=b.dataset.i;draw()}));draw();return draw};

/* mapas */
function svgMapa(id,w,h,colorear){
  const sx=w/G.ancho,sy=h/G.alto,s=Math.min(sx,sy),ox=(w-G.ancho*s)/2,oy=(h-G.alto*s)/2;
  const P=(x,y)=>(ox+x*s).toFixed(1)+','+(oy+(G.alto-y)*s).toFixed(1);
  let out='<svg id="'+id+'" viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Mapa de barrios y veredas de Medellín">';
  for(const b of G.barrios){out+='<path d="'+b.r.map(r=>'M'+r.map(([x,y])=>P(x,y)).join('L')+'Z').join('')+'" fill="'+colorear(b)+'" stroke="#9badc4" stroke-width=".4" data-n="'+esc(b.n)+'" data-c="'+b.c+'"/>'}
  return{out,P,s,ox,oy};
}
SIMS.mapaP1=function(el){
  const mx=Math.max(...G.barrios.map(b=>b.c));
  const col=b=>{if(!b.c)return '#f7f9fc';const t=b.c/mx;const r=Math.round(241-t*(241-21)),g=Math.round(246-t*(246-94)),bl=Math.round(253-t*(253-239));return `rgb(${r},${g},${bl})`};
  const {out}=svgMapa('m1',420,360,col);
  const top=[...G.barrios].sort((a,b)=>b.c-a.c).slice(0,5);
  el.innerHTML='<div class="mapa-grid"><div class="mapa">'+out+'</svg><p class="mini-read" id="m1O">Pasar el cursor por un barrio.</p></div><div><p class="mini-read"><b>'+D.resultados.referencia.p1.asignados+'</b> cruces dentro de un polígono; '+D.resultados.referencia.p1.fuera+' fuera. '+G.barrios.filter(b=>b.c>0).length+' barrios con al menos un cruce.</p><div class="barras">'+
    top.map(b=>'<div class="barra"><span>'+esc(b.n)+'</span><i style="width:'+b.c/mx*100+'%"></i><b>'+b.c+'</b></div>').join('')+'</div></div></div>';
  el.querySelectorAll('path').forEach(p=>{p.addEventListener('mouseenter',()=>{$('m1O').textContent=p.dataset.n+': '+p.dataset.c+' cruces'});p.addEventListener('focus',()=>{$('m1O').textContent=p.dataset.n+': '+p.dataset.c+' cruces'})});
  return null};

SIMS.mapaP2=function(el){
  el.innerHTML='<div class="mapa-grid"><div class="mapa"><canvas id="m2C" style="width:100%;height:340px" role="img" aria-label="Cruces semafóricos alrededor del cruce elegido con un círculo del radio elegido"></canvas></div>'+
    '<div><label for="m2R">Radio <output id="m2O"></output></label><input id="m2R" type="range" min="50" max="1000" step="10" value="300"><div class="chips"><button data-r="300">300 m</button><button data-r="500">500 m</button><button data-r="1000">1 000 m</button></div>'+
    '<label for="m2F" style="margin-top:10px">Campo en el que «125» es el número del cruce</label><select id="m2F"><option value="id_cruce">id_cruce</option><option value="OBJECTID">OBJECTID</option></select><p class="mini-read" id="m2T" aria-live="polite"></p></div></div>';
  const c=$('m2C');
  const draw=()=>{const radio=+$('m2R').value,campo=$('m2F').value;$('m2O').textContent=radio+' m';const r=crucesCercanos(campo,125,radio);
    const rect=c.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);c.width=Math.max(1,Math.round(rect.width*dpr));c.height=Math.max(1,Math.round(rect.height*dpr));const x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);
    const W=Math.max(10,rect.width),H=Math.max(10,rect.height),ver=1300,s=Math.min(W,H)/(2*ver),cx=W/2,cy=H/2;
    x.clearRect(0,0,W,H);x.fillStyle='#f7f9fc';x.fillRect(0,0,W,H);
    const T=(px,py)=>[cx+(px-r.c.x)*s,cy-(py-r.c.y)*s];
    x.strokeStyle='#c9d6e8';x.lineWidth=.6;for(const b of G.barrios)for(const ring of b.r){x.beginPath();ring.forEach(([px,py],i)=>{const [a,bb]=T(px,py);i?x.lineTo(a,bb):x.moveTo(a,bb)});x.closePath();x.stroke()}
    x.fillStyle=css('--blue')+'22';x.strokeStyle=css('--blue');x.lineWidth=1.5;x.beginPath();x.arc(cx,cy,radio*s,0,7);x.fill();x.stroke();
    for(const p of G.cruces){const d=Math.hypot(p.x-r.c.x,p.y-r.c.y);if(d>ver*1.5)continue;const [a,b]=T(p.x,p.y);x.fillStyle=d>0&&d<=radio?css('--blue'):'#9badc4';x.beginPath();x.arc(a,b,d>0&&d<=radio?3.5:2.5,0,7);x.fill()}
    x.fillStyle='#c0392b';x.beginPath();x.arc(cx,cy,5,0,7);x.fill();x.fillStyle='#122b49';x.font='12px sans-serif';x.fillText('cruce 125 ('+campo+')',cx+8,cy-8);
    x.fillStyle='#526781';x.font='11px sans-serif';x.fillText('ventana de '+(2*ver/1000)+' km · EPSG:9377',8,H-8);
    $('m2T').innerHTML='<b>'+r.n+' cruces</b> a '+radio+' m o menos del cruce con '+campo+' = 125 (en '+esc(r.c.b)+'), sin contar el propio cruce. Con el otro campo: '+crucesCercanos(campo==='id_cruce'?'OBJECTID':'id_cruce',125,radio).n+'.'};
  $('m2R').addEventListener('input',draw);$('m2F').addEventListener('change',draw);el.querySelectorAll('[data-r]').forEach(b=>b.addEventListener('click',()=>{$('m2R').value=b.dataset.r;draw()}));draw();return draw};

/* ---------- trazas reales ---------- */
const TR=D.trazas;
function tokensDe(t){return t.pasos.filter(p=>p.tipo==='modelo').reduce((a,p)=>a+(p.tokens_entrada||0)+(p.tokens_salida||0),0)}
function mensajeHTML(m,activo){
  const rol={system:'sistema',user:'usuario',assistant:'modelo',tool:'herramienta'}[m.role]||m.role;
  let cuerpo='';
  if(m.role==='assistant'&&m.tool_calls&&m.tool_calls.length)cuerpo=m.tool_calls.map(t=>'<code>'+esc(t.function.name)+'('+esc(t.function.arguments)+')</code>').join('<br>')+(m.content?'<br>'+esc(m.content):'');
  else cuerpo=esc(m.content||'').replace(/\n/g,'<br>');
  return '<div class="msg msg-'+m.role+(activo?' msg-on':'')+'"><span>'+rol+'</span><div>'+cuerpo+'</div></div>';
}
function pasosAMensajes(t){
  const ms=[{role:'system',content:D.resultados.instrucciones},{role:'user',content:t.pregunta}];
  for(const p of t.pasos){if(p.tipo==='modelo'){ms.push({role:'assistant',content:p.contenido,tool_calls:p.tool_calls.map(c=>({function:{name:c.name,arguments:c.arguments}})),tokens:p})}else ms.push({role:'tool',content:JSON.stringify(p.resultado)})}
  return ms;
}
SIMS.ciclo=function(el){
  const t=TR.ejemplo_p2;const ms=pasosAMensajes(t);let paso=2;
  el.innerHTML='<div class="chips"><button id="ciP">◀ paso anterior</button><button id="ciN">paso siguiente ▶</button><span id="ciC" class="mini-read"></span></div><div id="ciM" class="msgs"></div><p class="mini-read" id="ciT"></p>';
  const draw=()=>{paso=Math.max(2,Math.min(ms.length,paso));$('ciM').innerHTML=ms.slice(0,paso).map((m,i)=>mensajeHTML(m,i===paso-1)).join('');
    const ult=ms[paso-1];let txt='';
    if(ult.role==='user')txt='Contexto inicial: instrucciones + pregunta + esquemas de las cuatro herramientas. Se envía al modelo.';
    else if(ult.role==='assistant'&&ult.tool_calls.length)txt='El modelo no ejecuta nada: devuelve el nombre de la herramienta y los argumentos en JSON. El programa los valida.'+(ult.tokens.tokens_entrada?' Esta llamada leyó '+ult.tokens.tokens_entrada+' tokens y escribió '+ult.tokens.tokens_salida+' en '+num(ult.tokens.latencia_s,1)+' s.':'');
    else if(ult.role==='tool')txt='Observación: el resultado de la función vuelve como un mensaje de rol «tool» y se añade al contexto. El modelo lo verá en la siguiente llamada.';
    else txt='Respuesta final: el modelo escribe texto sin pedir herramientas; el ciclo termina.'+(ult.tokens.tokens_entrada?' Esta llamada leyó '+ult.tokens.tokens_entrada+' tokens: el contexto creció con la llamada y la observación.':'');
    $('ciC').textContent='mensaje '+paso+' de '+ms.length;$('ciP').disabled=paso<=2;$('ciN').disabled=paso>=ms.length;$('ciT').textContent=txt+(t.simulado?' (Traza del modelo simulado del cuaderno; se reemplaza por la real al correr con Groq.)':' Corrida real: '+t.modelo+'.')};
  $('ciP').addEventListener('click',()=>{paso--;draw()});$('ciN').addEventListener('click',()=>{paso++;draw()});draw();return draw};

SIMS.salida=function(el){
  const cand=TR.corridas.filter(c=>c.tarea==='p4');const t=cand.find(c=>c.correcto)||cand[0];if(!t){el.textContent='Sin trazas de P4.';return null}
  const ms=pasosAMensajes(t);const necesarias=t.iteraciones;
  el.innerHTML='<label for="saT">Tope de iteraciones <output id="saO"></output></label><input id="saT" type="range" min="1" max="6" step="1" value="6"><div id="saM" class="msgs"></div><div id="saE" class="estado" aria-live="polite"></div>';
  const draw=()=>{const tope=+$('saT').value;$('saO').textContent=tope;let k=0,corte=ms.length;
    for(let i=0;i<ms.length;i++){if(ms[i].role==='assistant'){k++;if(k>tope){corte=i;break}}}
    $('saM').innerHTML=ms.slice(0,corte).map(m=>mensajeHTML(m,false)).join('');const e=$('saE');
    if(corte<ms.length){e.className='estado no';e.innerHTML='<b>Tope alcanzado en '+tope+(tope===1?' iteración':' iteraciones')+'.</b> El programa corta el ciclo sin respuesta final; necesitaba '+necesarias+'. Sin tope, un modelo que insistiera en una herramienta inexistente giraría sin fin.'}
    else{e.className='estado si';e.innerHTML='<b>Terminó por respuesta final en '+necesarias+(necesarias===1?' iteración':' iteraciones')+'.</b> '+(t.correcto?'La respuesta declara que no hay capa de accidentes, sin inventar una cifra.':'La respuesta no cumplió el criterio: se muestra tal cual.')+(t.simulado?' (Traza simulada.)':' ('+t.modelo+', intento '+t.intento+'.)')}};
  $('saT').addEventListener('input',draw);draw();return draw};

SIMS.contextoTokens=function(el){
  const cand=TR.corridas.filter(c=>c.tarea==='p3');const t=cand.find(c=>c.correcto)||cand[0];
  const llamadas=t?t.pasos.filter(p=>p.tipo==='modelo'):[];const real=llamadas.some(p=>p.tokens_entrada>0);
  el.innerHTML='<canvas id="ctC" style="width:100%;height:230px" role="img" aria-label="Tokens de entrada de cada llamada al modelo en la pregunta 3"></canvas><label for="ctF">Si la herramienta devolviera la tabla entera en vez de un resumen: filas añadidas al contexto <output id="ctO"></output></label><input id="ctF" type="range" min="0" max="42673" step="100" value="0"><p class="mini-read" id="ctT"></p>';
  const c=$('ctC');
  const draw=()=>{const filas=+$('ctF').value;$('ctO').textContent=filas.toLocaleString('es-CO')+' filas';
    const rect=c.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);c.width=Math.max(1,Math.round(rect.width*dpr));c.height=Math.max(1,Math.round(rect.height*dpr));const x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);
    const W=Math.max(10,rect.width),H=Math.max(10,rect.height);x.clearRect(0,0,W,H);
    const tokFila=35,extra=filas*tokFila,vals=llamadas.map((p,i)=>(real?p.tokens_entrada:800+i*300)+(i>0?extra:0)),lim=131072;
    const mx=Math.max(lim*1.05,...vals),n=vals.length||1,bw=Math.min(90,(W-80)/n-20);
    x.strokeStyle='#dae4f0';x.beginPath();x.moveTo(50,H-30);x.lineTo(W-10,H-30);x.stroke();
    const Y=v=>H-30-(v/mx)*(H-50);
    x.strokeStyle='#c0392b';x.setLineDash([5,4]);x.beginPath();x.moveTo(50,Y(lim));x.lineTo(W-10,Y(lim));x.stroke();x.setLineDash([]);x.fillStyle='#c0392b';x.font='11px sans-serif';x.fillText('ventana de contexto de gpt-oss-20b: 131 072 tokens',56,Y(lim)-5);
    vals.forEach((v,i)=>{const bx=60+i*(bw+20);x.fillStyle=v>lim?'#c0392b':css('--blue');x.fillRect(bx,Y(v),bw,H-30-Y(v));x.fillStyle='#122b49';x.font='12px sans-serif';x.fillText('llamada '+(i+1),bx,H-14);x.fillText(v.toLocaleString('es-CO'),bx,Y(v)-6)});
    $('ctT').innerHTML=(real?'Tokens de entrada que midió la API en cada llamada de la pregunta 3 ('+t.modelo+'): el contexto crece con cada llamada y cada observación.':'Barras ilustrativas: la traza es simulada y no trae tokens; al correr con Groq se usan los medidos.')+
      (filas>0?' Si la herramienta devolviera las '+filas.toLocaleString('es-CO')+' filas en vez de un resumen, con unos '+tokFila+' tokens por fila entrarían '+extra.toLocaleString('es-CO')+' tokens más'+(vals.some(v=>v>lim)?': la ventana no alcanza y la llamada falla.':'.'):'')};
  $('ctF').addEventListener('input',draw);draw();return draw};

/* ---------- recuperación léxica real ---------- */
const DICC=D.diccionario;
const raiz=w=>w.length>4&&w.endsWith('s')?w.slice(0,-1):w;
function tf(t){const m=new Map();for(const w0 of palabras(t)){if(w0.length<3)continue;const w=raiz(w0);m.set(w,(m.get(w)||0)+1)}return m}
SIMS.tfidf=function(el){
  const docs=DICC.map(d=>({...d,tf:tf(d.texto)}));const N=docs.length;const df=new Map();for(const d of docs)for(const w of d.tf.keys())df.set(w,(df.get(w)||0)+1);
  const idf=w=>Math.log((N+1)/((df.get(w)||0)+1))+1;
  el.innerHTML='<label for="rgQ">Pregunta</label><input id="rgQ" type="text" value="¿en qué barrio hubo más hurtos en 2022?" maxlength="90"><p class="mini-lbl">Fragmentos ordenados por parecido con la pregunta (barra = similitud de 0 a 1; a la derecha, las palabras que comparten)</p><div id="rgR" class="barras"></div><div id="rgD" class="estado si"></div>';
  const draw=()=>{const q=tf($('rgQ').value);const sc=docs.map(d=>{let s=0,na=0,nb=0;for(const [w,c] of q){const a=c*idf(w);na+=a*a;const b=(d.tf.get(w)||0)*idf(w);s+=a*b}for(const [w,c] of d.tf){const b=c*idf(w);nb+=b*b}return{d,s:na&&nb?s/Math.sqrt(na*nb):0,comunes:[...q.keys()].filter(w=>d.tf.has(w))}}).sort((a,b)=>b.s-a.s);
    const mx=sc[0].s||1;$('rgR').innerHTML=sc.slice(0,5).map(r=>'<div class="barra"><span>'+esc(r.d.titulo)+'</span><i style="width:'+Math.max(2,r.s/mx*100)+'%"></i><b>'+num(r.s,2)+'</b><small>'+esc(r.comunes.join(', ')||'—')+'</small></div>').join('');
    $('rgD').innerHTML=sc[0].s>0?'<b>Fragmento que entra al contexto:</b> «'+esc(sc[0].d.texto)+'»':'<b>Ningún fragmento comparte palabras con la pregunta:</b> no entra nada al contexto.'};
  $('rgQ').addEventListener('input',draw);draw();return draw};

/* ---------- enrutamiento por reglas ---------- */
SIMS.ruta=function(el){
  const reglas=[['accidente|siniestro|choque','no respondible (no hay capa)','#c0392b'],['hurto|robo','hurtos_por_barrio','#008c9b'],['cerca|cercan|radio|a menos de|metros','cruces_cercanos','#008c9b'],['cruce|semaf|barrio','contar_por_barrio','#008c9b']];
  const pres=Object.values(D.resultados.preguntas).concat(['¿Cuántos hurtos hubo cerca del cruce 125?','¿Qué barrio tiene más cámaras?']);
  el.innerHTML='<label for="ruQ">Pregunta</label><input id="ruQ" type="text" value="'+esc(pres[4])+'" maxlength="90"><div class="chips">'+pres.map((p,i)=>'<button data-q="'+esc(p)+'">P'+(i+1)+'</button>').join('')+'</div><div id="ruR" class="estado"></div><table class="tabla" id="ruT"><thead><tr><th>si la pregunta contiene…</th><th>va a…</th></tr></thead><tbody>'+reglas.map(r=>'<tr><td><code>'+esc(r[0])+'</code></td><td style="color:'+r[2]+'">'+esc(r[1])+'</td></tr>').join('')+'</tbody></table>';
  const draw=()=>{const q=$('ruQ').value.toLowerCase();const r=reglas.find(r=>new RegExp(r[0]).test(q));const o=$('ruR');
    if(!r){o.className='estado no';o.innerHTML='<b>Ninguna regla coincide:</b> el enrutador no sabe adónde enviarla. Un clasificador con modelo de lenguaje cubriría más formas de preguntar, con el mismo límite: elige una rama, no combina dos.';return}
    const mezcla=/hurto|robo/.test(q)&&/cerca|cercan|radio|metros/.test(q);
    o.className='estado '+(mezcla?'no':'si');o.innerHTML='<b>Rama elegida: '+esc(r[1])+'</b> (regla «'+esc(r[0])+'»).'+(mezcla?' La pregunta pide hurtos <i>y</i> distancia a un cruce: ninguna rama hace las dos cosas. El enrutamiento falla cuando la pregunta cruza dos capas; un agente podría encadenar dos herramientas.':'')};
  $('ruQ').addEventListener('input',draw);el.querySelectorAll('[data-q]').forEach(b=>b.addEventListener('click',()=>{$('ruQ').value=b.dataset.q;draw()}));draw();return draw};

/* ---------- pass@k ---------- */
SIMS.passk=function(el){
  const res=D.resultados.resumen;const p0=res.length?res[0].exito:0.6;
  el.innerHTML='<label for="pkP">Proporción de intentos que aciertan (p) <output id="pkO"></output></label><input id="pkP" type="range" min="0" max="1" step="0.05" value="'+p0+'"><div class="chips">'+res.map(r=>'<button data-p="'+r.exito+'">'+esc(r.tarea)+' · '+esc(r.modelo.split('/')[1])+' ('+num(r.exito,2)+')</button>').join('')+'</div><canvas id="pkC" style="width:100%;height:230px" role="img" aria-label="Curvas de pass arroba k y pass elevado a k para k de 1 a 10"></canvas><p class="mini-read" id="pkT"></p>';
  const c=$('pkC');
  const draw=()=>{const p=+$('pkP').value;$('pkO').textContent=num(p,2);const rect=c.getBoundingClientRect(),dpr=Math.min(devicePixelRatio||1,2);c.width=Math.max(1,Math.round(rect.width*dpr));c.height=Math.max(1,Math.round(rect.height*dpr));const x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);
    const W=Math.max(10,rect.width),H=Math.max(10,rect.height),X=k=>50+(k-1)*(W-70)/9,Y=v=>H-30-v*(H-50);x.clearRect(0,0,W,H);
    x.strokeStyle='#dae4f0';x.beginPath();x.moveTo(50,H-30);x.lineTo(W-10,H-30);x.moveTo(50,10);x.lineTo(50,H-30);x.stroke();x.fillStyle='#526781';x.font='11px sans-serif';for(let k=1;k<=10;k++)x.fillText(k,X(k)-3,H-14);x.fillText('1',36,Y(1)+4);x.fillText('0',36,Y(0)+4);x.fillText('k = intentos →',W-90,H-2);
    const curva=(f,col)=>{x.strokeStyle=col;x.lineWidth=2.5;x.beginPath();for(let k=1;k<=10;k++){const v=f(k);k===1?x.moveTo(X(k),Y(v)):x.lineTo(X(k),Y(v))}x.stroke();for(let k=1;k<=10;k++){x.fillStyle=col;x.beginPath();x.arc(X(k),Y(f(k)),3,0,7);x.fill()}};
    curva(k=>1-Math.pow(1-p,k),css('--blue'));curva(k=>Math.pow(p,k),'#c0392b');
    x.fillStyle=css('--blue');x.fillText('pass@k: al menos un acierto en k intentos',60,20);x.fillStyle='#c0392b';x.fillText('pass^k: los k intentos aciertan',60,36);
    $('pkT').innerHTML='Con p = '+num(p,2)+': pass@3 = '+num(1-Math.pow(1-p,3),2)+' y pass^3 = '+num(Math.pow(p,3),2)+'. Un sistema que debe acertar <i>siempre</i> se mide con pass^k; uno al que basta acertar alguna vez, con pass@k.'};
  $('pkP').addEventListener('input',draw);el.querySelectorAll('[data-p]').forEach(b=>b.addEventListener('click',()=>{$('pkP').value=b.dataset.p;draw()}));draw();return draw};

/* ---------- resultados del cuaderno (tablas) ---------- */
SIMS.evals=function(el){
  const r=D.resultados;const tareas=[...new Set(r.resumen.map(x=>x.tarea))];
  let h='<table class="tabla"><thead><tr><th>tarea</th><th>criterio</th>'+r.modelos.map(m=>'<th>'+esc(m.split('/')[1])+'<br><small>aciertos / '+r.intentos+'</small></th>').join('')+'<th>iteraciones</th><th>tokens</th><th>latencia</th></tr></thead><tbody>';
  for(const t of tareas){const filas=r.resumen.filter(x=>x.tarea===t);h+='<tr><td><b>'+t.toUpperCase()+'</b></td><td>'+esc(r.casos[t])+'</td>'+filas.map(f=>'<td class="'+(f.exito>=0.8?'ok':f.exito>=0.5?'medio':'mal')+'">'+Math.round(f.exito*r.intentos)+' / '+r.intentos+'</td>').join('')+'<td>'+num(filas.reduce((a,f)=>a+f.iteraciones,0)/filas.length,1)+'</td><td>'+Math.round(filas.reduce((a,f)=>a+f.tokens,0)/filas.length).toLocaleString('es-CO')+'</td><td>'+num(filas.reduce((a,f)=>a+f.latencia_s,0)/filas.length,1)+' s</td></tr>'}
  el.innerHTML=h+'</tbody></table><p class="mini-read">'+(r.modo==='simulado'?'Cifras del modelo simulado (siempre acierta y no mide tokens): se reemplazan por las corridas reales con Groq.':'Corridas reales en GroqCloud el '+r.fecha+'; tokens y latencia son promedios por intento medidos por la API.')+'</p>';return null};

SIMS.trazas=function(el){
  const r=D.resultados;const tareas=[...new Set(TR.corridas.map(c=>c.tarea))];
  el.innerHTML='<div class="form3"><label>tarea <select id="trT">'+tareas.map(t=>'<option value="'+t+'">'+t.toUpperCase()+' · '+esc(r.preguntas[t])+'</option>').join('')+'</select></label><label>modelo <select id="trM">'+r.modelos.map(m=>'<option value="'+esc(m)+'">'+esc(m)+'</option>').join('')+'</select></label><label>intento <select id="trI">'+Array.from({length:r.intentos},(_,i)=>'<option value="'+(i+1)+'">'+(i+1)+'</option>').join('')+'</select></label></div><div id="trE" class="estado"></div><div id="trX" class="msgs"></div>';
  const draw=()=>{const t=TR.corridas.find(c=>c.tarea===$('trT').value&&c.modelo===$('trM').value&&c.intento===+$('trI').value);if(!t){$('trX').innerHTML='';$('trE').textContent='No hay esa corrida.';return}
    const ms=pasosAMensajes(t);$('trX').innerHTML=ms.slice(1).map(m=>mensajeHTML(m,false)).join('');const e=$('trE');e.className='estado '+(t.correcto?'si':'no');
    e.innerHTML='<b>'+(t.correcto?'Cumple el criterio':'No cumple el criterio')+'</b> («'+esc(r.casos[t.tarea])+'») · '+t.iteraciones+(t.iteraciones===1?' iteración':' iteraciones')+' · '+(t.tokens||0).toLocaleString('es-CO')+' tokens · '+num(t.latencia_s||0,1)+' s · terminó por '+esc(t.terminado_por)+(t.simulado?' · traza simulada':'')};
  for(const id of['trT','trM','trI'])$(id).addEventListener('change',draw);draw();return draw};

SIMS.inyeccion=function(el){
  const r=D.resultados.inyeccion;el.innerHTML=Object.entries(r).map(([m,v])=>'<div class="estado '+(v.obedecio?'no':'si')+'"><b>'+esc(m)+'</b> — '+(v.obedecio?'obedeció la instrucción inyectada':'no la obedeció')+'.<br>Respuesta: «'+esc(v.respuesta||'(sin texto)')+'»</div>').join('')+'<p class="mini-read">'+(D.resultados.modo==='simulado'?'El modelo simulado copia el nombre tal cual: muestra el riesgo, no mide nada.':'Respuestas reales del cuaderno, sección 9, el '+D.resultados.fecha+'.')+'</p>';return null};

SIMS.memoria=function(el){
  const r=D.resultados.memoria;el.innerHTML=Object.entries(r).map(([m,v])=>{const a=v.sin_memoria.llamadas[0]||{},b=v.con_memoria.llamadas[0]||{};return '<div class="dos"><div class="estado"><b>'+esc(m)+' · sin memoria</b><br>llamada: <code>'+esc(JSON.stringify(a))+'</code><br>«'+esc(v.sin_memoria.respuesta||'')+'»</div><div class="estado si"><b>con memoria (radio 300 m, campo id_cruce)</b><br>llamada: <code>'+esc(JSON.stringify(b))+'</code><br>«'+esc(v.con_memoria.respuesta||'')+'»</div></div>'}).join('')+'<p class="mini-read">Pregunta sin radio: «'+esc('¿Cuántos cruces semafóricos hay cerca del cruce 125?')+'». La memoria es el archivo memoria_agente.json leído e insertado en las instrucciones.</p>';return null};

SIMS.sinHerramientas=function(el){
  const r=D.resultados.sin_herramientas;el.innerHTML=Object.entries(r).map(([m,v])=>'<div class="estado no"><b>'+esc(m)+'</b> (sin herramientas)<br>«'+esc(v.contenido||'(sin texto)')+'»</div>').join('')+'<p class="mini-read">Referencia calculada con la capa: La Candelaria, 45 cruces. Lo que diga el modelo sin herramientas no se puede comprobar desde el texto.</p>';return null};

SIMS.calidad=function(el){
  const q=D.resultados.referencia.calidad_hurtos;const filas=[['registros','registros en el CSV'],['sin coordenadas','sin latitud o longitud: no se pueden ubicar'],['duplicados exactos','filas idénticas en todas las columnas'],['registros de 2023 sin coordenadas','todos los de 2023 carecen de coordenadas'],['longitud fuera de rango','longitud mayor que −75° (un punto con −0,0007)']];
  el.innerHTML='<table class="tabla"><thead><tr><th>comprobación</th><th>valor</th><th>qué significa</th></tr></thead><tbody>'+filas.map(([k,d])=>'<tr><td>'+esc(k)+'</td><td><b>'+(q[k]||0).toLocaleString('es-CO')+'</b></td><td>'+esc(d)+'</td></tr>').join('')+'</tbody></table>';return null};

/* ---------- arranque ---------- */
const activas=[];
window.iniciarSims=function(root){for(const el of (root||document).querySelectorAll('[data-sim]')){if(el.dataset.listo)continue;el.dataset.listo='1';const f=SIMS[el.dataset.sim];if(!f){el.textContent='Simulación no encontrada: '+el.dataset.sim;continue}try{const r=f(el);if(r)activas.push(r)}catch(e){console.error(el.dataset.sim,e);el.textContent='Error en la simulación '+el.dataset.sim+': '+e.message}}};
window.redibujarSims=function(){activas.forEach(f=>{try{f()}catch(e){console.error(e)}})};
})();

/* ---------- flujos animados sobre los grafos de LangGraph ---------- */
(function(){
const $=(id)=>document.getElementById(id);
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const D=window.DATOS;const SIMS=window.SIMS;
let contador=0;

/* disposición por niveles (camino más largo desde __start__, ignorando aristas de retroceso) */
function disponer(grafo){
  const ids=grafo.nodes.map(n=>n.id),edges=grafo.edges.map(e=>({s:e.source,t:e.target,c:!!e.conditional}));
  const sal={};ids.forEach(i=>sal[i]=[]);edges.forEach(e=>sal[e.s].push(e.t));
  const nivel={},estado={};const atras=new Set();
  (function dfs(u,prof){estado[u]=1;nivel[u]=Math.max(nivel[u]||0,prof);for(const v of sal[u]){if(estado[v]===1){atras.add(u+'>'+v);continue}if(!(estado[v]===2&&nivel[v]>prof))dfs(v,prof+1)}estado[u]=2})('__start__',0);
  ids.forEach(i=>{if(nivel[i]===undefined)nivel[i]=0});
  const maxN=Math.max(...Object.values(nivel));ids.forEach(i=>{if(i==='__end__')nivel[i]=maxN});
  const porNivel={};ids.forEach(i=>{(porNivel[nivel[i]]=porNivel[nivel[i]]||[]).push(i)});
  const W=Math.max(1,maxN),pos={};
  for(const [n,lista] of Object.entries(porNivel)){lista.forEach((id,k)=>{pos[id]={x:+n/W,y:(k+1)/(lista.length+1)}})}
  /* disposiciones fijas para los grafos con ciclo, que el nivel no resuelve bien */
  const FIJAS={'__end__,__start__,herramientas,modelo':{__start__:[0,0.28],modelo:[0.42,0.28],herramientas:[0.86,0.28],__end__:[0.42,0.86]}};
  const clave=[...ids].sort().join(',');
  if(FIJAS[clave]){for(const [id,[x,y]] of Object.entries(FIJAS[clave]))pos[id]={x,y}}
  return{pos,edges:edges.map(e=>({...e,atras:atras.has(e.s+'>'+e.t)}))};
}
function nombre(id){return id==='__start__'?'inicio':id==='__end__'?'fin':id.replace(/_/g,' ')}

/* dibuja el grafo en un SVG y devuelve utilidades para animar */
function dibujar(svg,grafo,opc){
  const {pos,edges}=disponer(grafo);const porNivel={};Object.values(pos).forEach(p=>{porNivel[p.x]=(porNivel[p.x]||0)+1});const maxPN=Math.max(...Object.values(porNivel));
  const W=opc.w||760,H=opc.h||Math.max(100,36+46*maxPN),mx=opc.nw?opc.nw*0.55:70,my=Math.min(40,H/4),nw=opc.nw||126,nh=opc.fs?30:36;
  const P=id=>({x:mx+pos[id].x*(W-2*mx),y:my+pos[id].y*(H-2*my)});
  const uid='m'+(++contador);let s=`<defs><marker id="${uid}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#7f94b3"/></marker></defs>`;
  const caminos={};
  for(const e of edges){const a=P(e.s),b=P(e.t);let d;const esp=id=>id==='__start__'||id==='__end__';
    const ra=esp(e.s)?14:nw/2,rb=esp(e.t)?14:nw/2;
    if(e.atras){const x1=a.x-ra*0.3,y1=a.y-nh/2,x2=b.x+rb*0.3,y2=b.y-nh/2;d=`M${x1},${y1} C${x1},${y1-60} ${x2},${y2-60} ${x2},${y2}`}
    else{const dx=b.x-a.x,dy=b.y-a.y;const x1=a.x+(dx>0?ra:dx<0?-ra:0),x2=b.x-(dx>0?rb:dx<0?-rb:0);const y1=a.y+(dx===0?Math.sign(dy)*nh/2:0),y2=b.y-(dx===0?Math.sign(dy)*nh/2:0);
      d=Math.abs(dy)<2?`M${x1},${y1} L${x2},${y2}`:`M${x1},${y1} C${(x1+x2)/2},${y1} ${(x1+x2)/2},${y2} ${x2},${y2}`}
    caminos[e.s+'>'+e.t]=d;
    s+=`<path class="fl-arista" d="${d}" fill="none" stroke="#9fb0c8" stroke-width="${e.atras?1.6:2}" ${e.c||e.atras?'stroke-dasharray="6,5"':''} marker-end="url(#${uid})"/>`}
  for(const id of Object.keys(pos)){const p=P(id);
    if(id==='__start__'||id==='__end__'){s+=`<g class="fl-nodo" data-n="${id}"><circle cx="${p.x}" cy="${p.y}" r="14" fill="#fff" stroke="#8ca0ba" stroke-width="2"/><text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-size="10.5" fill="#526781">${nombre(id)}</text></g>`}
    else{s+=`<g class="fl-nodo" data-n="${id}"><rect x="${p.x-nw/2}" y="${p.y-nh/2}" width="${nw}" height="${nh}" rx="9" fill="#fff" stroke="${css('--blue')}" stroke-width="2"/><text x="${p.x}" y="${p.y+5}" text-anchor="middle" font-size="${opc.fs||14}" font-weight="600" fill="#122b49">${esc(nombre(id))}</text></g>`}}
  s+=`<g class="fl-fichas"></g>`;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.innerHTML=s;
  return{P,caminos,svgNS:'http://www.w3.org/2000/svg'};
}

/* una simulación de flujo: grafo + guion (lista de pasos; cada paso: {n:[nodos activos], de:[nodos de origen], t:título, x:texto}) */
function flujo(el,grafo,guion,opc){
  opc=opc||{};const id='fl'+(++contador);
  el.innerHTML=`<div class="fl-cab"><div class="chips"><button id="${id}p">◀</button><button id="${id}n">paso ▶</button><button id="${id}a">▶ reproducir</button><button id="${id}r">reiniciar</button><span class="mini-read" id="${id}c"></span></div>${opc.selector||''}</div>`+
    `<svg class="fl-svg" role="img" aria-label="${esc(opc.alt||'Grafo del patrón y recorrido de la pregunta')}"></svg><div class="fl-panel" id="${id}t" aria-live="polite"></div>`;
  const svg=el.querySelector('svg');let G=dibujar(svg,grafo,opc),paso=-1,timer=null,gu=guion;
  const nodos=()=>[...svg.querySelectorAll('.fl-nodo')];
  function pintar(){nodos().forEach(g=>{const on=paso>=0&&gu[paso].n.includes(g.dataset.n);const f=g.querySelector('rect,circle');f.setAttribute('fill',on?'#eaf1ff':'#fff');f.setAttribute('stroke',on?css('--navy'):(g.dataset.n.startsWith('__')?'#8ca0ba':css('--blue')));f.setAttribute('stroke-width',on?3:2)});
    const fichas=svg.querySelector('.fl-fichas');fichas.innerHTML='';
    if(paso>=0){const p=gu[paso];(p.de||[]).forEach((origen,k)=>{const dest=p.n[Math.min(k,p.n.length-1)];const d=G.caminos[origen+'>'+dest];if(!d)return;
      const c=document.createElementNS(G.svgNS,'circle');c.setAttribute('r','7');c.setAttribute('fill',css('--teal'));fichas.appendChild(c);
      const an=document.createElementNS(G.svgNS,'animateMotion');an.setAttribute('dur','0.7s');an.setAttribute('fill','freeze');an.setAttribute('path',d);c.appendChild(an);an.beginElement&&an.beginElement()})}
    $(id+'c').textContent=paso<0?'0 / '+gu.length:(paso+1)+' / '+gu.length;
    $(id+'t').innerHTML=paso<0?'<span class="fl-tit">'+esc(opc.inicio||'Pulsar «paso» para recorrer el grafo con la pregunta real.')+'</span>':'<span class="fl-tit">'+esc(gu[paso].t)+'</span>'+esc(gu[paso].x||'').replace(/\n/g,'<br>');
    $(id+'p').disabled=paso<0;$(id+'n').disabled=paso>=gu.length-1}
  $(id+'n').addEventListener('click',()=>{if(paso<gu.length-1){paso++;pintar()}});
  $(id+'p').addEventListener('click',()=>{if(paso>=0){paso--;pintar()}});
  $(id+'r').addEventListener('click',()=>{clearInterval(timer);timer=null;paso=-1;pintar()});
  $(id+'a').addEventListener('click',()=>{if(timer){clearInterval(timer);timer=null;$(id+'a').textContent='▶ reproducir';return}$(id+'a').textContent='❚❚ pausa';paso=-1;pintar();timer=setInterval(()=>{if(paso<gu.length-1){paso++;pintar()}else{clearInterval(timer);timer=null;$(id+'a').textContent='▶ reproducir'}},1500)});
  pintar();
  return {setGuion(g){gu=g;paso=-1;pintar()},setGrafo(gr){G=dibujar(svg,gr,opc);paso=-1;pintar()}};
}
const FL=D.flujos;
function simFlujo(clave,opc){return function(el){const f=FL[clave];if(!f){el.textContent='Sin datos para el flujo '+clave;return null}flujo(el,D.grafos[f.grafo].grafo,f.guion,Object.assign({alt:f.alt,inicio:f.inicio},opc||{}));return null}}
SIMS.flujoAgente=simFlujo('agente_p2',{h:150});
SIMS.flujoAgenteP3=simFlujo('agente_p3',{h:150});
SIMS.flujoCadena=simFlujo('cadena',{h:110});
SIMS.flujoParalelo=simFlujo('paralelo',{h:190});
SIMS.flujoEvaluador=simFlujo('evaluador',{h:130});
SIMS.flujoOrquestador=simFlujo('orquestador',{h:130});
SIMS.flujoInyeccion=simFlujo('inyeccion',{h:150});
SIMS.flujoCalificador=simFlujo('calificador',{h:150});
SIMS.flujoReact=simFlujo('react',{h:150});
SIMS.flujoRuta=function(el){const sel='<select id="flrSel">'+Object.keys(FL.ruta).map(k=>'<option value="'+k+'">'+k.toUpperCase()+' · '+esc(D.resultados.preguntas[k])+'</option>').join('')+'</select>';
  const f=FL.ruta.p1;const api=flujo(el,D.grafos.ruta.grafo,f.guion,{h:175,selector:sel,alt:'Grafo de enrutamiento con cuatro ramas',inicio:f.inicio});
  $('flrSel').addEventListener('change',e=>api.setGuion(FL.ruta[e.target.value].guion));return null};
SIMS.workflowVsAgente=function(el){el.innerHTML='<div class="dos"><div><p class="fl-rotulo">Flujo de trabajo: encadenamiento (grafo de LangGraph)</p><div id="wvaA"></div></div><div><p class="fl-rotulo">Agente: el modelo decide cuándo parar</p><div id="wvaB"></div></div></div>';
  flujo($('wvaA'),D.grafos.cadena.grafo,FL.cadena.guion,{h:120,w:560,nw:106,inicio:FL.cadena.inicio});flujo($('wvaB'),D.grafos.agente.grafo,FL.agente_p3.guion,{h:170,w:560,nw:106,inicio:FL.agente_p3.inicio});return null};
SIMS.grafosPatrones=function(el){const claves=['cadena','ruta','paralelo','evaluador','orquestador'];el.innerHTML='<div class="fl-grid">'+claves.map(k=>'<div><p class="fl-rotulo">'+esc({cadena:'encadenamiento · pasos fijos en fila',ruta:'enrutamiento · elegir una rama',paralelo:'paralelización · varias a la vez',evaluador:'evaluador–optimizador · proponer y revisar',orquestador:'orquestador · repartir subtareas'}[k])+'</p><svg id="gp_'+k+'" class="fl-svg"></svg></div>').join('')+'</div><p class="mini-read">Los cinco grafos tal como los dibuja LangGraph desde el código del cuaderno; las aristas punteadas son condicionales.</p>';
  claves.forEach(k=>dibujar($('gp_'+k),D.grafos[k].grafo,{w:440,h:k==='ruta'?160:k==='cadena'?66:k==='paralelo'?130:92,nw:84,fs:11}));return null};
SIMS.costos=function(el){const c=D.resultados.costos||[];const mx=Math.max(1,...c.map(x=>x.tokens)),ml=Math.max(0.01,...c.map(x=>x.latencia_s));
  el.innerHTML='<div class="barras">'+c.map(x=>'<div class="barra b3"><span>'+esc(x["patrón"])+'</span><i style="width:'+(x.tokens/mx*100)+'%"></i><b>'+x.tokens.toLocaleString('es-CO')+' tokens</b><i class="t" style="width:'+(x.latencia_s/ml*100)+'%"></i><b>'+String(x.latencia_s).replace('.',',')+' s</b><small>'+x["llamadas al modelo"]+' llamadas</small></div>').join('')+'</div><p class="mini-read">'+(D.resultados.modo==='simulado'?'Modelo simulado: sin tokens ni tiempos reales; se reemplazan por las corridas con Groq.':'Pregunta cruzada («'+esc(D.resultados.pregunta_cruzada||'')+'») y pregunta 2 resueltas con cada patrón en GroqCloud, '+D.resultados.fecha+'. Azul: tokens; verde: segundos.')+'</p>';return null};
SIMS.memoriaArchivo=function(el){const mem=JSON.stringify({radio_por_defecto_m:300,campo_de_identificador:'id_cruce'},null,1);
  el.innerHTML='<div class="chips"><button data-s="1">sesión 1: sin memoria</button><button data-s="2">entre sesiones: el programa escribe el archivo</button><button data-s="3">sesión 2: con memoria</button></div><div class="dos"><div class="estado" id="maA"></div><div class="estado" id="maB"></div></div>';
  const pintar=s=>{$('maA').innerHTML=s===2?'<b>memoria_agente.json</b><pre class="codigo chico">'+esc(mem)+'</pre>':s===3?'<b>memoria_agente.json</b> (se lee al empezar)<pre class="codigo chico">'+esc(mem)+'</pre>':'<b>memoria_agente.json</b><br><i>no existe todavía</i>';
    $('maB').innerHTML=s===1?'<b>Instrucciones de la llamada</b><br>«…Indica siempre las unidades.»<br><br>Pregunta: «¿Cuántos cruces hay cerca del cruce 125?» → el modelo no sabe qué radio usar.':s===2?'<b>Parámetros del modelo</b><br>no cambian: siguen siendo los del entrenamiento.':'<b>Instrucciones de la llamada</b><br>«…Indica siempre las unidades. <mark>Preferencias guardadas del usuario: {"radio_por_defecto_m": 300, "campo_de_identificador": "id_cruce"}</mark>»<br><br>La misma pregunta → el modelo tiene el radio en el contexto.'};
  el.querySelectorAll('[data-s]').forEach(b=>b.addEventListener('click',()=>pintar(+b.dataset.s)));pintar(1);return null};
})();
