/* Shareable presentation settings; scientific inputs and calculations stay fixed. */
(function (root, factory) {
  const api=factory(); if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SeismicSequenceView=api;
})(typeof window!=='undefined'?window:this,function(){
  'use strict';
  const allowed={lang:['es','en'],region:['mexico','alaska'],cut:['4.5','4.1','3.5'],method:['nn','gk'],weight:['fixed','reported_b'],membership:['native','common'],case:['all','2017','2022'],extent:['local','family'],view:['explorer','cases','diagnostics','benchmark'],comparison:['both','fixed','reported_b'],source:['all','ssn','usgs','alaska'],diagnostic_panel:['all','fmd','tr','difference'],pair_cut:['3.5','4.1','4.5'],benchmark_metric:['time','pairs','nodes','phases'],scale:['log','linear'],panel:['all','full','local','timeline','inspector'],expanded_map:['none','full','local'],point_size:['normal','large']};
  const defaults={lang:'es',region:'mexico',cut:'4.5',method:'nn',weight:'fixed',membership:'native',case:'all',extent:'local',view:'explorer',comparison:'both',source:'all',diagnostic_panel:'all',pair_cut:'3.5',benchmark_metric:'time',scale:'log',panel:'all',expanded_map:'none',point_size:'normal'};
  const numeric={radius:['150',50,300],before:['7',0,30],after:['30',1,90]};
  const viewportKeys=Object.freeze(['full','local'].flatMap(kind=>['lat','lon','zoom'].map(key=>kind+'_'+key)));
  function mapViewport(input,kind){
    if(!['full','local'].includes(kind))return null;
    const values=['lat','lon','zoom'].map(key=>input[kind+'_'+key]);
    if(values.some(value=>!['string','number'].includes(typeof value)||!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(String(value))))return null;
    const [latitude,longitude,zoom]=values.map(Number);
    // Leaflet's Web Mercator map has a finite latitude range; a viewport is
    // accepted only as a complete triple, never a partly trusted location.
    if(![latitude,longitude,zoom].every(Number.isFinite)||Math.abs(latitude)>85.051129||Math.abs(longitude)>180||zoom<2||zoom>13)return null;
    return {latitude,longitude,zoom:Math.round(zoom*10)/10};
  }
  function normalize(input){
    const state={};for(const key of Object.keys(defaults))state[key]=allowed[key].includes(input[key])?input[key]:defaults[key];
    for(const [key,[fallback,min,max]] of Object.entries(numeric)){
      const raw=input[key],n=Number(raw);state[key]=raw!==''&&raw!=null&&Number.isFinite(n)&&n>=min&&n<=max?String(n):fallback;
    }
    state.benchmark_n=[2000,5000,10000,20000,50000,100000,170880].includes(Number(input.benchmark_n))?String(Number(input.benchmark_n)):'all';
    if(state.view==='cases'){state.region='mexico';state.cut='4.5';state.method='nn';if(state.case==='all')state.case='2017';if(state.source==='alaska')state.source='all';}
    if(state.region==='alaska'){state.membership='native';state.case='all';}
    if(state.region!=='mexico'||state.cut!=='4.5'||state.method!=='nn')state.weight='fixed';
    if(state.case==='all')state.extent='local';
    if(state.view!=='cases'){state.panel='all';state.expanded_map='none';state.point_size='normal';}
    else {
      for(const kind of ['full','local']){const viewport=mapViewport(input,kind);if(viewport)for(const [key,value] of [['lat',viewport.latitude],['lon',viewport.longitude],['zoom',viewport.zoom]])state[kind+'_'+key]=String(Number(value.toFixed(6)));}
      if(['ssn','usgs'].includes(input.inspect_source)&&typeof input.inspect_record==='string'&&/^[A-Za-z0-9][A-Za-z0-9._~:-]{0,255}$/.test(input.inspect_record)){state.inspect_source=input.inspect_source;state.inspect_record=input.inspect_record;}
    }
    return state;
  }
  function transition(current,patch){
    const next={...current,...patch};
    // A changed case, calculation membership or display window gets a fresh
    // extent. Source/weight visibility, language and focus keep the comparison.
    if(['case','membership','radius','before','after'].some(key=>patch[key]!==undefined&&String(patch[key])!==String(current[key])))for(const key of [...viewportKeys,'inspect_source','inspect_record'])delete next[key];
    return normalize(next);
  }
  function parse(search){return normalize(Object.fromEntries(new URLSearchParams(search)));}
  function query(input){
    const state=normalize(input),params=new URLSearchParams();params.set('lang',state.lang);
    for(const [key,value] of Object.entries(state))if(key!=='lang'&&value!==(defaults[key]??numeric[key]?.[0]??'all'))params.set(key,value);
    return '?'+params.toString();
  }
  function articleCase(year,language){return normalize({...defaults,view:'cases',lang:language,case:year,extent:'family'});}
  function referenceCircle(anchor,radiusKm=150){
    const lat=Number(anchor.latitude),lon=Number(anchor.longitude);
    if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180||!Number.isFinite(radiusKm)||radiusKm<=0)throw new Error('Invalid reference circle');
    const rad=Math.PI/180,phi=lat*rad,lambda=lon*rad,delta=radiusKm/6371.0088,points=[];
    for(let i=0;i<=120;i++){
      const bearing=i*2*Math.PI/120;
      const p=Math.asin(Math.sin(phi)*Math.cos(delta)+Math.cos(phi)*Math.sin(delta)*Math.cos(bearing));
      const l=lambda+Math.atan2(Math.sin(bearing)*Math.sin(delta)*Math.cos(phi),Math.cos(delta)-Math.sin(phi)*Math.sin(p));
      points.push({latitude:p/rad,longitude:((l/rad+540)%360)-180});
    }
    return points;
  }
  return Object.freeze({parse,query,normalize,transition,mapViewport,viewportKeys,articleCase,referenceCircle});
});
