'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const dir=path.resolve(__dirname,'../system/dist/sequences/data');
const manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
const counts={'4_5':{ssn:1780,usgs:1256,alaska:555},'4_1':{ssn:14537,usgs:3139,alaska:1260},'3_5':{ssn:170880,usgs:3945,alaska:3630}};
let files=0,observations=0;
for(const [name,spec] of Object.entries(manifest.files)) {
  assert.equal(path.basename(name),name,'flat source path');
  const bytes=fs.readFileSync(path.join(dir,name));
  assert.equal(bytes.length,spec.bytes,name+' size');assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),spec.sha256,name+' hash');files++;
  if(name.startsWith('inputs_')) {
    const value=JSON.parse(bytes.toString('utf8')),cut=name.slice(7,-5),expected=counts[cut];assert.ok(expected,name);
    for(const [source,rows] of Object.entries(value.sources)) {
      assert.equal(rows.length,expected[source],name+'/'+source);observations+=rows.length;
      const ids=new Set();let previous=null;
      for(const r of rows) {
        assert.ok(!ids.has(r.record_id),'unique namespaced ID');ids.add(r.record_id);
        assert.ok(Number(r.magnitude)>=Number(cut.replace('_','.')),'reported selection');
        assert.ok([r.t_year,Number(r.latitude),Number(r.longitude),r.sin_lat,r.cos_lat,r.lon_rad,...r.xyz].every(Number.isFinite),'finite canonical inputs');
        assert.equal(r.xyz.length,3);
        if(previous) {
          assert.ok(previous.time_utc<=r.time_utc || previous.t_year<=r.t_year,'chronological inputs');
          assert.ok(previous.t_year<=r.t_year,'chronological epoch years');
          if(previous.time_utc===r.time_utc)assert.ok(Buffer.compare(Buffer.from(previous.record_id),Buffer.from(r.record_id))<=0,'UTF-8 tie ordering');
        }
        for(const forbidden of ['role','roles','parent','parent_index','classification','component'])assert.ok(!(forbidden in r),'no offline answer in observation input');
        previous=r;
      }
    }
  }
}
const c=JSON.parse(fs.readFileSync(path.join(dir,'calibration.json'),'utf8'));
for(const source of ['ssn','usgs','alaska'])assert.equal(c.cuts['4.5'][source].diagnostics.two_mode_BIC_guard_passed,true,'primary supported separation');
for(const cut of ['3.5','4.1'])assert.equal(c.cuts[cut].ssn.diagnostics.two_mode_BIC_guard_passed,false,'unsupported sensitivities stay explicit');
console.log(`Sequence scientific manifest: ${files} verified files; ${observations} row-selections; no offline classifications PASS`);
