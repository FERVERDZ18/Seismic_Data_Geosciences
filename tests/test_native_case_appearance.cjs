'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element{
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.style={};this.events={};this.visible=true;this.clientWidth=360;this.className='';this.classList={add:name=>{this.className+=' '+name;}};}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  insertBefore(node,before){this.children.splice(this.children.indexOf(before),0,node);}
  setAttribute(k,v){this.attributes[k]=v;if(k==='class')this.className=v;}
  addEventListener(name,fn){this.events[name]=fn;}
  getClientRects(){return this.visible?[{}]:[];}
  scrollIntoView(){}
  querySelectorAll(selector){const result=[];const match=node=>selector==='[data-case-map]'?!!node.dataset?.caseMap:selector.startsWith('.')?String(node.className).split(/\s+/).includes(selector.slice(1)):false;const walk=node=>{for(const child of node.children||[]){if(match(child))result.push(child);walk(child);}};walk(this);return result;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
const host=new Element('section'),maps=[],scales=[],markers=[],observers=[],listeners=new Set(),variables=new Map([
  ['--map-ocean','#dcece9'],['--map-land','#f0f2e8'],['--map-boundary','#889e97'],['--line','#d4dfd6'],['--muted','#566b61'],['--ink','#183c39']
]);
class Layer{
  constructor(style={}){this.style={...style};this.events={};this.layers=[];}
  addTo(target){target.layers.push(this);return this;}
  bindTooltip(){return this;}
  on(name,fn){this.events[name]=fn;return this;}
  setStyle(style){Object.assign(this.style,style);return this;}
  clearLayers(){this.layers=[];}
  eachLayer(fn){this.layers.forEach(fn);}
}
const L={
  map(container){const map={container,layers:[],controls:[],center:[20,-100],zoom:4,size:{x:640,y:390},invalidations:0,fitCalls:0,
    fitBounds(){this.fitCalls++;this.center=[20,-100];this.zoom=4;return this;},getSize(){return this.size;},invalidateSize(){this.invalidations++;this.size=host.visible?{x:640,y:390}:{x:0,y:0};},
    getContainer(){return this.container;},getZoom(){return this.zoom;},setView(center,zoom){this.center=center;this.zoom=zoom;return this;},remove(){this.removed=true;},attributionControl:{addAttribution(){}}};maps.push(map);return map;},
  canvas:()=>({}),layerGroup:()=>new Layer(),geoJSON:(_,options)=>new Layer(options.style),rectangle:(_,style)=>new Layer(style),circleMarker:(_,style)=>new Layer(style),polyline:(_,style)=>new Layer(style),marker:(coordinates,options)=>{markers.push({coordinates,options});return new Layer();},divIcon:value=>value,latLngBounds:value=>value,
  control:{scale(options){scales.push(options);return {addTo(map){map.controls.push(options);return this;}};}}
};
const rows=source=>[
  {record_id:source+'-anchor',time_utc:'2017-09-08T04:49:18Z',magnitude:8.2,latitude:15,longitude:-94,magnitude_type:null},
  {record_id:source+'-witness',time_utc:'2017-09-19T18:14:39Z',magnitude:7.1,latitude:18.3297,longitude:-98.6712,magnitude_type:null}
];
const sources={};for(const source of ['ssn','usgs'])sources[source]={rows:rows(source),fixedSet:new Set([0]),weightedSet:new Set([0,1]),membersFixed:[0],membersWeighted:[0,1],local:[0],localFixed:[0],localWeighted:[0],fixedSpan:{maximum_gap_days:11.559},anchorIndex:0,witnessIndex:1,index:new Map([[source+'-anchor',0],[source+'-witness',1]]),fixed:{parent:[-1,0]},weighted:{parent:[-1,0]}};
const analysis={anchor:sources.usgs.rows[0],view:{radius:150,before:7,after:30},sources,localPairs:[]};
let classifications=0;
const client={cases:async()=>[],pairs:async()=>({pairs:[]}),basemap:async()=>({features:[]}),classify:async()=>{classifications++;return {};}};
const CaseAnalysis={DAY:86400000,analyze:options=>({...analysis,view:{radius:Number(options.state.radius??150),before:Number(options.state.before??7),after:Number(options.state.after??30)}}),circle:()=>[[15,-94],[16,-94]],inspect:(a,source,i)=>({...a.sources[source].rows[i],fixed:{role:'isolated',parent_record_id:source+'-anchor',log10_eta:-5.22,threshold_log10:-5.31,in_anchor_family:false},reported_b:{role:'associated',parent_record_id:source+'-anchor',log10_eta:-7.90,threshold_log10:-6.14,in_anchor_family:true}})};
class ResizeObserver{constructor(callback){this.callback=callback;observers.push(this);}observe(target){this.target=target;}disconnect(){this.disconnected=true;}notify(){if(!this.disconnected)this.callback([]);}}
const scope={L,CaseAnalysis,ResizeObserver,console,location:{href:'https://example.test/repo/index.html?workspace=sequences&view=cases&case=2017'},requestAnimationFrame:fn=>fn(),document:{documentElement:new Element('html'),createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},getComputedStyle:()=>({getPropertyValue:key=>variables.get(key)||''}),SeismicPreferences:{subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);}}};scope.window=scope;
vm.runInContext(fs.readFileSync('system/dist/sequences/native-cases.js','utf8'),vm.createContext(scope));
(async()=>{
  const original=JSON.stringify(Object.fromEntries(Object.entries(sources).map(([k,v])=>[k,v.rows])));
  await scope.NativeCases.mount(host,{client,state:{lang:'en',case:'2017',comparison:'both',membership:'native',source:'all'}});
  assert.equal(maps.length,2);assert.equal(classifications,4);assert.equal(listeners.size,1);assert.equal(scales.length,2);
  for(const options of scales){assert.equal(options.metric,true);assert.equal(options.imperial,false);assert.equal(options.maxWidth,120);}
  const chartTarget=host.querySelector('.nc-timeline-target');let chart=chartTarget.children[0];
  assert.equal(chart.attributes.viewBox,'0 0 360 320');
  const tickDays=()=>chart.children.filter(node=>node.attributes?.['data-day']!==undefined).map(node=>Number(node.attributes['data-day']));
  assert(tickDays().includes(0));assert(tickDays().includes(-7));assert(tickDays().includes(30));assert(!tickDays().includes(.4));
  assert.equal(host.querySelector('.nc-witness-chip').textContent,'W1/W2');
  const witnessMarkers=markers.filter(marker=>marker.options.icon.className.includes('nc-witness-marker'));
  assert.equal(witnessMarkers.length,2);assert.deepEqual(witnessMarkers.map(marker=>marker.options.icon.iconAnchor[1]).sort((a,b)=>a-b),[-6,30]);
  for(const marker of witnessMarkers)assert.deepEqual(Array.from(marker.coordinates),[18.3297,-98.6712],'Offset labels must retain the original witness coordinates');

  const witness=host.querySelectorAll('.nc-witness-button')[0];witness.events.click();
  const inspector=host.querySelector('.nc-inspector'),inspectedNodes=inspector.children.slice();
  maps[0].setView([18.3,-98.6],7);maps[1].setView([15.2,-94.1],6);
  const geometries=maps.map(map=>map.layers.find(layer=>layer.style.fillColor==='#f0f2e8'));
  variables.set('--map-land','#263c35');variables.set('--map-ocean','#122d35');variables.set('--map-boundary','#6c8a7d');variables.set('--ink','#e4eee8');
  for(const notify of listeners)notify();
  assert.deepEqual(maps.map(m=>m.zoom),[7,6]);assert.deepEqual(maps.map(m=>m.center),[[18.3,-98.6],[15.2,-94.1]]);
  assert.equal(classifications,4);assert.deepEqual(inspector.children,inspectedNodes);
  const sizeCalls=maps.map(map=>map.invalidations);chartTarget.clientWidth=720;observers[0].notify();chart=chartTarget.children[0];
  assert.equal(chart.attributes.viewBox,'0 0 720 360');assert.deepEqual(maps.map(map=>map.invalidations),sizeCalls);assert.deepEqual(maps.map(map=>map.zoom),[7,6]);assert.equal(classifications,4);assert.deepEqual(inspector.children,inspectedNodes);
  const sameChart=chart;observers[0].notify();assert.strictEqual(chartTarget.children[0],sameChart,'Repeated observer notifications at the same width must not redraw');

  geometries.forEach(layer=>{assert.equal(layer.style.fillColor,'#263c35');assert.equal(layer.style.color,'#6c8a7d');});
  maps.forEach(map=>assert.equal(map.container.style.backgroundColor,'#122d35'));
  host.visible=false;const invalidations=maps.map(m=>m.invalidations),fits=maps.map(m=>m.fitCalls);
  for(const notify of listeners)notify();scope.NativeCases.resize();assert.deepEqual(maps.map(m=>m.invalidations),invalidations);
  host.visible=true;scope.NativeCases.resize();assert.deepEqual(maps.map(m=>m.fitCalls),fits);assert.deepEqual(maps.map(m=>m.zoom),[7,6]);
  assert.equal(JSON.stringify(Object.fromEntries(Object.entries(sources).map(([k,v])=>[k,v.rows]))),original);
  scope.NativeCases.destroy();assert(observers.every(observer=>observer.disconnected));assert.equal(listeners.size,0);assert(maps.every(map=>map.removed));assert.equal(host.children.length,0);
  console.log('Native case appearance PASS: responsive timeline/anchor0/natural ticks, witness chips and live themes preserve maps, selected inspector and rows; observer/subscription cleanup verified');
})().catch(error=>{console.error(error);process.exitCode=1;});
