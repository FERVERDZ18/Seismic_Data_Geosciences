'use strict';
const assert=require('node:assert/strict');
const gallery=require('../system/dist/article-gallery.js');
assert.equal(gallery.figureCount,13);
const en=gallery.targets('en'),es=gallery.targets('es');
assert.equal(en.length,26);
assert.deepEqual([...new Set(en.map(x=>x.figure))],Array.from({length:13},(_,i)=>i+1));
assert.equal(new Set(en.map(x=>x.href)).size,26);
assert.equal(es.length,en.length);
const legacy=en.filter(x=>x.legacy).map(x=>x.legacy);
assert.deepEqual(new Set(legacy),new Set(['1','2','3','3-time','4a','4b','4c','4d','regional-a','regional-b','regional-c','regional-d','6','7','9a','9b']));
const four=en.filter(x=>x.figure===4);
assert.deepEqual(four.map(x=>[x.letter,x.case,x.panel]),[['A','2017','full'],['B','2017','local'],['C','2017','timeline'],['D','2022','full'],['E','2022','local'],['F','2022','timeline']]);
for(let i=0;i<en.length;i++){
  const a=new URL(en[i].href,'https://example.test/observatory/index.html');
  const b=new URL(es[i].href,'https://example.test/observatory/index.html');
  assert.equal(a.pathname,'/observatory/index.html');
  assert.equal(a.origin,'https://example.test');
  assert.equal(a.searchParams.get('lang'),'en');assert.equal(b.searchParams.get('lang'),'es');
  assert.equal(a.hash,'');
  if(en[i].view){
    assert.equal(a.searchParams.get('workspace'),'sequences');
    assert.equal(a.searchParams.get('view'),en[i].view);
    if(en[i].view==='cases'){assert.equal(a.searchParams.get('comparison'),'both');assert.equal(a.searchParams.get('membership'),'native');}
  }else assert.equal(a.searchParams.get('figure'),en[i].legacy);
}
assert.equal(new URL(en.find(x=>x.figure===5&&x.panel==='inspector').href,'https://example.test/').searchParams.get('panel'),'inspector');
const view=require('../system/dist/sequences/sequence-view.js');
for(const target of four){const state=view.parse(new URL(target.href,'https://example.test/').search);assert.equal(state.point_size,'large');for(const key of ['full_lat','full_lon','full_zoom','local_lat','local_lon','local_zoom'])assert.notEqual(state[key],null,key);}
const inspector=view.parse(new URL(en.find(x=>x.figure===5&&x.panel==='inspector').href,'https://example.test/').search);assert.equal(inspector.inspect_source,'ssn');assert.equal(inspector.inspect_record,'ssn-mx-historical~ssn-local-81c01bd323843b791355110b-1');
assert.equal(new URL(gallery.href({legacy:'5'},'es'),'https://example.test/').searchParams.get('figure'),'5');
assert.equal(new URL(gallery.href({legacy:'8'},'en'),'https://example.test/').searchParams.get('figure'),'8');
console.log('Article gallery: thirteen figures, twenty-six functional targets and historical IDs PASS');
