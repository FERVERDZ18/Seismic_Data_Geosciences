'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const math=require('../system/dist/sequences/diagnostics-math.js'),nn=require('../system/dist/sequences/nearest-parent.js');
const directory=path.join(__dirname,'../system/dist/sequences/data');
assert.equal(math.tenthHalfUp('3.55'),36);assert.equal(math.tenthHalfUp('3.45'),35);assert.equal(math.tenthHalfUp('-0.05'),-1);
assert.equal(math.compareDecimal('0.30000000000000001','0.3'),1);
assert.equal(math.gft(['3.49','3.50','3.55'],'3.5').n,2,'cut original magnitudes before half-up binning');
assert.equal(math.gft([],'4.5').b_reported_MLE,null);
assert.deepEqual(math.cumulativeFmd([3.51,3.55,3.55,4.1].map(magnitude=>({magnitude}))),[
  {magnitude:3.51,count:1,cumulative:4},{magnitude:3.55,count:2,cumulative:3},{magnitude:4.1,count:1,cumulative:1}
]);
const simple=math.boxSummary([0,1,2,3,100].map(delta_m=>({delta_m:String(delta_m)})));
assert.deepEqual([simple.q1,simple.median,simple.q3,simple.lower_whisker,simple.upper_whisker],[1,2,3,0,3]);assert.equal(simple.outliers[0].delta_m,'100');
const decimalPair=math.pairedGroups([{ssn:'a',usgs:'b',delta_m:'0.3'}],[{record_id:'a',magnitude:4.6}],[{record_id:'b',magnitude:4.3,magnitude_type:'mb'}]);
assert.equal(decimalPair.groups[0].median,.3,'use the retained decimal difference, not binary subtraction');
const masked=math.trPoints([{}, {}, {}],{ids:['a','b','c'],parent:[-1,0,0],tn:[null,1,1],rn:[null,0,1e-5],metadata:{threshold_log10:-5}});
assert.equal(masked.no_parent,1);assert.equal(masked.nonpositive_with_parent,1);assert.equal(masked.points.length,1);assert.equal(masked.points[0].retained,true,'inclusive author cutoff');

const raw=fs.readFileSync(path.join(directory,'inputs_3_5.json'));
assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),'9bcac42fe96e6b0980020bae609383d7a5898ddc467e536b4203f437fadceb03');
const inputs=JSON.parse(raw),expectations={
  ssn:{n:170880,'4.1':[14537,2.164882600403793,88.40691307876102],'4.5':[1780,1.3411592258636142,93.41839921370854]},
  usgs:{n:3945,'4.1':[3139,.9870400598735166,94.58181682481556],'4.5':[1256,1.0571199016869839,96.82468447923978]},
  alaska:{n:3630,'4.1':[1260,.8995743008352742,95.73996203143058],'4.5':[555,.9439335713973163,95.57217301679992]}
};
for(const [source,expected]of Object.entries(expectations)){
  assert.equal(math.cumulativeFmd(inputs.sources[source])[0].cumulative,expected.n);
  for(const cut of ['4.1','4.5']){const value=math.gft(inputs.sources[source].map(r=>r.magnitude),cut),[n,b,gft]=expected[cut];assert.equal(value.n,n);assert(Math.abs(value.b_reported_MLE-b)<1e-12);assert(Math.abs(value.fit_percent-gft)<1e-10);}
}
const pairs=JSON.parse(fs.readFileSync(path.join(directory,'candidates_3_5.json'))).pairs,boxes=math.pairedGroups(pairs,inputs.sources.ssn,inputs.sources.usgs);
assert.equal(boxes.pairs.length,2989);assert.deepEqual(boxes.groups.map(g=>[g.name,g.n]),[['mb',2546],['ml',66],['mwr',52],['mww',276],['other',49]]);
assert.deepEqual(boxes.groups.map(g=>g.median),[.2,.315,.2,0,.14]);
assert.equal(math.pairedGroups(pairs,inputs.sources.ssn,inputs.sources.usgs,'4.5').pairs.length,889);
const primary=JSON.parse(fs.readFileSync(path.join(directory,'inputs_4_5.json'))),calibration=JSON.parse(fs.readFileSync(path.join(directory,'calibration.json')));
for(const [source,plotted,retained]of [['ssn',1779,581],['usgs',1255,405]]){
  const rows=primary.sources[source],cut=calibration.cuts['4.5'][source].threshold_log10,p=nn.search(rows,{d:1.6,w:1,q:.5,backend:'kd'}),diagnostic=math.trPoints(rows,{ids:p.ids,parent:p.parent,tn:p.tn,rn:p.rn,metadata:{threshold_log10:cut}});
  assert.equal(diagnostic.points.length,plotted);assert.equal(diagnostic.no_parent,1);assert.equal(diagnostic.nonpositive_with_parent,0);assert.equal(diagnostic.points.filter(p=>p.retained).length,retained);
}
console.log('PASS: exact reported-magnitude cuts/rounding, six Python-reference b/GFT results, 2989 paired differences, and native T–R counts/masks');
