'use strict';
const $=id=>document.getElementById(id),status=$('status'),collected=[];
let rows,manifest,stopRequested=false,active=false;
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',value)),v=>v.toString(16).padStart(2,'0')).join('');
const sizes=[2000,10000,50000,170880],plan=sizes.flatMap(n=>[0,1,2].flatMap(rep=>(rep%2?['kd','reference']:['reference','kd']).map(backend=>({n,rep,backend}))));
function updateReady(){$('start').disabled=active||!rows||!$('window').checked||collected.length>0;}
$('window').addEventListener('change',updateReady);
async function load(){
 manifest=await(await fetch('BROWSER_MANIFEST.json')).json();
 for(const item of manifest.assets){const response=await fetch(item.file);if(!response.ok)throw Error('HTTP '+response.status+' '+item.file);
   const bytes=await response.arrayBuffer();if(await digest(bytes)!==item.sha256)throw Error('Hash mismatch '+item.file);
   if(item.file==='inputs_ssn_m35.json')rows=JSON.parse(new TextDecoder().decode(bytes)).rows;}
 if(rows.length!==170880)throw Error('Unexpected cohort');
 status.textContent='Verified170880 original observed rows. Ready for24 predefined cells; no results yet.';updateReady();
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
   $('download').disabled=false;
   if(result.status==='FAIL'||stopRequested)break;
 }
 active=false;$('stop').disabled=true;status.textContent=`Finished${collected.length}/${plan.length} cells. Censorship and failures retained. Download JSON for independent array verification; this page alone does not certify Python parity.`;
};
function encode(buffer){const bytes=new Uint8Array(buffer),chunks=[];for(let i=0;i<bytes.length;i+=32768)chunks.push(String.fromCharCode(...bytes.subarray(i,i+32768)));return btoa(chunks.join(''));}
$('download').onclick=()=>{
 const output={schema:'actual-browser-nearest-parent-cost/1',created_utc:new Date().toISOString(),user_agent:navigator.userAgent,
   location:location.href,manifest,plan,cpu_note:$('window').checked?'Coordinator UI acknowledgement; user/OS processes not controlled':'No coordinator UI acknowledgement',
   scope:'Measured Worker kernel is separate from load/verification/setup/transfer/paint; no worker peak-memory claim',
   cells:collected.map(item=>({...item,fields:item.fields?Object.fromEntries(Object.entries(item.fields).map(([key,buffer])=>[key,{encoding:'base64',dtype:key==='parent'?'int32-le':'float64-le',bytes:encode(buffer)}])):undefined}))};
 const blob=new Blob([JSON.stringify(output)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='actual-browser-nearest-parent-cost.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
};
load().catch(error=>{status.textContent='FAIL: '+String(error.stack||error);});
