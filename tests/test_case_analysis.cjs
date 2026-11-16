'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const C=require('../system/dist/sequences/case-analysis.js'),N=require('../system/dist/sequences/nearest-parent.js');
const directory=path.join(__dirname,'../system/dist/sequences/data');
const read=n=>JSON.parse(fs.readFileSync(path.join(directory,n),'utf8'));
const inputs=read('inputs_4_5.json'),calibration=read('calibration.json'),definitions=read('diagnostics.json').cases,pairs=read('candidates_4_5.json').pairs;
const classified={};
for(const source of ['ssn','usgs']){
  classified[source]={};
  for(const weight of ['fixed','reported_b']){
    const c=weight==='fixed'?calibration.cuts['4.5'][source]:calibration.weight_modes.reported_b[source],rows=inputs.sources[source];
    const p=N.search(rows,{d:1.6,w:c.w??1,q:.5,backend:'kd'}),g=N.families(p,rows,c.threshold_log10);
    classified[source][weight]={rows,result:{ids:p.ids,parent:Array.from(p.parent),component:Array.from(g.component),roles:g.roles,log_eta:Array.from(p.logEta),metadata:{...p.metadata,w:c.w??1,threshold_log10:c.threshold_log10}}};
  }
}
for(const [year,expected] of Object.entries({'2017':{full:[292,955,204,208],local:[148,137],localFamily:[148,136],pairs:86,witness:['2017-09-19T18:14:39Z','2017-11-02T15:49:08.650Z']},'2022':{full:[21,84,10,10],local:[13,9],localFamily:[13,9],pairs:8,witness:['2022-09-24T08:37:53Z',null]}})){
  const a=C.analyze({definitions,classified,pairs,state:{case:year,radius:'150',before:'7',after:'30'}}),s=a.sources;
  assert.deepEqual([s.ssn.membersFixed.length,s.ssn.membersWeighted.length,s.usgs.membersFixed.length,s.usgs.membersWeighted.length],expected.full);
  assert.deepEqual([s.ssn.local.length,s.usgs.local.length],expected.local);
  assert.deepEqual([s.ssn.localFixed.length,s.usgs.localFixed.length],expected.localFamily);
  assert.equal(a.localPairs.length,expected.pairs);
  for(const [i,source] of ['ssn','usgs'].entries()){
    const v=s[source];assert.equal(v.witnessIndex===null?null:v.rows[v.witnessIndex].time_utc,expected.witness[i]);
    if(v.witnessIndex!==null){const detail=C.inspect(a,source,v.witnessIndex);assert.notEqual(detail.fixed.role,detail.reported_b.role);assert.equal(detail.record_id,v.rows[v.witnessIndex].record_id);}
  }
  const altered=C.analyze({definitions,classified,pairs,state:{case:year,radius:'75',before:'1',after:'3'}});
  assert.deepEqual([altered.sources.ssn.witnessIndex,altered.sources.usgs.witnessIndex],[s.ssn.witnessIndex,s.usgs.witnessIndex]);
  for(const source of ['ssn','usgs']){
    assert.deepEqual(altered.sources[source].membersFixed,s[source].membersFixed);
    assert.deepEqual(altered.sources[source].membersWeighted,s[source].membersWeighted);
  }
  assert(altered.sources.ssn.local.length<=s.ssn.local.length);
  for(const p of C.circle(a.anchor))assert(Math.abs(C.distance(a.anchor,{latitude:p[0],longitude:p[1]})-150)<1e-7);
  if(year==='2017'){assert(Math.abs(s.ssn.fixedSpan.maximum_gap_days-929.607)<.001);assert(s.ssn.fixedSpan.span_days>2600);}
}
assert.throws(()=>C.analyze({definitions,classified,pairs,state:{case:'1900'}}));
assert.throws(()=>C.analyze({definitions,classified,pairs,state:{case:'2017',radius:'NaN'}}));
const incomplete={...classified,ssn:{...classified.ssn,fixed:{...classified.ssn.fixed,result:{...classified.ssn.fixed.result,component:[]}}}};
assert.throws(()=>C.analyze({definitions,classified:incomplete,pairs,state:{case:'2017'}}),/Incomplete source classification/);
console.log('PASS: native case families, published witnesses, local memberships, candidate links and immutable display-window semantics');
