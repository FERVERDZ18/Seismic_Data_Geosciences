// Actual owned JS engine, no browser automation and no change of observations.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const base=__dirname,root=path.resolve(base,'../../../..');
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const [source,context,wText,destination]=process.argv.slice(2),w=Number(wText);
if(!['ssn','usgs'].includes(source)||!['native','common'].includes(context)||!Number.isFinite(w))throw Error('Explicit known source/context/weight required');
const output=path.resolve(destination);if(!output.startsWith(base+path.sep)||fs.existsSync(output))throw Error('New private output only');
const seal=JSON.parse(fs.readFileSync(path.join(base,'EXECUTION_SEAL.json'),'utf8'));
for(const item of seal.entries)if(hash(path.join(root,item.path))!==item.sha256)throw Error('Frozen source changed: '+item.path);
fs.mkdirSync(output,{recursive:true});
const enginePath=path.join(root,'system/dist/sequences/nearest-parent.js'),engine=require(enginePath);
let rows=JSON.parse(fs.readFileSync(path.join(root,'system/dist/sequences/data/inputs_3_5.json'),'utf8')).sources[source];
if(context==='common'){
  const pairs=JSON.parse(fs.readFileSync(path.join(base,'inputs/candidate_pairs.json'),'utf8'));
  const ids=new Set(pairs.map(p=>p[source+'_record_id']));rows=rows.filter(r=>ids.has(r.record_id));
}
const result=engine.search(rows,{backend:'kd',d:1.6,w,q:.5});
const files={};
for(const key of ['parent','eta','dt','distance','tn','rn','logEta','logProduct']){
  const array=result[key],p=path.join(output,key+'.bin');fs.writeFileSync(p,Buffer.from(array.buffer,array.byteOffset,array.byteLength));
  files[key]={path:path.relative(root,p).replaceAll('\\','/'),sha256:hash(p),count:array.length,type:key==='parent'?'int32-le':'float64-le'};
}
const idsFile=path.join(output,'ids.json');fs.writeFileSync(idsFile,JSON.stringify(result.ids)+'\n');
const receipt={status:'COMPUTED_PENDING_PYTHON_COMPARISON',source,context,w,n:rows.length,node:process.version,engine_sha256:hash(enginePath),
  files,ids:{path:path.relative(root,idsFile).replaceAll('\\','/'),sha256:hash(idsFile)},metadata:result.metadata,
  observations_changed:false,method:'Nearest parents/proximities only; no EM threshold or family classifications',created_utc:new Date().toISOString()};
fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
process.stdout.write(JSON.stringify({source,context,w,n:rows.length,total_ms:result.metadata.total_ms})+'\n');

