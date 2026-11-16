/* Shared verified observations and browser calculations for the study views. */
(function (root) {
  'use strict';
  const cache=new Map(),calculations=new Map();let request=0;
  function once(key,work){
    if(!cache.has(key))cache.set(key,Promise.resolve().then(work).catch(error=>{cache.delete(key);throw error;}));
    return cache.get(key);
  }
  async function verified(url,spec){
    const response=await fetch(url);if(!response.ok)throw new Error(url+': HTTP '+response.status);
    const bytes=await response.arrayBuffer();
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==spec.sha256||bytes.byteLength!==spec.bytes)throw new Error('Study input integrity mismatch: '+url);
    return JSON.parse(new TextDecoder().decode(bytes));
  }
  const assets=()=>once('study-assets',async()=>{const r=await fetch('study-assets.json');if(!r.ok)throw new Error('Study asset manifest: HTTP '+r.status);return r.json();});
  const manifest=()=>once('scientific-manifest',async()=>verified('data/manifest.json',(await assets()).scientific_manifest));
  const checked=path=>once('input:'+path,async()=>{const m=await manifest();if(!m.files[path])throw new Error('Unlisted scientific input: '+path);return verified('data/'+path,m.files[path]);});
  function key(cut){if(!['3.5','4.1','4.5'].includes(String(cut)))throw new Error('Unsupported reported-magnitude cut');return String(cut).replace('.','_');}
  const inputs=(cut='4.5')=>checked('inputs_'+key(cut)+'.json');
  const pairs=(cut='4.5')=>checked('candidates_'+key(cut)+'.json');
  const calibration=()=>checked('calibration.json');
  const cases=async()=>(await checked('diagnostics.json')).cases;
  const basemap=()=>once('basemap',async()=>verified('../data/basemap.geojson',(await assets()).basemap));
  const performanceData=()=>once('performance-data',async()=>verified('performance-data.json',(await assets()).performance));
  function worker(rows,parameters,threshold){
    return new Promise((resolve,reject)=>{
      const w=new Worker('worker.js'),token=++request;
      w.onmessage=event=>{w.terminate();const data=event.data;if(data.request!==token)return reject(new Error('Unexpected worker response'));data.error?reject(new Error(data.error)):resolve(data.result);};
      w.onerror=event=>{w.terminate();reject(new Error(event.message||'Study worker failed'));};
      w.postMessage({request:token,rows,method:'nn',parameters,threshold});
    });
  }
  function classify(source,options={}){
    const cut=String(options.cut||'4.5'),weight=options.weight||'fixed',membership=options.membership||'native';key(cut);
    if(!['ssn','usgs','alaska'].includes(source)||!['fixed','reported_b'].includes(weight)||!['native','common'].includes(membership))return Promise.reject(new Error('Invalid study classification selection'));
    if(weight==='reported_b'&&(cut!=='4.5'||source==='alaska'))return Promise.reject(new Error('Reported-b sensitivity is defined for Mexico M>=4.5 only'));
    if(source==='alaska'&&membership==='common')return Promise.reject(new Error('Alaska has no cross-catalogue candidate cohort'));
    const id=[source,cut,weight,membership].join('|');
    if(!calculations.has(id))calculations.set(id,(async()=>{
      const data=await inputs(cut),c=await calibration();let rows=data.sources[source];
      if(membership==='common'){
        const p=await pairs(cut),ids=new Set(p.pairs.map(v=>v[source]));rows=rows.filter(row=>ids.has(row.record_id));
      }
      const frozen=weight==='reported_b'?c.weight_modes?.reported_b?.[source]:c.cuts[cut]?.[source];
      if(!frozen||!Number.isFinite(frozen.threshold_log10))throw new Error('No estimable development cutoff for this selection');
      const result=await worker(rows,{d:1.6,w:frozen.w??1,q:.5,backend:'kd'},frozen.threshold_log10);
      return {rows,result,calibration:frozen};
    })().catch(error=>{calculations.delete(id);throw error;}));
    return calculations.get(id);
  }
  root.SeismicStudyData=Object.freeze({manifest,checked,inputs,pairs,cases,calibration,basemap,performance:performanceData,classify});
})(window);
