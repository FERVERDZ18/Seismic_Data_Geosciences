/* Shareable presentation settings; scientific inputs and calculations stay fixed. */
(function (root, factory) {
  const api=factory(); if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SeismicSequenceView=api;
})(typeof window!=='undefined'?window:this,function(){
  'use strict';
  const allowed={lang:['es','en'],region:['mexico','alaska'],cut:['4.5','4.1','3.5'],method:['nn','gk'],weight:['fixed','reported_b'],membership:['native','common'],case:['all','2017','2022'],extent:['local','family']};
  const defaults={lang:'es',region:'mexico',cut:'4.5',method:'nn',weight:'fixed',membership:'native',case:'all',extent:'local'};
  function normalize(input){
    const state={};for(const key of Object.keys(defaults))state[key]=allowed[key].includes(input[key])?input[key]:defaults[key];
    if(state.region==='alaska'){state.membership='native';state.case='all';}
    if(state.region!=='mexico'||state.cut!=='4.5'||state.method!=='nn')state.weight='fixed';
    if(state.case==='all')state.extent='local';
    return state;
  }
  function parse(search){return normalize(Object.fromEntries(new URLSearchParams(search)));}
  function query(input){return '?'+new URLSearchParams(normalize(input)).toString();}
  function articleCase(year,language){return normalize({...defaults,lang:language,case:year,extent:'family'});}
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
  return Object.freeze({parse,query,normalize,articleCase,referenceCircle});
});
