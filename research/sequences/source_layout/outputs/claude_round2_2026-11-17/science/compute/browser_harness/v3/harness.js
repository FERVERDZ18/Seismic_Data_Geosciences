'use strict';
const $=id=>document.getElementById(id),status=$('status'),collected=[];
let rows,manifest,stopRequested=false,active=false;
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',value)),v=>v.toString(16).padStart(2,'0')).join('');
const sizes=[2000,10000,50000,170880],plan=sizes.flatMap(n=>[0,1,2].flatMap(rep=>(rep%2?['kd','reference']:['reference','kd']).map(backend=>({n,rep,backend}))));
function updateReady(){$('start').disabled=active||!rows||!$('window').checked||collected.length>0;}
$('window').addEventListener('change',updateReady);
let initialLoad;
const visibilityStarted=performance.now(),visibilityObservations=[{elapsed_ms:0,state:document.visibilityState}];
document.addEventListener('visibilitychange',()=>visibilityObservations.push({elapsed_ms:performance.now()-visibilityStarted,state:document.visibilityState}));
async function load(){
 const started=performance.now();
 initialLoad={started_utc:new Date().toISOString(),initial_visibility:document.visibilityState,assets:[],
   scope:'Initial byte fetch/read/SHA256/UTF8 decode/JSON parse/structure validation only; separate from Worker kernels, cell wall and paint',
   paint_measured:false,worker_peak_memory_measured:false,transfer_time_isolated:false,
   os_suspension:'Not measured or excluded; keep tab visible; user/OS processes uncontrolled'};
 let clock=performance.now();const manifestResponse=await fetch('BROWSER_MANIFEST.json');
 const manifestFetch=performance.now()-clock;if(!manifestResponse.ok)throw Error('HTTP '+manifestResponse.status+' manifest');
 clock=performance.now();const manifestBytes=await manifestResponse.arrayBuffer();const manifestRead=performance.now()-clock;
 clock=performance.now();const manifestText=new TextDecoder().decode(manifestBytes);const manifestDecode=performance.now()-clock;
 clock=performance.now();manifest=JSON.parse(manifestText);const manifestParse=performance.now()-clock;
 clock=performance.now();
 if(manifest.planned_cells!==24||manifest.wall_cap_seconds!==120||manifest.repetitions!==3||JSON.stringify(manifest.sizes)!==JSON.stringify(sizes))throw Error('Unexpected predefined plan');
 const manifestValidation=performance.now()-clock;
 initialLoad.manifest={bytes:manifestBytes.byteLength,fetch_resolution_ms:manifestFetch,body_read_ms:manifestRead,
   utf8_decode_ms:manifestDecode,json_parse_ms:manifestParse,validation_ms:manifestValidation};
 for(const item of manifest.assets){
   const observed={file:item.file,bytes:item.bytes};
   clock=performance.now();const response=await fetch(item.file);observed.fetch_resolution_ms=performance.now()-clock;
   if(!response.ok)throw Error('HTTP '+response.status+' '+item.file);
   clock=performance.now();const bytes=await response.arrayBuffer();observed.body_read_ms=performance.now()-clock;
   clock=performance.now();const actualHash=await digest(bytes);observed.sha256_ms=performance.now()-clock;
   clock=performance.now();if(actualHash!==item.sha256||bytes.byteLength!==item.bytes)throw Error('Asset mismatch '+item.file);
   observed.hash_and_size_validation_ms=performance.now()-clock;observed.sha256=actualHash;
   if(item.file==='../inputs_ssn_m35.json'){
     clock=performance.now();const text=new TextDecoder().decode(bytes);observed.utf8_decode_ms=performance.now()-clock;
     clock=performance.now();const parsed=JSON.parse(text);observed.json_parse_ms=performance.now()-clock;
     clock=performance.now();if(!Array.isArray(parsed.rows)||parsed.rows.length!==170880)throw Error('Unexpected cohort');
     rows=parsed.rows;observed.structure_and_count_validation_ms=performance.now()-clock;
   }
   initialLoad.assets.push(observed);
 }
 clock=performance.now();if(!rows||rows.length!==170880)throw Error('Missing cohort');
 initialLoad.final_validation_ms=performance.now()-clock;initialLoad.total_ms=performance.now()-started;
 initialLoad.completed_utc=new Date().toISOString();initialLoad.final_visibility=document.visibilityState;
 status.textContent='Verified170880 original observed rows. Ready for24 predefined cells; initial load observed separately; no results yet.';updateReady();
}
function oneCell(spec){return new Promise(resolve=>{
 const started=performance.now(),worker=new Worker('worker.js'),deadline=setTimeout(()=>finish({status:'CENSORED',wall_limit_ms:120000}),120000);
 let done=false,warmFinished;
 function finish(value){if(done)return;done=true;clearTimeout(deadline);worker.terminate();resolve({...spec,...value,cell_wall_ms:performance.now()-started,completed_utc:new Date().toISOString()});}
 worker.onerror=error=>finish({status:'FAIL',error:String(error.message)});
 worker.onmessage=async event=>{const value=event.data;
   if(value.status==='WARMED'){warmFinished=performance.now();worker.postMessage({command:'run',rows:rows.slice(0,spec.n),backend:spec.backend});return;}
   if(value.status!=='COMPUTED'){finish(value);return;}
   const hashes={};for(const [key,bytes]of Object.entries(value.fields))hashes[key]=await digest(bytes);
   finish({...value,hashes,warmup_worker_setup_ms:warmFinished-started,
      ids_sha256:await digest(new TextEncoder().encode(value.ids.join('\n')+'\n')),
      id_count:value.ids.length,ids:undefined});
 };
 worker.postMessage({command:'warm',rows:rows.slice(0,64)});
});}
$('stop').onclick=()=>{stopRequested=true;status.textContent+='\nStop requested: current bounded cell will complete or be censored.';};
$('start').onclick=async()=>{
 active=true;updateReady();$('stop').disabled=false;
 for(const spec of plan){
   status.textContent=`Running${collected.length+1}/${plan.length}:N${spec.n},rep${spec.rep},${spec.backend}. Deadline120s.`;
   const result=await oneCell(spec);collected.push(result);
   const tr=document.createElement('tr');for(const text of [result.n,result.rep,result.backend,result.status,result.metadata?.total_ms??'—',result.cell_wall_ms]){const td=document.createElement('td');td.textContent=String(text);tr.append(td);}$('results').append(tr);
   if(result.status==='FAIL'||stopRequested)break;
 }
 active=false;$('stop').disabled=true;status.textContent=`Finished${collected.length}/${plan.length} cells. Censorship and failures retained. Independent array verification remains required.`;
 if(collected.length===plan.length){
   try{await prepareSave();await saveObserved();}catch(error){$('saveStatus').textContent='Save preparation failed: '+String(error.stack||error);}
 }else{$('saveStatus').textContent='Incomplete plan retained in page memory. No POST: all24 cells are required.';}
};
function encode(buffer){const bytes=new Uint8Array(buffer),chunks=[];for(let i=0;i<bytes.length;i+=32768)chunks.push(String.fromCharCode(...bytes.subarray(i,i+32768)));return btoa(chunks.join(''));}
let saveBody,saveSha,saveBytes,saving=false;
async function prepareSave(){
 if(active||collected.length!==24)throw Error('POST requires all24 cells to finish');
 const output={schema:'actual-browser-nearest-parent-cost/1',transport:'same-origin-loopback-post-v3',evaluation_label:'V3_TRANSPORT_REPEAT_AFTER_V2_EXPORT_FAILURE',created_utc:new Date().toISOString(),user_agent:navigator.userAgent,
   location:location.href,manifest,plan,initial_load:initialLoad,visibility_observations:visibilityObservations,cpu_note:$('window').checked?'Coordinator UI acknowledgement; user/OS processes not controlled':'No coordinator UI acknowledgement',
   scope:'Measured Worker kernel is separate from load/verification/setup/transfer/paint; no worker peak-memory claim',
   cells:collected.map(item=>({...item,fields:item.fields?Object.fromEntries(Object.entries(item.fields).map(([key,buffer])=>[key,{encoding:'base64',dtype:key==='parent'?'int32-le':'float64-le',bytes:encode(buffer)}])):undefined}))};
 saveBody=JSON.stringify(output);const bytes=new TextEncoder().encode(saveBody);saveBytes=bytes.byteLength;saveSha=await digest(bytes);
 $('saveStatus').textContent=`Prepared after all24 cells: bytes=${saveBytes}; SHA256=${saveSha}. Saving…`;
}
async function saveObserved(){
 if(active||collected.length!==24||!saveBody||saving)return;
 saving=true;$('retrySave').disabled=true;
 try{
   const response=await fetch('/__results/browser-v3',{method:'POST',headers:{'Content-Type':'application/json'},body:saveBody,credentials:'same-origin',cache:'no-store'});
   const responseText=await response.text();let ack;
   try{ack=JSON.parse(responseText);}catch(_){throw Error('HTTP'+response.status+' returned a non-JSON receipt: '+responseText);}
   if(!response.ok)throw Error('HTTP'+response.status+' '+responseText);
   if(ack.saved!==true||ack.sha256!==saveSha||ack.bytes!==saveBytes||ack.fixture_only!==false)throw Error('Receipt bytes/hash differ: '+responseText);
   $('saveStatus').textContent=`Saved: bytes=${saveBytes}; SHA256=${saveSha}; HTTP${response.status}. Server receipt: ${responseText}. Independent numerical parity remains pending.`;
 }catch(error){
   $('saveStatus').textContent=`Save failed: bytes=${saveBytes}; SHA256=${saveSha}. ${String(error.stack||error)}. Retry sends identical JSON bytes without recomputing any cell.`;
   $('retrySave').disabled=false;
 }finally{saving=false;}
}
$('retrySave').onclick=saveObserved;
load().catch(error=>{status.textContent='FAIL: '+String(error.stack||error);});
