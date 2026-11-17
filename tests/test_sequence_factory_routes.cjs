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
  const mounted=deferred(),mountEntered=deferred(),caseCalls=[];let caseState=null,gateFirst=true;
  function renderCase(container,state){caseState={...state};container.caseControl={value:state.case};}
  const NativeCases={async mount(container,options){caseCalls.push(['mount',options.state.case]);mountEntered.resolve();if(gateFirst){gateFirst=false;await mounted.promise;}renderCase(container,options.state);},async setState(state){caseCalls.push(['setState',state.case]);renderCase(elements.get('nativeCases'),state);},resize(){},destroy(){}};
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
  const controller=scope.SeismicSequenceExplorer.mount(host,{state:routes.normalize({view:'diagnostics',lang:'en'}),getLanguage:()=> 'en',buildURL:()=>'/repo/index.html?workspace=sequences'});
  return {controller,elements,mounted,mountEntered,caseCalls,getCaseState:()=>caseState};
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
  env.controller.destroy();
  console.log('Sequence factory route PASS: real factory forwards latest case through deferred mount, GK→NN navigation, view history, panel-only routes and language');
}
module.exports={regression};
if(require.main===module)regression().catch(error=>{console.error(error);process.exitCode=1;});
