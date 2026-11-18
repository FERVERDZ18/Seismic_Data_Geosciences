'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const directory=path.join(__dirname,'../system/dist/sequences');
function client(options={}){
  const fetched=[],workerUrls=[];
  class LocalWorker{
    constructor(url){
      workerUrls.push(url);
      this.self={postMessage:value=>queueMicrotask(()=>this.onmessage?.({data:value}))};
      const scope=vm.createContext({self:this.self,performance,console});
      scope.importScripts=(...files)=>files.forEach(file=>vm.runInContext(fs.readFileSync(path.join(directory,file),'utf8'),scope));
      vm.runInContext(fs.readFileSync(path.join(directory,'worker.js'),'utf8'),scope);
    }
    postMessage(message){queueMicrotask(()=>{try{this.self.onmessage({data:structuredClone(message)});}catch(error){this.onerror?.({message:error.message});}});}
    terminate(){}
  }
  const window={},scope=vm.createContext({window,URL,...(options.scriptURL?{document:{currentScript:{src:options.scriptURL}}}:{}),crypto:crypto.webcrypto,TextDecoder,Worker:LocalWorker,fetch:async url=>{
    fetched.push(url);const relative=/^https?:/.test(url)?path.posix.relative('/repo/sequences',new URL(url).pathname):url;const target=path.resolve(directory,relative);assert(target.startsWith(path.resolve(directory,'..')));
    let data=fs.readFileSync(target);if(options.tamperPerformance&&url===options.tamperPerformance)data=Buffer.concat([data,Buffer.from(' ')]);
    return {ok:true,status:200,json:async()=>JSON.parse(data),arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength)};
  }});
  vm.runInContext(fs.readFileSync(path.join(directory,'study-data.js'),'utf8'),scope);
  return {api:window.SeismicStudyData,fetched,workerUrls};
}
(async()=>{
  const {api,fetched}=client();
  const first=api.classify('ssn',{cut:'4.5',weight:'fixed'});
  assert.strictEqual(first,api.classify('ssn',{cut:'4.5',weight:'fixed'}));
  const fixed=await first,weighted=await api.classify('ssn',{cut:'4.5',weight:'reported_b'}),common=await api.classify('ssn',{cut:'4.5',membership:'common'});
  assert.equal(fixed.rows.length,1780);assert.equal(common.rows.length,889);assert.equal(weighted.result.metadata.w,1.3265675928192793);
  const anchor=(await api.cases()).find(c=>c.year==='2017').clock_FMD_excluded_anchor_record_ids.ssn;
  const family=value=>{const index=value.rows.findIndex(r=>r.record_id===anchor),component=value.result.component[index];return value.result.component.filter(v=>v===component).length;};
  assert.equal(family(fixed),292);assert.equal(family(weighted),955);
  assert.equal(fetched.filter(u=>u==='data/inputs_4_5.json').length,1);
  assert.equal(fetched.filter(u=>u==='data/calibration.json').length,1);
  assert((await api.basemap()).features.length>0);assert.equal((await api.performance()).measurements.length,49);
  const matched=await api.matchedPerformance();assert.equal(matched.measurements.length,81);assert.equal(matched.threads,1);assert.equal(matched.repetitions,3);
  assert.strictEqual(await api.matchedPerformance(),matched);
  assert.equal(fetched.filter(url=>url==='performance-matched-data.json').length,1);
  await assert.rejects(()=>api.classify('alaska',{membership:'common'}),/Alaska/);
  await assert.rejects(()=>api.classify('ssn',{cut:'3.5',weight:'reported_b'}),/4.5/);
  await assert.rejects(()=>api.checked('../private.json'),/Unlisted/);
  await assert.rejects(()=>client({tamperPerformance:'performance-data.json'}).api.performance(),/integrity/);
  await assert.rejects(()=>client({tamperPerformance:'performance-matched-data.json'}).api.matchedPerformance(),/integrity/);
  const embedded=client({scriptURL:'https://example.test/repo/sequences/study-data.js?v=pinned'});
  const embeddedRows=await embedded.api.classify('ssn',{cut:'4.5'});assert.equal(embeddedRows.rows.length,1780);assert.equal(family(embeddedRows),292);
  assert(embedded.fetched.includes('https://example.test/repo/sequences/data/inputs_4_5.json'));
  assert.deepEqual(embedded.workerUrls,['https://example.test/repo/sequences/worker.js']);
  assert((await embedded.api.basemap()).features.length>0);assert.equal((await embedded.api.performance()).measurements.length,49);

  console.log('Native study client PASS: actual worker protocol, weighted/frozen families, cache separation and tamper rejection');
})().catch(error=>{console.error(error);process.exitCode=1;});
