'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const routes=require('../system/dist/sequences/sequence-view.js');
class Element{
  constructor(){this.children=[];this.dataset={};this.attributes={};this.events={};this.options=[{},{},{}];this.value='';this.checked=false;this.hidden=false;this.disabled=false;this.textContent='';}
  append(...nodes){for(const node of nodes){node.parentElement=this;this.children.push(node);}}
  replaceChildren(...nodes){this.children=[];this.append(...nodes);}
  setAttribute(k,v){this.attributes[k]=v;}
  removeAttribute(k){delete this.attributes[k];}
  addEventListener(name,fn){this.events[name]=fn;}
  scrollIntoView(){this.scrolled=true;}
  querySelector(selector){if(selector.startsWith('[data-case-map='))return this.focusTarget||(this.focusTarget=new Element());return null;}
}
function deferred(){let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};}
function environment(sourceOverride){
  const fragment=fs.readFileSync(path.join(__dirname,'../system/dist/sequence-workbench.js'),'utf8');
  const ids=[...fragment.matchAll(/data-seq-id=\\"([^\\]+)\\"/g)].map(m=>m[1]);
  const elements=new Map([...new Set(ids)].map(id=>[id,new Element()]));
  const nav=new Element(),links=['explorer','cases','diagnostics','benchmark'].map(view=>{const node=new Element();node.dataset.studyView=view;return node;});
  const host={querySelector(selector){if(selector==='.workspace-nav')return nav;const match=selector.match(/^\[data-seq-id="([^"]+)"\]$/);return match?elements.get(match[1]):null;},querySelectorAll(selector){return selector==='[data-study-view]'?links:[];},replaceChildren(){}};
  const mounted=deferred(),mountEntered=deferred(),caseCalls=[],changes=[];let caseState=null,gateFirst=true,nativeOptions=null;
  function renderCase(container,state){caseState={...state};container.caseControl={value:state.case};}
  const NativeCases={async mount(container,options){nativeOptions=options;caseCalls.push(['mount',options.state.case]);mountEntered.resolve();if(gateFirst){gateFirst=false;await mounted.promise;}renderCase(container,options.state);},async setState(state){caseCalls.push(['setState',state.case]);renderCase(elements.get('nativeCases'),state);},resize(){},destroy(){}};
  const NativeDiagnostics={async mount(){},async setState(){},destroy(){}},NativePerformance={async mount(){},setState(){},destroy(){}};
  const rows=source=>[{record_id:source+'-a',time_utc:'2017-09-08T04:49:18Z',latitude:15,longitude:-94,magnitude:8.2},{record_id:source+'-b',time_utc:'2022-09-19T18:05:08Z',latitude:18,longitude:-103,magnitude:7.6}];
  const definitions=['2017','2022'].map(year=>({year,anchor:{record_id:'usgs-'+year,time_utc:year==='2017'?'2017-09-08T04:49:18Z':'2022-09-19T18:05:08Z',latitude:15,longitude:-94,magnitude:8.2}}));
  const data={sources:{ssn:rows('ssn'),usgs:rows('usgs'),alaska:rows('alaska')}};
  const client={manifest:async()=>({snapshot_utc:'test'}),basemap:async()=>({features:[]}),checked:async name=>name==='diagnostics.json'?{cases:definitions}:name.startsWith('inputs_')?data:name==='calibration.json'?{cuts:{'4.5':{ssn:{threshold_log10:-5,w:1},usgs:{threshold_log10:-5,w:1}}}}:{pairs:[]}};
  class Worker{
    postMessage(message){assert.equal(message.method,'gk');queueMicrotask(()=>this.onmessage({data:{request:message.request,result:{ids:message.rows.map(r=>r.record_id),parent:[-1,0],component:[0,0],roles:['main','associated'],metadata:{total_ms:1,method:'gk'}}}}));}
    terminate(){}
  }
  const scope={URL,Promise,Map,Set,Date,JSON,Math,Number,console,performance,queueMicrotask,Worker,requestAnimationFrame:fn=>fn(),location:{search:'?workspace=sequences&view=diagnostics&lang=en',pathname:'/repo/index.html'},SeismicSequenceView:routes,SeismicStudyData:client,NativeCases,NativeDiagnostics,NativePerformance,
    document:{currentScript:{src:'https://example.test/repo/sequences/app.js'},createElement:()=>new Element(),createElementNS:()=>new Element()}};
  scope.window=scope;
  const source=sourceOverride||fs.readFileSync(path.join(__dirname,'../system/dist/sequences/app.js'),'utf8');vm.runInContext(source,vm.createContext(scope));
  const controller=scope.SeismicSequenceExplorer.mount(host,{state:routes.normalize({view:'diagnostics',lang:'en'}),getLanguage:()=> 'en',buildURL:()=>'/repo/index.html?workspace=sequences',onStateChange:(state,meta)=>changes.push({state,meta})});
  return {controller,elements,mounted,mountEntered,caseCalls,changes,nativeChange:(patch,meta)=>nativeOptions.onStateChange(patch,meta),getCaseState:()=>caseState};
}
async function regression(sourceOverride){
  const env=environment(sourceOverride),base=routes.normalize({view:'cases',case:'2017',lang:'en'});
  await env.controller.ready;
  // A real factory mount is held while a newer route requests another year.
  const first=env.controller.setState(base);await env.mountEntered.promise;
  const latest=env.controller.setState({...base,case:'2022',panel:'full'});env.mounted.resolve();await Promise.all([first,latest]);
  assert.equal(env.controller.getState().case,'2022');assert.equal(env.elements.get('nativeCases').caseControl.value,'2022');assert.equal(env.getCaseState().case,'2022');
  assert.deepEqual(env.caseCalls.slice(0,2),[['mount','2017'],['setState','2022']]);
  // Reproduce the reported browser path with an actual GK Explorer result that
  // deliberately has no NN T/R arrays. Native navigation must not render it as NN.
  await env.controller.setState(base);
  await env.controller.setState({...base,view:'diagnostics'});
  await env.controller.setState({...base,view:'benchmark',benchmark_n:'2000'});
  await env.controller.setState({...base,view:'diagnostics'});
  await env.controller.setState({...base,view:'explorer',case:'all',method:'gk'});
  assert.equal(env.elements.get('exportCsv').disabled,false,'GK result must have completed, rather than bypassing the rendering path');
  await env.controller.setState({...base,case:'2022',panel:'full'});
  assert.equal(env.controller.getState().case,'2022');assert.equal(env.elements.get('nativeCases').caseControl.value,'2022');
  assert.equal(env.getCaseState().method,'nn');assert.equal(env.getCaseState().case,'2022');
  const count=env.caseCalls.length;await env.controller.setState({...base,case:'2022',panel:'local'});
  assert.equal(env.caseCalls.length,count,'Changing only focused panel must preserve the actual native render');
  await env.controller.setLanguage('es');assert.equal(env.elements.get('nativeCases').caseControl.value,'2022');assert.equal(env.getCaseState().lang,'es');
  const presentationCalls=env.caseCalls.length;
  const context=Object.fromEntries(['case','membership','radius','before','after'].map(key=>[key,env.controller.getState()[key]]));
  env.nativeChange({full_lat:'19.25',full_lon:'-103.5',full_zoom:'7.3',local_lat:'18.4',local_lon:'-103.25',local_zoom:'8.1',inspect_source:'ssn',inspect_record:'source-record-2022'},{presentation:true,context});
  assert.equal(env.caseCalls.length,presentationCalls,'A move or record selection must not queue a native rerender');assert.equal(env.controller.getState().full_zoom,'7.3');assert.equal(env.controller.getState().inspect_record,'source-record-2022');assert.equal(env.changes.at(-1).meta.push,false);
  const notifications=env.changes.length;await env.controller.setState({...env.controller.getState(),panel:'inspector'});
  assert.equal(env.caseCalls.length,presentationCalls);assert.equal(env.changes.length,notifications,'A route restore must not notify root history again');
  env.nativeChange({full_zoom:'3'},{presentation:true,context:{...context,case:'2017'}});assert.equal(env.controller.getState().full_zoom,'7.3','A stale map callback must not overwrite a newer case');
  await env.controller.setState({...env.controller.getState(),full_zoom:'6.2'});assert.equal(env.getCaseState().full_zoom,'6.2');assert.equal(env.changes.length,notifications);
  await env.nativeChange({radius:'200'});for(const key of [...routes.viewportKeys,'inspect_source','inspect_record'])assert.equal(env.controller.getState()[key],undefined,'Window controls must reset old extents and inspected IDs');
  const freshRoute=routes.normalize({...base,case:'2017',lang:'es',full_lat:'15.75',full_lon:'-94.25',full_zoom:'6.8',inspect_source:'usgs',inspect_record:'source-record-2017'});await env.controller.setState(freshRoute);assert.equal(env.getCaseState().case,'2017');assert.equal(env.getCaseState().full_zoom,'6.8');assert.equal(env.getCaseState().inspect_record,'source-record-2017','A complete restored URL retains its own viewport and record when the case changes');
  await env.controller.setState({...base,case:'2022',lang:'es'});assert.equal(env.getCaseState().full_zoom,undefined);assert.equal(env.getCaseState().inspect_record,undefined,'An old URL without presentation fields must not inherit the previous route selection');
  env.controller.destroy();
  console.log('Sequence factory route PASS: deferred latest case, GK→NN navigation, viewport/record move-only routes, stale-event rejection, complete URL restoration and window reset semantics');
}
module.exports={regression};
if(require.main===module)regression().catch(error=>{console.error(error);process.exitCode=1;});
