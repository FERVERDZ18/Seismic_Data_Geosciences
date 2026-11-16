'use strict';
const assert=require('node:assert/strict');
const nn=require('../system/dist/sequences/nearest-parent.js');
function row(i,lat,lon,m=4.5,t=i){return {record_id:'fixture-'+String(i).padStart(6,'0'),time_utc:new Date(Date.UTC(2016,0,1)+t*1000).toISOString(),t_year:t/nn.YEAR,latitude:lat,longitude:lon,magnitude:m};}
function nextDown(x){const b=new ArrayBuffer(8),v=new DataView(b);v.setFloat64(0,x);v.setBigUint64(0,v.getBigUint64(0)+(x>0?-1n:1n));return v.getFloat64(0);}
function parity(rows){
  const a=nn.search(rows,{backend:'reference'}),b=nn.search(rows,{backend:'kd'});
  for(const k of ['ids','parent','eta','dt','distance','tn','rn','logEta','logProduct'])assert.deepEqual(b[k],a[k],k);
  for(let i=0;i<rows.length;i++)if(b.parent[i]>=0)assert.ok(Number(rows[b.parent[i]].t_year)<Number(rows[i].t_year),'strict earlier parent');
  return b;
}
let state=20261116;const random=()=>{state=(1664525*state+1013904223)>>>0;return state/4294967296;};
const fixtures=[[],[row(0,0,0)],
 [row(0,89.99,179.99),row(1,89.99,-179.99),row(2,-89.99,179.99),row(3,-89.99,-179.99)],
 [row(0,0,0,4,0),row(1,0,0,8,0),row(2,0,0,4,1)],
 Array.from({length:512},(_,i)=>row(i,-89+178*random(),-180+360*random(),3.5+5*random(),Math.floor(i/3))),
 Array.from({length:257},(_,i)=>row(i,15+(i%17)*1e-11,-94+Math.floor(i/17)*1e-11,4.5,i))];
for(const rows of fixtures)parity(rows);
const ties=parity([row(0,0,0),row(1,0,0,8),row(2,0,0,4)]);
assert.deepEqual([...ties.parent],[-1,0,0]);assert.equal(ties.eta[2],0,'zero radius remains eligible');
const rows=[row(0,0,0,4),row(1,0,0,6),row(2,0,0,5)];
const exact={parent:Int32Array.of(-1,0,1),logEta:Float64Array.of(NaN,-6,-4)};
const included=nn.families(exact,rows,-4),excluded=nn.families(exact,rows,nextDown(-4));
assert.deepEqual([...included.component],[0,0,0]);assert.deepEqual(included.roles,['associated','main','associated']);
assert.deepEqual([...excluded.component],[0,0,2]);assert.deepEqual(excluded.roles,['associated','main','isolated']);
assert.throws(()=>nn.families(exact,rows,NaN));
assert.throws(()=>nn.search([row(0,91,0)]));
assert.throws(()=>nn.search([row(1,0,0),row(0,0,0)]));
assert.throws(()=>nn.search([{...row(0,15,-94),sin_lat:0}]));
assert.throws(()=>nn.search([{...row(0,0,0),sin_lat:0,cos_lat:1,lon_rad:0,xyz:[0,1,0]}]),/disagrees/);
assert.equal(nn.cosineDifference(0),1);
console.log('Sequence nearest-parent: exhaustive/index parity, boundaries, zeros, canonical input checks PASS ('+fixtures.length+' fixtures)');
