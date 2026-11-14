'use strict';
const assert=require('node:assert/strict'),M=require('../system/dist/map-tools.js');
const f={geometry:{type:'Polygon',coordinates:[[[-104,15],[-98,15],[-98,20],[-104,20],[-104,15]],[[-102,16],[-101,16],[-101,17],[-102,17],[-102,16]]]}};
assert(M.contains(f,-103,18));assert(!M.contains(f,-101.5,16.5));assert(!M.contains(f,-110,18));
const dateline={geometry:{type:'Polygon',coordinates:[[[170,50],[-170,50],[-170,60],[170,60],[170,50]]]}};
assert(M.contains(dateline,179,55));assert(M.contains(dateline,-179,55));assert(!M.contains(dateline,-150,55));
assert.equal(M.coordinateText(15.688,-99.212),'15.6880° N · 99.2120° W');assert.equal(M.coordinateText(-2,181),'2.0000° S · 179.0000° W');
const tones=[2.99,3,4.99,5,6.99,7].map(m=>M.magnitudeColor('#0d9471',m));assert(tones[0].endsWith('78%)'));assert.equal(tones[1],tones[2]);assert(tones[3].endsWith('42%)'));assert(tones[5].endsWith('27%)'));assert.notEqual(M.magnitudeColor('#2563eb',5),M.magnitudeColor('#0d9471',5));
assert.equal(M.shakingLinks({id:'us2000ahv0',mag:5.9}), '');assert(M.shakingLinks({id:'us2000ahv0',mag:8.2}).includes('/us2000ahv0/shakemap/intensity'));
assert(M.shakingLinks({id:'usgs-na~us2000ahv0',source_event_id:'us2000ahv0',mag:8.2}).includes('/us2000ahv0/dyfi/intensity'));
assert(!M.shakingLinks({id:'ssn-key',mag:7.8,_catalog_id:'ssn-mx-historical'}).includes('href='));assert(!M.shakingLinks({id:'<script>',mag:8}).includes('<script>'));
console.log('PASS coordinate wrap, polygon holes/dateline, magnitude boundaries and source-safe official intensity links');

// Pan outside and back: a displaced rank badge must travel with its epicentre.
const rankLayers=new Set(),rankHandlers={},rankLeaders={layers:[],addTo(){rankLayers.add(this);return this;},clearLayers(){this.layers=[];}};
let rankPan=0;
const rankMap={
  getSize:()=>({x:400,y:300}),getContainer:()=>({getBoundingClientRect:()=>({left:0,top:0}),querySelectorAll:()=>[]}),
  latLngToLayerPoint:p=>({x:p[1]+rankPan,y:p[0]}),latLngToContainerPoint:p=>({x:p[1]+rankPan,y:p[0]}),
  layerPointToLatLng:p=>[p[1],p[0]-rankPan],hasLayer:layer=>rankLayers.has(layer),removeLayer:layer=>rankLayers.delete(layer),
  on(events,fn){for(const event of events.split(' '))rankHandlers[event]=fn;},off(events,fn){for(const event of events.split(' '))if(rankHandlers[event]===fn)delete rankHandlers[event];}
};
const originalWindow=global.window;
global.window={L:{layerGroup:()=>rankLeaders,divIcon:options=>options,
  polyline:points=>({addTo(group){group.layers.push({kind:'leader',points});return this;}}),
  circleMarker:point=>({addTo(group){group.layers.push({kind:'epicentre',point});return this;}})}};
try{
  const point=[100,100],marker={addTo(){rankLayers.add(this);return this;},setIcon(icon){this.icon=icon;return this;}}.addTo(rankMap);
  const ranks=M.declutterRanks(rankMap,[{marker,point,html:'<b>1</b>'}]);
  assert(rankLayers.has(marker));assert.equal(rankLeaders.layers.length,2);assert.notDeepEqual(marker.icon.iconAnchor,[17,17]);
  rankPan=-110;rankHandlers.moveend();
  assert(!rankLayers.has(marker),'an off-screen epicentre must not leave its displaced badge visible');assert.equal(rankLeaders.layers.length,0);
  rankPan=0;rankHandlers.moveend();
  assert(rankLayers.has(marker),'panning back must restore the same rank marker');assert.equal(rankLeaders.layers.length,2);
  rankPan=350;rankHandlers.zoomend();assert(!rankLayers.has(marker));assert.equal(rankLeaders.layers.length,0);
  rankPan=0;rankHandlers.resize();assert(rankLayers.has(marker));assert.equal(rankLeaders.layers.length,2);assert.deepEqual(point,[100,100]);
  ranks.dispose();assert(!rankLayers.has(rankLeaders));assert.equal(Object.keys(rankHandlers).length,0);
}finally{if(originalWindow===undefined)delete global.window;else global.window=originalWindow;}
console.log('PASS rank badges leave and re-enter with their epicentres after pan, zoom and resize');
