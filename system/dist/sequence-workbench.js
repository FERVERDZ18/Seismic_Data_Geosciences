/* One host document and router for the observatory's scientific workspaces. */
(function(global){
  'use strict';
  const base=new URL('.',document.currentScript.src);
  const HTML="<select hidden aria-label=\"Study language\" data-seq-id=\"language\"><option value=\"es\">Español</option><option value=\"en\">English</option></select><a hidden data-seq-id=\"back\"></a>\n<p class=\"eyebrow\" data-en=\"RETAINED CATALOGUE COMPARISON\">COMPARACIÓN DE CATÁLOGOS CONSERVADOS</p>\n<h2 class=\"workspace-title\" data-en=\"Earthquake sequences across catalogues\">Secuencias sísmicas entre catálogos</h2>\n<p id=\"seq-intro\" data-seq-id=\"intro\" data-en=\"Detect groups of nearby earthquakes in time and space; inspect which source records and decisions change their classification.\">Detecta grupos de sismos cercanos en tiempo y espacio; examina qué registros y decisiones cambian su clasificación.</p>\n<nav class=\"workspace-nav\" aria-label=\"Vistas del estudio\"><a href=\"?view=explorer&amp;lang=es\" data-study-view=\"explorer\" data-en=\"Catalogue explorer\">Explorador general</a><a href=\"?view=cases&amp;lang=es\" data-study-view=\"cases\" data-en=\"Compared families · Figure 4\">Familias comparadas · Figura 4</a><a href=\"?view=diagnostics&amp;lang=es\" data-study-view=\"diagnostics\" data-en=\"Magnitudes and T–R · Figure 3\">Magnitudes y T–R · Figura 3</a><a href=\"?view=benchmark&amp;lang=es\" data-study-view=\"benchmark\" data-en=\"Search performance · Figure 2\">Búsqueda · Figura 2</a></nav>\n<div id=\"seq-explorerWorkspace\" data-seq-id=\"explorerWorkspace\">\n<form id=\"seq-controls\" data-seq-id=\"controls\"><label><span data-en=\"Region\">Región</span><select id=\"seq-region\" data-seq-id=\"region\"><option value=\"mexico\">México · SSN / ComCat</option><option value=\"alaska\">Alaska · ComCat (una fuente)</option></select></label>\n<label><span data-en=\"Reported magnitude\">Magnitud reportada</span><select id=\"seq-cut\" data-seq-id=\"cut\"><option value=\"4.5\">≥ 4.5 · principal</option><option value=\"4.1\">≥ 4.1 · sensibilidad</option><option value=\"3.5\">≥ 3.5 · diagnóstico de escala</option></select></label>\n<label><span data-en=\"Method\">Método</span><select id=\"seq-method\" data-seq-id=\"method\"><option value=\"nn\">Vecino más cercano · Zaliapin–Ben-Zion</option><option value=\"gk\">Ventanas · Gardner–Knopoff</option></select></label>\n<label><span data-en=\"Magnitude weight\">Peso de magnitud</span><select id=\"seq-weightPolicy\" data-seq-id=\"weightPolicy\"><option value=\"fixed\">w = 1</option><option value=\"reported_b\">b aparente por fuente · sensibilidad</option></select></label>\n<label><span data-en=\"Records\">Registros</span><select id=\"seq-membership\" data-seq-id=\"membership\"><option value=\"native\">Cada catálogo completo</option><option value=\"common\">Sólo parejas candidatas comunes</option></select></label>\n<button id=\"seq-calculate\" data-seq-id=\"calculate\" type=\"submit\" data-en=\"Calculate sequences\">Calcular secuencias</button></form>\n<details id=\"seq-explanation\" data-seq-id=\"explanation\" open><summary data-en=\"What does this method mean?\">¿Qué significa este método?</summary><p id=\"seq-methodExplanation\" data-seq-id=\"methodExplanation\"></p><p class=\"warning\" data-en=\"Operational groups are not proof of physical triggering. A sequence is not a duplicate; no source observation is erased. Reported magnitudes retain their original scales. None of these cuts certifies completeness.\">Los grupos operativos no prueban que un sismo haya causado otro. Una secuencia no es un duplicado: ningún registro original se borra. Las magnitudes conservan sus escalas originales. Estos cortes no certifican completitud.</p></details>\n<p id=\"seq-status\" data-seq-id=\"status\" role=\"status\" aria-live=\"polite\"></p><p id=\"seq-fitWarning\" data-seq-id=\"fitWarning\" class=\"warning\" role=\"status\"></p><p id=\"seq-agreement\" data-seq-id=\"agreement\"></p>\n<section id=\"seq-caseSelector\" data-seq-id=\"caseSelector\" class=\"case-selector\"><div class=\"heading\"><h2 data-en=\"Inspect a sequence\">Examinar una secuencia</h2><label><span data-en=\"Case\">Caso</span><select id=\"seq-case\" data-seq-id=\"case\"><option value=\"all\">Todo el intervalo</option><option value=\"2017\">2017 · Tehuantepec · −7 / +30 días · 150 km</option><option value=\"2022\">2022 · Michoacán · −7 / +30 días · 150 km</option></select></label><label class=\"family-toggle\"><input id=\"seq-familyExtent\" data-seq-id=\"familyExtent\" type=\"checkbox\" disabled><span data-en=\"Show the complete anchor family\">Mostrar toda la familia del ancla</span></label></div><p id=\"seq-caseDescription\" data-seq-id=\"caseDescription\"></p></section>\n<div class=\"legend\"><span class=\"main\" data-en=\"Largest event in group\">Mayor evento del grupo</span><span class=\"associated\" data-en=\"Associated\">Asociado</span><span class=\"isolated\" data-en=\"Isolated\">Aislado</span></div>\n<p id=\"seq-anchorKey\" data-seq-id=\"anchorKey\" hidden class=\"anchor-key\" data-en=\"★ Reference ComCat anchor · dashed circle: 150 km. Source epicentres retain their original coordinates.\">★ Ancla ComCat de referencia · círculo discontinuo: 150 km. Los epicentros conservan sus coordenadas originales.</p>\n<section id=\"seq-maps\" data-seq-id=\"maps\" class=\"grid\" aria-label=\"Comparación de epicentros\"></section>\n<section id=\"seq-cases\" data-seq-id=\"cases\"><h2 data-en=\"Event timelines\">Cronología de los eventos</h2><div id=\"seq-timelines\" data-seq-id=\"timelines\" class=\"grid\"></div></section>\n<section id=\"seq-diagnostics\" data-seq-id=\"diagnostics\" class=\"grid\"></section>\n\n<section id=\"seq-record\" data-seq-id=\"record\" aria-live=\"polite\"><h2 data-en=\"Source record\">Registro de origen</h2><p data-en=\"Select an epicentre or a point in the timeline to inspect its record and nearest parent.\">Selecciona un epicentro o un punto temporal para consultar su registro y su vecino anterior.</p><div id=\"seq-recordDetails\" data-seq-id=\"recordDetails\"></div></section>\n<div class=\"exports\"><button id=\"seq-exportCsv\" data-seq-id=\"exportCsv\" disabled data-en=\"Export classifications · CSV\">Exportar clasificaciones · CSV</button><button id=\"seq-exportJson\" data-seq-id=\"exportJson\" disabled data-en=\"Export computation · JSON\">Exportar cálculo · JSON</button><button id=\"seq-exportSvg\" data-seq-id=\"exportSvg\" disabled data-en=\"Export visible figures · SVG\">Exportar figuras visibles · SVG</button></div>\n<p class=\"warning\" data-en=\"Case controls crop the figures only; CSV and JSON retain the complete calculation. A family can extend over years and large distances without proving a continuous physical sequence.\">Los controles de caso sólo recortan las figuras; CSV y JSON conservan el cálculo completo. Una familia puede extenderse por años y grandes distancias sin demostrar una secuencia física continua.</p>\n<details><summary data-en=\"Inspect the exported computation\">Consultar el cálculo exportado</summary><p data-en=\"Prepare a readable copy of the same JSON available for download, including source IDs, parameters and classifications.\">Prepara una copia legible del mismo JSON descargable, con IDs de origen, parámetros y clasificaciones.</p><button id=\"seq-showJson\" data-seq-id=\"showJson\" disabled data-en=\"Show computation JSON\">Mostrar JSON del cálculo</button><textarea id=\"seq-visibleJson\" data-seq-id=\"visibleJson\" readonly hidden aria-label=\"Computation JSON\"></textarea></details>\n<details><summary data-en=\"Method, sources and reproducibility\">Método, fuentes y reproducción</summary><p id=\"seq-parameters\" data-seq-id=\"parameters\"></p><p data-en=\"Training: 2016–2020; temporal evaluation: 2021–2025 for Mexico. Alaska uses 2020–2022 training and 2023–2025 evaluation on one source. Candidate pairs use 30 s / 50 km, one-to-one maximum-cardinality, minimum-cost assignment; they are not reviewed identities. Calibration remains fixed when catalogue membership changes.\">Desarrollo: 2016–2020; evaluación temporal: 2021–2025 en México. Alaska usa desarrollo 2020–2022 y evaluación 2023–2025 con una sola fuente. Las parejas candidatas usan 30 s / 50 km y asignación uno a uno de máxima cardinalidad y coste mínimo; no son identidades revisadas. Al cambiar la membresía se conserva la calibración.</p><p><a href=\"https://doi.org/10.1002/jgrb.50179\">Zaliapin y Ben-Zion (2013)</a> · <a href=\"https://doi.org/10.1785/BSSA0640051363\">Gardner y Knopoff (1974)</a> · <a href=\"https://github.com/GEMScienceTools/oq-mbtk/tree/d13e63bebedcc6788e0ec88e8632957b749d3b60\">GEM · asociación de catálogos</a></p><p id=\"seq-provenance\" data-seq-id=\"provenance\"></p><p data-en=\"Sources: SSN, UNAM Institute of Geophysics; USGS ComCat and contributing networks. Provider terms and original attribution remain applicable. This research view is not an operational alert service.\">Fuentes: SSN, Instituto de Geofísica, UNAM; USGS ComCat y redes contribuyentes. Se conservan los términos y créditos originales. Esta vista de investigación no es un servicio operativo de alertas.</p></details>\n</div>\n<section id=\"seq-articleFigures\" data-seq-id=\"articleFigures\" hidden><section id=\"seq-nativeCases\" data-seq-id=\"nativeCases\" hidden></section><section id=\"seq-nativeDiagnostics\" data-seq-id=\"nativeDiagnostics\" hidden></section><section id=\"seq-nativePerformance\" data-seq-id=\"nativePerformance\" hidden></section></section>\n<section id=\"seq-nativeRecord\" data-seq-id=\"nativeRecord\" hidden><h2 data-en=\"Inspected source record\">Registro de origen consultado</h2><div id=\"seq-nativeRecordDetails\" data-seq-id=\"nativeRecordDetails\"></div></section>\n";
  const ASSETS={
  "styles": [
    "sequences/native-cases.css?v=f1a0c444cdec",
    "sequences/native-diagnostics.css?v=fb5e5064e0fb",
    "sequences/native-performance.css?v=81fe49618a67",
    "sequence-workbench.css?v=e1c454015d71"
  ],
  "scripts": [
    [
      "sequences/sequence-view.js?v=e65d91309b6e",
      "SeismicSequenceView"
    ],
    [
      "sequences/study-data.js?v=d60c8cb76058",
      "SeismicStudyData"
    ],
    [
      "sequences/case-analysis.js?v=2d98bcbd011a",
      "CaseAnalysis"
    ],
    [
      "sequences/native-cases.js?v=cfb018fca0a9",
      "NativeCases"
    ],
    [
      "sequences/diagnostics-math.js?v=d2bd3cd95d06",
      "SequenceDiagnosticsMath"
    ],
    [
      "sequences/native-diagnostics.js?v=b0cbb719c7e0",
      "NativeDiagnostics"
    ],
    [
      "sequences/performance-math.js?v=0b1458e203b1",
      "PerformanceMath"
    ],
    [
      "sequences/native-performance.js?v=7a4cd1c74ee3",
      "NativePerformance"
    ],
    [
      "sequences/app.js?v=19015ecc9ab2",
      "SeismicSequenceExplorer"
    ]
  ]
};
  let dependencies=null;const loadedStyles=new Map();
  const url=path=>new URL(path,base).href;
  function style(path){
    if(!loadedStyles.has(path))loadedStyles.set(path,new Promise((resolve,reject)=>{const node=document.createElement('link');node.rel='stylesheet';node.href=url(path);node.onload=()=>resolve();node.onerror=()=>{node.remove();loadedStyles.delete(path);reject(new Error('Could not load workspace stylesheet: '+path));};document.head.append(node);}));
    return loadedStyles.get(path);
  }
  function script(path,name){if(global[name])return Promise.resolve();return new Promise((resolve,reject)=>{const node=document.createElement('script');node.src=url(path);node.async=false;node.onload=()=>resolve();node.onerror=()=>{node.remove();reject(new Error('Could not load workspace component: '+path));};document.head.append(node);});}
  function load(){if(!dependencies)dependencies=(async()=>{await Promise.all(ASSETS.styles.map(style));for(const [path,name]of ASSETS.scripts)await script(path,name);})().catch(error=>{dependencies=null;throw error;});return dependencies;}
  function buildURL(state={view:'cases',case:'2017'}){
    const value=global.SeismicSequenceView?global.SeismicSequenceView.normalize(state):state;
    const params=new URLSearchParams('workspace=sequences');
    const keys=['lang','region','cut','method','weight','membership','case','extent','view','comparison','source','diagnostic_panel','pair_cut','benchmark_metric','scale','radius','before','after','benchmark_n','panel'];
    const query=global.SeismicSequenceView?new URLSearchParams(global.SeismicSequenceView.query(value)):new URLSearchParams(keys.filter(key=>value[key]!=null).map(key=>[key,String(value[key])]));
    for(const [key,val]of query)if(keys.includes(key))params.set(key,val);
    if(!params.has('view'))params.set('view',value.view||'cases');
    const target=new URL('index.html',base);target.search=params.toString();return target.href;
  }
  async function mount(container,options={}){
    if(!container||typeof container.replaceChildren!=='function')throw new TypeError('An application workspace container is required');
    let controller=null,destroyed=false,isVisible=true,initializing=null,pendingState=options.state||{view:'cases',case:'2017'},pendingLanguage=options.getLanguage?.()||pendingState.lang||'es';
    const api={getState:()=>controller?controller.getState():({...pendingState,lang:pendingLanguage}),buildURL:state=>buildURL(state||api.getState()),async setState(state){pendingState=state;if(['es','en'].includes(state.lang))pendingLanguage=state.lang;if(controller)return controller.setState({...state,lang:pendingLanguage});},async setLanguage(lang){pendingLanguage=lang==='en'?'en':'es';if(controller)return controller.setLanguage(pendingLanguage);},setVisible(value){isVisible=Boolean(value);controller?.setVisible(isVisible);},destroy(){destroyed=true;controller?.destroy();container.replaceChildren();}};
    async function initialize(){
    const loading=document.createElement('p');loading.setAttribute('role','status');loading.textContent=pendingLanguage==='en'?'Loading earthquake sequence views…':'Cargando las vistas de secuencias sísmicas…';container.replaceChildren(loading);
    try{
      await load();if(destroyed)return;
      const host=document.createElement('div');host.className='sequence-workspace';host.innerHTML=HTML;container.replaceChildren(host);
      controller=global.SeismicSequenceExplorer.mount(host,{state:pendingState,getLanguage:()=>pendingLanguage,buildURL,onStateChange:(state,meta)=>{pendingState=state;pendingLanguage=state.lang;options.onStateChange?.(state,meta);}});
      controller.setVisible(isVisible);await controller.ready;if(destroyed)return;
      options.onStateChange?.(controller.getState(),{push:false,initial:true});
    }catch(error){controller?.destroy();controller=null;if(!destroyed){const message=document.createElement('p'),retry=document.createElement('button');message.setAttribute('role','alert');message.className='warning';message.textContent=(pendingLanguage==='en'?'The sequence workspace could not load: ':'No se pudo cargar el espacio de secuencias: ')+error.message;retry.type='button';retry.textContent=pendingLanguage==='en'?'Retry':'Reintentar';retry.addEventListener('click',()=>start());container.replaceChildren(message,retry);}
    }
    }
    function start(){if(!initializing)initializing=initialize().finally(()=>{initializing=null;});return initializing;}
    await start();return Object.freeze(api);
  }
  global.SeismicSequenceWorkbench=Object.freeze({mount,load,buildURL});
})(window);
