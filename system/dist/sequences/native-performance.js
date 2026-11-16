/* Native, inspectable charts calculated from retained measured runs. */
(function(global){
  'use strict';
  const NS='http://www.w3.org/2000/svg';
  const color={cached_reference:'#34465a',kd:'#0a8190',octree:'#c76627',build:'#8061aa',search:'#268d92',numeric:'#a9b6c1'};
  const words={
    es:{kicker:'FIGURA 2 · EVALUACIÓN COMPUTACIONAL',title:'Explora el costo de la búsqueda',intro:'Cada punto procede de una medición conservada. Selecciona un tamaño o una gráfica para inspeccionar sus tiempos, repeticiones y trabajo de búsqueda.',
      retained:'Mediciones del estudio, no un ensayo de este navegador.',loading:'Cargando las mediciones verificadas…',failed:'No se pudieron cargar las mediciones: ',size:'Tamaño del prefijo cronológico',all:'Todos los tamaños',metric:'Gráfica destacada',scale:'Escala vertical de las curvas',log:'Logarítmica',linear:'Lineal',
      time:'Tiempo medido',pairs:'Pares evaluados',nodes:'Nodos por consulta',phases:'Fases del índice',timeTitle:'A · Tiempo de cálculo observado',pairsTitle:'B · Pares cuya distancia se evaluó',nodesTitle:'C · Trabajo de búsqueda y poda',phasesTitle:'D · Construcción y búsqueda',
      timeY:'Tiempo (s)',pairsY:'Pares evaluados (% de elegibles)',nodesY:'Nodos por registro objetivo',nX:'Registros del prefijo cronológico',phaseY:'Mediana del componente (s)',
      cached_reference:'Exhaustiva optimizada · 4 hilos',kd:'KD activo · 1 hilo',octree:'Octree activo · 1 hilo',visited:'visitados',pruned:'podados',build:'Construcción',search:'Búsqueda exacta',numeric:'Preparación / exportación numérica',
      ranges:'Las barras indican mínimo–máximo de tres ejecuciones del índice, no intervalos de confianza. La referencia exhaustiva tiene una observación por tamaño.',
      phaseNote:'Las fases usan escala lineal. La suma de medianas de componentes puede diferir de la mediana del tiempo total.',
      inspect:'Dato inspeccionado',inspectHint:'Pasa sobre un punto o selecciónalo con clic o teclado. También puedes usar la tabla.',n:'Registros',backend:'Método',seconds:'Tiempo (s)',range:'Mínimo–máximo (s)',repetitions:'Ejecuciones',ratio:'Exhaustiva / índice',candidate:'Distancias evaluadas',eligible:'Pares estrictamente anteriores',percent:'Porcentaje evaluado',visitCount:'Nodos visitados',pruneCount:'Nodos podados',
      summary:'Resumen calculado en el navegador',runs:'Ejecuciones originales',inspectButton:'Inspeccionar',download:'Descargar selección · JSON',downloadSvg:'Descargar gráfica destacada · SVG',protocol:'Alcance de las mediciones',
      scope:'Un equipo AMD Ryzen 5 5600G / Windows 11; prefijos del SSN retenido 2016–2025, M reportada ≥3.5. Referencia exhaustiva optimizada de cuatro hilos frente a índices de un hilo. Incluye preparación, construcción, búsqueda y exportación numérica; excluye importaciones, calentamiento JIT y compresión. No es una comparación de peligrosidad ni una velocidad universal.',
      verification:'Los resultados numéricos completos de Python coincidieron entre los tres métodos. La poda es empírica para esta entrada: el peor caso sigue siendo cuadrático.',
      observation:'1 observación',median:'Mediana de 3',selected:'Tamaño inspeccionado',small:'En el prefijo más pequeño la búsqueda exhaustiva fue más rápida que KD. Ese resultado adverso permanece visible.',
      rawNote:'Los tiempos y contadores son observaciones retenidas; las medianas, rangos, porcentajes y cocientes se calculan a partir de ellas en esta vista.',phaseSelected:'Fases para N = ',repeat:'ID de repetición',total:'Total',preparation:'Preparación',construction:'Construcción',kernel:'Búsqueda',postprocess:'Exportación numérica',noCounter:'No registrado para la referencia exhaustiva.'},
    en:{kicker:'FIGURE 2 · COMPUTATIONAL EVALUATION',title:'Explore the search cost',intro:'Every point comes from a retained measurement. Select a size or chart to inspect its timings, repetitions and search work.',
      retained:'Study measurements, not a timing experiment performed by this browser.',loading:'Loading the verified measurements…',failed:'Measurements could not be loaded: ',size:'Chronological prefix size',all:'All sizes',metric:'Highlighted chart',scale:'Vertical scale of the curves',log:'Logarithmic',linear:'Linear',
      time:'Measured time',pairs:'Evaluated pairs',nodes:'Nodes per query',phases:'Index phases',timeTitle:'A · Observed computation time',pairsTitle:'B · Pairs whose distance was evaluated',nodesTitle:'C · Search and pruning work',phasesTitle:'D · Construction and search',
      timeY:'Elapsed time (s)',pairsY:'Evaluated pairs (% of eligible)',nodesY:'Nodes per target record',nX:'Records in chronological prefix',phaseY:'Median component time (s)',
      cached_reference:'Optimized exhaustive · 4 threads',kd:'Active KD · 1 thread',octree:'Active octree · 1 thread',visited:'visited',pruned:'pruned',build:'Construction',search:'Exact search',numeric:'Numeric preparation / export',
      ranges:'Bars show the minimum–maximum of three index runs, not confidence intervals. The exhaustive reference has one observation at each size.',
      phaseNote:'Phases use a linear scale. Sums of component medians may differ from the median total time.',
      inspect:'Inspected measurement',inspectHint:'Hover over a point or select it with a click or keyboard. The table is also available.',n:'Records',backend:'Method',seconds:'Time (s)',range:'Minimum–maximum (s)',repetitions:'Runs',ratio:'Exhaustive / index',candidate:'Distances evaluated',eligible:'Strictly earlier eligible pairs',percent:'Evaluated percentage',visitCount:'Visited nodes',pruneCount:'Pruned nodes',
      summary:'Summary calculated in the browser',runs:'Original measured runs',inspectButton:'Inspect',download:'Download selection · JSON',downloadSvg:'Download highlighted chart · SVG',protocol:'Measurement scope',
      scope:'One AMD Ryzen 5 5600G / Windows 11 computer; prefixes of retained SSN data for 2016–2025, reported M≥3.5. Four-thread optimized exhaustive scan against single-thread indices. Includes numeric preparation, construction, search and numeric export; excludes imports, JIT warm-up and compression. It is neither a hazard comparison nor a universal speed claim.',
      verification:'Complete Python numerical outputs agreed among the three methods. Pruning is empirical for this input: worst-case work remains quadratic.',
      observation:'1 observation',median:'Median of 3',selected:'Inspected size',small:'At the smallest prefix the exhaustive scan was faster than KD. That adverse result remains visible.',
      rawNote:'Timings and counters are retained observations; medians, ranges, percentages and ratios are calculated from them in this view.',phaseSelected:'Phases for N = ',repeat:'Repetition ID',total:'Total',preparation:'Preparation',construction:'Construction',kernel:'Search',postprocess:'Numeric export',noCounter:'Not recorded for the exhaustive reference.'}
  };
  let root=null,client=null,state={},onStateChange=null,data=null,summary=[],inspection=null,token=0;
  const lang=()=>state.lang==='en'?'en':'es',w=()=>words[lang()];
  const node=(tag,className='',text='')=>{const e=document.createElement(tag);if(className)e.className=className;if(text)e.textContent=text;return e;};
  const svgNode=(tag,attrs={},text='')=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(tag==='text'){e.setAttribute('font-family','system-ui,sans-serif');e.setAttribute('font-size','12');e.setAttribute('fill','#405c70');}if(text)e.textContent=text;return e;};
  const format=(value,digits=3)=>Number.isFinite(value)?value.toLocaleString(lang(),{maximumFractionDigits:digits}):'—';
  const exact=value=>Number.isFinite(value)?String(value):'—';
  const smallN=n=>n>=1000?format(n/1000,n%1000?1:0)+'k':String(n);
  function normalize(next){
    const size=String(next.benchmark_n||'all');
    return {...next,lang:next.lang==='en'?'en':'es',benchmark_n:data?.sizes.includes(Number(size))?size:'all',benchmark_metric:['time','pairs','nodes','phases'].includes(next.benchmark_metric)?next.benchmark_metric:'time',scale:next.scale==='linear'?'linear':'log'};
  }
  function change(patch){if(onStateChange)onStateChange(patch);else{state=normalize({...state,...patch});render();}}
  function select(row,metric,phase){inspection={row,metric,phase};change({benchmark_n:String(row.n),benchmark_metric:metric});showInspection();}
  function hover(row,metric,phase){inspection={row,metric,phase};showInspection();}
  function bind(element,row,metric,description,phase){
    element.setAttribute('tabindex','0');element.setAttribute('role','button');element.setAttribute('aria-label',description);
    element.append(svgNode('title',{},description));
    element.addEventListener('pointerenter',()=>hover(row,metric,phase));element.addEventListener('focus',()=>hover(row,metric,phase));
    element.addEventListener('click',()=>select(row,metric,phase));
    element.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(row,metric,phase);}});
  }
  function option(value,label){const e=node('option','',label);e.value=value;return e;}
  function control(key,label,options,value){
    const wrapper=node('label','np-control'),select=node('select');wrapper.append(node('span','',label));select.setAttribute('data-np-control',key);
    for(const [v,text] of options)select.append(option(v,text));select.value=value;select.addEventListener('change',()=>change({[key]:select.value}));wrapper.append(select);return wrapper;
  }
  function legend(items){const e=node('div','np-legend');for(const item of items){const label=node('span','np-legend-item'),swatch=node('i');swatch.style.backgroundColor=item.color;if(item.dashed)swatch.className='np-dashed';label.append(swatch,document.createTextNode(item.label));e.append(label);}return e;}
  function chart(metric,title,note){
    const panel=node('article','np-chart'+(state.benchmark_metric===metric?' np-active':''));panel.dataset.metric=metric;
    const heading=node('button','np-chart-heading',title);heading.type='button';heading.setAttribute('aria-pressed',String(state.benchmark_metric===metric));heading.addEventListener('click',()=>change({benchmark_metric:metric}));panel.append(heading);
    const wrap=node('div','np-plot-wrap'),svg=svgNode('svg',{xmlns:NS,viewBox:'0 0 600 350',class:'np-svg',role:'img','aria-label':title});svg.append(svgNode('title',{},title));wrap.append(svg);panel.append(wrap);if(note)panel.append(node('p','np-chart-note',note));return {panel,svg};
  }
  function lineAxes(svg,values,xLabel,yLabel){
    const box={left:72,right:575,top:20,bottom:287},useLog=state.scale==='log';
    let low=Math.min(...values.filter(v=>v>0)),high=Math.max(...values);
    if(useLog){low=Math.pow(10,Math.floor(Math.log10(low)));high=Math.pow(10,Math.ceil(Math.log10(high)));if(low===high)high*=10;}
    else {low=0;high*=1.08;if(!high)high=1;}
    const transform=v=>useLog?Math.log10(v):v,range=[transform(low),transform(high)];
    const x=n=>box.left+(Math.log10(n)-Math.log10(data.sizes[0]))/(Math.log10(data.sizes.at(-1))-Math.log10(data.sizes[0]))*(box.right-box.left);
    const y=v=>box.bottom-(transform(v)-range[0])/(range[1]-range[0])*(box.bottom-box.top);
    for(let i=0;i<=4;i++){
      const raw=range[0]+i*(range[1]-range[0])/4,value=useLog?Math.pow(10,raw):raw,py=y(value);
      svg.append(svgNode('line',{x1:box.left,x2:box.right,y1:py,y2:py,stroke:'#dce6ed','stroke-width':.7}),svgNode('text',{x:box.left-10,y:py+4,'text-anchor':'end'},value>=100?format(value,0):value>=.1?format(value,2):value.toExponential(1)));
    }
    for(const n of data.sizes){const px=x(n);svg.append(svgNode('line',{x1:px,x2:px,y1:box.top,y2:box.bottom,stroke:'#edf2f5','stroke-width':.7}),svgNode('text',{x:px,y:box.bottom+22,'text-anchor':'middle'},smallN(n)));}
    svg.append(svgNode('text',{x:(box.left+box.right)/2,y:338,'text-anchor':'middle'},xLabel),svgNode('text',{transform:'translate(18 155) rotate(-90)','text-anchor':'middle'},yLabel));
    if(state.benchmark_n!=='all')svg.append(svgNode('line',{x1:x(Number(state.benchmark_n)),x2:x(Number(state.benchmark_n)),y1:box.top,y2:box.bottom,stroke:'#5a7284','stroke-width':1,'stroke-dasharray':'3 4'}));
    return {...box,x,y};
  }
  function lineChart(metric,title,yLabel,series,note){
    const result=chart(metric,title,note),values=series.flatMap(s=>s.rows.flatMap(row=>s.range?[row.min_total_seconds,row.max_total_seconds]:[s.value(row)]));
    const axes=lineAxes(result.svg,values,w().nX,yLabel);
    for(const s of series){
      result.svg.append(svgNode('polyline',{points:s.rows.map(row=>axes.x(row.n)+','+axes.y(s.value(row))).join(' '),fill:'none',stroke:s.color,'stroke-width':1.8,...(s.dashed?{'stroke-dasharray':'6 4'}:{})}));
      for(const row of s.rows){
        const x=axes.x(row.n),value=s.value(row),y=axes.y(value);
        if(s.range&&row.repetitions>1)result.svg.append(svgNode('line',{x1:x,x2:x,y1:axes.y(row.min_total_seconds),y2:axes.y(row.max_total_seconds),stroke:s.color,'stroke-width':1.4}));
        const point=svgNode('circle',{cx:x,cy:y,r:state.benchmark_n===String(row.n)?5.5:4,fill:s.color,stroke:'#fff','stroke-width':1,class:'np-point'});
        bind(point,row,metric,`${s.label}; N=${row.n}; ${title}: ${exact(value)}`);result.svg.append(point);
      }
    }
    result.panel.append(legend(series.map(s=>({label:s.label,color:s.color,dashed:s.dashed}))));return result.panel;
  }
  function phaseChart(){
    const n=state.benchmark_n==='all'?data.sizes.at(-1):Number(state.benchmark_n),rows=summary.filter(r=>r.n===n&&r.backend!=='cached_reference');
    const result=chart('phases',w().phasesTitle,w().phaseNote),svg=result.svg;
    const max=Math.max(...rows.map(row=>PerformanceMath.phases(row).reduce((s,p)=>s+p.seconds,0)))*1.2,bottom=287,top=30,y=v=>bottom-v/max*(bottom-top);
    for(let i=0;i<=4;i++){const v=max*i/4;svg.append(svgNode('line',{x1:72,x2:575,y1:y(v),y2:y(v),stroke:'#dce6ed','stroke-width':.7}),svgNode('text',{x:62,y:y(v)+4,'text-anchor':'end'},format(v,2)));}
    rows.forEach((row,i)=>{
      const x=155+i*245;let accumulated=0;
      for(const phase of PerformanceMath.phases(row)){
        const rect=svgNode('rect',{x,y:y(accumulated+phase.seconds),width:100,height:Math.max(.6,y(accumulated)-y(accumulated+phase.seconds)),fill:color[phase.id],class:'np-point'});
        bind(rect,row,'phases',`${w()[row.backend]}; N=${n}; ${w()[phase.id]}: ${exact(phase.seconds)} s`,phase.id);svg.append(rect);accumulated+=phase.seconds;
      }
      svg.append(svgNode('text',{x:x+50,y:bottom+24,'text-anchor':'middle'},row.backend.toUpperCase()),svgNode('text',{x:x+50,y:y(accumulated)-9,'text-anchor':'middle'},format(accumulated,3)+' s'));
    });
    svg.append(svgNode('text',{x:323,y:337,'text-anchor':'middle'},w().phaseSelected+format(n,0)),svgNode('text',{transform:'translate(18 155) rotate(-90)','text-anchor':'middle'},w().phaseY));
    result.panel.append(legend(['build','search','numeric'].map(id=>({label:w()[id],color:color[id]}))));return result.panel;
  }
  function showInspection(){
    const element=root?.querySelector('.np-inspection-data');if(!element)return;
    if(!inspection){element.replaceChildren(node('p','np-muted',w().inspectHint));return;}
    const row=inspection.row,dl=node('dl','np-data');
    const fields=[[w().n,format(row.n,0)],[w().backend,w()[row.backend]],[w().seconds,exact(row.median_total_seconds)],[w().range,exact(row.min_total_seconds)+' – '+exact(row.max_total_seconds)],[w().repetitions,String(row.repetitions)],[w().ratio,format(row.speedup_vs_native,5)+'×'],[w().eligible,format(row.eligible_earlier_pairs,0)],[w().candidate,row.candidate_pairs===null?w().noCounter:format(row.candidate_pairs,0)],[w().percent,format(row.evaluated_percent,8)],[w().visitCount,format(row.visited_nodes,0)],[w().pruneCount,row.pruned_on_pop===null?'—':format(row.pruned_on_pop+row.pruned_before_push,0)]];
    if(inspection.phase)fields.unshift([w()[inspection.phase],exact(PerformanceMath.phases(row).find(p=>p.id===inspection.phase).seconds)+' s']);
    for(const [name,value] of fields)dl.append(node('dt','',name),node('dd','',value));element.replaceChildren(dl);
  }
  function table(rows,raw=false){
    const wrap=node('div','np-table-wrap'),table=node('table','np-table'),head=node('thead'),tr=node('tr');
    const headers=raw?[w().n,w().backend,w().repeat,w().total+' (s)',w().preparation+' (s)',w().construction+' (s)',w().kernel+' (s)',w().postprocess+' (s)']:[w().n,w().backend,w().seconds,w().range,w().repetitions,w().ratio,w().candidate];
    headers.forEach(h=>{const cell=node('th','',h);cell.setAttribute('scope','col');tr.append(cell);});if(!raw)tr.append(node('th','',w().inspectButton));head.append(tr);table.append(head);const body=node('tbody');
    for(const row of rows){
      const item=node('tr');
      const values=raw?[format(row.n,0),w()[row.backend],String(row.rep),exact(row.total_seconds),exact(row.preparation_seconds),exact(row.tree_seconds),exact(row.kernel_seconds),exact(row.postprocess_seconds)]:[format(row.n,0),w()[row.backend],format(row.median_total_seconds,6),format(row.min_total_seconds,6)+' – '+format(row.max_total_seconds,6),String(row.repetitions),format(row.speedup_vs_native,4)+'×',format(row.candidate_pairs,0)];
      values.forEach(v=>item.append(node('td','',v)));
      if(!raw){const cell=node('td'),button=node('button','np-inspect-button',w().inspectButton);button.type='button';button.setAttribute('aria-label',`${w().inspectButton}: ${w()[row.backend]}, N=${row.n}`);button.addEventListener('click',()=>select(row,state.benchmark_metric));cell.append(button);item.append(cell);}body.append(item);
    }
    table.append(body);wrap.append(table);return wrap;
  }
  function download(name,body,type){const url=URL.createObjectURL(new Blob([body],{type})),a=node('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportJSON(){const n=state.benchmark_n;download('seismic-search-measurements.json',JSON.stringify({schema:'explored-retained-search-measurements/1',view:{benchmark_n:n,benchmark_metric:state.benchmark_metric,scale:state.scale},scope:data.scope,source_files:data.source_files,summary:summary.filter(r=>n==='all'||String(r.n)===n),measurements:data.measurements.filter(r=>n==='all'||String(r.n)===n)},null,2),'application/json');}
  function exportSVG(){const current=root.querySelector(`.np-chart[data-metric="${state.benchmark_metric}"] svg`);if(!current)return;const svg=current.cloneNode(true);svg.querySelectorAll('[tabindex]').forEach(e=>{e.removeAttribute('tabindex');e.removeAttribute('role');});download('seismic-search-'+state.benchmark_metric+'.svg',new XMLSerializer().serializeToString(svg),'image/svg+xml');}
  function render(){
    if(!root||!data)return;state=normalize(state);const focused=document.activeElement?.getAttribute('data-np-control');
    root.classList.add('np-study');root.setAttribute('lang',lang());
    const header=node('div','np-heading');header.append(node('p','np-kicker',w().kicker),node('h2','',w().title),node('p','np-intro',w().intro),node('p','np-retained',w().retained));
    const controls=node('div','np-controls');controls.append(control('benchmark_n',w().size,[['all',w().all],...data.sizes.map(n=>[String(n),format(n,0)])],state.benchmark_n),control('benchmark_metric',w().metric,['time','pairs','nodes','phases'].map(k=>[k,w()[k]]),state.benchmark_metric),control('scale',w().scale,[['log',w().log],['linear',w().linear]],state.scale));
    const n=state.benchmark_n==='all'?data.sizes.at(-1):Number(state.benchmark_n),kpis=node('div','np-kpis');
    for(const row of summary.filter(r=>r.n===n)){const card=node('div','np-kpi');card.append(node('span','',w()[row.backend]),node('strong','',format(row.median_total_seconds,3)+' s'),node('small','',row.repetitions===1?w().observation:w().median));kpis.append(card);}
    const selected=node('p','np-selected',w().selected+': N = '+format(n,0));
    const grid=node('div','np-chart-grid'),group=backend=>summary.filter(r=>r.backend===backend);
    grid.append(lineChart('time',w().timeTitle,w().timeY,PerformanceMath.BACKENDS.map(backend=>({rows:group(backend),label:w()[backend],color:color[backend],value:r=>r.median_total_seconds,range:true})),w().ranges),
      lineChart('pairs',w().pairsTitle,w().pairsY,['kd','octree'].map(backend=>({rows:group(backend),label:w()[backend],color:color[backend],value:r=>r.evaluated_percent})),''),
      lineChart('nodes',w().nodesTitle,w().nodesY,['kd','octree'].flatMap(backend=>[{rows:group(backend),label:backend.toUpperCase()+' · '+w().visited,color:color[backend],value:r=>r.visited_per_query},{rows:group(backend),label:backend.toUpperCase()+' · '+w().pruned,color:color[backend],value:r=>r.pruned_per_query,dashed:true}])),phaseChart());
    const inspector=node('section','np-inspection');inspector.append(node('h3','',w().inspect),node('div','np-inspection-data'));
    const summarySection=node('section','np-summary');summarySection.append(node('h3','',w().summary),node('p','np-muted',w().rawNote),table(summary.filter(r=>state.benchmark_n==='all'||String(r.n)===state.benchmark_n)));
    const runs=node('details','np-runs');runs.append(node('summary','',w().runs),table(data.measurements.filter(r=>state.benchmark_n==='all'||String(r.n)===state.benchmark_n),true));
    const actions=node('div','np-actions'),json=node('button','',w().download),svg=node('button','',w().downloadSvg);json.type=svg.type='button';json.addEventListener('click',exportJSON);svg.addEventListener('click',exportSVG);actions.append(json,svg);
    const protocol=node('details','np-protocol');protocol.append(node('summary','',w().protocol),node('p','',w().scope),node('p','',w().verification),node('p','',w().small));
    root.replaceChildren(header,controls,selected,kpis,grid,inspector,summarySection,runs,actions,protocol);showInspection();
    if(focused)root.querySelector(`[data-np-control="${focused}"]`)?.focus({preventScroll:true});
  }
  const api={
    async mount(element,options={}){
      if(!element||typeof element.replaceChildren!=='function'||!options.client?.performance)throw new TypeError('A container and performance data client are required');
      root=element;client=options.client;onStateChange=options.onStateChange||null;state={...options.state};const own=++token;root.classList.add('np-study');root.replaceChildren(node('p','np-loading',w().loading));
      try{const loaded=await client.performance();if(own!==token)return api;const computed=PerformanceMath.summarize(loaded);data=loaded;summary=computed;state=normalize(state);render();}
      catch(error){if(own===token)root.replaceChildren(node('p','np-error',w().failed+error.message));throw error;}
      return api;
    },
    setState(next){
      const previousN=state.benchmark_n;state=normalize({...state,...next});
      if(inspection&&previousN!==state.benchmark_n&&state.benchmark_n!=='all'&&Number(inspection.row.n)!==Number(state.benchmark_n))inspection=null;
      if(data)render();
    },
    setLanguage(language){state={...state,lang:language==='en'?'en':'es'};if(data)render();},
    destroy(){token++;if(root)root.replaceChildren();root=null;data=null;summary=[];inspection=null;}
  };
  global.NativePerformance=Object.freeze(api);
})(window);
