/* Scientific workspace. Classifications are calculated in a browser worker. */
(function (global) {
  'use strict';
  const scriptBase=new URL('.',document.currentScript.src);
  function mount(host,options={}) {
  if(!host)throw new TypeError('A sequence workspace host is required');
  const $ = id => host.querySelector('[data-seq-id="'+id+'"]'), NS = 'http://www.w3.org/2000/svg';
  const colors = {main:'#b93624', associated:'#d28b09', isolated:'#347bad'};
  const initialView=SeismicSequenceView.normalize({...SeismicSequenceView.parse(location.search),...options.state,lang:options.getLanguage?.()||options.state?.lang||SeismicSequenceView.parse(location.search).lang});
  let lang = initialView.lang;
  let viewState=initialView,panelFocusPending=initialView.panel!=='all';
  const nativeMounts=new Map(),nativeRendered=new Map(),nativeOperations=new Map();
  let destroyed=false,visible=true,notifySuppressed=1,pendingPush=false,lastCalculationKey=null;
  let manifest, cached = new Map(), active = {}, results = {}, currentPairs = [], workers = [], request = 0, basemap, diagnostics, latestTiming=null, firstDisplay=true;
  let fitState={unsupported:[],weighted:false};
  const t = (es,en) => lang === 'en' ? en : es;
  function status(text) {$('status').textContent = text;}
  function describe() {
    $('methodExplanation').textContent = $('method').value === 'gk' ? t(
      'Gardner y Knopoff son los autores de un método publicado en 1974. Alrededor de cada sismo grande se abre una ventana de días y kilómetros que depende de su magnitud. Los registros dentro de esa ventana forman un grupo. Aquí sirve como comparación sencilla: no elimina registros ni demuestra relaciones físicas.',
      'Gardner and Knopoff published this method in 1974. Each large event defines a window of days and kilometres that depends on its magnitude. Records inside the window form an operational group. It is a simple comparison method; it neither deletes records nor proves physical triggering.') : t(
      'El método de Zaliapin y Ben-Zion (2013) busca para cada registro un sismo anterior cercano, considerando el tiempo, la distancia y la magnitud del posible padre. Se conservan los enlaces por debajo de un umbral calculado con 2016–2020. Sus componentes forman grupos; el mayor evento de cada grupo es su representante operativo. No se usa el adelgazamiento aleatorio de fondo de 2020 para definir estas secuencias.',
      'Zaliapin and Ben-Zion (2013) link each record to an earlier event using time, distance and parent magnitude. Links below a threshold fitted on 2016–2020 are retained. Their components form groups, with the largest event as operational representative. The 2020 random background-thinning mask is not used to identify these sequences.');
  }
  function language() {
    host.lang=lang; $('language').value = lang;host.querySelector('.workspace-nav').setAttribute('aria-label',t('Vistas de secuencias','Earthquake sequence views'));
    host.querySelectorAll('[data-en]').forEach(e => {if (!e.dataset.es) e.dataset.es=e.textContent; e.textContent=lang==='en'?e.dataset.en:e.dataset.es;});
    $('region').options[1].textContent=t('Alaska · ComCat (una fuente)','Alaska · ComCat (one source)');
    $('method').options[0].textContent='Zaliapin–Ben-Zion (2013)';
    $('method').options[1].textContent='Gardner–Knopoff (1974)';
    $('membership').options[0].textContent=t('Cada catálogo completo','Each complete catalogue');
    $('membership').options[1].textContent=t('Sólo parejas candidatas comunes','Common candidate pairs only');
    $('weightPolicy').options[1].textContent=t('b aparente · sensibilidad','Apparent b · sensitivity');
    $('case').options[0].textContent=t('Todo el intervalo','Full interval');
    $('maps').setAttribute('aria-label',t('Comparación de epicentros','Epicentre comparison'));
    $('visibleJson').setAttribute('aria-label',t('JSON del cálculo','Computation JSON'));
    ['4.5','4.1','3.5'].forEach((c,i) => $('cut').options[i].textContent='≥ '+c+' · '+[t('principal','primary'),t('sensibilidad','sensitivity'),t('diagnóstico de escala','scale diagnostic')][i]);
    $('back').textContent=t('← Observatorio','← Observatory');
    describe(); if(latestTiming&&viewState.view==='explorer'&&lastCalculationKey===selectionKey()){render();calculationStatus();renderFitWarning();}
    rememberView();
  }
  function viewSettings(){return {...viewState,lang,region:$('region').value,cut:$('cut').value,method:$('method').value,weight:$('weightPolicy').value,membership:$('membership').value,case:$('case').value,extent:$('familyExtent').checked?'family':'local'};}
  function rememberView(){viewState=SeismicSequenceView.normalize(viewSettings());if(!notifySuppressed)options.onStateChange?.({...viewState},{push:pendingPush});pendingPush=false;updateStudyNavigation();}
  function selectionKey(){return JSON.stringify(['region','cut','method','weightPolicy','membership'].map(id=>$(id).value));}
  function focusPanel(){if(!visible||!panelFocusPending||viewState.view!=='cases'||viewState.panel==='all')return;const selectors={full:'[data-case-map="full"]',local:'[data-case-map="local"]',timeline:'.nc-timeline-card',inspector:'.nc-inspector'};const target=$('nativeCases').querySelector(selectors[viewState.panel]);if(target){panelFocusPending=false;target.scrollIntoView({block:'start',behavior:'auto'});}}
  function applyView(v){
    viewState=v;
    lang=v.lang;for(const key of ['region','cut','method','membership','case'])$(key).value=v[key];
    $('weightPolicy').value=v.weight;$('familyExtent').checked=v.extent==='family';configureOptions();
  }
  function updateStudyNavigation(){
    host.querySelectorAll('[data-study-view]').forEach(a=>{
      const view=a.dataset.studyView,settings={...viewState,view};
      if(view==='cases'&&settings.case==='all')settings.case='2017';
      a.href=options.buildURL?options.buildURL(settings):SeismicSequenceView.query(settings);
      if(view===viewState.view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
    });
  }
  function inspectNative(value){options.onRecord?.(value);}
  function clearNativeRecord(){$('nativeRecord').hidden=true;$('nativeRecordDetails').replaceChildren();}
  function nativeSignature(state){return JSON.stringify({...state,panel:'all'});}
  function rememberNativePresentation(patch,meta){
    if(destroyed||viewState.view!=='cases'||Object.entries(meta.context||{}).some(([key,value])=>String(viewState[key])!==String(value)))return;
    viewState=SeismicSequenceView.normalize({...viewState,...patch});
    nativeRendered.set('cases',nativeSignature(viewState));updateStudyNavigation();
    if(!notifySuppressed)options.onStateChange?.({...viewState},{push:false,presentation:true});
  }
  async function activateStudy(){
    if(destroyed)return;
    const view=viewState.view,registry={cases:['nativeCases',window.NativeCases],diagnostics:['nativeDiagnostics',window.NativeDiagnostics],benchmark:['nativePerformance',window.NativePerformance]};
    $('explorerWorkspace').hidden=view!=='explorer';$('articleFigures').hidden=view==='explorer';
    for(const [name,[id]] of Object.entries(registry))$(id).hidden=view!==name;
    updateStudyNavigation();if(view==='explorer')return;
    const [id,api]=registry[view],container=$(id);
    if(!api){container.textContent=t('La vista todavía no está disponible.','This view is not available yet.');return;}
    // Serialize each native controller. A completed mount describes the state
    // it received, never the later global route that may have changed meanwhile.
    const operation=(nativeOperations.get(view)||Promise.resolve()).catch(()=>{}).then(async()=>{
      if(destroyed||viewState.view!==view)return;
      try{
        if(!nativeMounts.has(view)){
          const mountedState={...viewState},mountedSignature=nativeSignature(mountedState);
          const nativeOptions={client:SeismicStudyData,state:mountedState,buildURL:options.buildURL,onStateChange:(patch,meta={})=>meta.presentation?rememberNativePresentation(patch,meta):navigateStudy(patch),onRecord:value=>{if(viewState.view===view)inspectNative(value);}};
          nativeMounts.set(view,Promise.resolve(api.mount(container,nativeOptions)).then(value=>{if(!destroyed)nativeRendered.set(view,mountedSignature);return value;}));
        }
        await nativeMounts.get(view);if(destroyed||viewState.view!==view)return;
        const desired={...viewState},signature=nativeSignature(desired);
        if(nativeRendered.get(view)!==signature){await api.setState(desired);if(destroyed)return;nativeRendered.set(view,signature);}
        if(viewState.view===view){api.resize?.();focusPanel();}
      }catch(error){if(destroyed)return;nativeMounts.delete(view);nativeRendered.delete(view);container.replaceChildren();const p=document.createElement('p'),retry=document.createElement('button');p.className='warning';p.textContent=t('No se pudo abrir el análisis: ','Could not open the analysis: ')+error.message;retry.type='button';retry.textContent=t('Reintentar','Retry');retry.addEventListener('click',activateStudy);container.append(p,retry);}
    });
    nativeOperations.set(view,operation);await operation;
  }
  async function navigateStudy(patch,push=false,restoring=false){
    const next=restoring?SeismicSequenceView.normalize({...patch,lang:patch.lang||lang}):SeismicSequenceView.transition(viewState,{...patch,lang:patch.lang||lang});
    pendingPush=push;
    applyView(next);language();clearNativeRecord();await activateStudy();
    if(next.view==='explorer'&&manifest){if(!latestTiming||lastCalculationKey!==selectionKey())await calculate();else{render();calculationStatus();}}
  }
  function calculationStatus(){
    const elapsed=Object.values(results).reduce((s,r)=>s+r.metadata.total_ms,0),n=Object.values(active).reduce((s,r)=>s+r.length,0);
    status(t('Calculado en el navegador','Calculated in the browser')+' · '+n.toLocaleString(lang)+' '+t('registros','records')+' · '+Math.round(elapsed).toLocaleString(lang)+' ms '+t('cálculo','calculation')+(latestTiming?' · '+Math.round(latestTiming.calculation_to_render_ms).toLocaleString(lang)+' ms '+t('hasta la vista','to rendered view'):''));
  }
  function renderFitWarning(){
    $('fitWarning').textContent=fitState.unsupported.length?fitState.unsupported.join(', ')+': '+t('el ajuste tiene un corte numérico, pero no respalda dos modos separados. Estas agrupaciones son una sensibilidad exploratoria; no hay certificación estadística de familias.','the fit returns a numerical cutoff but does not support two separate modes. These groups are an exploratory sensitivity; they are not statistically certified families.'):'';
    if(fitState.weighted)$('fitWarning').textContent+=' '+t('Se usa el b aparente propio de cada fuente, con su corte de desarrollo congelado. Es una sensibilidad numérica, no una calibración física de magnitudes.','Each source uses its own apparent b and frozen development cutoff. This is a numerical sensitivity, not a physical magnitude calibration.');
  }
  async function checked(path) {return SeismicStudyData.checked(path);}
  function calculateWorker(rows, method, threshold, token, weight=1) {
    return new Promise((resolve,reject)=>{
      const worker=new Worker(new URL('worker.js',scriptBase).href); workers.push(worker);
      worker.onmessage=e=>{worker.terminate(); if(e.data.request!==token) return reject(new Error('Stale worker result')); e.data.error?reject(new Error(e.data.error)):resolve(e.data.result);};
      worker.onerror=e=>{worker.terminate(); reject(new Error(e.message));};
      worker.postMessage({request:token,rows,method,parameters:{d:1.6,w:weight,q:.5,backend:'kd'},threshold});
    });
  }
  async function calculate(event) {
    if(event) event.preventDefault(); const token=++request, calculationKey=selectionKey(), overallStarted=performance.now();
    workers.forEach(w=>w.terminate()); workers=[]; results={}; active={};
    latestTiming=null;lastCalculationKey=null;['maps','timelines','diagnostics','recordDetails'].forEach(id=>$(id).replaceChildren());$('agreement').textContent='';
    $('calculate').disabled=true; ['exportCsv','exportJson','exportSvg','showJson'].forEach(id=>$(id).disabled=true);$('visibleJson').value='';$('visibleJson').hidden=true;
    status(t('Verificando datos y calculando en el navegador…','Verifying data and calculating in the browser…'));
    try {
      const key=$('cut').value.replace('.','_'), data=await checked('inputs_'+key+'.json');if(token!==request||selectionKey()!==calculationKey)return;
      const calibration=await checked('calibration.json');if(token!==request||selectionKey()!==calculationKey)return;
      const matching=$('region').value==='mexico'?await checked('candidates_'+key+'.json'):{pairs:[]};if(token!==request||selectionKey()!==calculationKey)return;
      currentPairs=matching.pairs;
      const sources=$('region').value==='alaska'?['alaska']:['ssn','usgs'];
      const common=$('membership').value==='common' && sources.length===2;
      const ids={ssn:new Set(currentPairs.map(p=>p.ssn)),usgs:new Set(currentPairs.map(p=>p.usgs))};
      const method=$('method').value, unsupported=[];
      for(const source of sources) {
        const rows=data.sources[source].filter(r=>!common||ids[source].has(r.record_id));
        active[source]=rows;
        const c=$('weightPolicy').value==='reported_b'?calibration.weight_modes?.reported_b?.[source]:calibration.cuts[$('cut').value]?.[source];
        if(method==='nn' && (!c || !Number.isFinite(c.threshold_log10))) throw new Error(t('Umbral de desarrollo no estimable para esta selección.','Development threshold is not estimable for this selection.'));
        if(method==='nn' && !c.diagnostics?.two_mode_BIC_guard_passed) unsupported.push(source==='ssn'?'SSN':source);
        // Sequential workers make timing interpretable and leave the UI responsive.
        results[source]=await calculateWorker(rows,method,c?.threshold_log10,token,c?.w??1);
        if(token!==request||selectionKey()!==calculationKey)return;
      }
      const elapsed=Object.values(results).reduce((s,r)=>s+r.metadata.total_ms,0);
      lastCalculationKey=calculationKey;fitState={unsupported,weighted:$('weightPolicy').value==='reported_b'};renderFitWarning();
      calculationStatus();
      $('parameters').textContent=Object.entries(results).map(([s,r])=>s+': '+JSON.stringify(r.metadata)).join(' | ');
      $('provenance').textContent=t('Entradas verificadas por SHA-256; fecha de corte: ','Inputs verified by SHA-256; snapshot: ')+manifest.snapshot_utc+'. '+t('Clasificaciones recalculadas; calibración de desarrollo fija.','Classifications recalculated; development calibration fixed.');
      render();
      latestTiming={worker_kernel_and_numeric_preparation_ms:elapsed,calculation_to_render_ms:performance.now()-overallStarted,first_navigation_to_render_ms:firstDisplay?performance.now():null,scope:'calculation includes input fetch/cache, SHA-256, parsing, Worker startup/transfers and synchronous SVG/canvas render; first navigation also includes initial manifest/diagnostics/basemap loads; browser paint is not awaited'};firstDisplay=false;
      calculationStatus();
      ['exportCsv','exportJson','exportSvg','showJson'].forEach(id=>$(id).disabled=false);
    } catch(error) {if(token===request)status(t('No se pudo completar: ','Calculation failed: ')+error.message);}
    finally {if(token===request) $('calculate').disabled=false;}
  }
  function element(tag,attrs={},text='') {const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;return e;}
  function chart(title,width=600,height=350) {
    const svg=element('svg',{xmlns:NS,viewBox:`0 0 ${width} ${height}`,class:'plot',role:'img','aria-label':title});svg.append(element('title',{},title));return svg;
  }
  function axes(svg,xlim,ylim,xlabel,ylabel,w=600,h=350) {
    const box={left:55,right:w-20,top:20,bottom:h-46};
    const x=v=>box.left+(v-xlim[0])/(xlim[1]-xlim[0])*(box.right-box.left),y=v=>box.bottom-(v-ylim[0])/(ylim[1]-ylim[0])*(box.bottom-box.top);
    for(let i=0;i<=4;i++) {
      const a=xlim[0]+i*(xlim[1]-xlim[0])/4,b=ylim[0]+i*(ylim[1]-ylim[0])/4;
      svg.append(element('line',{x1:x(a),x2:x(a),y1:box.top,y2:box.bottom,class:'gridline'}),element('line',{x1:box.left,x2:box.right,y1:y(b),y2:y(b),class:'gridline'}));
      svg.append(element('text',{x:x(a),y:box.bottom+18,'text-anchor':'middle'},Math.abs(a)>=100? a.toFixed(0):a.toFixed(1)),element('text',{x:box.left-8,y:y(b)+4,'text-anchor':'end'},b.toFixed(1)));
    }
    svg.append(element('text',{x:(box.left+box.right)/2,y:h-7,'text-anchor':'middle'},xlabel),element('text',{transform:`translate(14 ${(box.top+box.bottom)/2}) rotate(-90)`,'text-anchor':'middle'},ylabel));
    return {...box,x,y};
  }
  function card(source,target,subtitle) {const article=document.createElement('article');article.className='card';const h=document.createElement('h2');h.textContent=source==='ssn'?'SSN · México':source==='usgs'?'ComCat · México':'ComCat · Alaska';const p=document.createElement('p');p.className='stats';p.textContent=subtitle;article.append(h,p);$(target).append(article);return article;}
  function point(svg,x,y,source,i,radius=2) {
    const role=results[source].roles[i],dot=element('circle',{cx:x,cy:y,r:radius,fill:colors[role],opacity:role==='main'?.9:.5,class:'dot',tabindex:'0',role:'button','aria-label':active[source][i].record_id});
    dot.append(element('title',{},active[source][i].time_utc+' · M '+active[source][i].magnitude+' · '+role));
    dot.addEventListener('click',()=>inspect(source,i));dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' ')inspect(source,i);});svg.append(dot);
  }
  function scatter(svg,coordinates,source,radius=2) {
    // Draw every record. Raster rendering avoids hundreds of thousands of DOM nodes.
    if(coordinates.length<=12000){coordinates.forEach(([x,y,i])=>point(svg,x,y,source,i,typeof radius==='function'?radius(i):radius));return;}
    const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=700;
    const ctx=canvas.getContext('2d');ctx.scale(2,2);
    for(const [x,y,i] of coordinates){const role=results[source].roles[i];ctx.beginPath();ctx.fillStyle=colors[role];ctx.globalAlpha=role==='main'?.9:.45;ctx.arc(x,y,typeof radius==='function'?radius(i):radius,0,2*Math.PI);ctx.fill();}
    const image=element('image',{href:canvas.toDataURL('image/png'),x:0,y:0,width:600,height:350,role:'img','aria-label':t('Todos los registros; representación raster para esta selección densa','All records; raster rendering for this dense selection')});
    image.addEventListener('click',e=>{const box=svg.getBoundingClientRect(),x=(e.clientX-box.left)*600/box.width,y=(e.clientY-box.top)*350/box.height;let best=Infinity,chosen=-1;for(const [px,py,i] of coordinates){const d=(px-x)**2+(py-y)**2;if(d<best){best=d;chosen=i;}}if(best<=100&&chosen>=0)inspect(source,chosen);});svg.append(image);
  }
  function geographicDistance(a,b) {const rad=Math.PI/180,dy=(b.latitude-a.latitude)*rad,dx=(b.longitude-a.longitude)*rad,h=Math.sin(dy/2)**2+Math.cos(a.latitude*rad)*Math.cos(b.latitude*rad)*Math.sin(dx/2)**2;return 2*6371.0088*Math.asin(Math.sqrt(Math.min(1,h)));}
  function selected() {
    const out={};let anchor=null;
    if($('case').value!=='all' && $('region').value==='mexico') {
      const c=Array.isArray(diagnostics?.cases)?diagnostics.cases.find(v=>String(v.year)===$('case').value):diagnostics?.cases?.[$('case').value];
      if(!c)throw new Error('Selected case is absent from the verified inputs');
      anchor=c.anchor||{record_id:c.anchor_usgs_record_id,time_utc:c.anchor_time_utc,latitude:c.anchor_latitude,longitude:c.anchor_longitude,magnitude:c.anchor_reported_magnitude};
    }
    const wholeFamily=Boolean(anchor&&$('familyExtent').checked);
    for(const [s,rows] of Object.entries(active)) {
      let family=null;
      if(wholeFamily){const c=diagnostics.cases.find(v=>String(v.year)===$('case').value),id=c.clock_FMD_excluded_anchor_record_ids[s],i=rows.findIndex(r=>r.record_id===id);if(i<0)throw new Error('Anchor source record is absent');family=results[s].component[i];}
      out[s]=rows.map((r,i)=>i).filter(i=>wholeFamily?results[s].component[i]===family:!anchor||((Date.parse(rows[i].time_utc)-Date.parse(anchor.time_utc))/86400000>=-7&&(Date.parse(rows[i].time_utc)-Date.parse(anchor.time_utc))/86400000<=30&&geographicDistance(rows[i],anchor)<=150));
    }
    $('caseDescription').textContent=anchor?t('Ventana descriptiva anclada en ','Descriptive window anchored on ')+anchor.time_utc+' · '+anchor.record_id+' · '+t('se conservan los roles calculados con todo el intervalo.','roles remain those calculated over the full interval.'):t('Se muestran todos los registros de la selección. Selecciona un caso para distinguir eventos próximos.','All selected records are shown. Select a case to distinguish nearby events.');
    if(wholeFamily)$('caseDescription').textContent=t('Familias operativas completas que contienen el ancla; se muestra su extensión global en el catálogo, incluidos miembros fuera del episodio local. Los huecos temporales no prueban continuidad física.','Complete operational families containing the anchor; their full catalogue extent is shown, including members outside the local episode. Temporal gaps do not prove physical continuity.');
    return {out,anchor:wholeFamily?null:anchor,referenceAnchor:anchor};
  }
  function mapPlot(source,ids,anchor,referenceAnchor) {
    const rows=active[source],result=results[source],wrap=lon=>source==='alaska'&&lon>0?lon-360:lon;
    let xlim=source==='alaska'?[-170,-130]:[-118,-86],ylim=source==='alaska'?[50,72]:[14,33];
    if(anchor){const lon=Number(anchor.longitude),lat=Number(anchor.latitude);xlim=[lon-2,lon+2];ylim=[lat-1.5,lat+1.5];}
    const counts={main:0,associated:0,isolated:0};for(const i of ids)counts[result.roles[i]]++;
    const c=card(source,'maps',t('Registros: ','Records: ')+ids.length.toLocaleString(lang)+' · '+t('Representantes: ','Representatives: ')+counts.main+' · '+t('Asociados: ','Associated: ')+counts.associated);
    const svg=chart(t('Epicentros y roles operativos','Epicentres and operational roles')),a=axes(svg,xlim,ylim,t('Longitud (°)','Longitude (°)'),t('Latitud (°)','Latitude (°)'));
    const clipId='clip-'+source,def=element('defs'),clip=element('clipPath',{id:clipId});clip.append(element('rect',{x:a.left,y:a.top,width:a.right-a.left,height:a.bottom-a.top}));def.append(clip);svg.append(def);
    function ring(points){return points.map(p=>[wrap(p[0]),p[1]]).filter(p=>p.every(Number.isFinite));}
    for(const f of basemap?.features||[]) {
      const polygons=f.geometry?.type==='Polygon'?[f.geometry.coordinates]:f.geometry?.type==='MultiPolygon'?f.geometry.coordinates:[];
      for(const polygon of polygons)for(const raw of polygon) {
        const ps=ring(raw);if(!ps.some(p=>p[0]>=xlim[0]-1&&p[0]<=xlim[1]+1&&p[1]>=ylim[0]-1&&p[1]<=ylim[1]+1))continue;
        // Clip drawing geometry without changing any source coordinate.
        const d=ps.map((p,i)=>(i?'L':'M')+a.x(p[0])+','+a.y(p[1])).join(' ')+'Z';
        const path=element('path',{d,fill:'#eff2f2',stroke:'#9aaeb5','stroke-width':.7});
        path.setAttribute('clip-path','url(#'+clipId+')');svg.append(path);
      }
    }
    if(anchor && ylim[0]<14){svg.append(element('rect',{x:a.left,y:a.y(14),width:a.right-a.left,height:a.bottom-a.y(14),fill:'#dce2e6',opacity:.9}),element('line',{x1:a.left,x2:a.right,y1:a.y(14),y2:a.y(14),stroke:'#5f7280','stroke-dasharray':'5 4'}),element('text',{x:a.left+8,y:a.bottom-8},t('No consultado: latitud < 14°N','Not queried: latitude < 14°N')));}
    const order=ids.slice().sort((i,j)=>(result.roles[i]==='main')-(result.roles[j]==='main'));
    const coordinates=[];for(const i of order){const r=rows[i],x=wrap(r.longitude);if(x<xlim[0]||x>xlim[1]||r.latitude<ylim[0]||r.latitude>ylim[1])continue;coordinates.push([a.x(x),a.y(r.latitude),i]);}
    scatter(svg,coordinates,source,i=>result.roles[i]==='main'?3:ids.length>5000?1.2:2);
    if(referenceAnchor){
      const circle=SeismicSequenceView.referenceCircle(referenceAnchor).map(p=>a.x(wrap(p.longitude))+','+a.y(p.latitude)).join(' ');
      const line=element('polyline',{points:circle,fill:'none',stroke:'#233d4b','stroke-width':1.4,'stroke-dasharray':'6 4','clip-path':'url(#'+clipId+')'});line.append(element('title',{},'150 km'));svg.append(line);
      const x=a.x(wrap(Number(referenceAnchor.longitude))),y=a.y(Number(referenceAnchor.latitude));
      const star=element('polygon',{points:Array.from({length:10},(_,i)=>{const theta=-Math.PI/2+i*Math.PI/5,r=i%2?3.5:8;return (x+r*Math.cos(theta))+','+(y+r*Math.sin(theta));}).join(' '),fill:'#152d3a',stroke:'#fff','stroke-width':.8,'clip-path':'url(#'+clipId+')'});
      star.append(element('title',{},t('Ancla ComCat de referencia: ','Reference ComCat anchor: ')+referenceAnchor.record_id));svg.append(star);
    }
    c.append(svg);
  }
  function timeline(source,ids,anchor) {
    const rows=active[source],c=card(source,'timelines',t('Magnitud reportada por evento','Reported magnitude by event'));
    const origin=anchor?Date.parse(anchor.time_utc):Date.UTC(source==='alaska'?2020:2016,0,1),scale=anchor?86400000:365.25*86400000;
    const xlim=anchor?[-7,30]:[source==='alaska'?2020:2016,2026],offset=anchor?0:xlim[0];
    const svg=chart(t('Evolución temporal','Temporal evolution')),a=axes(svg,xlim,[Number($('cut').value),8.7],anchor?t('Días desde el ancla','Days since anchor'):t('Año UTC continuo','Continuous UTC year'),t('Magnitud reportada','Reported magnitude'));
    scatter(svg,ids.map(i=>{const r=rows[i];return [a.x((Date.parse(r.time_utc)-origin)/scale+offset),a.y(Number(r.magnitude)),i];}),source,2.2);
    c.append(svg);
  }
  function diagnosticPlot(source) {
    const rows=active[source],r=results[source],c=card(source,'diagnostics',$('method').value==='nn'?t('Separación tiempo–distancia; línea = umbral fijo','Time–distance separation; line = fixed threshold'):t('Distribución de magnitudes reportadas','Reported magnitude distribution'));
    const svg=chart(t('Diagnóstico del método','Method diagnostic'));
    if($('method').value==='nn') {
      const finite=rows.map((_,i)=>i).filter(i=>r.tn[i]>0&&r.rn[i]>0),xs=finite.map(i=>Math.log10(r.rn[i])),ys=finite.map(i=>Math.log10(r.tn[i]));
      const ext=a=>a.reduce((b,v)=>[Math.min(b[0],Math.floor(v)),Math.max(b[1],Math.ceil(v))],[Infinity,-Infinity]);
      if(finite.length){const xl=ext(xs),yl=ext(ys);if(xl[0]===xl[1])xl[1]++;if(yl[0]===yl[1])yl[1]++;const a=axes(svg,xl,yl,'log₁₀ R (kmᵈ)',t('log₁₀ T (años)','log₁₀ T (years)'));const cut=r.metadata.threshold_log10;
        const x0=Math.max(xl[0],cut-yl[1]),x1=Math.min(xl[1],cut-yl[0]);if(x0<=x1)svg.append(element('line',{x1:a.x(x0),x2:a.x(x1),y1:a.y(cut-x0),y2:a.y(cut-x1),stroke:'#333','stroke-dasharray':'6 4'}));
        scatter(svg,finite.map((i,j)=>[a.x(xs[j]),a.y(ys[j]),i]),source,1.7);}
    } else {
      const floor=Number($('cut').value),bins=[];for(let m=floor;m<=8.6;m+=.1)bins.push([m,rows.filter(r=>Number(r.magnitude)>=m-1e-10).length]);
      const a=axes(svg,[floor,8.6],[0,Math.max(1,Math.ceil(Math.log10(rows.length)))],t('Magnitud reportada','Reported magnitude'),'log₁₀ N(M ≥ m)');
      svg.append(element('polyline',{points:bins.filter(b=>b[1]>0).map(b=>a.x(b[0])+','+a.y(Math.log10(b[1]))).join(' '),fill:'none',stroke:'#155b78','stroke-width':2}));
    }
    c.append(svg);
  }
  function render() {
    ['maps','timelines','diagnostics'].forEach(id=>$(id).replaceChildren());const {out,anchor,referenceAnchor}=selected();
    $('anchorKey').hidden=!referenceAnchor;
    for(const source of Object.keys(active)){mapPlot(source,out[source],anchor,referenceAnchor);timeline(source,out[source],anchor);diagnosticPlot(source);}
    if(results.ssn&&results.usgs) {
      const maps=Object.fromEntries(Object.entries(results).map(([s,r])=>[s,new Map(r.ids.map((id,i)=>[id,r.roles[i]]))]));
      const pairs=currentPairs.filter(p=>maps.ssn.has(p.ssn)&&maps.usgs.has(p.usgs));let same=0;for(const p of pairs)if(maps.ssn.get(p.ssn)===maps.usgs.get(p.usgs))same++;
      $('agreement').textContent=pairs.length?`${same} / ${pairs.length} (${(100*same/pairs.length).toFixed(2)} %) · `+t('mismo papel operativo en parejas candidatas. Concordancia no significa exactitud.','same operational role in candidate pairs. Agreement is not accuracy.'):t('Sin parejas evaluables para esta selección.','No evaluable pairs in this selection.');
    } else $('agreement').textContent=t('Alaska: comparación entre métodos con una sola fuente; no es una comparación entre catálogos.','Alaska: methods can be compared on one source; this is not a cross-catalogue comparison.');
  }
  function inspect(source,i) {
    const r=active[source][i],v=results[source],p=v.parent?.[i];const data={...r,operational_role:v.roles[i],component:v.component[i],nearest_parent:p>=0?active[source][p].record_id:null,log10_eta:v.log_eta?.[i]??null};
    const dl=document.createElement('dl');for(const [k,value] of Object.entries(data)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=k;dd.textContent=value===null||value===''?t('No suministrado / no definido','Not supplied / undefined'):String(value);dl.append(dt,dd);}$('recordDetails').replaceChildren(dl);
  }
  function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportRows(){const out=[];for(const [source,rows] of Object.entries(active)){const r=results[source];rows.forEach((v,i)=>out.push({...v,source,method:$('method').value,role:r.roles[i],component:r.component[i],parent_record_id:r.parent?.[i]>=0?rows[r.parent[i]].record_id:'',log10_eta:r.log_eta?.[i]??''}));}return out;}
  function computationJson(){return JSON.stringify({schema:'browser-sequence-computation/1',runtime:{user_agent:navigator.userAgent,language:lang,timing:latestTiming},selection:{region:$('region').value,cut:$('cut').value,membership:$('membership').value,method:$('method').value,weight_policy:$('weightPolicy').value,display_case:$('case').value,display_whole_family:$('familyExtent').checked},manifest,results,records:exportRows()},null,2);}
  function configureOptions(){
    const alaska=$('region').value==='alaska';$('membership').disabled=alaska;$('case').disabled=alaska;if(alaska){$('case').value='all';$('membership').value='native';}
    const weighted=!alaska&&$('cut').value==='4.5'&&$('method').value==='nn';$('weightPolicy').disabled=!weighted;if(!weighted)$('weightPolicy').value='fixed';
    $('familyExtent').disabled=alaska||$('case').value==='all';if($('familyExtent').disabled)$('familyExtent').checked=false;
  }
  function invalidate() {
    request++;workers.forEach(w=>w.terminate());workers=[];active={};results={};latestTiming=null;lastCalculationKey=null;
    ['maps','timelines','diagnostics','recordDetails'].forEach(id=>$(id).replaceChildren());
    ['agreement','parameters','fitWarning','caseDescription'].forEach(id=>$(id).textContent='');
    $('anchorKey').hidden=true;
    ['exportCsv','exportJson','exportSvg','showJson'].forEach(id=>$(id).disabled=true);
    $('visibleJson').value='';$('visibleJson').hidden=true;$('calculate').disabled=!manifest;
    status(t('Selección modificada. Pulsa Calcular secuencias.','Selection changed. Press Calculate sequences.'));
  }
  $('controls').addEventListener('submit',calculate);$('method').addEventListener('change',describe);
  ['region','cut','method','membership','weightPolicy'].forEach(id=>$(id).addEventListener('change',()=>{configureOptions();invalidate();rememberView();}));
  $('case').addEventListener('change',()=>{configureOptions();if(latestTiming)render();rememberView();});
  $('familyExtent').addEventListener('change',()=>{if(latestTiming)render();rememberView();});
  $('language').addEventListener('change',()=>{lang=$('language').value;language();activateStudy();});
  host.querySelectorAll('[data-study-view]').forEach(a=>a.addEventListener('click',event=>{event.preventDefault();navigateStudy({view:a.dataset.studyView},true);}));
  $('exportCsv').addEventListener('click',()=>{const rows=exportRows(),keys=Object.keys(rows[0]||{}),q=v=>'"'+String(v??'').replaceAll('"','""')+'"';download('sequence-classifications.csv',[keys.map(q).join(','),...rows.map(r=>keys.map(k=>q(r[k])).join(','))].join('\r\n'),'text/csv;charset=utf-8');});
  $('exportJson').addEventListener('click',()=>download('sequence-computation.json',computationJson(),'application/json'));
  $('showJson').addEventListener('click',()=>{$('visibleJson').value=computationJson();$('visibleJson').hidden=false;});
  $('exportSvg').addEventListener('click',()=>{const svgs=[...host.querySelectorAll('svg.plot')],combined=element('svg',{xmlns:NS,width:1200,height:Math.ceil(svgs.length/2)*420,viewBox:`0 0 1200 ${Math.ceil(svgs.length/2)*420}`});combined.append(element('style',{},'text{font:12px system-ui,sans-serif;fill:#435b6f}.gridline{stroke:#dce5ed;stroke-width:.7}.axis{stroke:#7a8fa2;stroke-width:1}'));svgs.forEach((svg,i)=>{const g=element('g',{transform:`translate(${i%2*600} ${Math.floor(i/2)*420})`});const title=svg.parentElement.querySelector('h2').textContent;g.append(element('text',{x:25,y:24,style:'font:18px sans-serif'},title));const copy=svg.cloneNode(true);copy.setAttribute('x','0');copy.setAttribute('y','35');copy.setAttribute('width','600');copy.setAttribute('height','350');copy.querySelectorAll('.dot').forEach(e=>{e.removeAttribute('tabindex');e.removeAttribute('role');});g.append(copy);combined.append(g);});download('sequence-figures.svg',new XMLSerializer().serializeToString(combined),'image/svg+xml');});
  applyView(initialView);
  language();notifySuppressed=0;status(t('Cargando contrato de datos…','Loading the data contract…'));
  const initialActivation=activateStudy();
  const dataReady=SeismicStudyData.manifest().then(async m=>{if(destroyed)return;manifest=m;diagnostics=await checked('diagnostics.json');if(destroyed)return;try{basemap=await SeismicStudyData.basemap();}catch(_){}if(!destroyed&&viewState.view==='explorer')await calculate();}).catch(e=>{if(!destroyed)status(t('No se pudo cargar: ','Loading failed: ')+e.message);throw e;});
  const ready=Promise.all([initialActivation,dataReady]);
  return Object.freeze({ready,getState:()=>({...viewState}),async setState(next){panelFocusPending=Boolean(next.panel&&next.panel!=='all');notifySuppressed++;try{return await navigateStudy(next,false,true);}finally{notifySuppressed--;}} ,async setLanguage(next){if(next===lang)return;notifySuppressed++;try{lang=next==='en'?'en':'es';viewState.lang=lang;language();await activateStudy();}finally{notifySuppressed--;}} ,setVisible(value){visible=Boolean(value);if(visible)requestAnimationFrame(()=>{if(!visible||destroyed)return;if(viewState.view==='cases')global.NativeCases?.resize?.();focusPanel();});},destroy(){destroyed=true;request++;workers.forEach(w=>w.terminate());workers=[];for(const api of [global.NativeCases,global.NativeDiagnostics,global.NativePerformance])api?.destroy?.();host.replaceChildren();}});
  }
  global.SeismicSequenceExplorer=Object.freeze({mount});
})(window);
