'use strict';
importScripts('../nearest-parent.js');
self.onmessage=event=>{
  const {command,rows,backend}=event.data;
  try{
    if(command==='warm'){
      for(const kind of ['reference','kd'])self.SequenceNearestParent.search(rows,{backend:kind,d:1.6,w:1,q:.5});
      self.postMessage({status:'WARMED'});return;
    }
    const started=performance.now(),result=self.SequenceNearestParent.search(rows,{backend,d:1.6,w:1,q:.5});
    const wall=performance.now()-started,fields={};
    for(const key of ['parent','eta','dt','distance','tn','rn','logEta','logProduct'])fields[key]=result[key].buffer;
    self.postMessage({status:'COMPUTED',metadata:result.metadata,worker_wall_ms:wall,
      ids:result.ids,fields},Object.values(fields));
  }catch(error){self.postMessage({status:'FAIL',error:String(error.stack||error)});}
};

