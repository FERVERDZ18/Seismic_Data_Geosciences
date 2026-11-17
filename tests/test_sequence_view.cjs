'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const view=require('../system/dist/sequences/sequence-view.js');
const defaults=view.parse('');
assert.equal(defaults.view,'explorer');assert.equal(defaults.case,'all');assert.equal(defaults.cut,'4.5');assert.equal(defaults.pair_cut,'3.5');assert.equal(defaults.radius,'150');
const weighted={...defaults,lang:'en',region:'mexico',cut:'4.5',method:'nn',weight:'reported_b',membership:'common',case:'2017',extent:'family'};
assert.deepEqual(view.parse(view.query(weighted)),weighted);
assert.deepEqual(view.articleCase('2022','en'),{...weighted,view:'cases',case:'2022',weight:'fixed',membership:'native'});
assert.equal(view.parse('?view=cases&source=alaska&region=alaska&case=all&cut=3.5&method=gk').case,'2017');
assert.equal(view.parse('?view=cases&source=alaska').source,'all');
const nativeCase=view.parse('?view=cases&case=2022&comparison=both&radius=200&before=3&after=40&lang=en');
assert.deepEqual(view.parse(view.query(nativeCase)),nativeCase);
assert.equal(view.parse('?radius=Infinity&before=-1&after=1000&benchmark_n=javascript:1').radius,'150');
assert.equal(view.parse('?radius=Infinity&before=-1&after=1000').after,'30');
assert.equal(view.parse('?view=diagnostics&cut=4.5&pair_cut=3.5').pair_cut,'3.5');
assert.equal(view.parse('?view=benchmark&benchmark_metric=phases&benchmark_n=170880&scale=linear').benchmark_n,'170880');
assert.equal(view.parse('?view=benchmark&benchmark_n=12345').benchmark_n,'all');
assert.equal(view.parse('?view=benchmark&benchmark_n=002000').benchmark_n,'2000');
const focused=view.parse('?view=cases&case=2022&panel=local&lang=en');assert.equal(focused.panel,'local');assert.deepEqual(view.parse(view.query(focused)),focused);
assert.equal(view.parse('?view=diagnostics&panel=local').panel,'all');assert.equal(view.parse('?view=cases&panel=javascript:1').panel,'all');
assert.equal(view.parse('?case=2017&region=alaska&weight=reported_b&membership=common&extent=family').case,'all');
assert.equal(view.parse('?region=alaska&membership=common').membership,'native');
assert.equal(view.parse('?method=gk&weight=reported_b').weight,'fixed');
assert.equal(view.parse('?cut=3.5&weight=reported_b').weight,'fixed');
assert.equal(view.parse('?case=javascript%3Aalert(1)&lang=xx&cut=0&extent=family').case,'all');
assert.equal(view.parse('?case=all&extent=family').extent,'local');
assert(!view.query({...weighted,redirect:'https://example.com',token:'private'}).includes('redirect'));
const framed=view.parse('?view=cases&case=2022&panel=full&expanded_map=full&point_size=large&full_lat=18.503259&full_lon=-103.22556&full_zoom=7.3&local_lat=18.4&local_lon=-103.3&local_zoom=8.2&inspect_source=ssn&inspect_record=ssn-mx-historical~ssn-local-abc-1');
assert.deepEqual(view.parse(view.query(framed)),framed);
assert.equal(framed.expanded_map,'full');assert.equal(framed.point_size,'large');assert.equal(framed.inspect_source,'ssn');
assert.deepEqual(view.mapViewport(framed,'full'),{latitude:18.503259,longitude:-103.22556,zoom:7.3});
for(const invalid of [
  {full_lat:'90'}, {full_lat:'-90'}, {full_lat:'NaN'}, {full_lat:'Infinity'}, {full_lat:''}, {full_lat:'0x10'}, {full_lat:' 18 '}, {full_lat:[]},
  {full_lon:'181'}, {full_lon:'-181'}, {full_zoom:'1.9'}, {full_zoom:'13.1'}, {full_zoom:null}, {full_lon:undefined}
]){const rejected=view.normalize({...framed,...invalid});for(const key of ['full_lat','full_lon','full_zoom'])assert.equal(rejected[key],undefined);assert.equal(rejected.local_zoom,'8.2');}
for(const viewport of [{full_lat:'85.051129',full_lon:'180',full_zoom:'13'},{full_lat:'-85.051129',full_lon:'-180',full_zoom:'2'}]){const accepted=view.normalize({...framed,...viewport});assert.deepEqual(view.parse(view.query(accepted)),accepted);}
assert.equal(view.normalize({...framed,full_lat:'18.12345678'}).full_lat,'18.123457');
assert.equal(view.normalize({...framed,full_zoom:'7.3456'}).full_zoom,'7.3');
for(const invalid of [{inspect_source:'alaska'},{inspect_record:'../private'},{inspect_record:'<script>'},{inspect_record:'a'.repeat(257)},{inspect_record:null}]){const rejected=view.normalize({...framed,...invalid});assert.equal(rejected.inspect_source,undefined);assert.equal(rejected.inspect_record,undefined);}
for(const patch of [{case:'2017'},{membership:'common'},{radius:'200'},{before:'3'},{after:'40'}]){const changed=view.transition(framed,patch);for(const key of [...view.viewportKeys,'inspect_source','inspect_record'])assert.equal(changed[key],undefined);}
for(const patch of [{lang:'es'},{source:'usgs'},{comparison:'fixed'},{panel:'inspector'},{expanded_map:'local'},{point_size:'normal'}]){const changed=view.transition(framed,patch);assert.equal(changed.full_zoom,'7.3');assert.equal(changed.inspect_record,framed.inspect_record);}
const otherView=view.normalize({...framed,view:'diagnostics'});assert.equal(otherView.full_lat,undefined);assert.equal(otherView.inspect_record,undefined);assert.equal(otherView.expanded_map,'none');assert.equal(otherView.point_size,'normal');
assert.equal(view.parse('?view=cases&expanded_map=javascript:1&point_size=huge').expanded_map,'none');
const distance=(a,b)=>{const r=Math.PI/180,p=(b.latitude-a.latitude)*r,l=(b.longitude-a.longitude)*r,h=Math.sin(p/2)**2+Math.cos(a.latitude*r)*Math.cos(b.latitude*r)*Math.sin(l/2)**2;return 2*6371.0088*Math.asin(Math.sqrt(Math.min(1,h)));};
for(const anchor of [{latitude:15,longitude:-94},{latitude:18.4,longitude:-103.3},{latitude:80,longitude:179.9}]){
  const points=view.referenceCircle(anchor);assert.equal(points.length,121);
  for(const p of points)assert(Math.abs(distance(anchor,p)-150)<1e-7);
  assert(Math.abs(points[0].latitude-points.at(-1).latitude)<1e-10);
  assert(Math.abs(points[0].longitude-points.at(-1).longitude)<1e-10);
}
assert.throws(()=>view.referenceCircle({latitude:91,longitude:0}));
const directory=path.join(__dirname,'../system/dist/sequences'),manifest=JSON.parse(fs.readFileSync(path.join(directory,'figures/manifest.json'),'utf8'));
const manuscriptPins={4:'0b9dacc6f0825940fd4401a340c3a6806e5cb827203334142a4867d670bf6f1b',3:'c8d94ee30e99a45038df8f627d43b9c1c402a2a8b3c72070f227d4374c852a84',2:'d9f02368bfa26195966ca8e8faf11325322926c982d46afa22760f5b3df7bea9'};
assert.equal(manifest.reference_manuscript_pdf_sha256,'8593a19d51ccc5a5a8168278f2869a53c5fcc2af0472f9b23ed5da5aaaee9f66');
assert.deepEqual(manifest.assets.map(a=>a.article_figure).sort(),[2,3,4]);
for(const item of manifest.assets){const data=fs.readFileSync(path.join(directory,item.path));assert.equal(data.length,item.bytes);assert.equal(crypto.createHash('sha256').update(data).digest('hex'),manuscriptPins[item.article_figure]);assert.equal(item.sha256,manuscriptPins[item.article_figure]);assert.equal(data.readUInt32BE(16),item.width);assert.equal(data.readUInt32BE(20),item.height);}
console.log('PASS: shared routes, incompatible/untrusted selections, spherical reference circles, and three byte-exact manuscript figures');
