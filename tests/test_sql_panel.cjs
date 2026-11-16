'use strict';
// Integration seam: mount -> actual setData payload -> pinned SQLite -> rendered answer.
const assert=require('node:assert/strict'),fs=require('node:fs');
const P=require('../system/dist/sql-panel.js'),Q=require('../system/dist/sql-explorer.js');
const init=require('../system/dist/vendor/sqljs/sql-wasm.js');
class Element {
  constructor(){this.value='';this.hidden=false;this.dataset={};this.attributes={};this.classList={add(){},toggle(){}};this.listeners={};}
  setAttribute(k,v){this.attributes[k]=v;}removeAttribute(k){delete this.attributes[k];}
  addEventListener(k,v){this.listeners[k]=v;}focus(){}replaceChildren(){}
}
function surface(){
  const nodes=new Map(),labels=[],root=new Element();
  root.ownerDocument={defaultView:{},body:new Element()};
  Object.defineProperty(root,'innerHTML',{set(html){
    for(const match of html.matchAll(/data-sql-text="([^"]+)"/g)){
      const node=new Element();node.dataset.sqlText=match[1];labels.push(node);
    }
  }});
  root.querySelector=selector=>{if(!nodes.has(selector))nodes.set(selector,new Element());return nodes.get(selector);};
  root.querySelectorAll=selector=>selector==='[data-sql-text]'?labels:[];
  return {root,nodes,labels};
}
async function main(){
  const SQL=await init({wasmBinary:fs.readFileSync('system/dist/vendor/sqljs/sql-wasm.wasm')});
  let passed=0;const test=async(name,fn)=>{await fn();passed++;console.log('PASS '+name);};
  const unit='exact_source_record_groups',context={ready:true,key:'copies=1',selectionLabel:'Controlled exact-copy selection',evidence:{count_unit:unit},
    catalogs:[{catalogue_id:'A'},{catalogue_id:'B'}],records:[
      {record_key:'A~one',catalogue_id:'A',event_id:'one',time:'2020-01-01',year:2020,mag:4,mag_type:'mww',depth_km:10,exact_group_key:'g1',source_record_count:2},
      {record_key:'A~two',catalogue_id:'A',event_id:'two',time:'2022-01-01',year:2022,mag:6,mag_type:'mww',depth_km:null,exact_group_key:'g2',source_record_count:1}
    ],exact_membership:[
      {group_key:'g1',representative_key:'A~one',member_key:'A~one',catalogue_id:'A',source_event_id:'one'},
      {group_key:'g1',representative_key:'A~one',member_key:'B~one',catalogue_id:'B',source_event_id:'one'}
    ]};
  let loaded,database,language='es';const s=surface(),before=JSON.stringify(context);
  const panel=P.mount(s.root,{getContext:()=>context,getLanguage:()=>language,engine:{create:()=>({
    async setData(payload){loaded=payload;database=await Q.createDatabase(SQL,payload);return database.metadata;},
    async query(sql){return Q.execute(database.db,sql);},cancel(){},dispose(){database?.db.close();}
  })}});
  await test('mount forwards real exact-copy membership through setData to SQLite',async()=>{
    await panel.activate();assert.equal(JSON.stringify(context),before);
    assert.deepEqual(loaded.exact_membership,context.exact_membership);
    assert.equal(database.metadata.exactMembershipCount,2);
    assert.deepEqual(Q.execute(database.db,'SELECT COUNT(*), SUM(source_record_count) FROM records').rows,[[2,3]]);
    assert.equal(Q.execute(database.db,'SELECT COUNT(*) FROM exact_membership').rows[0][0],2);
    const result=panel.getResult();assert.equal(result.count_unit,unit);
    assert.equal(result.result.rows[0][0],2);assert.equal(result.result.rows[0][1],3);
    assert(result.limits[0].includes('not unique physical events'));
  });
  await test('group labels, group chart and schema are explicit in both languages',async()=>{
    assert(s.labels.filter(n=>n.dataset.sqlText==='records').every(n=>n.textContent==='grupos de copias exactas'));
    assert(s.nodes.get('.sql-result-visual').innerHTML.includes('filas de origen representadas'));
    assert(s.nodes.get('.sql-schema-tables').innerHTML.includes('exact_membership'));
    assert(s.nodes.get('.sql-schema-tables').innerHTML.includes('grupos de un miembro no aparecen'));
    assert(s.nodes.get('.sql-schema-tables').innerHTML.includes('puede ser local o derivado'));
    await panel.runGuided('annual');assert(s.nodes.get('.sql-result-visual').innerHTML.includes('Grupos de copias exactas'));
    language='en';panel.refreshLanguage();assert(s.nodes.get('.sql-result-visual').innerHTML.includes('Exact-copy groups'));
    assert(s.nodes.get('.sql-schema-tables').innerHTML.includes('need not be an official event ID'));
  });
  panel.destroy();
  await test('a represented multi-member group without actual membership fails, rather than looking validated',async()=>{
    const incomplete={...context,key:'incomplete',exact_membership:[]};
    await assert.rejects(Q.createDatabase(SQL,incomplete),/Incomplete exact-copy membership/);
    const view=surface(),bad=P.mount(view.root,{getContext:()=>incomplete,engine:{create:()=>({
      async setData(payload){return Q.createDatabase(SQL,payload);},async query(){throw Error('must not query incomplete data');},cancel(){},dispose(){}
    })}});
    await bad.activate();assert.equal(bad.getResult(),null);
    assert(view.nodes.get('.sql-query-status').textContent.includes('Incomplete exact-copy membership'));
    bad.destroy();
  });
  await test('default raw rows retain source-row labels and an empty membership table',async()=>{
    const raw={...context,key:'copies=0',evidence:{count_unit:'source_records'},exact_membership:[],records:context.records.map(r=>({...r,source_record_count:1,exact_group_key:null}))};
    let handle;const view=surface(),rawPanel=P.mount(view.root,{getContext:()=>raw,getLanguage:()=> 'en',engine:{create:()=>({
      async setData(payload){handle=await Q.createDatabase(SQL,payload);return handle.metadata;},async query(sql){return Q.execute(handle.db,sql);},cancel(){},dispose(){handle?.db.close();}
    })}});
    await rawPanel.activate();assert(view.labels.filter(n=>n.dataset.sqlText==='records').every(n=>n.textContent==='source rows'));
    assert.equal(rawPanel.getResult().count_unit,'source_records');
    assert(!rawPanel.getResult().result.columns.includes('represented_source_rows'));
    assert.equal(Q.execute(handle.db,'SELECT COUNT(*) FROM exact_membership').rows[0][0],0);
    rawPanel.destroy();
  });
  console.log(JSON.stringify({passed}));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
