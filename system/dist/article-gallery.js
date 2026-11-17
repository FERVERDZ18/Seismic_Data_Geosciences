/* Current manuscript figures open working views inside the observatory shell. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SeismicArticleGallery=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const text={
    es:{title:'Del artículo al sistema',intro:'Cada figura abre su vista de trabajo en este observatorio. Puedes cambiar sus parámetros, consultar registros y conservar el resultado. Las imágenes del artículo documentan una selección; el sistema permite explorarla.',figure:'Figura',open:'Abrir vista',additional:'Vistas históricas adicionales',note:'Los identificadores de los enlaces históricos se conservan aunque cambie la numeración del manuscrito. Las selecciones son registros conservados; no son un flujo en tiempo real ni una predicción.',manual:'Selecciona W1 dentro de la vista para abrir el registro que ilustra el inspector. El enlace restaura los parámetros, no un epicentro inspeccionado ni el zoom.',
      design:'Diseño del sistema',designText:'Selecciona fuentes y abre el mapa desde la arquitectura implementada.',performance:'Coste de la búsqueda',performanceText:'Explora las mediciones conservadas, sus repeticiones, tamaños y fases. No ejecuta de nuevo el benchmark original.',diagnostics:'Magnitudes y separación T–R',diagnosticsText:'Consulta las observaciones, los cortes, las curvas y los registros detrás de cada punto.',families:'Familias comparadas entre catálogos',familiesText:'Abre cada panel de 2017 o 2022: mapas completos, entorno local y cronología.',native:'Inspección de un registro y su vecino',home:'Vista conjunta de los catálogos',homeText:'Mapa e inventario de las cuatro fuentes con procedencia conservada.',sources:'Fuentes y cobertura',sourcesText:'Consulta el atlas, las fechas y el alcance de los paquetes conservados.',maps:'Selecciones por fuente',mapsText:'México, Estados Unidos, Canadá y la selección conjunta del artículo.',regional:'Selecciones regionales',regionalText:'Guerrero, California, Yukon y Alaska con sus filtros documentados.',guerrero:'Guerrero y el filtro terrestre',guerreroText:'Examina el mapa ampliado y el contexto tectónico de esta selección.',compare:'Comparación continental',compareText:'Compara Canadá y México sobre la misma fuente y selección.',top:'Diez registros de mayor magnitud',topText:'Explora el ranking, sus epicentros y los registros de cada fuente.',proximity:'Proximidad histórica',proximityText:'Inspecciona pares de epicentros bajo el radio documentado, sin inferir recurrencia.',atlas:'Atlas de fuentes',time:'Tiempo y cobertura',full:'Mapa completo',local:'Entorno local',timeline:'Cronología',inspector:'Abrir inspector · seleccionar W1',mexico:'México · SSN',usa:'Estados Unidos · USGS',canada:'Canadá · NRCan',combined:'Las cuatro fuentes',descriptive:'Estadísticos de Guerrero',simple:'Vista simple'},
    en:{title:'From the article to the system',intro:'Each figure opens its working view in this observatory. Change its parameters, inspect source records and retain the result. Article images document a selection; the system lets you explore it.',figure:'Figure',open:'Open working view',additional:'Additional historical views',note:'Historical route identifiers remain stable when manuscript figures are renumbered. Selections are retained source records, not a live feed or a prediction.',manual:'Select W1 within the view to open the record illustrated by the inspector. The link restores parameters, not the inspected epicentre or map zoom.',
      design:'Implemented system design',designText:'Choose sources and open the map through the working architecture.',performance:'Search performance',performanceText:'Explore retained measurements, repetitions, input sizes and phases. This does not rerun the original benchmark.',diagnostics:'Magnitudes and T–R separation',diagnosticsText:'Inspect observations, cuts, curves and the source records behind each point.',families:'Compared catalogue families',familiesText:'Open each 2017 or 2022 panel: complete maps, local surroundings and timelines.',native:'Inspect a source record and its parent',home:'Combined catalogue view',homeText:'Explore the map and inventory of all four source packages with their provenance.',sources:'Sources and coverage',sourcesText:'Consult the atlas, dates and scope of the retained packages.',maps:'Selections by source',mapsText:'Mexico, the United States, Canada and the combined article selection.',regional:'Regional selections',regionalText:'Guerrero, California, Yukon and Alaska with their documented filters.',guerrero:'Guerrero and land containment',guerreroText:'Inspect the enlarged map and tectonic context of this selection.',compare:'Continental comparison',compareText:'Compare Canada and Mexico using the same source and selection.',top:'Ten records with the largest reported magnitudes',topText:'Explore the ranking, epicentres and source records.',proximity:'Historical proximity',proximityText:'Inspect epicentre pairs under the documented radius without inferring recurrence.',atlas:'Source atlas',time:'Time and coverage',full:'Complete map',local:'Local surroundings',timeline:'Timeline',inspector:'Open inspector · select W1',mexico:'Mexico · SSN',usa:'United States · USGS',canada:'Canada · NRCan',combined:'All four sources',descriptive:'Guerrero descriptives',simple:'Simple view'}
  };
  const figures=[
    {number:1,title:'design',description:'designText',targets:[{legacy:'1'}]},
    {number:2,title:'performance',description:'performanceText',targets:[{view:'benchmark'}]},
    {number:3,title:'diagnostics',description:'diagnosticsText',targets:[{view:'diagnostics',cut:'4.5',pair_cut:'3.5'}]},
    {number:4,title:'families',description:'familiesText',targets:[
      {view:'cases',case:'2017',panel:'full',letter:'A',label:'full'},
      {view:'cases',case:'2017',panel:'local',letter:'B',label:'local'},
      {view:'cases',case:'2017',panel:'timeline',letter:'C',label:'timeline'},
      {view:'cases',case:'2022',panel:'full',letter:'D',label:'full'},
      {view:'cases',case:'2022',panel:'local',letter:'E',label:'local'},
      {view:'cases',case:'2022',panel:'timeline',letter:'F',label:'timeline'}]},
    {number:5,title:'native',description:'manual',targets:[{view:'cases',case:'2017',panel:'inspector',label:'inspector'}]},
    {number:6,title:'home',description:'homeText',targets:[{legacy:'2'}]},
    {number:7,title:'sources',description:'sourcesText',targets:[{legacy:'3',label:'atlas'},{legacy:'3-time',label:'time'}]},
    {number:8,title:'maps',description:'mapsText',targets:[{legacy:'4a',letter:'A',label:'mexico'},{legacy:'4b',letter:'B',label:'usa'},{legacy:'4c',letter:'C',label:'canada'},{legacy:'4d',letter:'D',label:'combined'}]},
    {number:9,title:'regional',description:'regionalText',targets:[{legacy:'regional-a',letter:'A',name:'Guerrero'},{legacy:'regional-b',letter:'B',name:'California'},{legacy:'regional-c',letter:'C',name:'Yukon'},{legacy:'regional-d',letter:'D',name:'Alaska'}]},
    {number:10,title:'guerrero',description:'guerreroText',targets:[{legacy:'6'}]},
    {number:11,title:'compare',description:'compareText',targets:[{legacy:'7'}]},
    {number:12,title:'top',description:'topText',targets:[{legacy:'9a'}]},
    {number:13,title:'proximity',description:'proximityText',targets:[{legacy:'9b'}]}
  ];
  const additional=[{title:'descriptive',targets:[{legacy:'5'}]},{title:'simple',targets:[{legacy:'8'}]}];
  const language=value=>value==='es'?'es':'en';
  function href(target,lang='en'){
    const p=new URLSearchParams();
    if(target.legacy)p.set('figure',target.legacy);
    else{
      p.set('workspace','sequences');p.set('view',target.view);
      for(const key of ['case','panel','cut','pair_cut'])if(target[key])p.set(key,target[key]);
      if(target.view==='cases'){p.set('comparison','both');p.set('membership','native');}
    }
    p.set('lang',language(lang));return '?'+p.toString();
  }
  function targets(lang='en'){
    const result=[];
    for(const figure of figures)for(const target of figure.targets)result.push({figure:figure.number,...target,href:href(target,lang)});
    return result;
  }
  function mount(container,options={}){
    if(!container)throw new Error('The article gallery needs a container');
    const getLanguage=options.getLanguage||(()=>options.lang||'en');let disposed=false;
    function node(tag,className,value){const e=document.createElement(tag);if(className)e.className=className;if(value)e.textContent=value;return e;}
    function card(def,w,lang,extra=false){
      const e=node('article','article-gallery-card');
      if(!extra)e.append(node('p','article-gallery-code',w.figure+' '+def.number));
      e.append(node('h2','',w[def.title]));if(def.description)e.append(node('p','',w[def.description]));
      const actions=node('div','article-gallery-actions');
      for(const target of def.targets){
        const a=node('a','',[(target.letter?target.letter+' · ':''),target.case?target.case+' · ':'',target.name||w[target.label]||w.open].join(''));a.href=href(target,lang);
        a.addEventListener('click',event=>{
          if(typeof options.onNavigate!=='function'||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
          event.preventDefault();Promise.resolve().then(()=>options.onNavigate(a.getAttribute('href'))).catch(error=>{
            if(disposed)return;const status=container.querySelector('.article-gallery-status');if(status)status.textContent=error?.message||String(error);
          });
        });actions.append(a);
      }
      e.append(actions);return e;
    }
    function render(){
      if(disposed)return;const lang=language(getLanguage()),w=text[lang],grid=node('div','article-gallery-grid');
      for(const def of figures)grid.append(card(def,w,lang));
      const extra=node('section','article-gallery-additional'),extraGrid=node('div','article-gallery-grid');extra.append(node('h2','',w.additional));for(const def of additional)extraGrid.append(card(def,w,lang,true));extra.append(extraGrid);
      const title=node('h1','',w.title),status=node('p','article-gallery-status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
      container.classList.add('article-gallery');container.replaceChildren(title,node('p','article-gallery-intro',w.intro),grid,node('p','article-gallery-note',w.note),extra,status);
    }
    render();return {render,setLanguage:render,destroy(){disposed=true;container.replaceChildren();}};
  }
  return Object.freeze({mount,href,targets,figureCount:figures.length});
});
