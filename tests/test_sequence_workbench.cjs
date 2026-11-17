'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const dist=path.join(__dirname,'../system/dist');
const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').slice(0,12);
const loaderSource=fs.readFileSync(path.join(dist,'sequence-workbench.js'),'utf8');
const assetManifest=JSON.parse(loaderSource.match(/const ASSETS=(\{[\s\S]*?\});/)[1]);
for(const reference of [...assetManifest.styles,...assetManifest.scripts.map(entry=>entry[0])]){
  const [name,query]=reference.split('?');assert.equal(new URLSearchParams(query).get('v'),digest(path.join(dist,name)),name);
}
const entry=fs.readFileSync(path.join(dist,'index.html'),'utf8');
for(const match of entry.matchAll(/(?:src|href)=["']([^"']+\.(?:js|css))\?v=([a-f0-9]{12})["']/g)){
  if(!match[1].startsWith('vendor/'))assert.equal(match[2],digest(path.join(dist,match[1])),match[1]);
}
function environment({failFirst=false}={}){
  const appended=[],controllers=[];let mountCount=0;
  class Element{
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.events={};this.attributes={};this.hidden=false;}
    setAttribute(k,v){this.attributes[k]=v;}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=[...nodes];}
    addEventListener(name,callback){this.events[name]=callback;}
    remove(){this.removed=true;}
  }
  const document={currentScript:{src:'https://example.test/repo/sequence-workbench.js?v=current'},createElement:tag=>new Element(tag)};
  const scope={URL,URLSearchParams,Promise,queueMicrotask,console,document};scope.window=scope;
  scope.SeismicSequenceExplorer={mount(host,options){
    mountCount++;let state={...options.state,lang:options.getLanguage()};
    const controller={host,options,ready:failFirst&&mountCount===1?Promise.reject(new Error('temporary input failure')):Promise.resolve(),getState:()=>state,
      setState(next){state={...state,...next};},setLanguage(lang){state.lang=lang;},setVisible(value){controller.visible=value;},destroy(){controller.destroyed=true;}};
    controllers.push(controller);return controller;
  }};
  const context=vm.createContext(scope);
  document.head={append(node){appended.push(node);queueMicrotask(()=>{
    if(node.tagName==='SCRIPT'){
      const filename=new URL(node.src).pathname.replace(/^\/repo\//,'');
      document.currentScript=node;
      vm.runInContext(fs.readFileSync(path.join(dist,filename),'utf8'),context,{filename});
    }
    node.onload();
  });}};
  vm.runInContext(fs.readFileSync(path.join(dist,'sequence-workbench.js'),'utf8'),context);
  return {api:context.SeismicSequenceWorkbench,scope,appended,controllers,container:new Element('section')};
}
(async()=>{
  const env=environment(),changes=[],api=await env.api.mount(env.container,{state:{view:'cases',case:'2017',lang:'es'},getLanguage:()=> 'es',onStateChange:(state,meta)=>changes.push({state,meta})});
  assert.equal(env.controllers.length,1);assert.equal(env.container.children.length,1);
  const html=env.container.children[0].innerHTML;
  assert(html.includes('data-seq-id="controls"'));assert(!/<iframe\b/i.test(html));
  const ids=[...html.matchAll(/\sid="([^"]+)"/g)].map(m=>m[1]);assert(ids.every(id=>id.startsWith('seq-')));assert.equal(new Set(ids).size,ids.length);
  assert.equal(changes.length,1);assert.equal(changes[0].meta.initial,true);
  assert(env.appended.filter(n=>n.tagName==='SCRIPT').every(n=>new URL(n.src).origin==='https://example.test'));
  const focused=new URL(api.buildURL({...api.getState(),case:'2022',panel:'local',redirect:'https://evil.test',token:'private'}));
  assert.equal(focused.pathname,'/repo/index.html');assert.equal(focused.searchParams.get('workspace'),'sequences');assert.equal(focused.searchParams.get('panel'),'local');assert(!focused.searchParams.has('redirect'));assert(!focused.searchParams.has('token'));
  const exact=new URL(api.buildURL({...api.getState(),view:'cases',case:'2022',panel:'inspector',full_lat:'18.125',full_lon:'-103.5',full_zoom:'7.3',local_lat:'18.25',local_lon:'-103.25',local_zoom:'8.1',expanded_map:'local',point_size:'large',inspect_source:'ssn',inspect_record:'ssn-mx-historical~ssn-local-abc-1'}));
  assert.equal(exact.searchParams.get('full_zoom'),'7.3');assert.equal(exact.searchParams.get('local_lon'),'-103.25');assert.equal(exact.searchParams.get('expanded_map'),'local');assert.equal(exact.searchParams.get('point_size'),'large');assert.equal(exact.searchParams.get('inspect_record'),'ssn-mx-historical~ssn-local-abc-1');
  const invalid=new URL(api.buildURL({...api.getState(),view:'cases',full_lat:'91',full_lon:'-103',full_zoom:'7',inspect_source:'ssn',inspect_record:'../private'}));assert(!invalid.searchParams.has('full_lat'));assert(!invalid.searchParams.has('full_zoom'));assert(!invalid.searchParams.has('inspect_record'));
  for(const view of ['explorer','cases','diagnostics','benchmark']){
    const u=new URL(api.buildURL({view,case:'2017',lang:'en'}));assert.equal(u.searchParams.get('view'),view);
  }
  await api.setState({view:'cases',case:'2022',panel:'timeline',lang:'en'});assert.equal(api.getState().case,'2022');assert.equal(api.getState().lang,'en');
  api.setVisible(false);assert.equal(env.controllers[0].visible,false);await api.setLanguage('es');assert.equal(api.getState().lang,'es');
  api.destroy();assert.equal(env.controllers[0].destroyed,true);assert.equal(env.container.children.length,0);
  const recovery=environment({failFirst:true}),recovered=await recovery.api.mount(recovery.container,{state:{view:'cases',case:'2017',lang:'en'}});
  const retry=recovery.container.children.find(e=>e.tagName==='BUTTON');assert(retry);assert.equal(retry.textContent,'Retry');
  await retry.events.click();assert.equal(recovery.controllers.length,2);assert.equal(recovered.getState().case,'2017');
  await recovered.setLanguage('es');assert.equal(recovery.controllers[1].getState().lang,'es');
  console.log('Sequence workbench PASS: same-document host, scoped IDs, lazy components, root/panel URLs, state/language lifecycle and recoverable input failure');
})().catch(error=>{console.error(error);process.exitCode=1;});
