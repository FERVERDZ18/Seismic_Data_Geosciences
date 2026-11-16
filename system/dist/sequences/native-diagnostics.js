/* Native, inspectable diagnostics rebuilt from verified observations. */
(function(global){
  'use strict';
  const NS='http://www.w3.org/2000/svg',M=global.SequenceDiagnosticsMath;
  const palette={ssn:'#1b6e93',usgs:'#c34b25',alaska:'#8071a5'};
  const sourceName={ssn:'SSN · México',usgs:'ComCat · México',alaska:'ComCat · Alaska'};
  let instance=null;
  function html(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;}
  function svg(tag,attributes={},text){const e=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attributes))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
  function axes(title,xlim,ylim,xlabel,ylabel,logY=false){
    const plot=svg('svg',{viewBox:'0 0 640 370',class:'nd-plot',role:'img','aria-label':title});plot.append(svg('title',{},title));
    const a={left:66,right:620,top:20,bottom:315};a.x=v=>a.left+(v-xlim[0])/(xlim[1]-xlim[0])*(a.right-a.left);a.y=v=>a.bottom-(v-ylim[0])/(ylim[1]-ylim[0])*(a.bottom-a.top);
    for(let i=0;i<=5;i++){const x=xlim[0]+i*(xlim[1]-xlim[0])/5;plot.append(svg('line',{x1:a.x(x),x2:a.x(x),y1:a.top,y2:a.bottom,class:'nd-grid'}),svg('text',{x:a.x(x),y:a.bottom+22,'text-anchor':'middle'},Number(x.toFixed(1)).toString()));}
    const ys=logY?Array.from({length:Math.floor(ylim[1])-Math.ceil(ylim[0])+1},(_,i)=>Math.ceil(ylim[0])+i):Array.from({length:6},(_,i)=>ylim[0]+i*(ylim[1]-ylim[0])/5);
    for(const y of ys)plot.append(svg('line',{x1:a.left,x2:a.right,y1:a.y(y),y2:a.y(y),class:'nd-grid'}),svg('text',{x:a.left-10,y:a.y(y)+4,'text-anchor':'end'},logY?'10'+superscript(y):Number(y.toFixed(1)).toString()));
    plot.append(svg('text',{x:(a.left+a.right)/2,y:359,'text-anchor':'middle'},xlabel),svg('text',{transform:'translate(17 170) rotate(-90)','text-anchor':'middle'},ylabel));
    return {plot,a};
  }
  function superscript(number){const digits={'-':'⁻',0:'⁰',1:'¹',2:'²',3:'³',4:'⁴',5:'⁵',6:'⁶',7:'⁷',8:'⁸',9:'⁹'};return String(number).split('').map(c=>digits[c]||c).join('');}
  function extent(points,key){let low=Infinity,high=-Infinity;for(const p of points){low=Math.min(low,p[key]);high=Math.max(high,p[key]);}return [Math.floor(low)-.2,Math.ceil(high)+.2];}
  class Diagnostics {
    constructor(element,options){this.root=element;this.client=options.client;this.state={lang:'es',cut:'4.5',source:'all',diagnostic_panel:'all',pair_cut:'3.5',...options.state};this.onStateChange=options.onStateChange||null;this.onRecord=options.onRecord||(()=>{});this.token=0;this.selection=null;this.page=0;this.raw=null;this.paired=null;this.results=new Map();this.fmdCache=new Map();this.chartData={};this.busy=true;}
    t(es,en){return this.state.lang==='en'?en:es;}
    fmt(value,digits=2){return value===null||!Number.isFinite(Number(value))?'—':Number(value).toLocaleString(this.state.lang,{maximumFractionDigits:digits});}
    select(label,key,choices){const wrap=html('label','nd-control'),text=html('span','',label),control=html('select');control.dataset.control=key;for(const [value,title]of choices){const o=html('option','',title);o.value=value;control.append(o);}control.value=this.state[key];control.addEventListener('change',()=>this.change({[key]:control.value}));wrap.append(text,control);return wrap;}
    change(patch){if(this.onStateChange)return this.onStateChange(patch);this.state={...this.state,...patch};return this.draw();}
    async mount(){
      this.shell();this.status.textContent=this.t('Verificando observaciones y preparando diagnósticos…','Verifying observations and preparing diagnostics…');
      try{const [data,matching]=await Promise.all([this.client.inputs('3.5'),this.client.pairs('3.5')]);this.raw=data.sources;this.paired=matching.pairs;await this.draw();}catch(error){this.status.textContent=this.t('No se pudo cargar: ','Loading failed: ')+error.message;throw error;}
      return this;
    }
    shell(){
      this.root.classList.add('nd-view');this.root.replaceChildren();
      const header=html('div','nd-heading');header.append(html('p','nd-kicker',this.t('MAGNITUDES, UMBRALES Y REGISTROS','MAGNITUDES, THRESHOLDS AND RECORDS')),html('h2','',this.t('Diagnósticos del catálogo','Catalogue diagnostics')),html('p','nd-intro',this.t('Gráficas calculadas con las observaciones: pulsa una magnitud, un epicentro en T–R o una caja para consultar los registros.','Plots computed from observations: select a magnitude, a T–R point or a box to inspect the records.')));
      const controls=html('div','nd-controls');controls.append(this.select(this.t('Mostrar','Show'),'diagnostic_panel',[['all',this.t('Todos los paneles','All panels')],['fmd',this.t('Frecuencia–magnitud','Frequency–magnitude')],['tr',this.t('Separación T–R','T–R separation')],['difference',this.t('Diferencias por tipo','Differences by type')]]),this.select(this.t('Fuente','Source'),'source',[['all',this.t('Todas','All')],['ssn','SSN · México'],['usgs','ComCat · México'],['alaska','ComCat · Alaska']]),this.select(this.t('Corte de T–R','T–R cut'),'cut',[['4.5','M ≥ 4.5'],['4.1','M ≥ 4.1'],['3.5','M ≥ 3.5']]),this.select(this.t('Corte de las parejas','Candidate-pair cut'),'pair_cut',[['3.5','M ≥ 3.5'],['4.1','M ≥ 4.1'],['4.5','M ≥ 4.5']]));
      const reset=html('button','nd-secondary',this.t('Restaurar figura 3','Restore figure 3'));reset.type='button';reset.addEventListener('click',()=>this.change({diagnostic_panel:'all',source:'all',cut:'4.5',pair_cut:'3.5'}));
      const download=html('button','nd-secondary',this.t('Datos graficados · JSON','Plotted data · JSON'));download.type='button';download.disabled=true;download.addEventListener('click',()=>this.download());this.exportButton=download;controls.append(reset,download);
      this.status=html('p','nd-status');this.status.setAttribute('role','status');this.grid=html('div','nd-grid-layout');this.inspector=html('section','nd-inspector');
      const note=html('p','nd-note',this.t('La FMD usa todas las observaciones retenidas desde M 3.5; T–R y las parejas tienen sus propios cortes. Las magnitudes conservan sus tipos originales. Ni b ni GFT certifican completitud física o equivalencia con Mw.','FMD uses all observations retained from M 3.5; T–R and candidate pairs have their own cuts. Magnitudes retain their original types. Neither b nor GFT certifies physical completeness or equivalence to Mw.'));
      this.root.append(header,controls,this.status,note,this.grid,this.inspector);this.renderSelection();
    }
    async draw(){
      if(!this.raw)return;const token=++this.token;this.busy=true;this.selection=null;this.page=0;this.chartData={fmd:[],tr:[],differences:null};this.shell();this.status.textContent=this.t('Recalculando paneles…','Recalculating panels…');
      const sources=this.state.source==='all'?['ssn','usgs','alaska']:[this.state.source],panel=this.state.diagnostic_panel;
      try{
        if(panel==='all'||panel==='fmd')for(const source of sources)this.fmd(source);
        if(panel==='all'||panel==='tr'){
          const requested=this.state.source==='all'?['ssn','usgs']:sources;
          const classified=await Promise.all(requested.map(async source=>{const cut=this.state.cut,key=source+':'+cut;if(!this.results.has(key)){const pending=Promise.resolve().then(()=>this.client.classify(source,{cut,weight:'fixed',membership:'native'})).catch(error=>{this.results.delete(key);throw error;});this.results.set(key,pending);}const result=await this.results.get(key);return {source,...result};}));
          if(token!==this.token)return;
          const entries=classified.map(c=>({...c,...M.trPoints(c.rows,c.result)})),all=entries.flatMap(e=>e.points);
          const limits=all.length?{x:extent(all,'x'),y:extent(all,'y')}:{x:[-10,0],y:[-8,4]};
          for(const entry of entries)this.tr(entry,limits);
        }
        if(token!==this.token)return;
        if(panel==='all'||panel==='difference')this.differences();
        this.busy=false;this.exportButton.disabled=false;this.status.textContent=this.t('Calculado en el navegador · datos observados y cortes de desarrollo congelados.','Calculated in the browser · observed data and frozen development cutoffs.');
      }catch(error){if(token===this.token)this.status.textContent=this.t('No se pudo calcular: ','Calculation failed: ')+error.message;}
    }
    card(title,subtitle){const card=html('article','nd-card');card.append(html('h3','',title),html('p','nd-subtitle',subtitle));this.grid.append(card);return card;}
    fmd(source){
      let cached=this.fmdCache.get(source);if(!cached){const rows=this.raw[source],values=rows.map(r=>r.magnitude);cached={bins:M.cumulativeFmd(rows),fits:['4.1','4.5'].map(cut=>({cut,...M.gft(values,cut)}))};this.fmdCache.set(source,cached);}
      const {bins,fits}=cached,n=this.raw[source].length,card=this.card(sourceName[source]+' · FMD',this.fmt(n,0)+' '+this.t('observaciones; acumulado de magnitudes originales','observations; cumulative original magnitudes'));
      const {plot,a}=axes(sourceName[source]+' FMD',[3.45,8.4],[0,Math.ceil(Math.log10(Math.max(1,n)))+.15],this.t('Magnitud reportada','Reported magnitude'),this.t('Número acumulado','Cumulative count'),true);
      const maxObserved=bins.length?bins[bins.length-1].magnitude:8.4;
      for(const fit of fits){if(fit.b_reported_MLE===null)continue;const points=[];for(let x=Number(fit.cut);x<=maxObserved+1e-10;x+=.025){const y=Math.log10(fit.n)-fit.b_reported_MLE*(x-Number(fit.cut));if(y>=0)points.push(a.x(x)+','+a.y(y));}plot.append(svg('polyline',{points:points.join(' '),fill:'none',stroke:fit.cut==='4.1'?'#7d7d7d':'#233d4b','stroke-width':1.5,'stroke-dasharray':fit.cut==='4.1'?'6 4':'none'}));}
      for(const bin of bins){const point=svg('circle',{cx:a.x(bin.magnitude),cy:a.y(Math.log10(bin.cumulative)),r:3.2,fill:palette[source],class:'nd-point',tabindex:0,role:'button','aria-label':sourceName[source]+' M ≥ '+bin.magnitude+': '+bin.cumulative});point.append(svg('title',{},'M ≥ '+bin.magnitude+' · '+bin.cumulative));const select=()=>this.selectMagnitude(source,bin.magnitude);point.addEventListener('click',select);point.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});plot.append(point);}
      card.append(plot);const table=html('table','nd-summary');table.innerHTML='<thead><tr><th>'+this.t('Corte','Cut')+'</th><th>n</th><th>b</th><th>GFT</th></tr></thead>';const body=html('tbody');for(const fit of fits){const tr=html('tr');for(const value of ['≥ '+fit.cut,this.fmt(fit.n,0),this.fmt(fit.b_reported_MLE),this.fmt(fit.fit_percent,1)+' %'])tr.append(html('td','',value));body.append(tr);}table.append(body);card.append(table);
      this.chartData.fmd.push({source,bins,fits});
    }
    tr(entry,limits){
      const {source,rows,result,points,no_parent,nonpositive_with_parent}=entry,cut=result.metadata.threshold_log10;
      const card=this.card(sourceName[source]+' · T–R',this.fmt(points.length,0)+' '+this.t('puntos; fuera del eje logarítmico: ','points; outside logarithmic axes: ')+(no_parent+nonpositive_with_parent));
      const frame=html('div','nd-chart-frame'),{plot,a}=axes(sourceName[source]+' T–R',limits.x,limits.y,'log₁₀ Tₙ '+this.t('(años)','(years)'),'log₁₀ Rₙ (kmᵈ)');
      const lineStart=Math.max(limits.x[0],cut-limits.y[1]),lineEnd=Math.min(limits.x[1],cut-limits.y[0]);
      if(lineStart<=lineEnd)plot.append(svg('line',{x1:a.x(lineStart),x2:a.x(lineEnd),y1:a.y(cut-lineStart),y2:a.y(cut-lineEnd),stroke:'#b74524','stroke-width':1.7,'stroke-dasharray':'6 4'}));
      const pick=p=>this.inspectTr(source,rows,result,p);
      if(points.length<=8000){for(const p of points){const row=rows[p.i],point=svg('circle',{cx:a.x(p.x),cy:a.y(p.y),r:2.3,fill:p.retained?'#247a91':'#aeb4ba',opacity:.65,class:'nd-point',tabindex:0,role:'button','aria-label':row.record_id});point.append(svg('title',{},row.time_utc+' · M '+row.magnitude+' · '+(p.retained?this.t('enlace retenido','retained link'):this.t('enlace cortado','cut link'))));point.addEventListener('click',()=>pick(p));point.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(p);}});plot.append(point);}}
      else this.canvasPoints(frame,points,a,rows,pick);
      frame.append(plot);card.append(frame);
      const legend=html('p','nd-legend');legend.append(html('span','nd-retained',this.t('● Retenido','● Retained')),html('span','nd-cut',this.t('● Cortado','● Cut')),html('span','nd-cutoff',this.t('┄ Umbral congelado c = ','┄ Frozen cutoff c = ')+this.fmt(cut,6)));card.append(legend);
      if((source==='ssn'&&this.state.cut!=='4.5'))card.append(html('p','nd-warning',this.t('Este corte SSN produce un umbral numérico sin dos modos respaldados: sensibilidad exploratoria, no familias estadísticamente certificadas.','This SSN cut returns a numerical boundary without supported separate modes: exploratory sensitivity, not statistically certified families.')));
      card.append(html('p','nd-note',this.t('Cada punto enlaza un registro con su candidato anterior; color según la suma de logaritmos y el corte. No identifica disparo físico.','Each point links a record to its earlier candidate; colour follows the sum of logarithms and the cutoff. It does not identify physical triggering.')));
      this.chartData.tr.push({source,cut:this.state.cut,threshold_log10:cut,no_parent,nonpositive_with_parent,points:points.map(p=>({...p,record_id:rows[p.i].record_id,parent_record_id:rows[result.parent[p.i]]?.record_id}))});
    }
    canvasPoints(frame,points,a,rows,pick){
      const canvas=html('canvas','nd-canvas');canvas.width=1280;canvas.height=740;canvas.setAttribute('aria-label',this.t('Todos los puntos T–R; usa el ratón o las flechas para seleccionar','All T–R points; use the pointer or arrow keys to select'));canvas.tabIndex=0;const ctx=canvas.getContext('2d');ctx.scale(2,2);
      const cells=new Map();for(const p of points){const x=a.x(p.x),y=a.y(p.y);ctx.fillStyle=p.retained?'#247a9188':'#aeb4ba77';ctx.beginPath();ctx.arc(x,y,1.3,0,2*Math.PI);ctx.fill();const key=Math.floor(x/8)+','+Math.floor(y/8);if(!cells.has(key))cells.set(key,[]);cells.get(key).push(p);}
      const tip=html('div','nd-tooltip');tip.hidden=true;let current=null,index=0;
      const show=p=>{current=p;tip.hidden=!p;if(p)tip.textContent=rows[p.i].time_utc+' · M '+rows[p.i].magnitude+' · '+rows[p.i].record_id;};
      canvas.addEventListener('pointermove',event=>{const rect=canvas.getBoundingClientRect(),x=(event.clientX-rect.left)*640/rect.width,y=(event.clientY-rect.top)*370/rect.height,cx=Math.floor(x/8),cy=Math.floor(y/8);let nearest=null,best=64;for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const p of cells.get((cx+dx)+','+(cy+dy))||[]){const d=(a.x(p.x)-x)**2+(a.y(p.y)-y)**2;if(d<best){best=d;nearest=p;}}show(nearest);});
      canvas.addEventListener('pointerleave',()=>show(null));canvas.addEventListener('click',()=>{if(current)pick(current);});canvas.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();index=(index+(e.key==='ArrowLeft'?-1:1)+points.length)%points.length;show(points[index]);}if(e.key==='Enter'&&current)pick(current);});frame.append(canvas,tip);
    }
    differences(){
      if(this.state.source==='alaska'){this.grid.append(html('p','nd-note',this.t('Las parejas SSN–ComCat corresponden a México. Alaska conserva una sola fuente.','SSN–ComCat candidate pairs concern Mexico. Alaska retains one source.')));return;}
      const data=M.pairedGroups(this.paired,this.raw.ssn,this.raw.usgs,this.state.pair_cut||'3.5'),card=this.card(this.t('Diferencias de magnitud por tipo ComCat','Magnitude differences by ComCat type'),this.fmt(data.pairs.length,0)+' '+this.t('parejas candidatas; SSN menos ComCat, sin conversión','candidate pairs; SSN minus ComCat, no conversion'));
      const values=data.pairs.map(p=>Number(p.delta_m));let lo=-1.2,hi=1;for(const v of values){lo=Math.min(lo,v-.05);hi=Math.max(hi,v+.05);}
      const {plot,a}=axes(this.t('Diferencias por tipo','Differences by type'),[-.6,Math.max(.6,data.groups.length-.4)],[lo,hi],'',this.t('SSN − ComCat · magnitud reportada','SSN − ComCat · reported magnitude'));plot.querySelectorAll('text').forEach(e=>{if(e.getAttribute('y')==='337')e.remove();});
      plot.append(svg('line',{x1:a.left,x2:a.right,y1:a.y(0),y2:a.y(0),stroke:'#6c7e88','stroke-width':1}));
      data.groups.forEach((g,i)=>{const x=a.x(i),width=38;plot.append(svg('line',{x1:x,x2:x,y1:a.y(g.lower_whisker),y2:a.y(g.upper_whisker),stroke:'#263c48'}));for(const v of [g.lower_whisker,g.upper_whisker])plot.append(svg('line',{x1:x-12,x2:x+12,y1:a.y(v),y2:a.y(v),stroke:'#263c48'}));
        const box=svg('rect',{x:x-width/2,y:a.y(g.q3),width,height:Math.max(1,a.y(g.q1)-a.y(g.q3)),fill:'#d7e7ec',stroke:'#263c48',class:'nd-point',tabindex:0,role:'button','aria-label':g.name+': '+g.n+' '+this.t('parejas','pairs')});box.append(svg('title',{},g.name+' · n='+g.n+' · '+this.t('mediana','median')+' '+this.fmt(g.median,3)));const select=()=>this.selectPairs(g);box.addEventListener('click',select);box.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});plot.append(box,svg('line',{x1:x-width/2,x2:x+width/2,y1:a.y(g.median),y2:a.y(g.median),stroke:'#bc4425','stroke-width':2}),svg('text',{x,y:337,'text-anchor':'middle'},g.name==='other'?this.t('otros','other'):g.name),svg('text',{x,y:354,'text-anchor':'middle'},'n='+g.n));
        g.outliers.forEach((p,j)=>{const point=svg('circle',{cx:x+((j%5)-2)*2,cy:a.y(Number(p.delta_m)),r:2.4,fill:'#697681',opacity:.6,class:'nd-point',tabindex:0,role:'button','aria-label':p.ssn+' / '+p.usgs});point.append(svg('title',{},p.delta_m+' · '+p.ssn+' / '+p.usgs));const pick=()=>this.inspectPair(p);point.addEventListener('click',pick);point.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();pick();}});plot.append(point);});
      });card.append(plot,html('p','nd-note',this.t('Cajas: mediana e IQR; bigotes a 1.5 IQR; todos los atípicos visibles. Tipos con menos de 50 pares se reúnen en «otros». SSN no suministra el tipo por registro.','Boxes: median and IQR; 1.5-IQR whiskers; every outlier is shown. Types with fewer than 50 pairs are pooled as “other”. SSN does not supply per-record magnitude type.')));
      this.chartData.differences={cut:this.state.pair_cut||'3.5',n:data.pairs.length,groups:data.groups.map(g=>({name:g.name,n:g.n,q1:g.q1,median:g.median,q3:g.q3,lower_whisker:g.lower_whisker,upper_whisker:g.upper_whisker,pairs:g.pairs.map(p=>({ssn:p.ssn,usgs:p.usgs,delta_m:p.delta_m,magnitude_type:p.type}))}))};
    }
    selectMagnitude(source,cut){const rows=this.raw[source],indices=[];for(let i=0;i<rows.length;i++)if(M.compareDecimal(rows[i].magnitude,cut)>=0)indices.push(i);this.selection={kind:'rows',source,rows,indices,label:sourceName[source]+' · M ≥ '+cut};this.page=0;this.renderSelection();this.inspector.scrollIntoView({block:'nearest'});}
    selectPairs(group){this.selection={kind:'pairs',pairs:group.pairs,label:this.t('Parejas candidatas · ','Candidate pairs · ')+group.name};this.page=0;this.renderSelection();this.inspector.scrollIntoView({block:'nearest'});}
    inspectTr(source,rows,result,p){const row=rows[p.i],parent=rows[result.parent[p.i]];const record={source,...row,operational_role:result.roles[p.i],candidate_parent_record_id:parent?.record_id||null,log10_T:p.x,log10_R:p.y,cut_score:p.score,threshold_log10:result.metadata.threshold_log10,retained_link:p.retained};this.showRecord(record);}
    inspectPair(p){this.showRecord({candidate_pair:true,ssn:{record_id:p.ssn,time_utc:p.ssn_row.time_utc,latitude:p.ssn_row.latitude,longitude:p.ssn_row.longitude,magnitude:p.ssn_row.magnitude,magnitude_type:p.ssn_row.magnitude_type},comcat:{record_id:p.usgs,time_utc:p.usgs_row.time_utc,latitude:p.usgs_row.latitude,longitude:p.usgs_row.longitude,magnitude:p.usgs_row.magnitude,magnitude_type:p.usgs_row.magnitude_type},SSN_minus_ComCat_reported_magnitude:p.delta_m,distance_km:p.distance_km,SSN_minus_ComCat_seconds:p.delta_seconds});}
    showRecord(record){this.selection={kind:'record',record,label:this.t('Registro inspeccionado','Inspected record')};this.renderSelection();this.onRecord(record);this.inspector.scrollIntoView({block:'nearest'});}
    renderSelection(){
      if(!this.inspector)return;this.inspector.replaceChildren();if(!this.selection){this.inspector.append(html('p','nd-note',this.t('Selecciona un punto o una caja para consultar datos originales.','Select a point or a box to inspect original data.')));return;}
      const s=this.selection;this.inspector.append(html('h3','',s.label));if(s.kind==='record'){this.inspector.append(html('pre','nd-record',JSON.stringify(s.record,null,2)));return;}
      const total=s.kind==='rows'?s.indices.length:s.pairs.length,size=12,pages=Math.max(1,Math.ceil(total/size));this.page=Math.min(this.page,pages-1);this.inspector.append(html('p','nd-note',this.fmt(total,0)+' '+(s.kind==='rows'?this.t('registros conservados','retained records'):this.t('parejas candidatas','candidate pairs'))+' · '+this.t('tabla paginada, sin eliminar observaciones.','paginated table, no observations removed.')));
      const wrap=html('div','nd-table-wrap'),table=html('table','nd-record-table'),head=html('thead'),tr=html('tr');for(const label of (s.kind==='rows'?[this.t('Fecha UTC','UTC time'),'M',this.t('Registro','Record'),'']:[this.t('Registro SSN','SSN record'),this.t('Registro ComCat','ComCat record'),'ΔM','']))tr.append(html('th','',label));head.append(tr);table.append(head);const body=html('tbody');
      for(let i=this.page*size;i<Math.min(total,(this.page+1)*size);i++){const line=html('tr'),value=s.kind==='rows'?s.rows[s.indices[i]]:s.pairs[i],columns=s.kind==='rows'?[value.time_utc,value.magnitude,value.record_id]:[value.ssn,value.usgs,value.delta_m];for(const value of columns)line.append(html('td','',String(value)));const td=html('td'),button=html('button','nd-inspect-button',this.t('Inspeccionar','Inspect'));button.type='button';button.addEventListener('click',()=>s.kind==='rows'?this.showRecord({source:s.source,...value}):this.inspectPair(value));td.append(button);line.append(td);body.append(line);}table.append(body);wrap.append(table);this.inspector.append(wrap);
      const paging=html('div','nd-pagination');for(const [delta,label]of [[-1,this.t('Anterior','Previous')],[1,this.t('Siguiente','Next')]]){const button=html('button','nd-secondary',label);button.type='button';button.disabled=this.page+delta<0||this.page+delta>=pages;button.addEventListener('click',()=>{this.page+=delta;this.renderSelection();});paging.append(button);}paging.append(html('span','',this.t('Página ','Page ')+(this.page+1)+' / '+pages));this.inspector.append(paging);
    }
    download(){if(this.busy||!this.exportButton||this.exportButton.disabled)return;const data=JSON.stringify({schema:'native-sequence-diagnostics/1',state:this.state,interpretation:'Observed reported magnitudes; no homogenization, physical completeness certification or triggering truth.',plots:this.chartData},null,2),url=URL.createObjectURL(new Blob([data],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='seismic-native-diagnostics.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    async setState(state){this.state={...this.state,...state};return this.draw();}
    async setLanguage(lang){this.state.lang=lang==='en'?'en':'es';return this.draw();}
    destroy(){this.token++;this.busy=true;this.selection=null;this.chartData={};this.root.replaceChildren();}
  }
  global.NativeDiagnostics=Object.freeze({async mount(element,options){if(!element)throw new TypeError('A diagnostics container is required');if(instance)instance.destroy();instance=new Diagnostics(element,options);return instance.mount();},setState:state=>instance?.setState(state),setLanguage:lang=>instance?.setLanguage(lang),destroy:()=>instance?.destroy()});
})(window);
