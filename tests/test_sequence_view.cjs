'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const view=require('../system/dist/sequences/sequence-view.js');
assert.deepEqual(view.parse(''),{lang:'es',region:'mexico',cut:'4.5',method:'nn',weight:'fixed',membership:'native',case:'all',extent:'local'});
const weighted={lang:'en',region:'mexico',cut:'4.5',method:'nn',weight:'reported_b',membership:'common',case:'2017',extent:'family'};
assert.deepEqual(view.parse(view.query(weighted)),weighted);
assert.deepEqual(view.articleCase('2022','en'),{...weighted,case:'2022',weight:'fixed',membership:'native'});
assert.equal(view.parse('?case=2017&region=alaska&weight=reported_b&membership=common&extent=family').case,'all');
assert.equal(view.parse('?region=alaska&membership=common').membership,'native');
assert.equal(view.parse('?method=gk&weight=reported_b').weight,'fixed');
assert.equal(view.parse('?cut=3.5&weight=reported_b').weight,'fixed');
assert.equal(view.parse('?case=javascript%3Aalert(1)&lang=xx&cut=0&extent=family').case,'all');
assert.equal(view.parse('?case=all&extent=family').extent,'local');
assert(!view.query({...weighted,redirect:'https://example.com',token:'private'}).includes('redirect'));
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
