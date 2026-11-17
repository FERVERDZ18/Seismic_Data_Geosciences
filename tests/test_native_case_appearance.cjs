'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const routes=require('../system/dist/sequences/sequence-view.js');
class Element{
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.style={};this.events={};this.visible=true;this.clientWidth=360;this.className='';this.classList={add:name=>{this.className+=' '+name;},toggle:(name,active)=>{const names=this.className.split(/\s+/).filter(value=>value!==name);if(active)names.push(name);this.className=names.join(' ');}};}
  append(...nodes){this.children.push(...nodes);}
  get firstChild(){return this.children[0]||null;}
  replaceChildren(...nodes){this.children=[...nodes];}
  insertBefore(node,before){this.children.splice(this.children.indexOf(before),0,node);}
  setAttribute(k,v){this.attributes[k]=v;if(k==='class')this.className=v;}
  removeAttribute(k){delete this.attributes[k];}
  cloneNode(deep){const copy=new Element(this.tagName);copy.attributes={...this.attributes};copy.className=this.className;copy.textContent=this.textContent;copy.dataset={...this.dataset};if(deep)copy.children=this.children.map(child=>child.cloneNode(true));return copy;}
  addEventListener(name,fn){this.events[name]=fn;}
  click(){return this.events.click?.();}
  getClientRects(){return this.visible?[{}]:[];}
  scrollIntoView(){}
  querySelectorAll(selector){const result=[];const match=node=>selector==='[data-case-map]'?!!node.dataset?.caseMap:selector==='[tabindex]'?node.attributes?.tabindex!==undefined:selector==='svg'?node.tagName==='svg':selector.startsWith('.')?String(node.className).split(/\s+/).includes(selector.slice(1)):false;const walk=node=>{for(const child of node.children||[]){if(match(child))result.push(child);walk(child);}};walk(this);return result;}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
}
const host=new Element('section'),maps=[],scales=[],markers=[],circles=[],observers=[],listeners=new Set(),variables=new Map([
  ['--map-ocean','#dcece9'],['--map-land','#f0f2e8'],['--map-boundary','#889e97'],['--line','#d4dfd6'],['--muted','#566b61'],['--ink','#183c39']
]);
class Layer{
  constructor(style={}){this.style={...style};this.events={};this.layers=[];}
  addTo(target){target.layers.push(this);return this;}
  bindTooltip(){return this;}
  on(name,fn){this.events[name]=fn;return this;}
  setStyle(style){Object.assign(this.style,style);return this;}
  setIcon(icon){this.icon=icon;return this;}
  clearLayers(){this.layers=[];}
  eachLayer(fn){this.layers.forEach(fn);}
}
const L={
  map(container,options){const map={container,options,layers:[],controls:[],events:{},center:[20,-100],zoom:4,size:{x:640,y:390},invalidations:0,fitCalls:0,
    fitBounds(bounds){this.fitCalls++;this.lastFit=bounds;this.center=[20,-100];this.zoom=4.3;this.events.moveend?.();return this;},getSize(){return this.size;},invalidateSize(){this.invalidations++;this.size=host.visible?{x:640,y:390}:{x:0,y:0};},
    on(name,callback){this.events[name]=callback;return this;},getCenter(){return {lat:this.center[0],lng:this.center[1]};},getBounds(){return {contains:([lat,lon])=>lat>=-5&&lat<=35&&lon>=-120&&lon<=-70,getSouth:()=>-5,getWest:()=>-120,getNorth:()=>35,getEast:()=>-70};},latLngToContainerPoint([lat,lon]){return {x:(lon+110)*10,y:(25-lat)*20};},containerPointToLatLng([x,y]){return [25-y/20,x/10-110];},getContainer(){return this.container;},getZoom(){return this.zoom;},setView(center,zoom){this.center=Array.from(center);this.zoom=zoom;this.events.moveend?.();return this;},remove(){this.removed=true;},attributionControl:{addAttribution(){}}};maps.push(map);return map;},
  canvas:()=>({}),layerGroup:()=>new Layer(),geoJSON:(_,options)=>new Layer(options.style),rectangle:(_,style)=>new Layer(style),circleMarker:(coordinates,style)=>{circles.push({coordinates:Array.from(coordinates),style});return new Layer(style);},polyline:(_,style)=>new Layer(style),marker:(coordinates,options)=>{markers.push({coordinates,options});return new Layer();},divIcon:value=>value,latLngBounds:value=>value,
  control:{scale(options){scales.push(options);return {addTo(map){map.controls.push(options);return this;}};}}
};
const rows=source=>[
  {record_id:source+'-anchor',time_utc:'2017-09-08T04:49:18Z',magnitude:8.2,latitude:15,longitude:-94,magnitude_type:null},
  {record_id:source+'-witness',time_utc:'2017-09-19T18:14:39Z',magnitude:7.1,latitude:18.3297,longitude:-98.6712,magnitude_type:null},
  {record_id:source+'-context',time_utc:'2018-01-04T01:49:18Z',magnitude:4.6,latitude:25,longitude:-110,magnitude_type:null}
];
const sources={};for(const source of ['ssn','usgs'])sources[source]={rows:rows(source),fixedSet:new Set([0]),weightedSet:new Set([0,1]),membersFixed:[0],membersWeighted:[0,1],local:[0],localFixed:[0],localWeighted:[0],fixedSpan:{maximum_gap_days:11.559},anchorIndex:0,witnessIndex:1,index:new Map([[source+'-anchor',0],[source+'-witness',1]]),fixed:{parent:[-1,0]},weighted:{parent:[-1,0]}};
const analysis={anchor:sources.usgs.rows[0],view:{radius:150,before:7,after:30},sources,localPairs:[]};
let classifications=0,analyses=0;
const client={cases:async()=>[],pairs:async()=>({pairs:[]}),basemap:async()=>({type:'FeatureCollection',features:[{type:'Feature',geometry:{type:'Polygon',coordinates:[[[-110,14],[-90,14],[-90,25],[-110,25],[-110,14]]]}}]}),classify:async()=>{classifications++;return {};}};
const CaseAnalysis={DAY:86400000,analyze:options=>{analyses++;return {...analysis,view:{radius:Number(options.state.radius??150),before:Number(options.state.before??7),after:Number(options.state.after??30)}};},circle:()=>[[15,-94],[16,-94]],inspect:(a,source,i)=>({...a.sources[source].rows[i],fixed:{role:'isolated',parent_record_id:source+'-anchor',log10_eta:-5.22,threshold_log10:-5.31,in_anchor_family:false},reported_b:{role:'associated',parent_record_id:source+'-anchor',log10_eta:-7.90,threshold_log10:-6.14,in_anchor_family:true}})};
class ResizeObserver{constructor(callback){this.callback=callback;observers.push(this);}observe(target){this.target=target;}disconnect(){this.disconnected=true;}notify(){if(!this.disconnected)this.callback([]);}}
const exportedBlobs=[],escape=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
class XMLSerializer{serializeToString(node){return '<'+node.tagName+Object.entries(node.attributes).map(([key,value])=>' '+key+'="'+escape(value)+'"').join('')+'>'+escape(node.textContent||'')+node.children.map(child=>this.serializeToString(child)).join('')+'</'+node.tagName+'>';}}
const scope={L,CaseAnalysis,ResizeObserver,SeismicSequenceView:routes,XMLSerializer,Blob,URL:{createObjectURL(blob){exportedBlobs.push(blob);return 'blob:test';},revokeObjectURL(){}},setTimeout:fn=>fn(),console,location:{pathname:'/repo/index.html',href:'https://example.test/repo/index.html?workspace=sequences&view=cases&case=2017'},requestAnimationFrame:fn=>fn(),document:{documentElement:new Element('html'),createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)},getComputedStyle:()=>({getPropertyValue:key=>variables.get(key)||''}),SeismicPreferences:{subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);}}};scope.window=scope;
vm.runInContext(fs.readFileSync('system/dist/sequences/native-cases.js','utf8'),vm.createContext(scope));
(async()=>{
  const original=JSON.stringify(Object.fromEntries(Object.entries(sources).map(([k,v])=>[k,v.rows])));
  const changes=[];
  await scope.NativeCases.mount(host,{client,state:{lang:'en',case:'2017',comparison:'both',membership:'native',source:'all'},buildURL:state=>'https://example.test/repo/index.html'+routes.query(state),onStateChange:(patch,meta)=>changes.push({patch,meta})});
  assert.equal(maps.length,2);assert.equal(classifications,4);assert.equal(listeners.size,1);assert.equal(scales.length,2);
  assert.equal(analyses,1);maps.forEach(map=>{assert.equal(map.options.zoomSnap,.1);assert.equal(map.options.zoomDelta,.5);});
  assert(maps[0].lastFit.some(point=>point[0]===14),'The full-family fit must preserve the northern edge of the unqueried south');
  assert(maps[0].lastFit.some(point=>point[0]===18.3297&&point[1]===-98.6712),'The full fit must include the unchanged complete-family coordinates');
  assert.equal(host.querySelectorAll('.nc-map-key').length,2);
  assert.equal(maps[0].container.querySelector('.nc-map-key'),null,'The legend must remain outside the geographic map viewport');
  assert.deepEqual(circles.slice(0,6).map(circle=>circle.style.radius),[2,2,3.6,3.6,4.3,4.3],'Context from both sources must be painted before either family and before additions');
  for(const options of scales){assert.equal(options.metric,true);assert.equal(options.imperial,false);assert.equal(options.maxWidth,120);}
  const chartTarget=host.querySelector('.nc-timeline-target');let chart=chartTarget.children[0];
  assert.equal(chart.attributes.viewBox,'0 0 360 320');
  const tickDays=()=>chart.children.filter(node=>node.attributes?.['data-day']!==undefined).map(node=>Number(node.attributes['data-day']));
  assert(tickDays().includes(0));assert(tickDays().includes(-7));assert(tickDays().includes(30));assert(!tickDays().includes(.4));
  assert.equal(host.querySelector('.nc-witness-chip').textContent,'W1/W2');
  const witnessMarkers=markers.filter(marker=>marker.options.icon.className.includes('nc-witness-marker'));
  assert.equal(witnessMarkers.length,2);
  for(const marker of witnessMarkers)assert.deepEqual(Array.from(marker.coordinates),[18.3297,-98.6712],'Offset labels must retain the original witness coordinates');

  const witness=host.querySelectorAll('.nc-witness-button')[0];witness.events.click();
  const inspector=host.querySelector('.nc-inspector'),inspectedNodes=inspector.children.slice();
  maps[0].setView([18.3,-98.6],7);maps[1].setView([15.2,-94.1],6);
  const changedCount=changes.length,drawnCircles=circles.length;maps[0].events.moveend();
  assert.equal(changes.length,changedCount,'A duplicate moveend must not notify the router again');assert.equal(circles.length,drawnCircles);assert.equal(maps.length,2);assert.equal(analyses,1);
  const mapState=scope.NativeCases.getState();assert.equal(mapState.full_lat,'18.3');assert.equal(mapState.full_lon,'-98.6');assert.equal(mapState.full_zoom,'7');assert.equal(mapState.local_zoom,'6');assert.equal(mapState.inspect_record,'ssn-witness');
  assert(changes.every(change=>change.meta.presentation===true));assert.equal(changes.at(-1).meta.context.case,'2017');
  for(const link of host.querySelectorAll('.nc-panel-link')){const restored=routes.parse(new URL(link.href).search);assert.equal(restored.full_zoom,'7');assert.equal(restored.inspect_record,'ssn-witness');}
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
  const previousMaps=maps.slice();await scope.NativeCases.setLanguage('es');
  assert.equal(classifications,4);assert.equal(analyses,1);assert.equal(maps.length,4);assert.equal(scope.NativeCases.getState().inspect_record,'ssn-witness');assert.equal(host.querySelector('.nc-record-id').textContent,'ssn-witness');
  assert.deepEqual(maps.slice(-2).map(map=>map.center),[[18.3,-98.6],[15.2,-94.1]]);assert.deepEqual(maps.slice(-2).map(map=>map.zoom),[7,6]);
  const afterLanguage=changes.length;previousMaps[0].setView([30,-110],3);assert.equal(changes.length,afterLanguage,'Detached maps must never overwrite a later route');
  const reloaded=routes.parse('?view=cases&case=2017&lang=es&full_lat=20.125&full_lon=-101.75&full_zoom=6.4&local_lat=15.125&local_lon=-94.25&local_zoom=7.2&inspect_source=usgs&inspect_record=usgs-witness');
  const mapCount=maps.length;await scope.NativeCases.setState(reloaded);
  assert.equal(maps.length,mapCount);assert.equal(classifications,4);assert.equal(analyses,1);assert.deepEqual(maps.slice(-2).map(map=>map.zoom),[6.4,7.2]);assert.equal(host.querySelector('.nc-record-id').textContent,'usgs-witness');
  assert.equal(changes.length,afterLanguage,'Restoring exact viewports and a valid inspector must not create a history loop');
  const beforeLarge=circles.length;await scope.NativeCases.setState({...scope.NativeCases.getState(),point_size:'large'});
  assert.equal(classifications,4);assert.equal(analyses,1);const large=circles.slice(beforeLarge).filter(circle=>circle.style.renderer);
  assert.equal(large.length,8);assert(large.some(circle=>circle.style.radius===4.3*1.75));
  assert(large.every(circle=>Object.values(sources).some(source=>source.rows.some(row=>row.latitude===circle.coordinates[0]&&row.longitude===circle.coordinates[1]))),'Large symbols must never relocate any source row');
  const beforeExpand=maps.length;host.querySelectorAll('.nc-expand-map')[0].events.click();
  assert.equal(maps.length,beforeExpand);assert.equal(scope.NativeCases.getState().expanded_map,'full');assert.equal(host.querySelector('.nc-expand-map').attributes['aria-pressed'],'true');assert(host.querySelector('.nc-map-expanded'));
  const expanded=routes.parse(new URL(host.querySelector('.nc-panel-link').href).search);assert.equal(expanded.expanded_map,'full');assert.equal(expanded.point_size,'large');assert.equal(expanded.full_zoom,'6.4');
  host.querySelectorAll('.nc-fit-map')[0].events.click();assert.equal(scope.NativeCases.getState().full_zoom,'4.3');assert.equal(classifications,4);assert.equal(analyses,1);
  await scope.NativeCases.setState({...scope.NativeCases.getState(),inspect_source:'ssn',inspect_record:'missing-record'});assert.equal(scope.NativeCases.getState().inspect_record,undefined);assert.equal(host.querySelector('.nc-record-id'),null);
  await scope.NativeCases.setState(routes.transition(scope.NativeCases.getState(),{radius:'200'}));assert.equal(classifications,4);assert.equal(analyses,2);assert.equal(scope.NativeCases.getState().inspect_record,undefined);assert.equal(scope.NativeCases.getState().full_zoom,'4.3');
  const beforeExport={maps:maps.length,classifications,analyses,changes:changes.length,circles:circles.length};
  const exported=host.querySelectorAll('.nc-export-map')[0].events.click();
  assert.equal(exportedBlobs.length,1);assert.equal(exportedBlobs[0].type,'image/svg+xml;charset=utf-8');assert.equal(await exportedBlobs[0].text(),exported);
  assert(exported.startsWith('<?xml version="1.0"'));assert(exported.includes('viewBox="0 0 640 495"'));assert(exported.includes('clip-path="url(#native-map-clip)"'));assert(exported.includes('seismic-native-map-svg/1'));assert(exported.includes('Leaflet projection'));assert(exported.includes('footer_height&quot;:105'));assert(exported.includes('Otros registros</text>'),'Legend words and spaces must be emitted together as complete labels');
  assert.equal((exported.match(/data-record-id=/g)||[]).length,6);assert.equal((exported.match(/font-size="20"/g)||[]).length,7);assert(exported.includes('cx="160" cy="200"'),'The SVG must use Leaflet’s live projection for the unchanged anchor coordinate');
  const overlap=(a,b)=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y,cross=(a,b,c)=>(b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x),crossing=(a,b,c,d)=>cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0;
  for(const factor of [1,1.75])for(const points of [[{x:312,y:269},{x:378,y:311}],[{x:250,y:250},{x:250,y:250}],[{x:251,y:251},{x:249,y:249}]]){const anchor=points[0].x===312?{x:400,y:333}:{x:250,y:250},radius=12*factor+4,star={x:anchor.x-radius,y:anchor.y-radius,width:radius*2,height:radius*2},originalPoints=JSON.stringify(points),placed=scope.NativeCases.layoutWitnesses(points.map((point,i)=>({label:'W'+(i+1),point})),anchor,{x:488,y:390},factor);assert(!placed.some(box=>overlap(box,star)),'Witness boxes must never cover the anchor, including coincident source epicentres');assert(!overlap(placed[0],placed[1]));assert(!crossing(placed[0].leader.from,placed[0].leader.to,placed[1].leader.from,placed[1].leader.to),'Witness leaders must not cross');assert.equal(JSON.stringify(points),originalPoints,'Only annotation boxes may move');}
  assert.deepEqual({maps:maps.length,classifications,analyses,changes:changes.length,circles:circles.length},beforeExport,'Export must not reclassify, redraw, move or reroute the live view');
  const liveTimeline=host.querySelector('.nc-timeline'),timelineChildren=liveTimeline.children.slice(),timelineSVG=host.querySelector('.nc-export-timeline').events.click();
  assert.equal(exportedBlobs.length,2);assert(timelineSVG.includes('seismic-native-timeline-svg/1'));assert(/<svg[^>]*><rect[^>]*fill="#fff"/.test(timelineSVG),'The exported timeline must start with an opaque theme-paper background');assert(timelineSVG.includes('font-family:Arial,sans-serif;font-size:14px'));assert(!timelineSVG.includes('font:14px system-ui'));assert.equal((timelineSVG.match(/class="nc-event-point"/g)||[]).length,2);assert(!timelineSVG.includes('tabindex='));assert.deepEqual(liveTimeline.children,timelineChildren,'Export styling and background must leave the live timeline data and axes intact');assert.deepEqual({maps:maps.length,classifications,analyses,changes:changes.length,circles:circles.length},beforeExport);
  const metadata=data=>JSON.parse(data.match(/<metadata>([\s\S]*?)<\/metadata>/)[1].replaceAll('&quot;','"').replaceAll('&lt;','<').replaceAll('&amp;','&'));
  const runtimeBeforePanelExport=JSON.stringify(scope.NativeCases.getState()),localSVG=host.querySelectorAll('.nc-export-map')[1].events.click();
  for(const [data,panel] of [[exported,'full'],[localSVG,'local'],[timelineSVG,'timeline']]){const snapshot=metadata(data);assert.equal(snapshot.panel,panel);assert.equal(snapshot.state.panel,panel);assert.equal(new URL(snapshot.url).searchParams.get('panel'),panel);assert.deepEqual(routes.parse(new URL(snapshot.url).search),snapshot.state,'Exported state must describe the same panel and camera as its own URL');}
  assert.equal(JSON.stringify(scope.NativeCases.getState()),runtimeBeforePanelExport,'Export snapshot metadata must not change live focus or presentation');
  assert.equal(JSON.stringify(Object.fromEntries(Object.entries(sources).map(([k,v])=>[k,v.rows]))),original);
  scope.NativeCases.destroy();assert(observers.every(observer=>observer.disconnected));assert.equal(listeners.size,0);assert(maps.every(map=>map.removed));assert.equal(host.children.length,0);
  console.log('Native case appearance PASS: fractional family fit, viewport/inspector URLs and reloads, move-only updates, expansion, large symbols, language/theme/selection preservation and unchanged source coordinates; cleanup verified');
})().catch(error=>{console.error(error);process.exitCode=1;});
